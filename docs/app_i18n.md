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
The app UI should use that API everywhere a label, tooltip, placeholder, action text, or tab title needs a translated value.

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

1. **Naming Convention (Automatic)**:
   Name your widget using one of the following prefixes to have it translated automatically:
   - `btn_<key>` (e.g. `btn_select_folder` translates using `select_folder` and resolves its tooltip as `tt_select_folder`).
   - `action_<key>` (e.g. `action_select_workspace`).
   - `tab_<key>` (e.g. `tab_hello`).

2. **Explicit Properties**:
   Attach explicit `i18n_*` properties to the widget (via PySide's `.setProperty()` or inside the `.ui` file) if you want to override the default convention lookup.

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

The walker is generic:

- `QGroupBox` uses `setTitle(...)`
- `QAction`, buttons, labels, and checkboxes use `setText(...)`
- line edits and similar widgets use `setPlaceholderText(...)`
- tooltips are applied when `i18n_tooltip_key` is present

Typical use cases:

- `i18n_text_key`: button text, label text, action text
- `i18n_tooltip_key`: tooltip
- `i18n_placeholder_key`: line edit placeholder
- `i18n_tab_key`: tab title
- `i18n_text_system_key` + `i18n_system_attr`: switch to a different label when the app is on `System`
- `i18n_format_attr`: value inserted into a translated template, such as a workspace path
- `i18n_none_key`: fallback text when the dynamic attribute is empty

## **When to Use What**

- **Naming Conventions (`btn_*`, `action_*`, `tab_*`)**:
  - **When**: Building standard persistent UI elements like buttons, actions, and tab widgets.
  - **Why**: Zero configuration. Just name the widget correctly and the system translates the text and tooltip automatically.

- **Explicit Properties (`i18n_text_key`, `i18n_format_attr`, etc.)**:
  - **When**: Surcharging standard convention lookups, setting up line edit placeholder keys, formatting strings with dynamic values (like `{path}` via `i18n_format_attr`), or handling system preference toggles.
  - **Why**: Allows advanced dynamic text formatting and fallback keys (`i18n_none_key`).

- **Direct API `translate(self.id, key, default)`**:
  - **When**: Translating non-persistent text dynamically in Python code (e.g. dialog messages, warning/error popups, dynamic log outputs).
  - **Why**: Best for ad-hoc strings that do not belong to static UI widgets.

## **Language Change Flow**

When the user changes the language:

1. `show_language_dialog()` resolves the selected language.
2. `get_translations()` loads the selected YAML file.
3. `i18n_synchro()` stores the active catalog.
4. `_apply_main_app_translations()` walks the UI tree and reapplies texts.
5. The engine registry and plugin SDK are refreshed through generic host hooks.

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
