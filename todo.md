# refactor
- [] cnetraliser toute les `def _declare_i18n` dans Ui/i18n.py cat il sont tous identique.recherche dabord parotut avant de faire la centralisation.
- [] appliquer le i18n à help_text dans uifeatures.
- [] les engine ne doivent avoir access que a leur sdk de meme que les plugins.
- [] pour tous les i18n analyser pour voir si il nest pas possible de inteegre le declare i18n dna stranslate pour que on est plus beoin de declarer et on fera juste `translate(self.id, key, default)`.