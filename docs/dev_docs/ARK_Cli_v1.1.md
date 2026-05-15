


Voici la SPEC CLI ARK 1.0 finale, version définitive et épurée. 

--- 

SPEC CLI ARK 1.0 

--- 

1. Philosophie 

La CLI est simple, prévisible, headless‑friendly. 

· Une seule binaire : ark
· Commandes explicites
· Pas de GUI spécialisée (tout est accessible en CLI)
· Pas de détection automatique dangereuse
· Reproductibilité stricte (verrous intégrés) 

--- 

2. Commandes finales 

```bash
# Workspace (utilisateur)
ark init --entry <path> [--icon <path>] [--with-venv] [--install-requirements] [--generate-requirements]
ark build
ark build --engine <id>
ark build --lock [file] 

# Exécution
ark run bcasl 

# GUI
ark gui
ark gui --legacy 

# Configuration (développeur)
ark set user-engine-dir <path>
ark set user-plugin-dir <path>
ark set dev-engine-dir <path>
ark set dev-plugin-dir <path> 

ark get user-engine-dir
ark get user-plugin-dir
ark get dev-engine-dir
ark get dev-plugin-dir 

ark unset user-engine-dir
ark unset user-plugin-dir
ark unset dev-engine-dir
ark unset dev-plugin-dir 

# Découverte
ark list engines
ark list plugins 

# Scaffolding
ark scaffold engine <name> [--path <dir>]
ark scaffold plugin-bcasl <name> [--path <dir>]
``` 

--- 

3. Ce qui est supprimé 

Suppression Raison
gui --bcasl, gui --engines, gui --classic, gui --ide Remplacé
config-auto, cfg-auto Dangereux
engine list, engine doctor Inutiles
workspace inspect, check, doctor, --info, --cli, unload Inutiles
ws init, ws config-auto Alias
BCASL GUI / Engines GUI Remplacées par CLI
ARK_Main_Config.yml Non supporté
.ark/pref.json Déplacé
ark init --create-main Projet existe déjà
ark init <path> Dossier courant uniquement
--entry pointant vers un dossier Doit être fichier
Création auto de dossier Dossier doit exister
--force Inutile
--yes Plus de questions interactives
Interaction dans --install-requirements Comportement déterministe 

--- 

4. GUI restantes 

GUI Commande Statut
IDE‑like GUI ark gui Active
Classic GUI ark gui --legacy Figée 

Message --legacy : 

```
⚠️ LIMITATION: The classic GUI does not support full UI feature integration.
For full functionality, use 'ark gui'.
``` 

--- 

5. Dossiers d'engines et plugins 

Dossier Rôle Emplacement
Core engines Engines fournis avec ARK ENGINES/
User engines Installés par l'utilisateur ~/ark_user/engines/ (défaut)
User plugins Installés par l'utilisateur ~/ark_user/plugins/ (défaut)
Dev engines En développement Optionnel (set dev-engine-dir)
Dev plugins En développement Optionnel (set dev-plugin-dir) 

Priorité de chargement : dev > user > core 

--- 

6. Configuration utilisateur (~/.arkconf/) 

```
~/.arkconf/
├── pref.json
├── user_engine_dir        # optionnel
├── user_plugin_dir        # optionnel
├── dev_engine_dir         # optionnel
└── dev_plugin_dir         # optionnel
``` 

Défauts : user-engine-dir = ~/ark_user/engines/ (créé auto)
Défauts : user-plugin-dir = ~/ark_user/plugins/ (créé auto) 

--- 

7. Dossier .ark/ dans un workspace 

```
.ark/
├── lock/
├── cache/
├── build/
└── logs/
``` 

--- 

8. Fichier ark.yml 

```yaml
project:
  name: mon_app
  version: 1.0.0
  entry: src/main.py 

workspace:
  exclude:
    - tests/**/*
    - __pycache__/**/* 

build:
  engine: nuitka
  output: dist/
  data:
    - source: plugins/
      destination: plugins/
  icon: assets/icon.ico   # optionnel
``` 

--- 

9. Validation de ark.yml avant build 

Champ Validation Niveau
project.name Présent, non vide Erreur
project.version Présent, format X.Y.Z Erreur
project.entry Présent, fichier existe Erreur
build.engine Présent, engine connu Erreur
build.output Présent, chemin valide Erreur
build.icon Optionnel, fichier existe si présent Warning
workspace.exclude Optionnel Ignoré
build.data Optionnel Ignoré 

Messages : 

```bash
# Erreur
ERROR: Invalid ark.yml
- project.name is required
- project.entry: file 'src/main.py' not found 

# Warning (non bloquant)
⚠️ Warning: Icon file 'assets/icon.ico' not found (ignored)
``` 

--- 

10. Détail des commandes 

ark init --entry <path> [options] 

Initialise le dossier courant. 

Prérequis : 

· Dossier courant existe
· --entry obligatoire, fichier existant (pas dossier) 

Options : 

Option Action
--entry <path> Définit project.entry
--icon <path> Définit build.icon (vérifie existence)
--with-venv Crée .ark/venv/
--generate-requirements Génère requirements.txt (erreur si existe)
--install-requirements Installe depuis requirements.txt (erreur si absent) 

Erreurs : 

```
ERROR: Current directory does not exist.
ERROR: Entry point must be a file, not a directory.
ERROR: Entry file 'src/main.py' not found.
ERROR: Icon file 'assets/icon.ico' not found.
ERROR: requirements.txt already exists. (--generate-requirements)
ERROR: requirements.txt not found. Run 'ark init --generate-requirements' first. (--install-requirements)
``` 

--- 

ark build 

Commande Comportement
ark build Valide + build avec engine par défaut
ark build --engine <id> Valide + build avec engine temporaire
ark build --lock [file] Rebuild strict (défaut: .ark/lock/latest.lock) 

Interdit : ark build --lock --engine <id> 

Message : 

```
ERROR: --engine cannot be used with --lock
If you need a different engine, create a new lock with: ark build --engine <engine_id>
``` 

--- 

ark run bcasl 

Options : --timeout, --parallel, --list-plugins 

--- 

ark gui 

· ark gui → IDE‑like GUI
· ark gui --legacy → Classic GUI (figée) 

--- 

ark set / get / unset 

```bash
ark set user-engine-dir <path>
ark set user-plugin-dir <path>
ark set dev-engine-dir <path>
ark set dev-plugin-dir <path> 

ark get <dir>
ark unset <dir>
``` 

--- 

ark list engines et ark list plugins 

Affiche dev > user > core. 

--- 

ark scaffold engine <name> [--path <dir>] 

--path Destination
Oui --path/<name>/
Non et dev-engine-dir défini dev-engine-dir/<name>/
Non et dev-engine-dir non défini Erreur 

Idem pour scaffold plugin-bcasl avec dev-plugin-dir. 

--- 

11. Aide 

ark --help 

```bash
Usage: ark <command> [options] 

Workspace:
  init --entry <path>     Initialize current directory
  build                   Build with engine from ark.yml
  build --engine <id>     Build with temporary engine
  build --lock [file]     Rebuild from lock 

Execution:
  run bcasl               Execute BCASL pipeline 

GUI:
  gui                     Launch IDE-like GUI
  gui --legacy            Launch classic GUI 

Options:
  --help, --version
``` 

ark --help-dev 

```bash
Developer commands:
  set/get/unset user-engine-dir, user-plugin-dir, dev-engine-dir, dev-plugin-dir
  list engines, list plugins
  scaffold engine <name> [--path <dir>]
  scaffold plugin-bcasl <name> [--path <dir>]
``` 

--- 

12. Règles finales 

ID Règle
CLI1-3 Pas de détection auto, 2 GUIs max
CLI4-5 --help et --help-dev séparés
CLI6-9 Scaffold, engine override, priorité dev>user>core
CLI10-11 Config dans ~/.arkconf/ fichiers texte
CLI12-13 .ark/ contient lock/cache/build/logs
CLI14-16 ark init exige --entry, fichier entry existant, ark.yml seul
CLI17-19 Init : dossier courant, --entry fichier, --icon vérifié
CLI20-22 --generate-requirements génère, --install-requirements installe, pas d'interaction
CLI23-24 Validation ark.yml avant build
CLI25-26 Icone optionnelle (warning), erreurs bloquantes (entry/engine) 

--- 

SPEC CLI ARK 1.0 — TERMINÉE ✅