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

import logging
import os
from typing import Any, Optional

from .base import CompilerEngine, log_i18n_level

logger = logging.getLogger(__name__)

_REGISTRY: dict[str, type[CompilerEngine]] = {}
_ORDER: list[str] = []
# UI mapping: engine id -> tab index
_TAB_INDEX: dict[str, int] = {}
# Keep live engine instances to support dynamic interactions (e.g., i18n refresh)
_INSTANCES: dict[str, CompilerEngine] = {}

# Default scroll behavior for engine tabs: wrap in a scroll area so large
# option panels stay usable without bloating the overall UI.
_ENGINE_TAB_SCROLL_MAX_HEIGHT: Optional[int] = None

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
_GLOBAL_TR: dict[str, Any] = {}
_GLOBAL_LANG: str = "en"
_ENGINE_TR: dict[str, dict[str, Any]] = {}


def _iter_i18n_roots(engine: CompilerEngine):
    seen: set[int] = set()
    try:
        values = list(vars(engine).values())
    except Exception:
        values = []
    for value in values:
        try:
            if value is None:
                continue
            if not hasattr(value, "children") and not hasattr(value, "setProperty"):
                continue
            oid = id(value)
            if oid in seen:
                continue
            seen.add(oid)
            yield value
        except Exception:
            continue


def _apply_engine_i18n(root: Any, engine_id: str) -> None:
    def _prop(obj: Any, name: str) -> Any:
        if hasattr(obj, "property"):
            val = obj.property(name)
            if val is not None:
                return val
        return getattr(obj, name, None)

    def _is_system_value(value: Any) -> bool:
        return str(value).strip().lower() == "system"

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

    def _apply_text(obj: Any, key: str, default: str | None = None) -> None:
        if hasattr(obj, "setText"):
            value = translate(engine_id, key, default)
            if isinstance(value, str) and value:
                obj.setText(value)

    def _apply_tooltip(obj: Any, key: str, default: str | None = None) -> None:
        if hasattr(obj, "setToolTip"):
            value = translate(engine_id, key, default)
            if isinstance(value, str) and value:
                obj.setToolTip(value)

    def _apply_placeholder(obj: Any, key: str, default: str | None = None) -> None:
        if hasattr(obj, "setPlaceholderText"):
            value = translate(engine_id, key, default)
            if isinstance(value, str) and value:
                obj.setPlaceholderText(value)

    def _apply_tab_text(obj: Any, key: str, default: str | None = None) -> None:
        parent = getattr(obj, "parent", lambda: None)()
        while parent is not None:
            if hasattr(parent, "indexOf") and hasattr(parent, "setTabText"):
                idx = parent.indexOf(obj)
                if idx >= 0:
                    value = translate(engine_id, key, default)
                    if isinstance(value, str) and value:
                        parent.setTabText(idx, value)
                break
            parent = getattr(parent, "parent", lambda: None)()

    for obj in _iter_objects(root):
        text_key = _prop(obj, "i18n_text_key")
        if text_key:
            system_key = _prop(obj, "i18n_text_system_key")
            system_attr = _prop(obj, "i18n_system_attr")
            format_attr = _prop(obj, "i18n_format_attr")
            none_key = _prop(obj, "i18n_none_key")
            current = obj.text() if hasattr(obj, "text") else None

            chosen_key = str(text_key)
            if system_key and system_attr and _is_system_value(getattr(root, str(system_attr), None)):
                chosen_key = str(system_key)

            if format_attr:
                ctx = getattr(root, str(format_attr), None)
                if ctx:
                    value = translate(engine_id, chosen_key, current if isinstance(current, str) else None)
                    if isinstance(value, str) and value:
                        obj.setText(value.replace("{path}", str(ctx)))
                elif none_key:
                    _apply_text(obj, str(none_key), current if isinstance(current, str) else None)
                continue

            _apply_text(obj, chosen_key, current if isinstance(current, str) else None)

        tooltip_key = _prop(obj, "i18n_tooltip_key")
        if tooltip_key:
            current = obj.toolTip() if hasattr(obj, "toolTip") else None
            _apply_tooltip(obj, str(tooltip_key), current if isinstance(current, str) else None)

        placeholder_key = _prop(obj, "i18n_placeholder_key")
        if placeholder_key:
            current = obj.placeholderText() if hasattr(obj, "placeholderText") else None
            _apply_placeholder(
                obj, str(placeholder_key), current if isinstance(current, str) else None
            )

        tab_key = _prop(obj, "i18n_tab_key")
        if tab_key:
            current = obj.text() if hasattr(obj, "text") else None
            _apply_tab_text(obj, str(tab_key), current if isinstance(current, str) else None)


def _refresh_live_engine_widgets(gui) -> None:
    for engine in list(_INSTANCES.values()):
        if engine is None:
            continue
        engine_id = str(getattr(engine, "id", "") or "")
        if not engine_id:
            continue
        for root in _iter_i18n_roots(engine):
            _apply_engine_i18n(root, engine_id)


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


def set_translations(gui, tr: Optional[dict]) -> None:
    """Store host translations and the resolved active language for engine i18n."""
    global _GLOBAL_TR, _GLOBAL_LANG
    try:
        _GLOBAL_TR = dict(tr) if isinstance(tr, dict) else {}
    except Exception:
        _GLOBAL_TR = {}
    try:
        _GLOBAL_LANG = resolve_language_code(gui, tr if isinstance(tr, dict) else None)
    except Exception:
        _GLOBAL_LANG = "en"


def get_translations() -> dict[str, Any]:
    return dict(_GLOBAL_TR) if isinstance(_GLOBAL_TR, dict) else {}


def get_language_code() -> str:
    return _GLOBAL_LANG or "en"


def register_engine_translations(engine_id: str, tr: dict) -> None:
    """Register or refresh translations for a specific engine id."""
    if not engine_id:
        return
    try:
        if isinstance(tr, dict):
            payload = dict(tr)
        else:
            payload = {}
        _ENGINE_TR[str(engine_id)] = payload
        _ENGINE_TR[str(engine_id).lower()] = payload
    except Exception:
        pass


def _engine_package_for_class(engine_cls: type[CompilerEngine]) -> str | None:
    try:
        module_name = str(getattr(engine_cls, "__module__", "") or "")
        if not module_name:
            return None
        if module_name.endswith(".__init__"):
            module_name = module_name[: -len(".__init__")]
        return module_name
    except Exception:
        return None


def _refresh_engine_translations_for_ids(engine_ids: list[str], code: str) -> None:
    """Load and cache language files for selected engine ids."""
    for eid in engine_ids:
        try:
            engine_cls = get_engine(eid)
            if engine_cls is None:
                continue
            engine_package = _engine_package_for_class(engine_cls)
            if not engine_package:
                continue
            data = load_engine_language_file(engine_package, code)
            register_engine_translations(eid, data if isinstance(data, dict) else {})
        except Exception:
            continue


def _refresh_all_engine_translations(code: str) -> None:
    """Reload translations for all registered engines for the active language."""
    try:
        _ENGINE_TR.clear()
    except Exception:
        pass
    _refresh_engine_translations_for_ids(list(_ORDER), code)


def translate(engine_or_id: Any, key: str, default: Optional[str] = None) -> str:
    """Translate an engine-local key with fallback to host translations and defaults."""
    engine_id = None
    try:
        if isinstance(engine_or_id, str):
            engine_id = engine_or_id
        else:
            engine_id = getattr(engine_or_id, "id", None)
    except Exception:
        engine_id = None

    try:
        if engine_id:
            for candidate in (str(engine_id), str(engine_id).lower()):
                payload = _ENGINE_TR.get(candidate)
                if isinstance(payload, dict):
                    value = payload.get(key)
                    if isinstance(value, str):
                        return value
    except Exception:
        pass

    try:
        fallback = _GLOBAL_TR.get(key)
        if isinstance(fallback, str):
            return fallback
    except Exception:
        pass

    return default if default is not None else str(key)


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
        return {"status": "error", "message": str(e), "unloaded": unloaded}

    return {
        "status": "success",
        "message": f"Unloaded {len(unloaded)} engine(s)",
        "unloaded": unloaded,
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
        # Ensure lazy discovery happened even when callers use `registry.bind_tabs`
        # directly instead of the top-level `bind_tabs` wrapper.
        try:
            import pycompiler_ark.Core.engine as engines_loader

            engines_loader.available_engines()
        except Exception:
            pass

        tabs = getattr(gui, "compiler_tabs", None)
        if not tabs:
            return

        try:
            tr = getattr(gui, "_tr", None)
            set_translations(gui, tr if isinstance(tr, dict) else None)
            _refresh_all_engine_translations(get_language_code())
        except Exception:
            pass

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

        def _log_tab_load_issue(
            eid: str, fr: str, en: str, exc: Exception | None = None
        ) -> None:
            try:
                log_i18n_level(gui, "warning", fr, en)
            except Exception:
                pass
            try:
                if exc is None:
                    logger.warning("%s", en)
                else:
                    logger.warning("%s: %s", en, exc, exc_info=exc)
            except Exception:
                pass

        def _wrap_tab_scroll(widget):
            try:
                from PySide6.QtCore import Qt
                from PySide6.QtWidgets import QFrame, QScrollArea, QSizePolicy

                if isinstance(widget, QScrollArea):
                    scroll = widget
                else:
                    scroll = QScrollArea()
                    scroll.setWidget(widget)

                scroll.setWidgetResizable(True)
                scroll.setFrameShape(QFrame.Shape.NoFrame)
                scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
                scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
                scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

                if _ENGINE_TAB_SCROLL_MAX_HEIGHT:
                    try:
                        scroll.setMaximumHeight(int(_ENGINE_TAB_SCROLL_MAX_HEIGHT))
                    except Exception:
                        pass

                try:
                    name = widget.objectName()
                    if name:
                        scroll.setObjectName(f"{name}_scroll")
                except Exception:
                    pass

                return scroll
            except Exception:
                return widget

        for eid in list(_ORDER):
            try:
                engine = create(eid)
                # Keep instance for later interactions (i18n, etc.)
                _INSTANCES[eid] = engine
                res = getattr(engine, "create_tab", None)
                if not callable(res):
                    continue
                try:
                    pair = res(gui)
                except Exception as exc:
                    _log_tab_load_issue(
                        eid,
                        f"Echec du chargement de l'onglet moteur '{eid}'",
                        f"Failed to load engine tab '{eid}'",
                        exc,
                    )
                    continue
                if not pair:
                    continue
                if not isinstance(pair, tuple) or len(pair) != 2:
                    _log_tab_load_issue(
                        eid,
                        f"Onglet invalide retourne par le moteur '{eid}'",
                        f"Engine '{eid}' returned an invalid tab payload",
                    )
                    continue
                any_engine_tab_created = True
                widget, label = pair
                widget = _wrap_tab_scroll(widget)
                try:
                    existing = tabs.indexOf(widget)
                except Exception:
                    existing = -1
                if isinstance(existing, int) and existing >= 0:
                    _TAB_INDEX[eid] = existing
                else:
                    idx = tabs.addTab(widget, label)
                    _TAB_INDEX[eid] = int(idx)
            except Exception as exc:
                _log_tab_load_issue(
                    eid,
                    f"Echec inattendu lors du chargement de l'onglet moteur '{eid}'",
                    f"Unexpected failure while loading engine tab '{eid}'",
                    exc,
                )
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
    """Propagate i18n translations to the shared engine translation cache."""
    set_translations(gui, tr)
    _refresh_all_engine_translations(get_language_code())
    _refresh_live_engine_widgets(gui)


def get_engine_for_tab(index: int) -> Optional[str]:
    try:
        for eid, idx in _TAB_INDEX.items():
            if idx == index:
                return eid
    except Exception:
        pass
    return None


def load_engine_language_file(engine_package: str, code: str) -> dict:
    """Load language file for an engine from its package's languages folder.

    Args:
        engine_package: The engine's package name (e.g., 'ENGINES.nuitka')
        code: Language code (e.g., 'fr', 'en')

    Returns:
        Dict containing the language data, or empty dict if not found
    """
    try:
        import importlib.resources as ilr
        try:
            import yaml
        except ImportError:  # pragma: no cover - PyYAML attendu dans le projet
            return {}

        candidates = [code]
        if "-" in code:
            candidates.append(code.split("-", 1)[0])
        candidates.append("en")

        for candidate in candidates:
            for ext in (".yml", ".yaml"):
                try:
                    ref = ilr.files(engine_package).joinpath(
                        "languages", f"{candidate}{ext}"
                    )
                    if not ref.is_file():
                        continue
                    with ilr.as_file(ref) as p:
                        with open(str(p), encoding="utf-8") as f:
                            lang_data = yaml.safe_load(f) or {}
                    if isinstance(lang_data, dict):
                        return lang_data
                except Exception:
                    continue
        return {}
    except Exception:
        return {}


def get_instance(eid: str) -> Optional[CompilerEngine]:
    try:
        return _INSTANCES.get(eid)
    except Exception:
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
