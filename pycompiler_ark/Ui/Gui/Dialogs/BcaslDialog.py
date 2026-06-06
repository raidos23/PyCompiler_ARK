# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
BcaslDialog — éditeur visuel du pipeline BCASL (Qt pur).

Respecte la SPEC UX BCASL :
  - Sections collapsibles par catégorie (tag → phase)
  - Spinbox priorité + ⚠️ hors-plage
  - ↑ / ↓ intra-section, DnD intra-section
  - Expert mode
  - Ctrl+S / Ctrl+Z / Ctrl+Y / Space / ↑↓
  - Format bcasl.yml : plugins en liste [{name, enabled, priority, config}]
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Optional

import yaml
from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot
from PySide6.QtGui import QKeySequence, QPalette, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from pycompiler_ark.Core.Configs import load_ark_config, save_ark_config

# ---------------------------------------------------------------------------
# Helpers Thème
# ---------------------------------------------------------------------------


def _is_dark() -> bool:
    """Détermine si le thème actuel est sombre."""
    try:
        from pycompiler_ark.Ui.Gui.UiConnection import _is_qss_dark

        app = QApplication.instance()
        return _is_qss_dark(app.styleSheet() if app else "")
    except Exception:
        return False


def _get_bcasl_colors() -> dict[str, str]:
    """Retourne les couleurs adaptées au thème (soumis au thème)."""
    app = QApplication.instance()
    pal = app.palette() if app else QPalette()

    # Récupérer les couleurs système pour une intégration parfaite
    # PlaceholderText est excellent pour les labels secondaires (gris dynamique)
    secondary_text = pal.color(QPalette.PlaceholderText).name()
    # AlternateBase est fait pour le contraste de fond dans les listes/groupes
    alt_bg = pal.color(QPalette.AlternateBase).name()

    if _is_dark():
        return {
            "warn_bg": "#504010",  # Ambre sombre mais distinct du fond ("noir")
            "warn_border": "#D4A017",  # Orange/Or
            "section_bg": alt_bg,
            "section_label": secondary_text,
        }
    return {
        "warn_bg": "#FFF3CD",  # Jaune pâle
        "warn_border": "orange",
        "section_bg": alt_bg,
        "section_label": secondary_text,
    }


def _apply_themed_icon(widget: QPushButton, icon_name: str, size: int = 18) -> None:
    """Applique une icône SVG thémée au widget."""
    try:
        from PySide6.QtCore import QSize

        from pycompiler_ark.Ui.Gui.UiConnection import themed_svg_icon

        # icons/ is at project root, which is 3 levels up from this file (Ui/Gui/Dialogs/)
        icon_path = os.path.abspath(
            os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                os.pardir,
                os.pardir,
                os.pardir,
                "data",
                "icons",
                icon_name,
            )
        )
        icon = themed_svg_icon(icon_path, size=size)
        if icon:
            widget.setIcon(icon)
            widget.setIconSize(QSize(size, size))
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

# phase_score → (display_name, description)
SECTION_PHASES: dict[int, tuple[str, str]] = {
    0: ("Cleanup", "Workspace cleanup and hygiene"),
    10: ("Validation", "Prerequisite validation and checking"),
    20: ("Preparation", "Resource preparation and generation"),
    30: ("Compliance", "Compliance and header injection"),
    40: ("Linting", "Linting, formatting, and type checking"),
    50: ("Obfuscation", "Obfuscation, protection and transpilation"),
    100: ("Default", "Other actions (default phase)"),
}

# Tag → score de phase
_TAG_PRIORITY_MAP: dict[str, int] = {}
try:
    from pycompiler_ark.bcasl.tagging import TAG_PRIORITY_MAP as _TAG_PRIORITY_MAP  # type: ignore
except Exception:
    pass


def _phase_score_for_tags(tags: list[str]) -> int:
    """Retourne le score de phase minimum pour une liste de tags."""
    scores = [_TAG_PRIORITY_MAP.get(str(t).strip().lower(), 100) for t in (tags or [])]
    return min(scores) if scores else 100


def _section_for_phase(score: int) -> tuple[int, str]:
    """Retourne (key, name) pour un score de phase."""
    # Trouver la section dont le score correspond
    for key in sorted(SECTION_PHASES):
        if score == key:
            name, _ = SECTION_PHASES[key]
            return key, name
    # Section par défaut
    name, _ = SECTION_PHASES[100]
    return 100, name


# ---------------------------------------------------------------------------
# Helpers lecture/écriture plugins
# ---------------------------------------------------------------------------


def _read_plugin_list(plugins_raw: Any) -> list[dict[str, Any]]:
    """Normalise plugins (liste ou dict) → liste [{name, enabled, priority, config}]."""
    if isinstance(plugins_raw, list):
        result = []
        for item in plugins_raw:
            if isinstance(item, dict) and item.get("name"):
                result.append(item)
        return result
    if isinstance(plugins_raw, dict):
        result = []
        for name, val in plugins_raw.items():
            if isinstance(val, bool):
                result.append(
                    {"name": name, "enabled": val, "priority": 0, "config": {}}
                )
            elif isinstance(val, dict):
                result.append(
                    {
                        "name": name,
                        "enabled": bool(val.get("enabled", True)),
                        "priority": int(val.get("priority", 0)),
                        "config": dict(val.get("config", {})),
                    }
                )
        return result
    return []


def _plugins_list_to_yaml(plugin_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Retourne la liste dans le format bcasl.yml officiel."""
    result = []
    for row in plugin_rows:
        result.append(
            {
                "name": row["name"],
                "enabled": bool(row.get("enabled", True)),
                "priority": int(row.get("priority", 0)),
                "config": dict(row.get("config", {})),
            }
        )
    return result


# ---------------------------------------------------------------------------
# Widget : ligne de plugin
# ---------------------------------------------------------------------------


class _PluginRow(QFrame):
    """Widget représentant un seul plugin dans le pipeline."""

    sig_move_up = Signal(str)  # plugin_id
    sig_move_down = Signal(str)
    sig_enabled = Signal(str, bool)

    def __init__(
        self,
        pid: str,
        name: str,
        enabled: bool,
        config: Optional[dict] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.pid = pid
        self.config: dict[str, Any] = dict(config or {})
        self._on_save_cb = None

        self.setFrameShape(QFrame.StyledPanel)
        self.setObjectName("PluginRow")

        row = QHBoxLayout(self)
        row.setContentsMargins(8, 4, 8, 4)
        row.setSpacing(8)

        # Checkbox enabled
        self.chk = QCheckBox()
        self.chk.setChecked(enabled)
        self.chk.setFixedWidth(20)
        self.chk.toggled.connect(lambda v: self.sig_enabled.emit(self.pid, v))
        row.addWidget(self.chk)

        # Nom plugin
        self.lbl_name = QLabel(name or pid)
        self.lbl_name.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        row.addWidget(self.lbl_name)

        # Boutons ↑ ↓
        self.btn_up = QPushButton()
        self.btn_up.setFixedWidth(32)
        self.btn_up.setToolTip("Monter dans la section")
        _apply_themed_icon(self.btn_up, "chevron-up.svg", size=18)
        self.btn_up.clicked.connect(lambda: self.sig_move_up.emit(self.pid))
        row.addWidget(self.btn_up)

        self.btn_down = QPushButton()
        self.btn_down.setFixedWidth(32)
        self.btn_down.setToolTip("Descendre dans la section")
        _apply_themed_icon(self.btn_down, "chevron-down.svg", size=18)
        self.btn_down.clicked.connect(lambda: self.sig_move_down.emit(self.pid))
        row.addWidget(self.btn_down)

        self.setStyleSheet(
            "QFrame#PluginRow { background: transparent; border: none; }"
        )

    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Accesseurs

    @property
    def is_enabled(self) -> bool:
        return self.chk.isChecked()

    def snapshot(self) -> dict[str, Any]:
        return {"pid": self.pid, "enabled": self.is_enabled}

    def restore(self, snap: dict[str, Any]) -> None:
        self.chk.setChecked(bool(snap.get("enabled", True)))


# ---------------------------------------------------------------------------
# Widget : section collapsible
# ---------------------------------------------------------------------------


class _SectionWidget(QGroupBox):
    """Section collapsible utilisant QGroupBox pour une meilleure intégration thématique."""

    sig_changed = Signal()

    def __init__(
        self,
        phase_key: int,
        name: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.phase_key = phase_key
        self._name = name
        self._rows: list[_PluginRow] = []

        # Titre natif du GroupBox
        self.setTitle(name)

        # Rendre le GroupBox collapsible via la checkbox native
        self.setCheckable(True)
        self.setChecked(True)
        self.toggled.connect(self._on_toggled)

        self._content_lay = QVBoxLayout(self)
        self._content_lay.setContentsMargins(8, 12, 8, 8)
        self._content_lay.setSpacing(3)

    # ------------------------------------------------------------------

    def _on_toggled(self, checked: bool) -> None:
        """Cache/affiche les lignes de plugins quand on toggle le GroupBox."""
        for i in range(self._content_lay.count()):
            item = self._content_lay.itemAt(i)
            if item and item.widget():
                item.widget().setVisible(checked)

    def add_row(self, row: _PluginRow) -> None:
        self._rows.append(row)
        self._content_lay.addWidget(row)
        row.sig_move_up.connect(self._on_move_up)
        row.sig_move_down.connect(self._on_move_down)
        row.sig_enabled.connect(lambda _pid, _v: self.sig_changed.emit())
        # S'assurer que la visibilité suit l'état actuel du toggle
        row.setVisible(self.isChecked())
        # Mettre à jour l'état des boutons ↑/↓ pour toute la section
        self._refresh_arrow_buttons()

    def _on_move_up(self, pid: str) -> None:
        idx = self._find_idx(pid)
        if idx <= 0:
            return
        self._swap(idx, idx - 1)
        self.sig_changed.emit()

    def _on_move_down(self, pid: str) -> None:
        idx = self._find_idx(pid)
        if idx < 0 or idx >= len(self._rows) - 1:
            return
        self._swap(idx, idx + 1)
        self.sig_changed.emit()

    def _find_idx(self, pid: str) -> int:
        for i, r in enumerate(self._rows):
            if r.pid == pid:
                return i
        return -1

    def _swap(self, i: int, j: int) -> None:
        """Échange visuellement deux lignes dans le layout."""
        self._rows[i], self._rows[j] = self._rows[j], self._rows[i]
        # Retirer tous les widgets et les ré-insérer dans le bon ordre
        for r in self._rows:
            self._content_lay.removeWidget(r)
        for r in self._rows:
            self._content_lay.addWidget(r)
        # Mettre à jour les boutons ↑/↓
        self._refresh_arrow_buttons()

    def _refresh_arrow_buttons(self) -> None:
        n = len(self._rows)
        for i, row in enumerate(self._rows):
            row.btn_up.setEnabled(i > 0)
            row.btn_down.setEnabled(i < n - 1)

    def refresh_expert(self) -> None:
        for row in self._rows:
            row.refresh_expert()

    def snapshot(self) -> list[dict]:
        return [r.snapshot() for r in self._rows]

    def restore(self, snaps: list[dict]) -> None:
        pid_to_snap = {s["pid"]: s for s in snaps}
        # Ré-ordonner les rows selon l'ordre du snapshot
        new_order: list[_PluginRow] = []
        for snap in snaps:
            row = next((r for r in self._rows if r.pid == snap["pid"]), None)
            if row:
                new_order.append(row)
                row.restore(snap)
        remaining = [r for r in self._rows if r.pid not in pid_to_snap]
        self._rows = new_order + remaining
        # Ré-afficher dans le bon ordre
        for r in self._rows:
            self._content_lay.removeWidget(r)
        for r in self._rows:
            self._content_lay.addWidget(r)
        self._refresh_arrow_buttons()

    @property
    def rows(self) -> list[_PluginRow]:
        return list(self._rows)

    @property
    def is_empty(self) -> bool:
        return len(self._rows) == 0


# ---------------------------------------------------------------------------
# Dialog principal
# ---------------------------------------------------------------------------


class BcaslPipelineDialog(QDialog):
    """Éditeur visuel du pipeline BCASL."""

    MAX_UNDO = 50

    def __init__(
        self,
        gui,
        workspace_root: Path,
        meta_map: "dict[str, dict[str, Any]]",
        cfg: "dict[str, Any]",
        plugin_instances: "dict[str, Any]",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent or gui)
        self._gui = gui
        self._workspace_root = workspace_root
        self._meta_map = meta_map
        self._cfg = cfg
        self._plugin_instances = plugin_instances

        # Charger la configuration ark.yml pour l'état d'activation global
        try:
            self._ark_cfg = load_ark_config(workspace_root)
        except Exception:
            self._ark_cfg = {}

        # Undo / Redo stacks
        self._undo_stack: list[Any] = []
        self._redo_stack: list[Any] = []

        self._sections: list[_SectionWidget] = []
        self._plugin_ui_state: dict[str, dict[str, Any]] = {}

        self.setWindowTitle(gui.tr("BCASL Pipeline", "BCASL Pipeline"))
        self.resize(860, 680)
        self.setModal(False)

        self._build_ui()
        self._install_shortcuts()
        self._push_undo()  # état initial

    # ------------------------------------------------------------------
    # Construction UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        main = QVBoxLayout(self)
        main.setSpacing(6)
        main.setContentsMargins(10, 10, 10, 10)

        # Titre
        title_row = QHBoxLayout()
        lbl = QLabel("<b>BCASL Pipeline</b>")
        lbl.setTextFormat(Qt.RichText)
        title_row.addWidget(lbl)
        title_row.addStretch(1)

        # Case à cocher pour l'activation globale (gérée par ark.yml)
        self._chk_bcasl_enabled = QCheckBox(
            self._gui.tr("Activer BCASL", "Enable BCASL")
        )
        self._chk_bcasl_enabled.setStyleSheet("font-weight: bold;")
        bcasl_active = self._ark_cfg.get("plugins", {}).get("bcasl_enabled", True)
        self._chk_bcasl_enabled.setChecked(bool(bcasl_active))
        self._chk_bcasl_enabled.toggled.connect(self._on_bcasl_enabled_toggled)
        title_row.addWidget(self._chk_bcasl_enabled)

        main.addLayout(title_row)

        # Tabs : Pipeline + onglets plugins
        self._tabs = QTabWidget()
        main.addWidget(self._tabs, 1)

        # Tab pipeline
        pipeline_tab = QWidget()
        pipeline_lay = QVBoxLayout(pipeline_tab)
        pipeline_lay.setContentsMargins(0, 4, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; }")

        container = QWidget()
        container.setObjectName("PipelineContainer")
        container.setStyleSheet(
            "QWidget#PipelineContainer { background: transparent; }"
        )

        self._pipeline_lay = QVBoxLayout(container)
        self._pipeline_lay.setSpacing(8)
        self._pipeline_lay.setContentsMargins(4, 4, 4, 4)
        self._pipeline_lay.addStretch(1)
        scroll.setWidget(container)
        pipeline_lay.addWidget(scroll, 1)

        self._tabs.addTab(pipeline_tab, self._gui.tr("Pipeline", "Pipeline"))

        # Construire les sections
        self._populate_sections()

        # Tab config plugins (si disponible)
        self._build_plugin_config_tabs()

        # Barre du bas
        bottom = QHBoxLayout()
        bottom.addStretch(1)

        btn_cancel = QPushButton(self._gui.tr("Annuler", "Cancel"))
        _apply_themed_icon(btn_cancel, "x-circle.svg")
        btn_cancel.clicked.connect(self.reject)
        bottom.addWidget(btn_cancel)

        btn_save = QPushButton(
            self._gui.tr("Enregistrer dans bcasl.yml", "Save to bcasl.yml")
        )
        _apply_themed_icon(btn_save, "save.svg")
        btn_save.setDefault(True)
        btn_save.clicked.connect(self._do_save)
        bottom.addWidget(btn_save)

        main.addLayout(bottom)

        # Initialiser l'état des onglets en fonction de l'activation
        self._on_bcasl_enabled_toggled(self._chk_bcasl_enabled.isChecked())

    def _on_bcasl_enabled_toggled(self, checked: bool) -> None:
        """Active ou désactive les onglets de configuration selon l'état global."""
        self._tabs.setEnabled(checked)
        if not checked:
            self._tabs.setToolTip(
                self._gui.tr(
                    "BCASL est désactivé dans ark.yml", "BCASL is disabled in ark.yml"
                )
            )
        else:
            self._tabs.setToolTip("")

    def _populate_sections(self) -> None:
        """Grouper les plugins par section et les insérer."""
        plugins_raw = (
            self._cfg.get("plugins", {}) if isinstance(self._cfg, dict) else {}
        )
        plugin_list = _read_plugin_list(plugins_raw)

        # Charger l'état des phases
        phases_cfg = self._cfg.get("phases", {})
        if not isinstance(phases_cfg, dict):
            phases_cfg = {}

        # Construire un mapping pid → entry
        pid_entry: dict[str, dict[str, Any]] = {}
        for entry in plugin_list:
            nm = entry.get("name", "")
            if nm:
                pid_entry[nm] = entry

        # Pour les plugins découverts non présents dans la config, créer une entrée par défaut
        for pid in self._meta_map:
            if pid not in pid_entry:
                pid_entry[pid] = {
                    "name": pid,
                    "enabled": True,
                    "priority": 0,
                    "config": {},
                }

        # Grouper par phase
        phase_groups: dict[int, list[tuple[str, dict[str, Any]]]] = {}
        for pid, entry in pid_entry.items():
            tags = self._meta_map.get(pid, {}).get("tags", [])
            score = _phase_score_for_tags(list(tags))
            phase_groups.setdefault(score, []).append((pid, entry))

        # Trier chaque groupe par priorité (ordre initial)
        for score in phase_groups:
            phase_groups[score].sort(key=lambda x: int(x[1].get("priority", 0)))

        # Créer les sections dans l'ordre des phases
        # Insérer avant le stretch final
        insert_pos = self._pipeline_lay.count() - 1

        for score in sorted(SECTION_PHASES.keys()):
            if score not in phase_groups:
                continue
            key_name, desc = SECTION_PHASES[score]
            section = _SectionWidget(score, key_name)
            section.setToolTip(desc)
            section.sig_changed.connect(self._on_any_change)

            # Appliquer l'état d'activation de la phase
            if key_name in phases_cfg:
                section.setChecked(bool(phases_cfg[key_name]))

            for pid, entry in phase_groups[score]:
                meta = self._meta_map.get(pid, {})
                display_name = meta.get("name") or pid
                ver = meta.get("version", "")
                label = f"{display_name} ({pid})" + (f" v{ver}" if ver else "")
                row = _PluginRow(
                    pid=pid,
                    name=label,
                    enabled=bool(entry.get("enabled", True)),
                    config=dict(entry.get("config", {})),
                )
                section.add_row(row)

            if not section.is_empty:
                self._pipeline_lay.insertWidget(insert_pos, section)
                insert_pos += 1
                self._sections.append(section)

    def _build_plugin_config_tabs(self) -> None:
        """Crée les onglets de configuration per-plugin."""
        try:
            from pycompiler_ark.bcasl.Base import PreCompileContext
            from pycompiler_ark.bcasl.Loader import _build_workspace_meta

            workspace_meta = _build_workspace_meta(self._workspace_root, self._cfg)
            ctx = PreCompileContext(
                self._workspace_root,
                config=self._cfg,
                workspace_metadata=workspace_meta,
            )
        except Exception:
            ctx = None

        plugins_raw = self._cfg.get("plugins", {})
        plugin_list = _read_plugin_list(plugins_raw)
        pid_entry = {e["name"]: e for e in plugin_list if e.get("name")}

        for pid, plugin in self._plugin_instances.items():
            if not hasattr(plugin, "build_config_tab"):
                continue
            try:
                entry = pid_entry.get(pid, {})
                base_cfg = dict(entry.get("config", {}))
                tab_res = plugin.build_config_tab(self._tabs, ctx, base_cfg)
                if tab_res is None:
                    continue
                title = widget = on_save = None
                if isinstance(tab_res, dict):
                    title = tab_res.get("title")
                    widget = tab_res.get("widget")
                    on_save = tab_res.get("on_save")
                elif isinstance(tab_res, (list, tuple)):
                    if len(tab_res) >= 2:
                        title, widget = tab_res[0], tab_res[1]
                        if len(tab_res) >= 3:
                            on_save = tab_res[2]
                    elif len(tab_res) == 1:
                        widget = tab_res[0]
                else:
                    widget = tab_res
                if widget is None:
                    continue
                if not title:
                    title = getattr(getattr(plugin, "meta", None), "name", None) or pid
                self._tabs.addTab(widget, str(title))
                self._plugin_ui_state[pid] = {"config": base_cfg, "on_save": on_save}
            except Exception:
                continue

    # ------------------------------------------------------------------
    # Raccourcis clavier
    # ------------------------------------------------------------------

    def _install_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+S"), self, activated=self._do_save)
        QShortcut(QKeySequence("Ctrl+Z"), self, activated=self._do_undo)
        QShortcut(QKeySequence("Ctrl+Y"), self, activated=self._do_redo)

    # ------------------------------------------------------------------
    # Expert mode
    # ------------------------------------------------------------------

    def _on_expert_toggled(self, checked: bool) -> None:
        self._expert[0] = checked
        for section in self._sections:
            section.refresh_expert()

    # ------------------------------------------------------------------
    # Undo / Redo
    # ------------------------------------------------------------------

    def _snapshot(self) -> list[dict]:
        """Prend un instantané de l'état complet du pipeline."""
        state = []
        for section in self._sections:
            state.append(
                {
                    "phase_key": section.phase_key,
                    "rows": section.snapshot(),
                }
            )
        return copy.deepcopy(state)

    def _push_undo(self) -> None:
        snap = self._snapshot()
        self._undo_stack.append(snap)
        if len(self._undo_stack) > self.MAX_UNDO:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def _do_undo(self) -> None:
        if len(self._undo_stack) <= 1:
            return
        self._redo_stack.append(self._undo_stack.pop())
        self._restore_snapshot(self._undo_stack[-1])

    def _do_redo(self) -> None:
        if not self._redo_stack:
            return
        snap = self._redo_stack.pop()
        self._undo_stack.append(snap)
        self._restore_snapshot(snap)

    def _restore_snapshot(self, state: list[dict]) -> None:
        phase_to_section = {s.phase_key: s for s in self._sections}
        for entry in state:
            section = phase_to_section.get(entry["phase_key"])
            if section:
                section.restore(entry["rows"])

    def _on_any_change(self) -> None:
        self._push_undo()

    # ------------------------------------------------------------------
    # Sauvegarde
    # ------------------------------------------------------------------

    def _collect_plugin_configs(self) -> dict[str, dict]:
        """Récupère les configs des onglets plugins."""
        result = {}
        for pid, state in self._plugin_ui_state.items():
            cfg_obj = state.get("config", {})
            on_save = state.get("on_save")
            if callable(on_save):
                try:
                    res = on_save(cfg_obj)
                    if isinstance(res, dict):
                        cfg_obj = res
                except Exception:
                    pass
            result[pid] = dict(cfg_obj) if isinstance(cfg_obj, dict) else {}
        return result

    def _do_save(self) -> None:
        plugin_configs = self._collect_plugin_configs()

        # 1) Sauvegarder l'état d'activation global dans ark.yml
        try:
            if "plugins" not in self._ark_cfg:
                self._ark_cfg["plugins"] = {}
            self._ark_cfg["plugins"][
                "bcasl_enabled"
            ] = self._chk_bcasl_enabled.isChecked()
            save_ark_config(str(self._workspace_root), self._ark_cfg)
        except Exception as e:
            QMessageBox.warning(
                self,
                self._gui.tr("Avertissement", "Warning"),
                f"Impossible de mettre à jour ark.yml: {e}",
            )

        # 2) Construire la liste ordonnée de plugins pour bcasl.yml et l'état des phases
        ordered: list[dict[str, Any]] = []
        phases_state: dict[str, bool] = {}

        # Le backend utilise rec.priority pour ordonner dans une phase.
        # On assigne un index global incrémental pour refléter l'ordre visuel.
        current_prio = 0

        for section in self._sections:
            phases_state[section._name] = section.isChecked()
            for row in section.rows:
                cfg_for_row = plugin_configs.get(row.pid, row.config or {})
                ordered.append(
                    {
                        "name": row.pid,
                        "enabled": row.is_enabled,
                        "priority": current_prio,
                        "config": cfg_for_row,
                    }
                )
                current_prio += 1

        # Construire la config de sortie pour bcasl.yml
        cfg_out: dict[str, Any] = dict(self._cfg) if isinstance(self._cfg, dict) else {}
        cfg_out["plugins"] = _plugins_list_to_yaml(ordered)
        cfg_out["phases"] = phases_state
        # plugin_order maintient la compatibilité avec l'ancien loader
        cfg_out["plugin_order"] = [e["name"] for e in ordered]

        # S'assurer que 'enabled' ne pollue plus bcasl.yml
        if "options" in cfg_out and isinstance(cfg_out["options"], dict):
            cfg_out["options"].pop("enabled", None)

        target = self._workspace_root / "bcasl.yml"
        try:
            target.write_text(
                yaml.safe_dump(cfg_out, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            try:
                if hasattr(self._gui, "log") and self._gui.log is not None:
                    self._gui.log.append(
                        self._gui.tr(
                            "✅ Pipeline BCASL enregistré dans bcasl.yml",
                            "✅ BCASL pipeline saved to bcasl.yml",
                        )
                    )
            except Exception:
                pass
            self.accept()
        except Exception as e:
            QMessageBox.critical(
                self,
                self._gui.tr("Erreur", "Error"),
                self._gui.tr(
                    f"Impossible d'écrire bcasl.yml: {e}",
                    f"Failed to write bcasl.yml: {e}",
                ),
            )


# ---------------------------------------------------------------------------
# Worker et bridge Qt (déplacés depuis bcasl/Loader.py)
# ---------------------------------------------------------------------------


class _BCASLWorker(QObject):
    finished = Signal(object)  # report or None
    log = Signal(str)

    def __init__(
        self,
        workspace_root: "Path",
        plugins_dirs: "list[Path]",
        cfg: "dict[str, Any]",
        build_context: Optional[Any] = None,
    ) -> None:
        super().__init__()
        self.workspace_root = workspace_root
        self.plugins_dirs = plugins_dirs
        self.cfg = cfg
        self.build_context = build_context
        self._cancel_requested = False

    def request_cancel(self) -> None:
        try:
            self._cancel_requested = True
        except Exception:
            pass

    @Slot()
    def run(self) -> None:
        try:
            from pycompiler_ark.bcasl.Loader import (
                BCASL_DISABLED_REPORT,
                _is_bcasl_enabled,
                _load_workspace_config,
                _run_bcasl_sync,
            )

            # 1. Vérifier si BCASL est activé (en arrière-plan)
            if not _is_bcasl_enabled(self.workspace_root):
                self.log.emit("BCASL disabled in ark.yml. Skipping execution\n")
                self.finished.emit(dict(BCASL_DISABLED_REPORT))
                return

            # 2. Charger la config si non fournie (en arrière-plan)
            if self.cfg is None:
                self.cfg = _load_workspace_config(self.workspace_root)

            # 3. Exécuter
            report = _run_bcasl_sync(
                self.workspace_root,
                self.plugins_dirs,
                self.cfg,
                log_cb=self.log.emit,
                stop_requested=lambda: self._cancel_requested,
                build_context=self.build_context,
            )

            self.finished.emit(report)
        except Exception as e:
            try:
                self.log.emit(f"Erreur BCASL: {e}\n")
            except Exception:
                pass
            self.finished.emit(None)


class _BCASLUiBridge(QObject):
    def __init__(self, gui, on_done, thread) -> None:
        super().__init__()
        self._gui = gui
        self._on_done = on_done
        self._thread = thread

    @Slot(str)
    def on_log(self, s: str) -> None:
        try:
            if hasattr(self._gui, "log") and self._gui.log:
                self._gui.log.append(s)
        except Exception:
            pass

    @Slot(object)
    def on_finished(self, rep) -> None:
        try:
            try:
                from pycompiler_ark.bcasl.Loader import is_bcasl_disabled_report
            except Exception:
                is_bcasl_disabled_report = lambda _r: False  # type: ignore[assignment,misc]

            if (
                rep
                and not is_bcasl_disabled_report(rep)
                and hasattr(self._gui, "log")
                and self._gui.log is not None
            ):
                self._gui.log.append("BCASL - Rapport:\n")
                for item in rep:
                    try:
                        state = (
                            "OK"
                            if getattr(item, "success", False)
                            else f"FAIL: {getattr(item, 'error', '')}"
                        )
                        dur = getattr(item, "duration_ms", 0.0)
                        pid = getattr(item, "plugin_id", "?")
                        self._gui.log.append(f" - {pid}: {state} ({dur:.1f} ms)\n")
                    except Exception:
                        pass
                try:
                    self._gui.log.append(rep.summary() + "\n")
                except Exception:
                    pass
            try:
                if callable(self._on_done):
                    self._on_done(rep)
            except Exception:
                pass
        finally:
            try:
                self._thread.quit()
            except Exception:
                pass


def _build_plugin_item(
    pid: str,
    meta: "dict[str, Any]",
    plugins_cfg: "dict[str, Any]",
    Qt,
    QListWidgetItem,
) -> Any:
    """Construit un QListWidgetItem pour un plugin BCASL."""
    from pycompiler_ark.bcasl.tagging import get_tag_phase_name

    label = meta.get("name") or pid
    ver = meta.get("version") or ""
    tags = meta.get("tags") or []

    phase_name = get_tag_phase_name(tags[0]) if tags else ""
    text = f"{label} ({pid})" + (f" v{ver}" if ver else "")
    if phase_name:
        text += f" [Phase: {phase_name}]"

    item = QListWidgetItem(text)

    try:
        desc = meta.get("description") or ""
        tooltip = desc
        if tags:
            tooltip += f"\n\nTags: {', '.join(tags)}"
        reqs = meta.get("requirements", [])
        if reqs:
            tooltip += "\n\nRequirements:\n" + "\n".join(f"  • {req}" for req in reqs)
        if tooltip:
            item.setToolTip(tooltip)
    except Exception:
        pass

    from pycompiler_ark.bcasl.Loader import _plugin_enabled

    enabled = _plugin_enabled(plugins_cfg, pid)
    try:
        item.setData(0x0100, pid)
    except Exception:
        pass
    if Qt is not None:
        item.setFlags(
            item.flags()
            | Qt.ItemIsUserCheckable
            | Qt.ItemIsEnabled
            | Qt.ItemIsSelectable
            | Qt.ItemIsDragEnabled
        )
        item.setCheckState(
            Qt.CheckState.Checked if enabled else Qt.CheckState.Unchecked
        )
    return item


# ---------------------------------------------------------------------------
# Point d'entrée (appelé par la GUI)
# ---------------------------------------------------------------------------


def ensure_bcasl_thread_stopped(self, timeout_ms: int = 5000) -> None:
    """Arrête proprement un thread BCASL en cours (si présent)."""
    try:
        # Request cooperative cancellation first, then hard-kill any sandbox workers.
        try:
            w = getattr(self, "_bcasl_worker", None)
            if w is not None and hasattr(w, "request_cancel"):
                w.request_cancel()
        except Exception:
            pass
        try:
            from pycompiler_ark.bcasl.executor import kill_active_workers

            kill_active_workers()
        except Exception:
            pass
        t = getattr(self, "_bcasl_thread", None)
        if t is not None:
            try:
                if t.isRunning():
                    try:
                        t.quit()
                    except Exception:
                        pass
                    if not t.wait(timeout_ms):
                        try:
                            t.terminate()
                        except Exception:
                            pass
                        try:
                            t.wait(1000)
                        except Exception:
                            pass
                    try:
                        from pycompiler_ark.bcasl.executor import kill_active_workers

                        kill_active_workers()
                    except Exception:
                        pass
            except Exception:
                pass
        # Nettoyage
        try:
            self._bcasl_thread = None
            self._bcasl_worker = None
            if hasattr(self, "_bcasl_ui_bridge"):
                self._bcasl_ui_bridge = None
        except Exception:
            pass
    except Exception:
        pass


def open_bc_loader_dialog(self) -> None:
    """Ouvre l'éditeur visuel du pipeline BCASL.

    Persiste dans <workspace>/bcasl.yml (format liste YAML).
    """
    try:
        from PySide6.QtWidgets import QMessageBox
    except Exception:  # pragma: no cover
        return

    try:
        if not getattr(self, "workspace_dir", None):
            QMessageBox.warning(
                self,
                self.tr("Attention", "Warning"),
                self.tr(
                    "Veuillez d'abord sélectionner un dossier workspace.",
                    "Please select a workspace folder first.",
                ),
            )
            return

        workspace_root = Path(self.workspace_dir).resolve()

        from pycompiler_ark.bcasl.Loader import (
            _discover_bcasl_meta,
            _discover_bcasl_plugins,
            _get_all_plugins_dirs,
            _load_workspace_config,
        )

        plugins_dirs = _get_all_plugins_dirs()

        meta_map = {}
        for pdir in plugins_dirs:
            if pdir.exists() and pdir.is_dir():
                meta_map.update(_discover_bcasl_meta(pdir))

        if not meta_map:
            QMessageBox.information(
                self,
                self.tr("Information", "Information"),
                self.tr(
                    "Aucun plugin détecté dans les répertoires configurés.",
                    "No plugins detected in configured directories.",
                ),
            )
            return

        cfg = _load_workspace_config(workspace_root)

        plugin_instances = {}
        for pdir in plugins_dirs:
            if pdir.exists() and pdir.is_dir():
                plugin_instances.update(
                    _discover_bcasl_plugins(pdir, workspace_root, cfg)
                )

        open_bcasl_pipeline_dialog(
            self, workspace_root, meta_map, cfg, plugin_instances
        )

    except Exception as e:
        try:
            if hasattr(self, "log") and self.log is not None:
                self.log.append(f"BCASL Pipeline UI error: {e}")
        except Exception:
            pass


def run_pre_compile_async(
    self, on_done: Optional[callable] = None, build_context: Optional[Any] = None
) -> None:
    """Lance BCASL en arrière-plan via QThread.
    on_done(report) appelé à la fin si fourni.
    """
    try:
        if not getattr(self, "workspace_dir", None):
            if callable(on_done):
                try:
                    on_done(None)
                except Exception:
                    pass
            return
        workspace_root = Path(self.workspace_dir).resolve()

        from pycompiler_ark.bcasl.Loader import (
            BCASL_DISABLED_REPORT,
            _get_all_plugins_dirs,
            _is_bcasl_enabled,
        )

        # Étape 0: Vérifier si BCASL est activé globalement via ark.yml
        if not _is_bcasl_enabled(workspace_root):
            try:
                if hasattr(self, "log") and self.log is not None:
                    self.log.append("BCASL désactivé dans ark.yml. Exécution ignorée\n")
            except Exception:
                pass
            if callable(on_done):
                try:
                    on_done(dict(BCASL_DISABLED_REPORT))
                except Exception:
                    pass
            return

        plugins_dirs = _get_all_plugins_dirs()

        thread = QThread()
        # On passe cfg=None pour que le worker le charge en arrière-plan
        worker = _BCASLWorker(
            workspace_root,
            plugins_dirs,
            cfg=None,
            build_context=build_context,
        )
        try:
            self._bcasl_thread = thread
            self._bcasl_worker = worker
        except Exception:
            pass
        bridge = _BCASLUiBridge(self, on_done, thread)
        try:
            self._bcasl_ui_bridge = bridge
        except Exception:
            pass
        if hasattr(self, "log") and self.log is not None:
            worker.log.connect(bridge.on_log)
        worker.finished.connect(bridge.on_finished)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        thread.start()

    except Exception as e:
        try:
            if callable(on_done):
                on_done(None)
        except Exception:
            pass
        try:
            if hasattr(self, "log") and self.log is not None:
                self.log.append(f"Erreur BCASL (async): {e}\n")
        except Exception:
            pass


def open_bcasl_pipeline_dialog(
    gui,
    workspace_root: Path,
    meta_map: "dict[str, dict[str, Any]]",
    cfg: "dict[str, Any]",
    plugin_instances: "dict[str, Any]",
) -> None:
    """Ouvre le dialog BCASL Pipeline."""
    dlg = BcaslPipelineDialog(gui, workspace_root, meta_map, cfg, plugin_instances)
    try:
        dlg.setModal(False)
        dlg.show()
    except Exception:
        try:
            dlg.exec()
        except Exception:
            pass
