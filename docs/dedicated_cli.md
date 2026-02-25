## Dedicated Interactive CLI (`--cli`)

PyCompiler ARK includes an interactive command-line mode that you can open with:

```bash
python pycompiler_ark.py --cli
# or
python -m pycompiler_ark --cli
```

This mode is designed as a lightweight control shell for common launcher actions.

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
- `main`: launch the main GUI.
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
- `engine ... -w <workspace>`: optional workspace override for engine commands.
- `unload`: unload all registered engines.
- `exit` or `quit`: close the dedicated CLI.

## Examples

```text
ark-cli> version
ark-cli> info
ark-cli> engines --dry-run
ark-cli> engine list
ark-cli> engine compat nuitka
ark-cli> engine dry-run pyinstaller src/main.py
ark-cli> engine compile nuitka src/main.py
ark-cli> bcasl list
ark-cli> bcasl run ~/my_workspace --timeout 30
ark-cli> bcasl ~/my_workspace
ark-cli> unload
ark-cli> exit
```

## Notes

- `--cli` is intended to be used alone, without a subcommand.
- When a GUI command is executed (`main`, `bcasl`, `engines`), control returns to the prompt after the GUI is closed.
- If Rich is installed, output is colorized. If not, the CLI still works in plain mode.
- `engine compile` validates the target file path before running the engine command.
