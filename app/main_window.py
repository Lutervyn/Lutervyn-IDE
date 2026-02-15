import sys
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
from app.ui.help_dialogs import (KeyboardShortcutsDialog, ReleaseNotesDialog,
                                  ReportIssueDialog, DeveloperToolsDialog,
                                  WelcomePageTab)
from app.core.config import config


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
        self.editor_tabs.tabs_changed.connect(self._on_tabs_collection_changed)
        
        # Restore last workspace if nothing was passed via CLI
        QTimer.singleShot(0, self._restore_state)

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

        # New
        self._add_action(file_menu, "New Text File", "Ctrl+N", self.cmd_new_file)
        self._add_action(file_menu, "New File...", "Ctrl+Alt+Win+N", self.cmd_new_file_advanced)
        self._add_action(file_menu, "New Window", "Ctrl+Shift+N", lambda: None)
        file_menu.addSeparator()

        # Open
        self._add_action(file_menu, "Open File...", "Ctrl+O", self.cmd_open_file)
        self._add_action(file_menu, "Open Folder...", "Ctrl+K,Ctrl+O", self.cmd_open_folder)
        self._add_action(file_menu, "Open Workspace from File...", "", lambda: None)
        
        # Open Recent
        recent_menu = file_menu.addMenu("Open Recent")
        self._add_action(recent_menu, "Reopen Closed Editor", "Ctrl+Shift+T", lambda: None)
        recent_menu.addSeparator()
        self._add_action(recent_menu, "Clear Recently Opened", "", lambda: None)
        
        file_menu.addSeparator()

        # Workspace
        self._add_action(file_menu, "Add Folder to Workspace...", "", self.cmd_add_folder_to_workspace)
        self._add_action(file_menu, "Save Workspace As...", "", lambda: None)
        self._add_action(file_menu, "Duplicate Workspace", "", lambda: None)
        file_menu.addSeparator()

        # Save
        self._add_action(file_menu, "Save", "Ctrl+S", self.cmd_save)
        self._add_action(file_menu, "Save As...", "Ctrl+Shift+S", self.cmd_save_as)
        self._add_action(file_menu, "Save All", "", lambda: None)
        file_menu.addSeparator()

        # Share
        share_menu = file_menu.addMenu("Share")
        self._add_action(share_menu, "Export Profile...", "", lambda: None)
        self._add_action(share_menu, "Import Profile...", "", lambda: None)
        file_menu.addSeparator()

        # Auto Save
        auto_save_action = QAction("Auto Save", self)
        auto_save_action.setCheckable(True)
        file_menu.addAction(auto_save_action)
        
        # Preferences
        pref_menu = file_menu.addMenu("Preferences")
        self._add_action(pref_menu, "Settings", "Ctrl+,", lambda: None)
        self._add_action(pref_menu, "Online Services Settings", "", lambda: None)
        self._add_action(pref_menu, "Extensions", "Ctrl+Shift+X", lambda: self._switch_sidebar("extensions"))
        pref_menu.addSeparator()
        self._add_action(pref_menu, "Keyboard Shortcuts", "Ctrl+K,Ctrl+S", lambda: None)
        self._add_action(pref_menu, "Keymaps", "Ctrl+K,Ctrl+M", lambda: None)
        pref_menu.addSeparator()
        self._add_action(pref_menu, "User Snippets", "", lambda: None)
        self._add_action(pref_menu, "User Tasks", "", lambda: None)
        pref_menu.addSeparator()
        self._add_action(pref_menu, "Theme", "Ctrl+K,Ctrl+T", self.cmd_toggle_theme)
        
        file_menu.addSeparator()

        # Close
        self._add_action(file_menu, "Revert File", "", lambda: None)
        self._add_action(file_menu, "Close Editor", "Ctrl+F4", 
                         lambda: self.editor_tabs._close_tab(self.editor_tabs.tabs.currentIndex()))
        self._add_action(file_menu, "Close Folder", "Ctrl+K,F", lambda: None)
        self._add_action(file_menu, "Close Window", "Alt+F4", self.close)
        
        file_menu.addSeparator()
        self._add_action(file_menu, "Exit", "", self.close)

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
        self.sidebar.terminal_requested.connect(self._on_terminal_requested)
        self.sidebar.find_in_folder_requested.connect(self._on_find_in_folder)
        self.sidebar.workspace_action_requested.connect(self._on_workspace_action)
        self.sidebar.file_close_requested.connect(self._on_file_close_requested)
        # Connect SearchPanel file_opened signal (includes line number)
        self.sidebar.search_panel.file_opened.connect(self._open_file_at_line)
        # Connect file reload signal for live updates after replace
        self.sidebar.search_panel.file_reloaded.connect(self._reload_file_in_editor)
        # SCM Badges
        self.sidebar.scm_count_changed.connect(self._update_scm_badge)
        
        # self.sidebar.setFixedWidth(280) # Removed to allow resizing
        self.sidebar.setMinimumWidth(50) # Allow shrinking


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
        self.main_splitter.setCollapsible(0, False) # Prevent sidebar from snapping/hiding on drag
        self.main_splitter.setCollapsible(1, False) # Prevent editor from snapping
        
        # Ensure sidebar can be resized but has a sane minimum
        self.sidebar.setMinimumWidth(150)
        self.sidebar.setMaximumWidth(600)

        content_layout.addWidget(self.main_splitter)
        root_layout.addWidget(content_widget, 1)

        self.status_bar = StatusBar(self.theme, self)
        root_layout.addWidget(self.status_bar)

        # Connect Sidebar and EditorTabs for synchronization
        self.editor_tabs.tabs_changed.connect(self._sync_open_editors)
        self._sync_open_editors() # Initial sync

    def _sync_open_editors(self):
        """Send the list of open files and untitled tabs to the sidebar."""
        open_items = []
        for i in range(self.editor_tabs.tabs.count()):
            widget = self.editor_tabs.tabs.widget(i)
            
            # Identify path if it's an editor
            path = None
            # Generic check to avoid circular imports or missing classes
            if hasattr(widget, "editor") and hasattr(widget.editor, "file_path"):
                path = widget.editor.file_path
            elif hasattr(widget, "file_path"):
                path = widget.file_path
                
            # Get name from tab text (handles "Untitled-1", "● file.py", etc.)
            name = self.editor_tabs.tabs.tabText(i).replace("● ", "")
            
            open_items.append({
                'name': name,
                'path': path,
                'index': i # Pass index for direct switching
            })
            
        self.sidebar.explorer_panel.sync_open_editors(open_items)

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

    def _update_scm_badge(self, count: int):
        """Update the Source Control activity bar badge."""
        text = str(count) if count > 0 else None
        self.activity_bar.set_badge("scm", text)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == event.Type.WindowStateChange:
            self.title_bar.set_maximized_state(self.isMaximized())

    def setWindowTitle(self, title):
        super().setWindowTitle(title)
        if hasattr(self, "title_bar"):
            self.title_bar.set_title(title)

    def _on_file_close_requested(self, path):
        """Handle request from sidebar to close a file (e.g. before deletion)."""
        self.editor_tabs.close_file(path)

    def _open_file(self, path_or_name):
        """Open a file in the editor or switch to existing tab."""
        # 1. If it's a valid file path on disk, open it
        if path_or_name and os.path.isfile(path_or_name):
            self.editor_tabs.open_file(path_or_name)
            return

        # 2. Try to switch by tab name (e.g. "Untitled-1")
        for i in range(self.editor_tabs.tabs.count()):
            name = self.editor_tabs.tabs.tabText(i).replace("● ", "")
            if name == path_or_name:
                self.editor_tabs.tabs.setCurrentIndex(i)
                return

    def _open_file_at_line(self, path, line_num):
        """Open a file and scroll to a specific line (for search results)."""
        if os.path.isfile(path):
            self.editor_tabs.open_file(path)
            # Get the current editor and scroll to line
            current_widget = self.editor_tabs.tabs.currentWidget()
            from app.ui.editor import CodeEditorWidget
            if isinstance(current_widget, CodeEditorWidget) and current_widget.file_path == path:
                # Line numbers in Scintilla are 0-indexed
                current_widget.editor.setCursorPosition(line_num - 1, 0)
                current_widget.editor.ensureLineVisible(line_num - 1)

    def _reload_file_in_editor(self, path):
        """Reload a file in the editor if it's currently open (for live replace updates)."""
        print(f"[MainWindow] _reload_file_in_editor called with path: {path}")
        
        if not os.path.isfile(path):
            print(f"[MainWindow] File does not exist: {path}")
            return
        
        # Normalize the path for comparison
        path_norm = os.path.normpath(path)
        print(f"[MainWindow] Normalized path: {path_norm}")
        
        # Find if the file is open in any tab
        print(f"[MainWindow] Checking {self.editor_tabs.tabs.count()} tabs")
        for i in range(self.editor_tabs.tabs.count()):
            widget = self.editor_tabs.tabs.widget(i)
            
            # Debug: Print widget type
            print(f"[MainWindow] Tab {i}: type = {type(widget).__name__}")
            
            # Unwrap EditorWithMinimap if needed
            from app.ui.editor import EditorWithMinimap, CodeEditorWidget
            actual_editor = None
            widget_file_path = None
            
            if isinstance(widget, EditorWithMinimap):
                # It's a wrapper - get the actual editor inside
                actual_editor = widget.editor
                if hasattr(actual_editor, 'file_path'):
                    widget_file_path = actual_editor.file_path
                    print(f"[MainWindow] Unwrapped EditorWithMinimap, file_path: {widget_file_path}")
            elif hasattr(widget, 'file_path'):
                # Direct widget with file_path
                actual_editor = widget
                widget_file_path = widget.file_path
            
            if widget_file_path:
                # Normalize both paths for comparison
                widget_path_norm = os.path.normpath(widget_file_path)
                print(f"[MainWindow] Tab {i}: {widget_path_norm}")
                
                if widget_path_norm == path_norm:
                    print(f"[MainWindow] MATCH! Reloading tab {i}")
                    
                    # Try to reload the file
                    try:
                        # Check if it's a CodeEditorWidget
                        if isinstance(actual_editor, CodeEditorWidget):
                            # Save cursor position
                            line, col = actual_editor.getCursorPosition()
                            
                            # Read file content
                            with open(path, 'r', encoding='utf-8') as f:
                                content = f.read()
                            
                            print(f"[MainWindow] Read {len(content)} characters from file")
                            
                            # Block signals temporarily to avoid triggering modified state
                            actual_editor.blockSignals(True)
                            actual_editor.setText(content)
                            actual_editor.blockSignals(False)
                            
                            # Restore cursor position (if still valid)
                            total_lines = actual_editor.lines()
                            if line < total_lines:
                                actual_editor.setCursorPosition(line, col)
                                actual_editor.ensureLineVisible(line)
                            
                            # Mark as saved (not modified)
                            actual_editor.setModified(False)
                        
                        # Check if it has a reload method (generic approach)
                        elif hasattr(actual_editor, 'reload_file'):
                            actual_editor.reload_file()
                            print(f"[MainWindow] Called reload_file() method")
                        
                        # Last resort: close and reopen the file
                        else:
                            print(f"[MainWindow] Unknown widget type, closing and reopening tab")
                            self.editor_tabs.tabs.removeTab(i)
                            self.editor_tabs.open_file(path)
                        
                        # Update tab title (remove unsaved indicator if any)
                        if self.editor_tabs.tabs.count() > i:
                            tab_title = os.path.basename(path)
                            self.editor_tabs.tabs.setTabText(i, tab_title)
                        
                        print(f"[MainWindow] Successfully reloaded file in tab {i}")
                        
                    except Exception as e:
                        print(f"[MainWindow] Error reloading file {path}: {e}")
                        import traceback
                        traceback.print_exc()
                    break
            else:
                print(f"[MainWindow] Tab {i}: No file_path found")
        else:
            print(f"[MainWindow] No matching tab found for {path_norm}")

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
        self.editor_tabs.new_file()
        self._sync_open_editors()

    def cmd_new_file_advanced(self):
        """Create a new file with language selection."""
        # TODO: Use a proper Quick Pick / Command Palette here
        # For now, just ask for language name (simple implementation)
        from PyQt6.QtWidgets import QInputDialog
        languages = ["python", "markdown", "json", "html", "css", "javascript"]
        lang, ok = QInputDialog.getItem(self, "New File...", "Select Language:", languages, 0, False)
        if ok and lang:
            self.editor_tabs.new_file(language=lang)
        else:
            self.editor_tabs.new_file()
        self._sync_open_editors()

    def cmd_open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open File", "",
            "Python Files (*.py *.pyw);;All Files (*.*)")
        if file_path:
            self._open_file(file_path)

    def cmd_open_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Open Folder")
        if folder:
            self.cmd_open_folder_path(folder)

    def cmd_open_folder_path(self, folder):
        """Open a folder directly by path (used by context menu integration)."""
        if folder and os.path.isdir(folder):
            self._current_folder = folder
            self.sidebar.set_root_folder(folder)
            self.sidebar.search_panel.set_workspace_root(folder)  # Set search root
            self.sidebar.switch_view("explorer")
            self.setWindowTitle(f"{os.path.basename(folder)} - {self.APP_NAME}")
            # Save for next launch
            config.set("last_folder", folder)

    def cmd_add_folder_to_workspace(self):
        """Pick a folder and add it to the existing workspace view."""
        path = QFileDialog.getExistingDirectory(self, "Add Folder to Workspace", self._current_folder or "")
        if path:
            self.sidebar.explorer_panel.add_root_folder(path)

    def cmd_save(self):
        editor = self.editor_tabs.get_current_editor()
        if editor:
            if editor.file_path:
                try:
                    editor.save_file()
                except Exception as e:
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.critical(self, "Error", f"Could not save file: {e}")
            else:
                self.cmd_save_as()

    def cmd_save_as(self):
        editor = self.editor_tabs.get_current_editor()
        if not editor: return

        # Default filename logic
        cwd = os.path.abspath(self._current_folder or os.getcwd())
        
        # Suggested name from tab
        index = self.editor_tabs.tabs.currentIndex()
        suggested_name = "untitled.py"
        if index != -1:
            tab_text = self.editor_tabs.tabs.tabText(index).replace("● ", "")
            # Basic sanitization of name (remove problematic characters for Windows)
            import re
            suggested_name = re.sub(r'[<>:"/\\|?*]', '_', tab_text)
            if "." not in suggested_name:
                suggested_name += ".py"

        # Use native separators for Windows compatibility
        default_path = os.path.normpath(os.path.join(cwd, suggested_name))
        
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self, "Save As...", default_path, 
            "Python Files (*.py);;Markdown Files (*.md);;JSON Files (*.json);;All Files (*.*)"
        )
        
        if file_path:
            try:
                # Normalize and ensure absolute
                file_path = os.path.abspath(os.path.normpath(file_path))
                
                # If no extension was typed and a specific filter was selected, add it?
                # Actually most users prefer explicit. But let's check.
                if "." not in os.path.basename(file_path):
                    if "Python" in selected_filter: file_path += ".py"
                    elif "Markdown" in selected_filter: file_path += ".md"
                    elif "JSON" in selected_filter: file_path += ".json"
                
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(editor.text())
                
                # Update editor state
                self.editor_tabs.set_current_file_path(file_path)
                editor.setModified(False)
                self.sidebar.explorer_panel.refresh()
                self._sync_open_editors()

            except Exception as e:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(self, "Error", f"Could not save file: {e}")

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
        config.set("theme_dark", self._dark_mode)

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

    def cmd_welcome(self):
        """Open the Welcome tab."""
        # Remove existing welcome tabs
        for i in range(self.editor_tabs.tabs.count()):
            w = self.editor_tabs.tabs.widget(i)
            if isinstance(w, WelcomePageTab):
                self.editor_tabs.tabs.setCurrentIndex(i)
                return
        # Create new welcome tab
        welcome = WelcomePageTab(self.theme, self.VERSION, self)
        welcome.action_requested.connect(self._on_welcome_action)
        idx = self.editor_tabs.tabs.addTab(welcome, "Welcome")
        self.editor_tabs.tabs.setCurrentIndex(idx)

    def _on_welcome_action(self, cmd_id):
        """Handle clicks from the Welcome page."""
        actions = {
            "file.new": self.cmd_new_file,
            "file.open": self.cmd_open_file,
            "file.open_folder": self.cmd_open_folder,
            "help.docs": self.cmd_documentation,
            "help.release_notes": self.cmd_release_notes,
            "help.shortcuts": self.cmd_keyboard_shortcuts,
            "help.report_issue": self.cmd_report_issue,
        }
        handler = actions.get(cmd_id)
        if handler:
            handler()

    def cmd_documentation(self):
        """Open documentation in the default browser."""
        QDesktopServices.openUrl(QUrl("https://github.com/Lutervyn/Lutervyn-IDE"))

    def cmd_release_notes(self):
        """Show release notes dialog."""
        dlg = ReleaseNotesDialog(self.theme, self.VERSION, self)
        dlg.exec()

    def cmd_keyboard_shortcuts(self):
        """Show keyboard shortcuts reference."""
        dlg = KeyboardShortcutsDialog(self.theme, self)
        dlg.exec()

    def cmd_report_issue(self):
        """Show report issue dialog with system info."""
        dlg = ReportIssueDialog(self.theme, self.VERSION, self)
        dlg.exec()

    def cmd_developer_tools(self):
        """Show developer tools / log viewer."""
        dlg = DeveloperToolsDialog(self.theme, self)
        dlg.exec()

    def cmd_check_updates(self):
        """Show current version info."""
        QMessageBox.information(
            self, "Check for Updates",
            f"<h3>Lutervyn IDE</h3>"
            f"<p>Current version: <b>{self.VERSION}</b></p>"
            f"<p>You are running the latest version.</p>"
            f"<br><p style=\"color: gray;\">Auto-update is not yet available.</p>")

    def cmd_about(self):
        """Show About dialog with full details."""
        import platform
        try:
            from PyQt6.QtCore import PYQT_VERSION_STR, QT_VERSION_STR
            pyqt_ver = PYQT_VERSION_STR
            qt_ver = QT_VERSION_STR
        except Exception:
            pyqt_ver = "unknown"
            qt_ver = "unknown"

        QMessageBox.about(
            self, "About Lutervyn IDE",
            f"<h2>Lutervyn IDE</h2>"
            f"<p><b>Version {self.VERSION}</b></p>"
            f"<hr>"
            f"<p>A Python IDE made by LUTERVYN.</p>"
            f"<p>Built with Python + PyQt6 + QScintilla.</p>"
            f"<br>"
            f"<table>"
            f"<tr><td><b>Python:</b></td><td>{sys.version.split()[0]}</td></tr>"
            f"<tr><td><b>PyQt6:</b></td><td>{pyqt_ver}</td></tr>"
            f"<tr><td><b>Qt:</b></td><td>{qt_ver}</td></tr>"
            f"<tr><td><b>OS:</b></td><td>{platform.system()} {platform.release()}</td></tr>"
            f"</table>"
            f"<br>"
            f"<p style=\"color: gray;\">© 2026 Lutervyn</p>")

    def _restore_state(self):
        """Restore last session state (folder, theme, etc.)."""
        # Only restore folder if nothing was passed on command line
        if len(sys.argv) <= 1:
            last_folder = config.get("last_folder")
            if last_folder and os.path.exists(last_folder):
                self.cmd_open_folder_path(last_folder)
        
        # Restore dark/light theme
        is_dark = config.get("theme_dark", True)
        if is_dark != self._dark_mode:
            self.cmd_toggle_theme()

    def _open_file(self, file_path):
        if file_path and os.path.isfile(file_path):
            self.editor_tabs.open_file(file_path)
            self._update_title(file_path)
            self._update_language(file_path)

    def _on_terminal_requested(self, path):
        """Open a NEW terminal at the specified path."""
        # Ensure panel is visible and on Terminal tab
        self.panel.show_terminal()
        
        # Determine strict folder path
        target_dir = path if os.path.isdir(path) else os.path.dirname(path)
        
        # Create NEW terminal instance in that folder (VS Code style)
        self.panel.terminal_container.add_terminal(cwd=target_dir)

    def _on_find_in_folder(self, path):
        """Switch to search sidebar and set 'files to include'."""
        self._switch_sidebar("search")
        # TODO: Search sidebar API might need update to set filter programmatically
        # For now, just switch. Ideally: self.sidebar.search_panel.set_include_filter(path)
        pass

    def _on_workspace_action(self, action, path):
        """Handle workspace actions (add/remove folder)."""
        if action == "add_folder":
            self.cmd_add_folder_to_workspace()
        elif action == "remove_folder":
            self.sidebar.explorer_panel.remove_root_folder(path)
        """Open a NEW terminal at the specified path."""
        # Ensure panel is visible and on Terminal tab
        self.panel.show_terminal()
        
        # Determine strict folder path
        target_dir = path if os.path.isdir(path) else os.path.dirname(path)
        
        # Create NEW terminal instance in that folder (VS Code style)
        self.panel.terminal_container.add_terminal(cwd=target_dir)

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
            self.sidebar.explorer_panel.highlight_file(editor.file_path)
        self._on_tabs_collection_changed()

    def _on_tabs_collection_changed(self):
        """Update the sidebar's Open Editors list with all currently open files."""
        open_files = []
        for i in range(self.editor_tabs.tabs.count()):
            widget = self.editor_tabs.tabs.widget(i)
            # Handle welcome tab (don't show it in open editors)
            if hasattr(widget, "editor"):
                path = widget.editor.file_path
                if path:
                    open_files.append(path)
            elif hasattr(widget, "file_path"): # Just in case
                if widget.file_path:
                    open_files.append(widget.file_path)
        
        self.sidebar.explorer_panel.sync_open_editors(open_files)

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
