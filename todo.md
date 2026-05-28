# fix et amélioration de l'ergonomie

- [x] ajouter le snapshot du commit git dans le locking.
- [x] retirer les boutons export et import dans la gui.
- [x] ecrire des tests unitaires.
- [x] renforcement et blocage immédiat du build en cas d'absence d'Internet lors de l'installation des outils.

- [] [INFO] Thème appliqué : Mint Light (mint_light.qss)
[INFO] Langue appliquée : Français
[INFO] Language applied: Deutsch
[INFO] Theme applied: Dark (dark.qss)
[INFO] Theme applied: Light (light.qss)
[STATE] Exclusion applied: 402 file(s) excluded according to ark.yml
[INFO] 🔒 Generating build lock file...
[INFO] Starting pre-compilation phase (BCASL)...
[INFO] Pre-compilation (BCASL) if enabled...

BCASL désactivé dans ark.yml. Exécution ignorée
[ERROR] BCASL failed or returned no report. Compilation blocked.
[ERROR] BCASL validation failed. Compilation cannot continue.

ce probleme c'est produit en gui, normalemnt comme il est desactiver la compialtion doit ce lancer sans bcasl mais ici il bloque.