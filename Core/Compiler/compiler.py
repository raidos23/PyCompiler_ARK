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
MODULE compiler.py - Logique Principale de Compilation PyCompiler ARK++
================================================================================

Ce module constitue le cœur du système de compilation de PyCompiler ARK++.
Il orchestre l'ensemble du processus de compilation en gérant:

    - Le cycle de vie complet de la compilation (démarrage, filtrage, exécution)
    - L'intégration avec BCASL (Before-Compile ASync Loader) pour les plugins
    - Le filtrage intelligent des fichiers (exclusions, points d'entrée)
    - La gestion des erreurs et le nettoyage des processus

FONCTIONS PRINCIPALES:
    ┌────────────────────────────────────────────────────────────────────────┐
    │ GESTION DU CYCLE DE VIE                                                │
    ├────────────────────────────────────────────────────────────────────────┤
    │ • compile_all()           → Point d'entrée principal, lance la         │
    │                             compilation après exécution des plugins    │
    │                             BCASL                                      │
    │ • _continue_compile_all() → Suite de la compilation après BCASL,      │
    │                             filtrage et préparation de la file         │
    │ • _kill_all_processes()   → Nettoyage d'urgence en cas d'erreur,       │
    │                             tue tous les processus et réinitialise     │
    │                             l'état de l'interface                      │
    └────────────────────────────────────────────────────────────────────────┘

FLUX DE COMPILATION:
    ┌───────────────────────────────────────────────────────────────────────┐
    │ 1. compile_all(self)                                                  │
    │    ├─ Vérifications préliminaires (processus actifs, fichiers)        │
    │    ├─ Désactivation des contrôles UI                                  │
    │    └─ Exécution asynchrone de BCASL (_run_bcasl_async)               │
    │                                                                      │
    │ 2. Callback _after_bcasl(report)                                      │
    │    ├─ Vérification du rapport BCASL (erreurs, statut)                │
    │    ├─ Si OK: appel de _continue_compile_all()                        │
    │    └─ Si erreur: nettoyage et réactivation UI                         │
    │                                                                      │
    │ 3. _continue_compile_all(self)                                        │
    │    ├─ Chargement configuration ARK                                    │
    │    ├─ Filtrage des fichiers (exclusions, points d'entrée)             │
    │    ├─ Construction de la file d'attente                               │
    │    ├─ Configuration UI (barre de progression, logs)                   │
    │    └─ Appel de try_start_processes() pour lancer les compilations    │
    └───────────────────────────────────────────────────────────────────────┘

INTEGRATION BCASL:
    BCASL (Before-Compile ASync Loader) est un système de plugins qui s'exécute
    avant la compilation réelle. Il permet de:
    - Modifier les fichiers sources avant compilation
    - Valider des préconditions de compilation
    - Injecter du code ou des ressources
    - Exécuter des tâches de préparation asynchrones

    La compilation ne démarre que lorsque BCASL a terminé avec succès
    (ou est désactivé). Cela garantit l'intégrité du code compilé.

FILTRAGE DES FICHIERS:
    Le système de filtrage exclut automatiquement:
    - Fichiers dans site-packages (dépendances tierces)
    - Fichiers correspondant aux patterns d'exclusion ARK
    - Fichiers sans point d'entrée (__main__) si activé
    - Fichiers inexistants ou illisibles

DÉPENDANCES:
    - PySide6.QtWidgets : Boîtes de dialogue (QMessageBox)
    - Core.ark_config_loader : Chargement de la configuration ARK
    - bcasl.Loader : Exécution des plugins de pré-compilation

================================================================================
"""

# =============================================================================
# SECTION 1 : IMPORTS
# =============================================================================
# Imports des modules nécessaires au fonctionnement du compilateur.

from PySide6.QtWidgets import QMessageBox
import os
import traceback

# Imports des modules de configuration et de chargement ARK
from Core.ark_config_loader import (
    load_ark_config,
    should_exclude_file,
    get_compiler_options,
    get_output_options,
    get_dependency_options,
)


# =============================================================================
# SECTION 2 : GESTION D'URGENCE ET NETTOYAGE
# =============================================================================
# Cette section contient les fonctions de nettoyage d'urgence utilisées
# en cas d'erreur critique pour réinitialiser l'état de l'application.
# =============================================================================


def _kill_all_processes(self) -> None:
    """
    Tue tous les processus de compilation en cours et réinitialise l'état.
    
    Cette fonction est le mécanisme de récupération d'urgence principal.
    Elle doit être appelée en cas d'erreur critique pour:
    1. Arrêter proprement tous les processus de compilation actifs
    2. Vider la file d'attente des compilations
    3. Réinitialiser les compteurs et drapeaux internes
    4. Réactiver les contrôles de l'interface utilisateur
    
    L'ordre des opérations est important pour éviter les conditions de
    course et assurer un nettoyage complet et cohérent.
    
    Args:
        self: Instance de la fenêtre principale (MainWindow)
    
    Returns:
        None
    
    Processus Nettoyés:
        1. Processus actifs (terminate → wait → kill si nécessaire)
        2. File d'attente (queue.clear())
        3. Compteurs de compilation (current_compiling.clear())
        4. Contrôles UI (set_controls_enabled(True))
        5. Onglets du compilateur (setEnabled(True))
        6. Barre de progression (reset à 0/1)
        7. Drapeau de continuation (_compile_continued = False)
    
    Notes:
        - Cette fonction est "best-effort" : elle ignore les erreurs
          individuelles pour garantir que le nettoyage global se fait.
        - À utiliser uniquement pour la récupération d'erreurs, pas
          pour l'arrêt normal (utiliser cancel_all_compilations à la place).
    """
    # -----------------------------------------------------------------------------
    # ÉTAPE 1 : Arrêt des processus actifs
    # -----------------------------------------------------------------------------
    try:
        if hasattr(self, "processes") and self.processes:
            for pid, proc in list(self.processes.items()):
                try:
                    if proc is not None and proc.state() == proc.Running:
                        # Tentative d'arrêt propre (SIGTERM)
                        proc.terminate()
                        proc.waitForFinished(2000)  # Attendre max 2s
                        # Si toujours vivant, forcer le kill
                        if proc.state() == proc.Running:
                            proc.kill()
                            proc.waitForFinished(1000)
                except Exception:
                    pass  # Ignorer les erreurs individuelles
            # Vider le dictionnaire des processus
            self.processes.clear()
    except Exception:
        pass

    # -----------------------------------------------------------------------------
    # ÉTAPE 2 : Vidage de la file d'attente
    # -----------------------------------------------------------------------------
    try:
        if hasattr(self, "queue"):
            self.queue.clear()
    except Exception:
        pass

    # -----------------------------------------------------------------------------
    # ÉTAPE 3 : Réinitialisation des compteurs
    # -----------------------------------------------------------------------------
    try:
        if hasattr(self, "current_compiling"):
            self.current_compiling.clear()
    except Exception:
        pass

    # -----------------------------------------------------------------------------
    # ÉTAPE 4 : Réactivation des contrôles UI
    # -----------------------------------------------------------------------------
    try:
        self.set_controls_enabled(True)
    except Exception:
        pass

    try:
        if hasattr(self, "compiler_tabs") and self.compiler_tabs:
            self.compiler_tabs.setEnabled(True)
    except Exception:
        pass

    try:
        if hasattr(self, "progress"):
            self.progress.setRange(0, 1)
            self.progress.setValue(0)
    except Exception:
        pass

    try:
        if hasattr(self, "_compile_continued"):
            self._compile_continued = False
    except Exception:
        pass


# =============================================================================
# SECTION 3 : COMPILATION POST-BCASL
# =============================================================================
# Cette section contient la logique de compilation qui s'exécute après
# que BCASL a terminé avec succès. Elle gère le filtrage des fichiers
# et la préparation de la file d'attente de compilation.
# =============================================================================


def _continue_compile_all(self) -> None:
    """
    Suite de la compilation après exécution de BCASL.
    
    Cette fonction est appelée uniquement après que BCASL a terminé
    avec succès. Elle est responsable de:
    
    1. **Chargement de la configuration ARK** : Lit les paramètres de
       compilation depuis ARK_Main_Config.yml
    
    2. **Filtrage des fichiers** : Applique les règles d'exclusion et
       de sélection pour déterminer quels fichiers compiler
    
    3. **Construction de la file d'attente** : Crée la liste des fichiers
       à compiler avec leur statut (à compiler ou ignoré)
    
    4. **Configuration de l'interface** : Met à jour la barre de progression,
       les logs et l'état des contrôles
    
    5. **Lancement des compilations** : Appelle try_start_processes() pour
       démarrer les compilations parallèles
    
    Args:
        self: Instance de la fenêtre principale (MainWindow)
    
    Returns:
        None
    
    Configuration ARK Utilisée:
        - exclusion_patterns : Patterns de fichiers à exclure
        - inclusion_patterns : Patterns de fichiers à inclure (défaut: **/*.py)
        - auto_detect_entry_points : Détection automatique de __main__
        - compile_only_main : Compiler uniquement main.py/app.py
        - main_file_names : Noms de fichiers principaux à chercher
    
    Filtres Appliqués:
        1. Existence du fichier (must exist)
        2. Patterns d'exclusion ARK (site-packages, patterns personnalisés)
        3. Point d'entrée (__main__) si auto_detect_entry_points est activé
        4. Sélection UI (fichiers sélectionnés vs tous les fichiers)
    
    Notes:
        - Cette fonction est 非bloquante : elle lance les compilations
          et retourne immédiatement.
        - Les compilations réelles sont gérées par try_start_processes()
        - La barre de progression est mise en mode indéterminé (0, 0)
          pendant les compilations.
    """
    # -----------------------------------------------------------------------------
    # ÉTAPE 1 : Chargement de la configuration ARK
    # -----------------------------------------------------------------------------
    ark_config = load_ark_config(self.workspace_dir)
    exclusion_patterns = ark_config.get("exclusion_patterns", [])
    inclusion_patterns = ark_config.get("inclusion_patterns", ["**/*.py"])
    auto_detect_entry_points = ark_config.get("auto_detect_entry_points", True)
    compile_only_main_ark = ark_config.get("compile_only_main", False)
    main_file_names_ark = ark_config.get("main_file_names", ["main.py", "app.py"])

    # Compteurs pour les exclusions (pour le logging)
    exclusion_counts = {
        "site_packages": 0,
        "ark_patterns": 0,
        "no_entry_point": 0,
        "read_error": 0,
        "not_exists": 0,
    }

    # -----------------------------------------------------------------------------
    # ÉTAPE 2 : Définition du filtre de fichiers exécutables
    # -----------------------------------------------------------------------------
    def is_executable_script(path: str) -> bool:
        """
        Vérifie si un fichier Python est un script exécutable.
        
        Un fichier est considéré comme exécutable s'il:
        1. Existe physiquement sur le disque
        2. N'est pas dans site-packages
        3. Ne correspond pas aux patterns d'exclusion ARK
        4. Contient un point d'entrée __main__ (si activé)
        
        Args:
            path: Chemin absolu vers le fichier Python
            
        Returns:
            True si le fichier doit être compilé, False sinon
        """
        # Vérification de l'existence du fichier
        if not os.path.exists(path):
            exclusion_counts["not_exists"] += 1
            return False

        # Vérification des patterns d'exclusion ARK
        if should_exclude_file(path, self.workspace_dir, exclusion_patterns):
            exclusion_counts["ark_patterns"] += 1
            return False

        # Exclusion de site-packages
        if "site-packages" in path:
            exclusion_counts["site_packages"] += 1
            return False

        # Si détection automatique désactivée, accepter tous les fichiers
        if not auto_detect_entry_points:
            return True

        # Vérification du point d'entrée __main__
        try:
            with open(path, encoding="utf-8") as f:
                content = f.read()
                if (
                    "if __name__ == '__main__'" in content
                    or 'if __name__ == "__main__"' in content
                ):
                    return True
                else:
                    exclusion_counts["no_entry_point"] += 1
                    return False
        except Exception:
            exclusion_counts["read_error"] += 1
            return False

    # -----------------------------------------------------------------------------
    # ÉTAPE 3 : Détection du compilateur actif
    # -----------------------------------------------------------------------------
    use_nuitka = False
    if hasattr(self, "compiler_tabs") and self.compiler_tabs:
        # Désactiver les onglets pendant la compilation
        self.compiler_tabs.setEnabled(False)
        # Nuitka est à l'index 1 (PyInstaller à l'index 0)
        if self.compiler_tabs.currentIndex() == 1:
            use_nuitka = True

    # L'option UI a priorité sur la configuration ARK
    compile_only_main = (
        self.opt_main_only.isChecked()
        if hasattr(self, "opt_main_only") and self.opt_main_only is not None
        else compile_only_main_ark
    )

    # -----------------------------------------------------------------------------
    # ÉTAPE 4 : Sélection des fichiers à compiler
    # -----------------------------------------------------------------------------
    if use_nuitka:
        # Nuitka compile tous les fichiers (pas de restriction main.py)
        if self.selected_files:
            files_ok = [f for f in self.selected_files if is_executable_script(f)]
        else:
            files_ok = [f for f in self.python_files if is_executable_script(f)]
        self.queue = [(f, True) for f in files_ok]
    else:
        # PyInstaller avec logique de filtrage
        if self.selected_files:
            # Fichiers sélectionnés explicitement
            files_ok = [f for f in self.selected_files if is_executable_script(f)]
            self.queue = [(f, True) for f in files_ok]
        elif compile_only_main:
            # Recherche des fichiers principaux (main.py, app.py)
            files = [
                f
                for f in self.python_files
                if os.path.basename(f) in main_file_names_ark
            ]
            files_ok = [f for f in files if is_executable_script(f)]
            self.queue = [(f, True) for f in files_ok]
            
            # Message d'erreur si aucun fichier principal trouvé
            if not files_ok:
                main_names_str = ", ".join(main_file_names_ark)
                self.log.append(
                    f"❌ Aucun fichier exécutable trouvé parmi : {main_names_str}\n"
                    f"   Raison : Les fichiers spécifiés n'ont pas de point d'entrée "
                    f"(if __name__ == '__main__') ou n'existent pas.\n"
                )
                self.set_controls_enabled(True)
                if hasattr(self, "compiler_tabs") and self.compiler_tabs:
                    self.compiler_tabs.setEnabled(True)
                return
        else:
            # Tous les fichiers avec point d'entrée
            files_ok = [f for f in self.python_files if is_executable_script(f)]
            self.queue = [(f, True) for f in files_ok]

    # -----------------------------------------------------------------------------
    # ÉTAPE 5 : Vérification de la file d'attente
    # -----------------------------------------------------------------------------
    if not files_ok:
        try:
            self.log.append(
                f"❌ Aucun fichier exécutable à compiler.\n"
                f"   Raisons possibles :\n"
                f"   • Aucun fichier Python sélectionné ou dans le workspace\n"
                f"   • Les fichiers n'ont pas de point d'entrée (if __name__ == '__main__')\n"
                f"   • Les fichiers sont dans site-packages ou correspondent à des patterns d'exclusion\n"
                f"   • Les fichiers n'existent pas ou ne sont pas accessibles\n"
            )
        except Exception:
            pass
        try:
            self.set_controls_enabled(True)
        except Exception:
            pass
        try:
            if hasattr(self, "compiler_tabs") and self.compiler_tabs:
                self.compiler_tabs.setEnabled(True)
        except Exception:
            pass
        return

    # -----------------------------------------------------------------------------
    # ÉTAPE 6 : Initialisation des structures de données
    # -----------------------------------------------------------------------------
    try:
        self.current_compiling.clear()
    except Exception:
        pass
    try:
        self.processes.clear()
    except Exception:
        pass
    try:
        self.progress.setRange(0, 0)  # Mode indéterminé
    except Exception:
        pass

    # -----------------------------------------------------------------------------
    # ÉTAPE 7 : Logging de la configuration
    # -----------------------------------------------------------------------------
    if ark_config:
        try:
            self.log.append("📋 Configuration ARK chargée depuis ARK_Main_Config.yml\n")
        except Exception:
            pass
        try:
            self.log.append(
                f"   • Patterns d'inclusion : {', '.join(inclusion_patterns)}\n"
            )
        except Exception:
            pass
        try:
            self.log.append(
                f"   • Patterns d'exclusion : {len(exclusion_patterns)} pattern(s)\n"
            )
        except Exception:
            pass
        try:
            self.log.append(
                f"   • Détection point d'entrée : "
                f"{'Activée' if auto_detect_entry_points else 'Désactivée'}\n"
            )
        except Exception:
            pass
        try:
            self.log.append(
                f"   • Compiler uniquement main : "
                f"{'Oui' if compile_only_main else 'Non'}\n"
            )
        except Exception:
            pass

    try:
        self.log.append(
            f"🔨 Compilation parallèle démarrée ({len(files_ok)} fichier(s))...\n"
        )
    except Exception:
        pass

    # -----------------------------------------------------------------------------
    # ÉTAPE 8 : Lancement des compilations
    # -----------------------------------------------------------------------------
    try:
        self.set_controls_enabled(False)
    except Exception:
        pass
    try:
        self.try_start_processes()
    except Exception:
        pass


# =============================================================================
# SECTION 4 : POINT D'ENTRÉE PRINCIPAL
# =============================================================================
# Cette section contient la fonction compile_all(), le point d'entrée
# principal de la compilation qui coordonne l'ensemble du processus.
# =============================================================================


def compile_all(self) -> None:
    """
    Point d'entrée principal pour démarrer la compilation.
    
    Cette fonction orchestre l'ensemble du processus de compilation:
    
    1. **Vérifications préliminaires** : S'assure que les conditions
       nécessaires sont réunies (pas de compilation en cours, fichiers
       disponibles)
    
    2. **Désactivation de l'interface** : Bloque les contrôles utilisateur
       pour éviter les modifications pendant la compilation
    
    3. **Exécution BCASL** : Lance les plugins de pré-compilation de manière
       asynchrone (sans bloquer l'UI)
    
    4. **Callback de continuation** : Une fois BCASL terminé, appelle
       _continue_compile_all() pour lancer la compilation réelle
    
    Args:
        self: Instance de la fenêtre principale (MainWindow)
    
    Returns:
        None
    
    Flux d'Exécution:
        ┌─────────────────────────────────────────────────────────────────┐
        │ VERIFICATIONS PRÉLIMINAIRES                                     │
        │ ├─ Une compilation est-elle déjà en cours? → Warning + return  │
        │ ├─ Un workspace est-il défini? → Error log + return            │
        │ └─ Des fichiers sont-ils disponibles? → Error log + return     │
        └─────────────────────────────────────────────────────────────────┘
                               ↓
        ┌─────────────────────────────────────────────────────────────────┐
        │ PRÉPARATION                                                     │
        │ ├─ Réinitialiser les statistiques de compilation               │
        │ ├─ Désactiver les contrôles UI (sauf Annuler)                  │
        │ └─ Désactiver les onglets du compilateur                       │
        └─────────────────────────────────────────────────────────────────┘
                               ↓
        ┌─────────────────────────────────────────────────────────────────┐
        │ EXÉCUTION BCASL                                                 │
        │ ├─ Importer run_pre_compile_async                              │
        │ ├─ Définir le callback _after_bcasl                            │
        │ ├─ Lancer BCASL de manière asynchrone                          │
        │ └─ Retourner immédiatement (ne pas bloquer l'UI)               │
        └─────────────────────────────────────────────────────────────────┘
                               ↓
        [BCASL termine et appelle _after_bcasl]
                               ↓
        ┌─────────────────────────────────────────────────────────────────┐
        │ _after_bcasl(report)                                            │
        │ ├─ Vérifier les erreurs BCASL                                  │
        │ ├─ Si erreur: nettoyer et réactiver UI                         │
        │ └─ Si OK: appeler _continue_compile_all()                      │
        └─────────────────────────────────────────────────────────────────┘
                               ↓
        [_continue_compile_all s'exécute et lance les compilations]
    
    Gestion des Erreurs BCASL:
        - BCASL désactivé (status="disabled") : Continuer normalement
        - BCASL avec erreurs : Log des erreurs + nettoyage + réactivation UI
        - BCASL avec rapport inattendu : Traitement comme erreur
    
    Notes:
        - Cette fonction est 非bloquante grâce à l'exécution asynchrone
          de BCASL via run_pre_compile_async()
        - L'interface reste réactive pendant l'exécution de BCASL
        - La compilation réelle ne démarre qu'après BCASL (gating strict)
        - En cas d'erreur, _kill_all_processes() assure un nettoyage complet
    """
    import os

    # -----------------------------------------------------------------------------
    # ÉTAPE 1 : Vérifications préliminaires
    # -----------------------------------------------------------------------------
    
    # Vérification : une compilation est-elle déjà en cours?
    if self.processes:
        try:
            QMessageBox.warning(
                self,
                self.tr("Attention", "Warning"),
                self.tr(
                    "Des compilations sont déjà en cours.",
                    "Builds are already running.",
                ),
            )
        except Exception:
            pass
        return

    # Vérification : workspace et fichiers disponibles?
    if not self.workspace_dir or (not self.python_files and not self.selected_files):
        try:
            self.log.append("❌ Aucun fichier à compiler.\n")
        except Exception:
            pass
        return

    # -----------------------------------------------------------------------------
    # ÉTAPE 2 : Initialisation
    # -----------------------------------------------------------------------------
    
    # Réinitialiser les statistiques de compilation
    try:
        self._compilation_times = {}
    except Exception:
        pass

    # Désactiver les contrôles sensibles (sauf Annuler)
    try:
        self.set_controls_enabled(False)
    except Exception:
        pass
    try:
        if hasattr(self, "compiler_tabs") and self.compiler_tabs:
            self.compiler_tabs.setEnabled(False)
    except Exception:
        pass

    # -----------------------------------------------------------------------------
    # ÉTAPE 3 : Exécution de BCASL
    # -----------------------------------------------------------------------------
    try:
        from bcasl.Loader import run_pre_compile_async as _run_bcasl_async

        # Drapeau de poursuite pour éviter le double déclenchement
        try:
            self._compile_continued = False
        except Exception:
            pass

        # Callback exécuté après la fin de BCASL
        def _after_bcasl(_report) -> None:
            """
            Callback appelé après l'exécution de BCASL.
            
            Gère les différents cas de retour de BCASL et lance
            la compilation si tout s'est bien passé.
            
            Args:
                _report: Rapport de BCASL (dict ou objet avec attributs)
            """
            try:
                # Arrêter le timer de fallback si existant
                try:
                    tmr2 = getattr(self, "_compile_phase_timer", None)
                    if tmr2:
                        tmr2.stop()
                except Exception:
                    pass

                # Vérifier si BCASL a eu des erreurs
                if _report is not None:
                    if isinstance(_report, dict):
                        # Cas spécial: BCASL désactivé
                        if _report.get("status") == "disabled":
                            # BCASL désactivé, continuer normalement
                            pass
                        else:
                            # Autre dict inattendu, traiter comme erreur
                            try:
                                self.log.append(
                                    f"❌ Erreur BCASL: rapport inattendu {_report}\n"
                                )
                            except Exception:
                                pass
                            _kill_all_processes(self)
                            return
                    elif hasattr(_report, 'ok') and not _report.ok:
                        # BCASL a rencontré des erreurs
                        error_items = [
                            item for item in _report.items if not item.success
                        ]
                        error_msg = ", ".join(
                            [f"{item.plugin_id}: {item.error}" for item in error_items]
                        )
                        try:
                            self.log.append(f"❌ Erreur BCASL: {error_msg}\n")
                        except Exception:
                            pass
                        # Nettoyer tout et réactiver l'UI
                        _kill_all_processes(self)
                        return

                # BCASL OK, continuer la compilation
                if not getattr(self, "_compile_continued", False):
                    self._compile_continued = True
                    try:
                        self.log.append("⏭️ Démarrage compilation après BCASL.\n")
                    except Exception:
                        pass
                    try:
                        _continue_compile_all(self)
                    except Exception as _e:
                        try:
                            self.log.append(
                                f"❌ Erreur fatale dans _continue_compile_all: "
                                f"{_e}\n{traceback.format_exc()}\n"
                            )
                        except Exception:
                            pass
                        # En cas d'erreur: tout tuer et réinitialiser
                        _kill_all_processes(self)
            
            except Exception as _e:
                try:
                    self.log.append(
                        f"❌ Erreur critique dans _after_bcasl: "
                        f"{_e}\n{traceback.format_exc()}\n"
                    )
                except Exception:
                    pass
                # En cas d'erreur: tout tuer et réinitialiser
                _kill_all_processes(self)

        # Lancer BCASL de manière asynchrone
        _run_bcasl_async(self, _after_bcasl)
        return  # Retourner immédiatement, la suite se fait dans le callback

    except Exception as e:
        # BCASL n'a pas pu s'exécuter
        try:
            self.log.append(
                f"❌ BCASL non exécuté: {e}\n"
                f"La compilation est annulée car les API BCASL doivent "
                f"terminer avant de compiler.\n"
            )
        except Exception:
            pass
        # Réactiver l'UI et sortir
        try:
            if hasattr(self, "compiler_tabs") and self.compiler_tabs:
                self.compiler_tabs.setEnabled(True)
        except Exception:
            pass
        try:
            self.set_controls_enabled(True)
        except Exception:
            pass
        return


# =============================================================================
# FIN DU MODULE compiler.py
# =============================================================================

