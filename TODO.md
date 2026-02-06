# Refactoring Core/UiConnection.py

## Tasks
- [ ] Extract logo setup into a dedicated function `_setup_sidebar_logo`
- [ ] Break down `init_ui` into smaller functions:
  - [ ] `_load_ui_file`
  - [ ] `_clear_inline_styles`
  - [ ] `_apply_initial_theme`
  - [ ] `_setup_widgets`
  - [ ] `_connect_signals`
  - [ ] `_setup_compiler_tabs`
  - [ ] `_show_initial_help_message`
- [ ] Add docstrings to all functions
- [ ] Simplify try-except blocks where possible
- [ ] Organize code logically within the file
- [ ] Test UI initialization after refactoring
