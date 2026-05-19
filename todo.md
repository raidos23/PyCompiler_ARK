
### Logique Bcasl []

faire que la logique bcasl soit parfaitement aligner avec les capacités presumé de la guibcasl dans Ui/Gui/Dialogs/BcaslDialog.py . en exemple : la gui permet de desactiver toute une section de plugin donc le system bcasl doit prendre en charge que quadn une section est desactiver on la lance passe etc. et lon doit faire de mem pour toute les capacité de l'ui bcasl pas encore totalement pris en charge par bcasl.


le bcasl.yml ne doit plus contenir :

file_patterns:
- '**/*.py'
exclude_patterns:
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

## ark.yml []

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
dependencies:
  requirements_files:
  - requirements.txt
  - requirements-prod.txt
  - requirements-dev.txt
  - Pipfile
  - Pipfile.lock
  - pyproject.toml
  - setup.py
  - setup.cfg
  - poetry.lock
  - conda.yml
  - environment.yml
  auto_generate_from_imports: true
environment_manager:
  priority:
  - poetry
  - pipenv
  - conda
  - pdm
  - uv
  - pip
  auto_detect: true
  fallback_to_pip: true

  car les exclusion sont deja et doivent ere uniuqement gerer par workspace:
  exclude:

  et aussi  les pattern dinclusion ne sont plus necesaire car l'exclusion est suffisante.
(cela doit etre regler dans le Core/venvmanager)

## VenvManager []

dans venvmanager les logique comme celle de la generation de la reuirments etc ne doit normalement pas être dedans mais plutot gerer par le depsanalyser qui dispose de tout la technologie de pointe pour une fiablité .