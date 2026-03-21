# Architecture Overview

This document provides a high-level map of the main runtime layers in PyCompiler ARK.

## Core layers

### 1. Bootstrap and CLI

Main entrypoints:

- `pycompiler_ark.py`
- `cli/entrypoint.py`
- `cli/click_app.py`
- `cli/fallback.py`
- `cli/dedicated.py`

Responsibilities:

- parse top-level CLI options
- choose between Click-based CLI and fallback mode
- launch the main GUI, BCASL standalone, or Engines standalone
- expose the dedicated interactive CLI

### 2. Main GUI and UI wiring

Main files:

- `Core/Gui.py`
- `Core/UiConnection.py`
- `Core/UiFeatures.py`
- `Core/IdeLikeGui/connections.py`
- `ui/ui_design.ui`
- `ui/ui_ide_design2.ui`

Responsibilities:

- create the main application window
- map Qt widgets to Python attributes
- connect UI actions to shared application logic
- support both classic and IDE-like layouts
- apply theme and translation behavior

### 3. Workspace and environment management

Main files:

- `Core/WorkSpaceManager/`
- `Core/Venv_Manager/Manager.py`
- `Core/ArkConfigManager.py`

Responsibilities:

- manage workspace selection and file discovery
- detect and create virtual environments
- install requirements and tool dependencies
- load and persist workspace-oriented configuration

### 4. Compilation orchestration

Main files:

- `Core/Compiler/`
- `EngineLoader/`
- `ENGINES/`
- `engine_sdk/`

Responsibilities:

- run preflight checks
- load engines dynamically
- build compile commands
- execute compilation processes
- report logs, progress, and statistics

### 5. BCASL pre-compilation pipeline

Main files:

- `bcasl/`
- `Plugins/`
- `Plugins_SDK/`
- `OnlyMod/BcaslOnlyMod/`

Responsibilities:

- validate plugin compatibility
- discover and order BCASL plugins
- run pre-compilation tasks before build execution
- expose standalone BCASL tooling

## Dependency flow

At a high level:

1. CLI or GUI selects a workspace and files.
2. BCASL may run first if configured.
3. The selected engine resolves its required tools.
4. System dependencies are checked before Python tool installation.
5. The engine builds the final compile command.
6. `Core.Compiler` executes and monitors the process.

## UI variants

There are two main UI variants:

- classic GUI
- IDE-like GUI

Shared behavior should stay in reusable helpers when possible. The IDE-like UI should extend the classic behavior rather than fork it. See [IDE/classic parity matrix](./ide_classic_parity.md).

## Design guideline

When changing behavior:

- prefer shared core logic over UI-specific duplication
- keep engine-specific behavior inside engines or engine SDK helpers
- keep UI wiring thin and declarative
- add tests when introducing new heuristics or CLI behavior
