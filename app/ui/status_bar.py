"""
Status Bar - The bar at the very bottom of the IDE (like VS Code).
Shows: branch info, line/col, encoding, language, indent, notifications.

The problems counter uses VS Code exact colors:
  Error = #f14c4c (red)   Warning = #cca700 (yellow)
"""

import os
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QLabel, QSizePolicy,
                              QPushButton)
from PyQt6.QtCore import pyqtSignal, Qt, QSize
from PyQt6.QtGui import QFont, QColor, QPainter, QMouseEvent, QIcon


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
                padding: 0px 10px;
                font-size: 11px;
                background: transparent;
                border-right: 1px solid {theme.get('bg_light', '#333333')};
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

        # Errors / Warnings  (VS Code uses coloured icons)
        self._icons_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "assets", "icons"
        )
        self.problems_widget = QWidget()
        self.problems_widget.setCursor(Qt.CursorShape.PointingHandCursor)
        pw_layout = QHBoxLayout(self.problems_widget)
        pw_layout.setContentsMargins(8, 0, 8, 0)
        pw_layout.setSpacing(3)

        # Error icon + count
        err_icon_path = os.path.join(self._icons_dir, "problem_error.svg")
        self.err_icon_label = QLabel()
        if os.path.exists(err_icon_path):
            self.err_icon_label.setPixmap(QIcon(err_icon_path).pixmap(QSize(12, 12)))
        else:
            self.err_icon_label.setText("✕")
            self.err_icon_label.setStyleSheet("color: #f14c4c; font-size: 11px;")
        self.err_icon_label.setFixedSize(14, 14)
        pw_layout.addWidget(self.err_icon_label)

        self.err_count_label = QLabel("0")
        self.err_count_label.setStyleSheet(f"color: {theme['statusbar_fg']}; font-size: 11px; background: transparent;")
        pw_layout.addWidget(self.err_count_label)

        pw_layout.addSpacing(4)

        # Warning icon + count
        warn_icon_path = os.path.join(self._icons_dir, "problem_warning.svg")
        self.warn_icon_label = QLabel()
        if os.path.exists(warn_icon_path):
            self.warn_icon_label.setPixmap(QIcon(warn_icon_path).pixmap(QSize(12, 12)))
        else:
            self.warn_icon_label.setText("⚠")
            self.warn_icon_label.setStyleSheet("color: #cca700; font-size: 11px;")
        self.warn_icon_label.setFixedSize(14, 14)
        pw_layout.addWidget(self.warn_icon_label)

        self.warn_count_label = QLabel("0")
        self.warn_count_label.setStyleSheet(f"color: {theme['statusbar_fg']}; font-size: 11px; background: transparent;")
        pw_layout.addWidget(self.warn_count_label)

        self.problems_widget.setStyleSheet(f"""
            QWidget {{
                background: transparent;
                border-right: 1px solid {theme.get('bg_light', '#333333')};
            }}
            QWidget:hover {{
                background-color: {theme['statusbar_hover_bg']};
            }}
        """)
        layout.addWidget(self.problems_widget)

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
        self.err_count_label.setText(str(errors))
        self.warn_count_label.setText(str(warnings))

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(self.theme['statusbar_bg']))
        
        # Top border to separate from terminal
        p.setPen(QColor(self.theme.get('bg_light', '#3a3a3c')))
        p.drawLine(0, 0, self.width(), 0)
        p.end()
