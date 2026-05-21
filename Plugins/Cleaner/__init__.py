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

import os
import shutil
from pathlib import Path
from typing import Optional

from bcasl import bc_register
from Plugins_SDK.BcPluginContext import BcPluginBase, PluginMeta, PreCompileContext
from Plugins_SDK.GeneralContext import (
    Dialog,
    get_language_code,
    load_plugin_language_file,
    register_i18n_handler,
    register_plugin_translations,
    translate,
)

# Create instances of Dialog for logging and user interaction
# These now automatically execute in the main Qt thread, ensuring theme inheritance
# and proper UI integration with the main application
log = Dialog()
dialog = Dialog()


def _load_i18n() -> None:
    try:
        lang_code = get_language_code()
        data = load_plugin_language_file(__package__, lang_code)
        if isinstance(data, dict) and data:
            register_plugin_translations("cleaner", data)
    except Exception:
        pass


# Load translations now and refresh on language changes
_load_i18n()
try:
    register_i18n_handler(lambda _gui, _tr: _load_i18n())
except Exception:
    pass

# Plugin metadata
PLUGIN_META = PluginMeta(
    id="cleaner",
    name="Cleaner",
    version="1.0.0",
    description="Clean the workspace (.pyc and __pycache__)",
    author="Samuel Amen Ague",
    tags=["clean"],
    required_bcasl_version="2.0.0",
    required_core_version="1.0.0",
    required_plugins_sdk_version="1.0.0",
    required_bc_plugin_context_version="1.0.0",
    required_general_context_version="1.0.0",
)


@bc_register
class Cleaner(BcPluginBase):
    """Plugin de nettoyage du workspace avant compilation.

    Remove les files .pyc et les folders __pycache__ pour réduire la taille
    et éviter les problèmes de cache lors de la compilation.
    """

    meta = PLUGIN_META

    def __init__(self):
        super().__init__(meta=PLUGIN_META)
        self.cleaned_files = 0
        self.cleaned_dirs = 0

    def _get_config(self, ctx: PreCompileContext) -> dict:
        try:
            cfg = ctx.get_workspace_config() or {}
            plugins_cfg = cfg.get("plugins", {}) if isinstance(cfg, dict) else {}
            entry = (
                plugins_cfg.get(self.meta.id, {})
                if isinstance(plugins_cfg, dict)
                else {}
            )
            plugin_cfg = entry.get("config", {}) if isinstance(entry, dict) else {}
            if isinstance(plugin_cfg, dict):
                return dict(plugin_cfg)
        except Exception:
            pass
        return {}

    def build_config_tab(self, parent, ctx: PreCompileContext, config: dict):
        try:
            from PySide6.QtWidgets import (
                QCheckBox,
                QFormLayout,
                QGroupBox,
                QHBoxLayout,
                QLabel,
                QSizePolicy,
                QVBoxLayout,
                QWidget,
            )
        except Exception:
            return None

        w = QWidget(parent)
        lay = QVBoxLayout(w)
        lay.setSpacing(8)
        lay.setContentsMargins(8, 8, 8, 8)

        # Safety
        safety_group = QGroupBox(translate("cleaner", "ui_safety", "Safety"), w)
        safety_layout = QVBoxLayout()
        safety_layout.setSpacing(4)
        chk_confirm = QCheckBox(
            translate("cleaner", "ui_confirm", "Ask confirmation before cleaning"),
            safety_group,
        )
        safety_layout.addWidget(chk_confirm)
        safety_group.setLayout(safety_layout)

        # Targets
        targets_group = QGroupBox(translate("cleaner", "ui_targets", "Targets"), w)
        targets_layout = QFormLayout()
        targets_layout.setSpacing(6)
        chk_pyc = QCheckBox(
            translate("cleaner", "ui_pyc", "Remove .pyc files"), targets_group
        )
        chk_pycache = QCheckBox(
            translate("cleaner", "ui_pycache", "Remove __pycache__ folders"),
            targets_group,
        )
        targets_layout.addRow(chk_pyc)
        targets_layout.addRow(chk_pycache)
        targets_group.setLayout(targets_layout)

        chk_confirm.setChecked(bool(config.get("confirm", True)))
        chk_pyc.setChecked(bool(config.get("clean_pyc", True)))
        chk_pycache.setChecked(bool(config.get("clean_pycache", True)))

        lay.addWidget(safety_group)
        lay.addWidget(targets_group)

        # Compact hint
        hint = QLabel(
            translate(
                "cleaner", "ui_tip", "Tip: disable items you don't want to delete."
            ),
            w,
        )
        hint.setStyleSheet("color: #888; font-size: 11px;")
        hint.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        lay.addWidget(hint)
        lay.addStretch(1)

        def on_save(cfg: dict):
            cfg["confirm"] = bool(chk_confirm.isChecked())
            cfg["clean_pyc"] = bool(chk_pyc.isChecked())
            cfg["clean_pycache"] = bool(chk_pycache.isChecked())
            return cfg

        return ("Cleaner", w, on_save)

    def on_pre_compile(self, ctx: PreCompileContext) -> None:
        """Nettoie le workspace avant la compilation.

        Args:
          ctx: PreCompileContext avec les informations du workspace depuis bcasl.yml
        """
        try:
            # Vérifier que le workspace est valide et configuré dans bcasl.yml
            if not ctx.is_workspace_valid():
                log.log_warn("Workspace is not valid or bcasl.yml not found")
                return

            cfg = self._get_config(ctx)
            ask_confirm = bool(cfg.get("confirm", True))
            clean_pyc = bool(cfg.get("clean_pyc", True))
            clean_pycache = bool(cfg.get("clean_pycache", True))
            if not clean_pyc and not clean_pycache:
                log.log_info(
                    translate(
                        "cleaner",
                        "log_noop",
                        "Cleaner: nothing to do (both options disabled)",
                    )
                )
                return

            # Demander confirmation à l'utilisateur
            if ask_confirm:
                response = dialog.msg_question(
                    title="Cleaner",
                    text=translate(
                        "cleaner",
                        "dlg_confirm",
                        "Do you want to clean the workspace (.pyc and __pycache__)?",
                    ),
                    default_yes=True,
                )

                if not response:
                    log.log_info(
                        translate("cleaner", "log_cancel", "Cleaner cancelled by user")
                    )
                    return

            # Réinitialiser les compteurs
            self.cleaned_files = 0
            self.cleaned_dirs = 0

            # Obtenir le chemin du workspace depuis bcasl.yml
            workspace_path = ctx.get_workspace_root()
            workspace_name = ctx.get_workspace_name()

            log.log_info(f"Cleaning workspace: {workspace_name} ({workspace_path})")

            # Créer le dialog de progression
            progress = dialog.progress(title="Cleaning workspace...", cancelable=True)
            progress.show()

            try:
                # Étape 1: Parcourir et supprimer les fichiers .pyc
                progress.set_message(
                    "Scanning for .pyc files and __pycache__ directories..."
                )

                pyc_files = []
                try:
                    # Utiliser les patterns d'exclusion depuis bcasl.yml
                    exclude_patterns = ctx.get_exclude_patterns()
                    if clean_pyc:
                        for file_path in ctx.iter_files(["**/*.pyc"], exclude_patterns):
                            pyc_files.append(file_path)
                except Exception as e:
                    log.log_warn(f"Error iterating .pyc files: {e}")

                # Étape 2: Supprimer les fichiers .pyc
                if clean_pyc:
                    progress.set_message("Removing .pyc files...")
                    progress.set_progress(0, len(pyc_files))

                    for idx, file_path in enumerate(pyc_files):
                        if progress.is_canceled():
                            break
                        try:
                            Path(file_path).unlink()
                            self.cleaned_files += 1
                        except Exception as e:
                            log.log_warn(f"Failed to remove {file_path}: {e}")
                        progress.set_progress(idx + 1, len(pyc_files))

                # Étape 3: Parcourir et supprimer les dossiers __pycache__
                if clean_pycache:
                    progress.set_message("Removing __pycache__ directories...")

                pycache_dirs = []
                try:
                    if clean_pycache:
                        for pycache_dir in workspace_path.rglob("__pycache__"):
                            pycache_dirs.append(pycache_dir)
                except Exception as e:
                    log.log_warn(f"Error iterating __pycache__ directories: {e}")

                if clean_pycache:
                    progress.set_progress(0, len(pycache_dirs))

                    for idx, pycache_dir in enumerate(pycache_dirs):
                        if progress.is_canceled():
                            break
                        try:
                            shutil.rmtree(pycache_dir)
                            self.cleaned_dirs += 1
                        except Exception as e:
                            log.log_warn(f"Failed to remove {pycache_dir}: {e}")
                        progress.set_progress(idx + 1, len(pycache_dirs))

            finally:
                progress.close()

            # Afficher le résumé
            log.log_info(
                f"Cleaner completed: {self.cleaned_files} .pyc files and {self.cleaned_dirs} __pycache__ directories removed"
            )

        except Exception as e:
            log.log_warn(f"Error during cleaning: {e}")
