# **ARK BuildContext Specification v1.0**

This document defines the data contract between ARK core and compilation engines.

---

### **1. Definition**

The `BuildContext` is a normalized data structure passed by ARK to:

1. An engine's `build_command` method.
2. BC (Before-Compilation) plugins via the `PreCompileContext`.

- **Source Agnostic**: Engines do not read source files (`ark.yml`, lock files, etc.). They rely exclusively on this context.
- **Reproducibility**: The context contains all project-level metadata required to generate a consistent build command, regardless of whether it was triggered from a live configuration or a lock file.

---

### **2. Construction Modes**

The `BuildContext` is built differently depending on the entry point:

| Command | Source |
| :--- | :--- |
| `ark build` | Constructed from `ark.yml` + environment. |
| `ark build --lock` | Constructed strictly from the specified lock file. |
| **GUI Compile** | Constructed from the live `ark.yml` state. |

The resulting `BuildContext` object is identical in all cases.

---

### **3. Data Structure**

```python
@dataclass(slots=True)
class BuildContext:
    project_name: str       # Name of the project (used for executable naming)
    entry_point: str        # Main script path (relative to workspace root)
    output_dir: str         # Directory where artifacts should be placed
    exclude_patterns: list  # List of glob patterns for files to ignore
    data_mappings: list     # List of source/destination/type dicts for raw assets
    icon: str | None        # Optional path to an icon file

Each dictionary in `data_mappings` follows this structure:
- `source`: Path to the source file or directory.
- `destination`: Path to the destination in the bundle.
- `type`: Either `"file"` or `"dir"`. (Defaults to `"dir"` if omitted for backward compatibility).
```

---

### **4. Mapping Table**

| BuildContext Field | `ark.yml` Mapping | Lock File Mapping |
| :--- | :--- | :--- |
| `project_name` | `project.name` | `project.name` |
| `entry_point` | `project.entry` | `project.entry` |
| `output_dir` | `build.output` | `build.output` |
| `exclude_patterns` | `build.exclude` | `build.exclude` (or `workspace.exclude_patterns` fallback) |
| `data_mappings` | `build.data` | `build.data` |
| `icon` | `build.icon` | `build.icon` |

---

### **5. Engine Contract**

An engine implementation MUST adhere to the following rules when processing a `BuildContext`:

1. **Name Application**: Use `project_name` for the final executable (e.g., `MyApp.exe` or `MyApp`).
2. **Entry Point**: Treat `entry_point` as the primary script to compile/bundle.
3. **Output Path**: Place all generated artifacts and temporary files inside `output_dir`.
4. **Exclusions**: Respect `exclude_patterns` by preventing those modules/files from being bundled.
5. **Assets**: Copy all items defined in `data_mappings` from their source to the appropriate relative destination within the bundle.
6. **Icon**: Apply the file specified in `icon` to the executable metadata/resource if supported by the target OS.

---

### **6. Implementation Example**

```python
from engine_sdk import CompilerEngine, engine_register, BuildContext 

@engine_register
class MyEngine(CompilerEngine):
    id = "my_engine"
    name = "My Engine"

    def build_command(self, context: BuildContext) -> list[str]:
        # Start with base command
        cmd = ["nuitka", context.entry_point]
        
        # Convert exclusions
        for pattern in context.exclude_patterns:
            module = pattern.replace("/**/*", "").replace("**/*", "")
            cmd.append(f"--nofollow-import-to={module}")
        
        # Add data files
        for mapping in context.data_mappings:
            source = mapping['source']
            dest = mapping['destination']
            mapping_type = mapping.get('type', 'dir')
            
            if mapping_type == 'file':
                cmd.append(f"--include-data-files={source}={dest}")
            else:
                cmd.append(f"--include-data-dir={source}={dest}")
        
        # Metadata and resources
        if context.icon:
            cmd.append(f"--windows-icon-from-ico={context.icon}")
        
        cmd.append(f"--output-dir={context.output_dir}")
        cmd.append(f"--output-filename={context.project_name}")
        
        return cmd
```

---

### **7. Constraints & Prohibitions**

- **NO Project Scanning**: Engines must not manually scan the workspace to find files. Rely on the core's file discovery passed via the context.
- **NO Source Reading**: Engines must not attempt to parse `ark.yml` or search for `.git` folders.
- **NO Environmental Assumptions**: Use the environment variables provided by the core runner or injected via the engine's `environment()` hook.

---

### **8. Summary Rules**

- **B1**: The engine is a consumer of the `BuildContext` only.
- **B2**: The engine implementation must be stateless regarding the configuration source.
- **B3**: Engines are responsible for translating normalized context fields into engine-specific CLI flags or configuration parameters.

---
*End of Specification v1.0*
