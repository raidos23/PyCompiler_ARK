Voici la SPEC ARK Locking 1.0 mise à jour avec la section ark build --lock. 

--- 

ARK LOCKING SPEC 1.0 

--- 

1. Rôle du Lock 

Le lock est un snapshot figé de l'intention du projet et de l'environnement. 

Il garantit la reproductibilité : même lock → même artefact. 

--- 

2. Déclenchement 

Commande Génère un lock ?
ark build ✅ Oui (implicite)
ark build --lock ❌ Non (utilise un lock existant) 

--- 

3. Fichiers de lock 

```
.ark/lock/
├── ARK_YYYY_MM_DD_NNN.lock.yml
└── latest.lock.yml
``` 

Fichier Rôle Versionné
ARK_*.lock.yml Snapshot immuable ✅ Oui
latest.lock.yml Alias du dernier lock ✅ Oui 

--- 

4. Exemple de lock annoté 

```yaml
# build_id: généré par ARK (date + séquence)
build_id: ARK_2026_05_08_001 

project:
  # name → copié depuis ark.yml → project.name
  name: MonApp
  # version → copié depuis ark.yml → project.version
  version: 1.0.0
  # entry → copié depuis ark.yml → project.entry
  entry: src/main.py 

workspace:
  # exclude_patterns → copié depuis ark.yml → workspace.exclude
  exclude_patterns:
    - tests/**/*
    - __pycache__/**/* 

build:
  # output → copié depuis ark.yml → build.output
  output: dist/
  # data → copié depuis ark.yml → build.data
  data:
    - source: plugins/
      destination: plugins/
  # icon → copié depuis ark.yml → build.icon (optionnel)
  icon: assets/icon.ico 

engine:
  # name → copié depuis ark.yml → build.engine
  name: nuitka
  # version → résolu par ARK (version installée de l'engine)
  version: 2.4.1
  # config → copié depuis .ark/config/nuitka/config.json
  config:
    optimize: 2
    standalone: true 

platform:
  # os → snapshot environnement (sys.platform)
  os: windows
  # arch → snapshot environnement (platform.machine)
  arch: x86_64
  # python_version → snapshot environnement (sys.version)
  python_version: 3.11.9 

dependencies:
  # → snapshot des packages installés (pip freeze)
  PySide6: 6.7.2
  requests: 2.32.3 

# workspace_hash → calculé par ARK (hash des fichiers inclus après exclusion)
workspace_hash: sha256:4a5b6c7d8e9f0a1b2c3d...
``` 

--- 

5. Détail des champs avec sources 

Champ Source Figé
build_id Généré par ARK ✅
project.name ark.yml → project.name ✅
project.version ark.yml → project.version ✅
project.entry ark.yml → project.entry ✅
workspace.exclude_patterns ark.yml → workspace.exclude ✅
build.output ark.yml → build.output ✅
build.data ark.yml → build.data ✅
build.icon ark.yml → build.icon ✅
engine.name ark.yml → build.engine ✅
engine.version Résolu par ARK (version installée) ✅
engine.config .ark/config/<engine>/config.json ✅
platform.os Snapshot environnement ✅
platform.arch Snapshot environnement ✅
platform.python_version Snapshot environnement ✅
dependencies Snapshot pip freeze ✅
workspace_hash Calculé par ARK ✅ 

--- 

6. Ce qui n'est PAS dans le lock 

Élément Raison
timestamp Casserait la reproductibilité
git.commit Optionnel (dépend si git est utilisé) 

--- 

7. Génération du lock 

Lors de ark build, ARK : 

1. Lit ark.yml
2. Applique workspace.exclude pour déterminer les fichiers inclus
3. Calcule workspace_hash (hash des fichiers inclus)
4. Lit .ark/config/<engine>/config.json pour les options de l'engine
5. Résout la version de l'engine installée
6. Snapshot l'environnement (OS, arch, Python, dépendances)
7. Génère un build_id unique (date + séquence)
8. Écrit ARK_<build_id>.lock.yml
9. Met à jour latest.lock.yml 

--- 

8. Utilisation du lock 

Build pur (ark build) 

→ Génère un lock, puis construit 

Rebuild strict (ark build --lock) 

→ Lit le lock, construit sans regénérer
→ Ne lit pas ark.yml
→ Ne lit pas .ark/config/
→ Ne snapshot pas l'environnement 

--- 

9. Comportement de ark build --lock (re-génération + comparaison) 

Lors d'un rebuild, ARK regénère un lock à partir de l'état actuel (comme pour ark build) mais ne l'utilise pas pour le build. 

Processus : 

1. Lit le lock fourni par l'utilisateur (ex: latest.lock.yml)
2. Build à partir de ce lock
3. Regénère un nouveau lock à partir de ark.yml + environnement actuel
4. Compare le lock utilisé et le lock généré
5. Stocke le nouveau lock dans .ark/cache/rebuild.lock/ 

Structure : 

```
.ark/cache/
└── rebuild.lock/
    └── ARK_2026_05_08_002.lock.yml    # lock généré pendant le rebuild
``` 

Résultat de la comparaison : 

Résultat Action
Locks identiques ✅ Build réussi, environnement cohérent
Locks différents ⚠️ Warning (ou échec selon configuration) 

Exemple : 

```bash
# Environnement inchangé
ark build --lock .ark/lock/latest.lock.yml
# → [OK] Locks identiques 

# Environnement modifié (nouvelle dépendance installée)
ark build --lock .ark/lock/latest.lock.yml
# → [WARNING] Lock mismatch
# → Nouveau lock dans .ark/cache/rebuild.lock/ARK_2026_05_08_002.lock.yml
``` 

--- 

10. Règles fondamentales 

Règle Explication
L1 Pas de timestamp dans le lock
L2 latest.lock.yml est versionné
L3 Le lock contient workspace_hash
L4 Le lock contient la configuration figée de l'engine
L5 Deux locks identiques → deux builds identiques
L6 Le lock est la seule source de vérité pour ark build --lock
L7 ark build --lock régénère un lock et le compare avec celui utilisé 

--- 

11. Comparaison des commandes 

ark build ark build --lock
Lit ark.yml ✅ ❌
Lit .ark/config/ ✅ ❌
Snapshot environnement ✅ ✅ (pour comparaison)
Génère un lock ✅ ✅ (stocké dans cache/rebuild.lock)
Utilise un lock pour build ❌ ✅
Compare les locks ❌ ✅ 

--- 

12. Workflow typique 

```bash
# Développement : génère lock + compile
ark build 

# Commit du lock
git add .ark/lock/
git commit -m "build: lock v1.0.0" 

# CI : rebuild strict
ark build --lock .ark/lock/latest.lock.yml
# → Vérifie que l'environnement CI est cohérent
# → Si warning, alerter l'équipe
``` 

--- 

Fin de la SPEC ARK Locking 1.0

