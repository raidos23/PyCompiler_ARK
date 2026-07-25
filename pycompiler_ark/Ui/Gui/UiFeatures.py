# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Samuel Amen Ague
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
UiFeatures — mixin de fonctionnalités UI pour PyCompiler ARK.

Ce module ne contient que du code Qt. Toute logique métier est déléguée à Core/.
"""

import os
import platform
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QApplication, QFileDialog, QMenu, QMessageBox

from pycompiler_ark.Ui import output


class UiFeatures:
    """Mixin UI helper utilisé par la fenêtre principale."""

    # =========================================================================
    # SÉLECTION D'ICÔNE
    # =========================================================================

    def select_icon(self):
        """Open a file dialog to select the main icon."""
        icon_preview = getattr(self, "icon_preview", None)
        file, _ = QFileDialog.getOpenFileName(
            self, "Choisir un fichier .ico", "", "Icon Files (*.ico)"
        )
        if file:
            self.icon_path = file
            output.info(
                (f"🎨 Icône sélectionnée : {file}", f"🎨 Icon selected: {file}"),
                gui=self,
            )
            pixmap = QPixmap(file)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(
                    64,
                    64,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                if icon_preview is not None:
                    icon_preview.setPixmap(scaled_pixmap)
                    icon_preview.show()
            else:
                if icon_preview is not None:
                    icon_preview.hide()
        else:
            self.icon_path = None
            if icon_preview is not None:
                icon_preview.hide()
        self.update_command_preview()
        try:
            self.save_preferences()
        except Exception:
            pass

    # =========================================================================
    # DIALOGUE D'AIDE
    # =========================================================================

    def show_help_dialog(self):
        """Show the localized help dialog."""
        try:
            from ..i18n import translate

            help_title = translate(self, "help_title", "Help")
            help_text = translate(self, "help_text", "")
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
        """Enable context menu actions for entrypoint selection."""
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
        """Show context actions to set/clear workspace entrypoint."""
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
        """Return the icon used to mark the current entrypoint."""
        icon = getattr(self, "_entrypoint_icon_cache", None)
        token = getattr(self, "_entrypoint_icon_theme_token", None)
        try:
            app = QApplication.instance()
            css = app.styleSheet() if app else ""
        except Exception:
            css = ""
        current_token = hash(css or "")
        if token == current_token and isinstance(icon, QIcon) and not icon.isNull():
            return icon
        try:
            base = os.path.abspath(
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
            )
            path = os.path.join(base, "data", "icons", "check-circle.svg")
            if os.path.isfile(path):
                icon = None
                try:
                    from .UiConnection import themed_svg_icon

                    icon = themed_svg_icon(path, size=16, css=css)
                except Exception:
                    icon = None
                if icon is None or icon.isNull():
                    icon = QIcon(path)
                if not icon.isNull():
                    self._entrypoint_icon_cache = icon
                    self._entrypoint_icon_theme_token = current_token
                    return icon
        except Exception:
            pass
        return None

    def _refresh_entrypoint_marker(self) -> None:
        """Refresh entrypoint visual marker in the file list."""
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
        """Load workspace entrypoint from `ark.yml`."""
        workspace_dir = getattr(self, "workspace_dir", None)
        if not workspace_dir:
            return
        try:
            from pycompiler_ark.Core.Configs import get_entrypoint, load_ark_config

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
        """Set entrypoint using a selected file-list item."""
        if item is None:
            return
        rel_path = item.text()
        self.set_entrypoint(rel_path)

    def set_entrypoint(self, rel_path: str) -> None:
        """Persist a new workspace entrypoint in ARK config."""
        workspace_dir = getattr(self, "workspace_dir", None)
        if not workspace_dir or not rel_path:
            return
        abs_path = os.path.join(workspace_dir, rel_path)
        if not os.path.isfile(abs_path):
            output.warn(
                (
                    f"⚠️ Point d'entrée introuvable: {abs_path}",
                    f"⚠️ Entrypoint not found: {abs_path}",
                ),
                gui=self,
            )
            return
        try:
            from pycompiler_ark.Core.Configs import set_entrypoint

            ok = set_entrypoint(workspace_dir, rel_path)
        except Exception:
            ok = False
        if ok:
            self._entrypoint_relpath = rel_path
            self.entrypoint_file = abs_path
            self._refresh_entrypoint_marker()
            output.success(
                (
                    f"✅ Point d'entrée défini : {rel_path}",
                    f"✅ Entrypoint set: {rel_path}",
                ),
                gui=self,
            )
        else:
            output.error(
                (
                    "❌ Impossible de sauvegarder le point d'entrée.",
                    "❌ Unable to save entrypoint.",
                ),
                gui=self,
            )

    def clear_entrypoint(self) -> None:
        """Clear workspace entrypoint and update UI markers."""
        workspace_dir = getattr(self, "workspace_dir", None)
        if not workspace_dir:
            return
        try:
            from pycompiler_ark.Core.Configs import set_entrypoint

            ok = set_entrypoint(workspace_dir, None)
        except Exception:
            ok = False
        if ok:
            self._entrypoint_relpath = None
            self.entrypoint_file = None
            self._refresh_entrypoint_marker()
            output.success(
                ("✅ Point d'entrée effacé.", "✅ Entrypoint cleared."), gui=self
            )
        else:
            output.error(
                (
                    "❌ Impossible d'effacer le point d'entrée.",
                    "❌ Unable to clear entrypoint.",
                ),
                gui=self,
            )

    # =========================================================================
    # STATISTICS
    # =========================================================================

    def save_all_engine_configs(self) -> None:
        """Save configuration for all registered engines in one click."""
        workspace_dir = getattr(self, "workspace_dir", None)
        if not workspace_dir:
            output.error(
                ("❌ Aucun workspace sélectionné.", "❌ No workspace selected."),
                gui=self,
            )
            QMessageBox.warning(
                self,
                self.tr("Workspace manquant", "Workspace missing"),
                self.tr(
                    "Veuillez d'abord sélectionner un dossier workspace.",
                    "Please select a workspace folder first.",
                ),
            )
            return
        try:
            import pycompiler_ark.Core.engine as engines_loader

            from ...Core.engine.ConfigManager import (
                save_engine_config_for_gui,
            )

            engine_ids = list(engines_loader.available_engines())
            if not engine_ids:
                output.warn(("⚠️ Aucun moteur chargé.", "⚠️ No engine loaded."), gui=self)
                return

            saved = 0
            failed: list[str] = []
            for engine_id in engine_ids:
                try:
                    if save_engine_config_for_gui(self, engine_id):
                        saved += 1
                    else:
                        failed.append(str(engine_id))
                except Exception:
                    failed.append(str(engine_id))

            if failed:
                output.warn(
                    (
                        f"⚠️ Configs engines sauvegardées: {saved}/{len(engine_ids)}. Échecs: {', '.join(failed)}",
                        f"⚠️ Engine configs saved: {saved}/{len(engine_ids)}. Failed: {', '.join(failed)}",
                    ),
                    gui=self,
                )
            else:
                output.success(
                    (
                        f"✅ Configs engines sauvegardées: {saved}/{len(engine_ids)}",
                        f"✅ Engine configs saved: {saved}/{len(engine_ids)}",
                    ),
                    gui=self,
                )
        except Exception as e:
            output.error(
                (
                    f"❌ Erreur sauvegarde configs engines: {e}",
                    f"❌ Error saving engine configs: {e}",
                ),
                gui=self,
            )

    def update_command_preview(self):
        """Update command preview (no-op placeholder)."""
        pass

    # =========================================================================
    # CONTRÔLES D'INTERFACE
    # =========================================================================

    def set_controls_enabled(self, enabled: bool) -> None:
        """Enable or disable primary UI controls."""
        if hasattr(self, "compile_btn") and self.compile_btn:
            self.compile_btn.setEnabled(enabled)
            try:
                if hasattr(self.compile_btn, "style"):
                    self.compile_btn.style().unpolish(self.compile_btn)
                    self.compile_btn.style().polish(self.compile_btn)
                    self.compile_btn.update()
            except Exception:
                pass

        if hasattr(self, "cancel_btn") and self.cancel_btn:
            self.cancel_btn.setEnabled(not enabled)

        if hasattr(self, "btn_select_folder") and self.btn_select_folder:
            self.btn_select_folder.setEnabled(enabled)
        if hasattr(self, "btn_select_files") and self.btn_select_files:
            self.btn_select_files.setEnabled(enabled)
        if hasattr(self, "btn_remove_file") and self.btn_remove_file:
            self.btn_remove_file.setEnabled(enabled)

        if hasattr(self, "file_list") and self.file_list:
            self.file_list.setEnabled(enabled)
        if hasattr(self, "file_filter_input") and self.file_filter_input:
            self.file_filter_input.setEnabled(enabled)

        for attr in (
            "btn_suggest_deps",
            "btn_bc_loader",
            "btn_acasl_loader",
            "select_lang",
            "select_theme",
            "btn_show_stats",
            "btn_clear_workspace",
            "btn_help",
            "btn_lock_manager",
            "activity_btn_deps",
            "advanced_cfg_btn",
            "toolButton_more",
            "compiler_tabs",
        ):
            try:
                w = getattr(self, attr, None)
                if w:
                    w.setEnabled(enabled)
            except Exception:
                pass

        if hasattr(self, "venv_button") and self.venv_button:
            self.venv_button.setEnabled(enabled)

        self._refresh_grey_targets()
        try:
            QApplication.processEvents()
        except Exception:
            pass

    def _refresh_grey_targets(self) -> None:
        """Refresh visual state of controls."""
        try:
            target_names = (
                "compile_btn",
                "btn_select_folder",
                "btn_select_files",
                "btn_remove_file",
                "btn_bc_loader",
                "btn_acasl_loader",
                "btn_suggest_deps",
                "select_lang",
                "select_theme",
                "btn_show_stats",
                "btn_clear_workspace",
                "venv_button",
                "btn_help",
                "btn_lock_manager",
                "activity_btn_deps",
                "advanced_cfg_btn",
                "toolButton_more",
                "file_list",
                "file_filter_input",
            )
            for attr in target_names:
                try:
                    w = getattr(self, attr, None)
                    if w and hasattr(w, "style"):
                        w.style().unpolish(w)
                        w.style().polish(w)
                        w.update()
                except Exception:
                    pass

            if hasattr(self, "cancel_btn") and self.cancel_btn:
                try:
                    if hasattr(self.cancel_btn, "style"):
                        self.cancel_btn.style().unpolish(self.cancel_btn)
                        self.cancel_btn.style().polish(self.cancel_btn)
                        self.cancel_btn.update()
                except Exception:
                    pass
        except Exception:
            pass

    def set_compilation_ui_enabled(self, enabled: bool) -> None:
        """Alias for set_controls_enabled during compilation."""
        self.set_controls_enabled(enabled)

    # =========================================================================
    # STATISTIQUES
    # =========================================================================

    def show_statistics(self) -> None:
        """Show compilation statistics."""
        workspace_dir = getattr(self, "workspace_dir", None)
        if not workspace_dir:
            QMessageBox.warning(
                self,
                self.tr("Workspace manquant", "Workspace missing"),
                self.tr(
                    "Veuillez d'abord sélectionner un dossier workspace.",
                    "Please select a workspace folder first.",
                ),
            )
            return

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
            slowest_files = []
            for path, fstats in stats.get("files", {}).items():
                if not isinstance(fstats, dict):
                    continue
                candidate = fstats.get("max_time") or fstats.get("last_time")
                if candidate is None:
                    continue
                slowest_files.append((path, float(candidate)))
            slowest_files.sort(key=lambda item: item[1], reverse=True)
            slowest_file = slowest_files[0][0] if slowest_files else None
            slowest_time = slowest_files[0][1] if slowest_files else None
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
            slowest_file = (
                max(self._compilation_times, key=self._compilation_times.get)
                if total_files
                else None
            )
            slowest_time = max_time
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

        msg = f"<b>{self.tr('Statistiques de compilation', 'Build statistics')}</b><br><br>"
        msg += f"{self.tr('Fichiers distincts', 'Distinct files')} : {total_files}<br>"
        msg += (
            f"{self.tr('Compilations totales', 'Total builds')} : {total_compiles}<br>"
        )
        msg += (
            f"{self.tr('Succès', 'Success')} : {success} | "
            f"{self.tr('Échecs', 'Failed')} : {failed} | "
            f"{self.tr('Annulées', 'Cancelled')} : {canceled}<br>"
        )
        msg += f"{self.tr('Temps total', 'Total time')} : {total_time:.3f} {self.tr('secondes', 'seconds')}<br>"
        msg += f"{self.tr('Temps moyen', 'Average time')} : {avg_time:.3f} {self.tr('secondes', 'seconds')}<br>"
        if min_time is not None and max_time is not None:
            msg += f"{self.tr('Temps min/max', 'Min/max time')} : {float(min_time):.3f} / {float(max_time):.3f} {self.tr('secondes', 'seconds')}<br>"

        if slowest_file and slowest_time is not None:
            msg += (
                f"<br><b>{self.tr('Fichier le plus lent', 'Slowest file')}</b> : {os.path.basename(str(slowest_file))}"
                f" ({float(slowest_time):.3f} {self.tr('secondes', 'seconds')})<br>"
            )
        if slowest_files:
            top_n = slowest_files[:5]
            msg += f"<br><b>{self.tr('Top 5 fichiers les plus lents', 'Top 5 slowest files')} :</b><br>"
            for path, duration in top_n:
                msg += f"- {os.path.basename(str(path))} ({float(duration):.3f} {self.tr('secondes', 'seconds')})<br>"

        if isinstance(engines, dict) and engines:
            msg += f"<br><b>{self.tr('Par moteur', 'By engine')} :</b><br>"
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
                    f"- {engine_id} : {eng_count} {self.tr('compiles', 'builds')} | "
                    f"{eng_success} OK / {eng_failed} KO / {eng_canceled} {self.tr('ann.', 'canc.')} | "
                    f"{eng_avg:.3f}s {self.tr('moy', 'avg')}<br>"
                )

        if last_file and last_duration is not None:
            msg += f"<br><b>{self.tr('Dernier build', 'Last build')}</b> : {os.path.basename(str(last_file))}"
            msg += f" ({float(last_duration):.3f} {self.tr('secondes', 'seconds')})<br>"

        if mem_info is not None:
            msg += f"<br>{self.tr('Mémoire utilisée (GUI)', 'Memory usage (GUI)')} : {mem_info:.1f} Mo<br>"

        QMessageBox.information(
            self, self.tr("Statistiques de compilation", "Build statistics"), msg
        )

    # =========================================================================
    # INTERNATIONALISATION
    # =========================================================================

    def apply_language(self, lang_display: str) -> None:
        """Apply the selected language."""
        from ..i18n import apply_language as _i18n_apply_language

        _i18n_apply_language(self, lang_display)

    def register_language_refresh(self, callback: Callable) -> None:
        """Register a callback used for language refresh."""
        try:
            if not hasattr(self, "_language_refresh_callbacks"):
                self._language_refresh_callbacks = []
            if callable(callback):
                self._language_refresh_callbacks.append(callback)
        except Exception:
            pass

    def unregister_language_refresh(self, callback: Callable) -> None:
        """Unregister a previously registered language refresh callback."""
        try:
            callbacks = getattr(self, "_language_refresh_callbacks", None)
            if not callbacks:
                return
            if callback in callbacks:
                callbacks.remove(callback)
        except Exception:
            pass

    def show_language_dialog(self) -> None:
        """Open language selection dialog."""
        from .Dialogs.i18nDialog import show_language_dialog as _i18n_show_dialog

        _i18n_show_dialog(self)

    def _apply_main_app_translations(self, tr: dict) -> None:
        """Apply translations to main UI elements."""
        from ..i18n import (
            _apply_main_app_translations as _i18n_apply_translations,
        )

        _i18n_apply_translations(self, tr)

    def open_advanced_config_editor(self):
        """Open the advanced config editor dialog."""
        workspace_dir = getattr(self, "workspace_dir", None)
        if not workspace_dir:
            output.error(
                ("❌ Aucun workspace sélectionné.", "❌ No workspace selected."),
                gui=self,
            )
            QMessageBox.warning(
                self,
                self.tr("Workspace manquant", "Workspace missing"),
                self.tr(
                    "Veuillez sélectionner un Workspace pour accéder à l'éditeur avancé.",
                    "Please select a Workspace to access the advanced editor.",
                ),
            )
            return

        try:
            from .Dialogs.ConfigEditor import (
                ConfigEditor,
            )

            dlg = ConfigEditor(self)
            dlg.setModal(True)
            dlg.exec()
        except Exception as e:
            try:
                output.error(
                    (
                        f"Erreur ouverture configurations avancées: {e}",
                        f"Failed to open advanced configurations: {e}",
                    ),
                    gui=self,
                )
            except Exception:
                pass
