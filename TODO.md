
## revue du system de statistique de compilation.

- [x] Revoir le system de statistique car  
  elle ne marche pas.
  
- [x] Ameliorer les statistique pour une 
  précision maximale.

## revue de l'engine CxFreeze

- [x] WARNING: deprecated usage: required to use 
  --script NAME
  WARNING: deprecated --include-modules option replaced by --includes

## ui management 

- [x] le butto de vider workspace doit etre aussi griser lors de la compilation.

## Compilation

- [x] Bcasl doit se lancer avan la compilation.

## i18n 

- [x] Des error d'ecirture sont present dans languages/** pour les fichier de i18n json. le probleme vient du fait que certaine chose sont mal orthographier.

## Engines

- [x] les engines sans exception presente tous un probleme de design au niveau du bouton de choix d'icon. En effet le button est un simple button donc on ne sais pas si licon est bien selectionner alors il serait pertinent dajoutetr un label a coter qui montre le chemin de licon selectionner ce qui peut aussi permetrttre un  parametrage a la foix ux/ui et manuel.
 ## Docs

 - [ ] il faut preciser dans la docs for engine a la section de monolitics ui que pas la peine de faire le scroll area cr l'ui s'en charge automatiquement dès qu-il voit que le tab est trop large.

## venvmanager

- [ ] il faut que sur linux si on utilise le python of system que les installation utilise le flag break system package pour s'assurer que l-instalation aura lieu coute que coute. sur windows cela nest pas necessaire  car windwos n-a pas souvent de problme niveau resolution de package.

## ide gui 
- [x] donner toute les capacité gui de classic gui à ide gui.
- [x] pour les installations d'outils des engines ou meme des plugins en generale les action d'installation systeme et de python rentre en conflit le plus souvent alors lors de linstallation on dit dabord prioriser linstaltion systme avant meme de lancer les commande pour l'installation de type python. pour les boite de dialog qui saffiche sepcialemnt pour cela il faut un time out de taping de secret (mot de passe)  de l'user genre 120s si le delai est passer on annule linstallation system proprement et selon notrer regle si un processus du genre là est tuer tout les autre non plus le droit de sexecuter il sont comme des process enfant une fois que le processus premier est tuer on anneanti le reste pour securiser le system et surtout les projet des utilisateurs. au dela de cela il faut que l'on ameliore le venvnager car il doit suporter tous les types de venv a savvir .env env venv .venv etc et tout les non bizarre posible dans l'industrie. 

## P0

- [x] finaliser la parite IDE/classic et documenter la matrice de parite.
- [x] durcir l'analyseur deps avec un parseur d'imports testable et une meilleure couverture des imports relatifs et dynamiques.
