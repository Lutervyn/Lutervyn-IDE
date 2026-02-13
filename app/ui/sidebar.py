import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QTreeView, QLineEdit,
                              QStackedWidget, QPushButton, QTreeWidget,
                              QTreeWidgetItem, QSizePolicy, QAbstractItemView,
                              QFileIconProvider, QInputDialog, QMessageBox, QMenu,
                              QStyledItemDelegate, QStyleOptionViewItem)
from PyQt6.QtCore import pyqtSignal, Qt, QDir, QModelIndex, QFileInfo, QSize, QPoint, QRect
from PyQt6.QtGui import QFont, QColor, QPainter, QFileSystemModel, QIcon, QPen


class ExplorerDelegate(QStyledItemDelegate):
    """Custom delegate to draw indentation guides and modern chevrons."""
    def __init__(self, theme: dict, parent=None):
        super().__init__(parent)
        self.theme = theme

    def paint(self, painter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 1. Draw indentation guides
        indentation = 20
        level = option.rect.left() // indentation
        
        if level > 0:
            pen = QPen(QColor(self.theme.get('border', '#444444')), 0.8)
            painter.setPen(pen)
            for i in range(1, level + 1):
                # Line should be at the start of each indentation block
                x = i * indentation - 12
                painter.drawLine(x, option.rect.top(), x, option.rect.bottom())

        # 2. Extract state for chevrons
        model = index.model()
        is_expanded = False
        has_children = False
        if hasattr(index.model(), "hasChildren") and model.hasChildren(index):
            has_children = True
            # Checking expansion state from the view
            view = self.parent()
            if isinstance(view, QTreeView):
                is_expanded = view.isExpanded(index)

        # 3. Draw modern chevrons if it's a folder/has children
        if has_children:
            # We draw a small triangle (chevron)
            chevron_size = 8
            chevron_rect = QRect(option.rect.left() - 16, option.rect.center().y() - 4, chevron_size, chevron_size)
            
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(self.theme.get('text_secondary', '#888888')))
            
            if is_expanded:
                # Downward triangle
                points = [QPoint(0, 2), QPoint(8, 2), QPoint(4, 6)]
            else:
                # Rightward triangle
                points = [QPoint(2, 0), QPoint(2, 8), QPoint(6, 4)]
            
            painter.translate(chevron_rect.topLeft())
            painter.drawPolygon(points)
            painter.translate(-chevron_rect.topLeft())

        painter.restore()
        
        # 4. Standard paint for icon/text (with a bit of offset)
        new_option = QStyleOptionViewItem(option)
        # We handle selection highlight in the stylesheet mostly, 
        # but we can adjust icon/text position here if needed.
        super().paint(painter, new_option, index)

    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        size.setHeight(28) # Even taller for that premium feel
        return size


class VSCodeIconProvider(QFileIconProvider):
    """Custom icon provider that uses our VS Code-style SVGs."""
    def __init__(self, theme: dict):
        super().__init__()
        self.theme = theme
        self.icons_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "assets", "icons"
        )
        # Pre-load common icons
        self._dir_icon = QIcon(os.path.join(self.icons_path, "folder_closed.svg"))
        self._dir_open_icon = QIcon(os.path.join(self.icons_path, "folder_open.svg"))

    def icon(self, info: QFileInfo):
        if info.isDir():
            return self._dir_icon
        
        ext = info.suffix().lower()
        icon_name = {
            "py": "file_python.svg",
            "pyw": "file_python.svg",
            "html": "file_html.svg",
            "htm": "file_html.svg",
            "css": "file_css.svg",
            "js": "file_js.svg",
            "json": "file_json.svg",
            "md": "file_markdown.svg",
            "txt": "file_text.svg",
            "yaml": "file_json.svg",
            "yml": "file_json.svg",
            "toml": "file_json.svg",
            "cfg": "file_text.svg"
        }.get(ext, "file_default.svg")
        
        path = os.path.join(self.icons_path, icon_name)
        if os.path.exists(path):
            return QIcon(path)
        return super().icon(info)


class SidebarHeader(QWidget):
    """Header bar for each sidebar section (e.g. 'EXPLORER')."""

    def __init__(self, title: str, theme: dict, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.setFixedHeight(35)

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(12, 0, 8, 0) # More aligned
        self.layout.setSpacing(2)

        self.label = QLabel(title.upper())
        # More pronounced font for the main section header
        font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        font.setFamilies(["Segoe UI", "SF Pro Text", "Helvetica Neue", "Arial", "sans-serif"])
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.2)
        self.label.setFont(font)

        self.label.setStyleSheet(f"color: {theme['text_secondary']};")
        self.layout.addWidget(self.label)
        self.layout.addStretch()

    def add_action(self, icon_name: str, tooltip: str, callback):
        """Add a small action button to the header (VS Code style)."""
        btn = QPushButton()
        btn.setToolTip(tooltip)
        btn.setFixedSize(26, 26)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        icon_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "assets", "icons", icon_name
        )
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
            btn.setIcon(icon)
            btn.setIconSize(QSize(14, 14)) # Slightly smaller action icons
        
        btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 4px;
                padding: 4px;
            }}
            QPushButton:hover {{
                background-color: {self.theme['bg_hover']};
            }}
        """)
        btn.clicked.connect(callback)
        self.layout.addWidget(btn)

    def paintEvent(self, event):
        p = QPainter(self)
        # Subtle separator at the top maybe? VS Code usually has very clean borders.
        p.fillRect(self.rect(), QColor(self.theme['sidebar_bg']))
        p.end()



class FileExplorerPanel(QWidget):
    """File tree explorer — the main sidebar view."""

    file_opened = pyqtSignal(str)  # Emits file path when double-clicked

    def __init__(self, theme: dict, parent=None):
        super().__init__(parent)
        self.theme = theme
        self._root_path = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        self.header = SidebarHeader("Explorer", theme, self)
        self.header.add_action("action_new_file.svg", "New File", self.cmd_new_file)
        self.header.add_action("action_new_folder.svg", "New Folder", self.cmd_new_folder)
        self.header.add_action("action_refresh.svg", "Refresh", self.cmd_refresh)
        self.header.add_action("action_collapse.svg", "Collapse All", self.cmd_collapse_all)
        layout.addWidget(self.header)

        # Folder section header
        self.folder_header = QLabel("  No folder opened")
        self.folder_header.setFixedHeight(22)
        self.folder_header.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.folder_header.setStyleSheet(f"""
            color: {theme['sidebar_fg']};
            background-color: {theme['sidebar_bg']};
            padding-left: 12px;
        """)
        layout.addWidget(self.folder_header)

        # File system model
        self.model = QFileSystemModel()
        self.model.setIconProvider(VSCodeIconProvider(theme))
        self.model.setRootPath("")
        self.model.setNameFilters(["*.py", "*.pyw", "*.txt", "*.md", "*.json",
                                    "*.yaml", "*.yml", "*.toml", "*.cfg", "*.ini",
                                    "*.html", "*.css", "*.js", "*.ts", "*.xml",
                                    "*.csv", "*.sql", "*.sh", "*.bat", "*.ps1"])
        self.model.setNameFilterDisables(False)

        # Tree view
        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setItemDelegate(ExplorerDelegate(theme, self.tree))
        self.tree.setHeaderHidden(True)
        self.tree.setAnimated(True)
        self.tree.setIndentation(20) # More space like VS Code
        self.tree.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tree.setColumnHidden(1, True)
        self.tree.setColumnHidden(2, True)
        self.tree.setColumnHidden(3, True)
        self.tree.doubleClicked.connect(self._on_item_double_clicked)
        
        # Connect signals for icon switching
        self.tree.expanded.connect(self._on_item_expanded)
        self.tree.collapsed.connect(self._on_item_collapsed)

        # Context menu
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)

        # High-Fidelity Styling
        self.tree.setStyleSheet(f"""
            QTreeView {{
                background-color: {theme['sidebar_bg']};
                color: {theme['sidebar_fg']};
                border: none;
                outline: none;
            }}
            QTreeView::item {{
                height: 26px;
                padding-left: 0px;
                border: 1px solid transparent;
            }}
            QTreeView::item:hover {{
                background-color: {theme['bg_hover']};
            }}
            QTreeView::item:selected {{
                background-color: {theme['bg_selection']};
                color: {theme['text_primary']};
                border: 1px solid {theme['accent']};
                border-radius: 2px;
            }}
            QTreeView::branch {{
                background-color: transparent;
            }}
            QTreeView::branch:has-children:!has-siblings:closed,
            QTreeView::branch:closed:has-children:has-siblings {{
                border-image: none;
                image: none; /* We could use custom SVGs here for chevrons */
            }}
        """)

        layout.addWidget(self.tree)

    def set_root_folder(self, path: str):
        """Set the root folder to display in the explorer."""
        self._root_path = os.path.normpath(path)
        self.model.setRootPath(self._root_path)
        self.tree.setRootIndex(self.model.index(self._root_path))
        folder_name = os.path.basename(self._root_path)
        self.folder_header.setText(f"  {folder_name.upper()}")

    def _on_item_double_clicked(self, index: QModelIndex):
        path = self.model.filePath(index)
        if not self.model.isDir(index):
            self.file_opened.emit(path)

    def _on_item_expanded(self, index: QModelIndex):
        icon_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "assets", "icons", "folder_open.svg"
        )
        if os.path.exists(icon_path):
            self.model.setData(index, QIcon(icon_path), Qt.ItemDataRole.DecorationRole)

    def _on_item_collapsed(self, index: QModelIndex):
        icon_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "assets", "icons", "folder_closed.svg"
        )
        if os.path.exists(icon_path):
            self.model.setData(index, QIcon(icon_path), Qt.ItemDataRole.DecorationRole)

    def _show_context_menu(self, position):
        from PyQt6.QtWidgets import QMenu
        menu = QMenu(self)
        menu.addAction("New File", self.cmd_new_file)
        menu.addAction("New Folder", self.cmd_new_folder)
        menu.addSeparator()
        
        index = self.tree.indexAt(position)
        if index.isValid():
            menu.addAction("Delete", lambda: self.cmd_delete(index))
            menu.addAction("Rename", lambda: self.cmd_rename(index))
        
        menu.exec(self.tree.viewport().mapToGlobal(position))

    def cmd_delete(self, index: QModelIndex):
        path = self.model.filePath(index)
        confirm = QMessageBox.question(self, "Delete", f"Are you sure you want to delete {os.path.basename(path)}?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                if self.model.isDir(index):
                    import shutil
                    shutil.rmtree(path)
                else:
                    os.remove(path)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not delete: {e}")

    def cmd_rename(self, index: QModelIndex):
        old_path = self.model.filePath(index)
        old_name = os.path.basename(old_path)
        new_name, ok = QInputDialog.getText(self, "Rename", "Enter new name:", text=old_name)
        if ok and new_name and new_name != old_name:
            new_path = os.path.join(os.path.dirname(old_path), new_name)
            try:
                os.rename(old_path, new_path)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not rename: {e}")


    # Explorer Actions
    def cmd_new_file(self):
        if not self._root_path: return
        name, ok = QInputDialog.getText(self, "New File", "Enter file name:")
        if ok and name:
            path = os.path.join(self._root_path, name)
            try:
                open(path, 'a').close()
                self.file_opened.emit(path)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not create file: {e}")

    def cmd_new_folder(self):
        if not self._root_path: return
        name, ok = QInputDialog.getText(self, "New Folder", "Enter folder name:")
        if ok and name:
            path = os.path.join(self._root_path, name)
            try:
                os.makedirs(path, exist_ok=True)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not create folder: {e}")

    def cmd_refresh(self):
        if self._root_path:
            self.model.setRootPath("") # Force refresh
            self.model.setRootPath(self._root_path)

    def cmd_collapse_all(self):
        self.tree.collapseAll()



class SearchPanel(QWidget):
    """Search across files panel."""

    search_requested = pyqtSignal(str)

    def __init__(self, theme: dict, parent=None):
        super().__init__(parent)
        self.theme = theme

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.header = SidebarHeader("Search", theme, self)
        layout.addWidget(self.header)

        # Search input
        search_container = QWidget()
        search_layout = QVBoxLayout(search_container)
        search_layout.setContentsMargins(12, 8, 12, 8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search")
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {theme['input_bg']};
                color: {theme['input_fg']};
                border: 1px solid {theme['input_border']};
                padding: 5px 8px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border-color: {theme['input_border_focus']};
            }}
        """)
        self.search_input.returnPressed.connect(
            lambda: self.search_requested.emit(self.search_input.text()))
        search_layout.addWidget(self.search_input)

        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText("Replace")
        self.replace_input.setStyleSheet(self.search_input.styleSheet())
        search_layout.addWidget(self.replace_input)

        layout.addWidget(search_container)

        # Results tree
        self.results_tree = QTreeWidget()
        self.results_tree.setHeaderHidden(True)
        self.results_tree.setIndentation(16)
        layout.addWidget(self.results_tree)


class SourceControlPanel(QWidget):
    """Placeholder for source control view."""

    def __init__(self, theme: dict, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(SidebarHeader("Source Control", theme, self))

        msg = QLabel("Initialize a repository to\nuse source control features.")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setStyleSheet(f"color: {theme['text_secondary']}; padding: 20px;")
        layout.addWidget(msg)
        layout.addStretch()


class DebugPanel(QWidget):
    """Placeholder for run/debug view."""

    def __init__(self, theme: dict, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(SidebarHeader("Run and Debug", theme, self))

        msg = QLabel("Open a file and press F5\nto start debugging.")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setStyleSheet(f"color: {theme['text_secondary']}; padding: 20px;")
        layout.addWidget(msg)
        layout.addStretch()


class ExtensionsPanel(QWidget):
    """Placeholder for extensions view."""

    def __init__(self, theme: dict, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(SidebarHeader("Extensions", theme, self))

        msg = QLabel("No extensions installed yet.")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setStyleSheet(f"color: {theme['text_secondary']}; padding: 20px;")
        layout.addWidget(msg)
        layout.addStretch()


class Sidebar(QWidget):
    """Main sidebar that switches between panels."""

    file_opened = pyqtSignal(str)

    def __init__(self, theme: dict, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.setMinimumWidth(200)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Stacked widget to swap between panels
        self.stack = QStackedWidget()

        self.explorer_panel = FileExplorerPanel(theme, self)
        self.explorer_panel.file_opened.connect(self.file_opened.emit)
        self.search_panel = SearchPanel(theme, self)
        self.scm_panel = SourceControlPanel(theme, self)
        self.debug_panel = DebugPanel(theme, self)
        self.extensions_panel = ExtensionsPanel(theme, self)

        self.stack.addWidget(self.explorer_panel)    # 0
        self.stack.addWidget(self.search_panel)      # 1
        self.stack.addWidget(self.scm_panel)         # 2
        self.stack.addWidget(self.debug_panel)       # 3
        self.stack.addWidget(self.extensions_panel)  # 4

        layout.addWidget(self.stack)

        self._view_map = {
            "explorer": 0,
            "search": 1,
            "scm": 2,
            "debug": 3,
            "extensions": 4,
        }

    def switch_view(self, view_id: str):
        if view_id in self._view_map:
            self.stack.setCurrentIndex(self._view_map[view_id])

    def set_root_folder(self, path: str):
        self.explorer_panel.set_root_folder(path)

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(self.theme['sidebar_bg']))
        p.end()
