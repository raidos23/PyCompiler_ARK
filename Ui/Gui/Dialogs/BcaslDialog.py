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

from PySide6.QtCore import Qt, Signal, QMimeData, QByteArray
from PySide6.QtGui import QColor, QShortcut, QKeySequence, QPalette
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

# phase_score → (display_name, min_priority, max_priority)
SECTION_PHASES: dict[int, tuple[str, int, int]] = {
    0:   ("Nettoyage",    0,   9),
    10:  ("Validation",   10,  19),
    20:  ("Préparation",  20,  29),
    30:  ("Conformité",   30,  39),
    40:  ("Linting",      40,  49),
    50:  ("Obfuscation",  50,  59),
    100: ("Défaut",       60,  199),
}

_WARN_BG   = "#FFF3CD"   # fond jaune pâle
_WARN_BORDER = "orange"  # bordure spinbox hors-plage
_SECTION_BG  = "#F5F5F5" # fond section (clair)

# Tag → score de phase
_TAG_PRIORITY_MAP: dict[str, int] = {}
try:
    from bcasl.tagging import TAG_PRIORITY_MAP as _TAG_PRIORITY_MAP  # type: ignore
except Exception:
    pass


def _phase_score_for_tags(tags: list[str]) -> int:
    """Retourne le score de phase minimum pour une liste de tags."""
    scores = [_TAG_PRIORITY_MAP.get(str(t).strip().lower(), 100) for t in (tags or [])]
    return min(scores) if scores else 100


def _section_for_phase(score: int) -> tuple[int, str, int, int]:
    """Retourne (key, name, min_prio, max_prio) pour un score de phase."""
    # Trouver la section dont le score correspond
    for key in sorted(SECTION_PHASES):
        if score == key:
            name, lo, hi = SECTION_PHASES[key]
            return key, name, lo, hi
    # Section par défaut
    name, lo, hi = SECTION_PHASES[100]
    return 100, name, lo, hi


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
                result.append({"name": name, "enabled": val, "priority": 0, "config": {}})
            elif isinstance(val, dict):
                result.append({
                    "name": name,
                    "enabled": bool(val.get("enabled", True)),
                    "priority": int(val.get("priority", 0)),
                    "config": dict(val.get("config", {})),
                })
        return result
    return []


def _plugins_list_to_yaml(plugin_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Retourne la liste dans le format bcasl.yml officiel."""
    result = []
    for row in plugin_rows:
        result.append({
            "name": row["name"],
            "enabled": bool(row.get("enabled", True)),
            "priority": int(row.get("priority", 0)),
            "config": dict(row.get("config", {})),
        })
    return result


# ---------------------------------------------------------------------------
# Widget : ligne de plugin
# ---------------------------------------------------------------------------

class _PluginRow(QFrame):
    """Widget représentant un seul plugin dans le pipeline."""

    sig_move_up   = Signal(str)   # plugin_id
    sig_move_down  = Signal(str)
    sig_enabled    = Signal(str, bool)
    sig_priority   = Signal(str, int)

    def __init__(
        self,
        pid: str,
        name: str,
        priority: int,
        enabled: bool,
        min_prio: int,
        max_prio: int,
        expert_ref: "list[bool]",
        config: Optional[dict] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.pid = pid
        self._min = min_prio
        self._max = max_prio
        self._expert_ref = expert_ref   # [bool] mutable reference
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

        # Icône warning
        self.lbl_warn = QLabel("⚠️")
        self.lbl_warn.setFixedWidth(24)
        self.lbl_warn.setVisible(False)
        row.addWidget(self.lbl_warn)

        # Nom plugin
        self.lbl_name = QLabel(name or pid)
        self.lbl_name.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        row.addWidget(self.lbl_name)

        # Label "priority"
        row.addWidget(QLabel("priority"))

        # Spinbox priorité
        self.spin = QSpinBox()
        self.spin.setRange(0, 999)
        self.spin.setValue(priority)
        self.spin.setFixedWidth(70)
        self.spin.valueChanged.connect(self._on_priority_changed)
        row.addWidget(self.spin)

        # Boutons ↑ ↓
        self.btn_up = QPushButton("↑")
        self.btn_up.setFixedWidth(28)
        self.btn_up.setToolTip("Monter dans la section")
        self.btn_up.clicked.connect(lambda: self.sig_move_up.emit(self.pid))
        row.addWidget(self.btn_up)

        self.btn_down = QPushButton("↓")
        self.btn_down.setFixedWidth(28)
        self.btn_down.setToolTip("Descendre dans la section")
        self.btn_down.clicked.connect(lambda: self.sig_move_down.emit(self.pid))
        row.addWidget(self.btn_down)

        self._refresh_warning()

    # ------------------------------------------------------------------

    def _on_priority_changed(self, val: int) -> None:
        self._refresh_warning()
        self.sig_priority.emit(self.pid, val)

    def _refresh_warning(self) -> None:
        """Met à jour l'indicateur ⚠️ et les styles selon expert mode et valeur."""
        expert = bool(self._expert_ref[0]) if self._expert_ref else False
        val = self.spin.value()
        out_of_range = not (self._min <= val <= self._max)

        if expert or not out_of_range:
            self.lbl_warn.setVisible(False)
            self.setStyleSheet("")
            self.spin.setStyleSheet("")
        else:
            self.lbl_warn.setVisible(True)
            self.lbl_warn.setToolTip(
                f"⚠️ Priorité {val} hors de la plage recommandée ({self._min}-{self._max}).\n"
                "L'ordre d'exécution peut être inattendu.\n"
                "Utilisez le mode Expert pour désactiver les avertissements."
            )
            self.setStyleSheet(f"QFrame#PluginRow {{ background: {_WARN_BG}; }}")
            self.spin.setStyleSheet(f"QSpinBox {{ border: 2px solid {_WARN_BORDER}; }}")

    def refresh_expert(self) -> None:
        """Appelé quand expert mode change."""
        expert = bool(self._expert_ref[0]) if self._expert_ref else False
        if expert:
            self.spin.setRange(0, 999)
        else:
            self.spin.setRange(0, 999)  # toujours libre en saisie, warning géré visuellement
        self._refresh_warning()

    # ------------------------------------------------------------------
    # Accesseurs

    @property
    def is_enabled(self) -> bool:
        return self.chk.isChecked()

    @property
    def priority_value(self) -> int:
        return self.spin.value()

    def snapshot(self) -> dict[str, Any]:
        return {"pid": self.pid, "enabled": self.is_enabled, "priority": self.priority_value}

    def restore(self, snap: dict[str, Any]) -> None:
        self.chk.setChecked(bool(snap.get("enabled", True)))
        self.spin.setValue(int(snap.get("priority", 0)))


# ---------------------------------------------------------------------------
# Widget : section collapsible
# ---------------------------------------------------------------------------

class _SectionWidget(QFrame):
    """Section collapsible représentant une catégorie de plugins."""

    sig_changed = Signal()

    def __init__(
        self,
        phase_key: int,
        name: str,
        min_prio: int,
        max_prio: int,
        expert_ref: "list[bool]",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.phase_key = phase_key
        self._name = name
        self._min = min_prio
        self._max = max_prio
        self._expert_ref = expert_ref
        self._rows: list[_PluginRow] = []
        self._collapsed = False

        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet(f"QFrame {{ background: {_SECTION_BG}; border-radius: 4px; }}")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(4, 4, 4, 4)
        outer.setSpacing(2)

        # En-tête
        header = QFrame()
        header_lay = QHBoxLayout(header)
        header_lay.setContentsMargins(4, 2, 4, 2)

        self._toggle_btn = QPushButton("▼")
        self._toggle_btn.setFlat(True)
        self._toggle_btn.setFixedWidth(24)
        self._toggle_btn.clicked.connect(self._toggle_collapse)
        header_lay.addWidget(self._toggle_btn)

        self._title = QLabel(f"<b>{name}</b>  <small style='color:#888'>({min_prio}–{max_prio})</small>")
        self._title.setTextFormat(Qt.RichText)
        header_lay.addWidget(self._title)
        header_lay.addStretch(1)
        outer.addWidget(header)

        # Zone de contenu (plugins)
        self._content = QWidget()
        self._content_lay = QVBoxLayout(self._content)
        self._content_lay.setContentsMargins(8, 2, 4, 4)
        self._content_lay.setSpacing(3)
        outer.addWidget(self._content)

    # ------------------------------------------------------------------

    def _toggle_collapse(self) -> None:
        self._collapsed = not self._collapsed
        self._content.setVisible(not self._collapsed)
        self._toggle_btn.setText("▶" if self._collapsed else "▼")

    def add_row(self, row: _PluginRow) -> None:
        self._rows.append(row)
        self._content_lay.addWidget(row)
        row.sig_move_up.connect(self._on_move_up)
        row.sig_move_down.connect(self._on_move_down)
        row.sig_enabled.connect(lambda _pid, _v: self.sig_changed.emit())
        row.sig_priority.connect(lambda _pid, _v: self.sig_changed.emit())

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

        # Expert mode : liste mutable partagée avec les rows
        self._expert: list[bool] = [False]

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
        lbl = QLabel(f"<b>BCASL Pipeline</b>")
        lbl.setTextFormat(Qt.RichText)
        title_row.addWidget(lbl)
        title_row.addStretch(1)
        btn_save_top = QPushButton(self._gui.tr("Enregistrer", "Save"))
        btn_save_top.clicked.connect(self._do_save)
        title_row.addWidget(btn_save_top)
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
        container = QWidget()
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
        self._chk_expert = QCheckBox(self._gui.tr("Mode Expert (priorités libres)", "Expert mode (any priority)"))
        self._chk_expert.setChecked(False)
        self._chk_expert.toggled.connect(self._on_expert_toggled)
        bottom.addWidget(self._chk_expert)
        bottom.addStretch(1)

        btn_cancel = QPushButton(self._gui.tr("Annuler", "Cancel"))
        btn_cancel.clicked.connect(self.reject)
        bottom.addWidget(btn_cancel)

        btn_save = QPushButton(self._gui.tr("Enregistrer dans bcasl.yml", "Save to bcasl.yml"))
        btn_save.setDefault(True)
        btn_save.clicked.connect(self._do_save)
        bottom.addWidget(btn_save)

        main.addLayout(bottom)

    def _populate_sections(self) -> None:
        """Grouper les plugins par section et les insérer."""
        plugins_raw = self._cfg.get("plugins", {}) if isinstance(self._cfg, dict) else {}
        plugin_list = _read_plugin_list(plugins_raw)

        # Construire un mapping pid → entry
        pid_entry: dict[str, dict[str, Any]] = {}
        for entry in plugin_list:
            nm = entry.get("name", "")
            if nm:
                pid_entry[nm] = entry

        # Pour les plugins découverts non présents dans la config, créer une entrée par défaut
        for pid in self._meta_map:
            if pid not in pid_entry:
                pid_entry[pid] = {"name": pid, "enabled": True, "priority": 0, "config": {}}

        # Grouper par phase
        phase_groups: dict[int, list[tuple[str, dict[str, Any]]]] = {}
        for pid, entry in pid_entry.items():
            tags = self._meta_map.get(pid, {}).get("tags", [])
            score = _phase_score_for_tags(list(tags))
            phase_groups.setdefault(score, []).append((pid, entry))

        # Trier chaque groupe par priorité
        for score in phase_groups:
            phase_groups[score].sort(key=lambda x: int(x[1].get("priority", 0)))

        # Créer les sections dans l'ordre des phases
        # Insérer avant le stretch final
        insert_pos = self._pipeline_lay.count() - 1

        for score in sorted(SECTION_PHASES.keys()):
            if score not in phase_groups:
                continue
            key_name, lo, hi = SECTION_PHASES[score]
            section = _SectionWidget(score, key_name, lo, hi, self._expert)
            section.sig_changed.connect(self._on_any_change)

            for pid, entry in phase_groups[score]:
                meta = self._meta_map.get(pid, {})
                display_name = meta.get("name") or pid
                ver = meta.get("version", "")
                label = f"{display_name} ({pid})" + (f" v{ver}" if ver else "")
                row = _PluginRow(
                    pid=pid,
                    name=label,
                    priority=int(entry.get("priority", 0)),
                    enabled=bool(entry.get("enabled", True)),
                    min_prio=lo,
                    max_prio=hi,
                    expert_ref=self._expert,
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
            from bcasl.Base import PreCompileContext
            from bcasl.Loader import _build_workspace_meta

            workspace_meta = _build_workspace_meta(self._workspace_root, self._cfg)
            ctx = PreCompileContext(
                self._workspace_root, config=self._cfg, workspace_metadata=workspace_meta
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
            state.append({
                "phase_key": section.phase_key,
                "rows": section.snapshot(),
            })
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

        # Construire la liste ordonnée de plugins
        ordered: list[dict[str, Any]] = []
        for section in self._sections:
            for row in section.rows:
                cfg_for_row = plugin_configs.get(row.pid, row.config or {})
                ordered.append({
                    "name": row.pid,
                    "enabled": row.is_enabled,
                    "priority": row.priority_value,
                    "config": cfg_for_row,
                })

        # Construire la config de sortie
        cfg_out: dict[str, Any] = dict(self._cfg) if isinstance(self._cfg, dict) else {}
        cfg_out["plugins"] = _plugins_list_to_yaml(ordered)
        # plugin_order maintient la compatibilité avec l'ancien loader
        cfg_out["plugin_order"] = [e["name"] for e in ordered]

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
# Point d'entrée (appelé depuis bcasl/Loader.py)
# ---------------------------------------------------------------------------

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
