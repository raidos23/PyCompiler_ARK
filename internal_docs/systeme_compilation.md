# Documentation Détaillée du Système de Compilation PyCompiler ARK

## Vue d'ensemble

PyCompiler ARK est un compilateur Python multi-moteurs qui transforme des scripts Python en exécutables autonomes. Cette documentation détaille le fonctionnement interne pour faciliter le debugging et la maintenance.

## Architecture Générale

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Interface     │    │  Orchestrateur   │    │   Moteurs de    │
│   Utilisateur   │◄──►│   Processus      │◄──►│   Compilation   │
│   (PySide6)     │    │ (mainprocess.py) │    │ (ENGINES/)      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   File d'attente│    │  Gestion QProcess│    │   Génération    │
│   (queue)       │    │  + Timeouts      │    │   Commandes     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                       │
                                                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Auto_Command_   │    │   Mappings JSON  │    │   Détection     │
│ Builder         │◄──►│   (mapping.json) │◄──►│   Modules       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Variables Globales à Surveiller (Debugging)

### Dans mainprocess.py :
- `self.processes` : Liste des QProcess actifs
- `self.queue` : File d'attente [(file, to_compile), ...]
- `self.current_compiling` : Set des fichiers en cours
- `self._pending_engine_success_hooks` : Hooks de succès en attente
- `self._last_success_files` : Derniers fichiers réussis par moteur
- `self._compilation_times` : Temps de compilation par fichier

### Dans Auto_Command_Builder :
- `_MAPPING_CACHE` : Cache des mappings JSON
- `_VALIDATION_WARNINGS` : Avertissements de validation
- `ALIASES_IMPORT_TO_PACKAGE` : Alias import → package
- `PACKAGE_TO_IMPORT_NAME` : Package → nom d'import canonique

## Processus de Compilation Détaillé

### Phase 1: Initiation (`try_start_processes()` - lignes 89-130)

**Code référence** :
```python
def try_start_processes(self):
    while len(self.processes) < MAX_PARALLEL and self.queue:
        file, to_compile = self.queue.pop(0)
        if to_compile:
            self.start_compilation_process(file)
```

**Debugging** :
- Vérifier `len(self.processes)` et `MAX_PARALLEL`
- Inspecter `self.queue` pour les fichiers en attente
- Logs attendus : "✔️ Toutes les compilations sont terminées."

**Erreurs communes** :
- File d'attente vide mais processus bloqués : Vérifier `self.processes`
- MAX_PARALLEL ignoré : Contrôler `from ..preferences import MAX_PARALLEL`

### Phase 2: Génération des Commandes (`start_compilation_process()` - lignes 133-300+)

**Important** : `mainprocess.py` NE génère PAS les commandes !

**Flux de génération** :
```
start_compilation_process()
    ↓
Détermination moteur (lignes 143-150)
    ↓
Instanciation moteur (lignes 153-158)
    ↓
Vérifications préliminaires (lignes 161-167)
    ↓
Récupération commande (lignes 170-175) ← APPEL AU MOTEUR
    ↓
Configuration QProcess (lignes 200-250)
    ↓
Lancement (ligne 300+)
```

**Code référence** :
```python
# Ligne 170-175 : Récupération commande
prog_args = engine.program_and_args(self, file)
if not prog_args:
    return
program, args = prog_args
```

**Qui génère réellement ?**
- Le moteur instancié via `engine.program_and_args()`
- Cette méthode appelle `engine.build_command()`

**Exemple Nuitka détaillé** (`ENGINES/nuitka/__init__.py` lignes 60-90) :
```python
def build_command(self, gui, file: str) -> list[str]:
    # Ligne 62-65 : Base commande
    cmd = [python_path, "-m", "nuitka"]

    # Ligne 67-72 : Options UI
    if self._get_opt("standalone").isChecked():
        cmd.append("--standalone")
    if self._get_opt("onefile").isChecked():
        cmd.append("--onefile")

    # Ligne 75-80 : Auto-détection
    auto_map = compute_for_all(self) or {}
    auto_nuitka_args = auto_map.get("nuitka", [])
    cmd.extend(auto_nuitka_args)

    # Ligne 82 : Fichier cible
    cmd.append(file)
    return cmd
```

**Debugging Phase 2** :
- Vérifier `engine_id` (pyinstaller/nuitka/cx_freeze)
- Tester `engine.ensure_tools_installed(self)`
- Inspecter retour de `engine.preflight(self, file)`
- Logs attendus : "▶️ Lancement compilation [Moteur] : fichier.py"

**Erreurs communes** :
- "Impossible d'instancier le moteur" : Vérifier `engines_loader.registry`
- Outils manquants : Contrôler `engine.ensure_tools_installed()`
- Preflight échoue : Vérifier permissions fichier/dossier

### Phase 3: Détection Automatique des Modules

**Flux de détection** (`Core/Auto_Command_Builder/auto_build.py`) :
```
compute_for_all() → compute_auto_for_engine()
    ↓
_detect_modules_preferring_requirements()
    ↓
_match_with_requirements_aware()
    ↓
builder() → Liste d'arguments
```

**Sources par priorité** :
1. `requirements.txt` (fonction `_parse_requirements()`)
2. `pyproject.toml` (PEP 621/Poetry)
3. Analyse AST des imports Python

**Mappings JSON** :
- Emplacement : `ENGINES/{engine_id}/mapping.json`
- Format : `{"numpy": {"nuitka": ["--collect-all", "numpy"]}}`

**Debugging Phase 3** :
- Vérifier présence `requirements.txt` ou `pyproject.toml`
- Tester `_scan_imports(selected_files, workspace_dir)`
- Inspecter `_MAPPING_CACHE` et `_VALIDATION_WARNINGS`
- Logs attendus : "🔎 Auto-détection des modules sensibles (nuitka) activée."

**Erreurs communes** :
- Modules non détectés : Vérifier syntaxe `requirements.txt`
- Mapping invalide : Contrôler JSON Schema dans `schemas/mapping.schema.json`

### Phase 4: Exécution (`QProcess` - lignes 200-300)

**Configuration QProcess** :
```python
process = QProcess(self)
process.setProgram(program)
process.setArguments(args)
process.setWorkingDirectory(self.workspace_dir)
```

**Gestion Timeouts** (lignes 260-290) :
- Timeout par défaut : 1800s (30min)
- Configurable via `PYCOMPILER_PROCESS_TIMEOUT`
- Arrêt propre puis kill forcé

**Signaux connectés** :
- `readyReadStandardOutput` → `handle_stdout()`
- `readyReadStandardError` → `handle_stderr()`
- `finished` → `handle_finished()`

**Debugging Phase 4** :
- Vérifier `program` et `args` avant `process.start()`
- Surveiller `process.state()` (NotRunning/Starting/Running)
- Tester variables d'environnement avec `process.setProcessEnvironment()`
- Logs attendus : Commande masquée dans logs

**Erreurs communes** :
- Processus ne démarre pas : Vérifier chemin `program`
- Timeout prématuré : Ajuster `PYCOMPILER_PROCESS_TIMEOUT`
- Erreurs stdout/stderr : Examiner `handle_stdout()` et `handle_stderr()`

### Phase 5: Finalisation (`handle_finished()` - lignes 400-500)

**Code référence** :
```python
def handle_finished(self, process, exit_code, exit_status):
    # Nettoyage timers
    # Mesure temps et mémoire
    # Gestion succès/échec
    if exit_code == 0:
        # Hooks de succès
        for eng, fpath in self._pending_engine_success_hooks:
            eng.on_success(self, fpath)
```

**Actions finales** :
- Nettoyage `self.processes` et `self.current_compiling`
- Exécution hooks `on_success()` des moteurs
- Mise à jour UI et sauvegarde préférences
- Rapport performances si activé

**Debugging Phase 5** :
- Vérifier `exit_code` et `exit_status`
- Inspecter `self._pending_engine_success_hooks`
- Tester `eng.on_success(self, fpath)` individuellement
- Logs attendus : "✅ fichier.py compilé avec succès."

**Erreurs communes** :
- Hooks qui échouent : Attraper exceptions dans `on_success()`
- UI non mise à jour : Vérifier `self.set_controls_enabled(True)`
- Rapport non généré : Contrôler `PYCOMPILER_AUTO_REPORT=1`

## Conseils de Debugging Pratiques

### Commandes de Test
```bash
# Tester génération commande sans exécution
python -c "
from ENGINES.nuitka import NuitkaEngine
engine = NuitkaEngine()
cmd = engine.build_command(None, 'test.py')
print('Commande:', cmd)
"

# Vérifier mappings
python -c "
from Core.Auto_Command_Builder.auto_build import compute_for_all
class MockGUI:
    workspace_dir = '.'
    selected_files = ['test.py']
result = compute_for_all(MockGUI())
print('Auto-args:', result)
"
```

### Points de Surveillance
- **Avant compilation** : `self.queue`, `len(self.processes)`
- **Pendant génération** : `engine_id`, retour `program_and_args()`
- **Pendant exécution** : `process.processId()`, `process.state()`
- **Après finalisation** : `exit_code`, hooks exécutés

### Logs à Activer
- Définir `PYCOMPILER_AUTO_REPORT=1` pour rapports détaillés
- Vérifier masquage secrets avec `redact_secrets()`
- Surveiller avertissements dans `_VALIDATION_WARNINGS`

### Scénarios de Debug Courants

1. **Compilation ne démarre pas**
   - Vérifier `self.queue` et `MAX_PARALLEL`
   - Tester `engine.preflight()` et `engine.ensure_tools_installed()`

2. **Commande incorrecte**
   - Inspecter retour `engine.program_and_args()`
   - Vérifier mappings JSON et détection modules

3. **Timeout intempestif**
   - Contrôler `PYCOMPILER_PROCESS_TIMEOUT`
   - Surveiller progression dans `handle_stdout()`

4. **Échec silencieux**
   - Examiner `handle_stderr()` pour erreurs cachées
   - Tester commande manuellement dans terminal

5. **Hooks de succès non exécutés**
   - Vérifier `self._pending_engine_success_hooks`
   - Tester `eng.on_success()` individuellement

## Fichiers de Référence Détaillés

- `Core/Compiler/mainprocess.py` :
  - `try_start_processes()` (l.89) : Gestion file d'attente
  - `start_compilation_process()` (l.133) : Lancement compilation
  - `handle_finished()` (l.400) : Finalisation

- `Core/Auto_Command_Builder/auto_build.py` :
  - `compute_for_all()` (l.350) : Détection globale
  - `compute_auto_for_engine()` (l.400) : Par moteur
  - `_detect_modules_preferring_requirements()` (l.500) : Détection modules

- `ENGINES/nuitka/__init__.py` :
  - `build_command()` (l.60) : Construction commande
  - `program_and_args()` (l.95) : Interface QProcess

- `engine_sdk/base.py` : Interface commune des moteurs

---

*Documentation détaillée pour debugging - PyCompiler ARK Internal Docs v2.0*
