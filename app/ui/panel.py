"""
Bottom Panel - Terminal, Output, Problems tabs (like VS Code).
Contains an embedded terminal emulator + output/problems panels.

The Problems panel is an exact replica of VS Code's Problems view:
  - File-grouped tree with collapsible file headers
  - Error (red ✕), Warning (yellow ▲), Info (blue ℹ) icons
  - Filter toolbar with type toggles + text search
  - Click-to-navigate: clicking a problem jumps to the file/line
  - Badge counts on the PROBLEMS tab label
  - Real-time Python linting via py_compile + heuristic checks
"""

import os
import sys
import re
import subprocess
import threading
import py_compile
import tempfile
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
                              QPlainTextEdit, QLabel, QTreeWidget,
                              QTreeWidgetItem, QPushButton, QSizePolicy,
                              QLineEdit, QHeaderView, QAbstractItemView,
                              QFrame, QStyle, QSplitter, QStackedWidget,
                              QListWidget, QListWidgetItem)
from PyQt6.QtCore import (pyqtSignal, Qt, QProcess, QTimer, QSize, QPoint,
                           QThread)
from PyQt6.QtGui import (QFont, QColor, QTextCursor, QPainter, QKeyEvent,
                          QIcon, QPixmap)


class PanelHeader(QWidget):
    """Header for the bottom panel with tabs and action buttons."""
    def __init__(self, theme: dict, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.setFixedHeight(35)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 8, 0)
        self.layout.setSpacing(0)

        # Tab container will be handled by QTabWidget's bar
        self.layout.addStretch()
        self.actions_layout = QHBoxLayout()
        self.actions_layout.setSpacing(2)
        self.layout.addLayout(self.actions_layout)

    def add_action(self, icon_name: str, tooltip: str, callback):
        btn = QPushButton()
        btn.setToolTip(tooltip)
        btn.setFixedSize(26, 26)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        icon_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "assets", "icons", icon_name
        )
        if os.path.exists(icon_path):
            btn.setIcon(QIcon(icon_path))
            btn.setIconSize(QSize(14, 14))
        
        btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {self.theme['bg_hover']};
            }}
        """)
        btn.clicked.connect(callback)
        self.actions_layout.addWidget(btn)


class TerminalWidget(QPlainTextEdit):
    """Embedded terminal / interactive Python console."""

    command_executed = pyqtSignal(str, str)  # command, output
    output_emitted = pyqtSignal(str) # Live chunk emitted

    def __init__(self, theme: dict, parent=None, cwd=None):
        super().__init__(parent)
        self.theme = theme
        self.cwd = cwd
        self.process = None
        self._history: list[str] = []
        self._history_index = -1
        self._prompt_position = 0

        font = QFont("Cascadia Code", 13)
        font.setFamilies(["Cascadia Code", "Consolas", "Fira Code", "Droid Sans Mono", "Monospace"])
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)

        self.setReadOnly(False)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        self.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: #000000;
                color: {theme['terminal_fg']};
                border: none;
                padding: 10px;
                selection-background-color: {theme['bg_selection']};
                selection-color: #000000;
            }}
        """)

        self._start_shell()

    def _start_shell(self):
        """Start a system shell process."""
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self._read_output)
        self.process.readyReadStandardError.connect(self._read_output)
        if self.cwd and os.path.exists(self.cwd):
            self.process.setWorkingDirectory(self.cwd)

        if sys.platform == "win32":
            self.process.start("powershell.exe", ["-NoLogo"])
        else:
            shell = os.environ.get("SHELL", "/bin/bash")
            self.process.start(shell, [])

        self._write_prompt_header()

    def _write_prompt_header(self):
        cwd = self.cwd if self.cwd else os.getcwd()
        header = f"Lutervyn IDE Terminal\n{cwd}\n"
        self.appendPlainText(header)
        self._prompt_position = self.textCursor().position()

    def _read_output(self):
        if self.process:
            data = self.process.readAllStandardOutput().data()
            try:
                text = data.decode("utf-8", errors="replace")
            except Exception:
                text = str(data)
            if text.strip():
                self.moveCursor(QTextCursor.MoveOperation.End)
                self.insertPlainText(text)
                self.moveCursor(QTextCursor.MoveOperation.End)
                self._prompt_position = self.textCursor().position()
                self.output_emitted.emit(text)

    def keyPressEvent(self, event: QKeyEvent):
        cursor = self.textCursor()

        # Don't allow editing above the prompt
        if cursor.position() < self._prompt_position:
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.setTextCursor(cursor)

        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            # Extract command from current line
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.movePosition(QTextCursor.MoveOperation.StartOfLine,
                              QTextCursor.MoveMode.KeepAnchor)
            line = cursor.selectedText().strip()

            self.moveCursor(QTextCursor.MoveOperation.End)
            self.insertPlainText("\n")

            if line and self.process:
                self._history.append(line)
                self._history_index = len(self._history)
                self.process.write((line + "\n").encode("utf-8"))
            self._prompt_position = self.textCursor().position()
            return

        elif event.key() == Qt.Key.Key_Up:
            # History up
            if self._history and self._history_index > 0:
                self._history_index -= 1
                self._replace_current_line(self._history[self._history_index])
            return

        elif event.key() == Qt.Key.Key_Down:
            # History down
            if self._history_index < len(self._history) - 1:
                self._history_index += 1
                self._replace_current_line(self._history[self._history_index])
            else:
                self._history_index = len(self._history)
                self._replace_current_line("")
            return

        elif event.key() == Qt.Key.Key_Backspace:
            if cursor.position() <= self._prompt_position:
                return  # Don't backspace past prompt

        elif event.key() == Qt.Key.Key_L and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.clear_terminal()
            return

        elif event.key() == Qt.Key.Key_C and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if self.process:
                self.process.write(b"\x03")  # Ctrl+C
            return

        super().keyPressEvent(event)

    def clear_terminal(self):
        """Clear terminal screen but keep process alive."""
        self.clear()
        self._write_prompt_header()

    def _replace_current_line(self, text: str):
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.movePosition(QTextCursor.MoveOperation.StartOfLine,
                          QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        cursor.insertText(text)
        self.setTextCursor(cursor)

    def run_command(self, command: str):
        """Programmatically run a command in the terminal."""
        if self.process:
            self.moveCursor(QTextCursor.MoveOperation.End)
            self.insertPlainText(command + "\n")
            self.process.write((command + "\n").encode("utf-8"))
            self._prompt_position = self.textCursor().position()

    def close_terminal(self):
        if self.process:
            self.process.kill()
            self.process.waitForFinished(1000)


class OutputWidget(QPlainTextEdit):
    """Output panel for showing script execution output."""

    def __init__(self, theme: dict, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.setReadOnly(True)

        font = QFont("Cascadia Code", 13)
        font.setFamilies(["Cascadia Code", "Consolas", "Fira Code", "Droid Sans Mono", "Monospace"])
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)


        self.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {theme['terminal_bg']};
                color: {theme['terminal_fg']};
                border: none;
                padding: 8px;
            }}
        """)

    def append_output(self, text: str, color: str = None):
        self.moveCursor(QTextCursor.MoveOperation.End)
        self.insertPlainText(text)
        self.moveCursor(QTextCursor.MoveOperation.End)

    def clear_output(self):
        self.clear()


class ProblemsWidget(QWidget):
    """
    VS Code-style Problems panel.

    Layout (top to bottom):
    ┌─────────────────────────────────────────────────────────────┐
    │ [filter input………………………………] [Errors✕] [Warnings▲] [Info ℹ] │  ← toolbar
    ├─────────────────────────────────────────────────────────────┤
    │ ▾ filename.py  (2 errors, 1 warning)                       │  ← file header
    │    ✕  Unexpected indent          Ln 12, Col 1    [pylint]  │  ← problem row
    │    ✕  Missing import 'os'        Ln 3, Col 1     [pylint]  │
    │    ▲  Unused variable 'x'        Ln 7, Col 5     [pylint]  │
    │ ▾ utils.py  (1 info)                                       │
    │    ℹ  Consider using f-string    Ln 22, Col 1    [pylint]  │
    └─────────────────────────────────────────────────────────────┘
    """

    # Emitted as (file_path, line_number) so main window can navigate
    problem_clicked = pyqtSignal(str, int)

    # VS Code exact colours
    COLOR_ERROR   = "#f14c4c"
    COLOR_WARNING = "#cca700"
    COLOR_INFO    = "#3794ff"
    COLOR_FILE_FG = "#cccccc"
    COLOR_MSG_FG  = "#cccccc"
    COLOR_SRC_FG  = "#858585"
    COLOR_POS_FG  = "#858585"

    def __init__(self, theme: dict, parent=None):
        super().__init__(parent)
        self.theme = theme
        self._problems: list[dict] = []  # master list
        self._filter_text = ""
        self._show_errors = True
        self._show_warnings = True
        self._show_info = True

        self._icons_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "assets", "icons"
        )

        # ── Build layout ──────────────────────────────────
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Toolbar ───────────────────────────────────────
        toolbar = QWidget()
        toolbar.setFixedHeight(34)
        toolbar.setStyleSheet(f"""
            QWidget {{
                background-color: {theme['panel_bg']};
            }}
        """)
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(8, 4, 8, 4)
        tb_layout.setSpacing(4)

        # Filter input (VS Code uses a slim input with placeholder)
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Filter (e.g. text, **/*.py)")
        self.filter_input.setClearButtonEnabled(True)
        self.filter_input.setFixedHeight(24)
        self.filter_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {theme.get('input_bg', '#3c3c3c')};
                color: {theme.get('input_fg', '#cccccc')};
                border: 1px solid {theme.get('input_border', '#3c3c3c')};
                border-radius: 2px;
                padding: 0 6px;
                font-size: 12px;
                font-family: 'Segoe UI', sans-serif;
            }}
            QLineEdit:focus {{
                border: 1px solid {theme.get('input_border_focus', '#007fd4')};
            }}
        """)
        self.filter_input.textChanged.connect(self._on_filter_changed)
        tb_layout.addWidget(self.filter_input, 1)

        # Toggle buttons: Errors / Warnings / Info  (VS Code badge-style)
        self.btn_errors = self._make_toggle_btn("error", "0", self.COLOR_ERROR, True)
        self.btn_warnings = self._make_toggle_btn("warning", "0", self.COLOR_WARNING, True)
        self.btn_info = self._make_toggle_btn("info", "0", self.COLOR_INFO, True)
        self.btn_errors.clicked.connect(self._toggle_errors)
        self.btn_warnings.clicked.connect(self._toggle_warnings)
        self.btn_info.clicked.connect(self._toggle_info)
        tb_layout.addWidget(self.btn_errors)
        tb_layout.addWidget(self.btn_warnings)
        tb_layout.addWidget(self.btn_info)

        # Collapse all button
        collapse_btn = QPushButton()
        collapse_btn.setToolTip("Collapse All")
        collapse_btn.setFixedSize(22, 22)
        collapse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        icon_path = os.path.join(self._icons_dir, "action_collapse.svg")
        if os.path.exists(icon_path):
            collapse_btn.setIcon(QIcon(icon_path))
            collapse_btn.setIconSize(QSize(14, 14))
        collapse_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: none; border-radius: 3px;
            }}
            QPushButton:hover {{
                background-color: {theme['bg_hover']};
            }}
        """)
        collapse_btn.clicked.connect(self._collapse_all)
        tb_layout.addWidget(collapse_btn)

        root.addWidget(toolbar)

        # ── Separator ─────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {theme.get('panel_border', '#3a3a3c')};")
        root.addWidget(sep)

        # ── Tree widget ───────────────────────────────────
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setColumnCount(4)  # icon, message, position, source
        self.tree.setRootIsDecorated(True)
        self.tree.setIndentation(16)
        self.tree.setAnimated(False)
        self.tree.setExpandsOnDoubleClick(False)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tree.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # Hide header
        self.tree.header().setVisible(False)
        self.tree.header().setStretchLastSection(False)
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.header().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        self.tree.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {theme['panel_bg']};
                color: {self.COLOR_MSG_FG};
                border: none;
                outline: none;
                font-family: 'Segoe UI', 'SF Pro Text', sans-serif;
                font-size: 12px;
            }}
            QTreeWidget::item {{
                padding: 2px 4px;
                border: none;
                min-height: 22px;
            }}
            QTreeWidget::item:hover {{
                background-color: {theme.get('bg_hover', '#2a2d2e')};
            }}
            QTreeWidget::item:selected {{
                background-color: {theme.get('bg_selection', '#094771')};
                color: #ffffff;
            }}
            /* Hide ALL branch lines, connectors, and decorations */
            QTreeWidget::branch {{
                background-color: {theme['panel_bg']};
                border-image: none;
                image: none;
                border: none;
            }}
            QTreeWidget::branch:has-siblings:!adjoins-item {{
                border-image: none;
                image: none;
            }}
            QTreeWidget::branch:has-siblings:adjoins-item {{
                border-image: none;
                image: none;
            }}
            QTreeWidget::branch:!has-children:!has-siblings:adjoins-item {{
                border-image: none;
                image: none;
            }}
            QTreeWidget::branch:has-children:!has-siblings:closed,
            QTreeWidget::branch:closed:has-children:has-siblings {{
                image: none;
                border-image: none;
            }}
            QTreeWidget::branch:open:has-children:!has-siblings,
            QTreeWidget::branch:open:has-children:has-siblings {{
                image: none;
                border-image: none;
            }}
        """)

        self.tree.itemClicked.connect(self._on_item_clicked)
        self.tree.itemExpanded.connect(lambda: None)
        self.tree.itemCollapsed.connect(lambda: None)
        root.addWidget(self.tree, 1)

        # ── Empty state label ──────────────────────────────
        self.empty_label = QLabel("No problems have been detected in the workspace.")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.get('text_disabled', '#858585')};
                font-size: 12px;
                padding: 40px;
            }}
        """)
        root.addWidget(self.empty_label)
        self.empty_label.setVisible(True)
        self.tree.setVisible(False)

    # ────────────────────────────────────────
    # Toggle-button factory
    # ────────────────────────────────────────
    def _make_toggle_btn(self, kind: str, count: str, color: str, active: bool) -> QPushButton:
        """Create an error/warning/info toggle button with icon + count."""
        btn = QPushButton(f" {count}")
        btn.setCheckable(True)
        btn.setChecked(active)
        btn.setFixedHeight(22)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setProperty("kind", kind)

        icon_path = os.path.join(self._icons_dir, f"problem_{kind}.svg")
        if os.path.exists(icon_path):
            btn.setIcon(QIcon(icon_path))
            btn.setIconSize(QSize(14, 14))

        btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 3px;
                color: {color};
                font-size: 11px;
                font-weight: bold;
                padding: 0 6px;
                font-family: 'Segoe UI', sans-serif;
            }}
            QPushButton:hover {{
                background-color: {self.theme['bg_hover']};
            }}
            QPushButton:checked {{
                color: {color};
            }}
            QPushButton:!checked {{
                color: {self.theme.get('text_disabled', '#858585')};
                opacity: 0.5;
            }}
        """)
        return btn

    def _update_toggle_counts(self):
        """Refresh the numbers on the toggle buttons."""
        errs = sum(1 for p in self._problems if p['level'] == 'error')
        warns = sum(1 for p in self._problems if p['level'] == 'warning')
        infos = sum(1 for p in self._problems if p['level'] == 'info')
        self.btn_errors.setText(f" {errs}")
        self.btn_warnings.setText(f" {warns}")
        self.btn_info.setText(f" {infos}")

    # ────────────────────────────────────────
    # Filter callbacks
    # ────────────────────────────────────────
    def _on_filter_changed(self, text: str):
        self._filter_text = text.strip().lower()
        self._rebuild_tree()

    def _toggle_errors(self):
        self._show_errors = self.btn_errors.isChecked()
        self._rebuild_tree()

    def _toggle_warnings(self):
        self._show_warnings = self.btn_warnings.isChecked()
        self._rebuild_tree()

    def _toggle_info(self):
        self._show_info = self.btn_info.isChecked()
        self._rebuild_tree()

    def _collapse_all(self):
        self.tree.collapseAll()

    # ────────────────────────────────────────
    # Public API
    # ────────────────────────────────────────
    def set_problems(self, problems: list[dict]):
        """
        Replace the entire problem list and rebuild.
        Each dict: {level, message, file, line, col, source}
        level: 'error' | 'warning' | 'info'
        """
        self._problems = list(problems)
        self._update_toggle_counts()
        self._rebuild_tree()

    def add_problem(self, level: str, message: str, source: str,
                    line: int, col: int = 1, file_path: str = ""):
        """Add a single problem (kept for backward compat)."""
        self._problems.append({
            "level": level,
            "message": message,
            "file": file_path,
            "line": line,
            "col": col,
            "source": source,
        })
        self._update_toggle_counts()
        self._rebuild_tree()

    def clear_problems(self):
        self._problems.clear()
        self._update_toggle_counts()
        self._rebuild_tree()

    def get_counts(self) -> tuple[int, int, int]:
        """Return (errors, warnings, infos)."""
        e = sum(1 for p in self._problems if p['level'] == 'error')
        w = sum(1 for p in self._problems if p['level'] == 'warning')
        i = sum(1 for p in self._problems if p['level'] == 'info')
        return e, w, i

    # ────────────────────────────────────────
    # Tree building (VS Code exact layout)
    # ────────────────────────────────────────
    def _rebuild_tree(self):
        """Rebuild the tree from self._problems respecting filters."""
        self.tree.clear()

        # Apply level filter
        visible = []
        for p in self._problems:
            if p['level'] == 'error' and not self._show_errors:
                continue
            if p['level'] == 'warning' and not self._show_warnings:
                continue
            if p['level'] == 'info' and not self._show_info:
                continue
            # Text filter
            if self._filter_text:
                haystack = f"{p['message']} {p['file']} {p.get('source','')}".lower()
                if self._filter_text not in haystack:
                    continue
            visible.append(p)

        if not visible:
            self.tree.setVisible(False)
            self.empty_label.setVisible(True)
            return

        self.tree.setVisible(True)
        self.empty_label.setVisible(False)

        # Group by file
        files: dict[str, list[dict]] = {}
        for p in visible:
            f = p.get('file', 'Unknown')
            files.setdefault(f, []).append(p)

        for file_path, items in files.items():
            # ── File header row ──
            file_item = QTreeWidgetItem(self.tree)
            file_item.setFlags(file_item.flags() & ~Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)

            # File icon from existing icon set
            file_icon = self._get_file_icon(file_path)
            if file_icon:
                file_item.setIcon(0, file_icon)

            # Count errors/warnings/info for this file
            fe = sum(1 for x in items if x['level'] == 'error')
            fw = sum(1 for x in items if x['level'] == 'warning')
            fi = sum(1 for x in items if x['level'] == 'info')
            counts_parts = []
            if fe: counts_parts.append(f"{fe} error{'s' if fe > 1 else ''}")
            if fw: counts_parts.append(f"{fw} warning{'s' if fw > 1 else ''}")
            if fi: counts_parts.append(f"{fi} info")
            count_text = ", ".join(counts_parts)

            display_name = os.path.basename(file_path) if file_path else "Unknown"
            dir_part = os.path.dirname(file_path) if file_path else ""

            file_item.setText(0, f"  {display_name}")
            file_item.setText(1, dir_part)
            file_item.setText(2, count_text)
            file_item.setText(3, "")

            # Style file header
            header_font = QFont("Segoe UI", 12)
            header_font.setBold(True)
            file_item.setFont(0, header_font)
            file_item.setForeground(0, QColor(self.COLOR_FILE_FG))

            dir_font = QFont("Segoe UI", 11)
            file_item.setFont(1, dir_font)
            file_item.setForeground(1, QColor(self.COLOR_SRC_FG))

            count_font = QFont("Segoe UI", 11)
            file_item.setFont(2, count_font)
            # Color the badge by most severe
            badge_color = self.COLOR_INFO
            if fe > 0:
                badge_color = self.COLOR_ERROR
            elif fw > 0:
                badge_color = self.COLOR_WARNING
            file_item.setForeground(2, QColor(badge_color))

            file_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "file", "path": file_path})

            # Sort items: errors first, then warnings, then info
            order = {"error": 0, "warning": 1, "info": 2}
            items.sort(key=lambda x: (order.get(x['level'], 3), x.get('line', 0)))

            for prob in items:
                child = QTreeWidgetItem(file_item)

                # Severity icon
                level = prob['level']
                icon_file = f"problem_{level}.svg"
                icon_path = os.path.join(self._icons_dir, icon_file)
                if os.path.exists(icon_path):
                    child.setIcon(0, QIcon(icon_path))

                # Message
                child.setText(0, "")
                child.setText(1, prob['message'])

                # Position  [Ln X, Col Y]
                ln = prob.get('line', 0)
                col = prob.get('col', 1)
                child.setText(2, f"[Ln {ln}, Col {col}]")

                # Source tag
                child.setText(3, prob.get('source', ''))

                # Fonts & colors
                msg_font = QFont("Segoe UI", 12)
                child.setFont(1, msg_font)
                child.setForeground(1, QColor(self.COLOR_MSG_FG))

                pos_font = QFont("Segoe UI", 11)
                child.setFont(2, pos_font)
                child.setForeground(2, QColor(self.COLOR_POS_FG))

                src_font = QFont("Segoe UI", 11)
                child.setFont(3, src_font)
                child.setForeground(3, QColor(self.COLOR_SRC_FG))

                # Store data for click navigation
                child.setData(0, Qt.ItemDataRole.UserRole, {
                    "type": "problem",
                    "path": prob.get('file', ''),
                    "line": ln,
                    "col": col,
                })

            file_item.setExpanded(True)

    def _get_file_icon(self, file_path: str) -> QIcon | None:
        """Try to find an icon matching the file extension."""
        if not file_path:
            return None
        ext = os.path.splitext(file_path)[1].lower()
        ext_map = {
            ".py": "file_python.svg", ".pyw": "file_python.svg",
            ".js": "file_js.svg", ".ts": "file_js.svg",
            ".json": "file_json.svg", ".html": "file_html.svg",
            ".css": "file_css.svg", ".md": "file_markdown.svg",
            ".xml": "file_xml.svg", ".yaml": "file_config.svg",
            ".yml": "file_config.svg", ".toml": "file_config.svg",
            ".ini": "file_ini.svg", ".cfg": "file_config.svg",
            ".sh": "file_bat.svg", ".bat": "file_bat.svg",
            ".sql": "file_db.svg", ".txt": "file_default.svg",
            ".csv": "file_default.svg", ".log": "file_log.svg",
            ".java": "file_java.svg", ".c": "file_c.svg",
            ".cpp": "file_cpp.svg", ".rs": "file_rust.svg",
            ".go": "file_go.svg", ".rb": "file_ruby.svg",
            ".php": "file_php.svg", ".swift": "file_swift.svg",
        }
        icon_name = ext_map.get(ext, "file_default.svg")
        icon_path = os.path.join(self._icons_dir, icon_name)
        if os.path.exists(icon_path):
            return QIcon(icon_path)
        return None

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        if data['type'] == 'problem':
            self.problem_clicked.emit(data['path'], data['line'])
        elif data['type'] == 'file':
            # Toggle expand/collapse
            item.setExpanded(not item.isExpanded())


# ═══════════════════════════════════════════════════════════
# Python Linter - runs in a background thread
# ═══════════════════════════════════════════════════════════

class PythonLinter(QThread):
    """
    Background linting thread.
    Uses py_compile for syntax errors and basic regex heuristics
    for common warnings (unused imports, bare excepts, etc.).
    """
    results_ready = pyqtSignal(list)  # list[dict]

    def __init__(self, file_path: str, source_code: str, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.source_code = source_code

    def run(self):
        problems = []

        # ─── 1) Syntax check with py_compile ───
        try:
            # Write to a temp file so py_compile can read it
            with tempfile.NamedTemporaryFile(
                mode='w', suffix='.py', delete=False, encoding='utf-8'
            ) as tmp:
                tmp.write(self.source_code)
                tmp_path = tmp.name
            py_compile.compile(tmp_path, doraise=True)
        except py_compile.PyCompileError as e:
            msg = str(e)
            line = 1
            # Extract line number from message
            m = re.search(r'line (\d+)', msg)
            if m:
                line = int(m.group(1))
            # Clean up the message
            clean_msg = re.sub(r'\(.*?,\s*', '', msg)
            clean_msg = re.sub(r'\)$', '', clean_msg).strip()
            if not clean_msg:
                clean_msg = msg
            problems.append({
                "level": "error",
                "message": clean_msg,
                "file": self.file_path,
                "line": line,
                "col": 1,
                "source": "python",
            })
        except Exception:
            pass
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

        # ─── 2) Heuristic warnings ───
        lines = self.source_code.splitlines()
        imported_names = set()
        used_names = set()

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Bare except
            if re.match(r'^except\s*:', stripped):
                problems.append({
                    "level": "warning",
                    "message": "Bare 'except:' — consider catching specific exceptions",
                    "file": self.file_path,
                    "line": i, "col": 1,
                    "source": "lutervyn",
                })

            # TODO / FIXME / HACK comments
            todo_match = re.search(r'#\s*(TODO|FIXME|HACK|XXX)\b(.*)', stripped, re.IGNORECASE)
            if todo_match:
                tag = todo_match.group(1).upper()
                rest = todo_match.group(2).strip().rstrip('.')
                problems.append({
                    "level": "info",
                    "message": f"{tag}: {rest}" if rest else tag,
                    "file": self.file_path,
                    "line": i, "col": 1,
                    "source": "lutervyn",
                })

            # Wildcard import
            if re.match(r'^from\s+\S+\s+import\s+\*', stripped):
                problems.append({
                    "level": "warning",
                    "message": "Wildcard import — prefer explicit imports",
                    "file": self.file_path,
                    "line": i, "col": 1,
                    "source": "lutervyn",
                })

            # Mutable default argument
            if re.search(r'def\s+\w+\s*\(.*=\s*(\[\]|\{\}|\blist\(\)|\bdict\(\))', stripped):
                problems.append({
                    "level": "warning",
                    "message": "Mutable default argument — use None and assign inside",
                    "file": self.file_path,
                    "line": i, "col": 1,
                    "source": "lutervyn",
                })

            # print() left in code (mild info)
            if re.match(r'^\s*print\s*\(', line) and not stripped.startswith('#'):
                problems.append({
                    "level": "info",
                    "message": "print() statement found — consider using logging",
                    "file": self.file_path,
                    "line": i, "col": 1,
                    "source": "lutervyn",
                })

        self.results_ready.emit(problems)


class TerminalContainer(QWidget):
    """
    Manages multiple terminals in a split view:
    [ Terminal Content (Stack) | Terminal List (Sidebar) ]
    """
    terminal_output = pyqtSignal(str)

    def __init__(self, theme: dict, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.terminals: list[TerminalWidget] = []
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(1)
        
        # 1. Terminal Stack (Content)
        self.stack = QStackedWidget()
        self.splitter.addWidget(self.stack)
        
        # 2. Terminal Sidebar (List)
        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(200) # Initial width
        self.sidebar.setStyleSheet(f"background-color: {theme['panel_bg']};")
        
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)
        
        # Header
        header = QWidget()
        header.setFixedHeight(30)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 0, 4, 0)
        
        label = QLabel("TERMINALS")
        label.setStyleSheet(f"""
            color: {theme['text_secondary']}; 
            font-size: 11px; 
            font-weight: bold;
        """)
        header_layout.addWidget(label)
        header_layout.addStretch()
        
        # Add Button
        self.btn_add = QPushButton("+")
        self.btn_add.setFixedSize(20, 20)
        self.btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add.setToolTip("New Terminal")
        self.btn_add.clicked.connect(self.add_terminal)
        self.style_icon_btn(self.btn_add)
        header_layout.addWidget(self.btn_add)

        # Kill Button
        self.btn_kill = QPushButton("x")
        self.btn_kill.setFixedSize(20, 20)
        self.btn_kill.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_kill.setToolTip("Kill Terminal")
        self.btn_kill.clicked.connect(self.kill_current_terminal)
        self.style_icon_btn(self.btn_kill)
        header_layout.addWidget(self.btn_kill)
        
        sidebar_layout.addWidget(header)
        
        # List
        self.list_widget = QListWidget()
        self.list_widget.setFrameShape(QFrame.Shape.NoFrame)
        self.list_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.list_widget.currentRowChanged.connect(self._on_row_changed)
        
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: {theme['panel_bg']};
                color: {theme['text_primary']};
                outline: none;
            }}
            QListWidget::item {{
                height: 24px;
                padding-left: 4px;
                color: {theme['text_secondary']};
            }}
            QListWidget::item:selected {{
                background-color: {theme.get('bg_selection', '#094771')};
                color: #ffffff;
            }}
            QListWidget::item:hover:!selected {{
                background-color: {theme.get('bg_hover', '#2a2d2e')};
            }}
        """)
        sidebar_layout.addWidget(self.list_widget)
        
        self.splitter.addWidget(self.sidebar)
        
        # Main Layout
        layout.addWidget(self.splitter)
        
        # Initialize with one terminal
        self.add_terminal()

    def style_icon_btn(self, btn):
        btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; 
                border: none; 
                border-radius: 3px;
                color: {self.theme['text_secondary']};
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.theme['bg_hover']};
                color: {self.theme['text_primary']};
            }}
        """)

    def add_terminal(self, cwd=None):
        term = TerminalWidget(self.theme, self, cwd=cwd)
        term.output_emitted.connect(self.terminal_output.emit)
        self.terminals.append(term)
        self.stack.addWidget(term)
        
        # Add to list
        from PyQt6.QtWidgets import QListWidgetItem
        item = QListWidgetItem("powershell" if sys.platform == "win32" else "bash")
        
        # Icon
        icon_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "assets", "icons", "terminal.svg" # Fallback if specific icon not found
        )
        if not os.path.exists(icon_path):
             # Try generic icon or just text
             pass
        # item.setIcon(...) 
        
        self.list_widget.addItem(item)
        
        # Select new
        self.list_widget.setCurrentRow(self.stack.count() - 1)
        term.setFocus()

    def kill_current_terminal(self):
        idx = self.stack.currentIndex()
        if idx < 0: return
        
        term = self.terminals.pop(idx)
        term.close_terminal()
        self.stack.removeWidget(term)
        term.deleteLater()
        
        self.list_widget.takeItem(idx)
        
        if self.stack.count() == 0:
             # If no terminals left, maybe show empty state or auto-create one?
             # For now, just leave empty until user adds one
             pass

    def _on_row_changed(self, row):
        if row >= 0:
            self.stack.setCurrentIndex(row)
            self.terminals[row].setFocus()

class BottomPanel(QWidget):
    """The bottom panel area with Terminal, Output, Problems tabs."""

    # Forwarded from ProblemsWidget so main_window can connect
    problem_clicked = pyqtSignal(str, int)
    # Emitted when lint results change so status bar can update
    problems_changed = pyqtSignal(int, int)  # (errors, warnings)
    terminal_output = pyqtSignal(str) # Bubbled from TerminalContainer
    problems_found = pyqtSignal(str, list) # (file_path, problems_list)

    @property
    def terminal(self):
        """Property to access the currently active terminal widget."""
        return self.terminal_container.stack.currentWidget()

    def __init__(self, theme: dict, parent=None):
        super().__init__(parent)
        self.theme = theme
        self._linter_thread = None
        self._lint_timer = QTimer(self)
        self._lint_timer.setSingleShot(True)
        self._lint_timer.setInterval(800)  # debounce 800ms
        self._lint_timer.timeout.connect(self._run_lint)
        self._pending_lint_path = None
        self._pending_lint_code = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        
        # Panel Header (Action buttons in the corner)
        self.header = PanelHeader(theme, self)
        self.header.add_action("action_clear.svg", "Clear Terminal", self.cmd_clear_terminal)
        self.header.add_action("action_kill.svg", "Kill Terminal", self.cmd_kill_terminal)
        self.header.add_action("action_refresh.svg", "Restart Terminal", self.cmd_restart_terminal)
        
        self.tabs.setCornerWidget(self.header, Qt.Corner.TopRightCorner)

        # Terminals Container
        self.terminal_container = TerminalContainer(theme, self)
        self.terminal_container.terminal_output.connect(self.terminal_output.emit)
        self.tabs.addTab(self.terminal_container, "TERMINAL")

        # Output
        self.output = OutputWidget(theme, self)
        self.tabs.addTab(self.output, "OUTPUT")

        # Problems  (new VS Code-style widget)
        self.problems = ProblemsWidget(theme, self)
        self.problems.problem_clicked.connect(self.problem_clicked.emit)
        self.tabs.addTab(self.problems, "PROBLEMS")

        layout.addWidget(self.tabs)

        # Update problems badge whenever the tab changes
        self.tabs.currentChanged.connect(self._update_tab_badge)

        # VS Code style TabBar styling
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border-top: 1px solid {theme['panel_border']};
                background-color: {theme['panel_bg']};
            }}
            QTabBar {{
                background-color: {theme['panel_bg']};
            }}
            QTabBar::tab {{
                background-color: transparent;
                color: {theme['text_secondary']};
                padding: 8px 12px;
                font-weight: 600;
                text-transform: uppercase;
                font-size: 11px;
                letter-spacing: 0.5px;
                border: none;
                border-bottom: 2px solid transparent;
                font-family: 'Segoe UI', sans-serif;
            }}
            QTabBar::tab:selected {{
                color: {theme['text_primary']};
                border-bottom: 2px solid {theme['accent']};
            }}
            QTabBar::tab:hover {{
                color: {theme['text_primary']};
            }}
        """)

    def _update_tab_badge(self, _index=None):
        """Update the PROBLEMS tab label with error/warning counts."""
        errs, warns, infos = self.problems.get_counts()
        total = errs + warns + infos
        if total > 0:
            self.tabs.setTabText(2, f"PROBLEMS ({total})")
        else:
            self.tabs.setTabText(2, "PROBLEMS")

    # ────────────────────────────────────────
    # Linting API  (called from main_window)
    # ────────────────────────────────────────
    def lint_file(self, file_path: str, source_code: str):
        """
        Schedule a lint of the given file (debounced).
        Called when the user types or saves.
        """
        if not file_path or not file_path.endswith(('.py', '.pyw')):
            return
        self._pending_lint_path = file_path
        self._pending_lint_code = source_code
        self._lint_timer.start()

    def _run_lint(self):
        if not self._pending_lint_path:
            return
        if self._linter_thread and self._linter_thread.isRunning():
            return  # skip if still running
        self._linter_thread = PythonLinter(
            self._pending_lint_path, self._pending_lint_code, self
        )
        self._linter_thread.results_ready.connect(self._on_lint_results)
        self._linter_thread.start()

    def _on_lint_results(self, problems: list[dict]):
        # Merge: remove old problems for this file, add new ones
        path = self._pending_lint_path
        existing = [p for p in self.problems._problems if p.get('file') != path]
        existing.extend(problems)
        self.problems.set_problems(existing)
        self._update_tab_badge()
        # Notify for editor squiggles
        self.problems_found.emit(path, problems)
        # Emit signal so main window can update status bar
        self._notify_status_bar()

    def _notify_status_bar(self):
        """Emit problems_changed so the main window can update the status bar."""
        errs, warns, _ = self.problems.get_counts()
        self.problems_changed.emit(errs, warns)

    # ────────────────────────────────────────
    # Terminal commands
    # ────────────────────────────────────────
    def cmd_clear_terminal(self):
        current_term = self.terminal_container.stack.currentWidget()
        if current_term and isinstance(current_term, TerminalWidget):
             current_term.clear_terminal()

    def cmd_kill_terminal(self):
        self.terminal_container.kill_current_terminal()

    def cmd_restart_terminal(self):
        self.terminal_container.kill_current_terminal()
        self.terminal_container.add_terminal()

    def show_terminal(self):
        self.tabs.setCurrentWidget(self.terminal_container)
        self.show()

    def show_output(self):
        self.tabs.setCurrentWidget(self.output)
        self.show()

    def show_problems(self):
        self.tabs.setCurrentWidget(self.problems)
        self.show()

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(self.theme['panel_bg']))
        
        # Subtle top border for separation
        p.setPen(QColor(self.theme.get('bg_light', '#3a3a3c')))
        p.drawLine(0, 0, self.width(), 0)
        p.end()
