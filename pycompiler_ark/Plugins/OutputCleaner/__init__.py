# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Samuel Amen Ague
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

import shutil
from pathlib import Path
from typing import Optional


from pycompiler_ark.Plugins_SDK.BcPluginContext import (
    BcPluginBase,
    PluginMeta,
    bc_register,
    PreCompileContext,
)
from pycompiler_ark.Plugins_SDK.GeneralContext import Dialog, translate

# Create instances of Dialog for logging and user interaction.
log = Dialog()
dialog = Dialog()


def _tr(key: str, default: str, **values: object) -> str:
    try:
        text = translate("outputcleaner", key, default)
        return text.format(**values) if values else text
    except Exception:
        return default

# Plugin metadata
PLUGIN_META = PluginMeta(
    # pyrefly: ignore [unexpected-keyword]
    id="outputcleaner",
    # pyrefly: ignore [unexpected-keyword]
    name="Output Cleaner",
    # pyrefly: ignore [unexpected-keyword]
    version="1.0.0",
    # pyrefly: ignore [unexpected-keyword]
    description="Clean the output directory before compilation",
    # pyrefly: ignore [unexpected-keyword]
    author="Samuel Amen Ague",
    # pyrefly: ignore [unexpected-keyword]
    tags=["clean", "output"],
    # pyrefly: ignore [unexpected-keyword]
    required_bcasl_version="1.0.0",
)


@bc_register
class OutputCleaner(BcPluginBase):
    """Plugin to clean the output dir.

    Use BuildContext to identify the output dir .
    """

    meta = PLUGIN_META

    def __init__(self):
        super().__init__(meta=PLUGIN_META)

    def _get_config(self, ctx: PreCompileContext) -> dict:
        try:
            plugins_cfg = ctx.config.get("plugins", {})
            entry = plugins_cfg.get(self.meta.id, {})
            return entry.get("config", {}) if isinstance(entry, dict) else {}
        except Exception:
            return {}

    def create_tab(self, parent, ctx: PreCompileContext, config: dict):
        try:
            from PySide6.QtWidgets import (
                QCheckBox,
                QGroupBox,
                QLabel,
                QSizePolicy,
                QVBoxLayout,
                QWidget,
            )
        except Exception:
            return None

        widget = QWidget(parent)
        widget.setObjectName("plugin_outputcleaner")
        layout = QVBoxLayout(widget)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)

        safety_group = QGroupBox(
            _tr("ui_safety", "Safety"), widget
        )
        safety_group.setObjectName("ui_safety")
        safety_layout = QVBoxLayout(safety_group)
        safety_layout.setSpacing(4)

        chk_confirm = QCheckBox(
            _tr(
                "ui_confirm",
                "Ask confirmation before cleaning the output directory",
            ),
            safety_group,
        )
        chk_confirm.setObjectName("ui_confirm")
        safety_layout.addWidget(chk_confirm)

        hint = QLabel(
            _tr(
                "ui_hint",
                "This plugin removes the build output before compilation.",
            ),
            widget,
        )
        hint.setObjectName("ui_hint")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #888; font-size: 11px;")
        hint.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        safety_group.setLayout(safety_layout)
        layout.addWidget(safety_group)
        layout.addWidget(hint)
        layout.addStretch(1)

        chk_confirm.setChecked(bool(config.get("confirm", True)))

        def on_save(cfg: dict):
            cfg["confirm"] = bool(chk_confirm.isChecked())
            return cfg

        return (_tr("tab_title", "Output Cleaner"), widget, on_save)

    def on_pre_compile(self, ctx: PreCompileContext) -> None:
        """Nettoie le dossier output avant la compilation."""
        try:
            if not ctx.build_context:
                log.log_warn(
                    _tr(
                        "warn_no_build_context",
                        "OutputCleaner: No BuildContext available. Cannot identify output directory.",
                    )
                )
                return

            output_dir_str = getattr(ctx.build_context, "output_dir", None)
            if not output_dir_str:
                log.log_warn(
                    _tr(
                        "warn_no_output_dir",
                        "OutputCleaner: No output_dir defined in BuildContext.",
                    )
                )
                return

            output_dir = Path(output_dir_str)
            if not output_dir.is_absolute():
                output_dir = ctx.root / output_dir

            if not output_dir.exists():
                log.log_info(
                    _tr(
                        "info_output_missing",
                        "OutputCleaner: Output directory does not exist: {output_dir}",
                        output_dir=output_dir,
                    )
                )
                return

            log.log_info(
                _tr(
                    "info_cleaning",
                    "OutputCleaner: Cleaning output directory: {output_dir}",
                    output_dir=output_dir,
                )
            )

            # Simple confirmation if configured
            cfg = self._get_config(ctx)
            if bool(cfg.get("confirm", True)):
                response = dialog.msg_question(
                    title=_tr("dialog_title", "Output Cleaner"),
                    text=_tr(
                        "question_delete",
                        "Do you want to delete all contents in {output_dir}?",
                        output_dir=output_dir,
                    ),
                    default_yes=True,
                )
                if not response:
                    return

            # Actually delete the directory and recreate it
            try:
                shutil.rmtree(output_dir)
                output_dir.mkdir(parents=True, exist_ok=True)
                log.log_info(
                    _tr(
                        "success_cleaned",
                        "OutputCleaner: Successfully cleaned {output_dir}",
                        output_dir=output_dir,
                    )
                )
            except Exception as e:
                log.log_error(
                    _tr(
                        "error_failed",
                        "OutputCleaner: Failed to clean {output_dir}: {error}",
                        output_dir=output_dir,
                        error=e,
                    )
                )

        except Exception as e:
            log.log_error(
                _tr("error_generic", "OutputCleaner error: {error}", error=e)
            )
