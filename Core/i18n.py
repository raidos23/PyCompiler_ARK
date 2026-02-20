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

from __future__ import annotations

import asyncio
import json
import locale
import os
from typing import Any

from engine_sdk.utils import log_i18n_level

# Built-in fallback for English if language files are missing
FALLBACK_EN: dict[str, Any] = {
    "name": "English",
    "code": "en",
    "_meta": {"code": "en", "name": "English"},
    "select_folder": "Choose workspace",
    "select_files": "Add files",
    "build_all": "Compile",
    "export_config": "Export config",
    "import_config": "Import config",
    "cancel_all": "Cancel",
    "suggest_deps": "Dependencies",
    "help": "Help",
    "help_title": "Help",
    "help_text": "<b>PyCompiler ARK — Quick Help</b><br><ul><li>1) Select the Workspace and add your .py files.</li><li>2) Configure pre‑compile plugins via <b>Bc Plugins Loader</b> (BCASL).</li><li>3) Configure options in the <b>PyInstaller</b>, <b>Nuitka</b> or <b>CX_Freeze</b> tab.</li><li>4) Click <b>Build</b> and follow the logs.</li></ul><b>Notes</b><br><ul><li>When a build starts, all action controls are disabled (including Bc Plugins Loader) until it finishes or is canceled.</li><li>Pre‑compilation (BCASL) completes before compilation.</li><li>A <i>venv</i> can be created automatically; requirements.txt is installed if present; tools are installed into the venv as needed.</li><li>Plugins‑initiated workspace changes are auto‑applied; running builds are canceled before switching.</li></ul><b>License</b>: Apache-2.0 — <a href='https://www.apache.org/licenses/LICENSE-2.0'>apache.org/licenses/LICENSE-2.0</a><br><b>Author</b>: Ague Samuel Amen<br>© 2026 Ague Samuel Amen",
    "show_stats": "Statistics",
    "select_lang": "Language",
    "venv_button": "Choose venv folder",
    "label_workspace_section": "Workspace",
    "venv_label": "venv selected: None",
    "label_folder": "No folder selected",
    "label_files_section": "Files to compile",
    "btn_remove_file": "Remove selected file",
    "label_logs_section": "Compilation log",
    "label_tools": "Tools",
    "label_options_section": "Compilation options",
    "label_progress": "Compilation progress",
    "label_workspace_status": "Workspace: {path}",
    "label_workspace_status_none": "Workspace: None",
    "file_filter_placeholder": "Filter list…",
    "btn_clear_workspace": "Clear workspace",
    "choose_language_title": "Choose language",
    "choose_language_label": "Language:",
    "choose_language_system": "System",
    "choose_language_system_button": "Language (System)",
    "choose_language_button": "Language",
    "select_theme": "Theme",
    "choose_theme_button": "Theme",
    "choose_theme_system_button": "Theme (System)",
    "tt_select_folder": "Select the workspace folder.",
    "tt_select_files": "Add files to compile.",
    "tt_build_all": "Start compilation.",
    "tt_export_config": "Export the current configuration to a JSON file.",
    "tt_import_config": "Import a configuration from a JSON file.",
    "tt_cancel_all": "Cancel the current compilation.",
    "tt_remove_file": "Remove the selected file(s) from the list.",
    "tt_help": "Show help.",
    "tt_bc_loader": "Open BC Plugins Loader.",
    "tt_venv_button": "Manually select a venv directory to use for compilation.",
    "tt_suggest_deps": "Analyze project dependencies.",
    "tt_show_stats": "Show compilation statistics.",
    "tt_clear_workspace": "Clear the file list and reset the selection.",
}


# Cache global pour les traductions chargées (évite les rechargements)
_TRANSLATION_CACHE: dict[str, dict[str, Any]] = {}
_LANGUAGES_CACHE: list[dict[str, str]] | None = None
_CACHE_LOCK = asyncio.Lock()


def _project_root() -> str:
    """Retourne le chemin racine du projet (synchrone, pas d'I/O bloquant)."""
    try:
        return os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    except Exception:
        return os.getcwd()


def _languages_dir() -> str:
    """Retourne le chemin du dossier languages (synchrone, pas d'I/O bloquant)."""
    try:
        return os.path.join(_project_root(), "languages")
    except Exception:
        return "languages"


# Normalization helper must be pure (no I/O or system lookups)
# Leave "System" unresolved; callers must resolve system language asynchronously when needed.
async def normalize_lang_pref(pref: str | None) -> str:
    if not pref or pref == "System":
        return "System"
    pref_l = pref.lower()
    if pref_l in ("english", "en"):
        return "en"
    if pref_l in ("français", "francais", "fr"):
        return "fr"
    # Arbitrary language code - accept as-is
    return pref


# Internal sync helpers (non-public); used via asyncio.to_thread


def _resolve_system_language_sync() -> str:
    try:
        loc = locale.getdefaultlocale()[0] or ""
        return "fr" if loc.lower().startswith(("fr", "fr_")) else "en"
    except Exception:
        return "en"


def _load_language_file_sync(code: str) -> dict[str, Any] | None:
    fpath = os.path.join(_languages_dir(), f"{code}.json")
    if not os.path.isfile(fpath):
        return None
    try:
        with open(fpath, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _available_languages_sync() -> list[dict[str, str]]:
    langs: list[dict[str, str]] = []
    try:
        path = _languages_dir()
        if not os.path.isdir(path):
            return [
                {
                    "code": FALLBACK_EN["_meta"]["code"],
                    "name": FALLBACK_EN["_meta"]["name"],
                }
            ]
        for fname in sorted(os.listdir(path)):
            if not fname.endswith(".json"):
                continue
            default_code = os.path.splitext(fname)[0]
            fpath = os.path.join(path, fname)
            try:
                with open(fpath, encoding="utf-8") as f:
                    data = json.load(f)
                meta = data.get("_meta", {}) if isinstance(data, dict) else {}
                name = None
                code = None
                if isinstance(data, dict):
                    name = data.get("name") or (
                        meta.get("name") if isinstance(meta, dict) else None
                    )
                    code = data.get("code") or (
                        meta.get("code") if isinstance(meta, dict) else None
                    )
                langs.append(
                    {
                        "code": code or default_code,
                        "name": name or default_code,
                    }
                )
            except Exception:
                langs.append({"code": default_code, "name": default_code})
    except Exception:
        pass
    if not langs:
        langs = [
            {"code": FALLBACK_EN["_meta"]["code"], "name": FALLBACK_EN["_meta"]["name"]}
        ]
    return langs


# Public async Plugins with real-time caching and error handling


async def resolve_system_language() -> str:
    """Résout la langue système en temps réel avec gestion d'erreurs."""
    try:
        return await asyncio.to_thread(_resolve_system_language_sync)
    except Exception:
        return "en"


async def available_languages() -> list[dict[str, str]]:
    """Retourne les langues disponibles avec caching thread-safe."""
    global _LANGUAGES_CACHE

    try:
        # Vérifier le cache d'abord (rPluginsde)
        if _LANGUAGES_CACHE is not None:
            return _LANGUAGES_CACHE

        # Charger depuis le disque en thread pool
        langs = await asyncio.to_thread(_available_languages_sync)

        # Mettre en cache de manière thread-safe
        async with _CACHE_LOCK:
            _LANGUAGES_CACHE = langs

        return langs
    except Exception:
        # Fallback: retourner au moins l'anglais
        return [{"code": "en", "name": "English"}]


async def get_translations(lang_pref: str | None) -> dict[str, Any]:
    """Charge les traductions en temps réel avec caching et fallbacks robustes."""
    try:
        # Normaliser la préférence de langue
        code = await normalize_lang_pref(lang_pref)

        # Résoudre "System" vers la langue réelle
        if code == "System":
            code = await resolve_system_language()

        # Vérifier le cache d'abord (très rPluginsde)
        if code in _TRANSLATION_CACHE:
            return _TRANSLATION_CACHE[code]

        # Charger depuis le disque en thread pool
        data = await asyncio.to_thread(_load_language_file_sync, code)

        # Valider les données
        if not isinstance(data, dict) or not data:
            data = FALLBACK_EN.copy()

        # Normaliser les métadonnées
        data = _normalize_translation_meta(data, code)

        # Mettre en cache de manière thread-safe
        async with _CACHE_LOCK:
            _TRANSLATION_CACHE[code] = data

        return data

    except Exception:
        # Fallback ultime: retourner l'anglais avec métadonnées normalisées
        return _normalize_translation_meta(FALLBACK_EN.copy(), "en")


def _normalize_translation_meta(data: dict[str, Any], code: str) -> dict[str, Any]:
    """Normalise les métadonnées de traduction (synchrone, pas d'I/O)."""
    try:
        if not isinstance(data, dict):
            data = {}

        # Extraire les métadonnées existantes
        top_name = data.get("name") if isinstance(data, dict) else None
        top_code = data.get("code") if isinstance(data, dict) else None
        meta_in = data.get("_meta", {}) if isinstance(data, dict) else {}

        if not isinstance(meta_in, dict):
            meta_in = {}

        # Construire les métadonnées finales avec fallbacks
        final_code = top_code or meta_in.get("code") or code or "en"

        final_name = top_name or meta_in.get("name") or _get_language_name(final_code)

        # Mettre à jour les métadonnées
        data["_meta"] = {
            "code": final_code,
            "name": final_name,
        }

        return data

    except Exception:
        # En cas d'erreur, retourner une structure minimale valide
        return {
            "_meta": {"code": code or "en", "name": _get_language_name(code or "en")}
        }


def _get_language_name(code: str) -> str:
    """Retourne le nom de la langue pour un code donné (synchrone, pas d'I/O)."""
    code_lower = (code or "").lower()

    if code_lower in ("en", "english"):
        return "English"
    elif code_lower in ("fr", "français", "francais"):
        return "Français"
    elif code_lower in ("es", "español", "espanol"):
        return "Español"
    elif code_lower in ("de", "deutsch"):
        return "Deutsch"
    elif code_lower in ("it", "italiano"):
        return "Italiano"
    elif code_lower in ("pt", "português", "portugues"):
        return "Português"
    elif code_lower in ("ja", "日本語"):
        return "日本語"
    elif code_lower in ("zh", "中文"):
        return "中文"
    elif code_lower in ("ru", "русский"):
        return "Русский"
    else:
        # Retourner le code en majuscule comme fallback
        return code.upper() if code else "Unknown"


async def clear_translation_cache() -> None:
    """Vide le cache des traductions (utile pour les tests ou rechargements)."""
    global _TRANSLATION_CACHE, _LANGUAGES_CACHE

    try:
        async with _CACHE_LOCK:
            _TRANSLATION_CACHE.clear()
            _LANGUAGES_CACHE = None
    except Exception:
        pass


def get_current_language_sync() -> str:
    """Retourne la langue actuelle depuis les préférences utilisateur (synchrone)."""
    try:
        # Importer ici pour éviter les imports circulaires
        from .PreferencesManager import PREFS_FILE

        if os.path.isfile(PREFS_FILE):
            with open(PREFS_FILE, encoding="utf-8") as f:
                prefs = json.load(f)
            lang_pref = prefs.get("language_pref", prefs.get("language", "System"))
            if lang_pref == "System":
                return _resolve_system_language_sync()
            return lang_pref
        else:
            return _resolve_system_language_sync()
    except Exception:
        return "en"


def apply_language(self, lang_display: str) -> None:
    """Applique la langue sélectionnée (centralisé)."""
    from .Globals import _run_coro_async

    async def _do():
        code = (
            await resolve_system_language()
            if lang_display == "System"
            else await normalize_lang_pref(lang_display)
        )
        tr = await get_translations(code)
        return code, tr

    def _on_result(res):
        if isinstance(res, Exception):
            return
        code, tr = res
        _apply_main_app_translations(self, tr)
        # Notifier les moteurs pour rafraîchir leurs libellés
        try:
            for cb in getattr(self, "_language_refresh_callbacks", []) or []:
                try:
                    cb()
                except Exception:
                    pass
            try:
                import EngineLoader as engines_loader

                engines_loader.registry.apply_translations(self, tr)
            except Exception:
                pass
        except Exception:
            pass
        meta = tr.get("_meta", {})
        self.current_language = meta.get("name", lang_display)
        self.language = lang_display
        try:
            self.save_preferences()
        except Exception:
            pass
        try:
            log_i18n_level(
                self,
                "info",
                f"Langue appliquée : {self.current_language}",
                f"Language applied: {self.current_language}",
            )
        except Exception:
            pass

    _run_coro_async(_do(), _on_result, ui_owner=self)


# PyCompiler ARK main GUI translation - FUSED VERSION
def _apply_main_app_translations(self, tr: dict[str, object]) -> None:
    """Apply translations to main app UI elements.

    This is a fused version combining the best features from both implementations.
    Uses the _set helper pattern for cleaner code while maintaining comprehensive coverage.
    """

    # Internal helper for setting widget text with fallback
    def _set(attr: str, key: str, method: str = "setText"):
        try:
            widget = getattr(self, attr, None)
            value = tr.get(key)
            if widget is not None and value:
                getattr(widget, method)(value)
        except Exception:
            pass

    # Internal helper for tooltips with fallback
    def _tt(key: str, current: str) -> str:
        try:
            val = tr.get(key)
            if isinstance(val, str) and val.strip():
                return val
        except Exception:
            pass
        return current

    try:
        # === BUTTONS ===
        # Sidebar & main buttons
        _set("btn_select_folder", "select_folder")
        _set("btn_select_files", "select_files")
        _set("compile_btn", "build_all")
        _set("btn_export_config", "export_config")
        _set("btn_import_config", "import_config")
        _set("cancel_btn", "cancel_all")
        _set("btn_suggest_deps", "suggest_deps")
        _set("btn_help", "help")
        _set("btn_show_stats", "show_stats")
        _set("btn_remove_file", "btn_remove_file")
        _set("btn_clear_workspace", "btn_clear_workspace")

        # Bouton de langue (variante System vs simple), sans valeur de secours
        try:
            if getattr(self, "select_lang", None):
                if (
                    getattr(self, "language_pref", getattr(self, "language", "System"))
                    == "System"
                ):
                    val = tr.get("choose_language_system_button") or tr.get(
                        "choose_language_button"
                    )
                else:
                    val = tr.get("choose_language_button")
                if val:
                    self.select_lang.setText(val)
        except Exception:
            pass

        # Bouton de thème (variante System vs simple), sans valeur de secours
        try:
            if getattr(self, "select_theme", None):
                if getattr(self, "theme", "System") == "System":
                    val = tr.get("choose_theme_system_button") or tr.get(
                        "choose_theme_button"
                    )
                else:
                    val = tr.get("choose_theme_button")
                if val:
                    self.select_theme.setText(val)
        except Exception:
            pass

        # Venv button and icon buttons
        _set("venv_button", "venv_button")
        _set("btn_select_icon", "btn_select_icon")
        _set("btn_nuitka_icon", "btn_nuitka_icon")

        # === LABELS ===
        _set("label_workspace_section", "label_workspace_section")
        _set("venv_label", "venv_label")
        _set("label_folder", "label_folder")
        _set("label_files_section", "label_files_section")
        _set("label_tools", "label_tools")
        _set("label_options_section", "label_options_section")
        _set("label_logs_section", "label_logs_section")
        _set("label_progress", "label_progress")

        # Workspace status label (dynamic path if available)
        if getattr(self, "label_workspace_status", None):
            try:
                ws = getattr(self, "workspace_dir", None)
                if ws:
                    tmpl = tr.get("label_workspace_status") or "Workspace: {path}"
                    self.label_workspace_status.setText(
                        str(tmpl).replace("{path}", str(ws))
                    )
                else:
                    val = tr.get("label_workspace_status_none") or "Workspace: None"
                    self.label_workspace_status.setText(str(val))
            except Exception:
                pass

        # === TABS ===
        if getattr(self, "compiler_tabs", None):
            try:
                if getattr(self, "tab_pyinstaller", None):
                    idx = self.compiler_tabs.indexOf(self.tab_pyinstaller)
                    if idx >= 0:
                        self.compiler_tabs.setTabText(
                            idx,
                            str(
                                tr.get(
                                    "tab_pyinstaller", self.compiler_tabs.tabText(idx)
                                )
                            ),
                        )
                if getattr(self, "tab_nuitka", None):
                    idx2 = self.compiler_tabs.indexOf(self.tab_nuitka)
                    if idx2 >= 0:
                        self.compiler_tabs.setTabText(
                            idx2,
                            str(tr.get("tab_nuitka", self.compiler_tabs.tabText(idx2))),
                        )
                # CX_Freeze tab if exists
                if getattr(self, "tab_cx_freeze", None):
                    idx3 = self.compiler_tabs.indexOf(self.tab_cx_freeze)
                    if idx3 >= 0:
                        self.compiler_tabs.setTabText(
                            idx3,
                            str(
                                tr.get(
                                    "tab_cx_freeze", self.compiler_tabs.tabText(idx3)
                                )
                            ),
                        )
            except Exception:
                pass

        # === CHECKBOXES/OPTIONS ===
        # PyInstaller options
        _set("opt_onefile", "opt_onefile")
        _set("opt_windowed", "opt_windowed")
        _set("opt_noconfirm", "opt_noconfirm")
        _set("opt_clean", "opt_clean")
        _set("opt_noupx", "opt_noupx")
        _set("opt_main_only", "opt_main_only")
        _set("opt_debug", "opt_debug")
        _set("opt_auto_install", "opt_auto_install")
        _set("opt_silent_errors", "opt_silent_errors")

        # Nuitka options
        _set("nuitka_onefile", "nuitka_onefile")
        _set("nuitka_standalone", "nuitka_standalone")
        _set("nuitka_disable_console", "nuitka_disable_console")
        _set("nuitka_show_progress", "nuitka_show_progress")

        # CX_Freeze options (if exists)
        _set("cx_onefile", "cx_onefile")
        _set("cx_console", "cx_console")

        # === PLACEHOLDERS ===
        if getattr(self, "nuitka_output_dir", None):
            try:
                ph = tr.get("nuitka_output_dir")
                if isinstance(ph, str) and ph.strip():
                    self.nuitka_output_dir.setPlaceholderText(ph)
            except Exception:
                pass
        if getattr(self, "file_filter_input", None):
            try:
                ph = tr.get("file_filter_placeholder")
                if isinstance(ph, str) and ph.strip():
                    self.file_filter_input.setPlaceholderText(ph)
            except Exception:
                pass

        # === TOOLTIPS ===
        # Main buttons tooltips
        if getattr(self, "btn_select_folder", None):
            self.btn_select_folder.setToolTip(
                _tt("tt_select_folder", self.btn_select_folder.toolTip())
            )
        if getattr(self, "btn_select_files", None):
            self.btn_select_files.setToolTip(
                _tt("tt_select_files", self.btn_select_files.toolTip())
            )
        if getattr(self, "compile_btn", None):
            self.compile_btn.setToolTip(_tt("tt_build_all", self.compile_btn.toolTip()))
        if getattr(self, "btn_export_config", None):
            self.btn_export_config.setToolTip(
                _tt("tt_export_config", self.btn_export_config.toolTip())
            )
        if getattr(self, "btn_import_config", None):
            self.btn_import_config.setToolTip(
                _tt("tt_import_config", self.btn_import_config.toolTip())
            )
        if getattr(self, "cancel_btn", None):
            self.cancel_btn.setToolTip(_tt("tt_cancel_all", self.cancel_btn.toolTip()))
        if getattr(self, "btn_remove_file", None):
            self.btn_remove_file.setToolTip(
                _tt("tt_remove_file", self.btn_remove_file.toolTip())
            )
        if getattr(self, "btn_select_icon", None):
            self.btn_select_icon.setToolTip(
                _tt("tt_select_icon", self.btn_select_icon.toolTip())
            )
        if getattr(self, "btn_nuitka_icon", None):
            self.btn_nuitka_icon.setToolTip(
                _tt("tt_nuitka_icon", self.btn_nuitka_icon.toolTip())
            )
        if getattr(self, "btn_help", None):
            self.btn_help.setToolTip(_tt("tt_help", self.btn_help.toolTip()))
        if getattr(self, "btn_bc_loader", None):
            self.btn_bc_loader.setToolTip(
                _tt("tt_bc_loader", self.btn_bc_loader.toolTip())
            )
        if getattr(self, "venv_button", None):
            self.venv_button.setToolTip(
                _tt("tt_venv_button", self.venv_button.toolTip())
            )
        if getattr(self, "btn_suggest_deps", None):
            self.btn_suggest_deps.setToolTip(
                _tt("tt_suggest_deps", self.btn_suggest_deps.toolTip())
            )
        if getattr(self, "btn_show_stats", None):
            self.btn_show_stats.setToolTip(
                _tt("tt_show_stats", self.btn_show_stats.toolTip())
            )
        if getattr(self, "btn_clear_workspace", None):
            self.btn_clear_workspace.setToolTip(
                _tt("tt_clear_workspace", self.btn_clear_workspace.toolTip())
            )

        # Output directory tooltip
        if getattr(self, "output_dir_input", None):
            self.output_dir_input.setToolTip(
                _tt("tt_output_dir", self.output_dir_input.toolTip())
            )

        # Options checkboxes tooltips
        if getattr(self, "opt_onefile", None):
            self.opt_onefile.setToolTip(
                _tt("tt_opt_onefile", self.opt_onefile.toolTip())
            )
        if getattr(self, "opt_windowed", None):
            self.opt_windowed.setToolTip(
                _tt("tt_opt_windowed", self.opt_windowed.toolTip())
            )
        if getattr(self, "opt_noconfirm", None):
            self.opt_noconfirm.setToolTip(
                _tt("tt_opt_noconfirm", self.opt_noconfirm.toolTip())
            )
        if getattr(self, "opt_clean", None):
            self.opt_clean.setToolTip(_tt("tt_opt_clean", self.opt_clean.toolTip()))
        if getattr(self, "opt_noupx", None):
            self.opt_noupx.setToolTip(_tt("tt_opt_noupx", self.opt_noupx.toolTip()))
        if getattr(self, "opt_main_only", None):
            self.opt_main_only.setToolTip(
                _tt("tt_opt_main_only", self.opt_main_only.toolTip())
            )
        if getattr(self, "opt_debug", None):
            self.opt_debug.setToolTip(_tt("tt_opt_debug", self.opt_debug.toolTip()))
        if getattr(self, "opt_auto_install", None):
            self.opt_auto_install.setToolTip(
                _tt("tt_opt_auto_install", self.opt_auto_install.toolTip())
            )
        if getattr(self, "opt_silent_errors", None):
            self.opt_silent_errors.setToolTip(
                _tt("tt_opt_silent_errors", self.opt_silent_errors.toolTip())
            )

        # Nuitka specific tooltips
        if getattr(self, "nuitka_disable_console", None):
            self.nuitka_disable_console.setToolTip(
                _tt("tt_nuitka_disable_console", self.nuitka_disable_console.toolTip())
            )

    except Exception:
        pass


# LANGUAGE DIALOG and all ARK language's system translations propagation
def show_language_dialog(self):
    from PySide6.QtWidgets import QInputDialog

    try:
        langs = asyncio.run(available_languages())
    except Exception:
        langs = [{"code": "en", "name": "English"}, {"code": "fr", "name": "Français"}]
    # Build options list with 'System' at top
    options = ["System"] + [str(x.get("name", x.get("code", ""))) for x in langs]
    # Determine current index
    current_pref = getattr(self, "language", "System")
    try:
        if current_pref == "System":
            start_index = 0
        else:
            # map code->index
            codes = [str(x.get("code", "")) for x in langs]
            try:
                start_index = 1 + codes.index(current_pref)
            except Exception:
                start_index = 0
    except Exception:
        start_index = 0
    title = "Choisir la langue"
    label = "Langue :"
    choice, ok = QInputDialog.getItem(self, title, label, options, start_index, False)
    if ok and choice:
        lang_pref = (
            "System"
            if choice == "System"
            else next(
                (
                    str(x.get("code", "en"))
                    for x in langs
                    if str(x.get("name", "")) == choice
                ),
                "en",
            )
        )
        try:
            # Apply initial language from preference using async i18n
            tr = asyncio.run(get_translations(lang_pref))
            _apply_main_app_translations(self, tr)
            try:
                setattr(self, "_tr", tr)
            except Exception:
                pass
            # Propagate translations to all engines so their UI matches the app language immediately
            try:
                import EngineLoader as engines_loader

                engines_loader.registry.apply_translations(self, tr)
            except Exception:
                pass
            # Propagate translations to all BCASL plugins
            try:
                import bcasl.Loader as bcasl_loader

                bcasl_loader.apply_translations(self, tr)
            except Exception:
                pass
            # Update language preference markers
            try:
                self.language_pref = lang_pref
            except Exception:
                pass
            self.language = lang_pref
            try:
                if hasattr(self, "save_preferences"):
                    self.save_preferences()
            except Exception:
                pass
            meta = tr.get("_meta", {}) if isinstance(tr, dict) else {}
            lang_name = (
                meta.get("name", lang_pref) if isinstance(meta, dict) else lang_pref
            )
            try:
                self.current_language = lang_name
            except Exception:
                pass
            log_i18n_level(
                self,
                "info",
                f"Langue appliquée: {lang_name}",
                f"Language applied: {lang_name}",
            )
        except Exception as e:
            log_i18n_level(
                self,
                "warning",
                f"Échec application de la langue: {e}",
                f"Failed to apply language: {e}",
            )
    else:
        log_i18n_level(
            self,
            "info",
            "Sélection de la langue annulée.",
            "Language selection cancelled.",
        )
