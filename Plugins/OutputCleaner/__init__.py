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

import shutil
from pathlib import Path
from typing import Optional


from Plugins_SDK.BcPluginContext import (
    BcPluginBase,
    PluginMeta,
    PreCompileContext,
    bc_register,
)
from Plugins_SDK.GeneralContext import (
    Dialog,
    get_language_code,
    load_plugin_language_file,
    register_i18n_handler,
    register_plugin_translations,
    translate,
)

# Create instances of Dialog for logging and user interaction
log = Dialog()
dialog = Dialog()


def _load_i18n() -> None:
    try:
        lang_code = get_language_code()
        data = load_plugin_language_file(__package__, lang_code)
        if isinstance(data, dict) and data:
            register_plugin_translations("outputcleaner", data)
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

    def on_pre_compile(self, ctx: PreCompileContext) -> None:
        """Nettoie le dossier output avant la compilation."""
        try:
            if not ctx.build_context:
                log.log_warn(
                    "OutputCleaner: No BuildContext available. Cannot identify output directory."
                )
                return

            output_dir_str = getattr(ctx.build_context, "output_dir", None)
            if not output_dir_str:
                log.log_warn("OutputCleaner: No output_dir defined in BuildContext.")
                return

            output_dir = Path(output_dir_str)
            if not output_dir.is_absolute():
                output_dir = ctx.root / output_dir

            if not output_dir.exists():
                log.log_info(
                    f"OutputCleaner: Output directory does not exist: {output_dir}"
                )
                return

            log.log_info(f"OutputCleaner: Cleaning output directory: {output_dir}")

            # Simple confirmation if configured
            cfg = self._get_config(ctx)
            if bool(cfg.get("confirm", True)):
                response = dialog.msg_question(
                    title="Output Cleaner",
                    text=f"Do you want to delete all contents in {output_dir}?",
                    default_yes=True,
                )
                if not response:
                    return

            # Actually delete the directory and recreate it
            try:
                shutil.rmtree(output_dir)
                output_dir.mkdir(parents=True, exist_ok=True)
                log.log_info(f"OutputCleaner: Successfully cleaned {output_dir}")
            except Exception as e:
                log.log_err(f"OutputCleaner: Failed to clean {output_dir}: {e}")

        except Exception as e:
            log.log_err(f"OutputCleaner error: {e}")
