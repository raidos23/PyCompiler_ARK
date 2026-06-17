# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Samuel Amen Ague

"""Qt GUI layer — uniquement du code PySide6. Appelle Core/ pour la logique métier.

Ne pas importer PyCompilerArkGui ici pour éviter les imports circulaires.
Utiliser `from pycompiler_ark.Ui.Gui.Gui import PyCompilerArkGui` directement.
"""
