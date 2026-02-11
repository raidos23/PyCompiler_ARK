# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'ui_design.ui'
##
## Created by: Qt User Interface Compiler version 6.10.1
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
from PySide6.QtWidgets import (QApplication, QFrame, QGridLayout, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QProgressBar, QPushButton, QSizePolicy, QSpacerItem,
    QSplitter, QTabWidget, QTextEdit, QVBoxLayout,
    QWidget)

class Ui_PyCompilerARKGui(object):
    def setupUi(self, PyCompilerARKGui):
        if not PyCompilerARKGui.objectName():
            PyCompilerARKGui.setObjectName(u"PyCompilerARKGui")
        PyCompilerARKGui.resize(1280, 720)
        self.rootLayout = QVBoxLayout(PyCompilerARKGui)
        self.rootLayout.setSpacing(10)
        self.rootLayout.setObjectName(u"rootLayout")
        self.rootLayout.setContentsMargins(12, 12, 12, 12)
        self.header = QFrame(PyCompilerARKGui)
        self.header.setObjectName(u"header")
        self.header.setMinimumHeight(56)
        self.header.setFrameShape(QFrame.Shape.StyledPanel)
        self.headerLayout = QHBoxLayout(self.header)
        self.headerLayout.setSpacing(10)
        self.headerLayout.setObjectName(u"headerLayout")
        self.headerLayout.setContentsMargins(10, 10, 10, 10)
        self.header_left = QWidget(self.header)
        self.header_left.setObjectName(u"header_left")
        self.headerLeftLayout = QVBoxLayout(self.header_left)
        self.headerLeftLayout.setSpacing(2)
        self.headerLeftLayout.setObjectName(u"headerLeftLayout")
        self.headerLeftLayout.setContentsMargins(0, 0, 0, 0)
        self.label_app_title = QLabel(self.header_left)
        self.label_app_title.setObjectName(u"label_app_title")
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        self.label_app_title.setFont(font)

        self.headerLeftLayout.addWidget(self.label_app_title)

        self.label_workspace_status = QLabel(self.header_left)
        self.label_workspace_status.setObjectName(u"label_workspace_status")

        self.headerLeftLayout.addWidget(self.label_workspace_status)


        self.headerLayout.addWidget(self.header_left)

        self.headerSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.headerLayout.addItem(self.headerSpacer)

        self.header_right = QWidget(self.header)
        self.header_right.setObjectName(u"header_right")
        self.headerRightLayout = QHBoxLayout(self.header_right)
        self.headerRightLayout.setSpacing(8)
        self.headerRightLayout.setObjectName(u"headerRightLayout")
        self.headerRightLayout.setContentsMargins(0, 0, 0, 0)
        self.select_lang = QPushButton(self.header_right)
        self.select_lang.setObjectName(u"select_lang")

        self.headerRightLayout.addWidget(self.select_lang)

        self.select_theme = QPushButton(self.header_right)
        self.select_theme.setObjectName(u"select_theme")

        self.headerRightLayout.addWidget(self.select_theme)

        self.compile_btn = QPushButton(self.header_right)
        self.compile_btn.setObjectName(u"compile_btn")

        self.headerRightLayout.addWidget(self.compile_btn)

        self.cancel_btn = QPushButton(self.header_right)
        self.cancel_btn.setObjectName(u"cancel_btn")

        self.headerRightLayout.addWidget(self.cancel_btn)


        self.headerLayout.addWidget(self.header_right)


        self.rootLayout.addWidget(self.header)

        self.mainSplitter = QSplitter(PyCompilerARKGui)
        self.mainSplitter.setObjectName(u"mainSplitter")
        self.mainSplitter.setOrientation(Qt.Orientation.Horizontal)
        self.leftPanel = QWidget(self.mainSplitter)
        self.leftPanel.setObjectName(u"leftPanel")
        self.leftPanel.setMinimumWidth(280)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.leftPanel.sizePolicy().hasHeightForWidth())
        self.leftPanel.setSizePolicy(sizePolicy)
        self.leftLayout = QVBoxLayout(self.leftPanel)
        self.leftLayout.setSpacing(12)
        self.leftLayout.setObjectName(u"leftLayout")
        self.leftLayout.setContentsMargins(6, 6, 6, 6)
        self.frame_workspace = QFrame(self.leftPanel)
        self.frame_workspace.setObjectName(u"frame_workspace")
        self.frame_workspace.setFrameShape(QFrame.Shape.StyledPanel)
        self.layout_workspace_grid = QGridLayout(self.frame_workspace)
        self.layout_workspace_grid.setSpacing(12)
        self.layout_workspace_grid.setObjectName(u"layout_workspace_grid")
        self.layout_workspace_grid.setContentsMargins(10, 10, 10, 10)
        self.label_folder = QLabel(self.frame_workspace)
        self.label_folder.setObjectName(u"label_folder")

        self.layout_workspace_grid.addWidget(self.label_folder, 0, 0, 1, 2)

        self.venv_label = QLabel(self.frame_workspace)
        self.venv_label.setObjectName(u"venv_label")

        self.layout_workspace_grid.addWidget(self.venv_label, 1, 0, 1, 1)

        self.venv_button = QPushButton(self.frame_workspace)
        self.venv_button.setObjectName(u"venv_button")

        self.layout_workspace_grid.addWidget(self.venv_button, 1, 1, 1, 1)

        self.btn_select_folder = QPushButton(self.frame_workspace)
        self.btn_select_folder.setObjectName(u"btn_select_folder")

        self.layout_workspace_grid.addWidget(self.btn_select_folder, 2, 0, 1, 1)

        self.btn_clear_workspace = QPushButton(self.frame_workspace)
        self.btn_clear_workspace.setObjectName(u"btn_clear_workspace")

        self.layout_workspace_grid.addWidget(self.btn_clear_workspace, 2, 1, 1, 1)


        self.leftLayout.addWidget(self.frame_workspace)

        self.frame_files = QFrame(self.leftPanel)
        self.frame_files.setObjectName(u"frame_files")
        self.frame_files.setFrameShape(QFrame.Shape.StyledPanel)
        self.layout_files_grid = QGridLayout(self.frame_files)
        self.layout_files_grid.setSpacing(12)
        self.layout_files_grid.setObjectName(u"layout_files_grid")
        self.layout_files_grid.setContentsMargins(10, 10, 10, 10)
        self.label_files_section = QLabel(self.frame_files)
        self.label_files_section.setObjectName(u"label_files_section")
        font1 = QFont()
        font1.setPointSize(12)
        font1.setBold(False)
        self.label_files_section.setFont(font1)
        self.label_files_section.setWordWrap(True)

        self.layout_files_grid.addWidget(self.label_files_section, 0, 0, 1, 2)

        self.file_filter_input = QLineEdit(self.frame_files)
        self.file_filter_input.setObjectName(u"file_filter_input")

        self.layout_files_grid.addWidget(self.file_filter_input, 1, 0, 1, 2)

        self.file_list = QListWidget(self.frame_files)
        self.file_list.setObjectName(u"file_list")
        self.file_list.setMinimumHeight(140)
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(1)
        sizePolicy1.setHeightForWidth(self.file_list.sizePolicy().hasHeightForWidth())
        self.file_list.setSizePolicy(sizePolicy1)

        self.layout_files_grid.addWidget(self.file_list, 2, 0, 1, 1)

        self.layout_file_actions = QVBoxLayout()
        self.layout_file_actions.setSpacing(8)
        self.layout_file_actions.setObjectName(u"layout_file_actions")
        self.layout_file_actions.setContentsMargins(0, 0, 0, 0)
        self.btn_select_files = QPushButton(self.frame_files)
        self.btn_select_files.setObjectName(u"btn_select_files")

        self.layout_file_actions.addWidget(self.btn_select_files)

        self.btn_remove_file = QPushButton(self.frame_files)
        self.btn_remove_file.setObjectName(u"btn_remove_file")

        self.layout_file_actions.addWidget(self.btn_remove_file)

        self.fileActionsSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.layout_file_actions.addItem(self.fileActionsSpacer)


        self.layout_files_grid.addLayout(self.layout_file_actions, 2, 1, 1, 1)


        self.leftLayout.addWidget(self.frame_files)

        self.frame_tools = QFrame(self.leftPanel)
        self.frame_tools.setObjectName(u"frame_tools")
        self.frame_tools.setFrameShape(QFrame.Shape.StyledPanel)
        self.layout_tools_grid = QGridLayout(self.frame_tools)
        self.layout_tools_grid.setSpacing(10)
        self.layout_tools_grid.setObjectName(u"layout_tools_grid")
        self.layout_tools_grid.setContentsMargins(10, 10, 10, 10)
        self.label_tools = QLabel(self.frame_tools)
        self.label_tools.setObjectName(u"label_tools")

        self.layout_tools_grid.addWidget(self.label_tools, 0, 0, 1, 2)

        self.btn_suggest_deps = QPushButton(self.frame_tools)
        self.btn_suggest_deps.setObjectName(u"btn_suggest_deps")

        self.layout_tools_grid.addWidget(self.btn_suggest_deps, 1, 0, 1, 1)

        self.btn_bc_loader = QPushButton(self.frame_tools)
        self.btn_bc_loader.setObjectName(u"btn_bc_loader")

        self.layout_tools_grid.addWidget(self.btn_bc_loader, 1, 1, 1, 1)

        self.btn_show_stats = QPushButton(self.frame_tools)
        self.btn_show_stats.setObjectName(u"btn_show_stats")

        self.layout_tools_grid.addWidget(self.btn_show_stats, 2, 0, 1, 1)

        self.btn_help = QPushButton(self.frame_tools)
        self.btn_help.setObjectName(u"btn_help")

        self.layout_tools_grid.addWidget(self.btn_help, 2, 1, 1, 1)


        self.leftLayout.addWidget(self.frame_tools)

        self.leftSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.leftLayout.addItem(self.leftSpacer)

        self.mainSplitter.addWidget(self.leftPanel)
        self.rightPanel = QWidget(self.mainSplitter)
        self.rightPanel.setObjectName(u"rightPanel")
        self.rightPanel.setMinimumWidth(420)
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy2.setHorizontalStretch(1)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.rightPanel.sizePolicy().hasHeightForWidth())
        self.rightPanel.setSizePolicy(sizePolicy2)
        self.rightLayout = QVBoxLayout(self.rightPanel)
        self.rightLayout.setSpacing(16)
        self.rightLayout.setObjectName(u"rightLayout")
        self.rightLayout.setContentsMargins(6, 6, 6, 6)
        self.frame_options = QFrame(self.rightPanel)
        self.frame_options.setObjectName(u"frame_options")
        self.frame_options.setFrameShape(QFrame.Shape.StyledPanel)
        self.layout_options = QVBoxLayout(self.frame_options)
        self.layout_options.setSpacing(12)
        self.layout_options.setObjectName(u"layout_options")
        self.layout_options.setContentsMargins(10, 10, 10, 10)
        self.label_options_section = QLabel(self.frame_options)
        self.label_options_section.setObjectName(u"label_options_section")

        self.layout_options.addWidget(self.label_options_section)

        self.compiler_tabs = QTabWidget(self.frame_options)
        self.compiler_tabs.setObjectName(u"compiler_tabs")

        self.layout_options.addWidget(self.compiler_tabs)


        self.rightLayout.addWidget(self.frame_options)

        self.frame_logs = QFrame(self.rightPanel)
        self.frame_logs.setObjectName(u"frame_logs")
        self.frame_logs.setFrameShape(QFrame.Shape.StyledPanel)
        self.layout_logs = QVBoxLayout(self.frame_logs)
        self.layout_logs.setSpacing(12)
        self.layout_logs.setObjectName(u"layout_logs")
        self.layout_logs.setContentsMargins(10, 10, 10, 10)
        self.label_logs_section = QLabel(self.frame_logs)
        self.label_logs_section.setObjectName(u"label_logs_section")

        self.layout_logs.addWidget(self.label_logs_section)

        self.log = QTextEdit(self.frame_logs)
        self.log.setObjectName(u"log")
        self.log.setMinimumHeight(160)
        sizePolicy1.setHeightForWidth(self.log.sizePolicy().hasHeightForWidth())
        self.log.setSizePolicy(sizePolicy1)

        self.layout_logs.addWidget(self.log)


        self.rightLayout.addWidget(self.frame_logs)

        self.frame_progress = QFrame(self.rightPanel)
        self.frame_progress.setObjectName(u"frame_progress")
        self.frame_progress.setFrameShape(QFrame.Shape.StyledPanel)
        self.layout_progress = QVBoxLayout(self.frame_progress)
        self.layout_progress.setSpacing(8)
        self.layout_progress.setObjectName(u"layout_progress")
        self.layout_progress.setContentsMargins(10, 10, 10, 10)
        self.label_progress = QLabel(self.frame_progress)
        self.label_progress.setObjectName(u"label_progress")

        self.layout_progress.addWidget(self.label_progress)

        self.progress = QProgressBar(self.frame_progress)
        self.progress.setObjectName(u"progress")
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        self.progress.setMinimumHeight(18)

        self.layout_progress.addWidget(self.progress)


        self.rightLayout.addWidget(self.frame_progress)

        self.mainSplitter.addWidget(self.rightPanel)

        self.rootLayout.addWidget(self.mainSplitter)


        self.retranslateUi(PyCompilerARKGui)

        self.compiler_tabs.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(PyCompilerARKGui)
    # setupUi

    def retranslateUi(self, PyCompilerARKGui):
        self.label_app_title.setText(QCoreApplication.translate("PyCompilerARKGui", u"PyCompiler ARK++", None))
        self.label_workspace_status.setText(QCoreApplication.translate("PyCompilerARKGui", u"Workspace : Aucun", None))
        self.select_lang.setText(QCoreApplication.translate("PyCompilerARKGui", u"\U0001f310 Langue", None))
#if QT_CONFIG(tooltip)
        self.select_lang.setToolTip(QCoreApplication.translate("PyCompilerARKGui", u"Choisir la langue de l'interface", None))
#endif // QT_CONFIG(tooltip)
        self.select_theme.setText(QCoreApplication.translate("PyCompilerARKGui", u"\U0001f3a8 Th\U000000e8me", None))
#if QT_CONFIG(tooltip)
        self.select_theme.setToolTip(QCoreApplication.translate("PyCompilerARKGui", u"Choisir le th\u00e8me de l'interface", None))
#endif // QT_CONFIG(tooltip)
        self.compile_btn.setText(QCoreApplication.translate("PyCompilerARKGui", u"\U0001f680 Compiler", None))
#if QT_CONFIG(tooltip)
        self.compile_btn.setToolTip(QCoreApplication.translate("PyCompilerARKGui", u"Lancer la compilation", None))
#endif // QT_CONFIG(tooltip)
        self.cancel_btn.setText(QCoreApplication.translate("PyCompilerARKGui", u"\u26d4 Annuler", None))
#if QT_CONFIG(tooltip)
        self.cancel_btn.setToolTip(QCoreApplication.translate("PyCompilerARKGui", u"Annuler la compilation en cours", None))
#endif // QT_CONFIG(tooltip)
        self.label_folder.setText(QCoreApplication.translate("PyCompilerARKGui", u"Aucun dossier s\u00e9lectionn\u00e9", None))
        self.venv_label.setText(QCoreApplication.translate("PyCompilerARKGui", u"venv s\u00e9lectionn\u00e9 : Aucun", None))
        self.venv_button.setText(QCoreApplication.translate("PyCompilerARKGui", u"Choisir un dossier venv manuellement", None))
        self.btn_select_folder.setText(QCoreApplication.translate("PyCompilerARKGui", u"\U0001f4c1 Workspace", None))
#if QT_CONFIG(tooltip)
        self.btn_select_folder.setToolTip(QCoreApplication.translate("PyCompilerARKGui", u"S\u00e9lectionner le dossier de travail", None))
#endif // QT_CONFIG(tooltip)
        self.btn_clear_workspace.setText(QCoreApplication.translate("PyCompilerARKGui", u"\U0001f9f9 Clear workspace", None))
#if QT_CONFIG(tooltip)
        self.btn_clear_workspace.setToolTip(QCoreApplication.translate("PyCompilerARKGui", u"Vider la liste des fichiers et r\u00e9initialiser la s\u00e9lection", None))
#endif // QT_CONFIG(tooltip)
        self.label_files_section.setText(QCoreApplication.translate("PyCompilerARKGui", u"2. Fichiers \u00e0 compiler", None))
        self.file_filter_input.setPlaceholderText(QCoreApplication.translate("PyCompilerARKGui", u"Filtrer la liste\u2026", None))
        self.btn_select_files.setText(QCoreApplication.translate("PyCompilerARKGui", u"\U0001f4cb Fichiers", None))
#if QT_CONFIG(tooltip)
        self.btn_select_files.setToolTip(QCoreApplication.translate("PyCompilerARKGui", u"Ajouter des fichiers \u00e0 compiler", None))
#endif // QT_CONFIG(tooltip)
        self.btn_remove_file.setText(QCoreApplication.translate("PyCompilerARKGui", u"\U0001f5d1\U0000fe0f Supprimer le fichier s\U000000e9lectionn\U000000e9", None))
        self.label_tools.setText(QCoreApplication.translate("PyCompilerARKGui", u"Outils", None))
        self.btn_suggest_deps.setText(QCoreApplication.translate("PyCompilerARKGui", u"\U0001f50e D\U000000e9pendances", None))
#if QT_CONFIG(tooltip)
        self.btn_suggest_deps.setToolTip(QCoreApplication.translate("PyCompilerARKGui", u"Analyser les d\u00e9pendances du projet", None))
#endif // QT_CONFIG(tooltip)
        self.btn_bc_loader.setText(QCoreApplication.translate("PyCompilerARKGui", u"\U0001f9e9 Bc Plugins Loader", None))
#if QT_CONFIG(tooltip)
        self.btn_bc_loader.setToolTip(QCoreApplication.translate("PyCompilerARKGui", u"Charger Bc Plugins Loader", None))
#endif // QT_CONFIG(tooltip)
        self.btn_show_stats.setText(QCoreApplication.translate("PyCompilerARKGui", u"\U0001f4ca Statistiques", None))
#if QT_CONFIG(tooltip)
        self.btn_show_stats.setToolTip(QCoreApplication.translate("PyCompilerARKGui", u"Afficher les statistiques de compilation", None))
#endif // QT_CONFIG(tooltip)
        self.btn_help.setText(QCoreApplication.translate("PyCompilerARKGui", u"\u2753 Aide", None))
#if QT_CONFIG(tooltip)
        self.btn_help.setToolTip(QCoreApplication.translate("PyCompilerARKGui", u"Afficher l'aide", None))
#endif // QT_CONFIG(tooltip)
        self.label_options_section.setText(QCoreApplication.translate("PyCompilerARKGui", u"3. Options de compilation", None))
        self.label_logs_section.setText(QCoreApplication.translate("PyCompilerARKGui", u"4. Logs de compilation", None))
        self.label_progress.setText(QCoreApplication.translate("PyCompilerARKGui", u"Progression", None))
        pass
    # retranslateUi

