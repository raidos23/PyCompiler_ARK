# **PyCompiler ARK Application i18n Guide**

This document explains how to wire translations for the main PyCompiler ARK application UI.
It does not cover extensions. Engines and BC plugins have their own language packs and should
follow their dedicated guides.

## **Overview**

The application translation flow is centralized in `pycompiler_ark/Ui/i18n.py`.
That module owns:

- loading language catalogs from `pycompiler_ark/languages/*.yml`
- keeping the active translation catalog in memory
- applying the selected language to the main UI
- refreshing translated widgets when the language changes

The public lookup API is `translate(self.id, key, default)`.
The app UI should use that API everywhere a label, tooltip, placeholder, or tab title needs a translated value.

## **Language Files**

Application languages live in:

```text
pycompiler_ark/languages/en.yml
pycompiler_ark/languages/fr.yml
pycompiler_ark/languages/de.yml
...
```

Each file should contain:

- a `_meta` block with `code` and `name`
- one flat key per translatable string
- only application keys, not engine or plugin keys

Example:

```yaml
_meta:
  code: fr
  name: Français
build_all: Compiler
choose_language_button: Langue
tt_build_all: Démarrer la compilation
```

## **Application Pattern**

The recommended pattern is:

1. create the widget
2. attach i18n properties to it
3. let `pycompiler_ark/Ui/i18n.py` resolve the active language
4. call `translate(self.id, ...)` when reading text dynamically

For standard widgets, use the helper already used in the codebase:

```python
_declare_i18n(
    self.compile_btn,
    i18n_text_key="build_all",
    i18n_tooltip_key="tt_build_all",
)
```

If you need to attach properties manually, use:

```python
widget.setProperty("i18n_text_key", "build_all")
widget.setProperty("i18n_tooltip_key", "tt_build_all")
```

## **Supported i18n Properties**

`pycompiler_ark/Ui/i18n.py` reads these properties when it traverses the UI tree:

- `i18n_text_key`
- `i18n_text_system_key`
- `i18n_tooltip_key`
- `i18n_placeholder_key`
- `i18n_tab_key`
- `i18n_system_attr`
- `i18n_format_attr`
- `i18n_none_key`

Typical use cases:

- `i18n_text_key`: button text, label text, action text
- `i18n_tooltip_key`: tooltip
- `i18n_placeholder_key`: line edit placeholder
- `i18n_tab_key`: tab title
- `i18n_text_system_key` + `i18n_system_attr`: switch to a different label when the app is on `System`
- `i18n_format_attr`: value inserted into a translated template, such as a workspace path
- `i18n_none_key`: fallback text when the dynamic attribute is empty

## **Language Change Flow**

When the user changes the language:

1. `show_language_dialog()` resolves the selected language.
2. `get_translations()` loads the selected YAML file.
3. `i18n_synchro()` stores the active catalog.
4. `_apply_main_app_translations()` walks the UI tree and reapplies texts.
5. The IDE-like actions, engine registry, and plugin SDK are refreshed through their generic host hooks.

This is why the application should not hardcode translated strings inside the refresh path.
The refresh path must stay generic and data-driven.

## **What To Avoid**

- Do not keep application strings hardcoded in `Ui/i18n.py`.
- Do not duplicate engine or plugin keys in the global application catalogs.
- Do not add extension-specific translation logic in the main UI guide or the main UI catalog.
- Do not mix fallback English text with catalog data unless it is the literal default for `translate(...)`.

## **Minimal Example**

```python
from pycompiler_ark.Ui.i18n import translate

title = translate(self.id, "choose_theme_title", "Choose theme")
self.theme_button.setText(translate(self.id, "choose_theme_button", "Theme"))
```

If the key exists in the active catalog, the localized value is used.
Otherwise, the provided default is used.
