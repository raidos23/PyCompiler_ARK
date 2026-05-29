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