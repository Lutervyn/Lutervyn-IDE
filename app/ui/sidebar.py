import os
import sys
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QTreeView, QLineEdit, QFrame, QApplication,
                              QStackedWidget, QPushButton, QTreeWidget,
                              QTreeWidgetItem, QSizePolicy, QAbstractItemView,
                              QFileIconProvider, QInputDialog, QMessageBox, QMenu,
                              QStyledItemDelegate, QStyleOptionViewItem, QListWidget, QStyle)
from PyQt6.QtCore import pyqtSignal, Qt, QDir, QModelIndex, QFileInfo, QSize, QPoint, QRect, QEvent, QTimer
from PyQt6.QtGui import QFont, QColor, QPainter, QFileSystemModel, QIcon, QPen, QPixmap


class ExplorerDelegate(QStyledItemDelegate):
    """Custom delegate to draw indentation guides and modern chevrons."""
    def __init__(self, theme: dict, parent=None):
        super().__init__(parent)
        self.theme = theme

    def paint(self, painter, option, index):
        painter.save()
        
        # 1. State & Geometry
        view = self.parent()
        model = index.model()
        is_selected = (option.state & QStyle.StateFlag.State_Selected)
        is_hover = (option.state & QStyle.StateFlag.State_MouseOver)
        
        # Calculate level correctly (relative to the project root)
        level = 0
        root_index = view.rootIndex()
        temp_index = index
        while temp_index.parent().isValid() and temp_index.parent() != root_index:
            temp_index = temp_index.parent()
            level += 1
            
        # Refined VS Code measurements (Flushed Left)
        indent_width = 12
        left_offset = 6
        icon_size = 16
        
        # Base horizontal positions
        chevron_x = left_offset + (level * indent_width)
        icon_x = chevron_x + 16
        text_x = icon_x + 22
        
        # 2. Draw Background (Full Width)
        # Use a slightly larger rect to ensure perfectly continuous guide lines
        row_rect = option.rect
        full_row_rect = QRect(0, row_rect.top(), view.viewport().width(), row_rect.height())
        
        if is_selected:
            painter.fillRect(full_row_rect, QColor(self.theme.get('bg_selection', '#2c2c2e')))
            # Sharp 2px accent bar
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(self.theme.get('text_bright', '#ffffff')))
            painter.drawRect(0, row_rect.top(), 2, row_rect.height())
        elif is_hover:
            painter.fillRect(full_row_rect, QColor(self.theme.get('bg_hover', '#1c1c1e')))

        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # 3. Structural Guides (Vertical Lines)
        # Precise positioning for continuous, sharp lines
        if level > 0:
            # Disable antialiasing for pixel-perfect 1px lines
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
            
            # Increase opacity for high visibility (nearly 50% white)
            guide_color = QColor(255, 255, 255, 120) 
            painter.setPen(QPen(guide_color, 0)) # Cosmetic 0-width pen is 1px sharp
            
            for i in range(1, level + 1):
                # Align guide with the vertical center of the hierarchy step
                gx = left_offset + ((i-1) * indent_width) + 4
                painter.drawLine(gx, row_rect.top(), gx, row_rect.bottom())
                
            # Re-enable for the rest
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # 4. Chevron (Arrow)
        has_children = model.hasChildren(index) if hasattr(model, "hasChildren") else False
        if has_children:
            is_expanded = view.isExpanded(index) if isinstance(view, QTreeView) else False
            cy = row_rect.center().y()
            cx = chevron_x
            
            painter.setPen(QPen(QColor(self.theme.get('text_secondary', '#888888')), 1.2))
            if is_expanded:
                # ⌄ (Smaller, sharper)
                painter.drawPolyline([QPoint(cx, cy - 2), QPoint(cx + 4, cy + 2), QPoint(cx + 8, cy - 2)])
            else:
                # › (Sharper)
                painter.drawPolyline([QPoint(cx + 2, cy - 4), QPoint(cx + 6, cy), QPoint(cx + 2, cy + 4)])

        # 5. Icon Rendering
        icon = index.data(Qt.ItemDataRole.DecorationRole)
        icon_rect = QRect(icon_x, row_rect.center().y() - 8, icon_size, icon_size)
        if isinstance(icon, QIcon):
            icon.paint(painter, icon_rect, Qt.AlignmentFlag.AlignCenter)
            
        # 6. Text Rendering
        text = index.data(Qt.ItemDataRole.DisplayRole)
        text_color = QColor(self.theme.get('text_bright' if is_selected else 'sidebar_fg', '#ffffff'))
        text_rect = QRect(text_x, row_rect.top(), row_rect.width() - text_x, row_rect.height())
        
        painter.setFont(option.font)
        painter.setPen(text_color)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)
        
        painter.restore()

    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        size.setHeight(24) # Standard VS Code row height
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


class SectionHeader(QWidget):
    """Collapsible section header with a slim chevron."""
    
    toggled = pyqtSignal(bool)

    def __init__(self, title: str, theme: dict, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.title = title
        self._expanded = True
        self.setFixedHeight(24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 8, 0)
        layout.setSpacing(4)

        self.chevron = QLabel()
        self.chevron.setFixedSize(16, 16)
        self.chevron.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._expanded = True
        self._update_chevron()
        layout.addWidget(self.chevron)
        
        self.label = QLabel(title)
        font = QFont("Segoe UI", 10, QFont.Weight.Normal)
        font.setFamilies(["Segoe UI", "SF Pro Text", "Helvetica Neue", "Arial", "sans-serif"])
        self.label.setFont(font)
        self.label.setStyleSheet(f"color: {theme['text_secondary']};")
        layout.addWidget(self.label)
        
        layout.addStretch()

        # Separators
        self.setStyleSheet(f"""
            SectionHeader {{
                background-color: {theme['sidebar_bg']};
                border-top: 1px solid {theme['border']};
            }}
            SectionHeader:hover {{
                background-color: {theme['bg_hover']};
            }}
        """)

    def _update_chevron(self):
        # Draw a custom pixel-perfect stroke chevron
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(self.theme['text_secondary']), 1.8)) # Slightly thicker
        
        if self._expanded:
            # ⌄ (Stroke style)
            painter.drawPolyline([QPoint(4, 6), QPoint(8, 10), QPoint(12, 6)])
        else:
            # › (Stroke style)
            painter.drawPolyline([QPoint(6, 4), QPoint(10, 8), QPoint(6, 12)])
        
        painter.end()
        self.chevron.setPixmap(pixmap)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._expanded = not self._expanded
            self._update_chevron()
            self.toggled.emit(self._expanded)
        super().mousePressEvent(event)


class SidebarHeader(QWidget):
    """Main container header (e.g. 'Explorer')."""

    def __init__(self, title: str, theme: dict, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.setFixedHeight(35)

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(12, 0, 8, 0)
        self.layout.setSpacing(2)

        self.label = QLabel(title)
        font = QFont("Segoe UI", 11)
        font.setFamilies(["Segoe UI", "SF Pro Text", "Helvetica Neue", "Arial", "sans-serif"])
        self.label.setFont(font)
        self.label.setStyleSheet(f"color: {theme['sidebar_fg']};")
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
        p.fillRect(self.rect(), QColor(self.theme['sidebar_bg']))
        p.end()


def style_list_widget(widget, theme):
    """Helper to style list widgets consistently."""
    widget.setStyleSheet(f"""
        QListWidget {{
            background-color: {theme['sidebar_bg']};
            color: {theme['sidebar_fg']};
            border: none;
            outline: none;
        }}
        QListWidget::item {{
            height: 24px;
            padding-left: 12px;
        }}
        QListWidget::item:hover {{
            background-color: {theme['bg_hover']};
        }}
        QListWidget::item:selected {{
            background-color: {theme['bg_selection']};
            color: #000000;
        }}
    """)



class InlineCreator(QWidget):
    """Inline creation row with icon and input, VS Code style."""
    accepted = pyqtSignal(str)
    rejected = pyqtSignal()

    def __init__(self, theme, is_folder, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.is_folder = is_folder
        self._committed = False
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        # Icon
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(16, 16)
        
        icons_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "assets", "icons"
        )
        icon_file = "folder_closed.svg" if is_folder else "file_text.svg"
        icon_path = os.path.join(icons_path, icon_file)
        if os.path.exists(icon_path):
            self.icon_label.setPixmap(QIcon(icon_path).pixmap(16, 16))
        
        layout.addWidget(self.icon_label)
        
        # Input
        self.input = QLineEdit()
        self.input.setFrame(False)
        self.input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {theme['input_bg']};
                color: {theme['input_fg']};
                border: 1px solid #007acc;
                padding: 1px 4px;
                font-family: 'Segoe UI';
                font-size: 13px;
                selection-background-color: #094771;
            }}
        """)
        layout.addWidget(self.input)
        
        self.input.returnPressed.connect(self._on_accept)
        # Global click dismissal
        QApplication.instance().installEventFilter(self)
        
    def _on_accept(self):
        if not self._committed:
            text = self.input.text().strip()
            self._committed = True
            if text:
                self.accepted.emit(text)
            else:
                self.rejected.emit()
            self.hide()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseButtonPress:
            # If clicked anywhere outside this widget, commit (or cancel if empty)
            click_pos = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else event.globalPos()
            if not self.rect().contains(self.mapFromGlobal(click_pos)):
                self._on_accept()
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self._committed = True
            self.rejected.emit()
            self.hide()
        else:
            super().keyPressEvent(event)

    def setFocus(self):
        self.input.setFocus()
        self.input.selectAll()

    def setText(self, text):
        self.input.setText(text)
        self.input.selectAll()

    def text(self):
        return self.input.text()

    def hide(self):
        QApplication.instance().removeEventFilter(self)
        super().hide()


class ExplorerContainer(QFrame):
    """Container that clicks to focus the inner tree and tracks focus state."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("focused", "false")
        # Watch global focus changes for appearance updates
        QApplication.instance().focusChanged.connect(self._on_focus_changed)
        # Install a global event filter to catch clicks *anywhere* for dismissal
        QApplication.instance().installEventFilter(self)

    def mousePressEvent(self, event):
        # When clicking blank space, stay focused on the container to show the border
        self.setFocus()
        super().mousePressEvent(event)

    def eventFilter(self, obj, event):
        # If we see a mouse press anywhere in the application
        if event.type() == QEvent.Type.MouseButtonPress:
            # Check if the click is outside this container
            # We use globalPosition() if available, or pos()
            click_pos = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else event.globalPos()
            local_pos = self.mapFromGlobal(click_pos)
            
            if not self.rect().contains(local_pos):
                # Clicked outside! Remove the focus border.
                if self.property("focused") == "true":
                    self.setProperty("focused", "false")
                    self.style().unpolish(self)
                    self.style().polish(self)
        
        return super().eventFilter(obj, event)

    def _on_focus_changed(self, old, new):
        """Update border state when focus moves globally."""
        if not self.isVisible(): return
        
        # New logic: Only show the blue PANE border if the focus is on the CONTAINER itself
        # (the blank space). When clicking a file (tree), we only show the file selection.
        is_focused = (new == self)
        
        state = "true" if is_focused else "false"
        if self.property("focused") != state:
            self.setProperty("focused", state)
            self.style().unpolish(self)
            self.style().polish(self)


class FileExplorerPanel(QWidget):
    """The main 'Explorer' container with multiple sections."""

    file_opened = pyqtSignal(str)
    terminal_requested = pyqtSignal(str)

    def __init__(self, theme: dict, parent=None):
        super().__init__(parent)
        self.theme = theme
        self._root_path = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1) # 1px "gutter" for the focus border
        layout.setSpacing(0)

        # 1. Main Header
        self.header = SidebarHeader("Explorer", theme, self)
        self.header.add_action("action_new_file.svg", "New File", self.cmd_new_file)
        self.header.add_action("action_new_folder.svg", "New Folder", self.cmd_new_folder)
        self.header.add_action("action_refresh.svg", "Refresh", self.cmd_refresh)
        self.header.add_action("action_collapse.svg", "Collapse All", self.cmd_collapse_all)
        layout.addWidget(self.header)

        # 2. Open Editors Section
        self.editors_header = SectionHeader("Open Editors", theme, self)
        layout.addWidget(self.editors_header)
        
        self.editors_list = QListWidget()
        self.editors_list.setMinimumHeight(0)
        self.editors_list.setMaximumHeight(200)
        style_list_widget(self.editors_list, theme)
        self.editors_list.itemDoubleClicked.connect(self._on_editor_item_double_clicked)
        self.editors_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.editors_list)
        self.editors_header.toggled.connect(self._toggle_editors_visibility)
        self._update_editor_list_height() # Initial height (0)

        # 3. Project Section
        self.folder_header = SectionHeader("No Folder", theme, self)
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

        # Tree view wrapper for Focus Border
        self.tree_container = ExplorerContainer()
        self.tree_container.setObjectName("explorerContainer")
        container_layout = QVBoxLayout(self.tree_container)
        container_layout.setContentsMargins(1, 1, 1, 1)
        container_layout.setSpacing(0)
        
        self.tree = QTreeView()
        self.tree.setObjectName("explorerTree")
        self.tree.setModel(self.model)
        self.tree.setItemDelegate(ExplorerDelegate(theme, self.tree))
        self.tree.setHeaderHidden(True)
        self.tree.setAnimated(True)
        self.tree.setIndentation(0) # We handle indentation manually in the delegate
        self.tree.setRootIsDecorated(False) # Disable native arrows
        self.tree.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
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
        self.tree.setFont(QFont("Segoe UI", 10))
        
        # Style the container and tree
        self.tree_container.setStyleSheet(f"""
            QFrame#explorerContainer {{
                border: 1px solid transparent;
            }}
            QFrame#explorerContainer[focused="true"] {{
                border: 1px solid #007acc;
            }}
        """)
        
        self.tree.setStyleSheet(f"""
            QTreeView {{
                background-color: {theme['sidebar_bg']};
                color: {theme['sidebar_fg']};
                border: none;
                outline: none;
            }}
            QTreeView::item {{
                height: 24px;
                padding-left: 0px;
                border: none;
            }}
            QTreeView::item:hover {{
                background-color: {theme['bg_hover']};
            }}
            QTreeView::item:selected {{
                background-color: #094771; /* Vibrant VS Code Blue ("blue ones") */
                color: #ffffff;
            }}
            QTreeView::item:selected:!active {{
                background-color: {theme['bg_selection']}; /* Gray when inactive */
                color: {theme['text_bright']};
            }}
            QTreeView::branch {{
                background-color: transparent;
                image: none;
                border-image: none;
            }}
        """)

        container_layout.addWidget(self.tree)
        layout.addWidget(self.tree_container, 100) # Give high priority stretch
        
        # Ensure container can handle focus
        self.tree_container.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        self.folder_header.toggled.connect(self.tree_container.setVisible)

    def set_root_folder(self, path: str):
        """Set the root folder to display in the explorer."""
        self._root_path = os.path.normpath(path)
        self.model.setRootPath(self._root_path)
        self.tree.setRootIndex(self.model.index(self._root_path))
        folder_name = os.path.basename(self._root_path)
        self.folder_header.label.setText(folder_name)
        # Ensure it's expanded visually too
        if not self.folder_header._expanded:
            self.folder_header._expanded = True
            self.folder_header._update_chevron()
            self.tree.setVisible(True)

    def _toggle_editors_visibility(self, visible):
        self.editors_list.setVisible(visible)
        if visible:
            self._update_editor_list_height()

    def _update_editor_list_height(self):
        # Adjust height based on item count
        count = self.editors_list.count()
        self.editors_list.setFixedHeight(min(200, count * 24 + 4) if count > 0 else 0)

    def sync_open_editors(self, files: list[str]):
        """Update the 'Open Editors' list from the main window."""
        self.editors_list.clear()
        from PyQt6.QtWidgets import QListWidgetItem
        for f in files:
            name = os.path.basename(f)
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, f)
            # Add icon if available
            self.editors_list.addItem(item)
        self._update_editor_list_height()

    def _on_editor_item_double_clicked(self, item):
        file_path = item.data(Qt.ItemDataRole.UserRole)
        if file_path:
            self.file_opened.emit(file_path)

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
        from PyQt6.QtGui import QAction
        
        index = self.tree.indexAt(position)
        path = self.model.filePath(index) if index.isValid() else self._root_path
        is_dir = self.model.isDir(index) if index.isValid() else True
        
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {self.theme['sidebar_bg']};
                color: {self.theme['sidebar_fg']};
                border: 1px solid {self.theme['border']};
            }}
            QMenu::item:selected {{
                background-color: {self.theme['bg_selection']};
            }}
        """)
        
        # File Operations
        menu.addAction("New File", lambda: self.cmd_new_file(path if is_dir else os.path.dirname(path)))
        menu.addAction("New Folder", lambda: self.cmd_new_folder(path if is_dir else os.path.dirname(path)))
        menu.addSeparator()
        
        # Actions for everything
        menu.addAction("Reveal in File Explorer", lambda: self.cmd_reveal(path))
        menu.addAction("Open in Integrated Terminal", lambda: self.cmd_open_terminal(path if is_dir else os.path.dirname(path)))
        menu.addSeparator()
        
        # Premium/Pro placeholders
        menu.addAction("Share", lambda: print("Share requested")).setEnabled(False)
        menu.addSeparator()

        menu.addAction("Add Folder to Workspace...", lambda: print("Add to workspace")).setEnabled(False)
        menu.addAction("Open Folder Settings", lambda: print("Folder settings")).setEnabled(False)
        menu.addAction("Remove Folder from Workspace", lambda: print("Remove from workspace")).setEnabled(False)
        menu.addSeparator()

        menu.addAction("Find in Folder...", lambda: print("Find in folder requested")).setEnabled(index.isValid() and is_dir)
        menu.addSeparator()
        
        menu.addAction("Paste", lambda: print("Paste requested")).setEnabled(False)
        menu.addSeparator()
        
        menu.addAction("Copy Path", lambda: self.cmd_copy_path(path))
        menu.addAction("Copy Relative Path", lambda: self.cmd_copy_relative_path(path))
        
        if index.isValid():
            menu.addSeparator()
            menu.addAction("Rename", lambda: self.cmd_rename(index))
            menu.addAction("Delete", lambda: self.cmd_delete(index))
            
        menu.exec(self.tree.viewport().mapToGlobal(position))

    def cmd_reveal(self, path):
        """Open the file location in system explorer."""
        if os.path.exists(path):
            if os.name == 'nt':
                os.startfile(os.path.dirname(path) if not os.path.isdir(path) else path)
            else:
                import subprocess
                subprocess.run(['open' if sys.platform == 'darwin' else 'xdg-open', os.path.dirname(path)])

    def cmd_open_terminal(self, path):
        """Request opening a terminal at the specified path."""
        self.terminal_requested.emit(path)

    def cmd_copy_path(self, path):
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(path)

    def cmd_copy_relative_path(self, path):
        if self._root_path:
            rel = os.path.relpath(path, self._root_path)
            from PyQt6.QtWidgets import QApplication
            QApplication.clipboard().setText(rel)

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

    # Explorer Actions
    def cmd_new_file(self, base_path=None):
        self._start_inline_creation(base_path, is_folder=False)

    def cmd_new_folder(self, base_path=None):
        self._start_inline_creation(base_path, is_folder=True)

    def cmd_rename(self, index: QModelIndex):
        if not index.isValid(): return
        old_path = self.model.filePath(index)
        base_dir = os.path.dirname(old_path)
        old_name = os.path.basename(old_path)

        # Instead of QInputDialog, use the inline editor!
        self._start_inline_creation(base_dir, is_folder=self.model.isDir(index), rename_index=index)

    def _start_inline_creation(self, base_path, is_folder, rename_index=None):
        target_dir = base_path or self._root_path
        if not target_dir: return

        # 1. Determine index and level
        parent_index = self.model.index(target_dir) if not rename_index else rename_index.parent()
        item_index = rename_index if rename_index else None
        
        # Ensure expanded if it's a folder
        if parent_index.isValid() and self.model.isDir(parent_index):
            self.tree.expand(parent_index)

        # Calculate level for indent
        level = 0
        
        if item_index:
            # Renaming: calculate the level of the item being renamed
            temp = item_index
            while temp.parent().isValid() and temp.parent() != self.tree.rootIndex():
                temp = temp.parent()
                level += 1
        else:
            # Creating: calculate the level where the NEW item will appear
            # (one level deeper than the parent folder)
            temp = parent_index
            while temp.isValid() and temp != self.tree.rootIndex():
                temp = temp.parent()
                level += 1

        # Calculate Position  
        row_y = 0
        parent_widget = self.tree.viewport()  # Default parent
        
        if item_index:
            # Renaming: position directly over the item
            row_y = self.tree.visualRect(item_index).top()
        elif target_dir == self._root_path:
            # Root creation: insert spacer to push tree down (VS Code style)
            tree_container_layout = self.tree.parent().layout()
            if tree_container_layout:
                self._push_spacer = QWidget()
                self._push_spacer.setFixedHeight(24)
                self._push_spacer.setStyleSheet(f"background-color: {self.theme['sidebar_bg']};")
                tree_container_layout.insertWidget(0, self._push_spacer)
                parent_widget = self._push_spacer  # Parent to spacer so input appears inside it
                row_y = 1  # Small offset from top of spacer
        else:
            # Folder creation: position just after the folder header  
            row_y = self.tree.visualRect(parent_index).bottom()
            
        # Create or update the editor
        if hasattr(self, 'inline_editor'):
            self.inline_editor.deleteLater()
            
        self.inline_editor = InlineCreator(self.theme, is_folder, parent_widget)
        self.inline_editor.rejected.connect(self._cancel_inline_creation)
        
        if rename_index:
            old_name = os.path.basename(self.model.filePath(rename_index))
            self.inline_editor.setText(old_name)
            self.inline_editor.accepted.connect(lambda name: self._finish_rename(rename_index, name))
        else:
            self.inline_editor.accepted.connect(lambda name: self._finish_inline_creation(target_dir, name, is_folder))

        # Indent measurements
        indent_width = 12
        left_offset = 6
        icon_x = left_offset + (level * indent_width) + 16

        width = self.tree.viewport().width() - icon_x - 10
        self.inline_editor.setGeometry(icon_x, row_y + 1, width, 22)
        self.inline_editor.show()
        self.inline_editor.setFocus()

    def _cancel_inline_creation(self):
        # Clean up inline editor FIRST (before deleting its potential parent)
        if hasattr(self, 'inline_editor'):
            self.inline_editor.hide()
            self.inline_editor.deleteLater()
            del self.inline_editor
        
        # Then remove push spacer
        if hasattr(self, '_push_spacer'):
            self._push_spacer.deleteLater()
            del self._push_spacer

    def _finish_rename(self, index, new_name):
        self._cancel_inline_creation()
        if not index.isValid() or not new_name: return
        
        old_path = self.model.filePath(index)
        if os.path.basename(old_path) == new_name: return
        
        new_path = os.path.join(os.path.dirname(old_path), new_name)
        try:
            os.rename(old_path, new_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not rename: {e}")

    def _finish_inline_creation(self, target_dir, name, is_folder):
        self._cancel_inline_creation()
        if not name: return

        path = os.path.join(target_dir, name)
        try:
            if is_folder:
                os.makedirs(path, exist_ok=True)
            else:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                open(path, 'a').close()
                self.file_opened.emit(path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not create {'folder' if is_folder else 'file'}: {e}")

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
    terminal_requested = pyqtSignal(str)

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
        self.explorer_panel.terminal_requested.connect(self.terminal_requested.emit)
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
