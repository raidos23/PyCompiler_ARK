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
BCASL loader (simplifié)

Objectifs de simplification:
- Config YML uniquement (bcasl.yml ou .bcasl.yml) - YML ONLY, NO YAML, NO JSON
- Détection de plugins minimale: packages dans Plugins/ ayant __init__.py
- Ordre: plugin_order depuis config sinon basé sur tags simples, sinon alphabétique
- UI minimale pour activer/désactiver et réordonner (pas d'éditeur brut multi-format)
- Async via QThread si QtCore dispo, sinon repli synchrone
- Journalisation concise dans self.log si disponible
- Activation/désactivation gérée par ark.yml (plugins.bcasl_enabled)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

import yaml

from Core.Configs import load_ark_config

from .Base import BcPluginBase, PreCompileContext
from .executor import BCASL
from .tagging import compute_tag_order

# Qt (facultatif). Ne pas importer QtWidgets au niveau module pour compatibilité headless.
try:  # pragma: no cover
    from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot
except Exception:  # pragma: no cover
    QObject = None  # type: ignore
    QThread = None  # type: ignore
    Signal = None  # type: ignore
    Slot = None  # type: ignore
    Qt = None  # type: ignore

# --- Utilitaires ---


def _has_bcasl_marker(pkg_dir: Path) -> bool:
    try:
        return (pkg_dir / "__init__.py").exists()
    except Exception:
        return False


def _discover_bcasl_meta(Plugins_dir: Path) -> dict[str, dict[str, Any]]:
    """Décopen les plugins en important chaque package et en appelant bcasl_register(manager).
    Supporte également les plugins enregistrés avec le décorateur @bc_register.
    Return un mapping plugin_id -> meta dict {id, name, version, description, author, requirements}
    """
    meta: dict[str, dict[str, Any]] = {}
    try:
        import importlib.util as _ilu
        import sys as _sys

        for pkg_dir in sorted(Plugins_dir.iterdir(), key=lambda p: p.name):
            try:
                if not pkg_dir.is_dir():
                    continue
                init_py = pkg_dir / "__init__.py"
                if not init_py.exists():
                    continue
                mod_name = f"bcasl_meta_{pkg_dir.name}"
                spec = _ilu.spec_from_file_location(
                    mod_name, str(init_py), submodule_search_locations=[str(pkg_dir)]
                )
                if spec is None or spec.loader is None:
                    continue
                module = _ilu.module_from_spec(spec)
                _sys.modules[mod_name] = module
                spec.loader.exec_module(module)  # type: ignore[attr-defined]

                # Utilise un gestionnaire temporaire pour enregistrer et lire les métadonnées
                mgr = BCASL(Plugins_dir, config={}, sandbox=False, plugin_timeout_s=0.0)  # type: ignore[call-arg]

                # Méthode 1: chercher fonction bcasl_register
                reg = getattr(module, "bcasl_register", None)
                if callable(reg):
                    reg(mgr)
                else:
                    # Méthode 2: chercher classes marquées avec @bc_register
                    for attr_name in dir(module):
                        try:
                            attr = getattr(module, attr_name, None)
                            if attr is None:
                                continue
                            if not getattr(attr, "__bcasl_plugin__", False):
                                continue
                            if not isinstance(attr, type):
                                continue
                            # C'est une classe de plugin décorée avec @bc_register
                            plugin_instance = getattr(attr, "_bcasl_instance_", None)
                            if plugin_instance is None:
                                try:
                                    plugin_instance = attr()
                                except Exception:
                                    continue
                            # Enregistrer temporairement pour récupérer les métadonnées
                            pid = plugin_instance.meta.id
                            if pid not in mgr._registry:
                                mgr.add_plugin(plugin_instance)
                        except Exception:
                            continue

                # Récupère les plugins enregistrés
                for pid, rec in getattr(mgr, "_registry", {}).items():
                    try:
                        plg = rec.plugin
                        # Récupérer les tags depuis PluginMeta (normalisés)
                        tags: list[str] = []
                        try:
                            meta_tags = getattr(plg.meta, "tags", ())
                            if isinstance(meta_tags, (list, tuple)):
                                tags = [
                                    str(x).strip().lower()
                                    for x in meta_tags
                                    if str(x).strip()
                                ]
                        except Exception:
                            tags = []

                        # Récupérer les requirements
                        reqs: list[str] = []
                        try:
                            if plg.meta.required_bcasl_version != "1.0.0":
                                reqs.append(
                                    f"BCASL >= {plg.meta.required_bcasl_version}"
                                )
                            if plg.meta.required_core_version != "1.0.0":
                                reqs.append(f"Core >= {plg.meta.required_core_version}")
                            if plg.meta.required_plugins_sdk_version != "1.0.0":
                                reqs.append(
                                    f"Plugins SDK >= {plg.meta.required_plugins_sdk_version}"
                                )
                            if plg.meta.required_bc_plugin_context_version != "1.0.0":
                                reqs.append(
                                    f"BcPluginContext >= {plg.meta.required_bc_plugin_context_version}"
                                )
                            if plg.meta.required_general_context_version != "1.0.0":
                                reqs.append(
                                    f"GeneralContext >= {plg.meta.required_general_context_version}"
                                )
                        except Exception:
                            pass

                        m = {
                            "id": plg.meta.id,
                            "name": plg.meta.name,
                            "version": plg.meta.version,
                            "description": plg.meta.description,
                            "author": plg.meta.author,
                            "tags": tags,
                            "requirements": reqs,
                        }
                        meta[plg.meta.id] = m
                    except Exception:
                        continue
            except Exception:
                continue
    except Exception:
        pass
    return meta


def _discover_bcasl_plugins(
    Plugins_dir: Path, workspace_root: Path, cfg: dict[str, Any]
) -> dict[str, BcPluginBase]:
    """Load les plugins et return un mapping plugin_id -> instance."""
    plugins: dict[str, BcPluginBase] = {}
    try:
        mgr = BCASL(workspace_root, config=cfg, sandbox=False, plugin_timeout_s=0.0)
        mgr.load_plugins_from_directory(Plugins_dir)
        for pid, rec in getattr(mgr, "_registry", {}).items():
            try:
                plugins[str(pid)] = rec.plugin
            except Exception:
                continue
    except Exception:
        pass
    return plugins


# apply_translations removed: i18n is now handled at the SDK level to stay
# independent from BCASL and support future plugin systems.


# --- Chargement config (YML uniquement) ---


def _emit_log(log_cb: Optional[callable], message: str) -> None:
    """Émet un message via un callback de log si disponible."""
    try:
        if callable(log_cb):
            log_cb(message)
    except Exception:
        pass


def _resolve_plugin_timeout(cfg: dict[str, Any]) -> float:
    """Résout le timeout effectif (config > env), <= 0 => illimité."""
    try:
        env_timeout = float(os.environ.get("PYCOMPILER_BCASL_PLUGIN_TIMEOUT", "0"))
    except Exception:
        env_timeout = 0.0
    try:
        opt = cfg.get("options", {}) if isinstance(cfg, dict) else {}
        cfg_timeout = (
            float(opt.get("plugin_timeout_s", 0.0)) if isinstance(opt, dict) else 0.0
        )
    except Exception:
        cfg_timeout = 0.0
    plugin_timeout = cfg_timeout if cfg_timeout != 0.0 else env_timeout
    return float(plugin_timeout) if plugin_timeout and plugin_timeout > 0 else 0.0


def _is_bcasl_enabled(workspace_root: Path) -> bool:
    """Consulte ark.yml pour savoir si le BCASL est activé globalement."""
    try:
        ark_cfg = load_ark_config(workspace_root)
        return bool(ark_cfg.get("plugins", {}).get("bcasl_enabled", True))
    except Exception:
        return True


def _build_workspace_meta(workspace_root: Path, cfg: dict[str, Any]) -> dict[str, Any]:
    """Build les métadonnées du workspace pour BCASL."""
    return {
        "workspace_name": workspace_root.name,
        "workspace_path": str(workspace_root),
        "file_patterns": cfg.get("file_patterns", []),
        "exclude_patterns": cfg.get("exclude_patterns", []),
    }


def _resolve_order_list(cfg: dict[str, Any], plugins_dir: Path) -> list[str]:
    """Résout l'ordre des plugins (config > tags)."""
    order_list: list[str] = []
    try:
        order_list = list(cfg.get("plugin_order", [])) if isinstance(cfg, dict) else []
    except Exception:
        order_list = []
    if not order_list:
        try:
            meta_en = _discover_bcasl_meta(plugins_dir)
            order_list = list(compute_tag_order(meta_en))
        except Exception:
            order_list = []
    return order_list


def _apply_plugins_config(
    manager: BCASL,
    cfg: dict[str, Any],
    plugins_dir: Path,
    log_cb: Optional[callable] = None,
) -> list[str]:
    """Applique l'activation et les priorités, return l'ordre utilisé."""
    pmap = cfg.get("plugins", {}) if isinstance(cfg, dict) else {}
    if isinstance(pmap, dict):
        for pid, val in pmap.items():
            try:
                enabled = (
                    val
                    if isinstance(val, bool)
                    else bool((val or {}).get("enabled", True))
                )
                if not enabled:
                    manager.disable_plugin(pid)
            except Exception:
                pass
            try:
                if isinstance(val, dict) and "priority" in val:
                    manager.set_priority(pid, int(val.get("priority", 0)))
            except Exception:
                pass

    order_list = _resolve_order_list(cfg, plugins_dir)
    if order_list:
        for idx, pid in enumerate(order_list):
            _emit_log(log_cb, f"⏫ Priorité {idx} pour {pid}\n")
            try:
                manager.set_priority(pid, int(idx))
            except Exception:
                pass
    return order_list


def _run_bcasl_sync(
    workspace_root: Path,
    plugins_dir: Path,
    cfg: dict[str, Any],
    plugin_timeout: float,
    log_cb: Optional[callable] = None,
    stop_requested: Optional[callable] = None,
):
    """Execute BCASL en mode synchrone et return le rapport."""
    manager = BCASL(workspace_root, config=cfg, plugin_timeout_s=plugin_timeout)
    loaded, errors = manager.load_plugins_from_directory(plugins_dir)
    _emit_log(log_cb, f"BCASL: {loaded} package(s) chargé(s) depuis Plugins/\n")
    for mod, msg in errors or []:
        _emit_log(log_cb, f"Plugin '{mod}': {msg}\n")

    _apply_plugins_config(manager, cfg, plugins_dir, log_cb=log_cb)

    workspace_meta = _build_workspace_meta(workspace_root, cfg)
    return manager.run_pre_compile(
        PreCompileContext(
            workspace_root, config=cfg, workspace_metadata=workspace_meta
        ),
        stop_requested=stop_requested,
    )


def _get_plugins_dir() -> Path:
    try:
        return Path(__file__).resolve().parents[1] / "Plugins"
    except Exception:
        return Path("Plugins")


def _resolve_ordered_plugin_ids(
    plugin_ids: list[str], meta_map: dict[str, dict[str, Any]], cfg: dict[str, Any]
) -> list[str]:
    order: list[str] = []
    try:
        order = cfg.get("plugin_order", []) if isinstance(cfg, dict) else []
        order = [pid for pid in order if pid in plugin_ids]
    except Exception:
        order = []
    if not order:
        try:
            order = [pid for pid in compute_tag_order(meta_map) if pid in plugin_ids]
        except Exception:
            order = sorted(plugin_ids)
    remaining = [pid for pid in plugin_ids if pid not in order]
    return order + remaining


def _plugin_enabled(plugins_cfg: dict[str, Any], pid: str) -> bool:
    try:
        pentry = plugins_cfg.get(pid, {})
        if isinstance(pentry, dict):
            return bool(pentry.get("enabled", True))
        if isinstance(pentry, bool):
            return bool(pentry)
    except Exception:
        pass
    return True


def _load_workspace_config(workspace_root: Path) -> dict[str, Any]:
    """Load bcasl.yml si présent, sinon génère une config par défaut minimale et l'écrit.

    Fusionne aussi avec ark.yml si disponible pour les patterns et options plugins.
    YML ONLY - YAML and JSON files are NOT supported.
    """

    def _read_yml(p: Path) -> dict[str, Any]:
        try:
            return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        except Exception:
            return {}

    # 1) Fichiers candidats (YML uniquement - NO YAML, NO JSON)
    # Priorité: bcasl.yml > .bcasl.yml
    for name in ("bcasl.yml", ".bcasl.yml"):
        p = workspace_root / name
        if p.exists() and p.is_file():
            data = _read_yml(p)

            if isinstance(data, dict) and data:
                return data

    # 2) Génération défaut avec fusion ARK
    default_cfg: dict[str, Any] = {}
    try:
        Plugins_dir = _get_plugins_dir()
        detected_plugins: dict[str, Any] = {}
        meta_map = _discover_bcasl_meta(Plugins_dir) if Plugins_dir.exists() else {}
        if meta_map:
            order = compute_tag_order(meta_map)
            for idx, pid in enumerate(order):
                detected_plugins[pid] = {"enabled": True, "priority": idx}
            plugin_order = order
        else:
            # Fallback alphabétique par dossier
            try:
                names = [
                    p.name
                    for p in sorted(Plugins_dir.iterdir())
                    if (p.is_dir() and _has_bcasl_marker(p))
                ]
            except Exception:
                names = []
            for idx, pid in enumerate(sorted(names)):
                detected_plugins[pid] = {"enabled": True, "priority": idx}
            plugin_order = sorted(names)

        # Charger ARK config pour les patterns par défaut
        file_patterns = ["**/*.py"]
        exclude_patterns = [
            "**/__pycache__/**",
            "**/*.pyc",
            ".git/**",
            "venv/**",
            ".venv/**",
        ]
        plugin_timeout = 0.0

        try:
            from Core.Configs import load_ark_config

            ark_config = load_ark_config(str(workspace_root))

            # exclusion_patterns est désormais dans workspace: exclude
            workspace_cfg = ark_config.get("workspace", {})
            if isinstance(workspace_cfg, dict):
                exclude_patterns = workspace_cfg.get("exclude", exclude_patterns)

            # inclusion_patterns n'est plus supporté (l'exclusion suffit)

            plugin_opts = ark_config.get("plugins", {})
            if "plugin_timeout" in plugin_opts:
                plugin_timeout = float(plugin_opts["plugin_timeout"])
        except Exception:
            pass

        # Phases par défaut (toutes activées)
        default_phases = {
            "Nettoyage": True,
            "Validation": True,
            "Préparation": True,
            "Conformité": True,
            "Linting": True,
            "Obfuscation": True,
            "Défaut": True,
        }

        default_cfg = {
            "file_patterns": file_patterns,
            "exclude_patterns": exclude_patterns,
            "options": {
                "plugin_timeout_s": plugin_timeout,
                "sandbox": True,
                "plugin_parallelism": 0,
                "iter_files_cache": True,
            },
            "phases": default_phases,
            "plugins": detected_plugins,
            "plugin_order": plugin_order,
        }
        # Ecriture best-effort en YML uniquement
        try:
            target = workspace_root / "bcasl.yml"
            target.write_text(
                yaml.safe_dump(default_cfg, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
        except Exception:
            pass
    except Exception:
        pass
    return default_cfg


# --- Plugins publique attendue par le reste de l'app ---


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
            from .executor import kill_active_workers

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
                        from .executor import kill_active_workers

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


def resolve_bcasl_timeout(self) -> float:
    """Résout le timeout effectif des plugins à partir de la config et de l'env.
    <= 0 => illimité (0.0 renvoyé)
    """
    try:
        if not getattr(self, "workspace_dir", None):
            return 0.0
        workspace_root = Path(self.workspace_dir).resolve()
        cfg = _load_workspace_config(workspace_root)
        return _resolve_plugin_timeout(cfg)
    except Exception:
        return 0.0


def open_bc_loader_dialog(self) -> None:
    """Ouvre l'éditeur visuel du pipeline BCASL.

    Délègue à Ui/Gui/Dialogs/BcaslDialog.BcaslPipelineDialog.
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
        Plugins_dir = _get_plugins_dir()

        if not Plugins_dir.exists():
            QMessageBox.information(
                self,
                self.tr("Information", "Information"),
                self.tr(
                    "Aucun répertoire Plugins/ trouvé dans le projet.",
                    "No Plugins/ directory found in the project.",
                ),
            )
            return

        meta_map = _discover_bcasl_meta(Plugins_dir)
        if not meta_map:
            QMessageBox.information(
                self,
                self.tr("Information", "Information"),
                self.tr(
                    "Aucun plugin détecté dans Plugins/.",
                    "No plugins detected in Plugins.",
                ),
            )
            return

        cfg = _load_workspace_config(workspace_root)
        plugin_instances = _discover_bcasl_plugins(Plugins_dir, workspace_root, cfg)

        from Ui.Gui.Dialogs.BcaslDialog import open_bcasl_pipeline_dialog

        open_bcasl_pipeline_dialog(
            self, workspace_root, meta_map, cfg, plugin_instances
        )

    except Exception as e:
        try:
            if hasattr(self, "log") and self.log is not None:
                self.log.append(f"BCASL Pipeline UI error: {e}")
        except Exception:
            pass


# Plugins


def run_pre_compile_async(self, on_done: Optional[callable] = None) -> None:
    """Lance BCASL en arrière-plan si QtCore est dispo; sinon, exécution bloquante rPluginsde.
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
        Plugins_dir = _get_plugins_dir()

        cfg = _load_workspace_config(workspace_root)
        plugin_timeout = _resolve_plugin_timeout(cfg)

        # Vérifier si BCASL est activé globalement via ark.yml
        if not _is_bcasl_enabled(workspace_root):
            try:
                if hasattr(self, "log") and self.log is not None:
                    self.log.append(
                        self.tr(
                            "BCASL désactivé dans ark.yml. Exécution ignorée\n",
                            "BCASL disabled in ark.yml. Skipping execution\n",
                        )
                    )
            except Exception:
                pass
            if callable(on_done):
                try:
                    on_done({"status": "disabled"})
                except Exception:
                    pass
            return

        if QThread is not None and QObject is not None and Signal is not None:
            from Ui.Gui.Dialogs.BcaslDialog import _BCASLUiBridge, _BCASLWorker

            thread = QThread()
            worker = _BCASLWorker(workspace_root, Plugins_dir, cfg, plugin_timeout)
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
            return

        # Repli: exécution synchrone
        try:
            log_cb = None
            if hasattr(self, "log") and self.log is not None:
                log_cb = self.log.append
            report = _run_bcasl_sync(
                workspace_root,
                Plugins_dir,
                cfg,
                plugin_timeout,
                log_cb=log_cb,
            )
        except Exception as _e:
            report = None
            try:
                if hasattr(self, "log") and self.log is not None:
                    self.log.append(f"Erreur BCASL: {_e}\n")
            except Exception:
                pass
        if callable(on_done):
            try:
                on_done(report)
            except Exception:
                pass
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


def run_pre_compile(self) -> Optional[object]:
    """Execute la phase BCASL de pre-compilation (path synchrone, simple)."""
    try:
        if not getattr(self, "workspace_dir", None):
            return None
        workspace_root = Path(self.workspace_dir).resolve()
        Plugins_dir = _get_plugins_dir()

        cfg = _load_workspace_config(workspace_root)
        plugin_timeout = _resolve_plugin_timeout(cfg)

        # Vérifier si BCASL est activé globalement via ark.yml
        if not _is_bcasl_enabled(workspace_root):
            try:
                if hasattr(self, "log") and self.log is not None:
                    self.log.append("BCASL désactivé dans ark.yml. Exécution ignorée\n")
            except Exception:
                pass
            return None

        log_cb = None
        if hasattr(self, "log") and self.log is not None:
            log_cb = self.log.append
        report = _run_bcasl_sync(
            workspace_root,
            Plugins_dir,
            cfg,
            plugin_timeout,
            log_cb=log_cb,
        )
        if hasattr(self, "log") and self.log is not None:
            self.log.append("BCASL - Rapport:\n")
            for item in report:
                state = "OK" if item.success else f"FAIL: {item.error}"
                self.log.append(
                    f" - {item.plugin_id}: {state} ({item.duration_ms:.1f} ms)\n"
                )
            self.log.append(report.summary() + "\n")
        return report
    except Exception as e:
        try:
            if hasattr(self, "log") and self.log is not None:
                self.log.append(f"Erreur BCASL: {e}\n")
        except Exception:
            pass
        return None
