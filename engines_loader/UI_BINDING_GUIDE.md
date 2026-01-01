# UI Binding System

## Vue d'ensemble

Le système de binding UI permet aux engines de lier automatiquement leurs widgets à la configuration persistante. Les changements dans l'UI sont sauvegardés automatiquement.

## Architecture

### UIBinding (Abstrait)

Classe de base pour tous les bindings. Chaque type de widget a sa propre implémentation:

- **LineEditBinding**: QLineEdit
- **CheckBoxBinding**: QCheckBox
- **ComboBoxBinding**: QComboBox
- **SpinBoxBinding**: QSpinBox
- **DoubleSpinBoxBinding**: QDoubleSpinBox
- **SliderBinding**: QSlider

### UIBindingManager

Gestionnaire centralisé pour tous les bindings d'un engine.

## Utilisation

### 1. Créer un engine avec UI

```python
from engines_loader import CompilerEngine

class MyEngine(CompilerEngine):
    id = "my_engine"
    name = "My Engine"
    
    config_schema = {
        "optimization": 2,
        "strip": False,
        "output_dir": "dist",
    }
    
    def __init__(self):
        super().__init__()
        self.ui_manager = None
    
    def create_tab(self, gui):
        from PySide6.QtWidgets import (
            QWidget, QVBoxLayout, QLabel, 
            QSpinBox, QCheckBox, QLineEdit
        )
        
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Créer le gestionnaire de binding
        self.ui_manager = self.create_ui_binding_manager()
        
        # === Optimization ===
        opt_label = QLabel("Optimization:")
        opt_spin = QSpinBox()
        opt_spin.setMinimum(0)
        opt_spin.setMaximum(3)
        layout.addWidget(opt_label)
        layout.addWidget(opt_spin)
        
        # Lier le widget à la config
        self.ui_manager.bind("optimization", opt_spin, "spinbox")
        
        # === Strip ===
        strip_cb = QCheckBox("Strip Binaries")
        layout.addWidget(strip_cb)
        
        # Lier la checkbox
        self.ui_manager.bind("strip", strip_cb, "checkbox")
        
        # === Output Dir ===
        out_label = QLabel("Output Directory:")
        out_edit = QLineEdit()
        layout.addWidget(out_label)
        layout.addWidget(out_edit)
        
        # Lier le lineedit
        self.ui_manager.bind("output_dir", out_edit, "lineedit")
        
        # Charger la config sauvegardée
        self.load_ui_from_config(self.ui_manager)
        
        layout.addStretch()
        return tab, gui.tr("My Engine", "My Engine")
    
    def build_command(self, gui, file: str) -> list[str]:
        # Récupérer la config depuis les widgets
        if self.ui_manager:
            config = self.ui_manager.save_to_config()
        else:
            config = self.load_config()
        
        cmd = ["my-compiler"]
        
        if config.get("optimization", 0) > 0:
            cmd.append(f"-O{config['optimization']}")
        
        if config.get("strip"):
            cmd.append("--strip")
        
        cmd.append(file)
        return cmd
```

### 2. Binding automatique

Le type de widget est détecté automatiquement:

```python
# Détection automatique
self.ui_manager.bind("key", widget)

# Ou spécifier explicitement
self.ui_manager.bind("key", widget, "spinbox")
```

### 3. Sauvegarde automatique

Les changements dans les widgets sont sauvegardés automatiquement:

```python
# Créer le manager (sauvegarde auto activée)
self.ui_manager = self.create_ui_binding_manager()

# Chaque changement de widget déclenche:
# 1. Récupération des valeurs
# 2. Appel du callback
# 3. Sauvegarde dans la config persistante
```

### 4. Charger la config sauvegardée

```python
# Charger et appliquer aux widgets
self.load_ui_from_config(self.ui_manager)

# Ou manuellement
config = self.load_config()
self.ui_manager.load_from_config(config)
```

## API UIBindingManager

### Méthodes principales

#### `bind(key, widget, binding_type=None) -> UIBinding`

Lie un widget à une clé de configuration.

```python
# Détection automatique
binding = manager.bind("optimization", spinbox)

# Type explicite
binding = manager.bind("optimization", spinbox, "spinbox")
```

**Types supportés:**
- `"lineedit"` - QLineEdit
- `"checkbox"` - QCheckBox
- `"combobox"` - QComboBox
- `"spinbox"` - QSpinBox
- `"doublespinbox"` - QDoubleSpinBox
- `"slider"` - QSlider

#### `load_from_config(config: Dict) -> None`

Charge les valeurs depuis un dictionnaire dans les widgets.

```python
config = {"optimization": 3, "strip": True}
manager.load_from_config(config)
```

#### `save_to_config() -> Dict`

Récupère les valeurs des widgets dans un dictionnaire.

```python
config = manager.save_to_config()
# {"optimization": 3, "strip": True, ...}
```

#### `on_config_changed(callback) -> None`

Enregistre un callback appelé à chaque changement.

```python
def on_change(config):
    print(f"Config changed: {config}")
    # Sauvegarder, valider, etc.

manager.on_config_changed(on_change)
```

#### `get_bindings() -> Dict[str, UIBinding]`

Retourne tous les bindings.

```python
bindings = manager.get_bindings()
for key, binding in bindings.items():
    print(f"{key}: {binding.get_value()}")
```

#### `unbind(key) -> bool`

Supprime un binding.

```python
manager.unbind("optimization")
```

#### `clear_bindings() -> None`

Supprime tous les bindings.

```python
manager.clear_bindings()
```

## Exemple complet

```python
from engines_loader import CompilerEngine

class AdvancedEngine(CompilerEngine):
    id = "advanced"
    name = "Advanced Engine"
    
    config_schema = {
        "enabled": True,
        "optimization": 2,
        "strip": False,
        "output_dir": "dist",
        "timeout": 300,
        "profile": "Release",
    }
    
    def __init__(self):
        super().__init__()
        self.ui_manager = None
    
    def create_tab(self, gui):
        from PySide6.QtWidgets import (
            QWidget, QVBoxLayout, QHBoxLayout,
            QLabel, QSpinBox, QCheckBox, 
            QLineEdit, QComboBox
        )
        
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Créer le manager
        self.ui_manager = self.create_ui_binding_manager()
        
        # Optimization
        opt_row = QHBoxLayout()
        opt_spin = QSpinBox()
        opt_spin.setRange(0, 3)
        opt_row.addWidget(QLabel("Optimization:"))
        opt_row.addWidget(opt_spin)
        opt_row.addStretch()
        layout.addLayout(opt_row)
        self.ui_manager.bind("optimization", opt_spin)
        
        # Strip
        strip_cb = QCheckBox("Strip Binaries")
        layout.addWidget(strip_cb)
        self.ui_manager.bind("strip", strip_cb)
        
        # Output Dir
        out_row = QHBoxLayout()
        out_edit = QLineEdit()
        out_row.addWidget(QLabel("Output:"))
        out_row.addWidget(out_edit)
        layout.addLayout(out_row)
        self.ui_manager.bind("output_dir", out_edit)
        
        # Timeout
        timeout_row = QHBoxLayout()
        timeout_spin = QSpinBox()
        timeout_spin.setRange(1, 3600)
        timeout_row.addWidget(QLabel("Timeout:"))
        timeout_row.addWidget(timeout_spin)
        timeout_row.addStretch()
        layout.addLayout(timeout_row)
        self.ui_manager.bind("timeout", timeout_spin)
        
        # Profile
        profile_row = QHBoxLayout()
        profile_combo = QComboBox()
        profile_combo.addItems(["Debug", "Release", "RelWithDebInfo"])
        profile_row.addWidget(QLabel("Profile:"))
        profile_row.addWidget(profile_combo)
        profile_row.addStretch()
        layout.addLayout(profile_row)
        self.ui_manager.bind("profile", profile_combo)
        
        # Charger la config
        self.load_ui_from_config(self.ui_manager)
        
        layout.addStretch()
        return tab, "Advanced"
    
    def build_command(self, gui, file: str) -> list[str]:
        config = self.ui_manager.save_to_config() if self.ui_manager else self.load_config()
        
        cmd = ["advanced-compiler"]
        
        if config.get("optimization", 0) > 0:
            cmd.append(f"-O{config['optimization']}")
        
        if config.get("strip"):
            cmd.append("--strip")
        
        cmd.extend(["-o", config.get("output_dir", "dist")])
        cmd.append(f"--profile={config.get('profile', 'Release')}")
        cmd.append(file)
        
        return cmd
```

## Flux de données

```
User modifie widget
    ↓
UIBinding détecte le changement
    ↓
Callback UIBindingManager appelé
    ↓
save_to_config() récupère toutes les valeurs
    ↓
Callback on_config_changed() appelé
    ↓
Engine.save_config() sauvegarde dans ~/.pycompiler/engines/{id}.json
```

## Bonnes pratiques

1. **Créer le manager dans create_tab()**
   ```python
   self.ui_manager = self.create_ui_binding_manager()
   ```

2. **Lier tous les widgets pertinents**
   ```python
   self.ui_manager.bind("key", widget)
   ```

3. **Charger la config sauvegardée**
   ```python
   self.load_ui_from_config(self.ui_manager)
   ```

4. **Utiliser la config dans build_command()**
   ```python
   config = self.ui_manager.save_to_config() if self.ui_manager else self.load_config()
   ```

5. **Gérer les cas sans UI**
   ```python
   if self.ui_manager:
       config = self.ui_manager.save_to_config()
   else:
       config = self.load_config()
   ```

## Détection automatique de type

Le système détecte automatiquement le type de widget:

```python
# Pas besoin de spécifier le type
self.ui_manager.bind("key", spinbox)  # Détecte QSpinBox
self.ui_manager.bind("key", checkbox)  # Détecte QCheckBox
self.ui_manager.bind("key", lineedit)  # Détecte QLineEdit
```

## Gestion d'erreurs

Tous les bindings gèrent les erreurs gracieusement:

```python
# Pas d'exception levée
binding.set_value(None)  # Ignore silencieusement
binding.get_value()  # Retourne une valeur par défaut
```
