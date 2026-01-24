# 🏭 Engines Standalone Module

> Module autonome pour gérer et exécuter les moteurs de compilation PyCompiler ARK++ sans lancer l'application principale.

## 📋 Description

Ce module permet d'exécuter les moteurs de compilation (PyInstaller, Nuitka, cx_Freeze) de manière autonome, avec une interface graphique complète ou un mode CLI.

## 🚀 Utilisation

### Interface Graphique (GUI)

```bash
# Lancer l'interface GUI
python -m Core.engines_loader.engines_only_mod

# Avec un workspace spécifique
python -m Core.engines_loader.engines_only_mod /path/to/workspace

# Avec un thème spécifique
python -m Core.engines_loader.engines_only_mod --theme light
python -m Core.engines_loader.engines_only_mod --theme dark

# Avec une langue spécifique
python -m Core.engines_loader.engines_only_mod --language fr
python -m Core.engines_loader.engines_only_mod --language en
```

### Mode CLI

```bash
# Lister les moteurs disponibles
python -m Core.engines_loader.engines_only_mod --list-engines

# Vérifier la compatibilité d'un moteur
python -m Core.engines_loader.engines_only_mod --check-compat nuitka
python -m Core.engines_loader.engines_only_mod --check-compat pyinstaller
python -m Core.engines_loader.engines_only_mod --check-compat cx_freeze

# Mode dry-run (afficher la commande sans exécuter)
python -m Core.engines_loader.engines_only_mod --engine nuitka -f script.py --dry-run

# Compiler un fichier
python -m Core.engines_loader.engines_only_mod --engine nuitka -f script.py
```

### Via pycompiler_ark.py

```bash
# Lancer l'interface GUI
python -m pycompiler_ark engines

# Lister les moteurs
python -m pycompiler_ark engines --dry-run

# Avec un workspace
python -m pycompiler_ark engines /path/to/workspace
```

## 📁 Structure des Fichiers

```
engines_only_mod/
├── __init__.py      # Point d'entrée du module
├── __main__.py      # Point d'entrée CLI/GUI
├── app.py           # Logique métier (EnginesStandaloneApp)
├── gui.py           # Interface graphique (EnginesStandaloneGui)
└── README.md        # Cette documentation
```

## 🔧 Fonctionnalités

### Interface Graphique

- **Sélection du moteur** : Liste déroulante avec tous les moteurs disponibles
- **Sélection de fichier** : Navigateur pour choisir le fichier Python à compiler
- **Workspace** : Configuration du workspace du projet
- **Vérification de compatibilité** : Teste si le moteur est compatible avec le système
- **Compilation** : Exécution de la compilation avec sortie en temps réel
- **Logs** : Affichage des logs de compilation
- **Thèmes** : Support des thèmes clair et sombre
- **Langues** : Support de l'anglais et du français

### Mode CLI

- Liste des moteurs disponibles avec leur statut de compatibilité
- Vérification de compatibilité d'un moteur spécifique
- Mode dry-run pour tester les commandes

## 📦 Moteurs Disponibles

| Moteur | Description | Statut |
|--------|-------------|--------|
| `pyinstaller` | Compilation standard Python | ✅ Compatible |
| `nuitka` | Compilation haute performance | ✅ Compatible |
| `cx_freeze` | Support multi-plateforme | ✅ Compatible |

## 💻 Utilisation Programmatiquement

```python
# Import du module
from Core.engines_loader.engines_only_mod import EnginesStandaloneApp

# Création de l'application
app = EnginesStandaloneApp(
    engine_id="nuitka",
    file_path="/path/to/script.py",
    workspace_dir="/path/to/workspace",
    language="fr",
    theme="dark"
)

# Chargement des moteurs
engines = app.load_engines()
print(f"Moteurs disponibles : {len(engines)}")

# Vérification de compatibilité
result = app.check_engine_compatibility("nuitka")
print(f"Compatible : {result['compatible']}")

# Exécution de la compilation
result = app.run_compilation("nuitka", "/path/to/script.py")
print(f"Succès : {result['success']}")
```

## 🎨 Personnalisation

### Thèmes

Le module supporte deux thèmes :

- **dark** (défaut) : Thème sombre pour une utilisation confortable
- **light** : Thème clair pour les environnements lumineux

### Langues

Le module supporte deux langues :

- **en** (défaut) : Anglais
- **fr** : Français

## ⚠️ Notes

- Le module nécessite PySide6 pour l'interface graphique
- Les moteurs doivent être installés séparément (PyInstaller, Nuitka, cx_Freeze)
- La compatibilité des moteurs dépend de leur installation sur le système

## 📄 Licence

Ce projet est sous licence Apache 2.0.

---

PyCompiler ARK++ - Comprehensive Python compilation toolkit

