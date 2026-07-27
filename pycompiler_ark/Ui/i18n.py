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

# Global cache for loaded translations (avoids reloads)
_TRANSLATION_CACHE: dict[str, dict[str, Any]] = {}
_LANGUAGES_CACHE: list[dict[str, str]] | None = None
_CACHE_LOCK = asyncio.Lock()
_LANGUAGE_EXTENSIONS = (".yml", ".yaml")
_ACTIVE_TRANSLATIONS: dict[str, Any] = {}


def _project_root() -> str:
    """Return project root path (sync, no blocking I/O)."""
    return os.path.abspath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir)
    )


def _languages_dir() -> str:
    """Return `languages` directory path (sync, no blocking I/O)."""
    return os.path.abspath(os.path.join(_project_root(), "languages"))


def _load_language_data_sync(path: str) -> dict[str, Any] | None:
    """Load a YAML language file."""
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


def _load_language_file_sync(
    code: str,
) -> tuple[str | None, dict[str, Any] | None]:
    """Load a YAML/JSON language file with flexible resolution.

    Returns (resolved_code, data) or (None, None) if not found/invalid."""
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
            name = data.get("name") or (
                meta.get("name") if isinstance(meta, dict) else None
            )
            code = data.get("code") or (
                meta.get("code") if isinstance(meta, dict) else None
            )
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
    """Defines the active catalog used by the public API `translate()`."""
    global _ACTIVE_TRANSLATIONS
    _ACTIVE_TRANSLATIONS = dict(tr) if isinstance(tr, dict) else {}


def get_active_translations() -> dict[str, Any]:
    """Returns the current active catalog."""
    return (
        dict(_ACTIVE_TRANSLATIONS)
        if isinstance(_ACTIVE_TRANSLATIONS, dict)
        else {}
    )


def translate(
    domain: object | None, key: str, default: str | None = None
) -> str:
    """Returns the active translation for a given key.

    `domain` is preserved to keep the same signature as engines and plugins."""
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
        # Check cache first (rPluginsde)
        if _LANGUAGES_CACHE is not None:
            return _LANGUAGES_CACHE

        # Load from disk in thread pool
        langs = await asyncio.to_thread(_available_languages_sync)

        # Caching thread-safely
        async with _CACHE_LOCK:
            _LANGUAGES_CACHE = langs

        return langs
    except Exception:
        # Fallback: return at least English
        return [{"code": "en", "name": "English"}]


async def get_translations(lang_pref: str | None) -> dict[str, Any]:
    """Load translations in real time with caching and robust fallbacks."""
    try:
        # Standardize language preference
        code = await normalize_lang_pref(lang_pref)

        # Résoudre "System" vers la langue réelle
        if code == "System":
            code = await resolve_system_language()

        # Check cache first (very rPluginsde)
        if code in _TRANSLATION_CACHE:
            return _TRANSLATION_CACHE[code]

        # Load from disk in thread pool (with flexible resolution)
        resolved_code, data = await asyncio.to_thread(
            _load_language_file_sync, code
        )

        # Load English from language files as common base
        _, base_en = await asyncio.to_thread(_load_language_file_sync, "en")
        base_catalog = base_en if isinstance(base_en, dict) else {}

        # Si un code résolu différent est déjà en cache, le réutiliser
        if resolved_code and resolved_code in _TRANSLATION_CACHE:
            return _TRANSLATION_CACHE[resolved_code]

        # Merge from English catalog loaded on disk
        merged = _merge_translations(
            base_catalog,
            data if isinstance(data, dict) else None,
            resolved_code or code,
        )

        # Cache thread-safely (requested code + resolved code)
        async with _CACHE_LOCK:
            _TRANSLATION_CACHE[code] = merged
            if resolved_code:
                _TRANSLATION_CACHE[resolved_code] = merged

        return merged

    except Exception:
        # Fallback ultime: retourner un catalogue vide avec métadonnées normalisées
        return _normalize_translation_meta({}, "en")


def _normalize_translation_meta(
    data: dict[str, Any], code: str
) -> dict[str, Any]:
    """Normalize translation metadata (sync, no I/O)."""
    try:
        if not isinstance(data, dict):
            data = {}

        # Extract existing metadata
        top_name = data.get("name") if isinstance(data, dict) else None
        top_code = data.get("code") if isinstance(data, dict) else None
        meta_in = data.get("_meta", {}) if isinstance(data, dict) else {}

        if not isinstance(meta_in, dict):
            meta_in = {}

        # Building final metadata with fallbacks
        final_code = top_code or meta_in.get("code") or code or "en"

        final_name = (
            top_name or meta_in.get("name") or _get_language_name(final_code)
        )

        # Update metadata
        data["_meta"] = {
            "code": final_code,
            "name": final_name,
        }

        return data

    except Exception:
        # On error, return a valid minimal structure
        return {
            "_meta": {
                "code": code or "en",
                "name": _get_language_name(code or "en"),
            }
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
        # Return uppercase code as fallback
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
        from .PreferencesManager import PREFS_FILE

        if os.path.isfile(PREFS_FILE):
            with open(PREFS_FILE, encoding="utf-8") as f:
                prefs = json.load(f)
            lang_pref = prefs.get(
                "language_pref", prefs.get("language", "System")
            )
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
    return (
        val.startswith("fr-") or val.startswith("fr_") or val.startswith("fr")
    )


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
    re.compile(
        r"(authorization\s*[:]\s*bearer\s+)([A-Za-z0-9\-_.]+)", re.IGNORECASE
    ),
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


def i18n_synchro(self, lang_pref: str, tr: dict[str, Any]) -> str:
    """Synchronizes the active language on the UI, engines and plugins."""
    meta = tr.get("_meta", {}) if isinstance(tr, dict) else {}
    lang_name = (
        meta.get("name", lang_pref) if isinstance(meta, dict) else lang_pref
    )

    setattr(self, "_tr", tr)
    set_active_translations(tr)

    self.current_language = lang_name
    self.language = lang_pref
    self.language_pref = lang_pref

    _apply_main_app_translations(self, tr)

    from .Gui.IdeLikeGui.connections import (
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

    try:
        from pycompiler_ark.Ui import output

        output.info(
            (
                f"Langue appliquée : {lang_name}",
                f"Language applied: {lang_name}",
            ),
            gui=self,
        )
    except Exception:
        pass

    return str(lang_name)


def apply_language(self, lang_display: str) -> None:
    """Apply selected language through centralized i18n flow."""
    from .Gui.Globals import _run_coro_async

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
                key = name[len(prefix) :]
                if key in tr:
                    return key
        # Do not fall back to the object name: content widgets like QTextEdit
        # named "log" have setText() but no text(), so translate() would write
        # the name into the widget permanently.
        return ""

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
        return ""

    def _placeholder_for_name(name: str) -> str:
        if not name:
            return ""
        candidate = f"{name}_placeholder"
        if candidate in tr:
            return candidate
        for prefix in ("btn_", "action_", "tab_", "lbl_", "label_"):
            if name.startswith(prefix):
                candidate = f"{name[len(prefix) :]}_placeholder"
                if candidate in tr:
                    return candidate
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

    def _is_content_edit(obj: Any) -> bool:
        """True for multiline editors that must not receive i18n setText()."""
        cls_name = type(obj).__name__
        return cls_name in ("QTextEdit", "QPlainTextEdit")

    def _apply_text(obj: Any, key: str, default: str | None = None) -> None:
        if _is_content_edit(obj):
            return
        if hasattr(obj, "setText"):
            value = translate(self.id, key, default)
            if isinstance(value, str) and value:
                obj.setText(value)

    def _apply_tooltip(obj: Any, key: str, default: str | None = None) -> None:
        if hasattr(obj, "setToolTip"):
            value = translate(self.id, key, default)
            if isinstance(value, str) and value:
                obj.setToolTip(value)

    def _apply_placeholder(
        obj: Any, key: str, default: str | None = None
    ) -> None:
        if hasattr(obj, "setPlaceholderText"):
            value = translate(self.id, key, default)
            if isinstance(value, str) and value:
                obj.setPlaceholderText(value)

    def _apply_tab_text(
        obj: Any, key: str, default: str | None = None
    ) -> None:
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
        if text_key and not _is_content_edit(obj):
            system_key = _prop(obj, "i18n_text_system_key")
            system_attr = _prop(obj, "i18n_system_attr")
            format_attr = _prop(obj, "i18n_format_attr")
            none_key = _prop(obj, "i18n_none_key")
            current = obj.text() if hasattr(obj, "text") else None

            chosen_key = str(text_key)

            if (
                system_key
                and system_attr
                and _is_system_value(getattr(self, str(system_attr), None))
            ):
                chosen_key = str(system_key)

            if format_attr:
                ctx = getattr(self, str(format_attr), None)
                if ctx:
                    value = translate(
                        self.id,
                        chosen_key,
                        current if isinstance(current, str) else None,
                    )
                    if isinstance(value, str) and value:
                        obj.setText(value.replace("{path}", str(ctx)))
                elif none_key:
                    _apply_text(
                        obj,
                        str(none_key),
                        current if isinstance(current, str) else None,
                    )
                continue

            _apply_text(
                obj, chosen_key, current if isinstance(current, str) else None
            )

        tooltip_key = _prop(obj, "i18n_tooltip_key") or _tooltip_for_name(name)
        if tooltip_key:
            current = obj.toolTip() if hasattr(obj, "toolTip") else None
            _apply_tooltip(
                obj,
                str(tooltip_key),
                current if isinstance(current, str) else None,
            )

        placeholder_key = _prop(
            obj, "i18n_placeholder_key"
        ) or _placeholder_for_name(name)
        if placeholder_key:
            current = (
                obj.placeholderText()
                if hasattr(obj, "placeholderText")
                else None
            )
            _apply_placeholder(
                obj,
                str(placeholder_key),
                current if isinstance(current, str) else None,
            )

        tab_key = _prop(obj, "i18n_tab_key") or (
            name if name.startswith("tab_") else ""
        )
        if tab_key:
            current = obj.text() if hasattr(obj, "text") else None
            _apply_tab_text(
                obj,
                str(tab_key),
                current if isinstance(current, str) else None,
            )
