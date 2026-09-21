<p align="center">
  <img src="https://raw.githubusercontent.com/raidos23/PyCompiler_ARK/main/pycompiler_ark/images/logo2.png" alt="PyCompiler ARK logo" width="100%"/>
</p>

<p align="center">
  <a href="https://pypi.org/project/pycompiler-ark/"><img src="https://img.shields.io/pypi/v/pycompiler-ark?style=flat-square" alt="PyPI version"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-blue?style=flat-square" alt="License"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.11%2B-blue?style=flat-square" alt="Python"></a>
  <a href="https://github.com/raidos23/PyCompiler_ARK/stargazers"><img src="https://img.shields.io/github/stars/raidos23/PyCompiler_ARK?style=flat-square" alt="Stars"></a>
</p>

# **PyCompiler ARK**

Build Python applications without being locked to a single build engine.

You have a Python project.
You want to turn it into a standalone application.

But building a real Python application can quickly become annoying:

· Which build engine should I use?
· How do I handle dependencies?
· What packages need to be included?
· Which options does each engine require?
· How do I prepare the project before building?
· How do I reproduce the same build later?
· How do I automate it in CI/CD?

ARK handles it for you.

---

## 🚀 Quick Start

Initialize your project:

```bash
pycompiler_ark init --entry main.py
```

Then build:

```bash
pycompiler_ark build
```

ARK takes care of the build workflow — from project configuration and environment handling to pre-build processing, dependency handling, engine selection, and build execution.

You focus on your Python application.
ARK handles the build.

---

## 🤔 Why ARK?

Building a Python application is rarely just:

```
Python → EXE
```

Behind that simple result can be a lot of work:

```
Project
   ↓
Configuration
   ↓
Environment
   ↓
Dependencies
   ↓
Pre-build processing
   ↓
Engine selection
   ↓
Engine-specific options
   ↓
Build
   ↓
Artifacts
   ↓
Distribution
```

ARK brings these steps into a single workflow.

Instead of manually dealing with every build engine and every project-specific detail, you give ARK your project and let it handle the build process.

One project. Multiple engines.

```
                  ┌─ PyInstaller
                  │
Your project ─ ARK ┼─ Nuitka
                  │
                  └─ cx_Freeze
```

You don't have to redesign your workflow around every build backend.

---

##✨ What makes ARK different?

### ⚙️ Multi-engine

Use PyInstaller, Nuitka, or cx_Freeze through the same ARK workflow.

ARK handles the differences between engines instead of forcing you to learn every engine's workflow separately.

### 🔧 Pre-build pipeline

Prepare and transform your project before the actual build begins.

### 📦 Dependency & package handling

ARK can detect and handle project dependencies and translate package inclusions into the format required by the selected engine.

### 🧠 Engine-specific configuration

Different engines have different requirements and options.

ARK provides an abstraction layer so you don't have to manually translate your project configuration for every engine.

### 🤖 Automation

The same workflow can be used locally or integrated into automated build pipelines and CI/CD.

### 🧩 Extensible

ARK separates the build workflow from the engines performing the actual build.

This allows new build engines and BCASL plugins to be integrated without redesigning the whole system.

---

## 🛠️ Quick Start

Install

```bash
pip install pycompiler-ark
```

Initialize your project

```bash
pycompiler_ark init --entry main.py
```

ARK prepares the project workspace and build configuration.

Build

```bash
pycompiler_ark build
```

That's the simple path.

You don't need to manually assemble the entire build process first.

For advanced workflows, ARK provides a GUI for:

· Configuration
· Engine selection
· Build contexts
· Lock files
· Plugin orchestration
· Automation

---

## 📚 Documentation

- [Contributing Guide](https://github.com/raidos23/PyCompiler_ARK/blob/main/CONTRIBUTING.md)
- [VenvManager Architecture](https://github.com/raidos23/PyCompiler_ARK/blob/main/docs/VenvManager.md)
- [How to create an engine](https://github.com/raidos23/PyCompiler_ARK/blob/main/docs/how_to_create_an_engine.md)
- [How to create a BCASL plugin](https://github.com/raidos23/PyCompiler_ARK/blob/main/docs/how_to_create_a_bc_plugin.md)

---

## License

PyCompiler ARK is licensed under the Apache License 2.0

See [LICENSE](https://github.com/raidos23/PyCompiler_ARK/blob/main/LICENSE) for the full license text