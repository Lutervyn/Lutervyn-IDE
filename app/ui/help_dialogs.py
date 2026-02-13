"""
Lutervyn IDE - Help Dialogs
Implements all Help menu features:
  - Welcome Tab (rich getting-started page)
  - Keyboard Shortcuts Reference
  - Release Notes viewer
  - Report Issue dialog
  - Developer Tools (log viewer)
"""

import sys
import os
import platform
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QTextEdit, QTextBrowser,
                              QTableWidget, QTableWidgetItem, QHeaderView,
                              QWidget, QScrollArea, QFrame, QSizePolicy,
                              QApplication, QLineEdit)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QUrl
from PyQt6.QtGui import QFont, QColor, QPainter, QPixmap, QIcon, QDesktopServices


# ─────────────────────────────────────────────
# Keyboard Shortcuts Dialog
# ─────────────────────────────────────────────

class KeyboardShortcutsDialog(QDialog):
    """Shows all keyboard shortcuts in a searchable table."""

    SHORTCUTS = [
        # Category, Shortcut, Description
        ("General", "Ctrl+Shift+P", "Command Palette"),
        ("General", "Ctrl+,", "Preferences"),
        ("General", "F11", "Toggle Full Screen"),

        ("File", "Ctrl+N", "New File"),
        ("File", "Ctrl+O", "Open File"),
        ("File", "Ctrl+K", "Open Folder"),
        ("File", "Ctrl+S", "Save"),
        ("File", "Ctrl+Shift+S", "Save As"),
        ("File", "Ctrl+W", "Close Editor"),

        ("Edit", "Ctrl+Z", "Undo"),
        ("Edit", "Ctrl+Y", "Redo"),
        ("Edit", "Ctrl+X", "Cut"),
        ("Edit", "Ctrl+C", "Copy"),
        ("Edit", "Ctrl+V", "Paste"),
        ("Edit", "Ctrl+A", "Select All"),
        ("Edit", "Ctrl+F", "Find"),
        ("Edit", "Ctrl+H", "Replace"),
        ("Edit", "Ctrl+Shift+F", "Find in Files"),

        ("View", "Ctrl+B", "Toggle Sidebar"),
        ("View", "Ctrl+J", "Toggle Panel"),
        ("View", "Ctrl+`", "Toggle Terminal"),
        ("View", "Ctrl+Shift+E", "Explorer"),
        ("View", "Ctrl+Shift+F", "Search"),
        ("View", "Ctrl+Shift+G", "Source Control"),
        ("View", "Ctrl+Shift+D", "Run and Debug"),
        ("View", "Ctrl+Shift+X", "Extensions"),
        ("View", "Ctrl+Shift+M", "Problems"),
        ("View", "Ctrl+Shift+U", "Output"),

        ("Navigation", "Ctrl+P", "Go to File"),
        ("Navigation", "Ctrl+G", "Go to Line"),
        ("Navigation", "F12", "Go to Definition"),
        ("Navigation", "Shift+F12", "Go to References"),
        ("Navigation", "Alt+Left", "Navigate Back"),
        ("Navigation", "Alt+Right", "Navigate Forward"),

        ("Run", "F5", "Start Debugging"),
        ("Run", "Ctrl+F5", "Run Without Debugging"),
        ("Run", "Shift+F5", "Stop Debugging"),
        ("Run", "Ctrl+Shift+F5", "Restart Debugging"),
        ("Run", "F9", "Toggle Breakpoint"),

        ("Terminal", "Ctrl+Shift+`", "New Terminal"),

        ("Selection", "Shift+Alt+Up", "Copy Line Up"),
        ("Selection", "Shift+Alt+Down", "Copy Line Down"),
        ("Selection", "Alt+Up", "Move Line Up"),
        ("Selection", "Alt+Down", "Move Line Down"),
    ]

    def __init__(self, theme: dict, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.setWindowTitle("Keyboard Shortcuts")
        self.setMinimumSize(650, 500)
        self.resize(700, 550)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {theme['bg_dark']};
                color: {theme['text_primary']};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Title
        title = QLabel("Keyboard Shortcuts Reference")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {theme['text_primary']};")
        layout.addWidget(title)

        # Search box
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Type to search shortcuts...")
        self.search_box.setFont(QFont("Segoe UI", 12))
        self.search_box.setStyleSheet(f"""
            QLineEdit {{
                background-color: {theme['bg_medium']};
                color: {theme['text_primary']};
                border: 1px solid {theme['border']};
                padding: 8px 12px;
                border-radius: 4px;
            }}
            QLineEdit:focus {{
                border-color: {theme['accent']};
            }}
        """)
        self.search_box.textChanged.connect(self._filter)
        layout.addWidget(self.search_box)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Category", "Shortcut", "Command"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {theme['bg_medium']};
                color: {theme['text_primary']};
                border: 1px solid {theme['border']};
                gridline-color: {theme['border']};
            }}
            QTableWidget::item {{
                padding: 4px 8px;
            }}
            QTableWidget::item:selected {{
                background-color: {theme['bg_active']};
            }}
            QHeaderView::section {{
                background-color: {theme['bg_dark']};
                color: {theme['text_secondary']};
                padding: 6px 8px;
                border: 1px solid {theme['border']};
                font-weight: bold;
            }}
        """)
        layout.addWidget(self.table)

        self._populate()

    def _populate(self, filter_text=""):
        self.table.setRowCount(0)
        ft = filter_text.lower()
        for cat, shortcut, desc in self.SHORTCUTS:
            if ft and ft not in cat.lower() and ft not in shortcut.lower() and ft not in desc.lower():
                continue
            row = self.table.rowCount()
            self.table.insertRow(row)

            cat_item = QTableWidgetItem(cat)
            cat_item.setForeground(QColor(self.theme['text_disabled']))
            self.table.setItem(row, 0, cat_item)

            key_item = QTableWidgetItem(shortcut)
            key_item.setFont(QFont("Cascadia Code", 10))
            key_item.setForeground(QColor(self.theme['accent']))
            self.table.setItem(row, 1, key_item)

            desc_item = QTableWidgetItem(desc)
            self.table.setItem(row, 2, desc_item)

    def _filter(self, text):
        self._populate(text)


# ─────────────────────────────────────────────
# Release Notes Dialog
# ─────────────────────────────────────────────

class ReleaseNotesDialog(QDialog):
    """Shows release notes / changelog."""

    def __init__(self, theme: dict, version: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Release Notes — Lutervyn IDE {version}")
        self.setMinimumSize(600, 450)
        self.resize(650, 500)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {theme['bg_dark']};
                color: {theme['text_primary']};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setFont(QFont("Segoe UI", 11))
        browser.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {theme['bg_medium']};
                color: {theme['text_primary']};
                border: 1px solid {theme['border']};
                padding: 12px;
            }}
        """)
        browser.setHtml(f"""
        <h1 style="color: {theme['accent']};">Lutervyn IDE {version}</h1>
        <p style="color: {theme['text_secondary']};">Release Notes</p>
        <hr style="border-color: {theme['border']};">

        <h2 style="color: {theme['text_primary']};">✨ What's New</h2>
        <ul>
            <li><b>Custom Title Bar</b> — VS Code-style frameless window with integrated menus,
                logo, and window controls (minimize / maximize / close).</li>
            <li><b>Context Menu Integration</b> — Right-click any file or folder in
                Windows Explorer → "Open with Lutervyn IDE".</li>
            <li><b>Activity Bar</b> — Quick access to Explorer, Search, Source Control,
                Debug, and Extensions panels.</li>
            <li><b>Integrated Terminal</b> — Built-in PowerShell terminal with output capture.</li>
            <li><b>Python Runner</b> — Run Python scripts directly with F5 and see output in the panel.</li>
            <li><b>Command Palette</b> — Ctrl+Shift+P to access all commands quickly.</li>
            <li><b>Syntax Highlighting</b> — QScintilla-powered editor with support for
                Python, JavaScript, HTML, CSS, JSON, Markdown, YAML, SQL, XML, and more.</li>
            <li><b>Code Folding</b> — Collapse and expand code blocks.</li>
            <li><b>Dark &amp; Light Themes</b> — Toggle between dark and light modes.</li>
        </ul>

        <h2 style="color: {theme['text_primary']};">🐛 Known Issues</h2>
        <ul>
            <li>Debugger not yet implemented (planned for v1.1).</li>
            <li>Extensions system is a placeholder (planned for v1.2).</li>
            <li>Git integration is visual only (planned for v1.1).</li>
        </ul>

        <h2 style="color: {theme['text_primary']};">🗺️ Roadmap</h2>
        <ul>
            <li><b>v1.1</b> — Python debugger (pdb integration), basic Git operations.</li>
            <li><b>v1.2</b> — Extensions API, plugin marketplace.</li>
            <li><b>v1.3</b> — LSP support for multi-language intellisense.</li>
            <li><b>v2.0</b> — Remote development, collaborative editing.</li>
        </ul>

        <hr style="border-color: {theme['border']};">
        <p style="color: {theme['text_disabled']}; font-size: 10px;">
            Built with Python + PyQt6 + QScintilla
        </p>
        """)
        layout.addWidget(browser)

        close_btn = QPushButton("Close")
        close_btn.setFixedWidth(100)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme['accent']};
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {theme['accent_hover']};
            }}
        """)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)


# ─────────────────────────────────────────────
# Report Issue Dialog
# ─────────────────────────────────────────────

class ReportIssueDialog(QDialog):
    """Collects system info and lets the user describe a bug or feature request."""

    def __init__(self, theme: dict, version: str, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.setWindowTitle("Report Issue — Lutervyn IDE")
        self.setMinimumSize(550, 450)
        self.resize(600, 500)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {theme['bg_dark']};
                color: {theme['text_primary']};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("Report an Issue")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {theme['text_primary']};")
        layout.addWidget(title)

        # System info
        sysinfo = self._get_system_info(version)
        info_label = QLabel("System Information (auto-collected):")
        info_label.setFont(QFont("Segoe UI", 10))
        info_label.setStyleSheet(f"color: {theme['text_secondary']};")
        layout.addWidget(info_label)

        info_box = QTextEdit()
        info_box.setPlainText(sysinfo)
        info_box.setReadOnly(True)
        info_box.setMaximumHeight(100)
        info_box.setFont(QFont("Cascadia Code", 10))
        info_box.setStyleSheet(f"""
            QTextEdit {{
                background-color: {theme['bg_medium']};
                color: {theme['text_primary']};
                border: 1px solid {theme['border']};
                padding: 8px;
            }}
        """)
        layout.addWidget(info_box)

        # Description
        desc_label = QLabel("Describe the issue:")
        desc_label.setFont(QFont("Segoe UI", 10))
        desc_label.setStyleSheet(f"color: {theme['text_secondary']};")
        layout.addWidget(desc_label)

        self.desc_box = QTextEdit()
        self.desc_box.setPlaceholderText(
            "Steps to reproduce:\n1. ...\n2. ...\n\nExpected behavior:\n...\n\nActual behavior:\n...")
        self.desc_box.setFont(QFont("Segoe UI", 11))
        self.desc_box.setStyleSheet(f"""
            QTextEdit {{
                background-color: {theme['bg_medium']};
                color: {theme['text_primary']};
                border: 1px solid {theme['border']};
                padding: 8px;
            }}
            QTextEdit:focus {{
                border-color: {theme['accent']};
            }}
        """)
        layout.addWidget(self.desc_box)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        copy_btn = QPushButton("Copy to Clipboard")
        copy_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme['bg_medium']};
                color: {theme['text_primary']};
                border: 1px solid {theme['border']};
                padding: 8px 16px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {theme['bg_hover']};
            }}
        """)
        copy_btn.clicked.connect(lambda: self._copy_report(sysinfo))
        btn_row.addWidget(copy_btn)

        close_btn = QPushButton("Close")
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme['accent']};
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {theme['accent_hover']};
            }}
        """)
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)

        layout.addLayout(btn_row)

    def _get_system_info(self, version):
        try:
            from PyQt6.QtCore import PYQT_VERSION_STR, QT_VERSION_STR
            pyqt_ver = PYQT_VERSION_STR
            qt_ver = QT_VERSION_STR
        except Exception:
            pyqt_ver = "unknown"
            qt_ver = "unknown"

        return (
            f"Lutervyn IDE:  {version}\n"
            f"Python:        {sys.version.split()[0]}\n"
            f"PyQt6:         {pyqt_ver}\n"
            f"Qt:            {qt_ver}\n"
            f"OS:            {platform.system()} {platform.release()} ({platform.machine()})\n"
            f"Platform:      {platform.platform()}"
        )

    def _copy_report(self, sysinfo):
        report = f"## Issue Report\n\n### System Info\n```\n{sysinfo}\n```\n\n"
        report += f"### Description\n{self.desc_box.toPlainText()}\n"
        clipboard = QApplication.clipboard()
        clipboard.setText(report)


# ─────────────────────────────────────────────
# Developer Tools (Log Viewer)
# ─────────────────────────────────────────────

class DeveloperToolsDialog(QDialog):
    """Simple log viewer / developer console."""

    def __init__(self, theme: dict, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.setWindowTitle("Developer Tools — Lutervyn IDE")
        self.setMinimumSize(600, 400)
        self.resize(700, 450)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {theme['bg_dark']};
                color: {theme['text_primary']};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        title = QLabel("Developer Tools")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {theme['text_primary']};")
        layout.addWidget(title)

        # Python info
        info = QLabel(
            f"Python {sys.version} | PyQt6 | Platform: {platform.platform()}")
        info.setFont(QFont("Cascadia Code", 9))
        info.setStyleSheet(f"color: {theme['text_disabled']};")
        info.setWordWrap(True)
        layout.addWidget(info)

        # Console
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setFont(QFont("Cascadia Code", 11))
        self.console.setStyleSheet(f"""
            QTextEdit {{
                background-color: #0c0c0c;
                color: #cccccc;
                border: 1px solid {theme['border']};
                padding: 8px;
            }}
        """)
        self.console.setPlainText(
            f"Lutervyn IDE Developer Console\n"
            f"{'='*45}\n"
            f"Python:    {sys.executable}\n"
            f"Version:   {sys.version}\n"
            f"Platform:  {platform.platform()}\n"
            f"CWD:       {os.getcwd()}\n"
            f"PID:       {os.getpid()}\n"
            f"{'='*45}\n\n"
            f"Modules loaded: {len(sys.modules)}\n"
            f"Paths:\n" + "\n".join(f"  {p}" for p in sys.path[:10]) + "\n"
        )
        layout.addWidget(self.console)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        copy_btn = QPushButton("Copy Log")
        copy_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme['bg_medium']};
                color: {theme['text_primary']};
                border: 1px solid {theme['border']};
                padding: 6px 14px;
                border-radius: 4px;
            }}
            QPushButton:hover {{ background-color: {theme['bg_hover']}; }}
        """)
        copy_btn.clicked.connect(
            lambda: QApplication.clipboard().setText(self.console.toPlainText()))
        btn_row.addWidget(copy_btn)

        close_btn = QPushButton("Close")
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme['accent']};
                color: white;
                border: none;
                padding: 6px 14px;
                border-radius: 4px;
            }}
            QPushButton:hover {{ background-color: {theme['accent_hover']}; }}
        """)
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)

        layout.addLayout(btn_row)


# ─────────────────────────────────────────────
# Interactive Welcome Tab (rich version)
# ─────────────────────────────────────────────

class WelcomePageTab(QWidget):
    """Rich welcome page with logo, getting started, tips, and quick links."""

    # Signals to trigger commands in the main window
    action_requested = pyqtSignal(str)

    def __init__(self, theme: dict, version: str, parent=None):
        super().__init__(parent)
        self.theme = theme

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"background-color: {theme['editor_bg']}; border: none;")

        content = QWidget()
        main_layout = QVBoxLayout(content)
        main_layout.setContentsMargins(60, 40, 60, 40)
        main_layout.setSpacing(20)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # ── Logo + Title ──
        header = QHBoxLayout()
        header.setAlignment(Qt.AlignmentFlag.AlignLeft)

        logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)))), "assets", "logo.png")
        if os.path.exists(logo_path):
            logo_label = QLabel()
            pixmap = QPixmap(logo_path).scaled(
                48, 48, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(pixmap)
            logo_label.setStyleSheet("background: transparent;")
            header.addWidget(logo_label)

        title_col = QVBoxLayout()
        t = QLabel("Lutervyn IDE")
        t.setFont(QFont("Segoe UI", 26, QFont.Weight.Light))
        t.setStyleSheet(f"color: {theme['text_primary']}; background: transparent;")
        title_col.addWidget(t)

        sub = QLabel(f"Version {version} — Python Development Environment")
        sub.setFont(QFont("Segoe UI", 11))
        sub.setStyleSheet(f"color: {theme['text_disabled']}; background: transparent;")
        title_col.addWidget(sub)

        header.addLayout(title_col)
        main_layout.addLayout(header)

        # ── Separator ──
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {theme['border']};")
        main_layout.addWidget(sep)

        # ── Two Column Layout ──
        columns = QHBoxLayout()
        columns.setSpacing(40)

        # Left column: Start
        left = QVBoxLayout()
        left.setSpacing(8)

        start_title = QLabel("Start")
        start_title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        start_title.setStyleSheet(f"color: {theme['text_primary']}; background: transparent;")
        left.addWidget(start_title)

        start_links = [
            ("📄  New File", "file.new"),
            ("📂  Open File...", "file.open"),
            ("📁  Open Folder...", "file.open_folder"),
        ]
        for label_text, cmd_id in start_links:
            btn = self._make_link_button(label_text, cmd_id, theme)
            left.addWidget(btn)

        left.addSpacing(20)

        recent_title = QLabel("Help")
        recent_title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        recent_title.setStyleSheet(f"color: {theme['text_primary']}; background: transparent;")
        left.addWidget(recent_title)

        help_links = [
            ("📖  Documentation", "help.docs"),
            ("📋  Release Notes", "help.release_notes"),
            ("⌨️  Keyboard Shortcuts", "help.shortcuts"),
            ("🐛  Report Issue", "help.report_issue"),
        ]
        for label_text, cmd_id in help_links:
            btn = self._make_link_button(label_text, cmd_id, theme)
            left.addWidget(btn)

        left.addStretch()
        columns.addLayout(left)

        # Right column: Shortcuts
        right = QVBoxLayout()
        right.setSpacing(8)

        keys_title = QLabel("Keyboard Shortcuts")
        keys_title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        keys_title.setStyleSheet(f"color: {theme['text_primary']}; background: transparent;")
        right.addWidget(keys_title)

        shortcuts = [
            ("Ctrl+Shift+P", "Command Palette"),
            ("Ctrl+N", "New File"),
            ("Ctrl+O", "Open File"),
            ("Ctrl+S", "Save"),
            ("Ctrl+Shift+F", "Search in Files"),
            ("Ctrl+`", "Toggle Terminal"),
            ("F5", "Run Script"),
            ("Ctrl+B", "Toggle Sidebar"),
            ("Ctrl+J", "Toggle Panel"),
            ("F11", "Full Screen"),
        ]
        for key, desc in shortcuts:
            row = QHBoxLayout()
            row.setSpacing(10)

            key_label = QLabel(key)
            key_label.setFont(QFont("Cascadia Code", 10))
            key_label.setFixedWidth(150)
            key_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            key_label.setStyleSheet(f"""
                color: {theme['accent']};
                background-color: {theme['bg_medium']};
                padding: 4px 8px;
                border-radius: 3px;
                border: 1px solid {theme['border']};
            """)

            desc_label = QLabel(desc)
            desc_label.setFont(QFont("Segoe UI", 11))
            desc_label.setStyleSheet(f"color: {theme['text_secondary']}; background: transparent;")

            row.addWidget(key_label)
            row.addWidget(desc_label)
            row.addStretch()
            right.addLayout(row)

        right.addStretch()
        columns.addLayout(right)

        main_layout.addLayout(columns)
        main_layout.addStretch()

        scroll.setWidget(content)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _make_link_button(self, text, cmd_id, theme):
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFlat(True)
        btn.setFont(QFont("Segoe UI", 12))
        btn.setStyleSheet(f"""
            QPushButton {{
                color: {theme['accent']};
                text-align: left;
                padding: 4px 8px;
                border: none;
                background: transparent;
            }}
            QPushButton:hover {{
                color: {theme['accent_hover']};
                text-decoration: underline;
            }}
        """)
        btn.clicked.connect(lambda: self.action_requested.emit(cmd_id))
        return btn

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(self.theme['editor_bg']))
        p.end()
