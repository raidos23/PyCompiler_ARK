
### Logique Bcasl [x]

faire que la logique bcasl soit parfaitement aligner avec les capacités presumé de la guibcasl dans Ui/Gui/Dialogs/BcaslDialog.py . en exemple : la gui permet de desactiver toute une section de plugin donc le system bcasl doit prendre en charge que quadn une section est desactiver on la lance passe etc. et lon doit faire de mem pour toute les capacité de l'ui bcasl pas encore totalement pris en charge par bcasl.
Pour la priorité l'on ne va plus utiliser la logique de priorité ...l'execution devra etre desormais sequentielle par lancement par section donc la priorité devient inutile.

 ## Cli [x]
 les options de run bcasl ne sont pas encore fonctionnelle il faut les corriger. il faut que bcasl ne fasse pus de paralellism cest interdit.
 


le bcasl.yml ne doit plus contenir :


## ark.yml [x]

ark.yml ne doit plus contenir :

exclusion_patterns:
- .ark/**
- '**/__pycache__/**'
- '**/*.pyc'
- '**/*.pyo'
- '**/*.pyd'
- .git/**
- .svn/**
- .hg/**
- venv/**
- .venv/**
- env/**
- .env/**
- node_modules/**
- build/**
- dist/**
- '*.spec'
- '*.egg-info/**'
- .pytest_cache/**
- .mypy_cache/**
- .tox/**
- site-packages/**
inclusion_patterns:
- '**/*.py'


  car les exclusion sont deja et doivent ere uniuqement gerer par 
  workspace:
   exclude:

  et aussi  les pattern dinclusion ne sont plus necesaire car l'exclusion est suffisante.

  dans Core/Configs il faut eviter la retro compatibilité et revoir.

## VenvManager [x]

dans venvmanager les logique comme celle de la generation de la reuirments etc ne doit normalement pas être dedans mais plutot gerer par le depsanalyser qui dispose de tout la technologie de pointe pour une fiablité .  pour reduire le niveau de complexité inutile n'est rtil pas mieux que venvmanager ne gere que pip comme gestionnaiaire ?? si oui fait un plan.

## refactor: Séparation Core(logique métier) et Ui(interface utilisateur ou de pilotage) [x]

[x] Core/SysDependencyManager.py doit purement contenir de la logique metier et son usage   gui sera dans Ui/Gui/Dialogs/.

[x] Services/AdvancedAuth.py doit purement contenir la logique service et son usage gui sera dans Ui/Gui/Dialogs/.

[x] Mettre la logique metier de Ui/Gui/WorkspaceManipulation.py dans Core/WorkspaceManager/WorkspaceManipulation.py.

[x] pour Core/VenvManager/Manager.py ,garder la logique metier dans Core et déplacer la logique gui dans Ui/Gui/Dialogs/VenvDialog.py .

## linting [x]
Qualité du code améliorée avec ruff et pylint (score pylint: 9.56/10 sur les fichiers modifiés).
- Suppression des imports inutilisés.
- Ajout de docstrings manquantes.
- Validation des conventions de nommage.

## BuildContext []
- l'exclusion pour build doit etre dans la section build du ark.yml et celui de workspace est exsclusif pour le workspace. soit les exxclusion de compialtion doivent etre dans build et la sous section exclude.

## UI []
- l-annulation par ctrl + c doi tetre pour la cli et elle doit etre robuste et toujours fonctionnel...elledit tuer tout les processus prorperemt et imediatemnt sans freeze.
- l-annulation de la gui doit etre robuste et elle doit tuer tout les processus et les processus enfant aussi pour eviter les procesuss zombie.

## bcasl [x]
- retirer le timeout et le parralelism.... et revoir la cli en fonction de cela.