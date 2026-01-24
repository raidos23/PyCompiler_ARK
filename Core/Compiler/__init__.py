# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
================================================================================
PACKAGE Core.Compiler - Moteur de Compilation PyCompiler ARK++
================================================================================

Ce package constitue le cœur du système de compilation de PyCompiler ARK++.
Il orchestre l'ensemble du processus de compilation Python en gérant:

    - La construction sécurisée des commandes de compilation
    - L'exécution des processus via QProcess (Qt) ou subprocess
    - La gestion du cycle de vie des processus (démarrage, surveillance, arrêt)
    - L'intégration avec les moteurs de compilation (PyInstaller, Nuitka, etc.)
    - L'annulation propre des compilations et le nettoyage des processus

Architecture du Package:
    __init__.py          → Point d'entrée, exporte les fonctions publiques
    command_helpers.py   → Utilitaires bas niveau pour les commandes
    compiler.py          → Logique principale de compilation (BCASL, filtrage)
    mainprocess.py       → Gestion des processus Qt/subprocess
    process_killer.py    → Fonctions pour tuer les arbres de processus

Dépendances Principales:
    - PySide6 (Qt) : Interface graphique et gestion des processus QProcess
    - psutil : Énumération et termination des processus
    - Core.engines_loader : Chargement dynamique des moteurs de compilation
    - Core.Auto_Command_Builder : Construction automatique des commandes

Fonctions Publiques (Exportées):
    ┌─────────────────────────────────────────────────────────────────────────┐
    │ GESTION DES PROCESSUS                                                    │
    ├─────────────────────────────────────────────────────────────────────────┤
    │ • try_start_processes     → Démarre les compilations en file d'attente  │
    │ • start_compilation_process → Lance une compilation pour un fichier     │
    │ • cancel_all_compilations → Annule toutes les compilations en cours     │
    │ • _kill_process_tree      → Tue un processus et ses descendants         │
    │ • _kill_all_descendants   → Tue tous les descendants du processus GUI   │
    ├─────────────────────────────────────────────────────────────────────────┤
    │ GESTION DES SORTIES                                                      │
    ├─────────────────────────────────────────────────────────────────────────┤
    │ • handle_stdout           → Traite la sortie standard d'un processus    │
    │ • handle_stderr           → Traite la sortie d'erreur d'un processus    │
    │ • handle_finished         → Gère la fin d'un processus de compilation   │
    ├─────────────────────────────────────────────────────────────────────────┤
    │ UTILITAIRES                                                              │
    ├─────────────────────────────────────────────────────────────────────────┤
    │ • try_install_missing_modules → Installe les modules manquants détectés │
    │ • show_error_dialog       → Affiche une boîte de dialogue d'erreur      │
    │ • clamp_text              → Tronque le texte pour l'affichage           │
    │ • redact_secrets          → Masque les secrets dans les logs            │
    │ • compute_for_all         → Construit les commandes de compilation      │
    │ • engines_loader          → Charge et gère les moteurs de compilation   │
    └─────────────────────────────────────────────────────────────────────────┘

Utilisation Typique:
    >>> from Core.Compiler import compile_all, cancel_all_compilations
    >>> compile_all(self)  # Démarre la compilation de tous les fichiers
    >>> cancel_all_compilations(self)  # Annule toutes les compilations

Note:
    Ce package est conçu pour être utilisé exclusivement par l'interface
    graphique MainWindow. Il n'est pas prévu pour une utilisation en ligne
    de commande directe.

================================================================================
"""

# =============================================================================
# SECTION 1 : IMPORTS DES FONCTIONS DE COMPILATION PRINCIPALE
# =============================================================================
# Ces fonctions proviennent du module compiler.py et gèrent le flux de
# compilation complet, y compris l'intégration avec BCASL.

from .compiler import (
    _continue_compile_all,  # Suite de la compilation après BCASL
    compile_all,            # Point d'entrée principal de compilation
)

# =============================================================================
# SECTION 2 : IMPORTS DES FONCTIONS DE GESTION DES PROCESSUS
# =============================================================================
# Ces fonctions proviennent du module mainprocess.py et gèrent le cycle de
# vie des processus de compilation via QProcess ou subprocess.

from .mainprocess import (
    # --- Gestion du Cycle de Vie des Processus ---
    _kill_process_tree,           # Tue un processus et ses enfants (arbre)
    _kill_all_descendants,        # Tue tous les descendants du processus GUI
    try_start_processes,          # Démarre les compilations en file d'attente
    start_compilation_process,    # Lance une compilation pour un fichier
    cancel_all_compilations,      # Annule toutes les compilations en cours

    # --- Traitement des Sorties de Processus ---
    handle_finished,              # Gère la terminaison d'un processus
    handle_stderr,                # Traite la sortie d'erreur (stderr)
    handle_stdout,                # Traite la sortie standard (stdout)

    # --- Installation et Gestion des Erreurs ---
    try_install_missing_modules,  # Installe les modules pip manquants
    show_error_dialog,            # Affiche une boîte de dialogue d'erreur

    # --- Utilitaires ---
    clamp_text,                   # Tronque le texte pour l'affichage
    redact_secrets,               # Masque les secrets dans les logs
    compute_for_all,              # Construit les commandes de compilation
    engines_loader,               # Gestionnaire de moteurs de compilation
)

# =============================================================================
# SECTION 3 : EXPORTS PUBLICS (__all__)
# =============================================================================
# Cette liste définit les symboles publiquement accessibles lors d'un
# import depuis ce package. Elle sert de documentation et de contrôle d'accès.

__all__ = [
    # --- Gestion des Processus ---
    "_kill_process_tree",
    "_continue_compile_all",
    "_kill_all_descendants",
    "try_install_missing_modules",
    "try_start_processes",
    "show_error_dialog",
    "clamp_text",
    "start_compilation_process",
    "cancel_all_compilations",
    
    # --- Traitement des Sorties ---
    "handle_finished",
    "handle_stderr",
    "handle_stdout",
    
    # --- Utilitaires et Chargement ---
    "redact_secrets",
    "compiler",
    "compute_for_all",
    "engines_loader",
    "compile_all",
]

# =============================================================================
# FIN DU PACKAGE Core.Compiler
# =============================================================================
