# Plan de Correction - Erreur TypeError: CompilerEngine.ensure_tools_installed()

## Problème Identifié

Dans `Core/Compiler/__init__.py`, la fonction `get_engine(engine_id)` retourne la **classe** de l'engine, mais le code appelle des méthodes d'instance (`ensure_tools_installed`, `build_command`, `on_success`) sur cette classe au lieu d'une instance.

### Lieux du problème (ligne 221 et suivantes):
1. `compile_all()` - ligne ~221: `engine = get_engine(engine_id)` puis `engine.ensure_tools_installed(self)`
2. `_start_compilation_queue()` - ligne ~249: `if not engine.ensure_tools_installed(self)`
3. `start_compilation_process()` - ligne ~308: `engine = get_engine(engine_id)` puis `engine.ensure_tools_installed(self)`
4. `handle_finished()` - ligne ~400: `engine.on_success(self, file_path)`

## Solution

Remplacer `get_engine(engine_id)` par `create(engine_id)` dans `Core/Compiler/__init__.py` là où des méthodes d'instance sont appelées sur l'engine.

La fonction `create()` dans `EngineLoader/registry.py` instancie correctement l'engine:
```python
def create(eid: str) -> CompilerEngine:
    cls = get_engine(eid)
    if not cls:
        raise KeyError(f"Engine '{eid}' is not registered")
    try:
        return cls()  # Crée une instance!
    except Exception as e:
        raise RuntimeError(f"Failed to instantiate engine '{eid}': {e}")
```

## Fichiers à Modifier

| Fichier | Modification |
|---------|--------------|
| `Core/Compiler/__init__.py` | Remplacer `get_engine()` par `create()` pour les appels aux méthodes d'instance |

## Étapes de Correction

1. Importer `create` depuis EngineLoader.registry
2. Remplacer `get_engine(engine_id)` par `create(engine_id)` dans:
   - `compile_all()` - pour l'appel à `ensure_tools_installed()`
   - `_start_compilation_queue()` - pour les appels à `ensure_tools_installed()`, `build_command()`, et `environment()`
   - `start_compilation_process()` - pour les appels à `ensure_tools_installed()`, `build_command()`, et `on_success()`
   - `handle_finished()` - pour l'appel à `on_success()`

## Note Importante

Ne pas modifier les imports de `get_engine` car il est toujours utilisé ailleurs dans le code (par exemple pour obtenir la classe sans l'instancier).

