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
UiFeatures Module

Module de fonctionnalités UI pour PyCompiler ARK.
Contient les méthodes liées à l'interface utilisateur qui peuvent être
déconnectées ou remplacées selon les besoins de l'application.

Fournit:
- Gestion des icônes
- Export/Import de configuration
- Langue et internationalisation
- Contrôles d'interface
"""

import asyncio
import json
import os
import platform
from typing import Optional, Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QFileDialog, QMessageBox, QMenu


class UiFeatures:
    """
    Classe de fonctionnalités UI pour PyCompiler ARK.

    Cette classe contient les méthodes liées à l'interface utilisateur
    et peut être utilisée comme mixin ou importée séparément.
    """

    # =========================================================================
    # SÉLECTION D'ICÔNE
    # =========================================================================

    def select_icon(self):
        """Ouvre une boîte de dialogue pour sélectionner une icône."""
        file, _ = QFileDialog.getOpenFileName(
            self, "Choisir un fichier .ico", "", "Icon Files (*.ico)"
        )
        if file:
            self.icon_path = file
            self.log_i18n(
                f"🎨 Icône sélectionnée : {file}", f"🎨 Icon selected: {file}"
            )
            pixmap = QPixmap(file)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(
                    64,
                    64,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.icon_preview.setPixmap(scaled_pixmap)
                self.icon_preview.show()
            else:
                self.icon_preview.hide()
        else:
            # Annulation: supprimer l'icône sélectionnée et masquer l'aperçu
            self.icon_path = None
            self.icon_preview.hide()
        # Persistance et mise à jour en temps réel
        self.update_command_preview()
        try:
            self.save_preferences()
        except Exception:
            pass

    def select_nuitka_icon(self):
        """Ouvre une boîte de dialogue pour sélectionner une icône pour Nuitka (Windows uniquement)."""
        import platform

        if platform.system() != "Windows":
            return
        file, _ = QFileDialog.getOpenFileName(
            self, "Choisir une icône .ico pour Nuitka", "", "Icon Files (*.ico)"
        )
        if file:
            self.nuitka_icon_path = file
            self.log_i18n(
                f"🎨 Icône Nuitka sélectionnée : {file}",
                f"🎨 Nuitka icon selected: {file}",
            )
        else:
            self.nuitka_icon_path = None
        self.update_command_preview()

    # =========================================================================
    # DIALOGUE D'AIDE
    # =========================================================================

    def show_help_dialog(self):
        """Affiche une boîte de dialogue d'aide."""
        try:
            tr = getattr(self, "_tr", None)
            if tr and isinstance(tr, dict):
                help_title = tr.get("help_title", "Help")
                help_text = tr.get("help_text", "")
            else:
                help_title = "Help"
                help_text = ""
        except Exception:
            help_title = "Help"
            help_text = ""
        dlg = QMessageBox(self)
        dlg.setWindowTitle(help_title)
        dlg.setTextFormat(Qt.TextFormat.RichText)
        dlg.setText(help_text)
        dlg.setIcon(QMessageBox.Icon.Information)
        dlg.setStandardButtons(QMessageBox.StandardButton.Ok)
        dlg.exec()

    # =========================================================================
    # POINT D'ENTRÉE (ENTRYPOINT)
    # =========================================================================

    def setup_entrypoint_selector(self) -> None:
        """Configure le menu contextuel pour choisir le point d'entrée."""
        if not getattr(self, "file_list", None):
            return
        try:
            self.file_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            self.file_list.customContextMenuRequested.connect(
                self._show_entrypoint_menu
            )
        except Exception:
            pass

    def _show_entrypoint_menu(self, pos) -> None:
        """Affiche un menu contextuel pour gérer le point d'entrée."""
        if not getattr(self, "file_list", None):
            return
        item = self.file_list.itemAt(pos)
        menu = QMenu(self.file_list)

        set_action = None
        if item is not None:
            set_action = menu.addAction(
                self.tr("Définir comme point d'entrée", "Set as entrypoint")
            )
        clear_action = menu.addAction(
            self.tr("Effacer le point d'entrée", "Clear entrypoint")
        )

        chosen = menu.exec(self.file_list.viewport().mapToGlobal(pos))
        if chosen is None:
            return
        if chosen == set_action and item is not None:
            self.set_entrypoint_from_item(item)
        elif chosen == clear_action:
            self.clear_entrypoint()

    def _entrypoint_icon(self) -> QIcon | None:
        """Retourne l'icône utilisée pour marquer le point d'entrée."""
        icon = getattr(self, "_entrypoint_icon_cache", None)
        if isinstance(icon, QIcon) and not icon.isNull():
            return icon
        try:
            base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            path = os.path.join(base, "icons", "icons8-coche-50-2.svg")
            if os.path.isfile(path):
                icon = QIcon(path)
                if not icon.isNull():
                    self._entrypoint_icon_cache = icon
                    return icon
        except Exception:
            pass
        return None

    def _refresh_entrypoint_marker(self) -> None:
        """Met à jour l'affichage du point d'entrée dans la liste des fichiers."""
        if not getattr(self, "file_list", None):
            return
        entry_rel = getattr(self, "_entrypoint_relpath", None)
        icon = self._entrypoint_icon()
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if item is None:
                continue
            if entry_rel and item.text() == entry_rel and icon:
                item.setIcon(icon)
            else:
                item.setIcon(QIcon())

    def load_entrypoint_from_config(self) -> None:
        """Charge le point d'entrée depuis ARK_Main_Config.yml."""
        workspace_dir = getattr(self, "workspace_dir", None)
        if not workspace_dir:
            return
        try:
            from .ArkConfigManager import load_ark_config, get_entrypoint

            cfg = load_ark_config(workspace_dir)
            entry_rel = get_entrypoint(cfg)
        except Exception:
            entry_rel = None

        self._entrypoint_relpath = entry_rel
        if entry_rel and workspace_dir:
            self.entrypoint_file = os.path.join(workspace_dir, entry_rel)
        else:
            self.entrypoint_file = None
        self._refresh_entrypoint_marker()

    def set_entrypoint_from_item(self, item) -> None:
        """Définit le point d'entrée à partir d'un item de la liste."""
        if item is None:
            return
        rel_path = item.text()
        self.set_entrypoint(rel_path)

    def set_entrypoint(self, rel_path: str) -> None:
        """Définit et sauvegarde le point d'entrée dans la config ARK."""
        workspace_dir = getattr(self, "workspace_dir", None)
        if not workspace_dir or not rel_path:
            return
        abs_path = os.path.join(workspace_dir, rel_path)
        if not os.path.isfile(abs_path):
            self.log_i18n(
                f"⚠️ Point d'entrée introuvable: {abs_path}",
                f"⚠️ Entrypoint not found: {abs_path}",
            )
            return
        try:
            from .ArkConfigManager import set_entrypoint

            ok = set_entrypoint(workspace_dir, rel_path)
        except Exception:
            ok = False
        if ok:
            self._entrypoint_relpath = rel_path
            self.entrypoint_file = abs_path
            self._refresh_entrypoint_marker()
            self.log_i18n(
                f"✅ Point d'entrée défini : {rel_path}",
                f"✅ Entrypoint set: {rel_path}",
            )
        else:
            self.log_i18n(
                "❌ Impossible de sauvegarder le point d'entrée.",
                "❌ Unable to save entrypoint.",
            )

    def clear_entrypoint(self) -> None:
        """Efface le point d'entrée et met à jour la configuration."""
        workspace_dir = getattr(self, "workspace_dir", None)
        if not workspace_dir:
            return
        try:
            from .ArkConfigManager import set_entrypoint

            ok = set_entrypoint(workspace_dir, None)
        except Exception:
            ok = False
        if ok:
            self._entrypoint_relpath = None
            self.entrypoint_file = None
            self._refresh_entrypoint_marker()
            self.log_i18n(
                "✅ Point d'entrée effacé.",
                "✅ Entrypoint cleared.",
            )
        else:
            self.log_i18n(
                "❌ Impossible d'effacer le point d'entrée.",
                "❌ Unable to clear entrypoint.",
            )

    # =========================================================================
    # EXPORT/IMPORT CONFIGURATION
    # =========================================================================

    def export_config(self):
        """Exporte la configuration vers un fichier JSON."""
        file, _ = QFileDialog.getSaveFileName(
            self, "Exporter la configuration", "", "JSON Files (*.json)"
        )
        if file:
            if not file.endswith(".json"):
                file += ".json"
            # Normaliser la préférence de langue
            try:
                from .i18n import normalize_lang_pref

                base_lang_pref = getattr(
                    self,
                    "language_pref",
                    getattr(
                        self, "language", getattr(self, "current_language", "System")
                    ),
                )
                lang_pref_out = (
                    base_lang_pref
                    if base_lang_pref == "System"
                    else asyncio.run(normalize_lang_pref(base_lang_pref))
                )
            except Exception:
                lang_pref_out = getattr(self, "language_pref", "System")
            # Export minimal
            prefs = {
                "language_pref": lang_pref_out,
                "theme": getattr(self, "theme", "System"),
            }
            try:
                with open(file, "w", encoding="utf-8") as f:
                    json.dump(prefs, f, indent=4)
                self.log_i18n(
                    f"✅ Configuration exportée : {file}",
                    f"✅ Configuration exported: {file}",
                )
            except Exception as e:
                self.log_i18n(
                    f"❌ Erreur export configuration : {e}",
                    f"❌ Error exporting configuration: {e}",
                )

    def import_config(self):
        """Importe la configuration depuis un fichier JSON."""
        file, _ = QFileDialog.getOpenFileName(
            self, "Importer la configuration", "", "JSON Files (*.json)"
        )
        if file:
            try:
                with open(file, encoding="utf-8") as f:
                    prefs = json.load(f)
                # Appliquer la préférence de langue
                try:
                    lang_pref_in = prefs.get(
                        "language_pref", prefs.get("language", None)
                    )
                    if lang_pref_in is not None:
                        from .i18n import (
                            get_translations,
                            normalize_lang_pref,
                            resolve_system_language,
                        )

                        if lang_pref_in == "System":
                            self.language_pref = "System"
                            self.apply_language("System")
                            if getattr(self, "select_lang", None):

                                async def _fetch_sys():
                                    code = await resolve_system_language()
                                    return await get_translations(code)

                                from .Globals import _run_coro_async

                                _run_coro_async(
                                    _fetch_sys(),
                                    lambda tr: self.select_lang.setText(
                                        tr.get("choose_language_system_button")
                                        or tr.get("select_lang")
                                        or ""
                                    ),
                                    ui_owner=self,
                                )
                        else:
                            code = asyncio.run(normalize_lang_pref(lang_pref_in))
                            self.language_pref = code
                            self.apply_language(code)
                            if getattr(self, "select_lang", None):
                                from .Globals import _run_coro_async

                                _run_coro_async(
                                    get_translations(code),
                                    lambda tr2: self.select_lang.setText(
                                        tr2.get("choose_language_button")
                                        or tr2.get("select_lang")
                                        or ""
                                    ),
                                    ui_owner=self,
                                )
                except Exception:
                    pass
                # Appliquer la préférence de thème
                try:
                    theme_pref = prefs.get("theme", None)
                    if theme_pref is not None:
                        from .UiConnection import apply_theme

                        self.theme = theme_pref
                        apply_theme(self, theme_pref)
                except Exception:
                    pass
                self.log_i18n(
                    f"✅ Configuration importée : {file}",
                    f"✅ Configuration imported: {file}",
                )
                self.update_command_preview()
                try:
                    self.save_preferences()
                except Exception:
                    pass
            except Exception as e:
                self.log_i18n(
                    f"❌ Erreur import configuration : {e}",
                    f"❌ Error importing configuration: {e}",
                )

    def update_command_preview(self):
        """Met à jour l'aperçu de commande (placeholder)."""
        # Cette méthode est maintenant vide car les options sont gérées dynamiquement par les moteurs
        pass

    # =========================================================================
    # CONTRÔLES D'INTERFACE
    # =========================================================================

    def set_controls_enabled(self, enabled: bool) -> None:
        """Active ou désactive les contrôles de l'interface."""
        self.compile_btn.setEnabled(enabled)
        # Forcer une mise à jour visuelle
        try:
            if self.compile_btn and hasattr(self.compile_btn, "style"):
                self.compile_btn.style().unpolish(self.compile_btn)
                self.compile_btn.style().polish(self.compile_btn)
                self.compile_btn.update()
        except Exception:
            pass
        self.cancel_btn.setEnabled(not enabled)
        self.btn_select_folder.setEnabled(enabled)
        self.btn_select_files.setEnabled(enabled)
        self.btn_remove_file.setEnabled(enabled)

        # Check if buttons exist before calling setEnabled
        try:
            if hasattr(self, "btn_export_config") and self.btn_export_config:
                self.btn_export_config.setEnabled(enabled)
        except Exception:
            pass
        try:
            if hasattr(self, "btn_import_config") and self.btn_import_config:
                self.btn_import_config.setEnabled(enabled)
        except Exception:
            pass
        try:
            if hasattr(self, "btn_suggest_deps") and self.btn_suggest_deps:
                self.btn_suggest_deps.setEnabled(enabled)
        except Exception:
            pass
        try:
            if hasattr(self, "btn_bc_loader") and self.btn_bc_loader:
                self.btn_bc_loader.setEnabled(enabled)
        except Exception:
            pass
        try:
            if hasattr(self, "select_lang") and self.select_lang:
                self.select_lang.setEnabled(enabled)
        except Exception:
            pass
        try:
            if hasattr(self, "select_theme") and self.select_theme:
                self.select_theme.setEnabled(enabled)
        except Exception:
            pass
        try:
            if hasattr(self, "btn_show_stats") and self.btn_show_stats:
                self.btn_show_stats.setEnabled(enabled)
        except Exception:
            pass
        try:
            if hasattr(self, "btn_clear_workspace") and self.btn_clear_workspace:
                self.btn_clear_workspace.setEnabled(enabled)
        except Exception:
            pass
        self.venv_button.setEnabled(enabled)

        # Rafraîchir visuellement l'état grisé
        self._refresh_grey_targets()

    def _refresh_grey_targets(self) -> None:
        """Rafraîchit l'état visuel des contrôles."""
        try:
            grey_targets = [
                getattr(self, "compile_btn", None),
                getattr(self, "btn_select_folder", None),
                getattr(self, "btn_select_files", None),
                getattr(self, "btn_remove_file", None),
                getattr(self, "btn_export_config", None),
                getattr(self, "btn_import_config", None),
                getattr(self, "btn_bc_loader", None),
                getattr(self, "btn_suggest_deps", None),
                getattr(self, "select_lang", None),
                getattr(self, "select_theme", None),
                getattr(self, "btn_show_stats", None),
                getattr(self, "btn_clear_workspace", None),
                getattr(self, "venv_button", None),
            ]
            for w in grey_targets:
                try:
                    if w and hasattr(w, "style"):
                        w.style().unpolish(w)
                        w.style().polish(w)
                        w.update()
                except Exception:
                    pass
            # Cancel reflète visuellement son état inverse
            if hasattr(self, "cancel_btn") and self.cancel_btn:
                try:
                    self.cancel_btn.style().unpolish(self.cancel_btn)
                    self.cancel_btn.style().polish(self.cancel_btn)
                    self.cancel_btn.update()
                except Exception:
                    pass
        except Exception:
            pass

    def set_compilation_ui_enabled(self, enabled: bool) -> None:
        """Alias pour set_controls_enabled pendant la compilation."""
        self.set_controls_enabled(enabled)

    # =========================================================================
    # STATISTIQUES
    # =========================================================================

    def show_statistics(self) -> None:
        """Affiche les statistiques de compilation."""
        try:
            import psutil
        except Exception:
            psutil = None

        stats = getattr(self, "_compilation_stats", None)
        use_new = isinstance(stats, dict) and stats.get("total_count", 0) > 0

        if not use_new and (
            not hasattr(self, "_compilation_times") or not self._compilation_times
        ):
            QMessageBox.information(
                self,
                self.tr("Statistiques", "Statistics"),
                self.tr(
                    "Aucune compilation récente à analyser.",
                    "No recent builds to analyze.",
                ),
            )
            return

        if use_new:
            total_compiles = int(stats.get("total_count", 0))
            total_time = float(stats.get("total_time", 0.0))
            avg_time = total_time / total_compiles if total_compiles else 0.0
            total_files = len(stats.get("files", {}))
            success = int(stats.get("success", 0))
            failed = int(stats.get("failed", 0))
            canceled = int(stats.get("canceled", 0))
            min_time = stats.get("min_time")
            max_time = stats.get("max_time")
            last_file = stats.get("last_file")
            last_duration = stats.get("last_duration")
            engines = stats.get("engines", {})
            slowest_file = None
            slowest_time = None
            for path, fstats in stats.get("files", {}).items():
                if not isinstance(fstats, dict):
                    continue
                candidate = fstats.get("max_time")
                if candidate is None:
                    candidate = fstats.get("last_time")
                if candidate is None:
                    continue
                if slowest_time is None or float(candidate) > float(slowest_time):
                    slowest_time = float(candidate)
                    slowest_file = path
            slowest_files = []
            for path, fstats in stats.get("files", {}).items():
                if not isinstance(fstats, dict):
                    continue
                candidate = fstats.get("max_time")
                if candidate is None:
                    candidate = fstats.get("last_time")
                if candidate is None:
                    continue
                slowest_files.append((path, float(candidate)))
            slowest_files.sort(key=lambda item: item[1], reverse=True)
        else:
            total_files = len(self._compilation_times)
            total_time = sum(self._compilation_times.values())
            avg_time = total_time / total_files if total_files else 0
            total_compiles = total_files
            success = total_files
            failed = 0
            canceled = 0
            min_time = min(self._compilation_times.values()) if total_files else None
            max_time = max(self._compilation_times.values()) if total_files else None
            last_file = None
            last_duration = None
            engines = {}
            slowest_file = None
            slowest_time = max_time
            if total_files:
                slowest_file = max(self._compilation_times, key=self._compilation_times.get)
            slowest_files = [
                (path, float(duration))
                for path, duration in self._compilation_times.items()
            ]
            slowest_files.sort(key=lambda item: item[1], reverse=True)

        mem_info = None
        if psutil is not None:
            try:
                mem_info = psutil.Process().memory_info().rss / (1024 * 1024)
            except Exception:
                mem_info = None
        msg = "<b>Statistiques de compilation</b><br>"
        msg += f"Fichiers distincts : {total_files}<br>"
        msg += f"Compilations totales : {total_compiles}<br>"
        msg += f"Succès : {success} | Échecs : {failed} | Annulées : {canceled}<br>"
        msg += f"Temps total : {total_time:.3f} secondes<br>"
        msg += f"Temps moyen : {avg_time:.3f} secondes<br>"
        if min_time is not None and max_time is not None:
            msg += (
                f"Temps min/max : {float(min_time):.3f} / {float(max_time):.3f} secondes<br>"
            )
        if slowest_file and slowest_time is not None:
            msg += (
                f"Fichier le plus lent : {os.path.basename(str(slowest_file))}"
                f" ({float(slowest_time):.3f} secondes)<br>"
            )
        if slowest_files:
            top_n = slowest_files[:5]
            msg += "Top 5 fichiers les plus lents :<br>"
            for path, duration in top_n:
                msg += (
                    f"- {os.path.basename(str(path))} ({float(duration):.3f} secondes)<br>"
                )
        if isinstance(engines, dict) and engines:
            msg += "Par moteur :<br>"
            for engine_id, estats in engines.items():
                if not isinstance(estats, dict):
                    continue
                eng_count = int(estats.get("count", 0))
                eng_total = float(estats.get("total_time", 0.0))
                eng_avg = eng_total / eng_count if eng_count else 0.0
                eng_success = int(estats.get("success", 0))
                eng_failed = int(estats.get("failed", 0))
                eng_canceled = int(estats.get("canceled", 0))
                msg += (
                    f"- {engine_id} : {eng_count} compiles | "
                    f"{eng_success} OK / {eng_failed} KO / {eng_canceled} ann. | "
                    f"{eng_avg:.3f}s moy<br>"
                )
        if last_file and last_duration is not None:
            msg += f"Dernier fichier : {os.path.basename(str(last_file))}<br>"
            msg += f"Dernière durée : {float(last_duration):.3f} secondes<br>"
        if mem_info is not None:
            msg += f"Mémoire utilisée (processus GUI) : {mem_info:.1f} Mo<br>"
        QMessageBox.information(
            self, self.tr("Statistiques de compilation", "Build statistics"), msg
        )

    # =========================================================================
    # INTERNATIONALISATION
    # =========================================================================

    def apply_language(self, lang_display: str) -> None:
        """Applique la langue sélectionnée."""
        from .i18n import apply_language as _i18n_apply_language

        _i18n_apply_language(self, lang_display)

    def register_language_refresh(self, callback: Callable) -> None:
        """Enregistre un callback pour le rafraîchissement de langue."""
        try:
            if not hasattr(self, "_language_refresh_callbacks"):
                self._language_refresh_callbacks = []
            if callable(callback):
                self._language_refresh_callbacks.append(callback)
        except Exception:
            pass

    def log_i18n(self, fr: str, en: str) -> None:
        """Ajoute un message localisé au journal."""
        try:
            msg = self.tr(fr, en)
        except Exception:
            msg = en
        try:
            if hasattr(self, "log") and self.log:
                self.log.append(msg)
            else:
                print(msg)
        except Exception:
            try:
                print(msg)
            except Exception:
                pass

    def show_language_dialog(self) -> None:
        """Affiche la boîte de dialogue de sélection de langue."""
        from .i18n import show_language_dialog as _i18n_show_dialog

        _i18n_show_dialog(self)

    def _apply_main_app_translations(self, tr: dict) -> None:
        """Applique les traductions aux éléments UI."""
        from .i18n import _apply_main_app_translations as _i18n_apply_translations

        _i18n_apply_translations(self, tr)
