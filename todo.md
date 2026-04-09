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

### Section de corectif avant release 1.0.0


[x] Refactorisation du code.

[x] Pour une indépendance, le ADVANCEDCONFIGEDITOR doit etre independant de git( Créér le sys de diff etc de facon independante de git (from scratch))

[x] le bouton de analyse de deps dans ide gui doit etre application i18n comme les autre boutons... pour s'aasurer de la i18n de ce bouton il faut voir le bouton du meme nom de classic gui et voir comment on li integre le i18n au niveau du tooltips.

[x] Aligner la cli dedicated en fonction de la cli simple en vayant quil soit egaux au niveau des commandes (flags).

[x] Revoir le worflow github pour etre le plus correcte possible (Parametrer la release le ci etc). avant de suprr le ark self buil.yml  il faut fussionner son contenu avec celui de rekesase car la relesase doit ètre generer par release.yml .

[x] Revoir les versions (__version__) de tout les systems internes de ARK y compris les sdks etc.

[x] Revoir le system de statistique de Compilation pour plus d'ergonomie???

[x] on met a jour toutes les docs puis on fige les info de la version 1.O.0

[x] Le Core/Api.py retirer les gui.tr pour des msgbox en utilisant self.parent.tr (regarde comment il sont utilser dans le Core/Venv_Manager/Manager.py).

[x] tout les logs doivent utiliser le logging i18n_log (dans le pire des cas faire log_i18n + safe_log).

[x] le contributing.md doit etre mis a jour pour dire comment l'on doit coder ici et qul system de ark reutiliser dans tel ou tel chose pour ecrire le moins possible tout en respectant le philosohie de modularité et surtout i18n.


### Ideas pour Amelioration UX/UI

[ ] Utiliser le self.parent.tr pour quand lon doit afficher un msgbox quia besoin de i18n? l'tilser pour ameliorer  le systeme i18n destiné au plugin dans Plugins_SDK/GeneralContext/i18n.py pour quand on veut concevoir des msg box etc. il faut une method dédié.