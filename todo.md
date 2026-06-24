# Refactor Status

- [x] Centraliser tout les `def log_i18n` dans `pycompiler_ark/Ui/i18n.py` comme seule méthode pour le logging i18n de l'app.
- [x] Retirer l'utilisation des `safe_logs` et `_safe_log` dans toute l'appli pour privilégier l'usage de `log_i18n`.
- [x] Éviter le hardcoding dans i18n en nettoyant les noms des boutons et en exploitant la convention de traduction automatique par `tt_*`, `btn_*`, `tab_*` du système i18n et les propriétés dynamiques Qt.