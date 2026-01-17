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

# Built-in fallback for English if language files are missing
FALLBACK_EN: dict[str, Any] = {
    "name": "English",
    "code": "en",
    "_meta": {"code": "en", "name": "English"},
    "select_folder": "📁 Workspace",
    "select_files": "📋 Files",
    "build_all": "🚀 Build",
    "export_config": "💾 Export config",
    "import_config": "📥 Import config",
    "cancel_all": "⛔ Cancel",
    "suggest_deps": "🔎 Analyze dependencies",
    "help": "❓ Help",
    "help_title": "Help",
    "help_text": "<b>PyCompiler ARK++ — Quick Help</b><br><ul><li>1) Select the Workspace and add your .py files.</li><li>2) Configure pre‑compile plugins via <b>API Loader</b> (BCASL).</li><li>3) Configure options in the <b>PyInstaller</b>, <b>Nuitka</b> or <b>CX_Freeze</b> tab.</li><li>4) Click <b>Build</b> and follow the logs.</li></ul><b>Notes</b><br><ul><li>When a build starts, all action controls are disabled (including API Loader) until it finishes or is canceled.</li><li>Pre‑compilation (BCASL) completes before compilation.</li><li>A <i>venv</i> can be created automatically; requirements.txt is installed if present; tools are installed into the venv as needed.</li><li>API‑initiated workspace changes are auto‑applied; running builds are canceled before switching.</li></ul><b>License</b>: Apache-2.0 — <a href='https://www.apache.org/licenses/LICENSE-2.0'>apache.org/licenses/LICENSE-2.0</a><br><b>Author</b>: Ague Samuel Amen<br>© 2026 Ague Samuel Amen",
    "show_stats": "📊 Statistics",
    "select_lang": "Choose language",
    "venv_button": "Choose venv folder manually",
    "label_workspace_section": "1. Select workspace folder",
    "venv_label": "venv selected: None",
    "label_folder": "No folder selected",
    "label_files_section": "2. Files to build",
    "btn_remove_file": "🗑️ Remove selected file",
    "label_logs_section": "Build logs",
    "choose_language_title": "Choose language",
    "choose_language_label": "Language:",
    "choose_language_system": "System",
    "choose_language_system_button": "Choose language (System)",
    "choose_language_button": "Choose language",
    "select_theme": "Choose theme",
    "choose_theme_button": "Choose theme",
    "choose_theme_system_button": "Choose theme (System)",
    "tt_select_folder": "Select the workspace directory containing your Python files.",
    "tt_select_files": "Add Python files manually to the build list.",
    "tt_build_all": "Start building all selected files.",
    "tt_export_config": "Export the current configuration to a JSON file.",
    "tt_import_config": "Import a configuration from a JSON file.",
    "tt_cancel_all": "Cancel all ongoing builds.",
    "tt_remove_file": "Remove the selected file(s) from the list.",
    "tt_help": "Open help and information about the software.",
    "tt_bc_loader": "Configure API (BCASL) plugins to run before compilation.",
    "tt_venv_button": "Manually select a venv directory to use for compilation.",
    "tt_suggest_deps": "Analyze the project for missing Python dependencies.",
    "tt_show_stats": "Show build statistics (time, number of files, memory).",
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


# Public async API with real-time caching and error handling


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
        # Vérifier le cache d'abord (rapide)
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

        # Vérifier le cache d'abord (très rapide)
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
        from .preferences import PREFS_FILE

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
