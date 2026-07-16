# **Contributing to PyCompiler ARK**

Contributions to PyCompiler ARK go through pull requests. Do not push direct changes to shared branches.
Every commit in a contribution must include a `Signed-off-by` line.

## **Workflow**

1. Create a topic branch from the target branch.
2. Make focused commits with clear messages.
3. Sign each commit with `git commit -s`.
4. Open a pull request against the appropriate branch.
5. Wait for review before merging.

## **What To Read First**

If you are extending PyCompiler ARK, start with:

- **Application i18n**: [app_i18n.md](https://github.com/raidos23/PyCompiler_ARK/blob/main/docs/app_i18n.md)
- **Creating a Compilation Engine**: [how_to_create_an_engine.md](https://github.com/raidos23/PyCompiler_ARK/blob/main/docs/how_to_create_an_engine.md)
- **Creating a Pre-Compile Plugin**: [how_to_create_a_bc_plugin.md](https://github.com/raidos23/PyCompiler_ARK/blob/main/docs/how_to_create_a_bc_plugin.md)

For translation work, read the application guide first, then the engine or plugin guide that matches the area you are changing.

## **Core References**

- **BuildContext Spec**: [BuildContext.md](https://github.com/raidos23/PyCompiler_ARK/blob/main/docs/BuildContext.md)
- **CLI Spec**: [Cli.md](https://github.com/raidos23/PyCompiler_ARK/blob/main/docs/Cli.md)
- **Locking Spec**: [Locking.md](https://github.com/raidos23/PyCompiler_ARK/blob/main/docs/Locking.md)

## **License**

By contributing, you agree that your contributions will be licensed under the project's **Apache-2.0** license.
