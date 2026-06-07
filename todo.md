### alignement de finalisation

- aligner les version de la docs sur 1.0.0, ARK doit etre plutot PyCompiler ARK comme nom dans les docs.

- corriger les drift entre docs et arborescence reelle du code.

- corriger les docs de creation et toute les docs car pour cerer des chose via les sdks il faut coregiger (en exemle au lieu de from engine_sdk ca doit etre from pycompiler_ark.engine_sdk ...)..corriger how tocreat engine au niveau de la ou on presnete les ui helper comme add_icon_selector etc .... le buildcontext vient bannir de tel chose car le build ontext a crerr un contrat qui fait quil est inutlue de faire de tel chose desormais ... lon peut prendre en exemple code de pycompiler_ark/engines/nuitka/
dans le how to ceat a bc plugin il faut corriger les exemple de code car les chose ne doivnet importer que leur sdk Plugins_SDk cela va de meme pour la doc des engines.
aligner la docs bcasl avec les capcité non citer du BcPluginContext.

# tests
- corriger les tests dans tests/ .