# -*- coding: utf-8 -*-
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

################################################################################
## Form generated from reading UI file 'ui_design.ui'
##
## Created by: Qt User Interface Compiler version 6.9.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QProgressBar, QPushButton,
    QScrollArea, QSizePolicy, QSpacerItem, QTabWidget,
    QTextEdit, QVBoxLayout, QWidget)

class Ui_PyCompilerARKGui(object):
    def setupUi(self, PyCompilerARKGui):
        if not PyCompilerARKGui.objectName():
            PyCompilerARKGui.setObjectName(u"PyCompilerARKGui")
        PyCompilerARKGui.resize(1280, 720)
        self.mainLayout = QHBoxLayout(PyCompilerARKGui)
        self.mainLayout.setSpacing(0)
        self.mainLayout.setObjectName(u"mainLayout")
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.sidebarScrollArea = QScrollArea(PyCompilerARKGui)
        self.sidebarScrollArea.setObjectName(u"sidebarScrollArea")
        self.sidebarScrollArea.setWidgetResizable(True)
        self.sidebarScrollArea.setMaximumWidth(320)
        self.sidebarScrollArea.setMinimumWidth(280)
        self.sidebar = QFrame()
        self.sidebar.setObjectName(u"sidebar")
        self.sidebar.setGeometry(QRect(0, 0, 320, 700))
        self.sidebar.setFrameShape(QFrame.Shape.NoFrame)
        self.sidebarLayout = QVBoxLayout(self.sidebar)
        self.sidebarLayout.setSpacing(12)
        self.sidebarLayout.setObjectName(u"sidebarLayout")
        self.sidebarLayout.setContentsMargins(16, 16, 16, 16)
        self.sidebar_logo = QLabel(self.sidebar)
        self.sidebar_logo.setObjectName(u"sidebar_logo")
        self.sidebar_logo.setMinimumSize(QSize(80, 80))
        self.sidebar_logo.setMaximumSize(QSize(200, 200))
        self.sidebar_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.sidebarLayout.addWidget(self.sidebar_logo)

        self.frame_main_actions = QFrame(self.sidebar)
        self.frame_main_actions.setObjectName(u"frame_main_actions")
        self.frame_main_actions.setFrameShape(QFrame.Shape.StyledPanel)
        self.layout_main_actions = QVBoxLayout(self.frame_main_actions)
        self.layout_main_actions.setSpacing(8)
        self.layout_main_actions.setObjectName(u"layout_main_actions")
        self.label_main_actions = QLabel(self.frame_main_actions)
        self.label_main_actions.setObjectName(u"label_main_actions")

        self.layout_main_actions.addWidget(self.label_main_actions)

        self.btn_select_folder = QPushButton(self.frame_main_actions)
        self.btn_select_folder.setObjectName(u"btn_select_folder")

        self.layout_main_actions.addWidget(self.btn_select_folder)

        self.btn_select_files = QPushButton(self.frame_main_actions)
        self.btn_select_files.setObjectName(u"btn_select_files")

        self.layout_main_actions.addWidget(self.btn_select_files)

        self.compile_btn = QPushButton(self.frame_main_actions)
        self.compile_btn.setObjectName(u"compile_btn")

        self.layout_main_actions.addWidget(self.compile_btn)

        self.cancel_btn = QPushButton(self.frame_main_actions)
        self.cancel_btn.setObjectName(u"cancel_btn")

        self.layout_main_actions.addWidget(self.cancel_btn)


        self.sidebarLayout.addWidget(self.frame_main_actions)

        self.frame_tools = QFrame(self.sidebar)
        self.frame_tools.setObjectName(u"frame_tools")
        self.frame_tools.setFrameShape(QFrame.Shape.StyledPanel)
        self.layout_tools = QVBoxLayout(self.frame_tools)
        self.layout_tools.setSpacing(8)
        self.layout_tools.setObjectName(u"layout_tools")
        self.label_tools = QLabel(self.frame_tools)
        self.label_tools.setObjectName(u"label_tools")

        self.layout_tools.addWidget(self.label_tools)

        self.btn_suggest_deps = QPushButton(self.frame_tools)
        self.btn_suggest_deps.setObjectName(u"btn_suggest_deps")

        self.layout_tools.addWidget(self.btn_suggest_deps)

        self.btn_bc_loader = QPushButton(self.frame_tools)
        self.btn_bc_loader.setObjectName(u"btn_bc_loader")

        self.layout_tools.addWidget(self.btn_bc_loader)

        self.toolsSpacer = QSpacerItem(20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.layout_tools.addItem(self.toolsSpacer)

        self.btn_show_stats = QPushButton(self.frame_tools)
        self.btn_show_stats.setObjectName(u"btn_show_stats")

        self.layout_tools.addWidget(self.btn_show_stats)

        self.btn_help = QPushButton(self.frame_tools)
        self.btn_help.setObjectName(u"btn_help")

        self.layout_tools.addWidget(self.btn_help)


        self.sidebarLayout.addWidget(self.frame_tools)

        self.frame_settings = QFrame(self.sidebar)
        self.frame_settings.setObjectName(u"frame_settings")
        self.frame_settings.setFrameShape(QFrame.Shape.StyledPanel)
        self.layout_settings = QVBoxLayout(self.frame_settings)
        self.layout_settings.setSpacing(8)
        self.layout_settings.setObjectName(u"layout_settings")
        self.label_settings = QLabel(self.frame_settings)
        self.label_settings.setObjectName(u"label_settings")

        self.layout_settings.addWidget(self.label_settings)

        self.select_lang = QPushButton(self.frame_settings)
        self.select_lang.setObjectName(u"select_lang")

        self.layout_settings.addWidget(self.select_lang)

        self.select_theme = QPushButton(self.frame_settings)
        self.select_theme.setObjectName(u"select_theme")

        self.layout_settings.addWidget(self.select_theme)


        self.sidebarLayout.addWidget(self.frame_settings)

        self.sidebarSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.sidebarLayout.addItem(self.sidebarSpacer)

        self.sidebarScrollArea.setWidget(self.sidebar)

        self.mainLayout.addWidget(self.sidebarScrollArea)

        self.dashboardScrollArea = QScrollArea(PyCompilerARKGui)
        self.dashboardScrollArea.setObjectName(u"dashboardScrollArea")
        self.dashboardScrollArea.setWidgetResizable(True)
        self.contentArea = QWidget()
        self.contentArea.setObjectName(u"contentArea")
        self.contentArea.setGeometry(QRect(0, 0, 940, 700))
        self.contentLayout = QVBoxLayout(self.contentArea)
        self.contentLayout.setSpacing(16)
        self.contentLayout.setObjectName(u"contentLayout")
        self.contentLayout.setContentsMargins(20, 20, 20, 20)
        self.frame_workspace = QFrame(self.contentArea)
        self.frame_workspace.setObjectName(u"frame_workspace")
        self.frame_workspace.setFrameShape(QFrame.Shape.StyledPanel)
        self.layout_workspace = QVBoxLayout(self.frame_workspace)
        self.layout_workspace.setSpacing(12)
        self.layout_workspace.setObjectName(u"layout_workspace")
        self.label_workspace_section = QLabel(self.frame_workspace)
        self.label_workspace_section.setObjectName(u"label_workspace_section")

        self.layout_workspace.addWidget(self.label_workspace_section)

        self.venv_button = QPushButton(self.frame_workspace)
        self.venv_button.setObjectName(u"venv_button")

        self.layout_workspace.addWidget(self.venv_button)

        self.venv_label = QLabel(self.frame_workspace)
        self.venv_label.setObjectName(u"venv_label")

        self.layout_workspace.addWidget(self.venv_label)

        self.label_folder = QLabel(self.frame_workspace)
        self.label_folder.setObjectName(u"label_folder")

        self.layout_workspace.addWidget(self.label_folder)


        self.contentLayout.addWidget(self.frame_workspace)

        self.frame_files = QFrame(self.contentArea)
        self.frame_files.setObjectName(u"frame_files")
        self.frame_files.setFrameShape(QFrame.Shape.StyledPanel)
        self.layout_files = QVBoxLayout(self.frame_files)
        self.layout_files.setSpacing(12)
        self.layout_files.setObjectName(u"layout_files")
        self.label_files_section = QLabel(self.frame_files)
        self.label_files_section.setObjectName(u"label_files_section")

        self.layout_files.addWidget(self.label_files_section)

        self.file_list = QListWidget(self.frame_files)
        self.file_list.setObjectName(u"file_list")
        self.file_list.setMinimumHeight(150)

        self.layout_files.addWidget(self.file_list)

        self.btn_remove_file = QPushButton(self.frame_files)
        self.btn_remove_file.setObjectName(u"btn_remove_file")

        self.layout_files.addWidget(self.btn_remove_file)


        self.contentLayout.addWidget(self.frame_files)

        self.frame_options = QFrame(self.contentArea)
        self.frame_options.setObjectName(u"frame_options")
        self.frame_options.setFrameShape(QFrame.Shape.StyledPanel)
        self.layout_options = QVBoxLayout(self.frame_options)
        self.layout_options.setSpacing(12)
        self.layout_options.setObjectName(u"layout_options")
        self.label_options_section = QLabel(self.frame_options)
        self.label_options_section.setObjectName(u"label_options_section")

        self.layout_options.addWidget(self.label_options_section)

        self.compiler_tabs = QTabWidget(self.frame_options)
        self.compiler_tabs.setObjectName(u"compiler_tabs")

        self.layout_options.addWidget(self.compiler_tabs)


        self.contentLayout.addWidget(self.frame_options)

        self.frame_logs = QFrame(self.contentArea)
        self.frame_logs.setObjectName(u"frame_logs")
        self.frame_logs.setFrameShape(QFrame.Shape.StyledPanel)
        self.layout_logs = QVBoxLayout(self.frame_logs)
        self.layout_logs.setSpacing(12)
        self.layout_logs.setObjectName(u"layout_logs")
        self.label_logs_section = QLabel(self.frame_logs)
        self.label_logs_section.setObjectName(u"label_logs_section")

        self.layout_logs.addWidget(self.label_logs_section)

        self.log = QTextEdit(self.frame_logs)
        self.log.setObjectName(u"log")
        self.log.setMinimumHeight(200)

        self.layout_logs.addWidget(self.log)


        self.contentLayout.addWidget(self.frame_logs)

        self.frame_progress = QFrame(self.contentArea)
        self.frame_progress.setObjectName(u"frame_progress")
        self.frame_progress.setFrameShape(QFrame.Shape.StyledPanel)
        self.layout_progress = QVBoxLayout(self.frame_progress)
        self.layout_progress.setSpacing(8)
        self.layout_progress.setObjectName(u"layout_progress")
        self.label_progress = QLabel(self.frame_progress)
        self.label_progress.setObjectName(u"label_progress")

        self.layout_progress.addWidget(self.label_progress)

        self.progress = QProgressBar(self.frame_progress)
        self.progress.setObjectName(u"progress")
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        self.progress.setMinimumHeight(24)

        self.layout_progress.addWidget(self.progress)


        self.contentLayout.addWidget(self.frame_progress)

        self.dashboardScrollArea.setWidget(self.contentArea)

        self.mainLayout.addWidget(self.dashboardScrollArea)


        self.retranslateUi(PyCompilerARKGui)

        self.compiler_tabs.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(PyCompilerARKGui)
    # setupUi

    def retranslateUi(self, PyCompilerARKGui):
        self.label_main_actions.setText(QCoreApplication.translate("PyCompilerARKGui", u"Actions principales", None))
        self.btn_select_folder.setText(QCoreApplication.translate("PyCompilerARKGui", u"\ud83d\udcc1 Workspace", None))
#if QT_CONFIG(tooltip)
        self.btn_select_folder.setToolTip(QCoreApplication.translate("PyCompilerARKGui", u"S\u00e9lectionner le dossier de travail", None))
#endif // QT_CONFIG(tooltip)
        self.btn_select_files.setText(QCoreApplication.translate("PyCompilerARKGui", u"\ud83d\udccb Fichiers", None))
#if QT_CONFIG(tooltip)
        self.btn_select_files.setToolTip(QCoreApplication.translate("PyCompilerARKGui", u"Ajouter des fichiers \u00e0 compiler", None))
#endif // QT_CONFIG(tooltip)
        self.compile_btn.setText(QCoreApplication.translate("PyCompilerARKGui", u"\ud83d\ude80 Compiler", None))
#if QT_CONFIG(tooltip)
        self.compile_btn.setToolTip(QCoreApplication.translate("PyCompilerARKGui", u"Lancer la compilation", None))
#endif // QT_CONFIG(tooltip)
        self.cancel_btn.setText(QCoreApplication.translate("PyCompilerARKGui", u"\u26d4 Annuler", None))
#if QT_CONFIG(tooltip)
        self.cancel_btn.setToolTip(QCoreApplication.translate("PyCompilerARKGui", u"Annuler la compilation en cours", None))
#endif // QT_CONFIG(tooltip)
        self.label_tools.setText(QCoreApplication.translate("PyCompilerARKGui", u"Outils", None))
        self.btn_suggest_deps.setText(QCoreApplication.translate("PyCompilerARKGui", u"\ud83d\udd0e D\u00e9pendances", None))
#if QT_CONFIG(tooltip)
        self.btn_suggest_deps.setToolTip(QCoreApplication.translate("PyCompilerARKGui", u"Analyser les d\u00e9pendances du projet", None))
#endif // QT_CONFIG(tooltip)
        self.btn_bc_loader.setText(QCoreApplication.translate("PyCompilerARKGui", u"\ud83e\udde9 Bc Plugins Loader", None))
#if QT_CONFIG(tooltip)
        self.btn_bc_loader.setToolTip(QCoreApplication.translate("PyCompilerARKGui", u"Charger Bc Plugins Loader", None))
#endif // QT_CONFIG(tooltip)
        self.btn_show_stats.setText(QCoreApplication.translate("PyCompilerARKGui", u"\ud83d\udcca Statistiques", None))
#if QT_CONFIG(tooltip)
        self.btn_show_stats.setToolTip(QCoreApplication.translate("PyCompilerARKGui", u"Afficher les statistiques de compilation", None))
#endif // QT_CONFIG(tooltip)
        self.btn_help.setText(QCoreApplication.translate("PyCompilerARKGui", u"\u2753 Aide", None))
#if QT_CONFIG(tooltip)
        self.btn_help.setToolTip(QCoreApplication.translate("PyCompilerARKGui", u"Afficher l'aide", None))
#endif // QT_CONFIG(tooltip)
        self.label_settings.setText(QCoreApplication.translate("PyCompilerARKGui", u"Param\u00e8tres", None))
        self.select_lang.setText(QCoreApplication.translate("PyCompilerARKGui", u"\ud83c\udf10 Langue", None))
#if QT_CONFIG(tooltip)
        self.select_lang.setToolTip(QCoreApplication.translate("PyCompilerARKGui", u"Choisir la langue de l'interface", None))
#endif // QT_CONFIG(tooltip)
        self.select_theme.setText(QCoreApplication.translate("PyCompilerARKGui", u"\ud83c\udfa8 Th\u00e8me", None))
#if QT_CONFIG(tooltip)
        self.select_theme.setToolTip(QCoreApplication.translate("PyCompilerARKGui", u"Choisir le th\u00e8me de l'interface", None))
#endif // QT_CONFIG(tooltip)
        self.label_workspace_section.setText(QCoreApplication.translate("PyCompilerARKGui", u"1. S\u00e9lection du dossier de travail", None))
        self.venv_button.setText(QCoreApplication.translate("PyCompilerARKGui", u"Choisir un dossier venv manuellement", None))
        self.venv_label.setText(QCoreApplication.translate("PyCompilerARKGui", u"venv s\u00e9lectionn\u00e9 : Aucun", None))
        self.label_folder.setText(QCoreApplication.translate("PyCompilerARKGui", u"Aucun dossier s\u00e9lectionn\u00e9", None))
        self.label_files_section.setText(QCoreApplication.translate("PyCompilerARKGui", u"2. Fichiers \u00e0 compiler", None))
        self.btn_remove_file.setText(QCoreApplication.translate("PyCompilerARKGui", u"\ud83d\uddd1\ufe0f Supprimer le fichier s\u00e9lectionn\u00e9", None))
        self.label_options_section.setText(QCoreApplication.translate("PyCompilerARKGui", u"3. Options de compilation", None))
        self.label_logs_section.setText(QCoreApplication.translate("PyCompilerARKGui", u"4. Logs de compilation", None))
        self.label_progress.setText(QCoreApplication.translate("PyCompilerARKGui", u"Progression", None))
        pass
    # retranslateUi

