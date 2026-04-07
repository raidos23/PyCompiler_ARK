[x] Ajouter un bouton dans (...) dans le ide gui pour enregister la config ui de tout les engines d'u seul clic.
    - Fait: action `Save engine configs` ajoutée dans le menu `(...)` (IDE GUI).
    - Fait: sauvegarde batch des configs engines du workspace (`.ark/<engine_id>/config.json`).

[x] Ameliorer le CI/CD pour quel reprennet exactement le processus gui en headless, ne plus recrire du nouvea code il faut suppr l'inutile et reutiliser le code des packages du Core comme le fait l'application principale. en exemple il faut que la compilation utilise le venv linker dans .ark/pref.json ...etc il faut que l processus Cli = process gui (en headless).
    - Fait: le headless applique la pref venv workspace (`.ark/pref.json`) via `VenvManager`.
    - Fait: le headless charge les configs engines persistées (`.ark/<engine_id>/config.json`).
    - Fait: les engines consomment les options persistées même sans widgets UI (mode headless).

[x] de la meme manière que la gui puisse appliquer des langues rapidement avec fluidité... il faut que les msg box concu par les plugins ou autres puissent aussi recevoir leur i18n meme si celui des plugins est deja en vigueur le i18n ne sapplique pas au msg box cela est fort bizarre.
    - Fait: `Plugins_SDK/GeneralContext/Dialog.py` traduit automatiquement `title/text` des msgbox via i18n plugin/global.
    - Fait: détection automatique du plugin appelant (stack `Plugins/<plugin_id>/...`) pour appliquer la bonne table de traduction.

[x] L'application de languege dans les boutons de (...) dansle ide gui doit etre revue car les language dans le (...) ne sapplique qu'apres redemarrage de l'application.
    - Fait: re-traduction forcée du menu `(...)` immédiatement après `apply_language` (sans redémarrage).

[x] les fichier json de ./languages du projet en global ne doit pas avoir a faire a la traduction lié a des engines car ceux ci gere dejà la leur via ENGINES/engine_id/languages/**.json alors il faut revoir et corriger.
    - Fait: suppression des clés de traduction liées aux engines dans `languages/*.json`.
    - Principe appliqué: l'i18n des engines vit dans `ENGINES/<engine_id>/languages/*.json`.

[x] Améliorer le ADVANCEDCONFIGEDITOR...au niveau du system de diff ( il faut quil soit le plus proche possible e la technologie de git au niveau de perfectionnement ).
    - Fait: le diff utilise `git diff --no-index --minimal --patience` quand git est disponible.
    - Fallback: `difflib.unified_diff` si git n'est pas disponible.
