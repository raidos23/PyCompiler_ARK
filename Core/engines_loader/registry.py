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

from typing import Optional, Any

from .base import CompilerEngine

_REGISTRY: dict[str, type[CompilerEngine]] = {}
_ORDER: list[str] = []
# UI mapping: engine id -> tab index
_TAB_INDEX: dict[str, int] = {}
# Keep live engine instances to support dynamic interactions (e.g., i18n refresh)
_INSTANCES: dict[str, CompilerEngine] = {}

# Language code aliases for normalization
_LANG_ALIASES: dict[str, str] = {
    "en-us": "en",
    "en_gb": "en",
    "en-uk": "en",
    "fr-fr": "fr",
    "fr_ca": "fr",
    "fr-ca": "fr",
    "pt-br": "pt-BR",
    "pt_br": "pt-BR",
    "zh": "zh-CN",
    "zh_cn": "zh-CN",
    "zh-cn": "zh-CN",
}


def normalize_language_code(code: Optional[str]) -> str:
    """Normalize language code with fallback chain.

    Returns normalized code or 'en' as ultimate fallback.
    """
    if not code:
        return "en"

    try:
        raw = str(code)
        low = raw.lower().replace("_", "-")
        mapped = _LANG_ALIASES.get(low, raw)

        # Candidate order: mapped -> base (before '-') -> exact lower -> exact raw -> 'en'
        candidates = []
        if mapped not in candidates:
            candidates.append(mapped)

        base = None
        try:
            if "-" in mapped:
                base = mapped.split("-", 1)[0]
            elif "_" in mapped:
                base = mapped.split("_", 1)[0]
        except Exception:
            base = None

        if base and base not in candidates:
            candidates.append(base)
        if low not in candidates:
            candidates.append(low)
        if raw not in candidates:
            candidates.append(raw)
        if "en" not in candidates:
            candidates.append("en")

        return candidates[0] if candidates else "en"
    except Exception:
        return "en"


def resolve_language_code(gui, tr: Optional[dict]) -> str:
    """Resolve language code from translations metadata or GUI preferences.

    Returns normalized language code.
    """
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


def unregister(eid: str) -> None:
    """Unregister an engine id and its tab mapping if present."""
    try:
        if eid in _REGISTRY:
            del _REGISTRY[eid]
        if eid in _ORDER:
            _ORDER.remove(eid)
        if eid in _TAB_INDEX:
            del _TAB_INDEX[eid]
    except Exception:
        pass


def unload_all() -> dict[str, Any]:
    """Unload all registered engines and clean up all registry data.

    Returns:
        dict with status and list of unloaded engine IDs
    """
    unloaded = []
    try:
        # Collect all engine IDs before clearing
        unloaded = list(_ORDER)
        unloaded.extend(k for k in _REGISTRY.keys() if k not in unloaded)

        # Clear all registry data
        _REGISTRY.clear()
        _ORDER.clear()
        _TAB_INDEX.clear()

        # Clear instances
        _INSTANCES.clear()

    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "unloaded": unloaded
        }

    return {
        "status": "success",
        "message": f"Unloaded {len(unloaded)} engine(s)",
        "unloaded": unloaded
    }


def engine_register(engine_cls: type[CompilerEngine]):
    """Register an engine class. Enforces a non-empty unique id.

    If the same id is registered again with the same class object, this is a no-op.
    If a different class attempts to register the same id, the new registration is ignored.
    """
    eid = getattr(engine_cls, "id", None)
    if not eid or not isinstance(eid, str):
        raise ValueError("Engine class must define an 'id' attribute (str)")
    try:
        existing = _REGISTRY.get(eid)
        if existing is not None and existing is not engine_cls:
            # Ignore conflicting registration to avoid destabilizing at runtime
            return existing
        _REGISTRY[eid] = engine_cls
        if eid not in _ORDER:
            _ORDER.append(eid)
        return engine_cls
    except Exception:
        # Fail closed: do not crash the app
        return engine_cls


# Alias for backward compatibility
register = engine_register


def get_engine(eid: str) -> Optional[type[CompilerEngine]]:
    try:
        return _REGISTRY.get(eid)
    except Exception:
        return None


def available_engines() -> list[str]:
    try:
        return list(_ORDER)
    except Exception:
        return []


def bind_tabs(gui) -> None:
    """Create tabs for all registered engines that expose create_tab and store indexes.
    Robust to individual engine failures and avoids raising to the UI layer.
    Also handles hiding the Hello tab when engines are available.
    """
    try:
        tabs = getattr(gui, "compiler_tabs", None)
        if not tabs:
            return

        # Get the Hello tab if it exists
        hello_tab = getattr(gui, "tab_hello", None)
        hello_tab_index = -1
        if hello_tab is not None:
            try:
                hello_tab_index = tabs.indexOf(hello_tab)
            except Exception:
                hello_tab_index = -1

        # Track if any engine created a tab
        any_engine_tab_created = False

        for eid in list(_ORDER):
            try:
                engine = create(eid)
                # Keep instance for later interactions (i18n, etc.)
                _INSTANCES[eid] = engine
                res = getattr(engine, "create_tab", None)
                if not callable(res):
                    continue
                pair = res(gui)
                if not pair:
                    continue
                any_engine_tab_created = True
                widget, label = pair
                try:
                    existing = tabs.indexOf(widget)
                except Exception:
                    existing = -1
                if isinstance(existing, int) and existing >= 0:
                    _TAB_INDEX[eid] = existing
                else:
                    idx = tabs.addTab(widget, label)
                    _TAB_INDEX[eid] = int(idx)
                # Apply engine i18n immediately if GUI already has active translations
                try:
                    tr = getattr(gui, "_tr", None)
                    fn = getattr(engine, "apply_i18n", None)
                    if callable(fn) and isinstance(tr, dict):
                        fn(gui, tr)
                except Exception:
                    pass
            except Exception:
                # keep UI responsive even if a plugin tab fails
                continue

        # Hide the Hello tab if any engine has created a tab
        if any_engine_tab_created and hello_tab_index >= 0:
            try:
                tabs.tabBar().hideTab(hello_tab_index)
            except Exception:
                pass
    except Exception:
        # Swallow to avoid breaking app init
        pass


def show_hello_tab(gui) -> None:
    """Show the Hello tab when no engines are available."""
    try:
        tabs = getattr(gui, "compiler_tabs", None)
        if not tabs:
            return
        hello_tab = getattr(gui, "tab_hello", None)
        if hello_tab is not None:
            try:
                idx = tabs.indexOf(hello_tab)
                if idx >= 0:
                    tabs.tabBar().showTab(idx)
                    tabs.setCurrentIndex(idx)
            except Exception:
                pass
    except Exception:
        pass


def apply_translations(gui, tr: dict) -> None:
    """Propagate i18n translations to all engines that expose 'apply_i18n(gui, tr)'."""
    try:
        for eid, inst in list(_INSTANCES.items()):
            try:
                fn = getattr(inst, "apply_i18n", None)
                if callable(fn) and isinstance(tr, dict):
                    fn(gui, tr)
            except Exception:
                continue
    except Exception:
        pass


def get_engine_for_tab(index: int) -> Optional[str]:
    try:
        for eid, idx in _TAB_INDEX.items():
            if idx == index:
                return eid
    except Exception:
        pass
    return None


def create(eid: str) -> CompilerEngine:
    cls = get_engine(eid)
    if not cls:
        raise KeyError(f"Engine '{eid}' is not registered")
    try:
        return cls()
    except Exception as e:
        # If engine instantiation fails, propagate a clearer message
        raise RuntimeError(f"Failed to instantiate engine '{eid}': {e}")
