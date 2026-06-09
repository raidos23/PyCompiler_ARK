# CLi ux
- [x] lorsque le dialog rich saffiche poour a cofiramtion il doit atendre une reponse.

- [x] deplacer le engineloader vers Core/engine/loader.py pour centraliser la logcique de laoder et suppr Loaders/ ... et corriger les imports.

- [] refactor le engine_sdk .... suprimer les chose inutlise dans utils en verifant les import pycompiler_ark.engine_sdk et from pycompiler_ark.engine_sdk pour detecter ce qui est vraiment utliser.

- [] interdire et suppr utlisation des helper add_form_checkbox,
    add_output_dir, etc du engine_sdk suprrimer leur existance et mettre ajour tout les engine pour sassusrer des corectif.

- [] dans le docs engine vu ue le automapping est derectemnt apliquer automatiquement le engine_sdk/auto commad builder nest plus necesaire ilfaut le suppr .. et la docs doit etre mis ajour partout et aussi la section qui u=fait une impkemnttaition manuel doit etre retirer desomrais les crzeateur de engine doivent suelemnt crer les ficheir mapping.json e cest tout.

- [] mettre ajour readme.md au niveau de scommade cli en se referent a docs/Cli.md

- [] docs/view/ mettre a jour le mermaid et le corrgier en focntion du fponctionnement reel du code.