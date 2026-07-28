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

import os
from pathlib import Path
from typing import Any, Callable, Optional

from ...Core.globals import (
    _GLOBAL_LANG,
    _GLOBAL_TR,
    _LANG_ALIASES,
    INTERNAL_PLUGINS_DIR,
)

try:
    import yaml
except ImportError:
    yaml = None


_PLUGIN_TR: dict[str, dict[str, Any]] = {}
_HANDLERS: set[Callable[[Any, dict], None]] = set()


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
            pref = getattr(
                gui, "language_pref", getattr(gui, "language", "System")
            )
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
    try:
        _load_all_plugin_languages(_GLOBAL_LANG)
    except Exception:
        pass


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
        if plugin_id:
            if plugin_id in _PLUGIN_TR:
                val = _PLUGIN_TR[plugin_id].get(key)
                if isinstance(val, str):
                    return val
            low = str(plugin_id).lower()
            if low in _PLUGIN_TR:
                val = _PLUGIN_TR[low].get(key)
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


def _object_name(obj: Any) -> str:
    try:
        name = getattr(obj, "objectName", lambda: "")()
        if isinstance(name, str):
            return name.strip()
    except Exception:
        pass
    return ""


def refresh_widget_translations(root: Any, plugin_id: str) -> None:
    """Apply the active plugin catalog to an existing widget tree."""

    def _iter_objects(root_obj: Any):
        stack = [root_obj]
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
            try:
                children = list(obj.children())
            except Exception:
                children = []
            for child in reversed(children):
                stack.append(child)

    def _prop(obj: Any, name: str) -> str:
        try:
            value = getattr(obj, name, None)
            if isinstance(value, str) and value.strip():
                return value.strip()
        except Exception:
            pass
        try:
            value = obj.property(name) if hasattr(obj, "property") else None
            if isinstance(value, str) and value.strip():
                return value.strip()
        except Exception:
            pass
        return ""

    def _apply_text(obj: Any, key: str, default: str | None = None) -> None:
        if not hasattr(obj, "setText"):
            return
        value = translate(plugin_id, key, default)
        if isinstance(value, str) and value:
            obj.setText(value)

    def _apply_title(obj: Any, key: str, default: str | None = None) -> None:
        if not hasattr(obj, "setTitle"):
            return
        value = translate(plugin_id, key, default)
        if isinstance(value, str) and value:
            obj.setTitle(value)

    def _apply_placeholder(
        obj: Any, key: str, default: str | None = None
    ) -> None:
        if not hasattr(obj, "setPlaceholderText"):
            return
        value = translate(plugin_id, key, default)
        if isinstance(value, str) and value:
            obj.setPlaceholderText(value)

    def _apply_tooltip(obj: Any, key: str, default: str | None = None) -> None:
        if not hasattr(obj, "setToolTip"):
            return
        value = translate(plugin_id, key, default)
        if isinstance(value, str) and value:
            obj.setToolTip(value)

    for obj in _iter_objects(root):
        name = _object_name(obj)
        if not name:
            continue

        title_key = _prop(obj, "i18n_title_key") or name
        text_key = _prop(obj, "i18n_text_key") or name
        tooltip_key = _prop(obj, "i18n_tooltip_key")
        placeholder_key = _prop(obj, "i18n_placeholder_key")

        if hasattr(obj, "setTitle"):
            current = obj.title() if hasattr(obj, "title") else None
            _apply_title(
                obj, title_key, current if isinstance(current, str) else None
            )
            continue

        if hasattr(obj, "setText"):
            current = obj.text() if hasattr(obj, "text") else None
            _apply_text(
                obj, text_key, current if isinstance(current, str) else None
            )

        if tooltip_key:
            current = obj.toolTip() if hasattr(obj, "toolTip") else None
            _apply_tooltip(
                obj, tooltip_key, current if isinstance(current, str) else None
            )

        if placeholder_key:
            current = (
                obj.placeholderText()
                if hasattr(obj, "placeholderText")
                else None
            )
            _apply_placeholder(
                obj,
                placeholder_key,
                current if isinstance(current, str) else None,
            )


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
    """Load a YAML language file for a plugin."""
    try:
        import importlib.resources as ilr

        if not plugin_package:
            return {}
        normalized = normalize_language_code(code)
        candidates = [
            f"{normalized}.yml",
            f"{normalized.lower()}.yml",
            "en.yml",
        ]
        for name in candidates:
            try:
                ref = ilr.files(plugin_package).joinpath("languages", name)
                if not ref.is_file():
                    continue
                if yaml is None:
                    return {}
                with ilr.as_file(ref) as p:
                    data = yaml.safe_load(Path(p).read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
            except Exception:
                continue
        return {}
    except Exception:
        return {}


def _discover_plugins_dir() -> str | None:
    try:
        base = os.path.abspath(
            os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                os.pardir,
                os.pardir,
            )
        )
        cand = os.path.join(base, INTERNAL_PLUGINS_DIR)
        if os.path.isdir(cand):
            return cand
    except Exception:
        pass
    return None


def _load_plugin_languages_from_fs(
    plugins_dir: str, code: str
) -> dict[str, dict]:
    data: dict[str, dict] = {}
    normalized = normalize_language_code(code)
    candidates = [
        f"{normalized}.yml",
        f"{normalized.lower()}.yml",
        "en.yml",
    ]
    try:
        for entry in os.listdir(plugins_dir):
            plugin_path = os.path.join(plugins_dir, entry)
            if not os.path.isdir(plugin_path):
                continue
            if not os.path.isfile(os.path.join(plugin_path, "__init__.py")):
                continue
            lang_dir = os.path.join(plugin_path, "languages")
            if not os.path.isdir(lang_dir):
                continue
            payload: dict = {}
            for name in candidates:
                p = os.path.join(lang_dir, name)
                if not os.path.isfile(p):
                    continue
                try:
                    if yaml is None:
                        continue
                    with open(p, encoding="utf-8") as f:
                        content = yaml.safe_load(f)
                    if isinstance(content, dict):
                        payload.update(content)
                        break
                except Exception:
                    continue
            if payload:
                data[entry] = payload
    except Exception:
        pass
    return data


def _load_all_plugin_languages(code: str) -> None:
    """Load translations for all plugins in Plugins/ folder."""
    try:
        _PLUGIN_TR.clear()
    except Exception:
        pass
    plugins_dir = _discover_plugins_dir()
    if not plugins_dir:
        return
    data = _load_plugin_languages_from_fs(plugins_dir, code)
    for plugin_id, tr in data.items():
        register_plugin_translations(plugin_id, tr)
        try:
            register_plugin_translations(str(plugin_id).lower(), tr)
        except Exception:
            pass
