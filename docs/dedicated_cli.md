## Dedicated Interactive CLI (`--cli`)

PyCompiler ARK includes an interactive command-line mode that you can open with:

```bash
python pycompiler_ark.py --cli
# or
python -m pycompiler_ark --cli
```

Preferred main GUI launch from the top-level CLI:

```bash
python pycompiler_ark.py gui main --ide
```

Legacy compatibility alias outside dedicated CLI:

```bash
python pycompiler_ark.py --ide-gui
```

This mode is designed as a lightweight control shell for common launcher actions.

The dedicated shell is complementary to the structured top-level CLI. Use:

- top-level Click commands for scripting and CI
- `--cli` for interactive operator workflows

## What It Does

- Opens a persistent prompt (`ark-cli`).
- Lets you run launcher actions without restarting the process for each command.
- Uses Rich output (tables, panels, colors) with safe fallback to plain output.
- Supports live command syntax highlighting while typing (command/flags/paths) when `prompt_toolkit` is available.
- Renders an ASCII startup banner for `PyCompiler ARK` automatically (via `pyfiglet` when available).

## Available Commands

- `help`: show command list.
- `version`: print the current app version.
- `info`: print system and runtime information.
- `main`: launch the main GUI (classic layout).
- `main --ide-gui`: launch the main GUI in IDE-like layout.
- `bcasl [workspace]`: launch BCASL standalone GUI (optional workspace path).
- `bcasl list`: list available BCASL plugins (headless).
- `bcasl run <workspace> [--timeout S]`: execute BCASL on a workspace without GUI.
- `bcasl run -w <workspace> [--timeout S]`: same run command with explicit workspace option.
- `engines [workspace]`: launch Engines standalone GUI (optional workspace path).
- `engines --dry-run`: list currently available engines without opening the GUI.
- `engine list`: list engines with compatibility status.
- `engine compat <engine_id>`: run compatibility checks for one engine.
- `engine info <engine_id>`: print engine metadata and compatibility.
- `engine dry-run <engine_id> <file.py>`: build and print the compile command.
- `engine compile <engine_id> <file.py>`: execute compilation from the dedicated CLI.
- `engine ... --workspace <path>`: explicit workspace override when needed.
- `engine ... -w <workspace>`: optional workspace override for engine commands.
- `engine config show/path <engine_id> --workspace <path>`: inspect persisted engine config.
- `engine config set <engine_id> --workspace <path> --options-json '{...}'`: update engine options.
- `engine config reset <engine_id> --workspace <path>`: reset persisted engine config.
- `check [workspace]`: run strict CI/CD preflight checks (fail-only text mode).
- `init [workspace] [--with-venv]`: create workspace directory/config when missing, optionally prepare `.venv`.
- `config-auto [workspace]`: auto-configure entrypoint and dependency file order.
- `cfg-auto [workspace]`: alias of `config-auto`.
- `ws init [workspace]`: alias of `init`.
- `ws config-auto [workspace]`: alias of `config-auto`.
- `workspace entrypoint-set [workspace] <path>`: persist explicit workspace entrypoint.
- `workspace entrypoint-clear [workspace]`: clear persisted workspace entrypoint.
- `venv status [workspace]`: inspect workspace venv mode and preference file.
- `venv use-system [workspace]`: set workspace Python mode to system.
- `venv use-venv [workspace] [venv_path] [--create]`: set workspace Python mode to venv.
- `venv install-req [workspace]`: install requirements for current workspace Python mode.
- `unload`: unload all registered engines.
- `exit` or `quit`: close the dedicated CLI.

## Examples

```text
ark-cli> version
ark-cli> info
ark-cli> main --ide-gui
ark-cli> engines --dry-run
ark-cli> engine list
ark-cli> engine compat <engine_id>
ark-cli> engine dry-run <engine_id> src/main.py
ark-cli> engine compile <engine_id> src/main.py
ark-cli> engine config show <engine_id> --workspace ~/my_workspace
ark-cli> workspace entrypoint-set ~/my_workspace src/main.py
ark-cli> venv status ~/my_workspace
ark-cli> bcasl list
ark-cli> bcasl run ~/my_workspace --timeout 30
ark-cli> bcasl ~/my_workspace
ark-cli> init ~/my_workspace
ark-cli> cfg-auto ~/my_workspace
ark-cli> check ~/my_workspace
ark-cli> unload
ark-cli> exit
```

## Notes

- `--cli` is intended to be used alone, without a subcommand.
- `main` supports `--ide-gui` (also aliases: `main ide`, `main ide-like`).
- When a GUI command is executed (`main`, `bcasl`, `engines`), control returns to the prompt after the GUI is closed.
- If Rich is installed, output is colorized. If not, the CLI still works in plain mode.
- `engine compile` validates the target file path before running the engine command.
- In Engines standalone GUI, file selection is temporary for the current build/session.
- Engines standalone GUI may read workspace config (`ark.yml`) but does not persist entrypoint changes.
- To persist entrypoint in workspace config, use `workspace entrypoint-set`.
- For automation, prefer the top-level commands documented in the README (`engine`, `workspace`, `doctor`, `scaffold`, `gui`).
