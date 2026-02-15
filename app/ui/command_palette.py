"""
Command Palette - Quick command/file search, like VS Code.
  • No prefix  → search files  (Ctrl+P behaviour)
  • '>' prefix → search commands (Ctrl+Shift+P behaviour)
"""

import os

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLineEdit, QListWidget,
                              QListWidgetItem, QGraphicsDropShadowEffect,
                              QWidget, QStyledItemDelegate, QStyle)
from PyQt6.QtCore import pyqtSignal, Qt, QEvent, QRect, QSize
from PyQt6.QtGui import QFont, QColor, QKeyEvent, QPainter, QFontMetrics, QPen


# Item types stored in UserRole + 2
ITEM_TYPE_COMMAND = 0
ITEM_TYPE_FILE = 1


class _PaletteDelegate(QStyledItemDelegate):
    """Custom delegate – paints file rows (name + path) and command rows
    (label + shortcut badge) exactly like VS Code."""

    def __init__(self, theme: dict, parent=None):
        super().__init__(parent)
        self.theme = theme
        self._label_font = QFont("Segoe UI", 11)
        self._detail_font = QFont("Segoe UI", 9)
        self._key_font = QFont("Cascadia Code", 9)

    # ── paint ────────────────────────────────────────────────
    def paint(self, painter: QPainter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = option.rect
        is_selected = option.state & QStyle.StateFlag.State_Selected
        is_hover = option.state & QStyle.StateFlag.State_MouseOver

        # Background
        if is_selected:
            painter.fillRect(rect, QColor(self.theme['bg_active']))
        elif is_hover:
            painter.fillRect(rect, QColor(self.theme['bg_hover']))

        label = index.data(Qt.ItemDataRole.DisplayRole) or ""
        shortcut = index.data(Qt.ItemDataRole.UserRole + 1) or ""
        item_type = index.data(Qt.ItemDataRole.UserRole + 2)
        if item_type is None:
            item_type = ITEM_TYPE_COMMAND
        detail = index.data(Qt.ItemDataRole.UserRole + 3) or ""

        text_color = QColor(self.theme['text_bright'] if is_selected
                            else self.theme['text_primary'])

        left_x = rect.x() + 14

        if item_type == ITEM_TYPE_FILE:
            # ── File row: "filename   folder/path" ──
            label_fm = QFontMetrics(self._label_font)
            detail_fm = QFontMetrics(self._detail_font)

            label_w = label_fm.horizontalAdvance(label)
            gap = 10  # space between filename and path

            # filename (bright)
            painter.setFont(self._label_font)
            painter.setPen(text_color)
            label_rect = QRect(left_x, rect.y(), label_w, rect.height())
            painter.drawText(label_rect,
                             Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                             label)

            # folder path (dim, right of filename)
            if detail:
                painter.setFont(self._detail_font)
                painter.setPen(QColor(self.theme['text_disabled']))
                path_x = left_x + label_w + gap
                avail_w = rect.right() - path_x - 14
                if avail_w > 30:
                    elided = detail_fm.elidedText(
                        detail, Qt.TextElideMode.ElideMiddle, avail_w)
                    path_rect = QRect(path_x, rect.y(), avail_w, rect.height())
                    painter.drawText(path_rect,
                                     Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                                     elided)
        else:
            # ── Command row: "Label          [Shortcut]" ──
            right_content_w = 0
            if shortcut:
                key_fm = QFontMetrics(self._key_font)
                right_content_w = key_fm.horizontalAdvance(shortcut) + 26

            label_rect = QRect(left_x, rect.y(),
                               rect.width() - 28 - right_content_w, rect.height())
            painter.setFont(self._label_font)
            painter.setPen(text_color)
            painter.drawText(label_rect,
                             Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                             label)

            if shortcut:
                key_fm = QFontMetrics(self._key_font)
                key_w = key_fm.horizontalAdvance(shortcut) + 14
                key_h = key_fm.height() + 6
                key_x = rect.right() - key_w - 14
                key_y = rect.y() + (rect.height() - key_h) // 2
                badge_rect = QRect(key_x, key_y, key_w, key_h)

                painter.setPen(QPen(QColor(self.theme['border'])))
                painter.setBrush(QColor(self.theme['bg_medium']))
                painter.drawRoundedRect(badge_rect, 3, 3)

                painter.setFont(self._key_font)
                painter.setPen(QColor(self.theme['text_secondary']))
                painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, shortcut)

        painter.restore()

    def sizeHint(self, option, index):
        return QSize(0, 34)


# ═══════════════════════════════════════════════════════════
#  CommandPalette
# ═══════════════════════════════════════════════════════════
class CommandPalette(QDialog):
    """VS Code-style palette.

    • Empty / text without '>' → file search  (like Ctrl+P)
    • Text starting with '>'  → command search (like Ctrl+Shift+P)
    """

    command_selected = pyqtSignal(str)  # "file:/abs/path" or command-id

    _SKIP_DIRS = {'.git', '__pycache__', 'node_modules', '.venv', 'venv',
                  '.idea', '.vs', '.vscode', 'dist', 'build', '.mypy_cache',
                  '.pytest_cache', 'env', '.eggs', '*.egg-info'}

    def __init__(self, theme: dict, commands: list, parent=None,
                 workspace_folder: str = None, *,
                 start_in_command_mode: bool = False):
        super().__init__(parent)
        self.theme = theme
        self._workspace_folder = workspace_folder
        self._start_in_command_mode = start_in_command_mode

        # Normalize commands: (id, label[, shortcut])
        self.all_commands = []
        for cmd in commands:
            if len(cmd) >= 3:
                self.all_commands.append((cmd[0], cmd[1], cmd[2]))
            else:
                self.all_commands.append((cmd[0], cmd[1], ""))

        # Pre-scan workspace files
        self._file_cache: list = []
        if workspace_folder and os.path.isdir(workspace_folder):
            self._file_cache = self._scan_files(workspace_folder)

        # ── Window chrome ────────────────────────────────
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Popup)
        self.setFixedWidth(620)
        self.setMaximumHeight(420)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        container = QWidget()
        container.setObjectName("Container")
        container.setStyleSheet(f"""
            QWidget#Container {{
                background-color: {theme['bg_dark']};
                border: 1px solid {theme['border']};
                border-radius: 12px;
            }}
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setOffset(0, 4)
        container.setGraphicsEffect(shadow)
        main_layout.addWidget(container)

        self.layout = QVBoxLayout(container)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # ── Search input ─────────────────────────────────
        self.input = QLineEdit()
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

        # ── Results list ─────────────────────────────────
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
                border-radius: 6px;
                margin: 1px 4px;
            }}
        """)
        self.results.setItemDelegate(_PaletteDelegate(theme, self.results))
        self.results.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.results.itemClicked.connect(self._on_select)
        self.layout.addWidget(self.results)

    # ── file scanning ────────────────────────────────────
    def _scan_files(self, folder: str, max_files: int = 2000) -> list:
        """Return [(filename, rel_path, abs_path), ...]"""
        files = []
        for root, dirs, filenames in os.walk(folder):
            dirs[:] = [d for d in dirs if d not in self._SKIP_DIRS
                       and not d.startswith('.')]
            for fn in filenames:
                abs_path = os.path.join(root, fn)
                rel_path = os.path.relpath(abs_path, folder)
                files.append((fn, rel_path, abs_path))
                if len(files) >= max_files:
                    return files
        return files

    # ── populate helpers ─────────────────────────────────
    def _populate_commands(self, commands: list):
        for cmd_id, label, shortcut in commands:
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, cmd_id)
            item.setData(Qt.ItemDataRole.UserRole + 1, shortcut)
            item.setData(Qt.ItemDataRole.UserRole + 2, ITEM_TYPE_COMMAND)
            item.setData(Qt.ItemDataRole.UserRole + 3, "")
            self.results.addItem(item)

    def _populate_files(self, files: list):
        for fn, rel_path, abs_path in files:
            rel_dir = os.path.dirname(rel_path)
            item = QListWidgetItem(fn)
            item.setData(Qt.ItemDataRole.UserRole, f"file:{abs_path}")
            item.setData(Qt.ItemDataRole.UserRole + 1, "")
            item.setData(Qt.ItemDataRole.UserRole + 2, ITEM_TYPE_FILE)
            item.setData(Qt.ItemDataRole.UserRole + 3, rel_dir if rel_dir else ".")
            self.results.addItem(item)

    # ── core filter ──────────────────────────────────────
    def _filter(self, text: str):
        self.results.clear()
        raw = text.strip()

        if raw.startswith(">"):
            # ── COMMAND MODE (like Ctrl+Shift+P) ─────────
            query = raw[1:].strip().lower()
            if query:
                matched = [c for c in self.all_commands
                           if query in c[1].lower()]
            else:
                matched = self.all_commands
            self._populate_commands(matched)
        else:
            # ── FILE MODE (like Ctrl+P) ──────────────────
            query = raw.lower()
            if query:
                matched = []
                for fn, rel_path, abs_path in self._file_cache:
                    if query in fn.lower() or query in rel_path.lower():
                        matched.append((fn, rel_path, abs_path))
                    if len(matched) >= 30:
                        break
                self._populate_files(matched)
            else:
                # Empty input → show all files (up to 50)
                self._populate_files(self._file_cache[:50])

        if self.results.count() > 0:
            self.results.setCurrentRow(0)

    # ── selection ────────────────────────────────────────
    def _on_select(self, item: QListWidgetItem):
        cmd_id = item.data(Qt.ItemDataRole.UserRole)
        self.command_selected.emit(cmd_id)
        self.accept()

    # ── keyboard nav ─────────────────────────────────────
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

    # ── show ─────────────────────────────────────────────
    def showEvent(self, event):
        self.input.setFocus()
        if self._start_in_command_mode:
            self.input.setText(">")
            self.input.setPlaceholderText("Type a command...")
        else:
            self.input.clear()
            self.input.setPlaceholderText(
                "Search files by name (type > for commands)")
        self._filter(self.input.text())
        super().showEvent(event)
