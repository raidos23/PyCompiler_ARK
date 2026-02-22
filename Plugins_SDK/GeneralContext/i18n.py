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

from typing import Any, Optional, Callable

_GLOBAL_TR: dict[str, Any] = {}
_GLOBAL_LANG: str = "en"
_PLUGIN_TR: dict[str, dict[str, Any]] = {}
_HANDLERS: set[Callable[[Any, dict], None]] = set()

_LANG_ALIASES = {
    "en-us": "en",
    "en_gb": "en",
    "en-uk": "en",
    "fr-fr": "fr",
    "pt-br": "pt-BR",
    "zh-cn": "zh-CN",
    "zh-hans": "zh-CN",
}


def normalize_language_code(code: Optional[str]) -> str:
    try:
        raw = (code or "").strip()
        if not raw:
            return "en"
        low = raw.lower().replace("_", "-")
        mapped = _LANG_ALIASES.get(low, raw)
        # prefer base lang when possible
        if "-" in mapped:
            return mapped.split("-", 1)[0]
        return mapped
    except Exception:
        return "en"


def resolve_language_code(gui, tr: Optional[dict]) -> str:
    code = None
    try:
        if isinstance(tr, dict):
            meta = tr.get("_meta", {})
            code = meta.get("code") if isinstance(meta, dict) else None
    except Exception:
        code = None
    if not code:
        try:
            pref = getattr(gui, "language_pref", getattr(gui, "language", "System"))
            if isinstance(pref, str) and pref != "System":
                code = pref
        except Exception:
            pass
    return normalize_language_code(code)


def set_translations(gui, tr: dict) -> None:
    global _GLOBAL_TR, _GLOBAL_LANG
    try:
        if isinstance(tr, dict):
            _GLOBAL_TR = dict(tr)
    except Exception:
        _GLOBAL_TR = {}
    try:
        _GLOBAL_LANG = resolve_language_code(gui, tr)
    except Exception:
        _GLOBAL_LANG = "en"


def get_translations() -> dict[str, Any]:
    return dict(_GLOBAL_TR) if isinstance(_GLOBAL_TR, dict) else {}


def get_language_code() -> str:
    return _GLOBAL_LANG or "en"


def register_plugin_translations(plugin_id: str, tr: dict) -> None:
    if not plugin_id:
        return
    if isinstance(tr, dict):
        _PLUGIN_TR[str(plugin_id)] = dict(tr)


def translate(plugin_id: str, key: str, default: Optional[str] = None) -> str:
    try:
        if plugin_id and plugin_id in _PLUGIN_TR:
            val = _PLUGIN_TR[plugin_id].get(key)
            if isinstance(val, str):
                return val
    except Exception:
        pass
    try:
        val2 = _GLOBAL_TR.get(key)
        if isinstance(val2, str):
            return val2
    except Exception:
        pass
    return default if default is not None else str(key)


def register_i18n_handler(fn: Callable[[Any, dict], None]) -> None:
    if callable(fn):
        _HANDLERS.add(fn)


def unregister_i18n_handler(fn: Callable[[Any, dict], None]) -> None:
    try:
        _HANDLERS.discard(fn)
    except Exception:
        pass


def apply_translations(gui, tr: dict) -> None:
    set_translations(gui, tr)
    for fn in list(_HANDLERS):
        try:
            fn(gui, tr)
        except Exception:
            continue


def load_plugin_language_file(plugin_package: str, code: str) -> dict:
    """Load language file for a plugin from its package's languages folder."""
    try:
        import importlib.resources as ilr
        import json

        lang_data = {}
        if not plugin_package:
            return {}
        lang_dir = "languages"
        normalized = normalize_language_code(code)
        candidates = [
            f"{normalized}.json",
            f"{normalized.lower()}.json",
            "en.json",
        ]
        for name in candidates:
            try:
                with ilr.open_text(plugin_package, f"{lang_dir}/{name}") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    lang_data.update(data)
                    break
            except Exception:
                continue
        return lang_data
    except Exception:
        return {}
