# ARK i18n Integration Guide

This document explains the official ARK i18n integration model.

It is not only a translation reference. It describes:

- where translations live
- how classic GUI applies them
- how IDE-like GUI must integrate with the same flow
- what contributors must do when adding new UI

## Why This Matters

In ARK, i18n is part of the architecture.

The project does not expect each widget, dialog, or UI variant to manage its
own translation lifecycle. The expected model is:

1. translations are defined centrally
2. widgets are mapped centrally
3. runtime translation is applied centrally
4. UI variants reuse that flow instead of creating a parallel one

If that rule is ignored, typical regressions appear:

- language changes only apply after restart
- classic GUI and IDE-like GUI diverge
- hidden/proxy controls show stale text
- one widget updates while another equivalent widget does not

## Main Files

The official i18n path spans these files:

- `languages/*.json`
- `Core/i18n.py`
- `Core/Gui.py`
- `Core/UiConnection.py`
- `Core/UiFeatures.py`
- `Core/IdeLikeGui/connections.py`

## Official Source Of Truth

The runtime source of truth is:

- the active translation table stored in `self._tr`
- the centralized application pass in `Core/i18n.py`

Do not treat constructor text, temporary tooltips, or local UI code as the real
source of truth.

## End-To-End Classic GUI Flow

This is the official path used by the classic GUI.

### 1. The GUI is created

`Core/Gui.py` creates the main window and loads preferences.

Then it initializes the UI variant:

- classic GUI via `init_ui()`
- IDE-like GUI via `init_ide_like_ui()`

For classic GUI, widget wiring begins in:

- `Core/UiConnection.py`

### 2. Widgets are mapped before translation is applied

`Core/UiConnection.py` loads the `.ui` file and maps widgets to Python
attributes such as:

- `self.btn_select_folder`
- `self.btn_select_files`
- `self.select_lang`
- `self.select_theme`
- `self.btn_show_stats`

This step matters because the centralized i18n pass can only update widgets
that already exist and are already mapped.

### 3. The initial language is resolved

`Core/Gui.py` computes the effective language from:

- preferences
- or system language if the preference is `System`

Then it calls:

- `apply_language(...)`

### 4. The translation table is loaded

Inside `Core/i18n.py`:

- `normalize_lang_pref(...)` normalizes the preference
- `resolve_system_language()` resolves the real system language when needed
- `get_translations(...)` loads the language JSON and merges it with `FALLBACK_EN`

This gives a complete translation dictionary, even if some keys are missing in a
specific language file.

### 5. Runtime language state is updated

Inside `apply_language(...)`, ARK updates:

- `self._tr`
- `self.current_language`
- `self.language`
- `self.language_pref`

This must happen before variant-specific refresh code uses current language
state.

### 6. Centralized widget translation is applied

Still in `Core/i18n.py`, ARK calls:

- `_apply_main_app_translations(self, tr)`

This is the official integration point for the main GUI.

It applies translation to:

- button text via `_set(...)`
- labels
- tabs
- checkboxes and options
- placeholders
- tooltips via `_tt(...)`
- dynamic labels such as workspace status

This is the most important rule in the architecture:

If a control belongs to the main GUI surface, and especially if it exists in
both classic and IDE-like variants, its shared i18n should normally be wired
here.

### 7. Post-translation refresh callbacks run

After the central pass, ARK runs:

- registered language refresh callbacks
- engine translation propagation
- plugin SDK translation propagation

This is the correct moment for secondary refresh logic.

If a callback runs before the central translation pass or before `self._tr` is
updated, it may see stale state and create delayed refresh bugs.

## What Belongs In Each File

### `languages/*.json`

Put translation keys and values here.

Examples:

- button labels
- tooltip text
- dialog titles
- placeholders
- variant-specific labels that still belong to the shared app vocabulary

Rule:

- every new GUI-facing key must be added to every language file

### `Core/UiConnection.py`

Use this file to:

- map widgets from the Qt UI file to Python attributes
- connect signals
- set temporary/default widget state when needed

Do not treat it as the final i18n layer.

If a tooltip is set here for bootstrap reasons, it still needs proper runtime
i18n wiring in `Core/i18n.py`.

### `Core/i18n.py`

Use this file as the main integration layer for GUI i18n.

This is where contributors should usually:

- add `_set(...)` calls for new widget labels
- add `_tt(...)` calls for new tooltips
- update dynamic label handling
- keep language-state ordering correct

This is the official i18n technique used by classic GUI.

### `Core/UiFeatures.py`

Use this file for feature behavior.

It may consume translations, dialogs, or helpers, but it should not become a
second centralized i18n system.

### `Core/IdeLikeGui/connections.py`

Use this file only for IDE-specific translation glue.

The IDE-like GUI is a wiring/layout layer on top of the shared Core behavior.

That means:

- reuse classic GUI translation flow whenever possible
- do not hardcode labels that already exist in classic GUI
- do not duplicate the central application pass from `Core/i18n.py`

## Integration Rules By Control Type

### Case 1: A shared main GUI button

Examples:

- select workspace
- add files
- stats
- help
- export/import config

Expected integration:

1. add keys in `languages/*.json`
2. make sure the widget is mapped in `Core/UiConnection.py`
3. wire its text and tooltip in `Core/i18n.py`

### Case 2: A dynamic shared button

Examples:

- `select_lang`
- `select_theme`
- labels that depend on workspace path or system-python mode

Expected integration:

- still wire them in `Core/i18n.py`
- handle runtime state there with explicit logic
- avoid building special local refresh flows unless strictly necessary

### Case 3: An IDE proxy control for an existing classic feature

Examples:

- overflow menu `(...)`
- activity-bar button mirroring an existing classic button

Expected integration:

- reuse classic GUI translated widgets when the IDE control is just another view of the same feature
- or resolve from `self._tr` using the exact same translation keys
- resync at the moment the proxy control is shown if timing matters

Do not invent separate hardcoded labels for the IDE view.

### Case 4: A truly IDE-only control

Expected integration:

1. add a dedicated translation key in `languages/*.json`
2. resolve it from `self._tr`
3. keep the glue local to the IDE package only if it is genuinely IDE-specific

## The `(...)` Menu Rule

The IDE overflow menu deserves a special rule because it is a proxy surface.

Some actions in `(...)` already exist as classic GUI controls. In that case, the
best integration is not to create a second vocabulary, but to reuse the classic
one.

Examples:

- workspace selection
- venv selection
- add files
- clear workspace
- statistics
- language
- theme
- advanced config
- export/import config
- help

For those items:

- prefer reusing the corresponding classic widget text when appropriate
- otherwise use the same translation keys from `self._tr`

For IDE-only items:

- create explicit keys

Examples already present:

- `advanced_config`
- `save_engine_configs`
- `tt_more_actions`

## Plugin And Engine Propagation

ARK i18n is not limited to the main window.

After the main application pass, ARK also propagates translation state to:

- engines
- plugin SDK contexts

So if a contributor introduces isolated plugin or engine UI text, they should
first verify whether the shared propagation path already covers that use case.

## Mandatory Contributor Workflow For New i18n

When adding a new translatable UI element:

1. add the key in every `languages/*.json` file
2. ensure the widget is mapped to a stable `self.<attr>` name
3. wire the runtime translation in `Core/i18n.py` if the control belongs to shared GUI
4. only use local IDE glue if the control is genuinely IDE-only
5. verify live switching without restarting the app
6. verify both classic GUI and IDE-like GUI if the feature exists in both
7. verify hidden/proxy controls such as overflow menus or mirrored buttons

## Anti-Patterns To Avoid

Do not do the following:

- set translated text only in widget constructors
- hardcode English labels in IDE-specific refresh functions
- create a second i18n pipeline inside `Core/IdeLikeGui/`
- copy text from another widget before the central i18n pass has run
- update only one language file
- bypass `Core/i18n.py` for shared controls

## Practical Examples

### Add a new shared button

Use this model:

1. add `my_new_button` and `tt_my_new_button` to all `languages/*.json`
2. map `self.my_new_button` in `Core/UiConnection.py`
3. in `Core/i18n.py`, add:
   - `_set("my_new_button", "my_new_button")`
   - `self.my_new_button.setToolTip(_tt("tt_my_new_button", self.my_new_button.toolTip()))`

### Add a new IDE-only overflow action

Use this model:

1. add a new key like `my_ide_action`
2. resolve it from `self._tr` in `Core/IdeLikeGui/connections.py`
3. keep the logic local only because the control has no classic equivalent

### Mirror an existing classic control in IDE

Use this model:

1. reuse the same shared translation key
2. prefer reusing the existing classic widget text if the IDE element is only a proxy view
3. resync when the proxy surface opens if timing is sensitive

## Short Version

The official ARK i18n method is:

1. define keys in `languages/*.json`
2. map widgets in `Core/UiConnection.py`
3. apply translations centrally in `Core/i18n.py`
4. let classic GUI be the reference flow
5. make IDE-like GUI reuse that flow instead of replacing it
