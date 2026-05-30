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

- [] verifier commde specialement conçu pour les dev comme le engine user dir pour dev dir aussi et les scaffoldings.

- [] fix l'error [ERROR] Erreur démarrage compilation : `MainProcess.compile_from_context()` got an unexpected keyword argument `ark_config`

- [] ecrire des tests pour chaque partie critique du logiciel.

# revue de Ergonomie 

- [] le locking doit save aussi les commande genérer par auto mapping.
- [] lorsque en cli l'on lance le rebuild avec '--lock' si pas de fichier lock specifier il doit y avoir un msg qui dit de linker le lock a utliser pas de defaut. et aussi l'option `--lock` peut utliser `--lock latest`  pour utliser le dernier lock récencé.
- [] les log lors d'un rebuild sans `-v` verbose, doit etre plus ou moins expressif (en similitude au build simple en matiere de log) pour ne pas sembler bugger ou lent aux yeux de l'user.

- [] retirer les emojis en cli pour opter pour des implementation de rich.
- [] en cli sans le mode verbose, utlsier des spinners rich pour chaque etapes pour ne pas paraître bloquant.
- [] quand un worspace nest pas selectionner le advanced editor en gui ne doit point s'ouvrir et afiche un message qui indique de selectionner un workspace. tout comme le fait le dialog bcasl.