"""
Command Palette - Quick command search (Ctrl+Shift+P), like VS Code.
Centered, rounded, and modern.
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLineEdit, QListWidget,
                              QListWidgetItem, QGraphicsDropShadowEffect,
                              QWidget)
from PyQt6.QtCore import pyqtSignal, Qt, QEvent
from PyQt6.QtGui import QFont, QColor, QKeyEvent


class CommandPalette(QDialog):
    """A floating command palette for quick actions."""

    command_selected = pyqtSignal(str)  # Emits command id

    def __init__(self, theme: dict, commands: list[tuple[str, str]], parent=None):
        super().__init__(parent)
        self.theme = theme
        self.all_commands = commands

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Popup)
        self.setFixedWidth(600)
        self.setMaximumHeight(400)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground) # For rounded corners

        # Main layout with shadow container
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10) # Margin for shadow

        container = QWidget()
        container.setObjectName("Container")
        container.setStyleSheet(f"""
            QWidget#Container {{
                background-color: {theme['bg_dark']};
                border: 1px solid {theme['border']};
                border-radius: 12px;
            }}
        """)
        
        # Add shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setOffset(0, 4)
        container.setGraphicsEffect(shadow)
        
        main_layout.addWidget(container)

        self.layout = QVBoxLayout(container)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # Search input
        self.input = QLineEdit()
        self.input.setPlaceholderText("Type a command...")
        self.input.setFont(QFont("Segoe UI", 12)) 
        self.input.setAttribute(Qt.WidgetAttribute.WA_MacShowFocusRect, 0)
        self.input.setStyleSheet(f"""
            QLineEdit {{
                background-color: transparent;
                color: {theme['text_primary']};
                border: none;
                border-bottom: 1px solid {theme['border']};
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
                padding: 14px 16px;
                font-size: 14px;
            }}
        """)
        self.input.textChanged.connect(self._filter)
        self.input.installEventFilter(self)
        self.layout.addWidget(self.input)

        # Results list
        self.results = QListWidget()
        self.results.setStyleSheet(f"""
            QListWidget {{
                background-color: transparent;
                border: none;
                outline: none;
                border-bottom-left-radius: 12px;
                border-bottom-right-radius: 12px;
                padding: 4px;
            }}
            QListWidget::item {{
                padding: 8px 12px;
                border-radius: 6px;
                margin: 2px 4px;
                color: {theme['text_primary']};
            }}
            QListWidget::item:selected {{
                background-color: {theme['bg_active']};
                color: {theme['text_bright']};
            }}
            QListWidget::item:hover:!selected {{
                background-color: {theme['bg_hover']};
            }}
        """)
        self.results.setFont(QFont("Segoe UI", 11))
        self.results.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.results.itemClicked.connect(self._on_select)
        self.layout.addWidget(self.results)

        self._populate(commands)

    def _populate(self, commands: list[tuple[str, str]]):
        self.results.clear()
        for cmd_id, label in commands:
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, cmd_id)
            self.results.addItem(item)
        if self.results.count() > 0:
            self.results.setCurrentRow(0)

    def _filter(self, text: str):
        text = text.lower().strip()
        if not text:
            self._populate(self.all_commands)
            return
        filtered = [(cid, lbl) for cid, lbl in self.all_commands
                     if text in lbl.lower()]
        self._populate(filtered)

    def _on_select(self, item: QListWidgetItem):
        cmd_id = item.data(Qt.ItemDataRole.UserRole)
        self.command_selected.emit(cmd_id)
        self.accept()

    def eventFilter(self, obj, event):
        if obj == self.input and isinstance(event, QKeyEvent):
            if event.key() == Qt.Key.Key_Down:
                row = self.results.currentRow()
                if row < self.results.count() - 1:
                    self.results.setCurrentRow(row + 1)
                return True
            elif event.key() == Qt.Key.Key_Up:
                row = self.results.currentRow()
                if row > 0:
                    self.results.setCurrentRow(row - 1)
                return True
            elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                item = self.results.currentItem()
                if item:
                    self._on_select(item)
                return True
            elif event.key() == Qt.Key.Key_Escape:
                self.reject()
                return True
        return super().eventFilter(obj, event)

    def showEvent(self, event):
        self.input.setFocus()
        self.input.clear()
        self._populate(self.all_commands)
        if self.results.count() > 0:
            self.results.setCurrentRow(0)
        super().showEvent(event)
