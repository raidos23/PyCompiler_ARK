# PyCompiler ARK++ Build System Update

## Overview

Les scripts de build ont été mis à jour pour garantir que:

1. **Standalone uniquement** - Tous les builds créent des exécutables autonomes avec toutes les dépendances incluses
2. **Vérification des dépendances** - Les dépendances sont automatiquement analysées et incluses
3. **Exclusion des répertoires** - Les dossiers `Plugins/` et `ENGINES/` sont exclus de la compilation

## Fichiers modifiés

### Scripts de build
- `build_pyinstaller.py` - PyInstaller build script (standalone)
- `build_nuitka.py` - Nuitka build script (standalone)
- `build_cxfreeze.py` - cx_Freeze build script (standalone)
- `build_briefcase.py` - Briefcase build script (standalone)
- `build_pynsist.py` - pynsist build script (Windows standalone installer)

### Nouveaux fichiers
- `build_utils.py` - Utilitaires partagés pour l'analyse des dépendances
- `verify_build.py` - Script de vérification avant la compilation

## Utilisation

### 1. Vérifier que le projet est prêt pour la compilation

```bash
python verify_build.py
```

Cela va:
- Vérifier que toutes les dépendances requises sont installées
- Analyser la structure du projet
- Confirmer que les répertoires à exclure sont correctement identifiés

### 2. Compiler avec le tool de votre choix

#### PyInstaller (recommandé pour la plupart des cas)
```bash
python build_pyinstaller.py
```

#### Nuitka (meilleure performance)
```bash
python build_nuitka.py
```

#### cx_Freeze (cross-platform)
```bash
python build_cxfreeze.py
```

#### Briefcase (native installers)
```bash
python build_briefcase.py
```

#### pynsist (Windows installer avec Python bundlé)
```bash
python build_pynsist.py
```

## Configuration des builds

### Dépendances incluses automatiquement

Les packages suivants sont automatiquement inclus dans tous les builds:
- PySide6 / shiboken6 (Qt framework)
- psutil (system utilities)
- PyYAML (configuration)
- Pillow (image processing)
- jsonschema (validation)

### Packages locaux inclus

Les packages locaux suivants sont inclus:
- `Core/` - Core application logic
- `engine_sdk/` - Engine SDK
- `ENGINES/` - Compilation engines (cx_Freeze, Nuitka, PyInstaller)
- `bcasl/` - BCASL language support
- `Plugins_SDK/` - Plugin SDK

### Répertoires exclus de la compilation

Les répertoires suivants sont **exclus** de la compilation:
- `Plugins/` - Plugin implementations (loaded dynamically at runtime)
- `ENGINES/` - Engine implementations (loaded dynamically at runtime)
- `__pycache__/` - Python cache
- `.git/` - Git repository
- `.venv/` - Virtual environment
- `build/` - Build artifacts
- `dist/` - Distribution artifacts
- `Tests/` - Test files

### Fichiers de données inclus

Les répertoires de données suivants sont inclus dans tous les builds:
- `themes/` - Application themes
- `languages/` - Localization files
- `logo/` - Application logos and icons
- `ui/` - UI definition files

## Architecture des builds

### Mode Standalone

Tous les builds utilisent le mode **standalone**, ce qui signifie:
- L'exécutable inclut toutes les dépendances Python
- Aucune installation Python n'est requise sur la machine cible
- L'application est complètement autonome

### Exclusion des répertoires dynamiques

Les répertoires `Plugins/` et `ENGINES/` sont exclus car:
- Ils contiennent des implémentations qui sont chargées dynamiquement à l'exécution
- Ils ne sont pas nécessaires pour la compilation
- Cela réduit la taille de l'exécutable final

## Analyse des dépendances

Le module `build_utils.py` fournit:

### DependencyAnalyzer
- Analyse automatique des imports Python
- Distinction entre stdlib, packages locaux et packages externes
- Validation des dépendances requises
- Génération de patterns d'exclusion

### Fonctions utilitaires
- `check_dependencies()` - Vérifie que toutes les dépendances sont disponibles
- `get_build_config(tool_name)` - Retourne la configuration pour un tool spécifique

## Exemple de sortie de vérification

```
======================================================================
🔍 PyCompiler ARK++ Build Verification
======================================================================

📊 Analyzing project dependencies...

✅ External packages found: 6
   • PIL
   • PySide6
   • jsonschema
   • psutil
   • shiboken6
   • yaml

🔍 Validating required packages...
   ✅ PySide6
   ✅ shiboken6
   ✅ psutil
   ✅ yaml
   ✅ PIL
   ✅ jsonschema

✅ All required packages are available!

📁 Project Structure Analysis:

✅ Directories to exclude from build:
   • ENGINES/
   • Plugins/
   • Tests/
   • __pycache__/
   • build/
   • dist/
   ...

✅ Local packages to include:
   ✓ Core/
   ✓ engine_sdk/
   ✓ ENGINES/
   ✓ bcasl/
   ✓ Plugins_SDK/

✅ Data directories to include:
   ✓ themes/
   ✓ languages/
   ✓ logo/
   ✓ ui/

✅ Main entry points:
   ✓ pycompiler_ark.py
   ✓ main.py

======================================================================
✅ Build verification completed successfully!
======================================================================
```

## Troubleshooting

### Dépendances manquantes

Si vous recevez une erreur concernant des dépendances manquantes:

```bash
pip install -r requirements.txt
```

### Build échoue avec des modules manquants

Vérifiez que `build_utils.py` est dans le même répertoire que les scripts de build.

### Taille de l'exécutable trop grande

Cela est normal pour les builds standalone. Les options d'optimisation dans chaque script peuvent être ajustées:
- PyInstaller: Augmentez `--noupx` ou utilisez UPX
- Nuitka: Augmentez `--lto` ou utilisez `--follow-imports=all`
- cx_Freeze: Augmentez le niveau d'optimisation

## Notes importantes

1. **Plugins et Engines dynamiques**: Les répertoires `Plugins/` et `ENGINES/` ne sont pas compilés car ils sont chargés dynamiquement à l'exécution. Cela permet à l'application d'être extensible sans recompilation.

2. **Taille de l'exécutable**: Les builds standalone incluent toutes les dépendances, ce qui rend l'exécutable plus volumineux qu'une installation Python standard. C'est le compromis pour l'autonomie.

3. **Compatibilité**: Tous les builds sont testés sur Windows, macOS et Linux. Certains tools (comme pynsist) sont spécifiques à une plateforme.

4. **Performance**: Nuitka offre généralement les meilleures performances car il compile le code Python en C. PyInstaller est plus rapide à compiler mais l'exécutable est plus lent.

## Support

Pour plus d'informations sur chaque tool de build:
- [PyInstaller Documentation](https://pyinstaller.org/)
- [Nuitka Documentation](https://nuitka.net/)
- [cx_Freeze Documentation](https://cx-freeze.readthedocs.io/)
- [Briefcase Documentation](https://briefcase.readthedocs.io/)
- [pynsist Documentation](https://pynsist.readthedocs.io/)
