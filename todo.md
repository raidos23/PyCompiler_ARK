
### Logique Bcasl [x]

faire que la logique bcasl soit parfaitement aligner avec les capacités presumé de la guibcasl dans Ui/Gui/Dialogs/BcaslDialog.py . en exemple : la gui permet de desactiver toute une section de plugin donc le system bcasl doit prendre en charge que quadn une section est desactiver on la lance passe etc. et lon doit faire de mem pour toute les capacité de l'ui bcasl pas encore totalement pris en charge par bcasl.
Pour la priorité l'on ne va plus utiliser la logique de priorité ...l'execution devra etre desormais sequentielle par lancement par section donc la priorité devient inutile.

 ## Cli 
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

  dans Core/Configs il faut eviter la retro compatibilité et revoir

## VenvManager []

dans venvmanager les logique comme celle de la generation de la reuirments etc ne doit normalement pas être dedans mais plutot gerer par le depsanalyser qui dispose de tout la technologie de pointe pour une fiablité .  pour reduire le niveau de complexité inutile n'est rtil pas mieux que venvmanager ne gere que pip comme gestionnaiaire ?? si oui fait un plan