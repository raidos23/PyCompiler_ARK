# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main_window.ui'
##
## Created by: Qt User Interface Compiler version 6.7.3
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (
    QCoreApplication,
    QDate,
    QDateTime,
    QLocale,
    QMetaObject,
    QObject,
    QPoint,
    QRect,
    QSize,
    QTime,
    QUrl,
    Qt,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QConicalGradient,
    QCursor,
    QFont,
    QFontDatabase,
    QGradient,
    QIcon,
    QImage,
    QKeySequence,
    QLinearGradient,
    QPainter,
    QPalette,
    QPixmap,
    QRadialGradient,
    QTransform,
)
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1365, 768)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.centralwidget.setStyleSheet(
            "QWidget {\n"
            "  background: #1e1e1e;\n"
            "  color: #d4d4d4;\n"
            '  font-family: "Segoe UI", "Noto Sans", sans-serif;\n'
            "  font-size: 9pt;\n"
            "}\n"
            "QFrame#header, QFrame#activity_bar, QFrame#workspace_panel, QFrame#tools_panel, QFrame#logs_panel {\n"
            "  background: #252526;\n"
            "  border: 1px solid #3c3c3c;\n"
            "}\n"
            "QTabWidget::pane, QListWidget, QTextEdit, QLineEdit {\n"
            "  background: #1e1e1e;\n"
            "  border: 1px solid #3c3c3c;\n"
            "}\n"
            "QLabel#label_app_title { color: #ffffff; font-size: 10pt; font-weight: 600; }\n"
            "QLabel#label_workspace_section, QLabel#label_files_section, QLabel#label_tools,\n"
            "QLabel#label_logs_section, QLabel#label_progress, QLabel#label_options_section {\n"
            "  color: #c8c8c8;\n"
            "  font-weight: 600;\n"
            "}\n"
            "QPushButton {\n"
            "  background: #3c3c3c;\n"
            "  border: 1px solid #3c3c3c;\n"
            "  border-radius: 2px;\n"
            "  padding: 4px 10px;\n"
            "}\n"
            "QPushButton:hover { background: #454545; }\n"
            "QPushButton#btn_build_all {\n"
            "  background: #0e639c;\n"
            "  border-color: #0e639c;\n"
            "  color"
            ": #ffffff;\n"
            "  font-weight: 600;\n"
            "}\n"
            "QPushButton#btn_build_all:hover { background: #1177bb; }\n"
            "QPushButton#btn_cancel_all {\n"
            "  background: #5a1d1d;\n"
            "  border-color: #6a2a2a;\n"
            "  color: #f2b8b8;\n"
            "}\n"
            "QListWidget { padding: 4px; selection-background-color: #094771; selection-color: #ffffff; }\n"
            "QTabBar::tab {\n"
            "  background: #2d2d30;\n"
            "  border: 1px solid #3c3c3c;\n"
            "  border-bottom: none;\n"
            "  padding: 5px 12px;\n"
            "}\n"
            "QTabBar::tab:selected { background: #1e1e1e; }\n"
            "QTabBar::tab:hover { background: #37373d; }\n"
            "QProgressBar {\n"
            "  border: 1px solid #3c3c3c;\n"
            "  text-align: center;\n"
            "  background: #1e1e1e;\n"
            "}\n"
            "QProgressBar::chunk { background: #0e639c; }"
        )
        self.rootLayout = QVBoxLayout(self.centralwidget)
        self.rootLayout.setSpacing(0)
        self.rootLayout.setObjectName("rootLayout")
        self.rootLayout.setContentsMargins(0, 0, 0, 0)
        self.header = QFrame(self.centralwidget)
        self.header.setObjectName("header")
        self.header.setMinimumSize(QSize(0, 48))
        self.header.setMaximumSize(QSize(16777215, 56))
        self.header.setFrameShape(QFrame.Shape.StyledPanel)
        self.header.setFrameShadow(QFrame.Shadow.Raised)
        self.headerLayout = QHBoxLayout(self.header)
        self.headerLayout.setSpacing(8)
        self.headerLayout.setObjectName("headerLayout")
        self.headerLayout.setContentsMargins(10, 4, 10, 4)
        self.label_app_title = QLabel(self.header)
        self.label_app_title.setObjectName("label_app_title")

        self.headerLayout.addWidget(self.label_app_title)

        self.headerSpacer = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )

        self.headerLayout.addItem(self.headerSpacer)

        self.btn_build_all = QPushButton(self.header)
        self.btn_build_all.setObjectName("btn_build_all")
        self.btn_build_all.setMinimumSize(QSize(124, 34))

        self.headerLayout.addWidget(self.btn_build_all)

        self.btn_cancel_all = QPushButton(self.header)
        self.btn_cancel_all.setObjectName("btn_cancel_all")
        self.btn_cancel_all.setMinimumSize(QSize(124, 34))

        self.headerLayout.addWidget(self.btn_cancel_all)

        self.rootLayout.addWidget(self.header)

        self.mainSplitter = QSplitter(self.centralwidget)
        self.mainSplitter.setObjectName("mainSplitter")
        self.mainSplitter.setOrientation(Qt.Orientation.Horizontal)
        self.mainSplitter.setHandleWidth(1)
        self.activity_bar = QFrame(self.mainSplitter)
        self.activity_bar.setObjectName("activity_bar")
        self.activity_bar.setMinimumSize(QSize(48, 0))
        self.activity_bar.setMaximumSize(QSize(56, 16777215))
        self.activity_bar.setFrameShape(QFrame.Shape.StyledPanel)
        self.activity_bar.setFrameShadow(QFrame.Shadow.Raised)
        self.activityBarLayout = QVBoxLayout(self.activity_bar)
        self.activityBarLayout.setSpacing(8)
        self.activityBarLayout.setObjectName("activityBarLayout")
        self.activityBarLayout.setContentsMargins(6, 8, 6, 8)
        self.btn_more_actions = QToolButton(self.activity_bar)
        self.btn_more_actions.setObjectName("btn_more_actions")
        self.btn_more_actions.setMinimumSize(QSize(28, 28))

        self.activityBarLayout.addWidget(self.btn_more_actions)

        self.btn_activity_deps = QToolButton(self.activity_bar)
        self.btn_activity_deps.setObjectName("btn_activity_deps")
        self.btn_activity_deps.setMinimumSize(QSize(28, 28))

        self.activityBarLayout.addWidget(self.btn_activity_deps)

        self.activitySpacer = QSpacerItem(
            20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
        )

        self.activityBarLayout.addItem(self.activitySpacer)

        self.mainSplitter.addWidget(self.activity_bar)
        self.workspace_panel = QFrame(self.mainSplitter)
        self.workspace_panel.setObjectName("workspace_panel")
        self.workspace_panel.setMinimumSize(QSize(280, 0))
        self.workspace_panel.setMaximumSize(QSize(400, 16777215))
        self.workspace_panel.setFrameShape(QFrame.Shape.StyledPanel)
        self.workspace_panel.setFrameShadow(QFrame.Shadow.Raised)
        self.workspaceLayout = QVBoxLayout(self.workspace_panel)
        self.workspaceLayout.setSpacing(8)
        self.workspaceLayout.setObjectName("workspaceLayout")
        self.workspaceLayout.setContentsMargins(8, 8, 8, 8)
        self.label_workspace_section = QLabel(self.workspace_panel)
        self.label_workspace_section.setObjectName("label_workspace_section")

        self.workspaceLayout.addWidget(self.label_workspace_section)

        self.workspaceSelectLayout = QHBoxLayout()
        self.workspaceSelectLayout.setObjectName("workspaceSelectLayout")
        self.btn_select_folder = QPushButton(self.workspace_panel)
        self.btn_select_folder.setObjectName("btn_select_folder")

        self.workspaceSelectLayout.addWidget(self.btn_select_folder)

        self.btn_venv_button = QPushButton(self.workspace_panel)
        self.btn_venv_button.setObjectName("btn_venv_button")

        self.workspaceSelectLayout.addWidget(self.btn_venv_button)

        self.workspaceLayout.addLayout(self.workspaceSelectLayout)

        self.label_folder = QLabel(self.workspace_panel)
        self.label_folder.setObjectName("label_folder")

        self.workspaceLayout.addWidget(self.label_folder)

        self.label_workspace_status = QLabel(self.workspace_panel)
        self.label_workspace_status.setObjectName("label_workspace_status")

        self.workspaceLayout.addWidget(self.label_workspace_status)

        self.venv_label = QLabel(self.workspace_panel)
        self.venv_label.setObjectName("venv_label")

        self.workspaceLayout.addWidget(self.venv_label)

        self.label_files_section = QLabel(self.workspace_panel)
        self.label_files_section.setObjectName("label_files_section")

        self.workspaceLayout.addWidget(self.label_files_section)

        self.file_filter_input = QLineEdit(self.workspace_panel)
        self.file_filter_input.setObjectName("file_filter_input")

        self.workspaceLayout.addWidget(self.file_filter_input)

        self.fileButtonsLayout = QHBoxLayout()
        self.fileButtonsLayout.setObjectName("fileButtonsLayout")
        self.btn_select_files = QPushButton(self.workspace_panel)
        self.btn_select_files.setObjectName("btn_select_files")

        self.fileButtonsLayout.addWidget(self.btn_select_files)

        self.btn_remove_file = QPushButton(self.workspace_panel)
        self.btn_remove_file.setObjectName("btn_remove_file")

        self.fileButtonsLayout.addWidget(self.btn_remove_file)

        self.btn_clear_workspace = QPushButton(self.workspace_panel)
        self.btn_clear_workspace.setObjectName("btn_clear_workspace")

        self.fileButtonsLayout.addWidget(self.btn_clear_workspace)

        self.workspaceLayout.addLayout(self.fileButtonsLayout)

        self.file_list = QListWidget(self.workspace_panel)
        self.file_list.setObjectName("file_list")

        self.workspaceLayout.addWidget(self.file_list)

        self.mainSplitter.addWidget(self.workspace_panel)
        self.rightSplitter = QSplitter(self.mainSplitter)
        self.rightSplitter.setObjectName("rightSplitter")
        self.rightSplitter.setOrientation(Qt.Orientation.Vertical)
        self.rightSplitter.setHandleWidth(1)
        self.topSplitter = QSplitter(self.rightSplitter)
        self.topSplitter.setObjectName("topSplitter")
        self.topSplitter.setOrientation(Qt.Orientation.Horizontal)
        self.topSplitter.setHandleWidth(1)
        self.compiler_tabs = QTabWidget(self.topSplitter)
        self.compiler_tabs.setObjectName("compiler_tabs")
        self.topSplitter.addWidget(self.compiler_tabs)
        self.tools_panel = QFrame(self.topSplitter)
        self.tools_panel.setObjectName("tools_panel")
        self.tools_panel.setMinimumSize(QSize(200, 0))
        self.tools_panel.setMaximumSize(QSize(280, 16777215))
        self.tools_panel.setFrameShape(QFrame.Shape.StyledPanel)
        self.tools_panel.setFrameShadow(QFrame.Shadow.Raised)
        self.toolsLayout = QVBoxLayout(self.tools_panel)
        self.toolsLayout.setSpacing(8)
        self.toolsLayout.setObjectName("toolsLayout")
        self.toolsLayout.setContentsMargins(8, 8, 8, 8)
        self.label_tools = QLabel(self.tools_panel)
        self.label_tools.setObjectName("label_tools")

        self.toolsLayout.addWidget(self.label_tools)

        self.btn_suggest_deps = QPushButton(self.tools_panel)
        self.btn_suggest_deps.setObjectName("btn_suggest_deps")

        self.toolsLayout.addWidget(self.btn_suggest_deps)

        self.btn_bc_loader = QPushButton(self.tools_panel)
        self.btn_bc_loader.setObjectName("btn_bc_loader")

        self.toolsLayout.addWidget(self.btn_bc_loader)

        self.btn_advanced_config = QPushButton(self.tools_panel)
        self.btn_advanced_config.setObjectName("btn_advanced_config")

        self.toolsLayout.addWidget(self.btn_advanced_config)

        self.btn_help = QPushButton(self.tools_panel)
        self.btn_help.setObjectName("btn_help")

        self.toolsLayout.addWidget(self.btn_help)

        self.btn_show_stats = QPushButton(self.tools_panel)
        self.btn_show_stats.setObjectName("btn_show_stats")

        self.toolsLayout.addWidget(self.btn_show_stats)

        self.btn_select_lang = QPushButton(self.tools_panel)
        self.btn_select_lang.setObjectName("btn_select_lang")

        self.toolsLayout.addWidget(self.btn_select_lang)

        self.btn_select_theme = QPushButton(self.tools_panel)
        self.btn_select_theme.setObjectName("btn_select_theme")

        self.toolsLayout.addWidget(self.btn_select_theme)

        self.btn_acasl_loader = QPushButton(self.tools_panel)
        self.btn_acasl_loader.setObjectName("btn_acasl_loader")

        self.toolsLayout.addWidget(self.btn_acasl_loader)

        self.btn_select_icon = QPushButton(self.tools_panel)
        self.btn_select_icon.setObjectName("btn_select_icon")
        self.btn_select_icon.setVisible(False)

        self.toolsLayout.addWidget(self.btn_select_icon)

        self.btn_nuitka_icon = QPushButton(self.tools_panel)
        self.btn_nuitka_icon.setObjectName("btn_nuitka_icon")
        self.btn_nuitka_icon.setVisible(False)

        self.toolsLayout.addWidget(self.btn_nuitka_icon)

        self.toolsSpacer = QSpacerItem(
            20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
        )

        self.toolsLayout.addItem(self.toolsSpacer)

        self.topSplitter.addWidget(self.tools_panel)
        self.rightSplitter.addWidget(self.topSplitter)
        self.logs_panel = QFrame(self.rightSplitter)
        self.logs_panel.setObjectName("logs_panel")
        self.logs_panel.setMinimumSize(QSize(0, 190))
        self.logs_panel.setMaximumSize(QSize(16777215, 320))
        self.logs_panel.setFrameShape(QFrame.Shape.StyledPanel)
        self.logs_panel.setFrameShadow(QFrame.Shadow.Raised)
        self.logsLayout = QVBoxLayout(self.logs_panel)
        self.logsLayout.setSpacing(8)
        self.logsLayout.setObjectName("logsLayout")
        self.logsLayout.setContentsMargins(8, 8, 8, 8)
        self.label_logs_section = QLabel(self.logs_panel)
        self.label_logs_section.setObjectName("label_logs_section")

        self.logsLayout.addWidget(self.label_logs_section)

        self.log = QTextEdit(self.logs_panel)
        self.log.setObjectName("log")
        self.log.setAcceptRichText(False)
        self.log.setReadOnly(True)

        self.logsLayout.addWidget(self.log)

        self.progressRowLayout = QHBoxLayout()
        self.progressRowLayout.setObjectName("progressRowLayout")
        self.label_progress = QLabel(self.logs_panel)
        self.label_progress.setObjectName("label_progress")

        self.progressRowLayout.addWidget(self.label_progress)

        self.progress = QProgressBar(self.logs_panel)
        self.progress.setObjectName("progress")
        self.progress.setValue(0)

        self.progressRowLayout.addWidget(self.progress)

        self.logsLayout.addLayout(self.progressRowLayout)

        self.rightSplitter.addWidget(self.logs_panel)
        self.mainSplitter.addWidget(self.rightSplitter)

        self.rootLayout.addWidget(self.mainSplitter)

        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)

        self.compiler_tabs.setCurrentIndex(-1)

        QMetaObject.connectSlotsByName(MainWindow)

    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(
            QCoreApplication.translate(
                "MainWindow", "PyCompiler ARK - IDE Layout", None
            )
        )
        self.label_app_title.setText(
            QCoreApplication.translate("MainWindow", "PyCompiler ARK", None)
        )
        self.btn_build_all.setText(
            QCoreApplication.translate("MainWindow", "Build", None)
        )
        self.btn_cancel_all.setText(
            QCoreApplication.translate("MainWindow", "Cancel", None)
        )
        # if QT_CONFIG(tooltip)
        self.btn_more_actions.setToolTip(
            QCoreApplication.translate("MainWindow", "More tools", None)
        )
        # endif // QT_CONFIG(tooltip)
        self.btn_more_actions.setText(
            QCoreApplication.translate("MainWindow", "...", None)
        )
        # if QT_CONFIG(tooltip)
        self.btn_activity_deps.setToolTip(
            QCoreApplication.translate(
                "MainWindow", "Analyser d\u00e9pendances", None
            )
        )
        # endif // QT_CONFIG(tooltip)
        self.btn_activity_deps.setText("")
        self.label_workspace_section.setText(
            QCoreApplication.translate("MainWindow", "Workspace", None)
        )
        self.btn_select_folder.setText(
            QCoreApplication.translate("MainWindow", "Select Folder", None)
        )
        self.btn_venv_button.setText(
            QCoreApplication.translate("MainWindow", "Venv", None)
        )
        self.label_folder.setText(
            QCoreApplication.translate(
                "MainWindow", "Selected folder: (none)", None
            )
        )
        self.label_workspace_status.setText(
            QCoreApplication.translate("MainWindow", "Workspace: None", None)
        )
        self.venv_label.setText(
            QCoreApplication.translate("MainWindow", "Venv: (auto)", None)
        )
        self.label_files_section.setText(
            QCoreApplication.translate("MainWindow", "Files", None)
        )
        self.file_filter_input.setPlaceholderText(
            QCoreApplication.translate("MainWindow", "Filter files...", None)
        )
        self.btn_select_files.setText(
            QCoreApplication.translate("MainWindow", "Add", None)
        )
        self.btn_remove_file.setText(
            QCoreApplication.translate("MainWindow", "Supprimer", None)
        )
        self.btn_clear_workspace.setText(
            QCoreApplication.translate("MainWindow", "Clear", None)
        )
        self.label_tools.setText(
            QCoreApplication.translate("MainWindow", "Tools", None)
        )
        self.btn_suggest_deps.setText(
            QCoreApplication.translate("MainWindow", "Suggest Deps", None)
        )
        self.btn_bc_loader.setText(
            QCoreApplication.translate("MainWindow", "BC Loader", None)
        )
        self.btn_advanced_config.setText(
            QCoreApplication.translate("MainWindow", "Advanced Config", None)
        )
        self.btn_help.setText(
            QCoreApplication.translate("MainWindow", "Help", None)
        )
        self.btn_show_stats.setText(
            QCoreApplication.translate("MainWindow", "Stats", None)
        )
        self.btn_select_lang.setText(
            QCoreApplication.translate("MainWindow", "Language", None)
        )
        self.btn_select_theme.setText(
            QCoreApplication.translate("MainWindow", "Theme", None)
        )
        self.btn_acasl_loader.setText(
            QCoreApplication.translate("MainWindow", "ACASL", None)
        )
        # if QT_CONFIG(tooltip)
        self.btn_select_icon.setToolTip(
            QCoreApplication.translate("MainWindow", "Select icon", None)
        )
        # endif // QT_CONFIG(tooltip)
        self.btn_select_icon.setText(
            QCoreApplication.translate("MainWindow", "Icon", None)
        )
        # if QT_CONFIG(tooltip)
        self.btn_nuitka_icon.setToolTip(
            QCoreApplication.translate(
                "MainWindow", "Select Nuitka icon", None
            )
        )
        # endif // QT_CONFIG(tooltip)
        self.btn_nuitka_icon.setText(
            QCoreApplication.translate("MainWindow", "Nuitka", None)
        )
        self.label_logs_section.setText(
            QCoreApplication.translate("MainWindow", "Logs", None)
        )
        self.label_progress.setText(
            QCoreApplication.translate("MainWindow", "Progress", None)
        )

    # retranslateUi
