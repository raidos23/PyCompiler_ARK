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


from pycompiler_ark.Plugins_SDK.BcPluginContext import (
    BcPluginBase,
    PluginMeta,
    PreCompileContext,
    bc_register,
)
from pycompiler_ark.Plugins_SDK.GeneralContext import (
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
    # pyrefly: ignore [unexpected-keyword]
    id="cleaner",
    # pyrefly: ignore [unexpected-keyword]
    name="Cleaner",
    # pyrefly: ignore [unexpected-keyword]
    version="1.0.0",
    # pyrefly: ignore [unexpected-keyword]
    description="Clean the workspace (.pyc and __pycache__)",
    # pyrefly: ignore [unexpected-keyword]
    author="Samuel Amen Ague",
    # pyrefly: ignore [unexpected-keyword]
    tags=["clean"],
    # pyrefly: ignore [unexpected-keyword]
    required_bcasl_version="2.0.0",
    # pyrefly: ignore [unexpected-keyword]
    required_core_version="1.0.0",
    # pyrefly: ignore [unexpected-keyword]
    required_plugins_sdk_version="1.0.0",
    # pyrefly: ignore [unexpected-keyword]
    required_bc_plugin_context_version="1.0.0",
    # pyrefly: ignore [unexpected-keyword]
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
            plugins_cfg = ctx.config.get("plugins", {})
            entry = plugins_cfg.get(self.meta.id, {})
            return entry.get("config", {}) if isinstance(entry, dict) else {}
        except Exception:
            return {}

    def build_config_tab(self, parent, ctx: PreCompileContext, config: dict):
        try:
            from PySide6.QtWidgets import (
                QCheckBox,
                QFormLayout,
                QGroupBox,
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
        """Nettoie le workspace avant la compilation."""
        try:
            cfg = self._get_config(ctx)
            ask_confirm = bool(cfg.get("confirm", True))
            clean_pyc = bool(cfg.get("clean_pyc", True))
            clean_pycache = bool(cfg.get("clean_pycache", True))

            if not clean_pyc and not clean_pycache:
                return

            if ask_confirm:
                response = dialog.msg_question(
                    title="Cleaner",
                    text=f"Do you want to clean the workspace (.pyc and __pycache__)?",
                    default_yes=True,
                )
                if not response:
                    return

            self.cleaned_files = 0
            self.cleaned_dirs = 0

            log.log_info(f"Cleaning workspace: {ctx.name} ({ctx.root})")
            progress = dialog.progress(title="Cleaning workspace...", cancelable=True)
            progress.show()

            try:
                progress.set_message("Scanning files...")

                if clean_pyc:
                    pyc_files = list(ctx.iter_files(["**/*.pyc"]))
                    progress.set_message("Removing .pyc files...")
                    progress.set_progress(0, len(pyc_files))
                    for idx, file_path in enumerate(pyc_files):
                        if progress.is_canceled():
                            break
                        try:
                            file_path.unlink()
                            self.cleaned_files += 1
                        except Exception:
                            pass
                        progress.set_progress(idx + 1, len(pyc_files))

                if clean_pycache:
                    progress.set_message("Removing __pycache__ directories...")
                    pycache_dirs = list(ctx.root.rglob("__pycache__"))
                    progress.set_progress(0, len(pycache_dirs))
                    for idx, pycache_dir in enumerate(pycache_dirs):
                        if progress.is_canceled():
                            break
                        try:
                            shutil.rmtree(pycache_dir)
                            self.cleaned_dirs += 1
                        except Exception:
                            pass
                        progress.set_progress(idx + 1, len(pycache_dirs))
            finally:
                progress.close()

            log.log_info(
                f"Cleaner completed: {self.cleaned_files} files and {self.cleaned_dirs} dirs removed"
            )
        except Exception as e:
            log.log_warn(f"Error during cleaning: {e}")
