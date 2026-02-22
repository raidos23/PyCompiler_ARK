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
        PyCompilerARKGui.setStyleSheet(u"/* PyCompiler ARK \u2014 VSCode inspired */\n"
"\n"
"QWidget {\n"
"  background: #1E1E1E;\n"
"  color: #D4D4D4;\n"
"  font-family: \"Segoe UI\", \"Noto Sans\", \"DejaVu Sans\", Arial, sans-serif;\n"
"  font-size: 9pt;\n"
"}\n"
"\n"
"QToolTip {\n"
"  background-color: #252526;\n"
"  color: #D4D4D4;\n"
"  border: 1px solid #3C3C3C;\n"
"  border-radius: 2px;\n"
"  padding: 6px 8px;\n"
"}\n"
"\n"
"/* Header */\n"
"QFrame#header {\n"
"  background: #2D2D30;\n"
"  border: 1px solid #3C3C3C;\n"
"  border-radius: 0px;\n"
"}\n"
"QLabel#label_app_title {\n"
"  color: #FFFFFF;\n"
"  font-weight: 600;\n"
"}\n"
"QLabel#label_workspace_status {\n"
"  color: #C8C8C8;\n"
"}\n"
"\n"
"/* Section labels */\n"
"QLabel[objectName=\"label_workspace_section\"],\n"
"QLabel[objectName=\"label_files_section\"],\n"
"QLabel[objectName=\"label_options_section\"],\n"
"QLabel[objectName=\"label_logs_section\"] {\n"
"  font-weight: 600;\n"
"  font-size: 9pt;\n"
"  color: #C8C8C8;\n"
"  padding-bottom: 4px;\n"
"}\n"
"QLabel[objectName=\"label"
                        "_main_actions\"],\n"
"QLabel[objectName=\"label_config_actions\"],\n"
"QLabel[objectName=\"label_tools\"],\n"
"QLabel[objectName=\"label_settings\"],\n"
"QLabel[objectName=\"label_progress\"] {\n"
"  font-weight: 600;\n"
"  font-size: 9pt;\n"
"  color: #C8C8C8;\n"
"  padding-bottom: 4px;\n"
"}\n"
"\n"
"/* Buttons */\n"
"QPushButton {\n"
"  background: #3C3C3C;\n"
"  color: #D4D4D4;\n"
"  border: 1px solid #3C3C3C;\n"
"  border-radius: 2px;\n"
"  padding: 6px 10px;\n"
"  font-size: 9pt;\n"
"}\n"
"QPushButton:hover { background: #454545; border-color: #454545; }\n"
"QPushButton:pressed { background: #2A2A2A; }\n"
"QPushButton:disabled { color: #8A8A8A; background: #2B2B2B; border-color: #2B2B2B; }\n"
"\n"
"QPushButton#compile_btn {\n"
"  background: #0E639C;\n"
"  color: #FFFFFF;\n"
"  border-color: #0E639C;\n"
"  font-weight: 600;\n"
"}\n"
"QPushButton#compile_btn:hover { background: #1177BB; border-color: #1177BB; }\n"
"QPushButton#compile_btn:pressed { background: #0B4F7A; }\n"
"QPushButton#cancel_btn {\n"
" "
                        " background: #5A1D1D;\n"
"  color: #F2B8B8;\n"
"  border: 1px solid #6A2A2A;\n"
"}\n"
"QPushButton#cancel_btn:hover { background: #6A2727; border-color: #7A3030; }\n"
"\n"
"/* Checkboxes & Radio */\n"
"QCheckBox { color: #D4D4D4; }\n"
"QCheckBox::indicator { width: 14px; height: 14px; }\n"
"QCheckBox::indicator:unchecked { border: 1px solid #3C3C3C; background: #1E1E1E; }\n"
"QCheckBox::indicator:checked { image: none; border: 1px solid #007ACC; background: #007ACC; }\n"
"\n"
"QRadioButton::indicator { width: 14px; height: 14px; border: 1px solid #3C3C3C; background: #1E1E1E; border-radius: 7px; }\n"
"QRadioButton::indicator:checked { background: #007ACC; border-color: #007ACC; }\n"
"\n"
"/* Inputs */\n"
"QLineEdit, QTextEdit, QPlainTextEdit {\n"
"  background: #3C3C3C;\n"
"  color: #D4D4D4;\n"
"  border: 1px solid #3C3C3C;\n"
"  border-radius: 2px;\n"
"  padding: 4px 6px;\n"
"}\n"
"QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus { border-color: #007ACC; }\n"
"\n"
"/* Lists & Tables */\n"
"QListWidget, "
                        "QTreeWidget, QTableWidget, QTableView {\n"
"  background: #1E1E1E;\n"
"  color: #D4D4D4;\n"
"  border: 1px solid #3C3C3C;\n"
"  border-radius: 0px;\n"
"  selection-background-color: #094771;\n"
"  selection-color: #D4D4D4;\n"
"  padding: 2px;\n"
"}\n"
"QListWidget::item, QTreeWidget::item { padding: 4px 6px; }\n"
"QListWidget::item:hover, QTreeWidget::item:hover { background: #2A2D2E; }\n"
"QListWidget::item:selected, QTreeWidget::item:selected { background: #094771; color: #FFFFFF; }\n"
"\n"
"/* Tabs */\n"
"QTabWidget::pane { border: 1px solid #3C3C3C; background: #1E1E1E; }\n"
"QTabBar { background: #2D2D30; }\n"
"QTabBar::tab {\n"
"  background: #2D2D30;\n"
"  color: #D4D4D4;\n"
"  padding: 6px 12px;\n"
"  border: 1px solid #3C3C3C;\n"
"  border-bottom: none;\n"
"}\n"
"QTabBar::tab:selected { background: #1E1E1E; border-bottom-color: #1E1E1E; }\n"
"QTabBar::tab:hover { background: #37373D; }\n"
"\n"
"/* Progress */\n"
"QProgressBar {\n"
"  border: 1px solid #3C3C3C;\n"
"  border-radius: 0px;\n"
"  text-alig"
                        "n: center;\n"
"  background: #1E1E1E;\n"
"  color: #D4D4D4;\n"
"  height: 12px;\n"
"}\n"
"QProgressBar::chunk { background-color: #0E639C; }\n"
"\n"
"/* Combos & Spin */\n"
"QComboBox, QSpinBox, QDoubleSpinBox {\n"
"  background: #3C3C3C;\n"
"  color: #D4D4D4;\n"
"  border: 1px solid #3C3C3C;\n"
"  border-radius: 2px;\n"
"  padding: 4px 6px;\n"
"}\n"
"QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover { background: #454545; }\n"
"QComboBox QAbstractItemView {\n"
"  background: #252526;\n"
"  color: #D4D4D4;\n"
"  border: 1px solid #3C3C3C;\n"
"  selection-background-color: #094771;\n"
"  selection-color: #FFFFFF;\n"
"  outline: 0;\n"
"}\n"
"\n"
"QAbstractSpinBox:focus { border-color: #007ACC; }\n"
"QSpinBox::up-button, QDoubleSpinBox::up-button {\n"
"  subcontrol-origin: border;\n"
"  subcontrol-position: top right;\n"
"  width: 20px;\n"
"  border-left: 1px solid #3C3C3C;\n"
"  background: #2D2D30;\n"
"}\n"
"QSpinBox::down-button, QDoubleSpinBox::down-button {\n"
"  subcontrol-origin: border;\n"
"  subcontr"
                        "ol-position: bottom right;\n"
"  width: 20px;\n"
"  border-left: 1px solid #3C3C3C;\n"
"  background: #2D2D30;\n"
"}\n"
"\n"
"/* Frames & Groups */\n"
"QFrame[frameShape=\"4\"] {\n"
"  background: #252526;\n"
"  border: 1px solid #3C3C3C;\n"
"  border-radius: 0px;\n"
"}\n"
"QGroupBox {\n"
"  border: 1px solid #3C3C3C;\n"
"  border-radius: 0px;\n"
"  margin-top: 12px;\n"
"  padding-top: 8px;\n"
"}\n"
"QGroupBox::title {\n"
"  subcontrol-origin: margin;\n"
"  left: 12px;\n"
"  padding: 0 6px;\n"
"  background: transparent;\n"
"  color: #D4D4D4;\n"
"  font-weight: 600;\n"
"}\n"
"\n"
"/* Menus */\n"
"QMenuBar { background: #2D2D30; color: #D4D4D4; }\n"
"QMenuBar::item:selected { background: #37373D; }\n"
"QMenu {\n"
"  background: #252526;\n"
"  color: #D4D4D4;\n"
"  border: 1px solid #3C3C3C;\n"
"}\n"
"QMenu::item { padding: 6px 12px; }\n"
"QMenu::item:selected { background: #094771; }\n"
"QMenu::separator { height: 1px; background: #3C3C3C; margin: 6px 8px; }\n"
"\n"
"QStatusBar {\n"
"  background: #007ACC;\n"
""
                        "  color: #FFFFFF;\n"
"  border-top: 1px solid #005F9E;\n"
"}\n"
"QStatusBar::item { border: none; }\n"
"\n"
"/* Scrollbars */\n"
"QScrollBar:vertical { background: transparent; width: 12px; margin: 0px; border: none; }\n"
"QScrollBar::handle:vertical { background: #3F3F3F; min-height: 24px; }\n"
"QScrollBar::handle:vertical:hover { background: #4B4B4B; }\n"
"QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }\n"
"QScrollBar:horizontal { background: transparent; height: 12px; margin: 0px; border: none; }\n"
"QScrollBar::handle:horizontal { background: #3F3F3F; min-width: 24px; }\n"
"QScrollBar::handle:horizontal:hover { background: #4B4B4B; }\n"
"QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }\n"
"")
        self.rootLayout = QVBoxLayout(PyCompilerARKGui)
        self.rootLayout.setSpacing(0)
        self.rootLayout.setObjectName(u"rootLayout")
        self.rootLayout.setContentsMargins(0, 0, 0, 0)
        self.header = QFrame(PyCompilerARKGui)
        self.header.setObjectName(u"header")
        self.header.setMinimumSize(QSize(0, 44))
        self.header.setFrameShape(QFrame.Shape.StyledPanel)
        self.headerLayout = QHBoxLayout(self.header)
        self.headerLayout.setSpacing(8)
        self.headerLayout.setObjectName(u"headerLayout")
        self.headerLayout.setContentsMargins(8, 6, 8, 6)
        self.headerLeftLayout = QVBoxLayout()
        self.headerLeftLayout.setSpacing(0)
        self.headerLeftLayout.setObjectName(u"headerLeftLayout")
        self.headerLeftLayout.setContentsMargins(0, 0, 0, 0)
        self.label_app_title = QLabel(self.header)
        self.label_app_title.setObjectName(u"label_app_title")
        font = QFont()
        font.setFamilies([u"Segoe UI"])
        font.setPointSize(9)
        font.setWeight(QFont.DemiBold)
        self.label_app_title.setFont(font)

        self.headerLeftLayout.addWidget(self.label_app_title)

        self.label_workspace_status = QLabel(self.header)
        self.label_workspace_status.setObjectName(u"label_workspace_status")

        self.headerLeftLayout.addWidget(self.label_workspace_status)


        self.headerLayout.addLayout(self.headerLeftLayout)

        self.headerSpacer = QSpacerItem(40, 60, QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Minimum)

        self.headerLayout.addItem(self.headerSpacer)

        self.headerRightLayout = QHBoxLayout()
        self.headerRightLayout.setSpacing(6)
        self.headerRightLayout.setObjectName(u"headerRightLayout")
        self.headerRightLayout.setContentsMargins(0, 0, 0, 0)
        self.select_lang = QPushButton(self.header)
        self.select_lang.setObjectName(u"select_lang")

        self.headerRightLayout.addWidget(self.select_lang)

        self.select_theme = QPushButton(self.header)
        self.select_theme.setObjectName(u"select_theme")

        self.headerRightLayout.addWidget(self.select_theme)

        self.compile_btn = QPushButton(self.header)
        self.compile_btn.setObjectName(u"compile_btn")

        self.headerRightLayout.addWidget(self.compile_btn)

        self.cancel_btn = QPushButton(self.header)
        self.cancel_btn.setObjectName(u"cancel_btn")

        self.headerRightLayout.addWidget(self.cancel_btn)


        self.headerLayout.addLayout(self.headerRightLayout)


        self.rootLayout.addWidget(self.header)

        self.mainSplitter = QSplitter(PyCompilerARKGui)
        self.mainSplitter.setObjectName(u"mainSplitter")
        self.mainSplitter.setOrientation(Qt.Orientation.Horizontal)
        self.mainSplitter.setHandleWidth(6)
        self.leftPanel = QWidget(self.mainSplitter)
        self.leftPanel.setObjectName(u"leftPanel")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.leftPanel.sizePolicy().hasHeightForWidth())
        self.leftPanel.setSizePolicy(sizePolicy)
        self.leftPanel.setMinimumSize(QSize(280, 0))
        self.leftLayout = QVBoxLayout(self.leftPanel)
        self.leftLayout.setSpacing(8)
        self.leftLayout.setObjectName(u"leftLayout")
        self.leftLayout.setContentsMargins(6, 6, 6, 6)
        self.leftSplitter = QSplitter(self.leftPanel)
        self.leftSplitter.setObjectName(u"leftSplitter")
        self.leftSplitter.setOrientation(Qt.Orientation.Vertical)
        self.leftSplitter.setHandleWidth(6)
        self.frame_workspace = QFrame(self.leftSplitter)
        self.frame_workspace.setObjectName(u"frame_workspace")
        self.frame_workspace.setFrameShape(QFrame.Shape.StyledPanel)
        self.layout_workspace_grid = QGridLayout(self.frame_workspace)
        self.layout_workspace_grid.setSpacing(8)
        self.layout_workspace_grid.setObjectName(u"layout_workspace_grid")
        self.layout_workspace_grid.setContentsMargins(8, 8, 8, 8)
        self.label_workspace_section = QLabel(self.frame_workspace)
        self.label_workspace_section.setObjectName(u"label_workspace_section")
        self.label_workspace_section.setFont(font)

        self.layout_workspace_grid.addWidget(self.label_workspace_section, 0, 0, 1, 2)

        self.label_folder = QLabel(self.frame_workspace)
        self.label_folder.setObjectName(u"label_folder")
        font1 = QFont()
        font1.setFamilies([u"Segoe UI"])
        font1.setPointSize(9)
        font1.setBold(True)
        self.label_folder.setFont(font1)
        self.label_folder.setFrameShape(QFrame.Shape.NoFrame)
        self.label_folder.setFrameShadow(QFrame.Shadow.Plain)
        self.label_folder.setWordWrap(True)
        self.label_folder.setMargin(6)

        self.layout_workspace_grid.addWidget(self.label_folder, 1, 0, 1, 2)

        self.venv_label = QLabel(self.frame_workspace)
        self.venv_label.setObjectName(u"venv_label")
        self.venv_label.setFont(font1)
        self.venv_label.setFrameShape(QFrame.Shape.NoFrame)
        self.venv_label.setFrameShadow(QFrame.Shadow.Plain)
        self.venv_label.setWordWrap(True)
        self.venv_label.setMargin(6)

        self.layout_workspace_grid.addWidget(self.venv_label, 2, 0, 1, 1)

        self.venv_button = QPushButton(self.frame_workspace)
        self.venv_button.setObjectName(u"venv_button")

        self.layout_workspace_grid.addWidget(self.venv_button, 2, 1, 1, 1)

        self.btn_select_folder = QPushButton(self.frame_workspace)
        self.btn_select_folder.setObjectName(u"btn_select_folder")

        self.layout_workspace_grid.addWidget(self.btn_select_folder, 3, 0, 1, 1)

        self.btn_clear_workspace = QPushButton(self.frame_workspace)
        self.btn_clear_workspace.setObjectName(u"btn_clear_workspace")

        self.layout_workspace_grid.addWidget(self.btn_clear_workspace, 3, 1, 1, 1)

        self.leftSplitter.addWidget(self.frame_workspace)
        self.frame_files = QFrame(self.leftSplitter)
        self.frame_files.setObjectName(u"frame_files")
        self.frame_files.setFrameShape(QFrame.Shape.StyledPanel)
        self.layout_files_grid = QGridLayout(self.frame_files)
        self.layout_files_grid.setSpacing(8)
        self.layout_files_grid.setObjectName(u"layout_files_grid")
        self.layout_files_grid.setContentsMargins(8, 8, 8, 8)
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

        self.file_filter_input = QLineEdit(self.frame_files)
        self.file_filter_input.setObjectName(u"file_filter_input")

        self.layout_files_grid.addWidget(self.file_filter_input, 1, 0, 1, 2)

        self.file_list = QListWidget(self.frame_files)
        self.file_list.setObjectName(u"file_list")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(1)
        sizePolicy1.setHeightForWidth(self.file_list.sizePolicy().hasHeightForWidth())
        self.file_list.setSizePolicy(sizePolicy1)

        self.layout_files_grid.addWidget(self.file_list, 2, 0, 1, 1)

        self.label_files_section = QLabel(self.frame_files)
        self.label_files_section.setObjectName(u"label_files_section")
        self.label_files_section.setFont(font)
        self.label_files_section.setWordWrap(True)

        self.layout_files_grid.addWidget(self.label_files_section, 0, 0, 1, 2)

        self.leftSplitter.addWidget(self.frame_files)
        self.frame_tools = QFrame(self.leftSplitter)
        self.frame_tools.setObjectName(u"frame_tools")
        self.frame_tools.setFrameShape(QFrame.Shape.StyledPanel)
        self.layout_tools_grid = QGridLayout(self.frame_tools)
        self.layout_tools_grid.setSpacing(8)
        self.layout_tools_grid.setObjectName(u"layout_tools_grid")
        self.layout_tools_grid.setContentsMargins(8, 8, 8, 8)
        self.btn_show_stats = QPushButton(self.frame_tools)
        self.btn_show_stats.setObjectName(u"btn_show_stats")

        self.layout_tools_grid.addWidget(self.btn_show_stats, 2, 0, 1, 1)

        self.btn_suggest_deps = QPushButton(self.frame_tools)
        self.btn_suggest_deps.setObjectName(u"btn_suggest_deps")

        self.layout_tools_grid.addWidget(self.btn_suggest_deps, 1, 0, 1, 1)

        self.btn_bc_loader = QPushButton(self.frame_tools)
        self.btn_bc_loader.setObjectName(u"btn_bc_loader")

        self.layout_tools_grid.addWidget(self.btn_bc_loader, 1, 1, 1, 1)

        self.btn_help = QPushButton(self.frame_tools)
        self.btn_help.setObjectName(u"btn_help")

        self.layout_tools_grid.addWidget(self.btn_help, 2, 1, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 60, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.layout_tools_grid.addItem(self.verticalSpacer, 3, 0, 1, 2)

        self.label_tools = QLabel(self.frame_tools)
        self.label_tools.setObjectName(u"label_tools")
        self.label_tools.setFont(font)

        self.layout_tools_grid.addWidget(self.label_tools, 0, 0, 1, 2)

        self.leftSplitter.addWidget(self.frame_tools)

        self.leftLayout.addWidget(self.leftSplitter)

        self.mainSplitter.addWidget(self.leftPanel)
        self.rightPanel = QWidget(self.mainSplitter)
        self.rightPanel.setObjectName(u"rightPanel")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy2.setHorizontalStretch(1)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.rightPanel.sizePolicy().hasHeightForWidth())
        self.rightPanel.setSizePolicy(sizePolicy2)
        self.rightLayout = QVBoxLayout(self.rightPanel)
        self.rightLayout.setSpacing(8)
        self.rightLayout.setObjectName(u"rightLayout")
        self.rightLayout.setContentsMargins(6, 6, 6, 6)
        self.rightSplitter = QSplitter(self.rightPanel)
        self.rightSplitter.setObjectName(u"rightSplitter")
        self.rightSplitter.setOrientation(Qt.Orientation.Vertical)
        self.rightSplitter.setHandleWidth(6)
        self.frame_options = QFrame(self.rightSplitter)
        self.frame_options.setObjectName(u"frame_options")
        self.frame_options.setFrameShape(QFrame.Shape.StyledPanel)
        self.layout_options = QVBoxLayout(self.frame_options)
        self.layout_options.setSpacing(8)
        self.layout_options.setObjectName(u"layout_options")
        self.layout_options.setContentsMargins(8, 8, 8, 8)
        self.label_options_section = QLabel(self.frame_options)
        self.label_options_section.setObjectName(u"label_options_section")
        self.label_options_section.setFont(font)

        self.layout_options.addWidget(self.label_options_section)

        self.compiler_tabs = QTabWidget(self.frame_options)
        self.compiler_tabs.setObjectName(u"compiler_tabs")

        self.layout_options.addWidget(self.compiler_tabs)

        self.rightSplitter.addWidget(self.frame_options)
        self.frame_logs = QFrame(self.rightSplitter)
        self.frame_logs.setObjectName(u"frame_logs")
        self.frame_logs.setFrameShape(QFrame.Shape.StyledPanel)
        self.layout_logs = QVBoxLayout(self.frame_logs)
        self.layout_logs.setSpacing(8)
        self.layout_logs.setObjectName(u"layout_logs")
        self.layout_logs.setContentsMargins(8, 8, 8, 8)
        self.label_logs_section = QLabel(self.frame_logs)
        self.label_logs_section.setObjectName(u"label_logs_section")
        self.label_logs_section.setFont(font)

        self.layout_logs.addWidget(self.label_logs_section)

        self.log = QTextEdit(self.frame_logs)
        self.log.setObjectName(u"log")
        sizePolicy1.setHeightForWidth(self.log.sizePolicy().hasHeightForWidth())
        self.log.setSizePolicy(sizePolicy1)

        self.layout_logs.addWidget(self.log)

        self.rightSplitter.addWidget(self.frame_logs)
        self.frame_progress = QFrame(self.rightSplitter)
        self.frame_progress.setObjectName(u"frame_progress")
        self.frame_progress.setFrameShape(QFrame.Shape.StyledPanel)
        self.layout_progress = QVBoxLayout(self.frame_progress)
        self.layout_progress.setSpacing(6)
        self.layout_progress.setObjectName(u"layout_progress")
        self.layout_progress.setContentsMargins(8, 8, 8, 8)
        self.label_progress = QLabel(self.frame_progress)
        self.label_progress.setObjectName(u"label_progress")
        self.label_progress.setFont(font)

        self.layout_progress.addWidget(self.label_progress)

        self.progress = QProgressBar(self.frame_progress)
        self.progress.setObjectName(u"progress")
        self.progress.setValue(0)
        self.progress.setTextVisible(True)

        self.layout_progress.addWidget(self.progress)

        self.rightSplitter.addWidget(self.frame_progress)

        self.rightLayout.addWidget(self.rightSplitter)

        self.mainSplitter.addWidget(self.rightPanel)

        self.rootLayout.addWidget(self.mainSplitter)


        self.retranslateUi(PyCompilerARKGui)

        self.compiler_tabs.setCurrentIndex(-1)


        QMetaObject.connectSlotsByName(PyCompilerARKGui)
    # setupUi

    def retranslateUi(self, PyCompilerARKGui):
        self.label_app_title.setText(QCoreApplication.translate("PyCompilerARKGui", u"PyCompiler ARK", None))
        self.label_workspace_status.setText(QCoreApplication.translate("PyCompilerARKGui", u"Workspace : Aucun", None))
#if QT_CONFIG(tooltip)
        self.select_lang.setToolTip(QCoreApplication.translate("PyCompilerARKGui", u"Choisir la langue de l'interface", None))
#endif // QT_CONFIG(tooltip)
        self.select_lang.setText(QCoreApplication.translate("PyCompilerARKGui", u"Langue", None))
#if QT_CONFIG(tooltip)
        self.select_theme.setToolTip(QCoreApplication.translate("PyCompilerARKGui", u"Choisir le th\u00e8me de l'interface", None))
#endif // QT_CONFIG(tooltip)
        self.select_theme.setText(QCoreApplication.translate("PyCompilerARKGui", u"Th\u00e8me", None))
#if QT_CONFIG(tooltip)
        self.compile_btn.setToolTip(QCoreApplication.translate("PyCompilerARKGui", u"D\u00e9marrer la compilation", None))
#endif // QT_CONFIG(tooltip)
        self.compile_btn.setText(QCoreApplication.translate("PyCompilerARKGui", u"Compiler", None))
#if QT_CONFIG(tooltip)
        self.cancel_btn.setToolTip(QCoreApplication.translate("PyCompilerARKGui", u"Annuler la compilation en cours", None))
#endif // QT_CONFIG(tooltip)
        self.cancel_btn.setText(QCoreApplication.translate("PyCompilerARKGui", u"Annuler", None))
        self.label_workspace_section.setText(QCoreApplication.translate("PyCompilerARKGui", u"Workspace", None))
        self.label_folder.setText(QCoreApplication.translate("PyCompilerARKGui", u"Aucun dossier s\u00e9lectionn\u00e9", None))
        self.venv_label.setText(QCoreApplication.translate("PyCompilerARKGui", u"Venv s\u00e9lectionn\u00e9 : Aucun", None))
        self.venv_button.setText(QCoreApplication.translate("PyCompilerARKGui", u"Choisir un dossier venv", None))
#if QT_CONFIG(tooltip)
        self.btn_select_folder.setToolTip(QCoreApplication.translate("PyCompilerARKGui", u"S\u00e9lectionner le Workspace", None))
#endif // QT_CONFIG(tooltip)
        self.btn_select_folder.setText(QCoreApplication.translate("PyCompilerARKGui", u"Choisir le Workspace", None))
#if QT_CONFIG(tooltip)
        self.btn_clear_workspace.setToolTip(QCoreApplication.translate("PyCompilerARKGui", u"Vider la liste des fichiers et r\u00e9initialiser la s\u00e9lection", None))
#endif // QT_CONFIG(tooltip)
        self.btn_clear_workspace.setText(QCoreApplication.translate("PyCompilerARKGui", u"Vider le Workspace", None))
#if QT_CONFIG(tooltip)
        self.btn_select_files.setToolTip(QCoreApplication.translate("PyCompilerARKGui", u"Ajouter des fichiers \u00e0 compiler", None))
#endif // QT_CONFIG(tooltip)
        self.btn_select_files.setText(QCoreApplication.translate("PyCompilerARKGui", u"Ajouter des fichiers", None))
        self.btn_remove_file.setText(QCoreApplication.translate("PyCompilerARKGui", u"Supprimer le fichier s\u00e9lectionn\u00e9", None))
        self.file_filter_input.setPlaceholderText(QCoreApplication.translate("PyCompilerARKGui", u"Filtrer la liste\u2026", None))
        self.label_files_section.setText(QCoreApplication.translate("PyCompilerARKGui", u"Fichiers \u00e0 compiler", None))
#if QT_CONFIG(tooltip)
        self.btn_show_stats.setToolTip(QCoreApplication.translate("PyCompilerARKGui", u"Afficher les statistiques de compilation", None))
#endif // QT_CONFIG(tooltip)
        self.btn_show_stats.setText(QCoreApplication.translate("PyCompilerARKGui", u"Statistiques", None))
#if QT_CONFIG(tooltip)
        self.btn_suggest_deps.setToolTip(QCoreApplication.translate("PyCompilerARKGui", u"Analyser les d\u00e9pendances du projet", None))
#endif // QT_CONFIG(tooltip)
        self.btn_suggest_deps.setText(QCoreApplication.translate("PyCompilerARKGui", u"D\u00e9pendances", None))
#if QT_CONFIG(tooltip)
        self.btn_bc_loader.setToolTip(QCoreApplication.translate("PyCompilerARKGui", u"Ouvrir BC Plugins Loader", None))
#endif // QT_CONFIG(tooltip)
        self.btn_bc_loader.setText(QCoreApplication.translate("PyCompilerARKGui", u"BC Plugins Loader", None))
#if QT_CONFIG(tooltip)
        self.btn_help.setToolTip(QCoreApplication.translate("PyCompilerARKGui", u"Afficher l'aide", None))
#endif // QT_CONFIG(tooltip)
        self.btn_help.setText(QCoreApplication.translate("PyCompilerARKGui", u"Aide", None))
        self.label_tools.setText(QCoreApplication.translate("PyCompilerARKGui", u"Outils", None))
        self.label_options_section.setText(QCoreApplication.translate("PyCompilerARKGui", u"Options de compilation", None))
        self.label_logs_section.setText(QCoreApplication.translate("PyCompilerARKGui", u"Journal de compilation", None))
        self.label_progress.setText(QCoreApplication.translate("PyCompilerARKGui", u"Progression de la compilation", None))
        pass
    # retranslateUi

