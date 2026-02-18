import os

code = r'''import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout,
                              QVBoxLayout, QSplitter, QMenu,
                              QFileDialog, QMessageBox)
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QAction, QKeySequence, QIcon, QPixmap

from app.ui.theme import get_theme, build_stylesheet
from app.ui.titlebar import CustomTitleBar
from app.ui.activity_bar import ActivityBar
from app.ui.sidebar import Sidebar
from app.ui.editor import EditorTabs
from app.ui.panel import BottomPanel
from app.ui.status_bar import StatusBar
from app.ui.command_palette import CommandPalette
from app.core.runner import PythonRunner


class MainWindow(QMainWindow):
    APP_NAME = "Lutervyn IDE"
    VERSION = "1.0.0"

    COMMANDS = [
        ("file.new", "File: New File"),
        ("file.open", "File: Open File..."),
        ("file.open_folder", "File: Open Folder..."),
        ("file.save", "File: Save"),
        ("file.save_as", "File: Save As..."),
        ("file.close_tab", "File: Close Editor"),
        ("edit.undo", "Edit: Undo"),
        ("edit.redo", "Edit: Redo"),
        ("edit.cut", "Edit: Cut"),
        ("edit.copy", "Edit: Copy"),
        ("edit.paste", "Edit: Paste"),
        ("edit.find", "Edit: Find"),
        ("edit.replace", "Edit: Find and Replace"),
        ("edit.select_all", "Edit: Select All"),
        ("view.toggle_sidebar", "View: Toggle Sidebar Visibility"),
        ("view.toggle_panel", "View: Toggle Panel"),
        ("view.toggle_terminal", "View: Toggle Terminal"),
        ("view.explorer", "View: Show Explorer"),
        ("view.search", "View: Show Search"),
        ("view.command_palette", "View: Command Palette"),
        ("run.run_file", "Run: Run Python File"),
        ("run.stop", "Run: Stop"),
        ("terminal.new", "Terminal: Create New Terminal"),
        ("terminal.clear", "Terminal: Clear Terminal"),
        ("theme.toggle", "Preferences: Toggle Dark/Light Theme"),
    ]

    def __init__(self):
        super().__init__()
        self._dark_mode = True
        self._sidebar_visible = True
        self._panel_visible = True
        self._current_folder = None
        self._resize_edges = 0
        self.theme = get_theme(dark=self._dark_mode)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setWindowTitle(self.APP_NAME)
        self.setMinimumSize(1024, 600)
        self.resize(1400, 850)
        self._set_app_icon()
        self.setStyleSheet(build_stylesheet(self.theme))
        self.runner = PythonRunner(self)
        self._build_ui()
        self.runner.output_received.connect(self.panel.output.append_output)
        self.runner.error_received.connect(lambda t: self.panel.output.append_output(t))
        self.runner.finished.connect(self._on_run_finished)
        self.editor_tabs.tabs.currentChanged.connect(self._on_tab_changed)

    def _set_app_icon(self):
        logo_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "assets", "logo.png")
        if os.path.exists(logo_path):
            icon = QIcon(logo_path)
            self.setWindowIcon(icon)
            QApplication.instance().setWindowIcon(icon)

    def _build_menus(self):
        menubar = self.title_bar.get_menu_bar()

        file_menu = menubar.addMenu("&File")
        self._add_action(file_menu, "New File", "Ctrl+N", self.cmd_new_file)
        self._add_action(file_menu, "New Window", "Ctrl+Shift+N", lambda: None)
        file_menu.addSeparator()
        self._add_action(file_menu, "Open File...", "Ctrl+O", self.cmd_open_file)
        self._add_action(file_menu, "Open Folder...", "Ctrl+K", self.cmd_open_folder)
        file_menu.addSeparator()
        self._add_action(file_menu, "Save", "Ctrl+S", self.cmd_save)
        self._add_action(file_menu, "Save As...", "Ctrl+Shift+S", self.cmd_save_as)
        self._add_action(file_menu, "Save All", "", lambda: None)
        file_menu.addSeparator()
        self._add_action(file_menu, "Preferences", "Ctrl+,", lambda: None)
        file_menu.addSeparator()
        self._add_action(file_menu, "Close Editor", "Ctrl+W",
                         lambda: self.editor_tabs._close_tab(self.editor_tabs.tabs.currentIndex()))
        self._add_action(file_menu, "Close Window", "Alt+F4", self.close)

        edit_menu = menubar.addMenu("&Edit")
        self._add_action(edit_menu, "Undo", "Ctrl+Z", self.cmd_undo)
        self._add_action(edit_menu, "Redo", "Ctrl+Y", self.cmd_redo)
        edit_menu.addSeparator()
        self._add_action(edit_menu, "Cut", "Ctrl+X", self.cmd_cut)
        self._add_action(edit_menu, "Copy", "Ctrl+C", self.cmd_copy)
        self._add_action(edit_menu, "Paste", "Ctrl+V", self.cmd_paste)
        edit_menu.addSeparator()
        self._add_action(edit_menu, "Find", "Ctrl+F", self.cmd_find)
        self._add_action(edit_menu, "Replace", "Ctrl+H", self.cmd_replace)
        edit_menu.addSeparator()
        self._add_action(edit_menu, "Find in Files", "Ctrl+Shift+F",
                         lambda: self._switch_sidebar("search"))
        self._add_action(edit_menu, "Replace in Files", "Ctrl+Shift+H",
                         lambda: self._switch_sidebar("search"))

        selection_menu = menubar.addMenu("&Selection")
        self._add_action(selection_menu, "Select All", "Ctrl+A", self.cmd_select_all)
        self._add_action(selection_menu, "Expand Selection", "Shift+Alt+Right", lambda: None)
        self._add_action(selection_menu, "Shrink Selection", "Shift+Alt+Left", lambda: None)
        selection_menu.addSeparator()
        self._add_action(selection_menu, "Copy Line Up", "Shift+Alt+Up", lambda: None)
        self._add_action(selection_menu, "Copy Line Down", "Shift+Alt+Down", lambda: None)
        self._add_action(selection_menu, "Move Line Up", "Alt+Up", lambda: None)
        self._add_action(selection_menu, "Move Line Down", "Alt+Down", lambda: None)

        view_menu = menubar.addMenu("&View")
        self._add_action(view_menu, "Command Palette...", "Ctrl+Shift+P", self.cmd_command_palette)
        view_menu.addSeparator()
        appearance_menu = view_menu.addMenu("Appearance")
        self._add_action(appearance_menu, "Toggle Full Screen", "F11", self.cmd_toggle_fullscreen)
        self._add_action(appearance_menu, "Toggle Sidebar", "Ctrl+B", self.cmd_toggle_sidebar)
        self._add_action(appearance_menu, "Toggle Panel", "Ctrl+J", self.cmd_toggle_panel)
        self._add_action(appearance_menu, "Toggle Theme", "", self.cmd_toggle_theme)
        view_menu.addSeparator()
        self._add_action(view_menu, "Explorer", "Ctrl+Shift+E", lambda: self._switch_sidebar("explorer"))
        self._add_action(view_menu, "Search", "Ctrl+Shift+F", lambda: self._switch_sidebar("search"))
        self._add_action(view_menu, "Source Control", "Ctrl+Shift+G", lambda: self._switch_sidebar("scm"))
        self._add_action(view_menu, "Run and Debug", "Ctrl+Shift+D", lambda: self._switch_sidebar("debug"))
        self._add_action(view_menu, "Extensions", "Ctrl+Shift+X", lambda: self._switch_sidebar("extensions"))
        view_menu.addSeparator()
        self._add_action(view_menu, "Terminal", "Ctrl+`", self.cmd_toggle_panel)
        self._add_action(view_menu, "Problems", "Ctrl+Shift+M", lambda: self.panel.show_problems())
        self._add_action(view_menu, "Output", "Ctrl+Shift+U", lambda: self.panel.show_output())

        go_menu = menubar.addMenu("&Go")
        self._add_action(go_menu, "Back", "Alt+Left", lambda: None)
        self._add_action(go_menu, "Forward", "Alt+Right", lambda: None)
        go_menu.addSeparator()
        self._add_action(go_menu, "Go to File...", "Ctrl+P", lambda: None)
        self._add_action(go_menu, "Go to Line...", "Ctrl+G", lambda: None)
        self._add_action(go_menu, "Go to Symbol...", "Ctrl+Shift+O", lambda: None)
        go_menu.addSeparator()
        self._add_action(go_menu, "Go to Definition", "F12", lambda: None)
        self._add_action(go_menu, "Go to References", "Shift+F12", lambda: None)

        run_menu = menubar.addMenu("&Run")
        self._add_action(run_menu, "Start Debugging", "F5", self.cmd_run_file)
        self._add_action(run_menu, "Run Without Debugging", "Ctrl+F5", self.cmd_run_file)
        self._add_action(run_menu, "Stop Debugging", "Shift+F5", self.cmd_stop)
        self._add_action(run_menu, "Restart Debugging", "Ctrl+Shift+F5", lambda: None)
        run_menu.addSeparator()
        self._add_action(run_menu, "Toggle Breakpoint", "F9", lambda: None)

        terminal_menu = menubar.addMenu("&Terminal")
        self._add_action(terminal_menu, "New Terminal", "Ctrl+Shift+`", self.cmd_new_terminal)
        self._add_action(terminal_menu, "Split Terminal", "", lambda: None)
        terminal_menu.addSeparator()
        self._add_action(terminal_menu, "Run Active File", "", self.cmd_run_file)
        terminal_menu.addSeparator()
        self._add_action(terminal_menu, "Clear Terminal", "", self.cmd_clear_terminal)

        help_menu = menubar.addMenu("&Help")
        self._add_action(help_menu, "Welcome", "", lambda: None)
        self._add_action(help_menu, "Documentation", "", lambda: None)
        self._add_action(help_menu, "Release Notes", "", lambda: None)
        help_menu.addSeparator()
        self._add_action(help_menu, "About", "", self.cmd_about)

    def _add_action(self, menu, name, shortcut, callback):
        action = QAction(name, self)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        action.triggered.connect(callback)
        menu.addAction(action)
        return action

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.title_bar = CustomTitleBar(self.theme, self)
        self.title_bar.minimize_clicked.connect(self._on_minimize)
        self.title_bar.maximize_clicked.connect(self._on_maximize)
        self.title_bar.close_clicked.connect(self.close)
        root_layout.addWidget(self.title_bar)
        self._build_menus()

        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.activity_bar = ActivityBar(self.theme, self)
        self.activity_bar.view_changed.connect(self._on_activity_bar_click)
        content_layout.addWidget(self.activity_bar)

        self.sidebar = Sidebar(self.theme, self)
        self.sidebar.file_opened.connect(self._open_file)
        self.sidebar.setFixedWidth(280)

        right_area = QSplitter(Qt.Orientation.Vertical)
        right_area.setHandleWidth(1)
        self.editor_tabs = EditorTabs(self.theme, self)
        self.panel = BottomPanel(self.theme, self)
        self.panel.setMinimumHeight(100)
        right_area.addWidget(self.editor_tabs)
        right_area.addWidget(self.panel)
        right_area.setSizes([500, 200])

        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setHandleWidth(1)
        self.main_splitter.addWidget(self.sidebar)
        self.main_splitter.addWidget(right_area)
        self.main_splitter.setSizes([280, 1100])

        content_layout.addWidget(self.main_splitter)
        root_layout.addWidget(content_widget, 1)

        self.status_bar = StatusBar(self.theme, self)
        root_layout.addWidget(self.status_bar)

    def _on_minimize(self):
        self.showMinimized()

    def _on_maximize(self):
        if self.isMaximized():
            self.showNormal()
            self.title_bar.set_maximized_state(False)
        else:
            self.showMaximized()
            self.title_bar.set_maximized_state(True)

    def cmd_toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == event.Type.WindowStateChange:
            self.title_bar.set_maximized_state(self.isMaximized())

    def setWindowTitle(self, title):
        super().setWindowTitle(title)
        if hasattr(self, "title_bar"):
            self.title_bar.set_title(title)

    _EDGE_SIZE = 5

    def _get_edge(self, pos):
        rect = self.rect()
        x, y = pos.x(), pos.y()
        w, h = rect.width(), rect.height()
        e = self._EDGE_SIZE
        edges = 0
        if x < e:
            edges |= 1
        if x > w - e:
            edges |= 2
        if y < e:
            edges |= 4
        if y > h - e:
            edges |= 8
        return edges

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            edges = self._get_edge(event.pos())
            if edges:
                self._resize_edges = edges
                self._resize_start = event.globalPosition().toPoint()
                self._resize_geo = self.geometry()
            else:
                self._resize_edges = 0
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not event.buttons() and not self.isMaximized():
            edges = self._get_edge(event.pos())
            cursor_map = {
                1: Qt.CursorShape.SizeHorCursor,
                2: Qt.CursorShape.SizeHorCursor,
                4: Qt.CursorShape.SizeVerCursor,
                8: Qt.CursorShape.SizeVerCursor,
                5: Qt.CursorShape.SizeFDiagCursor,
                6: Qt.CursorShape.SizeBDiagCursor,
                9: Qt.CursorShape.SizeBDiagCursor,
                10: Qt.CursorShape.SizeFDiagCursor,
            }
            self.setCursor(cursor_map.get(edges, Qt.CursorShape.ArrowCursor))
        if self._resize_edges and event.buttons():
            delta = event.globalPosition().toPoint() - self._resize_start
            geo = self._resize_geo
            new_geo = geo.adjusted(0, 0, 0, 0)
            if self._resize_edges & 1:
                new_geo.setLeft(geo.left() + delta.x())
            if self._resize_edges & 2:
                new_geo.setRight(geo.right() + delta.x())
            if self._resize_edges & 4:
                new_geo.setTop(geo.top() + delta.y())
            if self._resize_edges & 8:
                new_geo.setBottom(geo.bottom() + delta.y())
            if new_geo.width() >= self.minimumWidth() and new_geo.height() >= self.minimumHeight():
                self.setGeometry(new_geo)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._resize_edges = 0
        self.setCursor(Qt.CursorShape.ArrowCursor)
        super().mouseReleaseEvent(event)

    def _on_activity_bar_click(self, view_id):
        if view_id == "__toggle__":
            self.cmd_toggle_sidebar()
        elif view_id == "settings":
            pass
        else:
            self.sidebar.switch_view(view_id)
            if not self._sidebar_visible:
                self.sidebar.show()
                self._sidebar_visible = True

    def _switch_sidebar(self, view_id):
        self.sidebar.switch_view(view_id)
        if not self._sidebar_visible:
            self.sidebar.show()
            self._sidebar_visible = True

    def cmd_new_file(self):
        self.editor_tabs.open_file("")

    def cmd_open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open File", "",
            "Python Files (*.py *.pyw);;All Files (*.*)")
        if file_path:
            self._open_file(file_path)

    def cmd_open_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Open Folder")
        if folder:
            self._current_folder = folder
            self.sidebar.set_root_folder(folder)
            self.sidebar.switch_view("explorer")
            self.setWindowTitle(f"{os.path.basename(folder)} - {self.APP_NAME}")

    def cmd_save(self):
        editor = self.editor_tabs.get_current_editor()
        if editor:
            if editor.file_path:
                editor.save_file()
            else:
                self.cmd_save_as()

    def cmd_save_as(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save As", "",
            "Python Files (*.py);;All Files (*.*)")
        if file_path:
            editor = self.editor_tabs.get_current_editor()
            if editor:
                editor.file_path = file_path
                editor.save_file()

    def cmd_undo(self):
        e = self.editor_tabs.get_current_editor()
        if e:
            e.undo()

    def cmd_redo(self):
        e = self.editor_tabs.get_current_editor()
        if e:
            e.redo()

    def cmd_cut(self):
        e = self.editor_tabs.get_current_editor()
        if e:
            e.cut()

    def cmd_copy(self):
        e = self.editor_tabs.get_current_editor()
        if e:
            e.copy()

    def cmd_paste(self):
        e = self.editor_tabs.get_current_editor()
        if e:
            e.paste()

    def cmd_select_all(self):
        e = self.editor_tabs.get_current_editor()
        if e:
            e.selectAll()

    def cmd_find(self):
        pass

    def cmd_replace(self):
        pass

    def cmd_toggle_sidebar(self):
        self._sidebar_visible = not self._sidebar_visible
        self.sidebar.setVisible(self._sidebar_visible)

    def cmd_toggle_panel(self):
        self._panel_visible = not self._panel_visible
        self.panel.setVisible(self._panel_visible)
        if self._panel_visible:
            self.panel.show_terminal()

    def cmd_toggle_theme(self):
        self._dark_mode = not self._dark_mode
        self.theme = get_theme(dark=self._dark_mode)
        self.setStyleSheet(build_stylesheet(self.theme))

    def cmd_run_file(self):
        file_path = self.editor_tabs.get_current_file_path()
        if file_path and file_path.endswith((".py", ".pyw")):
            self.cmd_save()
            self.panel.show()
            self._panel_visible = True
            self.panel.show_output()
            self.panel.output.clear_output()
            self.runner.run_file(file_path)
        else:
            self.panel.output.append_output("No Python file is currently open.\n")

    def cmd_stop(self):
        self.runner.stop()

    def cmd_new_terminal(self):
        self.panel.show_terminal()
        if not self._panel_visible:
            self.panel.show()
            self._panel_visible = True

    def cmd_clear_terminal(self):
        self.panel.terminal.clear()

    def cmd_command_palette(self):
        palette = CommandPalette(self.theme, self.COMMANDS, self)
        palette.command_selected.connect(self._execute_command)
        x = self.x() + (self.width() - palette.width()) // 2
        y = self.y() + 50
        palette.move(x, y)
        palette.exec()

    def cmd_about(self):
        QMessageBox.about(
            self, "About Lutervyn IDE",
            "<h2>Lutervyn IDE</h2>"
            "<p>Version " + self.VERSION + "</p>"
            "<p>A Python IDE inspired by VS Code</p>"
            "<p>Built with Python + PyQt6 + QScintilla</p>")

    def _open_file(self, file_path):
        if file_path and os.path.isfile(file_path):
            self.editor_tabs.open_file(file_path)
            self._update_title(file_path)
            self._update_language(file_path)

    def _update_title(self, file_path):
        name = os.path.basename(file_path)
        folder = os.path.basename(self._current_folder) if self._current_folder else ""
        if folder:
            self.setWindowTitle(f"{name} - {folder} - {self.APP_NAME}")
        else:
            self.setWindowTitle(f"{name} - {self.APP_NAME}")

    def _update_language(self, file_path):
        ext = os.path.splitext(file_path)[1].lower()
        lang_map = {
            ".py": "Python", ".pyw": "Python", ".js": "JavaScript",
            ".ts": "TypeScript", ".html": "HTML", ".css": "CSS",
            ".json": "JSON", ".md": "Markdown", ".xml": "XML",
            ".yaml": "YAML", ".yml": "YAML", ".sql": "SQL",
            ".sh": "Shell", ".bat": "Batch", ".txt": "Plain Text",
        }
        self.status_bar.update_language(lang_map.get(ext, "Plain Text"))

    def _on_tab_changed(self, index):
        editor = self.editor_tabs.get_current_editor()
        if editor and editor.file_path:
            self._update_title(editor.file_path)
            self._update_language(editor.file_path)

    def _on_run_finished(self, exit_code, status):
        if exit_code == 0:
            self.status_bar.update_problems(0, 0)

    def _execute_command(self, cmd_id):
        cmd_map = {
            "file.new": self.cmd_new_file,
            "file.open": self.cmd_open_file,
            "file.open_folder": self.cmd_open_folder,
            "file.save": self.cmd_save,
            "file.save_as": self.cmd_save_as,
            "file.close_tab": lambda: self.editor_tabs._close_tab(self.editor_tabs.tabs.currentIndex()),
            "edit.undo": self.cmd_undo,
            "edit.redo": self.cmd_redo,
            "edit.cut": self.cmd_cut,
            "edit.copy": self.cmd_copy,
            "edit.paste": self.cmd_paste,
            "edit.find": self.cmd_find,
            "edit.replace": self.cmd_replace,
            "edit.select_all": self.cmd_select_all,
            "view.toggle_sidebar": self.cmd_toggle_sidebar,
            "view.toggle_panel": self.cmd_toggle_panel,
            "view.toggle_terminal": self.cmd_toggle_panel,
            "view.explorer": lambda: self._switch_sidebar("explorer"),
            "view.search": lambda: self._switch_sidebar("search"),
            "view.command_palette": self.cmd_command_palette,
            "run.run_file": self.cmd_run_file,
            "run.stop": self.cmd_stop,
            "terminal.new": self.cmd_new_terminal,
            "terminal.clear": self.cmd_clear_terminal,
            "theme.toggle": self.cmd_toggle_theme,
        }
        handler = cmd_map.get(cmd_id)
        if handler:
            handler()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Lutervyn IDE")
    app.setOrganizationName("Lutervyn")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
'''

target = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app", "main_window.py")
with open(target, "w", encoding="utf-8") as f:
    f.write(code)
print(f"Written {len(code)} chars to {target}")
