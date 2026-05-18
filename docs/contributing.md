# **Contributing to PyCompiler ARK**

Thank you for your interest in contributing to ARK! This workshop is designed to be extensible through its multi-engine and pre-compile plugin systems.

## **Where to Start?**

If you are a developer looking to extend ARK's functionality, please refer to the following guides:

- **Creating a Compilation Engine**: [docs/how_to_create_an_engine.md](how_to_create_an_engine.md)
  Learn how to package and register a new compiler (e.g., Py2Exe, Docker).
- **Creating a Pre-Compile Plugin**: [docs/how_to_create_a_bc_plugin.md](how_to_create_a_bc_plugin.md)
  Learn how to add validation, cleanup, or preparation steps to the build pipeline.

## **Technical Specifications**

For a deeper dive into ARK's internal architecture, review our core specifications:

- **BuildContext Spec**: [docs/dev_docs/ARK_BuildContext_v1.0.md](dev_docs/ARK_BuildContext_v1.0.md)
- **CLI Spec**: [docs/dev_docs/ARK_Cli_v1.1.md](dev_docs/ARK_Cli_v1.1.md)
- **Locking Spec**: [docs/dev_docs/ARK_Locking_v1.0.md](dev_docs/ARK_Locking_v1.0.md)

## **Development Workflow**

1.  **Code Style**: We use `ruff` for linting and `black` for formatting.
2.  **Testing**: Run tests using `pytest`.
3.  **Engine Registry**: New engines should be placed in the `ENGINES/` directory.

## **License**

By contributing, you agree that your contributions will be licensed under the project's **Apache-2.0** license.
