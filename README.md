# PyCompiler ARK++

A Qt‑based workshop to compile Python projects with a **pre‑compilation plugin pipeline (BCASL)** and a **multi‑engine system**.

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](http://www.apache.org/licenses/LICENSE-2.0)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

<p align="center">
  <img src="./logo/logo2.png" alt="drawing" width="70%"/>
</p>

## ✨ Signature Capabilities

- **BCASL (Before Compilation Advanced System Loader)**
  - Pre‑compile plugins: validation, preparation, transformation
  - Ordering + dependencies, sandboxed execution, timeouts
  - Optional parallelism for independent plugins

- **Multi‑engine compilation**
  - **PyInstaller**, **Nuitka**, **cx_Freeze**
  - Extensible architecture via `ENGINES/`

- **Workspace‑oriented UI workflow**
  - Select workspace + files
  - File filtering, exclusions via `ARK_Main_Config.yml`
  - Integrated logs and progress

- **Dedicated tools**
  - **BCASL Standalone** (plugin manager)
  - **Engines Standalone** (engine manager)

- **Customization**
  - QSS themes (`themes/`)
  - Translations (`languages/`)

---

## 🚀 Quick Start

### Installation

```bash
git clone https://github.com/raidos23/PyCompiler_ARK.git
cd PyCompiler_ARK
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows

pip install -r requirements.txt
```

### Launch the Main App

```bash
python pycompiler_ark.py
# or
python -m pycompiler_ark
```

### CLI Entry (same binary)

```bash
python pycompiler_ark.py --help
python pycompiler_ark.py --version
python pycompiler_ark.py --info

# BCASL standalone (GUI)
python pycompiler_ark.py bcasl
python pycompiler_ark.py bcasl /path/to/workspace

# Engines standalone (GUI)
python pycompiler_ark.py engines
python pycompiler_ark.py engines /path/to/workspace
python pycompiler_ark.py engines --dry-run
```

---

## 🧭 Workflow (4 steps)

1. **Select a workspace**
2. **Add / filter files** to compile
3. **Configure the engine** (PyInstaller / Nuitka / cx_Freeze)
4. **Build** and follow logs + progress

---

## 📚 Documentation

- [How to create an engine](docs/how_to_create_an_engine.md)
- [How to create a BC plugin](docs/how_to_create_a_bc_plugin.md)

---

## 🔁 BCASL Pipeline (quick view)

```text
Workspace
  │
  ├─ Load bcasl.yml
  ├─ Discover plugins (Plugins/)
  ├─ Enable / order / priorities
  ├─ Sandboxed execution (timeouts, optional parallelism)
  ▼
Compilation (PyInstaller / Nuitka / cx_Freeze)
```

---

## 🧩 BCASL Standalone (Plugins)

```bash
python -m OnlyMod.BcaslOnlyMod --gui
python -m OnlyMod.BcaslOnlyMod --list-plugins
python -m OnlyMod.BcaslOnlyMod --run --workspace /path/to/workspace
```

## ⚙️ Engines Standalone

```bash
python -m OnlyMod.EngineOnlyMod
python -m OnlyMod.EngineOnlyMod --list-engines
python -m OnlyMod.EngineOnlyMod --check-compat nuitka
python -m OnlyMod.EngineOnlyMod --engine nuitka -f script.py --dry-run
```

---

## 📝 Configuration

- **`ARK_Main_Config.yml`** (workspace root)
  - Inclusion/exclusion patterns
  - Plugin options (BCASL)

- **`bcasl.yml`** (workspace root)
  - Enable/disable plugins
  - Order and timeouts

---

## 🗂️ Project Layout

- `Core/` — main UI logic
- `ENGINES/` — built‑in engines
- `EngineLoader/` — discovery/registry
- `Plugins/` — BCASL plugins
- `Plugins_SDK/` — plugin SDK
- `bcasl/` — BCASL core
- `OnlyMod/` — standalone tools (BCASL / Engines)
- `ui/` — Qt Designer UI
- `languages/` — translations
- `themes/` — QSS themes

---

## 🧪 Development

```bash
ruff check .
black --check .
mypy .
pytest
```

---

## 📄 License

Apache‑2.0 (see [`LICENSE`](LICENSE)).
