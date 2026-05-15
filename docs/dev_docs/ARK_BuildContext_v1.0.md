Voici la SPEC BuildContext 1.0 mise à jour avec la précision cruciale sur la source des données. 

--- 

SPEC BuildContext 1.0 

--- 

1. Définition 

Le BuildContext est la structure de données qu'ARK transmet à la méthode build_command de l'engine. 

L'engine ne lit aucun fichier source (ark.yml, lock.yml, etc.). Il reçoit uniquement ce contexte. 

L'engine ne sait pas si le contexte vient d'un ark.yml ou d'un lock.yml. 

--- 

2. Deux modes de construction 

Commande Source du BuildContext
ark build Construit depuis ark.yml + environnement
ark build --lock Construit depuis lock.yml uniquement 

Le BuildContext final est identique dans les deux cas. 

--- 

3. Rappel : ark.yml (ce que l'utilisateur écrit) 

```yaml
project:
  name: MonApp
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
  icon: assets/icon.ico
``` 

--- 

4. Structure du BuildContext 

```yaml
project_name: MonApp
entry_point: src/main.py
output_dir: dist/ 

exclude_patterns:
  - tests/**/*
  - __pycache__/**/* 

data_mappings:
  - source: plugins/
    destination: plugins/ 

icon: assets/icon.ico   # optionnel
``` 

--- 

5. Correspondance selon le mode 

BuildContext Source en ark build Source en ark build --lock
project_name ark.yml → project.name lock.yml → project.name
entry_point ark.yml → project.entry lock.yml → project.entry
output_dir ark.yml → build.output lock.yml → build.output
exclude_patterns ark.yml → workspace.exclude lock.yml → workspace.exclude_patterns
data_mappings ark.yml → build.data lock.yml → build.data
icon ark.yml → build.icon lock.yml → build.icon 

--- 

6. Description des champs 

Champ Type Description
project_name string Nom du projet (sert à nommer l'exécutable)
entry_point string Fichier principal à exécuter (chemin relatif)
output_dir string Répertoire où déposer l'artefact final
exclude_patterns list[string] Motifs (glob) des fichiers à ne PAS compiler
data_mappings list[{source, destination}] Fichiers/dossiers à copier en brut (non compilés)
icon string (optionnel) Chemin vers le fichier icône 

--- 

7. Contrat pour l'engine 

L'engine doit : 

1. Compiler tous les fichiers du projet sauf ceux qui matchent exclude_patterns
2. Copier les fichiers/dossiers de data_mappings (source → destination) dans output_dir
3. Appliquer l'icône à l'exécutable si icon est présent
4. Nommer l'exécutable avec project_name (MonApp.exe sur Windows, MonApp sur Unix)
5. Placer tous les artefacts dans output_dir 

--- 

8. Conversion interne 

L'engine est responsable de convertir ces données génériques en ses propres options. 

Contexte Converti en (exemple Nuitka)
exclude_patterns: ["tests/**/*"] --nofollow-import-to=tests
data_mappings: [{source: "plugins/", destination: "plugins/"}] --include-data-dir=plugins/=plugins/
icon: "assets/icon.ico" --windows-icon-from-ico=assets/icon.ico 

Contexte Converti en (exemple PyInstaller)
exclude_patterns: ["tests/**/*"] --exclude-module tests
data_mappings: [{source: "plugins/", destination: "plugins/"}] --add-data "plugins/;plugins/"
icon: "assets/icon.ico" --icon assets/icon.ico 

--- 

9. Ce que l'engine ne doit PAS faire 

Interdiction Pourquoi
Scanner le projet pour ajouter des fichiers L'engine ne décide pas
Ignorer exclude_patterns Rupture de reproductibilité
Ignorer data_mappings Rupture du contrat
Ignorer icon Rupture du contrat
Tenter de savoir si le contexte vient d'un lock ou non Inutile, cela ne change rien 

--- 

10. Exemple d'implémentation 

```python
from engine_sdk import CompilerEngine, engine_register, BuildContext 

@engine_register
class NuitkaEngine(CompilerEngine):
    id = "nuitka"
    name = "Nuitka"
    version = "2.4.1" 

    def build_command(self, context: BuildContext) -> list:
        cmd = ["nuitka", context.entry_point]
        
        for pattern in context.exclude_patterns:
            module = pattern.replace("/**/*", "").replace("**/*", "")
            cmd.append(f"--nofollow-import-to={module}")
        
        for mapping in context.data_mappings:
            cmd.append(f"--include-data-dir={mapping.source}={mapping.destination}")
        
        if context.icon:
            cmd.append(f"--windows-icon-from-ico={context.icon}")
        
        cmd.append(f"--output-dir={context.output_dir}")
        cmd.append(f"--output-filename={context.project_name}")
        
        return cmd
``` 

--- 

11. Règles 

Règle Explication
B1 L'engine ne lit ni ark.yml ni lock.yml
B2 L'engine reçoit uniquement le BuildContext dans build_command
B3 Le BuildContext est construit soit depuis ark.yml, soit depuis lock.yml
B4 L'engine ne peut pas savoir (et n'a pas besoin de savoir) la source
B5 L'engine convertit le contexte en ses propres options
B6 L'engine compile tout sauf exclude_patterns
B7 L'engine copie tous les data_mappings
B8 L'engine applique l'icône si présente 

--- 

Fin de la SPEC BuildContext 1.0

