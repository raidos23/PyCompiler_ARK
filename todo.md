[x] Ajouter un bouton dans (...) dans le ide gui pour enregister la config ui de tout les engines d'u seul clic.
    - Fait: action `Save engine configs` ajoutée dans le menu `(...)` (IDE GUI).
    - Fait: sauvegarde batch des configs engines du workspace (`.ark/<engine_id>/config.json`).

[x] Ameliorer le CI/CD pour quel reprennet exactement le processus gui en headless, ne plus recrire du nouvea code il faut suppr l'inutile et reutiliser le code des packages du Core comme le fait l'application principale. en exemple il faut que la compilation utilise le venv linker dans .ark/pref.json ...etc il faut que l processus Cli = process gui (en headless).
    - Fait: le headless applique la pref venv workspace (`.ark/pref.json`) via `VenvManager`.
    - Fait: le headless charge les configs engines persistées (`.ark/<engine_id>/config.json`).
    - Fait: les engines consomment les options persistées même sans widgets UI (mode headless).

[] de la meme manière que la gui puisse appliquer des langues rapidement avec fluidité... il faut que les msg box concu par les plugins ou autres puissent aussi recevoir leur i18n meme si celui des plugins est deja en vigueur le i18n ne sapplique pas au msg box cela est fort bizarre.

[] L'application de languege dans les boutons de (...) dansle ide gui doit etre revue car les language dans le (...) ne sapplique qu'apres redemarrage de l'application.

[] les fichier json de ./languages du projet en global ne doit pas avoir a faire a la traduction lié a des engines car ceux ci gere dejà la leur via ENGINES/engine_id/languages/**.json alors il faut revoir et corriger.

[] Améliorer le ADVANCEDCONFIGEDITOR...au niveau du system de diff ( il faut quil soit le plus proche possible e la technologie de git au niveau de perfectionnement ).
