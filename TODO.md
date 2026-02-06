# Plan de correction pour ArkConfigManager et BCASL

## Tâches à effectuer

1. **Supprimer les fonctions de comportement de compilation dans Core/ArkConfigManager.py**
   - Supprimer la fonction `get_compiler_options`
   - Supprimer la fonction `get_output_options`

2. **Supprimer la section de configuration de sortie dans Core/ArkConfigManager.py**
   - Retirer la section "CONFIGURATION DE LA SORTIE" du contenu par défaut dans `create_default_ark_config`

3. **Corriger BCASL pour qu'il ne dépende que de bcasl.yml**
   - Dans bcasl/Loader.py, supprimer la fusion avec la configuration ARK dans `_load_workspace_config`
   - Supprimer le chargement des patterns et options de plugins depuis ARK_Main_Config.yml

## Suivi des tâches
- [ ] Tâche 1: Supprimer get_compiler_options et get_output_options
- [ ] Tâche 2: Supprimer la section output dans create_default_ark_config
- [ ] Tâche 3: Corriger _load_workspace_config dans bcasl/Loader.py
