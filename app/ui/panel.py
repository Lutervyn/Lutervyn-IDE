"""
Bottom Panel - Terminal, Output, Problems tabs (like VS Code).
Contains an embedded terminal emulator + output/problems panels.
"""

import os
import sys
import subprocess
import threading
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
                              QPlainTextEdit, QLabel, QTreeWidget,
                              QTreeWidgetItem, QPushButton, QSizePolicy,
                              QLineEdit)
from PyQt6.QtCore import pyqtSignal, Qt, QProcess, QTimer, QSize, QPoint
from PyQt6.QtGui import QFont, QColor, QTextCursor, QPainter, QKeyEvent, QIcon


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

    def __init__(self, theme: dict, parent=None):
        super().__init__(parent)
        self.theme = theme
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
            }}
        """)

        self._start_shell()

    def _start_shell(self):
        """Start a system shell process."""
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self._read_output)
        self.process.readyReadStandardError.connect(self._read_output)

        if sys.platform == "win32":
            self.process.start("powershell.exe", ["-NoLogo"])
        else:
            shell = os.environ.get("SHELL", "/bin/bash")
            self.process.start(shell, [])

        self._write_prompt_header()

    def _write_prompt_header(self):
        cwd = os.getcwd()
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


class ProblemsWidget(QTreeWidget):
    """Problems panel showing errors and warnings."""

    def __init__(self, theme: dict, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.setHeaderLabels(["", "Message", "Source", "Line"])
        self.setColumnWidth(0, 30)
        self.setColumnWidth(1, 400)
        self.setColumnWidth(2, 200)
        self.setColumnWidth(3, 60)
        self.setRootIsDecorated(False)
        self.setAlternatingRowColors(False)

    def add_problem(self, level: str, message: str, source: str, line: int):
        icon = "❌" if level == "error" else "⚠" if level == "warning" else "ℹ"
        item = QTreeWidgetItem([icon, message, source, str(line)])
        self.addTopLevelItem(item)

    def clear_problems(self):
        self.clear()


class BottomPanel(QWidget):
    """The bottom panel area with Terminal, Output, Problems tabs."""

    def __init__(self, theme: dict, parent=None):
        super().__init__(parent)
        self.theme = theme

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

        # Terminal
        self.terminal = TerminalWidget(theme, self)
        self.tabs.addTab(self.terminal, "Terminal")

        # Output
        self.output = OutputWidget(theme, self)
        self.tabs.addTab(self.output, "Output")

        # Problems
        self.problems = ProblemsWidget(theme, self)
        self.tabs.addTab(self.problems, "Problems")

        layout.addWidget(self.tabs)

        # VS Code style TabBar styling
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border-top: 1px solid {theme['panel_border']};
                background-color: #000000;
            }}
            QTabBar {{
                background-color: {theme['panel_bg']};
            }}
            QTabBar::tab {{
                background-color: transparent;
                color: {theme['text_secondary']};
                padding: 8px 16px;
                font-weight: bold;
                text-transform: uppercase;
                font-size: 11px;
                border: none;
                border-bottom: 2px solid transparent;
            }}
            QTabBar::tab:selected {{
                color: {theme['text_primary']};
                border-bottom: 2px solid {theme['accent']};
            }}
            QTabBar::tab:hover {{
                color: {theme['text_primary']};
            }}
        """)

    def cmd_clear_terminal(self):
        self.terminal.clear_terminal()

    def cmd_kill_terminal(self):
        self.terminal.close_terminal()
        self.terminal.appendPlainText("\nProcess killed.\n")

    def cmd_restart_terminal(self):
        self.terminal.close_terminal()
        self.terminal.clear()
        self.terminal._start_shell()

    def show_terminal(self):
        self.tabs.setCurrentWidget(self.terminal)
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
        # Thin separator at the very top
        p.setPen(QColor(self.theme['panel_border']))
        p.drawLine(0, 0, self.width(), 0)
        p.end()
