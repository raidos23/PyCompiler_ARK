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

- [] ecrire des tests pour chaque partie critique du logiciel.

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
