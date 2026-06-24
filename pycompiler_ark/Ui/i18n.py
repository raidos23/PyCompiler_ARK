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

from __future__ import annotations

import asyncio
import json
import locale
import os
import re
from typing import Any

import yaml

# Cache global pour les traductions chargées (évite les rechargements)
_TRANSLATION_CACHE: dict[str, dict[str, Any]] = {}
_LANGUAGES_CACHE: list[dict[str, str]] | None = None
_CACHE_LOCK = asyncio.Lock()
_LANGUAGE_EXTENSIONS = (".yml", ".yaml")
_ACTIVE_TRANSLATIONS: dict[str, Any] = {}


def _project_root() -> str:
    """Return project root path (sync, no blocking I/O)."""
    return os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir))


def _languages_dir() -> str:
    """Return `languages` directory path (sync, no blocking I/O)."""
    return os.path.abspath(os.path.join(_project_root(), "languages"))


def _load_language_data_sync(path: str) -> dict[str, Any] | None:
    """Charger un fichier de langue YAML."""
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else None


# Normalization helper must be pure (no I/O or system lookups)
# Leave "System" unresolved; callers must resolve system language asynchronously when needed.
async def normalize_lang_pref(pref: str | None) -> str:
    if pref is None:
        return "System"
    pref = str(pref).strip()
    if not pref:
        return "System"
    if pref.lower() in ("system", "auto", "default"):
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
    loc = (locale.getlocale()[0] or "").strip()
    if not loc:
        loc = (
            os.environ.get("LC_ALL")
            or os.environ.get("LC_MESSAGES")
            or os.environ.get("LANG")
            or ""
        ).strip()
    return "fr" if loc.lower().startswith(("fr", "fr_")) else "en"


def _load_language_file_sync(code: str) -> tuple[str | None, dict[str, Any] | None]:
    """Charger un fichier de langue YAML/JSON avec résolution souple.

    Returns (resolved_code, data) or (None, None) if not found/invalid.
    """
    raw = str(code or "").strip()
    if not raw:
        return None, None

    lang_dir = _languages_dir()
    if not os.path.isdir(lang_dir):
        return None, None

    candidates: list[str] = []

    def _add(candidate: str) -> None:
        cand = str(candidate).strip()
        if cand and cand not in candidates:
            candidates.append(cand)

    # Original and common separator variants
    _add(raw)
    _add(raw.replace("_", "-"))
    _add(raw.replace("-", "_"))

    # Case normalization for locale-like codes (pt-BR, zh-CN, en-US, ...)
    norm = raw.replace("_", "-")
    parts = [p for p in norm.split("-") if p]
    if len(parts) >= 2:
        _add(f"{parts[0].lower()}-{parts[1].upper()}")

    # Base language (e.g., fr_FR -> fr)
    base = raw.replace("_", "-").split("-")[0]
    _add(base)

    # Try direct file matches first
    for cand in candidates:
        for ext in _LANGUAGE_EXTENSIONS:
            fpath = os.path.join(lang_dir, f"{cand}{ext}")
            if os.path.isfile(fpath):
                data = _load_language_data_sync(fpath)
                if data is not None:
                    return os.path.splitext(os.path.basename(fpath))[0], data

    # Case-insensitive fallback
    files = [
        f
        for f in os.listdir(lang_dir)
        if os.path.splitext(f)[1].lower() in _LANGUAGE_EXTENSIONS
    ]
    lower_map = {f.lower(): f for f in files}
    for cand in candidates:
        for ext in _LANGUAGE_EXTENSIONS:
            target = f"{cand}{ext}".lower()
            if target in lower_map:
                fpath = os.path.join(lang_dir, lower_map[target])
                data = _load_language_data_sync(fpath)
                if data is not None:
                    return os.path.splitext(os.path.basename(fpath))[0], data

    return None, None


def _available_languages_sync() -> list[dict[str, str]]:
    langs: list[dict[str, str]] = []
    path = _languages_dir()
    if not os.path.isdir(path):
        return []
    preferred: dict[str, dict[str, str]] = {}
    for fname in sorted(os.listdir(path)):
        ext = os.path.splitext(fname)[1].lower()
        if ext not in _LANGUAGE_EXTENSIONS:
            continue
        default_code = os.path.splitext(fname)[0]
        fpath = os.path.join(path, fname)
        data = _load_language_data_sync(fpath)
        meta = data.get("_meta", {}) if isinstance(data, dict) else {}
        name = None
        code = None
        if isinstance(data, dict):
            name = data.get("name") or (meta.get("name") if isinstance(meta, dict) else None)
            code = data.get("code") or (meta.get("code") if isinstance(meta, dict) else None)
        entry = {
            "code": code or default_code,
            "name": name or default_code,
        }
        if entry["code"] not in preferred:
            preferred[entry["code"]] = entry
    langs = list(preferred.values())
    return langs


def _merge_translations(
    base: dict[str, Any], override: dict[str, Any] | None, code: str
) -> dict[str, Any]:
    """Merge translations with robust fallbacks.

    - Keep all keys from base (English).
    - Override with non-empty string values from override.
    - Preserve override metadata when valid.
    """
    merged: dict[str, Any] = dict(base) if isinstance(base, dict) else {}

    if isinstance(override, dict):
        for key, val in override.items():
            if key == "_meta":
                continue
            if isinstance(val, str) and val.strip():
                merged[key] = val
        if isinstance(override.get("_meta"), dict):
            merged["_meta"] = dict(override.get("_meta", {}))

    # Ensure metadata is normalized and consistent
    return _normalize_translation_meta(merged, code)


def set_active_translations(tr: dict[str, Any] | None) -> None:
    """Définit le catalogue actif utilisé par l'API publique `translate()`."""
    global _ACTIVE_TRANSLATIONS
    _ACTIVE_TRANSLATIONS = dict(tr) if isinstance(tr, dict) else {}


def get_active_translations() -> dict[str, Any]:
    """Retourne le catalogue actif courant."""
    return dict(_ACTIVE_TRANSLATIONS) if isinstance(_ACTIVE_TRANSLATIONS, dict) else {}


def translate(domain: object | None, key: str, default: str | None = None) -> str:
    """Retourne la traduction active pour une clé donnée.

    `domain` est conservé pour garder la même signature que les engines et les plugins.
    """
    tr = get_active_translations()
    if isinstance(tr, dict):
        value = tr.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return default if default is not None else str(key)


def _object_name(obj: Any) -> str:
    try:
        name = getattr(obj, "objectName", lambda: "")()
        if isinstance(name, str):
            return name.strip()
    except Exception:
        pass
    return ""


# Public async Plugins with real-time caching and error handling


async def resolve_system_language() -> str:
    """Resolve system language in real time with safe fallbacks."""
    try:
        return await asyncio.to_thread(_resolve_system_language_sync)
    except Exception:
        return "en"


async def available_languages() -> list[dict[str, str]]:
    """Return available languages with thread-safe caching."""
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
    """Load translations in real time with caching and robust fallbacks."""
    try:
        # Normaliser la préférence de langue
        code = await normalize_lang_pref(lang_pref)

        # Résoudre "System" vers la langue réelle
        if code == "System":
            code = await resolve_system_language()

        # Vérifier le cache d'abord (très rPluginsde)
        if code in _TRANSLATION_CACHE:
            return _TRANSLATION_CACHE[code]

        # Charger depuis le disque en thread pool (avec résolution flexible)
        resolved_code, data = await asyncio.to_thread(_load_language_file_sync, code)

        # Charger l'anglais depuis les fichiers de langue comme base commune
        _, base_en = await asyncio.to_thread(_load_language_file_sync, "en")
        base_catalog = base_en if isinstance(base_en, dict) else {}

        # Si un code résolu différent est déjà en cache, le réutiliser
        if resolved_code and resolved_code in _TRANSLATION_CACHE:
            return _TRANSLATION_CACHE[resolved_code]

        # Merge à partir du catalogue anglais chargé sur disque
        merged = _merge_translations(
            base_catalog, data if isinstance(data, dict) else None, resolved_code or code
        )

        # Mettre en cache de manière thread-safe (code demandé + code résolu)
        async with _CACHE_LOCK:
            _TRANSLATION_CACHE[code] = merged
            if resolved_code:
                _TRANSLATION_CACHE[resolved_code] = merged

        return merged

    except Exception:
        # Fallback ultime: retourner un catalogue vide avec métadonnées normalisées
        return _normalize_translation_meta({}, "en")


def _normalize_translation_meta(data: dict[str, Any], code: str) -> dict[str, Any]:
    """Normalize translation metadata (sync, no I/O)."""
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
    """Return language display name for a code (sync, no I/O)."""
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
    """Clear translation caches (useful for tests and reloads)."""
    global _TRANSLATION_CACHE, _LANGUAGES_CACHE

    try:
        async with _CACHE_LOCK:
            _TRANSLATION_CACHE.clear()
            _LANGUAGES_CACHE = None
    except Exception:
        pass


def get_current_language_sync() -> str:
    """Return current language from user preferences (sync)."""
    try:
        # Absolute import to avoid relative-import issues outside Core package
        from pycompiler_ark.Ui.PreferencesManager import PREFS_FILE

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


def _is_french_token(value: object | None) -> bool:
    try:
        if value is None:
            return False
        val = str(value).strip().lower()
    except Exception:
        return False
    if not val:
        return False
    if val in ("fr", "français", "francais", "french"):
        return True
    return val.startswith("fr-") or val.startswith("fr_") or val.startswith("fr")


def is_french_language(gui: object | None = None) -> bool:
    """Return True if the effective language is French; otherwise False.

    Rule enforced: French only when explicitly selected (or system language is French).
    Any other language must fall back to English.
    """
    try:
        if gui is not None:
            for attr in ("language_pref", "language"):
                try:
                    pref = getattr(gui, attr, None)
                except Exception:
                    pref = None
                if pref is None:
                    continue
                try:
                    pref_s = str(pref).strip()
                except Exception:
                    pref_s = ""
                if not pref_s:
                    continue
                if pref_s.lower() in ("system", "auto", "default"):
                    try:
                        return _is_french_token(get_current_language_sync())
                    except Exception:
                        return False
                return _is_french_token(pref_s)

            try:
                tr = getattr(gui, "_tr", None)
                if isinstance(tr, dict):
                    meta = tr.get("_meta", {})
                    if isinstance(meta, dict):
                        if _is_french_token(meta.get("code")):
                            return True
                        if _is_french_token(meta.get("name")):
                            return True
            except Exception:
                pass

            try:
                cur = getattr(gui, "current_language", None)
                if _is_french_token(cur):
                    return True
            except Exception:
                pass
        return _is_french_token(get_current_language_sync())
    except Exception:
        return False


def tr_fr_en(gui: object | None, fr: str, en: str) -> str:
    """Force FR/EN rule: French only if language is French, else English."""
    try:
        return fr if is_french_language(gui) else en
    except Exception:
        return en


# -------------------------------
# i18n-aware logging helpers
# (moved from pycompiler_ark.engine_sdk.utils)
# -------------------------------

_REDACT_PATTERNS = [
    re.compile(r"(password\s*[:=]\s*)([^\s]+)", re.IGNORECASE),
    re.compile(r"(authorization\s*[:]\s*bearer\s+)([A-Za-z0-9\-_.]+)", re.IGNORECASE),
    re.compile(r"(token\s*[:=]\s*)([A-Za-z0-9\-_.]{12,})", re.IGNORECASE),
]


def redact_secrets(text: str) -> str:
    """Return text with obvious secrets masked to avoid log leakage."""
    if not text:
        return text
    redacted = str(text)
    try:
        for pat in _REDACT_PATTERNS:
            redacted = pat.sub(lambda m: m.group(1) + "<redacted>", redacted)
    except Exception:
        pass
    return redacted


def clamp_text(text: str, *, max_len: int = 10000) -> str:
    """Clamp long text to max_len characters (suffix with …)."""
    if text is None:
        return ""
    s = str(text)
    return s if len(s) <= max_len else (s[: max_len - 1] + "…")


def tr(gui: Any, fr: str, en: str) -> str:
    """Robust translator wrapper using the host GUI translator when available."""
    try:
        fn = getattr(gui, "tr", None)
        if callable(fn):
            return fn(fr, en)
    except Exception:
        pass
    return tr_fr_en(gui, fr, en)


essential_log_max_len = 10000


def safe_log(gui: Any, text: str, *, redact: bool = True, clamp: bool = True) -> None:
    """Append text to GUI log safely (or print), with optional redaction and clamping."""
    try:
        msg = str(text)
        if redact:
            msg = redact_secrets(msg)
        if clamp:
            msg = clamp_text(msg, max_len=essential_log_max_len)
        if hasattr(gui, "log") and getattr(gui, "log") is not None:
            try:
                gui.log.append(msg)
                return
            except Exception:
                pass
        print(msg)
    except Exception:
        try:
            print(text)
        except Exception:
            pass


_LOG_LEVEL_LABELS = {
    "info": "INFO",
    "warning": "WARN",
    "error": "ERROR",
    "success": "SUCCESS",
    "state": "STATE",
}

_LOG_EMOJI_PREFIXES = [
    "✅",
    "⚠️",
    "❌",
    "ℹ️",
    "❗",
    "⏩",
    "📝",
    "📋",
    "🔍",
    "🔧",
    "🔨",
    "➡️",
    "📦",
    "🗑️",
    "🧩",
    "🔌",
    "⏹️",
    "⏱️",
]


def _strip_emoji_prefix(text: str) -> str:
    try:
        s = str(text)
    except Exception:
        return text
    for emo in _LOG_EMOJI_PREFIXES:
        if s.startswith(emo):
            s = s[len(emo) :]
            break
    return s.lstrip()


_LOG_LEVEL_RICH = {
    "info": "cyan",
    "warning": "yellow",
    "error": "red",
    "success": "green",
    "state": "blue",
}

_LOG_LEVEL_COLORAMA = {
    "info": "CYAN",
    "warning": "YELLOW",
    "error": "RED",
    "success": "GREEN",
    "state": "BLUE",
}

_LOG_LEVEL_QT_COLORS = {
    "info": "#1E88E5",
    "warning": "#EF6C00",
    "error": "#D32F2F",
    "success": "#2E7D32",
    "state": "#00897B",
    "debug": "#546E7A",
}

_RICH_CONSOLE = None
_COLORAMA_READY = False


def _get_rich_console():
    global _RICH_CONSOLE
    if _RICH_CONSOLE is None:
        from rich.console import Console  # type: ignore

        _RICH_CONSOLE = Console()
    return _RICH_CONSOLE


def _console_log(level: str, label: str, message: str) -> None:
    # Prefer rich when available for consistent styling.
    try:
        console = _get_rich_console()
        style = _LOG_LEVEL_RICH.get(level, "white")
        console.print(f"[{style}]{label}[/] {message}")
        return
    except Exception:
        pass

    # Fallback to colorama for basic ANSI colors.
    try:
        from colorama import Fore, Style, init  # type: ignore

        global _COLORAMA_READY
        if not _COLORAMA_READY:
            init(autoreset=True)
            _COLORAMA_READY = True

        color_name = _LOG_LEVEL_COLORAMA.get(level)
        color = getattr(Fore, color_name, "")
        if color:
            print(f"{color}{label}{Style.RESET_ALL} {message}")
        else:
            print(f"{label} {message}")
        return
    except Exception:
        pass

    print(f"{label} {message}")


def _append_gui_log(gui: Any, level: str, label: str, msg: str) -> bool:
    """Append a log line to the GUI log, with color when possible."""
    try:
        log = getattr(gui, "log", None)
    except Exception:
        return False
    if log is None:
        return False

    line = f"[{label}] {msg}"

    # List-backed logs (tests)
    try:
        if isinstance(log, list):
            log.append(line)
            return True
    except Exception:
        pass

    # QTextEdit with rich formatting
    try:
        if hasattr(log, "textCursor") and callable(log.textCursor):
            try:
                from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor
            except Exception:
                return False
            cursor = log.textCursor()
            cursor.movePosition(QTextCursor.End)
            fmt = QTextCharFormat()
            color = _LOG_LEVEL_QT_COLORS.get(level)
            if color:
                fmt.setForeground(QColor(color))
            cursor.insertText(line, fmt)
            cursor.insertText("\n")
            try:
                log.setTextCursor(cursor)
                log.ensureCursorVisible()
            except Exception:
                pass
            return True
    except Exception:
        pass

    # QPlainTextEdit / generic append
    try:
        if hasattr(log, "appendPlainText") and callable(log.appendPlainText):
            log.appendPlainText(line)
            return True
    except Exception:
        pass

    try:
        if hasattr(log, "append") and callable(log.append):
            log.append(line)
            return True
    except Exception:
        pass

    return False


def log_with_level(
    gui: Any,
    level: str,
    message: str,
    *,
    redact: bool = True,
    clamp: bool = True,
) -> None:
    """Append a level-tagged message to GUI log or print with colors in console."""
    try:
        lvl = str(level).lower() if level is not None else "info"
    except Exception:
        lvl = "info"
    label = _LOG_LEVEL_LABELS.get(lvl, str(level).upper())

    msg = str(message) if message is not None else ""
    if redact:
        msg = redact_secrets(msg)
    if clamp:
        msg = clamp_text(msg, max_len=essential_log_max_len)
    msg = _strip_emoji_prefix(msg)

    try:
        if _append_gui_log(gui, lvl, label, msg):
            return
    except Exception:
        pass

    _console_log(lvl, label, msg)


def log_i18n(
    gui: Any,
    fr: str,
    en: str,
    level: str | None = None,
    *,
    redact: bool = True,
    clamp: bool = True,
) -> None:
    """Translate and log a message, automatically inferring the level from emojis if not provided."""
    lvl = level
    if lvl is None:
        lvl = "info"
        fr_str = str(fr)
        en_str = str(en)
        for emo, lv in (
            ("❌", "error"),
            ("⚠️", "warning"),
            ("❗", "warning"),
            ("✅", "success"),
            ("ℹ️", "info"),
            ("⏩", "state"),
            ("📝", "state"),
            ("📋", "state"),
            ("🔍", "state"),
            ("🔧", "state"),
            ("🔨", "state"),
            ("➡️", "state"),
            ("📦", "state"),
            ("🗑️", "state"),
        ):
            if fr_str.startswith(emo) or en_str.startswith(emo):
                lvl = lv
                break

    fr2 = _strip_emoji_prefix(fr)
    en2 = _strip_emoji_prefix(en)
    msg = tr(gui, fr2, en2)
    log_with_level(gui, lvl, msg, redact=redact, clamp=clamp)


def log_i18n_level(
    gui: Any,
    level: str,
    fr: str,
    en: str,
    *,
    redact: bool = True,
    clamp: bool = True,
) -> None:
    """Translate then log a level-tagged message."""
    log_i18n(gui, fr, en, level, redact=redact, clamp=clamp)


def i18n_synchro(self, lang_pref: str, tr: dict[str, Any]) -> str:
    """Synchronise la langue active sur l'UI, les engines et les plugins."""
    meta = tr.get("_meta", {}) if isinstance(tr, dict) else {}
    lang_name = meta.get("name", lang_pref) if isinstance(meta, dict) else lang_pref

    setattr(self, "_tr", tr)
    set_active_translations(tr)

    self.current_language = lang_name
    self.language = lang_pref
    self.language_pref = lang_pref

    _apply_main_app_translations(self, tr)

    from pycompiler_ark.Ui.Gui.IdeLikeGui.connections import (
        _retranslate_ide_like_actions,
    )

    _retranslate_ide_like_actions(self)

    import pycompiler_ark.Core.engine as engines_loader

    engines_loader.registry.apply_translations(self, tr)

    from pycompiler_ark.Plugins_SDK.GeneralContext import (
        apply_translations as sdk_apply_tr,
    )

    sdk_apply_tr(self, tr)

    for cb in getattr(self, "_language_refresh_callbacks", []) or []:
        cb()

    if hasattr(self, "save_preferences"):
        self.save_preferences()

    self.current_language = lang_name

    log_i18n_level(
        self,
        "info",
        f"Langue appliquée : {lang_name}",
        f"Language applied: {lang_name}",
    )

    return str(lang_name)


def apply_language(self, lang_display: str) -> None:
    """Apply selected language through centralized i18n flow."""
    from pycompiler_ark.Ui.Gui.Globals import _run_coro_async

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
        i18n_synchro(self, lang_display, tr)

    _run_coro_async(_do(), _on_result, ui_owner=self)


def _apply_main_app_translations(self, tr: dict[str, object]) -> None:
    def _prop(obj: Any, name: str) -> Any:
        if hasattr(obj, "property"):
            val = obj.property(name)
            if val is not None:
                return val
        return getattr(obj, name, None)

    def _is_system_value(value: Any) -> bool:
        return str(value).strip().lower() == "system"

    def _binding_for_name(name: str) -> str:
        if not name:
            return ""
        if name in tr:
            return name
        for prefix in ("btn_", "action_", "tab_", "lbl_", "label_"):
            if name.startswith(prefix):
                key = name[len(prefix):]
                if key in tr:
                    return key
        legacy = {
            "btn_acasl_loader": "bc_loader",
            "btn_advanced_cfg_btn": "advanced_config",
            "btn_venv_button": "venv_button",
        }
        if name in legacy:
            return legacy[name]
        return name

    def _tooltip_for_name(name: str) -> str:
        if not name:
            return ""
        if name.startswith("btn_"):
            candidate = f"tt_{name[4:]}"
            if candidate in tr:
                return candidate
        candidate = f"tt_{name}"
        if candidate in tr:
            return candidate
        if name.startswith("opt_"):
            candidate = f"tt_{name}"
            if candidate in tr:
                return candidate
        legacy_tooltips = {
            "btn_acasl_loader": "tt_bc_loader",
            "btn_activity_deps": "tt_suggest_deps",
            "btn_more_actions": "tt_more_actions",
        }
        if name in legacy_tooltips:
            return legacy_tooltips[name]
        return ""

    def _placeholder_for_name(name: str) -> str:
        if not name:
            return ""
        candidate = f"{name}_placeholder"
        if candidate in tr:
            return candidate
        for prefix in ("btn_", "action_", "tab_", "lbl_", "label_"):
            if name.startswith(prefix):
                candidate = f"{name[len(prefix):]}_placeholder"
                if candidate in tr:
                    return candidate
        legacy_placeholders = {
            "file_filter_input": "file_filter_placeholder",
        }
        if name in legacy_placeholders:
            return legacy_placeholders[name]
        return ""

    def _iter_objects(root: Any):
        stack = [root]
        seen: set[int] = set()
        while stack:
            obj = stack.pop()
            if obj is None:
                continue
            oid = id(obj)
            if oid in seen:
                continue
            seen.add(oid)
            yield obj
            children = list(obj.children())
            for child in reversed(children):
                stack.append(child)

    def _apply_text(obj: Any, key: str, default: str | None = None) -> None:
        if hasattr(obj, "setText"):
            value = translate(self.id, key, default)
            if isinstance(value, str) and value:
                obj.setText(value)

    def _apply_tooltip(obj: Any, key: str, default: str | None = None) -> None:
        if hasattr(obj, "setToolTip"):
            value = translate(self.id, key, default)
            if isinstance(value, str) and value:
                obj.setToolTip(value)

    def _apply_placeholder(obj: Any, key: str, default: str | None = None) -> None:
        if hasattr(obj, "setPlaceholderText"):
            value = translate(self.id, key, default)
            if isinstance(value, str) and value:
                obj.setPlaceholderText(value)

    def _apply_tab_text(obj: Any, key: str, default: str | None = None) -> None:
        parent = getattr(obj, "parent", lambda: None)()
        while parent is not None:
            if hasattr(parent, "indexOf") and hasattr(parent, "setTabText"):
                idx = parent.indexOf(obj)
                if idx >= 0:
                    value = translate(self.id, key, default)
                    if isinstance(value, str) and value:
                        parent.setTabText(idx, value)
                break
            parent = getattr(parent, "parent", lambda: None)()

    for obj in _iter_objects(self):
        name = _object_name(obj)
        text_key = _prop(obj, "i18n_text_key") or _binding_for_name(name)
        if text_key:
            system_key = _prop(obj, "i18n_text_system_key")
            system_attr = _prop(obj, "i18n_system_attr")
            format_attr = _prop(obj, "i18n_format_attr")
            none_key = _prop(obj, "i18n_none_key")
            current = obj.text() if hasattr(obj, "text") else None

            chosen_key = str(text_key)

            if system_key and system_attr and _is_system_value(getattr(self, str(system_attr), None)):
                chosen_key = str(system_key)

            if format_attr:
                ctx = getattr(self, str(format_attr), None)
                if ctx:
                    value = translate(
                        self.id, chosen_key, current if isinstance(current, str) else None
                    )
                    if isinstance(value, str) and value:
                        obj.setText(value.replace("{path}", str(ctx)))
                elif none_key:
                    _apply_text(obj, str(none_key), current if isinstance(current, str) else None)
                continue

            _apply_text(obj, chosen_key, current if isinstance(current, str) else None)

        tooltip_key = _prop(obj, "i18n_tooltip_key") or _tooltip_for_name(name)
        if tooltip_key:
            current = obj.toolTip() if hasattr(obj, "toolTip") else None
            _apply_tooltip(obj, str(tooltip_key), current if isinstance(current, str) else None)

        placeholder_key = _prop(obj, "i18n_placeholder_key") or _placeholder_for_name(name)
        if placeholder_key:
            current = obj.placeholderText() if hasattr(obj, "placeholderText") else None
            _apply_placeholder(
                obj, str(placeholder_key), current if isinstance(current, str) else None
            )

        tab_key = _prop(obj, "i18n_tab_key") or (name if name.startswith("tab_") else "")
        if tab_key:
            current = obj.text() if hasattr(obj, "text") else None
            _apply_tab_text(obj, str(tab_key), current if isinstance(current, str) else None)


# LANGUAGE DIALOG and all ARK language's system translations propagation
def show_language_dialog(self):
    from PySide6.QtWidgets import QInputDialog

    langs = asyncio.run(available_languages())
    # Build options list with 'System' at top
    options = ["System"] + [str(x.get("name", x.get("code", ""))) for x in langs]
    # Determine current index
    current_pref = getattr(self, "language", "System")
    if current_pref == "System":
        start_index = 0
    else:
        codes = [str(x.get("code", "")) for x in langs]
        start_index = 1 + codes.index(current_pref) if current_pref in codes else 0
    title = translate(self.id, "choose_language_title", getattr(self, "windowTitle", lambda: "")())
    label = translate(
        self.id,
        "choose_language_label",
        getattr(getattr(self, "select_lang", None), "text", lambda: "")(),
    )
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
        tr = asyncio.run(get_translations(lang_pref))
        i18n_synchro(self, lang_pref, tr)
    else:
        log_i18n_level(
            self,
            "info",
            "Sélection de la langue annulée.",
            "Language selection cancelled.",
        )
