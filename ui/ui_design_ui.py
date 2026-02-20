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
        PyCompilerARKGui.setStyleSheet(u"/* PyCompiler ARK \u2014 Dark Theme (ui/themes/dark.qss)\n"
"   Palette sombre contrast\u00e9e avec accent bleu\n"
"*/\n"
"\n"
"/* Base */\n"
"QWidget {\n"
"  background: #121417; /* presque noir, confortable */\n"
"  color: #E6E8EB;\n"
"  font-family: \"Segoe UI\", \"Noto Sans\", \"DejaVu Sans\", Arial, sans-serif;\n"
"  font-size: 10pt;\n"
"}\n"
"\n"
"QToolTip {\n"
"  background-color: #1B1E23;\n"
"  color: #E6E8EB;\n"
"  border: 1px solid #2A2F37;\n"
"  border-radius: 6px;\n"
"  padding: 6px 8px;\n"
"}\n"
"\n"
"/* Titres / labels */\n"
"QLabel[objectName=\"label_workspace_section\"],\n"
"QLabel[objectName=\"label_files_section\"],\n"
"QLabel[objectName=\"label_options_section\"],\n"
"QLabel[objectName=\"label_logs_section\"] {\n"
"  font-weight: 600;\n"
"  font-size: 12pt;\n"
"  color: #F1F3F5;\n"
"  padding-bottom: 4px;\n"
"}\n"
"\n"
"QLabel[objectName=\"label_main_actions\"],\n"
"QLabel[objectName=\"label_config_actions\"],\n"
"QLabel[objectName=\"label_tools\"],\n"
"QLabel[objectName=\"label_settings\"],"
                        "\n"
"QLabel[objectName=\"label_progress\"] {\n"
"  font-weight: 600;\n"
"  font-size: 11pt;\n"
"  color: #F1F3F5;\n"
"  padding-bottom: 4px;\n"
"}\n"
"\n"
"/* Boutons */\n"
"QPushButton {\n"
"  background: #1B1E23;\n"
"  color: #E6E8EB;\n"
"  border: 1px solid #2A2F37;\n"
"  border-radius: 10px;\n"
"  padding: 8px 14px;\n"
"  font-size: 10pt;\n"
"}\n"
"QPushButton:hover {\n"
"  background: #232831;\n"
"  border-color: #3A4049;\n"
"}\n"
"QPushButton:pressed {\n"
"  background: #20242C;\n"
"}\n"
"QPushButton:disabled {\n"
"  color: #878B93;\n"
"  background: #1A1D21;\n"
"  border-color: #1F2329;\n"
"}\n"
"\n"
"/* Boutons principaux */\n"
"QPushButton#compile_btn {\n"
"  background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3685FF, stop:1 #2D7DFF);\n"
"  color: #ffffff;\n"
"  border-color: #2D7DFF;\n"
"  font-weight: 600;\n"
"}\n"
"QPushButton#compile_btn:hover { \n"
"  background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4090FF, stop:1 #3280FF);\n"
"  border-color: #3685FF;\n"
"}\n"
"QPushButton#com"
                        "pile_btn:pressed { \n"
"  background: #226AF0; \n"
"}\n"
"QPushButton#cancel_btn {\n"
"  background: #3A2023;\n"
"  color: #ffb3ba;\n"
"  border: 1px solid #5A2A30;\n"
"}\n"
"QPushButton#cancel_btn:hover { \n"
"  background: #44262A;\n"
"  border-color: #6A3A40;\n"
"}\n"
"\n"
"/* Cases \u00e0 cocher */\n"
"QCheckBox { color: #E6E8EB; }\n"
"QCheckBox::indicator {\n"
"  width: 16px; height: 16px;\n"
"}\n"
"QCheckBox::indicator:unchecked {\n"
"  border: 1px solid #3A4049; border-radius: 3px; background: #14171B;\n"
"}\n"
"QCheckBox::indicator:checked {\n"
"  image: none; border: 1px solid #2D7DFF; background: #2D7DFF;\n"
"}\n"
"\n"
"/* Champs de saisie */\n"
"QLineEdit, QTextEdit, QPlainTextEdit {\n"
"  background: #14171B;\n"
"  color: #E6E8EB;\n"
"  border: 1px solid #2A2F37;\n"
"  border-radius: 6px;\n"
"  padding: 6px 8px;\n"
"}\n"
"QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus { border-color: #2D7DFF; }\n"
"\n"
"/* Listes */\n"
"QListWidget, QTreeWidget, QTableWidget, QTableView {\n"
"  background: "
                        "#14171B;\n"
"  color: #E6E8EB;\n"
"  border: 1px solid #2A2F37;\n"
"  border-radius: 8px;\n"
"  selection-background-color: #203357;\n"
"  selection-color: #E6E8EB;\n"
"  padding: 4px;\n"
"}\n"
"QListWidget::item, QTreeWidget::item {\n"
"  padding: 6px 8px;\n"
"  border-radius: 4px;\n"
"}\n"
"QListWidget::item:hover, QTreeWidget::item:hover {\n"
"  background: #1B1E23;\n"
"}\n"
"QListWidget::item:selected, QTreeWidget::item:selected {\n"
"  background: #203357;\n"
"  color: #E6E8EB;\n"
"}\n"
"QListWidget::item:alternate {\n"
"  background: #16191D;\n"
"}\n"
"\n"
"/* Onglets */\n"
"QTabWidget::pane {\n"
"  border: 1px solid #2A2F37; border-radius: 8px; background: #14171B;\n"
"}\n"
"QTabBar { background: #14171B; }\n"
"QTabBar::tab {\n"
"  background: #1B1E23; color: #E6E8EB; padding: 6px 12px; border: 1px solid #2A2F37; border-bottom: none; border-top-left-radius: 8px; border-top-right-radius: 8px;\n"
"}\n"
"QTabBar::tab:selected { background: #14171B; }\n"
"QTabBar::tab:hover { background: #232831; }\n"
"\n"
""
                        "/* Barre de progression */\n"
"QProgressBar {\n"
"  border: 1px solid #2A2F37; border-radius: 8px; text-align: center; background: #14171B; color: #E6E8EB; height: 14px;\n"
"}\n"
"QProgressBar::chunk { background-color: #2D7DFF; border-radius: 8px; }\n"
"\n"
"/* ComboBox */\n"
"QComboBox, QSpinBox, QDoubleSpinBox {\n"
"  background: #14171B; color: #E6E8EB; border: 1px solid #2A2F37; border-radius: 6px; padding: 4px 8px;\n"
"}\n"
"QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover { background: #1B1E23; }\n"
"QComboBox QAbstractItemView { background: #14171B; color: #E6E8EB; selection-background-color: #203357; selection-color: #E6E8EB; }\n"
"\n"
"/* Scrollbars (Qt6) */\n"
"QScrollBar:vertical {\n"
"  background: transparent; width: 12px; margin: 0px; border: none;\n"
"}\n"
"QScrollBar::handle:vertical {\n"
"  background: #3A4049; min-height: 24px; border-radius: 6px;\n"
"}\n"
"QScrollBar::handle:vertical:hover { background: #4A5059; }\n"
"QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { heigh"
                        "t: 0; }\n"
"\n"
"QScrollBar:horizontal {\n"
"  background: transparent; height: 12px; margin: 0px; border: none;\n"
"}\n"
"QScrollBar::handle:horizontal {\n"
"  background: #3A4049; min-width: 24px; border-radius: 6px;\n"
"}\n"
"QScrollBar::handle:horizontal:hover { background: #4A5059; }\n"
"QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }\n"
"\n"
"/* Dialogs & Message Boxes */\n"
"QDialog, QMessageBox {\n"
"  background: #14171B;\n"
"  color: #E6E8EB;\n"
"  border-radius: 12px;\n"
"  border: 1px solid #2A2F37;\n"
"}\n"
"QDialog QLabel, QMessageBox QLabel { color: #E6E8EB; }\n"
"QDialogButtonBox QPushButton, QMessageBox QPushButton {\n"
"  background: #1B1E23;\n"
"  color: #E6E8EB;\n"
"  border: 1px solid #2A2F37;\n"
"  border-radius: 10px;\n"
"  padding: 6px 12px;\n"
"  min-width: 90px;\n"
"}\n"
"QDialogButtonBox QPushButton:hover, QMessageBox QPushButton:hover { background: #232831; }\n"
"QDialogButtonBox QPushButton:pressed, QMessageBox QPushButton:pressed { background: #20242"
                        "C; }\n"
"QDialogButtonBox QPushButton:default, QMessageBox QPushButton:default {\n"
"  background: #2D7DFF; color: #ffffff; border-color: #2D7DFF;\n"
"}\n"
"QDialogButtonBox QPushButton:default:hover, QMessageBox QPushButton:default:hover { background: #226AF0; }\n"
"\n"
"/* Text edit log (monospace) */\n"
"QTextEdit#log {\n"
"  font-family: \"Cascadia Code\", \"Fira Code\", \"DejaVu Sans Mono\", monospace;\n"
"  font-size: 10pt;\n"
"  background: #0F1113;\n"
"}\n"
"\n"
"/* Modern selects and inputs */\n"
"QComboBox {\n"
"  background: #14171B;\n"
"  color: #E6E8EB;\n"
"  border: 1px solid #2A2F37;\n"
"  border-radius: 10px;\n"
"  padding: 6px 36px 6px 10px;\n"
"}\n"
"QComboBox:focus { border-color: #2D7DFF; }\n"
"QComboBox::drop-down {\n"
"  subcontrol-origin: padding;\n"
"  subcontrol-position: top right;\n"
"  width: 30px;\n"
"  border-left: 1px solid #2A2F37;\n"
"  background: #1B1E23;\n"
"  border-top-right-radius: 10px;\n"
"  border-bottom-right-radius: 10px;\n"
"}\n"
"QComboBox QAbstractItemView {\n"
" "
                        " background: #14171B;\n"
"  color: #E6E8EB;\n"
"  border: 1px solid #2A2F37;\n"
"  border-radius: 10px;\n"
"  padding: 4px;\n"
"  selection-background-color: #203357;\n"
"  selection-color: #E6E8EB;\n"
"  outline: 0;\n"
"}\n"
"QComboBox QAbstractItemView::item { min-height: 26px; }\n"
"\n"
"QAbstractSpinBox {\n"
"  background: #14171B;\n"
"  color: #E6E8EB;\n"
"  border: 1px solid #2A2F37;\n"
"  border-radius: 10px;\n"
"  padding: 6px 8px;\n"
"}\n"
"QAbstractSpinBox:focus { border-color: #2D7DFF; }\n"
"QSpinBox::up-button, QDoubleSpinBox::up-button {\n"
"  subcontrol-origin: border;\n"
"  subcontrol-position: top right;\n"
"  width: 22px;\n"
"  border-left: 1px solid #2A2F37;\n"
"  background: #1B1E23;\n"
"  border-top-right-radius: 10px;\n"
"}\n"
"QSpinBox::down-button, QDoubleSpinBox::down-button {\n"
"  subcontrol-origin: border;\n"
"  subcontrol-position: bottom right;\n"
"  width: 22px;\n"
"  border-left: 1px solid #2A2F37;\n"
"  background: #1B1E23;\n"
"  border-bottom-right-radius: 10px;\n"
"}\n"
"\n"
""
                        "QRadioButton::indicator {\n"
"  width: 16px; height: 16px;\n"
"  border: 1px solid #3A4049; border-radius: 8px; background: #14171B;\n"
"}\n"
"QRadioButton::indicator:checked {\n"
"  background: #2D7DFF; border-color: #2D7DFF;\n"
"}\n"
"\n"
"/* Frames et groupes */\n"
"QFrame[frameShape=\"4\"] {\n"
"  background: #16191D;\n"
"  border: 1px solid #2A2F37;\n"
"  border-radius: 12px;\n"
"}\n"
"\n"
"QGroupBox { \n"
"  border: 1px solid #2A2F37; \n"
"  border-radius: 10px; \n"
"  margin-top: 12px;\n"
"  padding-top: 8px;\n"
"}\n"
"QGroupBox::title { \n"
"  subcontrol-origin: margin; \n"
"  left: 12px; \n"
"  padding: 0 6px; \n"
"  background: transparent; \n"
"  color: #E6E8EB;\n"
"  font-weight: 600;\n"
"}\n"
"\n"
"/* Sidebar styling */\n"
"QScrollArea#sidebarScrollArea {\n"
"  background: #0F1113;\n"
"  border-right: 1px solid #2A2F37;\n"
"}\n"
"QScrollArea#sidebarScrollArea > QWidget {\n"
"  background: #0F1113;\n"
"}\n"
"\n"
"/* Main content area */\n"
"QScrollArea#dashboardScrollArea {\n"
"  background: #12141"
                        "7;\n"
"}\n"
"\n"
"\n"
"/* === Coverage: hidden widgets === */\n"
"QToolButton {\n"
"  background: palette(button);\n"
"  color: palette(text);\n"
"  border: 1px solid palette(mid);\n"
"  border-radius: 8px;\n"
"  padding: 6px 10px;\n"
"}\n"
"QToolButton:hover { background: palette(light); }\n"
"QToolButton:pressed, QToolButton:checked { background: palette(mid); }\n"
"QToolButton::menu-button { border: none; width: 16px; }\n"
"\n"
"QCommandLinkButton {\n"
"  background: palette(button);\n"
"  color: palette(text);\n"
"  border: 1px solid palette(mid);\n"
"  border-radius: 10px;\n"
"  padding: 8px 12px;\n"
"}\n"
"QCommandLinkButton:hover { background: palette(light); }\n"
"QCommandLinkButton:pressed { background: palette(mid); }\n"
"QCommandLinkButton:disabled { color: palette(mid); background: palette(window); border-color: palette(mid); }\n"
"\n"
"QToolBox::tab {\n"
"  background: palette(button);\n"
"  color: palette(text);\n"
"  border: 1px solid palette(mid);\n"
"  border-top-left-radius: 8px;\n"
"  border"
                        "-top-right-radius: 8px;\n"
"  padding: 6px 10px;\n"
"}\n"
"QToolBox::tab:selected { background: palette(base); }\n"
"QToolBox QWidget { background: palette(window); }\n"
"\n"
"QDockWidget {\n"
"  background: palette(window);\n"
"  border: 1px solid palette(mid);\n"
"}\n"
"QDockWidget::title {\n"
"  text-align: left;\n"
"  padding: 6px 10px;\n"
"  background: palette(base);\n"
"  color: palette(text);\n"
"  border-bottom: 1px solid palette(mid);\n"
"}\n"
"QDockWidget::close-button, QDockWidget::float-button {\n"
"  border: none;\n"
"  background: transparent;\n"
"  padding: 2px;\n"
"}\n"
"QDockWidget::close-button:hover, QDockWidget::float-button:hover {\n"
"  background: palette(light);\n"
"}\n"
"\n"
"QCalendarWidget {\n"
"  background: palette(base);\n"
"  border: 1px solid palette(mid);\n"
"  border-radius: 8px;\n"
"}\n"
"QCalendarWidget QWidget#qt_calendar_navigationbar {\n"
"  background: palette(button);\n"
"  border-bottom: 1px solid palette(mid);\n"
"}\n"
"QCalendarWidget QToolButton {\n"
"  background:"
                        " palette(button);\n"
"  color: palette(text);\n"
"  border: 1px solid palette(mid);\n"
"  border-radius: 6px;\n"
"  padding: 4px 8px;\n"
"}\n"
"QCalendarWidget QToolButton:hover { background: palette(light); }\n"
"QCalendarWidget QSpinBox { background: palette(base); border: 1px solid palette(mid); }\n"
"QCalendarWidget QAbstractItemView {\n"
"  background: palette(base);\n"
"  selection-background-color: palette(highlight);\n"
"  selection-color: palette(highlighted-text);\n"
"}\n"
"QCalendarWidget QAbstractItemView:disabled { color: palette(mid); }\n"
"\n"
"QDateEdit, QTimeEdit, QDateTimeEdit {\n"
"  background: palette(base);\n"
"  color: palette(text);\n"
"  border: 1px solid palette(mid);\n"
"  border-radius: 6px;\n"
"  padding: 4px 8px;\n"
"}\n"
"QDateEdit:focus, QTimeEdit:focus, QDateTimeEdit:focus { border-color: palette(highlight); }\n"
"\n"
"QSlider::groove:horizontal { height: 6px; background: palette(midlight); border-radius: 3px; }\n"
"QSlider::handle:horizontal { width: 16px; height: 16px; margin"
                        ": -5px 0; border-radius: 8px; background: palette(highlight); border: 1px solid palette(mid); }\n"
"QSlider::sub-page:horizontal { background: palette(highlight); border-radius: 3px; }\n"
"QSlider::add-page:horizontal { background: palette(midlight); border-radius: 3px; }\n"
"QSlider::groove:vertical { width: 6px; background: palette(midlight); border-radius: 3px; }\n"
"QSlider::handle:vertical { width: 16px; height: 16px; margin: 0 -5px; border-radius: 8px; background: palette(highlight); border: 1px solid palette(mid); }\n"
"QSlider::sub-page:vertical { background: palette(highlight); border-radius: 3px; }\n"
"QSlider::add-page:vertical { background: palette(midlight); border-radius: 3px; }\n"
"QSlider:disabled { color: palette(mid); }\n"
"\n"
"QLCDNumber {\n"
"  color: palette(highlight);\n"
"  background: palette(base);\n"
"  border: 1px solid palette(mid);\n"
"  border-radius: 6px;\n"
"  padding: 4px;\n"
"}\n"
"\n"
"QToolBar {\n"
"  background: palette(window);\n"
"  border-bottom: 1px solid palette(mid);"
                        "\n"
"  spacing: 6px;\n"
"}\n"
"QToolBar::separator { background: palette(mid); width: 1px; height: 1px; margin: 4px; }\n"
"\n"
"/* === Theme polish === */\n"
"QHeaderView::section {\n"
"  background: #1B1E23;\n"
"  color: #E6E8EB;\n"
"  border: 1px solid #2A2F37;\n"
"  padding: 6px 10px;\n"
"}\n"
"QHeaderView::section:hover { background: #232831; }\n"
"\n"
"QMenuBar {\n"
"  background: #16191D;\n"
"  color: #E6E8EB;\n"
"  border-bottom: 1px solid #2A2F37;\n"
"}\n"
"QMenuBar::item { padding: 6px 10px; background: transparent; border-radius: 8px; }\n"
"QMenuBar::item:selected { background: #232831; }\n"
"\n"
"QMenu {\n"
"  background: #14171B;\n"
"  color: #E6E8EB;\n"
"  border: 1px solid #2A2F37;\n"
"  border-radius: 10px;\n"
"}\n"
"QMenu::item { padding: 6px 12px; }\n"
"QMenu::item:selected { background: #203357; }\n"
"QMenu::separator { height: 1px; background: #2A2F37; margin: 6px 8px; }\n"
"\n"
"QStatusBar {\n"
"  background: #16191D;\n"
"  color: #878B93;\n"
"  border-top: 1px solid #2A2F37;\n"
"}\n"
"QSta"
                        "tusBar::item { border: none; }\n"
"\n"
"QListWidget::item:hover, QTreeWidget::item:hover, QTableView::item:hover {\n"
"  background: #203357;\n"
"}\n"
"")
        self.rootLayout = QVBoxLayout(PyCompilerARKGui)
        self.rootLayout.setSpacing(10)
        self.rootLayout.setObjectName(u"rootLayout")
        self.rootLayout.setContentsMargins(12, 12, 12, 12)
        self.header = QFrame(PyCompilerARKGui)
        self.header.setObjectName(u"header")
        self.header.setFrameShape(QFrame.Shape.StyledPanel)
        self.headerLayout = QHBoxLayout(self.header)
        self.headerLayout.setSpacing(10)
        self.headerLayout.setObjectName(u"headerLayout")
        self.headerLayout.setContentsMargins(10, 10, 10, 10)
        self.headerLeftLayout = QVBoxLayout()
        self.headerLeftLayout.setSpacing(2)
        self.headerLeftLayout.setObjectName(u"headerLeftLayout")
        self.headerLeftLayout.setContentsMargins(0, 0, 0, 0)
        self.label_app_title = QLabel(self.header)
        self.label_app_title.setObjectName(u"label_app_title")
        font = QFont()
        font.setFamilies([u"Segoe UI"])
        font.setPointSize(10)
        font.setBold(True)
        self.label_app_title.setFont(font)

        self.headerLeftLayout.addWidget(self.label_app_title)

        self.label_workspace_status = QLabel(self.header)
        self.label_workspace_status.setObjectName(u"label_workspace_status")

        self.headerLeftLayout.addWidget(self.label_workspace_status)


        self.headerLayout.addLayout(self.headerLeftLayout)

        self.headerSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.headerLayout.addItem(self.headerSpacer)

        self.headerRightLayout = QHBoxLayout()
        self.headerRightLayout.setSpacing(8)
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
        self.leftPanel = QWidget(self.mainSplitter)
        self.leftPanel.setObjectName(u"leftPanel")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.leftPanel.sizePolicy().hasHeightForWidth())
        self.leftPanel.setSizePolicy(sizePolicy)
        self.leftLayout = QVBoxLayout(self.leftPanel)
        self.leftLayout.setSpacing(18)
        self.leftLayout.setObjectName(u"leftLayout")
        self.leftLayout.setContentsMargins(10, 10, 10, 10)
        self.leftSplitter = QSplitter(self.leftPanel)
        self.leftSplitter.setObjectName(u"leftSplitter")
        self.leftSplitter.setOrientation(Qt.Orientation.Vertical)
        self.leftSplitter.setHandleWidth(8)
        self.frame_workspace = QFrame(self.leftSplitter)
        self.frame_workspace.setObjectName(u"frame_workspace")
        self.frame_workspace.setFrameShape(QFrame.Shape.StyledPanel)
        self.layout_workspace_grid = QGridLayout(self.frame_workspace)
        self.layout_workspace_grid.setSpacing(18)
        self.layout_workspace_grid.setObjectName(u"layout_workspace_grid")
        self.layout_workspace_grid.setContentsMargins(14, 14, 14, 14)
        self.label_workspace_section = QLabel(self.frame_workspace)
        self.label_workspace_section.setObjectName(u"label_workspace_section")
        font1 = QFont()
        font1.setFamilies([u"Segoe UI"])
        font1.setPointSize(12)
        font1.setWeight(QFont.DemiBold)
        self.label_workspace_section.setFont(font1)

        self.layout_workspace_grid.addWidget(self.label_workspace_section, 0, 0, 1, 2)

        self.label_folder = QLabel(self.frame_workspace)
        self.label_folder.setObjectName(u"label_folder")
        self.label_folder.setFont(font)
        self.label_folder.setFrameShape(QFrame.Shape.StyledPanel)
        self.label_folder.setFrameShadow(QFrame.Shadow.Sunken)
        self.label_folder.setWordWrap(True)
        self.label_folder.setMargin(6)

        self.layout_workspace_grid.addWidget(self.label_folder, 1, 0, 1, 2)

        self.venv_label = QLabel(self.frame_workspace)
        self.venv_label.setObjectName(u"venv_label")
        self.venv_label.setFont(font)
        self.venv_label.setFrameShape(QFrame.Shape.StyledPanel)
        self.venv_label.setFrameShadow(QFrame.Shadow.Sunken)
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
        self.layout_files_grid.setSpacing(18)
        self.layout_files_grid.setObjectName(u"layout_files_grid")
        self.layout_files_grid.setContentsMargins(14, 14, 14, 14)
        self.layout_file_actions = QVBoxLayout()
        self.layout_file_actions.setSpacing(12)
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
        self.label_files_section.setFont(font1)
        self.label_files_section.setWordWrap(True)

        self.layout_files_grid.addWidget(self.label_files_section, 0, 0, 1, 2)

        self.leftSplitter.addWidget(self.frame_files)
        self.frame_tools = QFrame(self.leftSplitter)
        self.frame_tools.setObjectName(u"frame_tools")
        self.frame_tools.setFrameShape(QFrame.Shape.StyledPanel)
        self.layout_tools_grid = QGridLayout(self.frame_tools)
        self.layout_tools_grid.setSpacing(18)
        self.layout_tools_grid.setObjectName(u"layout_tools_grid")
        self.layout_tools_grid.setContentsMargins(14, 14, 14, 14)
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
        font2 = QFont()
        font2.setFamilies([u"Segoe UI"])
        font2.setPointSize(11)
        font2.setWeight(QFont.DemiBold)
        self.label_tools.setFont(font2)

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
        self.rightLayout.setSpacing(16)
        self.rightLayout.setObjectName(u"rightLayout")
        self.rightLayout.setContentsMargins(6, 6, 6, 6)
        self.rightSplitter = QSplitter(self.rightPanel)
        self.rightSplitter.setObjectName(u"rightSplitter")
        self.rightSplitter.setOrientation(Qt.Orientation.Vertical)
        self.rightSplitter.setHandleWidth(8)
        self.frame_options = QFrame(self.rightSplitter)
        self.frame_options.setObjectName(u"frame_options")
        self.frame_options.setFrameShape(QFrame.Shape.StyledPanel)
        self.layout_options = QVBoxLayout(self.frame_options)
        self.layout_options.setSpacing(12)
        self.layout_options.setObjectName(u"layout_options")
        self.layout_options.setContentsMargins(10, 10, 10, 10)
        self.label_options_section = QLabel(self.frame_options)
        self.label_options_section.setObjectName(u"label_options_section")
        self.label_options_section.setFont(font1)

        self.layout_options.addWidget(self.label_options_section)

        self.compiler_tabs = QTabWidget(self.frame_options)
        self.compiler_tabs.setObjectName(u"compiler_tabs")

        self.layout_options.addWidget(self.compiler_tabs)

        self.rightSplitter.addWidget(self.frame_options)
        self.frame_logs = QFrame(self.rightSplitter)
        self.frame_logs.setObjectName(u"frame_logs")
        self.frame_logs.setFrameShape(QFrame.Shape.StyledPanel)
        self.layout_logs = QVBoxLayout(self.frame_logs)
        self.layout_logs.setSpacing(12)
        self.layout_logs.setObjectName(u"layout_logs")
        self.layout_logs.setContentsMargins(10, 10, 10, 10)
        self.label_logs_section = QLabel(self.frame_logs)
        self.label_logs_section.setObjectName(u"label_logs_section")
        self.label_logs_section.setFont(font1)

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
        self.layout_progress.setSpacing(8)
        self.layout_progress.setObjectName(u"layout_progress")
        self.layout_progress.setContentsMargins(10, 10, 10, 10)
        self.label_progress = QLabel(self.frame_progress)
        self.label_progress.setObjectName(u"label_progress")
        self.label_progress.setFont(font2)

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

