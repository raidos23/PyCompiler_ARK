# Engine Configuration System

## Vue d'ensemble

Le système de configuration persistante permet à chaque engine de sauvegarder et charger sa propre configuration dans `.pycompiler/engines/`.

### Structure

```
~/.pycompiler/
├── engines/
│   ├── nuitka.json
│   ├── pyinstaller.json
│   ├── cx_freeze.json
│   └── custom_engine.json
```

## API

### Classe `EngineConfigManager`

Gestionnaire centralisé pour toutes les configurations d'engines.

#### Initialisation

```python
from engines_loader import get_config_manager

# Utiliser le répertoire par défaut (~/.pycompiler)
manager = get_config_manager()

# Ou spécifier un répertoire personnalisé
manager = get_config_manager(config_dir="/custom/path/.pycompiler")
```

#### Méthodes

##### `load(engine_id: str, schema: Optional[Dict] = None) -> Dict`

Charge la configuration d'un engine.

```python
# Charger avec schéma par défaut
config = manager.load("nuitka", {
    "optimization": 2,
    "strip": False,
    "output_dir": "dist"
})

# Charger sans schéma
config = manager.load("nuitka")
```

**Comportement:**
- Si le fichier existe, retourne la configuration sauvegardée
- Si un schéma est fourni, fusionne la config sauvegardée avec le schéma
- Si le fichier n'existe pas, retourne le schéma (ou `{}` si pas de schéma)

##### `save(engine_id: str, config: Dict) -> bool`

Sauvegarde la configuration d'un engine.

```python
config = {
    "optimization": 3,
    "strip": True,
    "output_dir": "build"
}
success = manager.save("nuitka", config)
```

**Retour:** `True` si succès, `False` sinon

##### `delete(engine_id: str) -> bool`

Supprime la configuration d'un engine.

```python
success = manager.delete("nuitka")
```

##### `exists(engine_id: str) -> bool`

Vérifie si une configuration existe.

```python
if manager.exists("nuitka"):
    print("Configuration trouvée")
```

##### `list_engines() -> list[str]`

Liste tous les engines ayant une configuration sauvegardée.

```python
engines = manager.list_engines()
# ['nuitka', 'pyinstaller', 'cx_freeze']
```

##### `get_config_dir() -> Path`

Retourne le chemin du répertoire de configuration.

```python
config_dir = manager.get_config_dir()
# /home/user/.pycompiler
```

##### `get_engines_dir() -> Path`

Retourne le chemin du répertoire des configurations d'engines.

```python
engines_dir = manager.get_engines_dir()
# /home/user/.pycompiler/engines
```

### Classe `CompilerEngine` - Méthodes de configuration

Chaque engine hérite de `CompilerEngine` et peut utiliser ces méthodes.

#### Attribut `config_schema`

Définit le schéma par défaut de configuration pour l'engine.

```python
class MyEngine(CompilerEngine):
    id = "my_engine"
    name = "My Engine"
    
    config_schema = {
        "enabled": True,
        "output_dir": "dist",
        "optimization_level": 2,
        "strip_binaries": False,
        "timeout_seconds": 300,
    }
```

#### `load_config() -> Dict`

Charge la configuration de l'engine depuis le stockage persistant.

```python
engine = MyEngine()
config = engine.load_config()
# Retourne la config sauvegardée fusionnée avec config_schema
```

#### `save_config(config: Dict) -> bool`

Sauvegarde la configuration de l'engine.

```python
engine = MyEngine()
engine.config["optimization_level"] = 3
success = engine.save_config(engine.config)
```

#### `delete_config() -> bool`

Supprime la configuration de l'engine.

```python
engine = MyEngine()
success = engine.delete_config()
```

#### `has_config() -> bool`

Vérifie si l'engine a une configuration sauvegardée.

```python
engine = MyEngine()
if engine.has_config():
    print("Configuration trouvée")
```

#### `get_config_path() -> str`

Retourne le chemin complet du fichier de configuration.

```python
engine = MyEngine()
path = engine.get_config_path()
# /home/user/.pycompiler/engines/my_engine.json
```

## Exemples d'utilisation

### Exemple 1: Engine simple avec configuration

```python
from engines_loader import CompilerEngine

class NuitkaEngine(CompilerEngine):
    id = "nuitka"
    name = "Nuitka"
    
    config_schema = {
        "optimization": 2,
        "strip": False,
        "output_dir": "dist",
        "follow_imports": True,
    }
    
    def __init__(self):
        super().__init__()
        self.config = self.load_config()
    
    def build_command(self, gui, file: str) -> list[str]:
        cmd = ["nuitka"]
        
        if self.config.get("optimization"):
            cmd.append(f"-O{self.config['optimization']}")
        
        if self.config.get("strip"):
            cmd.append("--remove-output")
        
        cmd.append(file)
        return cmd
    
    def on_success(self, gui, file: str) -> None:
        # Mettre à jour la config après succès
        self.config["last_build"] = file
        self.config["last_build_time"] = str(datetime.now())
        self.save_config(self.config)
```

### Exemple 2: Charger et modifier la configuration

```python
from engines_loader import get_config_manager

manager = get_config_manager()

# Charger
config = manager.load("nuitka", {
    "optimization": 2,
    "strip": False,
})

# Modifier
config["optimization"] = 3
config["strip"] = True

# Sauvegarder
manager.save("nuitka", config)
```

### Exemple 3: Lister toutes les configurations

```python
from engines_loader import get_config_manager

manager = get_config_manager()
engines = manager.list_engines()

for engine_id in engines:
    config = manager.load(engine_id)
    print(f"{engine_id}: {config}")
```

### Exemple 4: Configuration personnalisée par répertoire

```python
from engines_loader import EngineConfigManager

# Utiliser un répertoire personnalisé pour les tests
manager = EngineConfigManager(config_dir="/tmp/test_config/.pycompiler")

config = manager.load("test_engine", {"key": "value"})
manager.save("test_engine", config)
```

## Schéma JSON

Le schéma de configuration est défini dans `schemas/engine_config.schema.json`.

### Structure de base

```json
{
  "id": "engine_id",
  "name": "Engine Name",
  "version": "1.0.0",
  "enabled": true,
  "metadata": {},
  "options": {},
  "environment": {},
  "timeout_seconds": 300,
  "output_dir": "dist",
  "open_output_on_success": false
}
```

### Champs

- **id** (string): Identifiant unique de l'engine
- **name** (string): Nom lisible de l'engine
- **version** (string): Version de la configuration
- **enabled** (boolean): Si l'engine est activé (défaut: true)
- **metadata** (object): Métadonnées spécifiques à l'engine
- **options** (object): Options de compilation spécifiques
- **environment** (object): Variables d'environnement à injecter
- **timeout_seconds** (integer|null): Timeout du processus en secondes
- **output_dir** (string): Répertoire de sortie
- **open_output_on_success** (boolean): Ouvrir le répertoire après succès

## Gestion des erreurs

Le système est robuste aux erreurs:

- Les fichiers corrompus retournent le schéma par défaut
- Les répertoires manquants sont créés automatiquement
- Les erreurs d'I/O sont silencieuses (retour `False` ou `{}`)

```python
# Pas d'exception levée, retourne le schéma par défaut
config = manager.load("nonexistent", {"default": "value"})
# config = {"default": "value"}

# Pas d'exception levée, retourne False
success = manager.save("engine", None)  # None n'est pas un dict
# success = False
```

## Singleton global

Le gestionnaire est un singleton global:

```python
from engines_loader import get_config_manager

# Première initialisation
manager1 = get_config_manager()

# Retourne la même instance
manager2 = get_config_manager()

assert manager1 is manager2  # True
```

Pour réinitialiser (utile en tests):

```python
from engines_loader import reset_config_manager

reset_config_manager()
manager = get_config_manager()  # Nouvelle instance
```

## Intégration avec ExternalEngineManifest

Pour les engines externes, la configuration peut inclure les champs du manifeste:

```python
config = {
    "id": "external_engine",
    "program": "/path/to/executable",
    "default_args": ["--verbose"],
    "arg_style": "config_file",
    "config_key": "--config",
    "timeout_seconds": 600,
    "output_dir": "build",
    "open_output_on_success": True,
    "options": {
        "custom_option": "value"
    }
}

manager.save("external_engine", config)
```

## Localisation des fichiers

- **Répertoire par défaut:** `~/.pycompiler/`
- **Répertoire des engines:** `~/.pycompiler/engines/`
- **Fichier de configuration:** `~/.pycompiler/engines/{engine_id}.json`

Exemple:
```
~/.pycompiler/
├── engines/
│   ├── nuitka.json
│   ├── pyinstaller.json
│   └── cx_freeze.json
```

## Bonnes pratiques

1. **Définir un schéma par défaut** dans `config_schema`
2. **Charger au démarrage** de l'engine
3. **Sauvegarder après modifications** importantes
4. **Valider les données** avant de les utiliser
5. **Gérer les erreurs** gracieusement

```python
class MyEngine(CompilerEngine):
    config_schema = {
        "optimization": 2,
        "strip": False,
    }
    
    def __init__(self):
        super().__init__()
        try:
            self.config = self.load_config()
        except Exception as e:
            print(f"Failed to load config: {e}")
            self.config = self.config_schema.copy()
    
    def save_config_safe(self, config):
        try:
            return self.save_config(config)
        except Exception as e:
            print(f"Failed to save config: {e}")
            return False
```
