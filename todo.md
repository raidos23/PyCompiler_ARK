# fix et amélioration de l'ergonomie

- [x] ajouter le snapshot du commit git dans le locking.
- [x] retirer les boutons export et import dans la gui.
- [x] ecrire des tests unitaires.
- [x] renforcement et blocage immédiat du build en cas d'absence d'Internet lors de l'installation des outils.

- [x] GUI : ne plus bloquer la compilation quand BCASL est désactivé dans ark.yml (rapport `disabled` au lieu de `None`).
- [x] Refactor de l'éditeur de config avancé en formulaire structuré pour ark.yml.
- [x] lors de la compialtion le widget de view des fichier dans les gui doivent etre griser alterer comme les autre .tout les elment ui alterer doivent refleter leur alteration par une couleur alterer comme on la deja fait pour le bouton build.
- [x] la section platform.python de locking doit contenir la version du python utliser pour la compilation.
- [x] le dialog statistic doit etre i18naliser  fr/en comme les autre dialogs.

- [x] dans le locking on doit aussi prendre en compte en plus du commit git , la branch git. et  apliquer les ajout ui(gui et cli) comme il a deja été fait lors de l'implementation du support de commit.

- [x] verifier que les commandes cli sont parfaitement fonctionnelle et verifer les fcntionnalités une a une au niveau cli. 

- [x] verifier commde specialement conçu pour les dev comme le engine user dir pour dev dir aussi et les scaffoldings.

- [x] fix l'error [ERROR] Erreur démarrage compilation : `MainProcess.compile_from_context()` got an unexpected keyword argument `ark_config`

- [x] ecrire des tests pour chaque partie critique du logiciel.

# revue de Ergonomie 

- [x] le locking doit save aussi les commande genérer par auto mapping.
- [x] lorsque en cli l'on lance le rebuild avec '--lock' si pas de fichier lock specifier il doit y avoir un msg qui dit de linker le lock a utliser pas de defaut. et aussi l'option `--lock` peut utliser `--lock latest` pour utliser le dernier lock récencé.
- [x] les log lors d'un rebuild sans `-v` verbose, doit etre plus ou moins expressif (en similitude au build simple en matiere de log) pour ne pas sembler bugger ou lent aux yeux de l'user.

- [x] retirer les emojis en cli pour opter pour des implementation de rich.
- [x] en cli sans le mode verbose, utlsier des spinners rich pour chaque etapes pour ne pas paraître bloquant.
- [x] quand un worspace nest pas selectionner le advanced editor en gui ne doit point s'ouvrir et afiche un message qui indique de selectionner un workspace. tout comme le fait le dialog bcasl.

- [x] fix de lerruer de bool  :

    [INFO] Auto-detection of sensitive modules (cx_freeze) enabled.
    [INFO] Detection source: imports
    [INFO] Detected modules: football_app 
    [INFO] No additional cx_freeze options required from mapping.
    [INFO] Starting compilation: main.py with cx_freeze
    [ERROR] Compilation start error: 'bool' object is not callable




L'erreur 'bool' object is not callable signifie qu'une variable contenant un booléen (True ou False) est utilisée comme si c'était une fonction (ex: variable()).

  Dans le cas précis ici , l'erreur survient juste après le log "Starting compilation", ce qui réduit les suspects à ce qui se passe dans la foulée du signal
  compilation_started.

  Voici les 3 causes probables à analyser :

   1. Shadowing de callable() : Si une variable nommée callable (ex: callable = True) existe dans le scope, l'appel à la fonction native callable(quelque_chose) plantera avec cette erreur exacte. J'ai vu des annotations de type callable dans le code qui pourraient être mal interprétées par Python s'il y a un conflit.
   2. Confusion success / success() : Le projet utilise massivement success comme variable booléenne et success("...") comme fonction de log (CLI). Si une fonction de log est importée ou définie sous le nom success mais qu'une variable locale success = True existe, tout appel à success() échouera.
   3. Signal/Slot Corrompu : Dans CompilerDialog.py, plusieurs signaux sont connectés à des lambdas (ex: compilation_finished). Si l'une des fonctions cibles (comme handle_finished) a été écrasée par un booléen (ex: self.handle_finished = True au lieu de pointer vers la fonction), l'émission du signal déclenchera l'erreur.

  Le point critique : L'erreur est catchée dans CompilerDialog.py autour de l'appel main_process. compile_from_context(...) dans compile_all. Cela signifie que l'erreur se produit soit :
   * Directement lors de l'appel à cette méthode (si compile_from_context est devenu un booléen sur l'objet main_process).
   * À l'intérieur de cette méthode, lors de l'appel d'un helper ou de l'émission d'un signal dont un slot est corrompu.


- [x] recire lintegralité de l'orchestration de build de la gui en focntion de la cli.

- [x] le locking est conçu pour un build reproductible mais dans l'incapacité de recréer un build bit par bit.. la comparaion lors dun rebuild doit etre revue pour une comparaison basé sur un build non bit for bit mais focntionnrlemnt equivalente donc l'on ne comparera plus le lock par hash ou en entireté mais plutot des metadonnées importante pour être fonctionnelement identique... .


- [x] corriger l'erreur : [ERROR] Error while validating BCASL report. Compilation blocked.
                        [ERROR] BCASL validation failed. Compilation cannot continue.


[INFO] Theme applied: Dark (dark.qss)
[INFO] Language applied: English
[STATE] Exclusion applied: 875 file(s) excluded according to ark.yml
[INFO] Starting pre-compilation phase (BCASL)...
[INFO] Pre-compilation (BCASL) if enabled...

BCASL désactivé dans ark.yml. Exécution ignorée
[SUCCESS] BCASL phase completed successfully.
[INFO] Starting compilation with CX_Freeze...
[INFO] 🔒 Generating compilation lock file...
[INFO] Engine-specific mapping (cx_freeze): /home/sam/PyCompiler_ARK/engines/cx_freeze/mapping.json
[INFO] Generic builder used for engine 'cx_freeze'.
[INFO] Auto-detection of sensitive modules (cx_freeze) enabled.
[INFO] Detection source: imports
[INFO] Detected modules: football_app
[INFO] No additional cx_freeze options required from mapping.
[INFO] Starting compilation: main.py with cx_freeze
[STATE] État: Compilation en cours...
[INFO] Starting compilation with cx_freeze
[INFO] Etape 1/3 : Verification et installation des outils requis...
[INFO] ⚙️ Environnement : System
[INFO] Etape 2/3 : Generation de la commande de compilation...
[INFO] Etape 3/3 : Execution du processus de compilation...
[INFO] Commande : /usr/bin/python -m cx_Freeze --target-dir dist/ --target-name just_an_app main.py
[INFO] ----------------------------------------
[INFO] running build_exe
[INFO] running egg_info
[INFO] writing UNKNOWN.egg-info/PKG-INFO
[INFO] writing dependency_links to UNKNOWN.egg-info/dependency_links.txt
[INFO] writing top-level names to UNKNOWN.egg-info/top_level.txt
[INFO] reading manifest file 'UNKNOWN.egg-info/SOURCES.txt'
[INFO] writing manifest file 'UNKNOWN.egg-info/SOURCES.txt'
[STATE] État: Annulation...
[STATE] État: Prêt
[INFO] Compilation cancellation requested
[INFO] Cancellation requested.
[INFO] -> [SUCCESS] Compilation CX_Freeze terminée avec succès.
[STATE] État: Prêt
[INFO] Compilation cancelled
[INFO] Compilation cancelled.
[STATE] État: Erreur

✅ BCASL pipeline saved to bcasl.yml[STATE] État: Prêt
[INFO] Process reset
[INFO] Starting pre-compilation phase (BCASL)...
[INFO] Pre-compilation (BCASL) if enabled...

BCASL: 2 package(s) chargé(s) depuis 1 dossiers

⏫ Priorité 0 pour cleaner

⏫ Priorité 1 pour outputcleaner

Phase: Cleanup
Plugin: Cleaner
Plugin: Output Cleaner
BCASL - Rapport:

 - cleaner: OK (2004.3 ms)

 - outputcleaner: OK (4.7 ms)

Plugins: 2/2 ok, temps total 2009.0 ms
[ERROR] Error while validating BCASL report. Compilation blocked.
[ERROR] BCASL validation failed. Compilation cannot continue.


- [x] en gui la compialtion tarde a ce lancer sur des projet exetrement massif...
- [x] lorsque bcasl n'est pas activer la compilation prend plus d temps a ce lancer en gui.

- [x] en fonction des derniere modification des docs sur lutlisation de `build.exclude` dans la cfg managed par le logiciel , ... modification de advancededitor car au message de fond de la section dediée a `build.exclude` il ya des exlusiond de dossier et Pycache comme exemple ... modifer vers des un message de fond parlt de exclusion de package python.

- [x] lors de la creation de .ark/ dans un dworkspace un gitingore doit etre ajouter permetant dexclure le ficheor pref.json le dossier cache le dossier logs et build  uniquement.

- [x] Implémentation de `build.include` dans ark.yml et l'UI pour permettre de forcer l'inclusion de packages Python (traduction automatique pour Nuitka, PyInstaller et cx_Freeze).

- [] reverifier la parité Gui et Cli pour une assurance finale de la parité. faire une synhese des details (verifer la parité des fonctionnalité presente en cli et non en gui tel que la recente vue que l'utlisation de la cfg des engines en compilation est pas utliser en gui etc bref localiser les petites zone de parité oublier mais qui sont cruciales)