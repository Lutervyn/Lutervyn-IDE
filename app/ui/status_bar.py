"""
Status Bar - The bar at the very bottom of the IDE (like VS Code).
Shows: branch info, line/col, encoding, language, indent, notifications.
"""

from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QLabel, QSizePolicy,
                              QPushButton)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont, QColor, QPainter, QMouseEvent


class StatusBarItem(QLabel):
    """A clickable item in the status bar."""

    clicked = pyqtSignal()

    def __init__(self, text: str, theme: dict, parent=None):
        super().__init__(text, parent)
        self.theme = theme
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QLabel {{
                color: {theme['statusbar_fg']};
                padding: 0px 8px;
                font-size: 12px;
                background: transparent;
            }}
            QLabel:hover {{
                background-color: {theme['statusbar_hover_bg']};
            }}
        """)

    def mousePressEvent(self, event: QMouseEvent):
        self.clicked.emit()


class StatusBar(QWidget):
    """Bottom status bar of the IDE."""

    def __init__(self, theme: dict, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.setFixedHeight(24)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Left side
        # Branch info
        self.branch_item = StatusBarItem("⎇ main", theme, self)
        layout.addWidget(self.branch_item)

        # Errors / Warnings
        self.problems_item = StatusBarItem("❌ 0  ⚠ 0", theme, self)
        layout.addWidget(self.problems_item)

        # Spacer
        layout.addStretch()

        # Right side
        # Line : Column
        self.position_item = StatusBarItem("Ln 1, Col 1", theme, self)
        layout.addWidget(self.position_item)

        # Spaces
        self.indent_item = StatusBarItem("Spaces: 4", theme, self)
        layout.addWidget(self.indent_item)

        # Encoding
        self.encoding_item = StatusBarItem("UTF-8", theme, self)
        layout.addWidget(self.encoding_item)

        # EOL
        self.eol_item = StatusBarItem("CRLF", theme, self)
        layout.addWidget(self.eol_item)

        # Language
        self.language_item = StatusBarItem("Python", theme, self)
        layout.addWidget(self.language_item)

        # Notifications bell
        self.notification_item = StatusBarItem("🔔", theme, self)
        layout.addWidget(self.notification_item)

    def update_position(self, line: int, col: int):
        self.position_item.setText(f"Ln {line}, Col {col}")

    def update_language(self, lang: str):
        self.language_item.setText(lang)

    def update_encoding(self, enc: str):
        self.encoding_item.setText(enc)

    def update_branch(self, branch: str):
        self.branch_item.setText(f"⎇ {branch}")

    def update_problems(self, errors: int, warnings: int):
        self.problems_item.setText(f"❌ {errors}  ⚠ {warnings}")

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(self.theme['statusbar_bg']))
        p.end()
