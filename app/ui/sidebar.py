import os
import sys
import subprocess
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QTreeView, QLineEdit, QFrame, QApplication,
                              QStackedWidget, QPushButton, QTreeWidget,
                              QTreeWidgetItem, QSizePolicy, QAbstractItemView,
                              QFileIconProvider, QInputDialog, QMessageBox, QMenu,
                              QStyledItemDelegate, QStyleOptionViewItem, QListWidget, QStyle,
                              QScrollArea)
from PyQt6.QtCore import pyqtSignal, Qt, QDir, QModelIndex, QFileInfo, QSize, QPoint, QRect, QEvent, QTimer
from PyQt6.QtGui import QFont, QColor, QPainter, QFileSystemModel, QIcon, QPen, QPixmap, QCursor
import shutil


class ExplorerDelegate(QStyledItemDelegate):
    """Custom delegate to draw indentation guides and modern chevrons."""
    def __init__(self, theme: dict, section=None, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.section = section

    def paint(self, painter, option, index):
        # If this is the row being expanded for creation, only draw in the top half
        actual_rect = option.rect
        if self.section and self.section.creating_parent == index:
            # The sizeHint was doubled, we draw the folder content in the top half
            row_h = actual_rect.height() // 2
            option.rect = QRect(actual_rect.left(), actual_rect.top(), actual_rect.width(), row_h)
        
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

        # 3. Draw Indentation Guides (VS Code Style)
        # Disable AA for sharp 1px lines
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.setPen(QPen(QColor(self.theme.get('indent_guide', '#404040')), 1))
        for i in range(level):
            gx = left_offset + (i * indent_width) + 4
            painter.drawLine(gx, row_rect.top(), gx, row_rect.bottom())

        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # 4. Chevron (Arrow)
        has_children = model.hasChildren(index) if hasattr(model, "hasChildren") else False
        if has_children:
            is_expanded = view.isExpanded(index) if isinstance(view, QTreeView) else False
            cy = row_rect.center().y()
            cx = chevron_x
            
            painter.setPen(QPen(QColor(self.theme.get('text_secondary', '#888888')), 1.2))
            if is_expanded:
                painter.drawPolyline([QPoint(cx, cy - 2), QPoint(cx + 4, cy + 2), QPoint(cx + 8, cy - 2)])
            else:
                painter.drawPolyline([QPoint(cx + 2, cy - 4), QPoint(cx + 6, cy), QPoint(cx + 2, cy + 4)])

        # 5. Icon Rendering
        # If we are renaming, don't show text or icon? In VS Code, the icon stays.
        icon = index.data(Qt.ItemDataRole.DecorationRole)
        icon_rect = QRect(icon_x, row_rect.center().y() - 8, icon_size, icon_size)
        if isinstance(icon, QIcon):
            icon.paint(painter, icon_rect, Qt.AlignmentFlag.AlignCenter)
            
        # 6. Text Rendering
        if not (self.section and self.section.editing_index == index):
            text = index.data(Qt.ItemDataRole.DisplayRole)
            path = os.path.normpath(model.filePath(index))
            
            # SCM Status logic
            status = None
            scm_dict = self.section.scm_status if self.section else {}
            
            # 1. Direct status (for files or exact folder match)
            if path in scm_dict:
                status = scm_dict[path]
            
            # 2. Inherited status for folders
            is_dir = model.isDir(index)
            if is_dir and not status:
                dir_path_with_sep = path + os.sep
                for p in scm_dict:
                    if p.startswith(dir_path_with_sep):
                        # Inherit 'M' if any child is changed
                        status = 'MOD_CHILD' 
                        break
            
            # Colors from user request
            scm_colors = {
                'M': '#e2c08d', 'A': '#73c991', 'D': '#c74e39',
                'U': '#73c991', 'R': '#4ec9b0', 'C': '#4ec9b0', 
                '?': '#73c991', 'MOD_CHILD': '#e2c08d'
            }
            
            text_color = QColor(self.theme.get('text_bright' if is_selected else 'sidebar_fg', '#ffffff'))
            if status and not is_selected:
                text_color = QColor(scm_colors.get(status, '#ffffff'))
            
            text_rect = QRect(text_x, row_rect.top(), row_rect.width() - text_x - 30, row_rect.height())
            
            painter.setFont(option.font)
            painter.setPen(text_color)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)
            
            # 7. Draw status letter or dot on the right
            if status:
                right_rect = QRect(view.viewport().width() - 25, row_rect.top(), 20, row_rect.height())
                painter.setOpacity(0.8)
                if status == 'MOD_CHILD':
                    # Draw a small dot for folders with modified children
                    painter.setBrush(QColor(scm_colors[status]))
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawEllipse(right_rect.center(), 3, 3)
                else:
                    # Draw the status char
                    painter.drawText(right_rect, Qt.AlignmentFlag.AlignCenter, status)
                painter.setOpacity(1.0)
        
        painter.restore()

    def sizeHint(self, option, index):
        # Enforce strict 24px height for compact VS Code-like layout
        h = 24
        size = super().sizeHint(option, index)
        if self.section and self.section.creating_parent == index:
            return QSize(size.width(), h * 2) # Double height for the creation gap
        return QSize(size.width(), h)


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
        if not ext and info.fileName().startswith('.'): # Handle .env, .gitignore
            ext = info.fileName()[1:].lower()

        # 1. Precise Mapping (Hierarchical)
        icon_name = {
            # Web & Logic
            "py": "file_python.svg", "pyw": "file_python.svg", "pyi": "file_python.svg",
            "js": "file_js.svg", "mjs": "file_js.svg", "cjs": "file_js.svg",
            "ts": "file_typescript.svg", "mts": "file_typescript.svg", "cts": "file_typescript.svg",
            "tsx": "file_tsx.svg", "jsx": "file_react.svg",
            "html": "file_html.svg", "htm": "file_html.svg", "xhtml": "file_html.svg",
            "css": "file_css.svg", "scss": "file_scss.svg", "sass": "file_sass.svg", "less": "file_less.svg",
            "vue": "file_vue.svg", "svelte": "file_svelte.svg", "astro": "file_astro.svg",
            "php": "file_php.svg", "rb": "file_ruby.svg", "go": "file_go.svg",
            "rs": "file_rust.svg", "java": "file_java.svg", "kt": "file_kotlin.svg",
            "cs": "file_csharp.svg", "cpp": "file_cpp.svg", "c": "file_c.svg", "h": "file_c.svg",
            "swift": "file_swift.svg", "dart": "file_dart.svg", "sh": "file_shell.svg", "zsh": "file_shell.svg",
            "ps1": "file_powershell.svg", "bat": "file_bat.svg", "cmd": "file_bat.svg",
            
            # Data & Config
            "json": "file_json.svg", "jsonc": "file_json.svg", "yaml": "file_yaml.svg", "yml": "file_yaml.svg",
            "toml": "file_toml.svg", "xml": "file_xml.svg", "sql": "file_sql.svg", "sqlite": "file_sqlite.svg",
            "db": "file_db.svg", "csv": "file_text.svg", "ini": "file_ini.svg", "cfg": "file_config.svg",
            "env": "file_env.svg", "lock": "file_config.svg",
            
            # Content
            "md": "file_markdown.svg", "txt": "file_text.svg", "log": "file_log.svg", "pdf": "file_pdf.svg",
            "svg": "file_svg.svg", "png": "file_image.svg", "jpg": "file_image.svg", "jpeg": "file_image.svg",
            "gif": "file_image.svg", "ico": "file_image.svg", "bmp": "file_image.svg",
            "mp4": "file_video.svg", "mov": "file_video.svg", "avi": "file_video.svg",
            "mp3": "file_audio.svg", "wav": "file_audio.svg", "flac": "file_audio.svg",
            "zip": "file_zip.svg", "rar": "file_zip.svg", "7z": "file_zip.svg", "tar": "file_zip.svg", "gz": "file_zip.svg",
            
            # Frameworks & Tools
            "dockerfile": "file_docker.svg", "git": "file_git.svg", "gitignore": "file_git.svg",
            "npm": "file_npm.svg", "yarn": "file_yarn.svg", "gradle": "file_gradle.svg",
            "cmake": "file_cmake.svg", "makefile": "file_config.svg",
            "ipynb": "file_jupyter.svg", "wasm": "file_wasm.svg"
        }.get(ext)

        # 2. Dynamic Fallback (check if file_{ext}.svg exists)
        if not icon_name:
            candidate = f"file_{ext}.svg"
            if os.path.exists(os.path.join(self.icons_path, candidate)):
                icon_name = candidate
            else:
                icon_name = "file_default.svg"
        
        path = os.path.join(self.icons_path, icon_name)
        return QIcon(path)


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
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

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

    def set_expanded(self, expanded: bool):
        """Programmatically set the expansion state."""
        if self._expanded != expanded:
            self._expanded = expanded
            self._update_chevron()
            self.toggled.emit(self._expanded)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.set_expanded(not self._expanded)
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
            padding-left: 6px;
        }}
        QListWidget::item:hover {{
            background-color: {theme['bg_hover']};
        }}
        QListWidget::item:selected {{
            background-color: {theme['bg_selection']};
            color: #000000;
        }}
    """)




class InputErrorPopup(QLabel):
    """VS Code style error popup that appears below the input."""
    def __init__(self, theme, text, parent=None):
        super().__init__(text, parent)
        self.theme = theme
        self.setStyleSheet(f"""
            QLabel {{
                background-color: #5a1d1d;
                color: #ce9178;
                border: 1px solid #be1100;
                padding: 6px 10px;
                font-family: 'Segoe UI';
                font-size: 13px;
            }}
        """)
        self.setWordWrap(True)
        self.adjustSize() 
    
    def show_below(self, widget):
        pos = widget.mapToGlobal(QPoint(0, widget.height()))
        pos = self.parent().mapFromGlobal(pos)
        self.move(pos.x(), pos.y() + 2) # Slight offset
        self.raise_()
        self.show()

class InlineCreator(QWidget):
    """Inline creation row with icon and input, VS Code style."""
    accepted = pyqtSignal(str)
    rejected = pyqtSignal()

    def __init__(self, theme, is_folder, parent=None, validator=None):
        super().__init__(parent)
        self.theme = theme
        self.is_folder = is_folder
        self.validator = validator # Function(text) -> str (error message) or None
        self._committed = False
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.error_popup = None
        
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
                font-size: 12px;
                selection-background-color: #094771;
            }}
        """)
        layout.addWidget(self.input)
        
        self.input.returnPressed.connect(self._on_accept)
        self.input.textChanged.connect(self._validate) # Live validation
        # Global click dismissal
        QApplication.instance().installEventFilter(self)
        
    def _validate(self, text):
        if not self.validator: return
        
        text = text.strip()
        if not text:
            if self.error_popup: self.error_popup.hide()
            # Reset style
            self.input.setStyleSheet(f"""
                QLineEdit {{
                    background-color: {self.theme['input_bg']};
                    color: {self.theme['input_fg']};
                    border: 1px solid #007acc;
                    padding: 1px 4px;
                    font-family: 'Segoe UI';
                    font-size: 12px;
                    selection-background-color: #094771;
                }}
            """)
            return

        error_msg = self.validator(text)
        if error_msg:
            self._show_error(error_msg)
        else:
            if self.error_popup: self.error_popup.hide()
            # Reset style to valid (blue border)
            self.input.setStyleSheet(f"""
                QLineEdit {{
                    background-color: {self.theme['input_bg']};
                    color: {self.theme['input_fg']};
                    border: 1px solid #007acc;
                    padding: 1px 4px;
                    font-family: 'Segoe UI';
                    font-size: 12px;
                    selection-background-color: #094771;
                }}
            """)

    def _on_accept(self):
        if not self._committed:
            text = self.input.text().strip()
            
            # Validation Logic
            if text and self.validator:
                error_msg = self.validator(text)
                if error_msg:
                    self._show_error(error_msg)
                    return # Block commit

            self._committed = True
            if text:
                self.accepted.emit(text)
            else:
                self.rejected.emit()
            self.hide()

    def _show_error(self, msg):
        if self.error_popup:
            self.error_popup.deleteLater()
        
        # Style input red
        self.input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.theme['input_bg']};
                color: {self.theme['input_fg']};
                border: 1px solid #be1100; /* Red border */
                padding: 1px 4px;
                font-family: 'Segoe UI';
                font-size: 12px;
                selection-background-color: #094771;
            }}
        """)
        
        self.error_popup = InputErrorPopup(self.theme, msg, self.parent()) # Parent to same as InlineCreator
        self.error_popup.show_below(self)

    def hide(self):
        if self.error_popup:
            self.error_popup.deleteLater()
        QApplication.instance().removeEventFilter(self)
        super().hide()

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
        
        # Only show the blue PANE border if the focus is on the CONTAINER itself
        # (the blank space). When clicking a file (tree), we only show the file selection.
        is_focused = (new == self)
        
        state = "true" if is_focused else "false"
        if self.property("focused") != state:
            self.setProperty("focused", state)
            self.style().unpolish(self)
            self.style().polish(self)


class ProjectSection(QWidget):
    """Encapsulates a single project folder section in the explorer."""
    file_opened = pyqtSignal(str)
    terminal_requested = pyqtSignal(str)
    find_in_folder_requested = pyqtSignal(str)
    workspace_action_requested = pyqtSignal(str, str)
    file_close_requested = pyqtSignal(str) # Request main window to close tab
    expansion_changed = pyqtSignal()

    def __init__(self, path: str, theme: dict, parent=None):
        super().__init__(parent)
        self.theme = theme
        self._parent_panel = parent
        self._root_path = os.path.normpath(path)
        self.creating_parent = None
        self.editing_index = None
        
        # SCM Status indicators
        self.scm_status = {} # abs_path -> status_char
        from app.core.git_manager import GitManager
        self.git = GitManager()
        self.git.detect_repo(self._root_path)
        
        self.scm_timer = QTimer(self)
        self.scm_timer.timeout.connect(self._refresh_scm_status)
        self.scm_timer.start(5000) # Refresh every 5 seconds
        QTimer.singleShot(500, self._refresh_scm_status) # Initial refresh
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. Section Header
        folder_name = os.path.basename(self._root_path)
        self.header = SectionHeader(folder_name, theme, self)
        layout.addWidget(self.header)

        # 2. File System Model
        self.model = QFileSystemModel()
        self.model.setReadOnly(False) # Enable dragging
        self.model.setIconProvider(VSCodeIconProvider(theme))
        self.model.setRootPath(self._root_path)

        # 3. Tree View Container (for focus border)
        self.tree_container = ExplorerContainer()
        self.tree_container.setObjectName("explorerContainer")
        container_layout = QVBoxLayout(self.tree_container)
        container_layout.setContentsMargins(1, 1, 1, 1)
        container_layout.setSpacing(0)
        
        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setItemDelegate(ExplorerDelegate(theme, self, self.tree))
        self.tree.setHeaderHidden(True)
        self.tree.setAnimated(True)
        self.tree.setIndentation(0)
        self.tree.setRootIsDecorated(False)
        self.tree.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tree.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        
        # Hide columns except name
        for i in range(1, 4):
            self.tree.setColumnHidden(i, True)
            
        self.tree.setRootIndex(self.model.index(self._root_path))
        self.tree.clicked.connect(self._on_item_clicked)
        self.tree.expanded.connect(self._on_item_expanded)
        self.tree.collapsed.connect(self._on_item_collapsed)
        
        # Context menu
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)

        # Key & Mouse Handling
        self.tree.keyPressEvent = self._tree_key_press
        self.tree.mousePressEvent = self._tree_mouse_press
        
        # Drag and Drop
        self.tree.setDragEnabled(True)
        self.tree.setAcceptDrops(True)
        self.tree.setDropIndicatorShown(True)
        self.tree.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.tree.dragEnterEvent = self._tree_drag_enter
        self.tree.dragMoveEvent = self._tree_drag_move
        self.tree.dropEvent = self._tree_drop

        # Styling
        self.tree.setFont(QFont("Segoe UI", 10))
        self._apply_styles()

        container_layout.addWidget(self.tree)
        layout.addWidget(self.tree_container, 1) # Internal stretch
        
        # Toggle visibility
        self.header.toggled.connect(self._handle_toggle)
        # Header context menu
        self.header.customContextMenuRequested.connect(self._show_context_menu)

    def _handle_toggle(self, expanded):
        self.tree_container.setVisible(expanded)
        self.expansion_changed.emit()

    def _apply_styles(self):
        theme = self.theme
        self.tree_container.setStyleSheet(f"""
            QFrame#explorerContainer {{ border: 1px solid transparent; }}
            QFrame#explorerContainer[focused="true"] {{ border: 1px solid #007acc; }}
        """)
        self.tree.setStyleSheet(f"""
            QTreeView {{
                background-color: {theme['sidebar_bg']};
                color: {theme['sidebar_fg']};
                border: none;
                outline: none;
            }}
            QTreeView::item {{ height: 24px; padding-left: 0px; border: none; }}
            QTreeView::item:hover {{ background-color: {theme['bg_hover']}; }}
            QTreeView::item:selected {{ background-color: #094771; color: #ffffff; }}
            QTreeView::item:selected:!active {{ background-color: {theme['bg_selection']}; color: {theme['text_bright']}; }}
            QTreeView::branch {{ background-color: transparent; image: none; border-image: none; }}
        """)

    def _tree_mouse_press(self, event):
        """Handle clicks on the tree, including deselecting on empty space."""
        index = self.tree.indexAt(event.pos())
        if not index.isValid():
            # Clicked blank space! Deselect everything.
            self.tree.clearSelection()
            self.tree.setCurrentIndex(QModelIndex())
            # Ensure the container gets focus for the blue border highlight
            self.tree_container.setFocus()
            return
            
        # Call base implementation for normal item selection
        QTreeView.mousePressEvent(self.tree, event)

    def _tree_drag_enter(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            QTreeView.dragEnterEvent(self.tree, event)

    def _tree_drag_move(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            QTreeView.dragMoveEvent(self.tree, event)

    def _tree_drop(self, event):
        """Handle dropping files/folders onto the tree."""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if not urls: return
            
            source_path = urls[0].toLocalFile()
            if not source_path or not os.path.exists(source_path): return
            
            # Determine target directory
            index = self.tree.indexAt(event.position().toPoint())
            if index.isValid():
                target_path = self.model.filePath(index)
                if not os.path.isdir(target_path):
                    target_path = os.path.dirname(target_path)
            else:
                target_path = self._root_path
                
            # Perform the move
            try:
                base = os.path.basename(source_path)
                dest = os.path.join(target_path, base)
                
                if source_path.lower() == dest.lower():
                    # Same location or just case change (on Windows)
                    return
                    
                if os.path.exists(dest):
                    # Check if it's the same file (same inode/stat)
                    if os.path.abspath(source_path) == os.path.abspath(dest):
                        return
                    QMessageBox.warning(self, "Move Error", f"'{base}' already exists in '{os.path.basename(target_path)}'.")
                    return

                # Ask for confirmation
                reply = QMessageBox.question(
                    self, "Confirm Move",
                    f"Are you sure you want to move '{base}' to '{os.path.basename(target_path)}'?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                if reply != QMessageBox.StandardButton.Yes:
                    return

                # Perform the filesystem move
                shutil.move(source_path, dest)
                event.acceptProposedAction()
                
            except Exception as e:
                QMessageBox.critical(self, "Move Error", f"Failed to move: {e}")
        else:
            QTreeView.dropEvent(self.tree, event)

    def _tree_key_press(self, event):
        if event.key() == Qt.Key.Key_Delete:
            idx = self.tree.currentIndex()
            if idx.isValid(): self.cmd_delete(idx)
        else:
            QTreeView.keyPressEvent(self.tree, event)

    def _on_item_clicked(self, index):
        path = self.model.filePath(index)
        if not self.model.isDir(index):
            self.file_opened.emit(path)
        else:
            # Toggle expansion on single click (VS Code behavior)
            if self.tree.isExpanded(index):
                self.tree.collapse(index)
            else:
                self.tree.expand(index)

    def _on_item_expanded(self, index):
        self._set_folder_icon(index, "folder_open.svg")

    def _on_item_collapsed(self, index):
        self._set_folder_icon(index, "folder_closed.svg")

    def _set_folder_icon(self, index, icon_name):
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                                 "assets", "icons", icon_name)
        if os.path.exists(icon_path):
            self.model.setData(index, QIcon(icon_path), Qt.ItemDataRole.DecorationRole)

    def _show_context_menu(self, position):
        index = self.tree.indexAt(position)
        path = self.model.filePath(index) if index.isValid() else self._root_path
        is_dir = self.model.isDir(index) if index.isValid() else True
        
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{ background-color: {self.theme['sidebar_bg']}; color: {self.theme['sidebar_fg']}; border: 1px solid {self.theme['border']}; }}
            QMenu::item:selected {{ background-color: {self.theme['bg_selection']}; }}
        """)
        
        # 1. Creation
        menu.addAction("New File", lambda: self.cmd_new_file(path if is_dir else os.path.dirname(path)))
        menu.addAction("New Folder", lambda: self.cmd_new_folder(path if is_dir else os.path.dirname(path)))
        menu.addSeparator()

        # 2. Open & System
        menu.addAction("Open to the Side", lambda: self.file_opened.emit(path))
        menu.addAction("Reveal in File Explorer", lambda: self.cmd_reveal(path))
        menu.addAction("Open in Integrated Terminal", lambda: self.terminal_requested.emit(path if is_dir else os.path.dirname(path)))
        menu.addSeparator()

        # 3. Workspace Operations
        if is_dir:
            menu.addAction("Add Folder to Workspace...", lambda: self.workspace_action_requested.emit("add_folder", path))
            menu.addAction("Open Folder Settings", lambda: self.cmd_open_folder_settings(path))
            if path == self._root_path:
                menu.addAction("Remove Folder from Workspace", lambda: self.workspace_action_requested.emit("remove_folder", path))
            
            menu.addSeparator()
            menu.addAction("Find in Folder...", lambda: self.find_in_folder_requested.emit(path))
            menu.addSeparator()

        # 4. Compare & Pro
        menu.addAction("Select for Compare").setEnabled(False)
        menu.addAction("Compare with Selected").setEnabled(False)
        menu.addSeparator()

        # 5. Clipboard/Paths
        menu.addAction("Copy Path", lambda: QApplication.clipboard().setText(path))
        menu.addAction("Copy Relative Path", lambda: self.cmd_copy_relative_path(path))
        menu.addAction("Copy Name", lambda: QApplication.clipboard().setText(os.path.basename(path)))
        menu.addSeparator()

        # 6. Clipboard Actions (Logical)
        menu.addAction("Cut", lambda: self.cmd_cut(path)).setEnabled(index.isValid())
        menu.addAction("Copy", lambda: self.cmd_copy(path)).setEnabled(index.isValid())
        
        # Paste is only enabled if we are over a directory or at root, and there's something in clipboard
        can_paste = self._parent_panel._clipboard_source is not None and is_dir
        paste_act = menu.addAction("Paste", lambda: self.cmd_paste(path))
        paste_act.setEnabled(can_paste)

        # 7. Editing
        if index.isValid():
            menu.addSeparator()
            menu.addAction("Rename", lambda: self.cmd_rename(index))
            menu.addAction("Delete", lambda: self.cmd_delete(index))
            
        menu.exec(QCursor.pos())

    # --- Commands (Moved from FileExplorerPanel) ---
    def cmd_open_folder_settings(self, path):
        import json
        vscode_dir = os.path.join(path, ".vscode")
        settings_file = os.path.join(vscode_dir, "settings.json")
        try:
            os.makedirs(vscode_dir, exist_ok=True)
            if not os.path.exists(settings_file):
                with open(settings_file, "w") as f: json.dump({}, f, indent=4)
            self.file_opened.emit(settings_file)
        except Exception: pass

    def cmd_copy_relative_path(self, path):
        if self._root_path:
            rel = os.path.relpath(path, self._root_path)
            from PyQt6.QtWidgets import QApplication
            QApplication.clipboard().setText(rel)
    def cmd_new_file(self, base_path=None):
        self._start_inline_creation(base_path, is_folder=False)
    def cmd_new_folder(self, base_path=None):
        self._start_inline_creation(base_path, is_folder=True)
    def cmd_rename(self, index):
        if not index.isValid(): return
        old_path = self.model.filePath(index)
        self._start_inline_creation(os.path.dirname(old_path), is_folder=self.model.isDir(index), rename_index=index)

    def cmd_delete(self, index):
        if not index.isValid(): return
        path = self.model.filePath(index)
        confirm = QMessageBox.question(self, "Delete", f"Are you sure you want to delete '{os.path.basename(path)}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            # Emit signal to close tab first (releases file lock)
            self.file_close_requested.emit(path)
            
            try:
                if os.path.isdir(path):
                    import shutil
                    shutil.rmtree(path)
                else:
                    os.remove(path)
            except Exception as e:
                QMessageBox.critical(self, "Delete Error", f"Could not delete: {e}")

    def cmd_copy(self, path):
        self._parent_panel._clipboard_source = path
        self._parent_panel._clipboard_op = 'copy'

    def cmd_cut(self, path):
        self._parent_panel._clipboard_source = path
        self._parent_panel._clipboard_op = 'cut'

    def cmd_paste(self, dest_dir):
        source = self._parent_panel._clipboard_source
        op = self._parent_panel._clipboard_op
        if not source or not os.path.exists(source):
            return

        base = os.path.basename(source)
        dest = os.path.join(dest_dir, base)

        # Avoid pasting into self or child
        if os.path.abspath(dest_dir).startswith(os.path.abspath(source)):
            QMessageBox.warning(self, "Paste Error", "Cannot paste a folder into itself or its subfolder.")
            return

        # Collision handling
        if os.path.exists(dest):
            if op == 'cut' and os.path.abspath(source) == os.path.abspath(dest):
                return # Same place
            
            name, ext = os.path.splitext(base)
            counter = 1
            while os.path.exists(dest):
                dest = os.path.join(dest_dir, f"{name} (Copy {counter}){ext}" if counter > 1 else f"{name} (Copy){ext}")
                counter += 1

        try:
            import shutil
            if op == 'copy':
                if os.path.isdir(source):
                    shutil.copytree(source, dest)
                else:
                    shutil.copy2(source, dest)
            else: # cut
                # Close file if it's open (releases lock for move)
                self.file_close_requested.emit(source)
                shutil.move(source, dest)
                # Clear cut state
                self._parent_panel._clipboard_source = None
                self._parent_panel._clipboard_op = None
        except Exception as e:
            QMessageBox.critical(self, "Paste Error", f"Could not paste: {e}")

    def cmd_reveal(self, path):
        if not path or not os.path.exists(path): return
        if os.name == 'nt':
            subprocess.Popen(f'explorer /select,"{os.path.normpath(path)}"', shell=True)
        elif sys.platform == 'darwin':
            subprocess.call(['open', '-R', path])
        else:
            subprocess.call(['xdg-open', os.path.dirname(path)])

    def cmd_refresh(self):
        """Force a reload of the file system model."""
        self.model.setRootPath("")
        self.model.setRootPath(self._root_path)

    def cmd_collapse_all(self):
        """Collapse all folders in the project tree."""
        self.tree.collapseAll()

    def _start_inline_creation(self, base_path, is_folder, rename_index=None):
        target_dir = base_path or self._root_path
        if not target_dir: return

        # Calculate level and position
        parent_index = self.model.index(target_dir) if not rename_index else rename_index.parent()
        if parent_index.isValid() and self.model.isDir(parent_index):
            self.tree.expand(parent_index)

        # Set state for delegate
        if rename_index: self.editing_index = rename_index
        else: self.creating_parent = parent_index
        
        # Force re-calculating row heights (sizeHint)
        self.tree.updateGeometries()
        # Emit dataChanged to force the tree to re-query sizeHint for the parent
        self.model.dataChanged.emit(parent_index, parent_index)

        level = 0
        temp = rename_index if rename_index else parent_index
        while temp.isValid() and temp != self.tree.rootIndex():
            temp = temp.parent()
            level += 1
        if not rename_index: level += 1

        row_y = 0
        parent_widget = self.tree.viewport()

        if rename_index:
            row_y = self.tree.visualRect(rename_index).top()
        elif target_dir == self._root_path:
            # Detect root-level creation and use the physical spacer
            if not hasattr(self, '_push_spacer') or not self._push_spacer:
                container_layout = self.tree.parent().layout()
                if container_layout:
                    self._push_spacer = QWidget()
                    self._push_spacer.setFixedHeight(24)
                    self._push_spacer.setStyleSheet(f"background-color: {self.theme['sidebar_bg']};")
                    container_layout.insertWidget(0, self._push_spacer)
            parent_widget = self._push_spacer
            row_y = 1
        else:
            # SUB-FOLDER: Use the sizeHint gap (below parent's content)
            parent_rect = self.tree.visualRect(parent_index)
            # The gap starts after the first 'half' of the parent's doubled-height row
            row_y = parent_rect.top() + (parent_rect.height() // 2)

        self.inline_editor = InlineCreator(self.theme, is_folder, parent_widget)
        if rename_index:
            self.inline_editor.setText(os.path.basename(self.model.filePath(rename_index)))
            self.inline_editor.accepted.connect(lambda name: self._finish_rename(rename_index, name))
        else:
            self.inline_editor.accepted.connect(lambda name: self._finish_inline_creation(target_dir, name, is_folder))
        
        self.inline_editor.rejected.connect(self._cancel_inline_creation)
        
        # Position it
        indent_width = 12
        left_offset = 6
        icon_x = left_offset + (level * indent_width) + 16
        width = self.tree.viewport().width() - icon_x - 10
        # For root level, the Y is relative to the spacer, not the viewport
        self.inline_editor.setGeometry(icon_x, row_y, width, 22)
        self.inline_editor.show()
        self.inline_editor.setFocus()

    scm_count_changed = pyqtSignal(int)

    def _refresh_scm_status(self):
        """Fetch git status and update the explorer visual state."""
        if not self.git.repo_root:
            if not self.git.detect_repo(self._root_path):
                return
        
        try:
            status_list = self.git.status()
            new_status = {}
            for item in status_list:
                new_status[os.path.normpath(item.abs_path)] = item.display_status
            
            # Emit total changed files count
            self.scm_count_changed.emit(len(status_list))
            
            if new_status != self.scm_status:
                self.scm_status = new_status
                # Request repaint of the entire tree to show new status colors/letters
                self.tree.viewport().update()
        except Exception:
            pass

    def _cancel_inline_creation(self):
        old_parent = self.creating_parent
        self.creating_parent = None
        self.editing_index = None
        
        # Force the tree to re-query row heights
        self.tree.doItemsLayout()
        self.tree.updateGeometries()
        
        # Notify the model/tree that the old parent is back to normal height
        if old_parent and old_parent.isValid():
            self.model.dataChanged.emit(old_parent, old_parent)
            
        if hasattr(self, 'inline_editor'):
            self.inline_editor.hide()
            self.inline_editor.deleteLater()
            del self.inline_editor
            
        if hasattr(self, '_push_spacer') and self._push_spacer:
            self._push_spacer.setParent(None)
            self._push_spacer.deleteLater()
            self._push_spacer = None

    def _finish_rename(self, index, new_name):
        self._cancel_inline_creation()
        if not index.isValid() or not new_name: return
        old_path = self.model.filePath(index)
        new_path = os.path.join(os.path.dirname(old_path), new_name)
        try: os.rename(old_path, new_path)
        except Exception as e: QMessageBox.critical(self, "Error", f"Could not rename: {e}")

    def _finish_inline_creation(self, target_dir, name, is_folder):
        self._cancel_inline_creation()
        if not name: return
        path = os.path.abspath(os.path.join(target_dir, name))
        try:
            if is_folder: os.makedirs(path, exist_ok=True)
            else:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, 'a'): pass
                self.file_opened.emit(path)
        except Exception as e: QMessageBox.critical(self, "Error", f"Could not create: {e}")

    def highlight_file(self, path):
        """Highlight and reveal the file in the tree."""
        if not path: return
        index = self.model.index(path)
        if index.isValid():
            # Manually expand all parent indices to reveal the file
            parent = index.parent()
            while parent.isValid() and parent != self.tree.rootIndex():
                self.tree.expand(parent)
                parent = parent.parent()
            
            self.tree.setCurrentIndex(index)
            self.tree.scrollTo(index)


class FileExplorerPanel(QWidget):
    """The main 'Explorer' container with multiple sections."""

    file_opened = pyqtSignal(str)
    terminal_requested = pyqtSignal(str)
    find_in_folder_requested = pyqtSignal(str)
    workspace_action_requested = pyqtSignal(str, str)
    file_close_requested = pyqtSignal(str)

    def __init__(self, theme: dict, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.projects = []
        self.icon_provider = VSCodeIconProvider(theme)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Shared clipboard for all projects
        self._clipboard_source = None # path
        self._clipboard_op = None     # 'copy' or 'cut'

        # 1. Main Header
        self.header = SidebarHeader("Explorer", theme, self)
        self.header.add_action("action_new_file.svg", "New File", lambda: self._on_global_new_file())
        self.header.add_action("action_new_folder.svg", "New Folder", lambda: self._on_global_new_folder())
        self.header.add_action("action_refresh.svg", "Refresh", lambda: self._on_global_refresh())
        self.header.add_action("action_collapse.svg", "Collapse All", lambda: self._on_global_collapse())
        self.main_layout.addWidget(self.header)

        # 2. Open Editors
        self.editors_header = SectionHeader("Open Editors", theme, self)
        self.main_layout.addWidget(self.editors_header)
        self.editors_list = QListWidget()
        self.editors_list.setMaximumHeight(200)
        style_list_widget(self.editors_list, theme)
        self.editors_list.itemClicked.connect(self._on_editor_item_clicked)
        self.main_layout.addWidget(self.editors_list)
        self.editors_header.toggled.connect(self.editors_list.setVisible)

        # 3. Dynamic Projects Container
        self.projects_container = QWidget()
        self.projects_layout = QVBoxLayout(self.projects_container)
        self.projects_layout.setContentsMargins(0, 0, 0, 0)
        self.projects_layout.setSpacing(0)
        self.main_layout.addWidget(self.projects_container, 1)
        self.projects_layout.addStretch(1) # Internal stretch to pack items at top

        # Context menu for empty space
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_empty_context_menu)

    def _show_empty_context_menu(self, position):
        from PyQt6.QtWidgets import QMenu, QApplication
        menu = QMenu(self)
        menu.setStyleSheet(f"QMenu {{ background-color: {self.theme['sidebar_bg']}; color: {self.theme['sidebar_fg']}; border: 1px solid {self.theme['border']}; }} QMenu::item:selected {{ background-color: {self.theme['bg_selection']}; }}")
        
        # Target the first project for context-sensitive global actions
        first_proj = self.projects[0] if self.projects else None
        root_path = first_proj._root_path if first_proj else ""

        # 1. New operations
        menu.addAction("New File", lambda: self._on_global_new_file())
        menu.addAction("New Folder", lambda: self._on_global_new_folder())
        menu.addSeparator()

        # 2. System/Terminal (Acting on first root)
        menu.addAction("Reveal in File Explorer", lambda: first_proj.cmd_reveal(root_path) if first_proj else None).setEnabled(bool(first_proj))
        menu.addAction("Open in Integrated Terminal", lambda: self.terminal_requested.emit(root_path) if root_path else None).setEnabled(bool(root_path))
        menu.addSeparator()

        # 3. Workspace
        menu.addAction("Add Folder to Workspace...", lambda: self.workspace_action_requested.emit("add_folder", ""))
        menu.addAction("Remove Folder from Workspace...").setEnabled(False) # Placeholder for picker
        if first_proj:
            menu.addAction("Open Folder Settings", lambda: first_proj.cmd_open_folder_settings(root_path))
        menu.addSeparator()

        # 4. Search & Copy
        menu.addAction("Find in Folder...", lambda: self.find_in_folder_requested.emit(root_path) if root_path else None).setEnabled(bool(root_path))
        menu.addAction("Copy Path", lambda: QApplication.clipboard().setText(root_path) if root_path else None).setEnabled(bool(root_path))
        menu.addSeparator()

        # 5. View properties
        menu.addAction("Refresh", lambda: self._on_global_refresh())
        menu.addAction("Collapse All", lambda: self._on_global_collapse())
        menu.addSeparator()
        
        # 6. Settings
        menu.addAction("Open Workspace Settings").setEnabled(False)
        
        menu.exec(QCursor.pos())

    def set_root_folder(self, path: str):
        # Clear existing projects (except stretch)
        for p in self.projects:
            self.projects_layout.removeWidget(p)
            p.deleteLater()
        self.projects.clear()
        self.add_root_folder(path)

    scm_count_changed = pyqtSignal(int)

    def add_root_folder(self, path: str):
        if not path or not os.path.exists(path): return
        # Avoid duplicates
        path = os.path.normpath(path)
        for p in self.projects:
            if p._root_path == path: return

        project = ProjectSection(path, self.theme, self)
        project.file_opened.connect(self.file_opened.emit)
        project.terminal_requested.connect(self.terminal_requested.emit)
        project.find_in_folder_requested.connect(self.find_in_folder_requested.emit)
        project.workspace_action_requested.connect(self.workspace_action_requested.emit)
        project.file_close_requested.connect(self.file_close_requested.emit)
        project.expansion_changed.connect(self._update_projects_stretch)
        project.scm_count_changed.connect(self._on_scm_count_changed)
        
        self.projects.append(project)
        # Insert before the stretch (which is the last item)
        self.projects_layout.insertWidget(self.projects_layout.count() - 1, project)
        self._update_projects_stretch()

    def _on_scm_count_changed(self):
        """Aggregate SCM counts from all projects and emit total."""
        total = 0
        for p in self.projects:
            # We need to access the last emitted count from each project
            # or ask them. Since we don't store it, let's store it on the project instance
            # actually better to just check their cached status
            if hasattr(p, 'scm_status'):
                total += len(p.scm_status)
        self.scm_count_changed.emit(total)

    def _update_projects_stretch(self):
        """Update stretch factors: expanded projects get stretch 1, collapsed get 0."""
        for i, p in enumerate(self.projects):
            # Header internal state
            is_expanded = p.header._expanded
            self.projects_layout.setStretch(i, 100 if is_expanded else 0)
        
        # Bottom spacer takes space ONLY if no projects are expanded
        any_expanded = any(p.header._expanded for p in self.projects)
        self.projects_layout.setStretch(self.projects_layout.count() - 1, 0 if any_expanded else 1)

    def remove_root_folder(self, path: str):
        path = os.path.normpath(path)
        for i, p in enumerate(self.projects):
            if p._root_path == path:
                self.projects_layout.removeWidget(p)
                p.deleteLater()
                self.projects.pop(i)
                break

    def _on_global_new_file(self):
        if self.projects: self.projects[0].cmd_new_file()
    def _on_global_new_folder(self):
        if self.projects: self.projects[0].cmd_new_folder()
    def _on_global_refresh(self):
        for p in self.projects: p.cmd_refresh()
        
    def refresh(self):
        """Unified refresh method used by MainWindow."""
        self._on_global_refresh()
    def _on_global_collapse(self):
        for p in self.projects: p.cmd_collapse_all()

    def _toggle_editors_visibility(self, visible):
        self.editors_list.setVisible(visible)
        if visible:
            self._update_editor_list_height()

    def _update_editor_list_height(self):
        # Adjust height based on item count
        count = self.editors_list.count()
        self.editors_list.setFixedHeight(min(200, count * 24 + 4) if count > 0 else 0)

    def sync_open_editors(self, items: list):
        """Update the 'Open Editors' list from the main window.
        items: list of dict {'name': str, 'path': str|None, 'index': int}
        """
        self.editors_list.clear()
        from PyQt6.QtWidgets import QListWidgetItem
        from PyQt6.QtCore import QFileInfo
        
        # print(f"DEBUG: sync_open_editors called with {len(items)} items")
        
        for data in items:
            if isinstance(data, dict):
                name = data.get('name', 'Untitled')
                path = data.get('path')
                index = data.get('index')
            elif isinstance(data, str):
                # Caller passed plain file paths
                name = os.path.basename(data) if data else 'Untitled'
                path = data
                index = None
            else:
                continue
            
            item = QListWidgetItem(name)
            # Store BOTH path and index if possible
            item.setData(Qt.ItemDataRole.UserRole, path)
            item.setData(Qt.ItemDataRole.UserRole + 1, index)
            
            # Choose Icon
            if path:
                info = QFileInfo(path)
                icon = self.icon_provider.icon(info)
            else:
                # Fallback for untitled or special widgets
                if "Untitled" in name:
                    # Look for file.txt icon
                    icon = self.icon_provider.icon(QFileInfo("file.txt"))
                else:
                    # Maybe it's Welcome or something else
                    icon = self.theme.get('icon_settings') # or some generic icon
                    
            if icon:
                item.setIcon(icon)
                
            self.editors_list.addItem(item)
            
        self._update_editor_list_height()

    def _on_editor_item_clicked(self, item):
        file_path = item.data(Qt.ItemDataRole.UserRole)
        index = item.data(Qt.ItemDataRole.UserRole + 1)
        
        # If we have a path and it exists, emit that
        if file_path and os.path.exists(file_path):
            self.file_opened.emit(file_path)
        else:
            # Fallback to switching by name (handled in MainWindow._open_file)
            self.file_opened.emit(item.text())

    def highlight_file(self, path):
        """Route highlight request to the correct project section."""
        if not path: return
        path = os.path.normpath(path)
        for p in self.projects:
            if path.startswith(p._root_path):
                # Ensure the section is expanded to show the file
                p.header.set_expanded(True)
                p.highlight_file(path)
                break


class SearchPanel(QWidget):
    """Search across files panel with real-time search and replace."""

    file_opened = pyqtSignal(str, int)  # path, line_number
    file_reloaded = pyqtSignal(str)  # path - signals that a file was modified and should reload

    def __init__(self, theme: dict, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.workspace_root = None
        self.search_results = []  # List of (file_path, line_num, line_text, match_start, match_end)
        self.current_match_index = -1
        
        # Debounce timer for search-as-you-type
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._perform_search)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.header = SidebarHeader("Search", theme, self)
        layout.addWidget(self.header)

        # Search input container
        search_container = QWidget()
        search_layout = QVBoxLayout(search_container)
        search_layout.setContentsMargins(12, 8, 12, 8)
        search_layout.setSpacing(6)

        # Search input with toggle buttons
        search_row = QHBoxLayout()
        search_row.setSpacing(4)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search")
        self.search_input.setFont(QFont("Segoe UI", 9))
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {theme['input_bg']};
                color: {theme['input_fg']};
                border: 1px solid {theme['input_border']};
                padding: 5px 8px;
                border-radius: 3px;
            }}
            QLineEdit:focus {{
                border-color: {theme['input_border_focus']};
            }}
        """)
        self.search_input.textChanged.connect(self._on_search_text_changed)
        search_row.addWidget(self.search_input)

        # Toggle buttons (Match Case, Regex, Whole Word)
        self.case_btn = self._create_toggle_button("Aa", "Match Case")
        self.regex_btn = self._create_toggle_button(".*", "Use Regular Expression")
        self.word_btn = self._create_toggle_button("Ab", "Match Whole Word")
        
        search_row.addWidget(self.case_btn)
        search_row.addWidget(self.regex_btn)
        search_row.addWidget(self.word_btn)
        
        search_layout.addLayout(search_row)

        # Replace input with action buttons
        replace_row = QHBoxLayout()
        replace_row.setSpacing(4)
        
        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText("Replace")
        self.replace_input.setFont(QFont("Segoe UI", 9))
        self.replace_input.setStyleSheet(self.search_input.styleSheet())
        replace_row.addWidget(self.replace_input)

        # Replace action buttons
        self.replace_btn = self._create_action_button("Replace", self._replace_current)
        self.replace_all_btn = self._create_action_button("Replace All", self._replace_all)
        
        replace_row.addWidget(self.replace_btn)
        replace_row.addWidget(self.replace_all_btn)
        
        search_layout.addLayout(replace_row)

        # Results info and navigation
        info_row = QHBoxLayout()
        info_row.setSpacing(6)
        
        self.results_label = QLabel("")
        self.results_label.setFont(QFont("Segoe UI", 8))
        self.results_label.setStyleSheet(f"color: {theme['text_secondary']};")
        info_row.addWidget(self.results_label)
        info_row.addStretch()
        
        self.prev_btn = self._create_nav_button("▲", "Previous Match", self._go_to_previous)
        self.next_btn = self._create_nav_button("▼", "Next Match", self._go_to_next)
        
        info_row.addWidget(self.prev_btn)
        info_row.addWidget(self.next_btn)
        
        search_layout.addLayout(info_row)
        
        layout.addWidget(search_container)

        # Results tree
        self.results_tree = QTreeWidget()
        self.results_tree.setHeaderHidden(True)
        self.results_tree.setIndentation(16)
        self.results_tree.setFont(QFont("Segoe UI", 9))
        self.results_tree.itemClicked.connect(self._on_result_clicked)
        self.results_tree.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {theme['sidebar_bg']};
                color: {theme['sidebar_fg']};
                border: none;
                outline: none;
            }}
            QTreeWidget::item {{
                padding: 2px;
            }}
            QTreeWidget::item:hover {{
                background-color: {theme['bg_hover']};
            }}
            QTreeWidget::item:selected {{
                background-color: {theme['bg_selection']};
            }}
        """)
        layout.addWidget(self.results_tree)

    def _create_toggle_button(self, text, tooltip):
        btn = QPushButton(text)
        btn.setToolTip(tooltip)
        btn.setCheckable(True)
        btn.setFixedSize(24, 24)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFont(QFont("Segoe UI", 8))
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {self.theme['input_bg']};
                border: 1px solid {self.theme['input_border']};
                border-radius: 3px;
                color: {self.theme['text_secondary']};
            }}
            QPushButton:hover {{
                background: {self.theme['bg_hover']};
            }}
            QPushButton:checked {{
                background: {self.theme['accent']};
                color: {self.theme['accent_fg']};
                border-color: {self.theme['accent']};
            }}
        """)
        btn.clicked.connect(self._on_search_text_changed)
        return btn

    def _create_action_button(self, text, callback):
        btn = QPushButton(text)
        btn.setFont(QFont("Segoe UI", 8))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(24)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {self.theme['input_bg']};
                border: 1px solid {self.theme['input_border']};
                border-radius: 3px;
                color: {self.theme['sidebar_fg']};
                padding: 0 8px;
            }}
            QPushButton:hover {{
                background: {self.theme['bg_hover']};
            }}
            QPushButton:pressed {{
                background: {self.theme['bg_selection']};
            }}
        """)
        btn.clicked.connect(callback)
        return btn

    def _create_nav_button(self, text, tooltip, callback):
        btn = QPushButton(text)
        btn.setToolTip(tooltip)
        btn.setFixedSize(20, 20)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFont(QFont("Segoe UI", 8))
        btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid {self.theme['input_border']};
                border-radius: 3px;
                color: {self.theme['sidebar_fg']};
            }}
            QPushButton:hover {{
                background: {self.theme['bg_hover']};
            }}
        """)
        btn.clicked.connect(callback)
        return btn

    def set_workspace_root(self, path):
        """Set the root directory for search operations."""
        self.workspace_root = path

    def _on_search_text_changed(self):
        """Debounce search trigger."""
        self.search_timer.stop()
        query = self.search_input.text().strip()
        if query:
            self.search_timer.start(300)  # 300ms debounce
        else:
            self.results_tree.clear()
            self.results_label.setText("")
            self.search_results = []

    def _perform_search(self):
        """Execute file search using grep/ripgrep or Python fallback."""
        query = self.search_input.text().strip()
        if not query or not self.workspace_root:
            return

        self.results_tree.clear()
        self.search_results = []
        
        # Try ripgrep first
        use_rg = False
        try:
            subprocess.run(["rg", "--version"], capture_output=True, check=True,
                          creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            use_rg = True
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass

        if use_rg:
            try:
                cmd = ["rg", "--line-number", "--column", "--no-heading", "--color=never"]
                if self.case_btn.isChecked():
                    cmd.append("--case-sensitive")
                else:
                    cmd.append("--ignore-case")
                if self.word_btn.isChecked():
                    cmd.append("--word-regexp")
                if not self.regex_btn.isChecked():
                    cmd.append("--fixed-strings")
                cmd.append(query)
                cmd.append(self.workspace_root)
                
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=10,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                
                self._parse_ripgrep_results(result.stdout, query)
                return
            except Exception as e:
                # Fall through to Python search
                pass
        
        # Python-based fallback search
        self._python_search(query)

    def _python_search(self, query):
        """Pure Python file search (fallback when grep/ripgrep unavailable)."""
        if not self.workspace_root:
            return
        
        import re
        
        # Compile search pattern
        if self.regex_btn.isChecked():
            try:
                flags = 0 if self.case_btn.isChecked() else re.IGNORECASE
                pattern = re.compile(query, flags)
            except re.error:
                self.results_label.setText("Invalid regex pattern")
                return
        else:
            # Fixed string search
            if self.case_btn.isChecked():
                if self.word_btn.isChecked():
                    pattern = re.compile(r'\b' + re.escape(query) + r'\b')
                else:
                    search_str = query
                    pattern = None
            else:
                if self.word_btn.isChecked():
                    pattern = re.compile(r'\b' + re.escape(query) + r'\b', re.IGNORECASE)
                else:
                    search_str = query.lower()
                    pattern = None
        
        file_results = {}
        binary_extensions = {'.exe', '.dll', '.so', '.dylib', '.bin', '.pyc', '.pyo', 
                            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico', 
                            '.mp3', '.mp4', '.avi', '.mov', '.pdf', '.zip', '.tar', '.gz'}
        
        try:
            for root, dirs, files in os.walk(self.workspace_root):
                # Skip common ignore directories
                dirs[:] = [d for d in dirs if d not in {'.git', '.svn', '__pycache__', 'node_modules', '.vscode', '.idea'}]
                
                for file in files:
                    file_path = os.path.join(root, file)
                    _, ext = os.path.splitext(file)
                    
                    # Skip binary files
                    if ext.lower() in binary_extensions:
                        continue
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            for line_num, line in enumerate(f, 1):
                                line_text = line.rstrip('\n\r')
                                
                                # Perform search
                                match = False
                                col = 0
                                
                                if pattern:
                                    m = pattern.search(line_text)
                                    if m:
                                        match = True
                                        col = m.start()
                                else:
                                    # Simple string search
                                    if self.case_btn.isChecked():
                                        idx = line_text.find(search_str)
                                    else:
                                        idx = line_text.lower().find(search_str)
                                    
                                    if idx >= 0:
                                        match = True
                                        col = idx
                                
                                if match:
                                    file_path_norm = os.path.normpath(file_path)
                                    if file_path_norm not in file_results:
                                        file_results[file_path_norm] = []
                                    file_results[file_path_norm].append((line_num, line_text, col))
                                    self.search_results.append((file_path_norm, line_num, line_text, col))
                    
                    except (PermissionError, UnicodeDecodeError, OSError):
                        continue
            
            # Populate tree
            total_matches = len(self.search_results)
            for file_path, matches in file_results.items():
                rel_path = os.path.relpath(file_path, self.workspace_root)
                
                file_item = QTreeWidgetItem([f"{rel_path} ({len(matches)})"])
                file_item.setData(0, Qt.ItemDataRole.UserRole, file_path)
                self.results_tree.addTopLevelItem(file_item)
                
                for line_num, text, col in matches:
                    match_item = QTreeWidgetItem([f"  {line_num}: {text}"])
                    match_item.setData(0, Qt.ItemDataRole.UserRole, (file_path, line_num))
                    file_item.addChild(match_item)
                
                file_item.setExpanded(True)

            self.results_label.setText(f"{total_matches} result{'s' if total_matches != 1 else ''} in {len(file_results)} file{'s' if len(file_results) != 1 else ''}")
            self.current_match_index = 0 if total_matches > 0 else -1

        except Exception as e:
            self.results_label.setText(f"Search error: {str(e)}")

    def _parse_ripgrep_results(self, stdout, query):
        """Parse ripgrep output and populate results."""
        file_results = {}
        for line in stdout.splitlines():
            # ripgrep format: file:line:column:text
            parts = line.split(':', 3)
            if len(parts) >= 4:
                file_path, line_num, col_num, text = parts
                line_num = int(line_num)
                col_num = int(col_num)
                
                file_path = os.path.normpath(file_path)
                if file_path not in file_results:
                    file_results[file_path] = []
                file_results[file_path].append((line_num, text.strip(), col_num))
                self.search_results.append((file_path, line_num, text.strip(), col_num))

        # Populate tree
        total_matches = len(self.search_results)
        for file_path, matches in file_results.items():
            rel_path = os.path.relpath(file_path, self.workspace_root)
            
            file_item = QTreeWidgetItem([f"{rel_path} ({len(matches)})"])
            file_item.setData(0, Qt.ItemDataRole.UserRole, file_path)
            self.results_tree.addTopLevelItem(file_item)
            
            for line_num, text, col in matches:
                match_item = QTreeWidgetItem([f"  {line_num}: {text}"])
                match_item.setData(0, Qt.ItemDataRole.UserRole, (file_path, line_num))
                file_item.addChild(match_item)
            
            file_item.setExpanded(True)

        self.results_label.setText(f"{total_matches} result{'s' if total_matches != 1 else ''} in {len(file_results)} file{'s' if len(file_results) != 1 else ''}")
        self.current_match_index = 0 if total_matches > 0 else -1

    def _on_result_clicked(self, item, column):
        """Open file at match location."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(data, tuple):
            file_path, line_num = data
            self.file_opened.emit(file_path, line_num)

    def _go_to_previous(self):
        """Navigate to previous match."""
        if not self.search_results:
            return
        self.current_match_index = (self.current_match_index - 1) % len(self.search_results)
        file_path, line_num, _, _ = self.search_results[self.current_match_index]
        self.file_opened.emit(file_path, line_num)

    def _go_to_next(self):
        """Navigate to next match."""
        if not self.search_results:
            return
        self.current_match_index = (self.current_match_index + 1) % len(self.search_results)
        file_path, line_num, _, _ = self.search_results[self.current_match_index]
        self.file_opened.emit(file_path, line_num)

    def _replace_current(self):
        """Replace the current match."""
        if self.current_match_index < 0 or not self.search_results:
            return
        
        file_path, line_num, line_text, col = self.search_results[self.current_match_index]
        replace_text = self.replace_input.text()
        search_text = self.search_input.text()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if 0 < line_num <= len(lines):
                line = lines[line_num - 1]
                # Perform replacement
                if self.regex_btn.isChecked():
                    import re
                    flags = 0 if self.case_btn.isChecked() else re.IGNORECASE
                    lines[line_num - 1] = re.sub(search_text, replace_text, line, count=1, flags=flags)
                else:
                    # Simple text replacement
                    if self.case_btn.isChecked():
                        lines[line_num - 1] = line.replace(search_text, replace_text, 1)
                    else:
                        # Case-insensitive replace
                        import re
                        lines[line_num - 1] = re.sub(re.escape(search_text), replace_text, line, count=1, flags=re.IGNORECASE)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                    f.flush()  # Force write to disk
                    os.fsync(f.fileno())  # Ensure it's physically written
                
                # Debug: Print what we're reloading
                print(f"[SearchPanel] Replaced in file: {file_path}")
                
                # Emit signal to reload the file in editor if open
                self.file_reloaded.emit(file_path)
                
                # Refresh search to update results (delay slightly to allow file save)
                QTimer.singleShot(100, self._perform_search)
                
        except Exception as e:
            QMessageBox.critical(self, "Replace Error", f"Could not replace: {e}")

    def _replace_all(self):
        """Replace all matches in all files."""
        if not self.search_results:
            return
        
        count = len(self.search_results)
        reply = QMessageBox.question(
            self, "Replace All",
            f"Replace {count} occurrence{'s' if count != 1 else ''} across {len(set(r[0] for r in self.search_results))} file{'s' if len(set(r[0] for r in self.search_results)) != 1 else ''}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.No:
            return
        
        replace_text = self.replace_input.text()
        search_text = self.search_input.text()
        
        # Group by file
        files_to_update = {}
        for file_path, line_num, line_text, col in self.search_results:
            if file_path not in files_to_update:
                files_to_update[file_path] = []
            files_to_update[file_path].append(line_num)
        
        try:
            for file_path, line_nums in files_to_update.items():
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Perform replacement
                if self.regex_btn.isChecked():
                    import re
                    flags = 0 if self.case_btn.isChecked() else re.IGNORECASE
                    content = re.sub(search_text, replace_text, content, flags=flags)
                else:
                    if self.case_btn.isChecked():
                        content = content.replace(search_text, replace_text)
                    else:
                        import re
                        content = re.sub(re.escape(search_text), replace_text, content, flags=re.IGNORECASE)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                # Emit signal to reload the file in editor if open
                self.file_reloaded.emit(file_path)
            
            QMessageBox.information(self, "Replace All", f"Replaced {count} occurrence{'s' if count != 1 else ''}")
            
            # Refresh search to update results (delay slightly)
            QTimer.singleShot(100, self._perform_search)
            
        except Exception as e:
            QMessageBox.critical(self, "Replace All Error", f"Could not replace: {e}")


class SCMFileItemWidget(QWidget):
    """Single changed-file row in the SCM panel — VS Code style."""

    stage_clicked = pyqtSignal(str)       # path
    unstage_clicked = pyqtSignal(str)     # path
    discard_clicked = pyqtSignal(str)     # path
    open_clicked = pyqtSignal(str)        # path

    # VS Code status colors
    STATUS_COLORS = {
        'M': '#e2c08d',   # Modified  – tan/yellow
        'A': '#73c991',   # Added     – green
        'D': '#c74e39',   # Deleted   – red
        'U': '#73c991',   # Untracked – green
        'R': '#4ec9b0',   # Renamed   – teal
        'C': '#4ec9b0',   # Copied    – teal
        '?': '#73c991',   # Unknown   – green
    }

    def __init__(self, file_status, theme: dict, is_staged: bool = False, parent=None):
        super().__init__(parent)
        self.file_status = file_status
        self.theme = theme
        self.is_staged = is_staged
        self.setFixedHeight(24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._hovered = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 4, 0)
        layout.setSpacing(4)

        # File name
        fname = os.path.basename(file_status.path)
        folder = os.path.dirname(file_status.path)
        self.name_label = QLabel(fname)
        self.name_label.setFont(QFont("Segoe UI", 9))
        self.name_label.setStyleSheet(f"color: {theme['sidebar_fg']};")
        layout.addWidget(self.name_label)

        # Folder path (dimmed)
        if folder:
            self.folder_label = QLabel(folder)
            self.folder_label.setFont(QFont("Segoe UI", 9))
            self.folder_label.setStyleSheet(f"color: {theme['text_disabled']};")
            layout.addWidget(self.folder_label)

        layout.addStretch()

        # Action buttons (visible on hover)
        self._action_btns = []
        if is_staged:
            self._add_action_btn("action_unstage.svg", "Unstage Changes",
                                 lambda: self.unstage_clicked.emit(file_status.path))
        else:
            if not file_status.is_untracked:
                self._add_action_btn("action_discard.svg", "Discard Changes",
                                     lambda: self.discard_clicked.emit(file_status.path))
            self._add_action_btn("action_stage.svg", "Stage Changes",
                                 lambda: self.stage_clicked.emit(file_status.path))

        # Status letter
        status = file_status.display_status if not is_staged else file_status.index_status
        if status == ' ':
            status = 'M'
        color = self.STATUS_COLORS.get(status, theme['text_secondary'])
        self.status_label = QLabel(status)
        self.status_label.setFont(QFont("Segoe UI Semibold", 9))
        self.status_label.setStyleSheet(f"color: {color}; min-width: 14px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        self.setStyleSheet("background: transparent;")
        self._update_btn_visibility()

    def _add_action_btn(self, icon_name, tooltip, callback):
        btn = QPushButton()
        btn.setToolTip(tooltip)
        btn.setFixedSize(20, 20)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        icon_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "assets", "icons", icon_name
        )
        if os.path.exists(icon_path):
            btn.setIcon(QIcon(icon_path))
            btn.setIconSize(QSize(12, 12))
        btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; border: none; border-radius: 3px; }}
            QPushButton:hover {{ background-color: {self.theme['bg_hover']}; }}
        """)
        btn.clicked.connect(callback)
        self.layout().addWidget(btn)
        self._action_btns.append(btn)

    def _update_btn_visibility(self):
        for btn in self._action_btns:
            btn.setVisible(self._hovered)

    def enterEvent(self, event):
        self._hovered = True
        self._update_btn_visibility()
        self.setStyleSheet(f"background: {self.theme['bg_hover']};")

    def leaveEvent(self, event):
        self._hovered = False
        self._update_btn_visibility()
        self.setStyleSheet("background: transparent;")

    def mouseDoubleClickEvent(self, event):
        self.open_clicked.emit(self.file_status.abs_path)


class SCMSectionHeader(QWidget):
    """Collapsible section header inside SCM panel (e.g. 'Staged Changes', 'Changes')."""

    action_clicked = pyqtSignal(str)  # action name

    def __init__(self, title: str, count: int, theme: dict,
                 actions: list = None, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.title = title
        self._expanded = True
        self.setFixedHeight(24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._hovered = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(4)

        # Chevron
        self.chevron = QLabel("▾")
        self.chevron.setFont(QFont("Segoe UI", 8))
        self.chevron.setStyleSheet(f"color: {theme['sidebar_fg']};")
        self.chevron.setFixedWidth(12)
        layout.addWidget(self.chevron)

        # Title
        self.title_label = QLabel(title.upper())
        font = QFont("Segoe UI Semibold", 9)
        self.title_label.setFont(font)
        self.title_label.setStyleSheet(f"color: {theme['sidebar_fg']};")
        layout.addWidget(self.title_label)

        # Count badge
        self.count_label = QLabel(str(count))
        self.count_label.setFont(QFont("Segoe UI", 8))
        self.count_label.setStyleSheet(
            f"color: {theme['text_secondary']}; padding: 0 4px;")
        layout.addWidget(self.count_label)

        layout.addStretch()

        # Action buttons
        self._action_btns = []
        if actions:
            for icon_name, tooltip, action_name in actions:
                btn = QPushButton()
                btn.setToolTip(tooltip)
                btn.setFixedSize(20, 20)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                icon_path = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                    "assets", "icons", icon_name
                )
                if os.path.exists(icon_path):
                    btn.setIcon(QIcon(icon_path))
                    btn.setIconSize(QSize(12, 12))
                btn.setStyleSheet(f"""
                    QPushButton {{ background: transparent; border: none; border-radius: 3px; }}
                    QPushButton:hover {{ background-color: {theme['bg_hover']}; }}
                """)
                btn.clicked.connect(lambda checked, n=action_name: self.action_clicked.emit(n))
                layout.addWidget(btn)
                self._action_btns.append(btn)

        self._update_btn_visibility()

    def update_count(self, count: int):
        self.count_label.setText(str(count))

    def _update_btn_visibility(self):
        for btn in self._action_btns:
            btn.setVisible(self._hovered)

    def enterEvent(self, event):
        self._hovered = True
        self._update_btn_visibility()

    def leaveEvent(self, event):
        self._hovered = False
        self._update_btn_visibility()

    @property
    def expanded(self):
        return self._expanded

    def mousePressEvent(self, event):
        self._expanded = not self._expanded
        self.chevron.setText("▾" if self._expanded else "▸")
        # parent will handle toggling content visibility
        p = self.parent()
        if p and hasattr(p, '_toggle_section'):
            p._toggle_section(self.title)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(self.theme['sidebar_bg']))
        painter.end()


class SourceControlPanel(QWidget):
    """Full Git source control panel — VS Code style."""

    file_opened = pyqtSignal(str)

    def __init__(self, theme: dict, parent=None):
        super().__init__(parent)
        self.theme = theme
        self._repo_root = None
        self._folder = None

        from app.core.git_manager import GitManager
        self.git = GitManager()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header with actions
        self.header = SidebarHeader("Source Control", theme, self)
        self.header.add_action("action_refresh.svg", "Refresh", self._refresh)
        layout.addWidget(self.header)

        # ── Stacked: No-repo view vs Repo view ──
        self.stack = QStackedWidget()

        # Page 0: No repo detected
        self.no_repo_page = QWidget()
        no_repo_layout = QVBoxLayout(self.no_repo_page)
        no_repo_layout.setContentsMargins(12, 20, 12, 12)
        no_repo_layout.setSpacing(12)

        self._no_git_label = QLabel()
        self._no_git_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._no_git_label.setWordWrap(True)
        self._no_git_label.setStyleSheet(f"color: {theme['text_secondary']};")
        no_repo_layout.addWidget(self._no_git_label)

        init_btn = QPushButton("Initialize Repository")
        init_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        init_btn.setFont(QFont("Segoe UI", 10))
        init_btn.setFixedHeight(30)
        init_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme['accent']};
                color: {theme['accent_fg']};
                border: none;
                border-radius: 4px;
                padding: 4px 16px;
            }}
            QPushButton:hover {{
                background-color: {theme['accent_hover']};
            }}
        """)
        init_btn.clicked.connect(self._init_repo)
        no_repo_layout.addWidget(init_btn)
        no_repo_layout.addStretch()

        # Page 1: Repo active
        self.repo_page = QWidget()
        repo_layout = QVBoxLayout(self.repo_page)
        repo_layout.setContentsMargins(0, 0, 0, 0)
        repo_layout.setSpacing(0)

        # ── Branch display ──
        branch_bar = QWidget()
        branch_layout = QHBoxLayout(branch_bar)
        branch_layout.setContentsMargins(12, 6, 12, 6)
        branch_layout.setSpacing(6)
        branch_icon_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "assets", "icons", "scm.svg"
        )
        branch_icon_label = QLabel()
        if os.path.exists(branch_icon_path):
            branch_icon_label.setPixmap(QIcon(branch_icon_path).pixmap(14, 14))
        branch_layout.addWidget(branch_icon_label)
        self.branch_label = QLabel("main")
        self.branch_label.setFont(QFont("Segoe UI", 9))
        self.branch_label.setStyleSheet(f"color: {theme['sidebar_fg']};")
        self.branch_label.setCursor(Qt.CursorShape.PointingHandCursor)
        branch_layout.addWidget(self.branch_label)
        self.sync_label = QLabel("")
        self.sync_label.setFont(QFont("Segoe UI", 8))
        self.sync_label.setStyleSheet(f"color: {theme['text_disabled']};")
        branch_layout.addWidget(self.sync_label)
        branch_layout.addStretch()

        # Sync / Push / Pull buttons in branch bar
        for icon_name, tooltip, callback in [
            ("action_sync.svg", "Sync Changes", self._sync),
        ]:
            btn = QPushButton()
            btn.setToolTip(tooltip)
            btn.setFixedSize(22, 22)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            ip = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "assets", "icons", icon_name
            )
            if os.path.exists(ip):
                btn.setIcon(QIcon(ip))
                btn.setIconSize(QSize(14, 14))
            btn.setStyleSheet(f"""
                QPushButton {{ background: transparent; border: none; border-radius: 3px; }}
                QPushButton:hover {{ background-color: {theme['bg_hover']}; }}
            """)
            btn.clicked.connect(callback)
            branch_layout.addWidget(btn)

        repo_layout.addWidget(branch_bar)

        # ── Commit message input ──
        commit_container = QWidget()
        cc_layout = QVBoxLayout(commit_container)
        cc_layout.setContentsMargins(8, 4, 8, 4)
        cc_layout.setSpacing(4)

        self.commit_input = QLineEdit()
        self.commit_input.setPlaceholderText("Message (press Enter to commit)")
        self.commit_input.setFont(QFont("Segoe UI", 9))
        self.commit_input.setFixedHeight(28)
        self.commit_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {theme['input_bg']};
                color: {theme['input_fg']};
                border: 1px solid {theme['input_border']};
                border-radius: 3px;
                padding: 2px 8px;
            }}
            QLineEdit:focus {{
                border-color: {theme['input_border_focus']};
            }}
        """)
        self.commit_input.returnPressed.connect(self._commit)
        cc_layout.addWidget(self.commit_input)

        # Commit button
        self.commit_btn = QPushButton("✓ Commit")
        self.commit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.commit_btn.setFont(QFont("Segoe UI", 9))
        self.commit_btn.setFixedHeight(26)
        self.commit_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme['accent']};
                color: {theme['accent_fg']};
                border: none;
                border-radius: 3px;
                padding: 2px 12px;
            }}
            QPushButton:hover {{
                background-color: {theme['accent_hover']};
            }}
        """)
        self.commit_btn.clicked.connect(self._commit)
        cc_layout.addWidget(self.commit_btn)

        repo_layout.addWidget(commit_container)

        # ── Separator ──
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {theme['border']};")
        repo_layout.addWidget(sep)

        # ── Scrollable file changes area ──
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: {theme['sidebar_bg']};
                border: none;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 10px;
            }}
            QScrollBar::handle:vertical {{
                background: {theme['scrollbar_thumb']};
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {theme['scrollbar_thumb_hover']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

        self.changes_container = QWidget()
        self.changes_layout = QVBoxLayout(self.changes_container)
        self.changes_layout.setContentsMargins(0, 0, 0, 0)
        self.changes_layout.setSpacing(0)
        self.changes_layout.addStretch()
        self.scroll_area.setWidget(self.changes_container)
        repo_layout.addWidget(self.scroll_area)

        # ── Status message at bottom ──
        self.status_msg = QLabel("")
        self.status_msg.setFont(QFont("Segoe UI", 8))
        self.status_msg.setStyleSheet(f"color: {theme['text_disabled']}; padding: 4px 8px;")
        self.status_msg.hide()
        repo_layout.addWidget(self.status_msg)

        self.stack.addWidget(self.no_repo_page)  # 0
        self.stack.addWidget(self.repo_page)      # 1
        layout.addWidget(self.stack)

        # Section tracking
        self._sections = {}  # title -> (header_widget, content_widget)

        # Auto-refresh timer
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh)
        self._refresh_timer.setInterval(3000)  # refresh every 3 seconds

        # Show no-repo initially
        self._show_no_repo("Open a folder to use source control features.")

    # ── Public API ─────────────────────────────────────────────

    def set_folder(self, folder: str):
        """Called when a folder is opened in the IDE."""
        self._folder = folder
        root = self.git.detect_repo(folder)
        if root:
            self._repo_root = root
            self.stack.setCurrentIndex(1)
            self._refresh_timer.start()
            self._refresh()
        else:
            self._show_no_repo(
                "The folder does not contain a Git repository.\n"
                "You can initialize one to get started."
            )
            self._refresh_timer.stop()

    # ── Internals ──────────────────────────────────────────────

    def _show_no_repo(self, message: str):
        self._no_git_label.setText(message)
        self.stack.setCurrentIndex(0)

    def _init_repo(self):
        """Initialize a new git repository."""
        if not self._folder:
            return
        try:
            self.git.init_repo(self._folder)
            self._repo_root = self._folder
            self.stack.setCurrentIndex(1)
            self._refresh_timer.start()
            self._refresh()
            self._show_status("Initialized empty Git repository")
        except Exception as e:
            self._show_status(f"Error: {e}")

    def _refresh(self):
        """Refresh the full source control view."""
        if not self._repo_root:
            return

        # Update branch
        branch = self.git.current_branch()
        self.branch_label.setText(f"  {branch}")

        # Ahead/behind
        ahead, behind = self.git.ahead_behind()
        parts = []
        if ahead:
            parts.append(f"↑{ahead}")
        if behind:
            parts.append(f"↓{behind}")
        self.sync_label.setText(" ".join(parts))

        # Get file statuses
        all_files = self.git.status()
        staged = [f for f in all_files if f.is_staged]
        unstaged = [f for f in all_files if f.is_unstaged and not f.is_untracked]
        untracked = [f for f in all_files if f.is_untracked]

        # Merge conflicts
        conflicts = [f for f in all_files if f.is_conflict]

        # Clear existing sections
        self._clear_changes()

        # Build sections
        if conflicts:
            self._add_section("Merge Changes", conflicts, is_staged=False,
                              actions=[])

        if staged:
            self._add_section("Staged Changes", staged, is_staged=True,
                              actions=[
                                  ("action_unstage.svg", "Unstage All", "unstage_all"),
                              ])

        changes_combined = unstaged + untracked
        if changes_combined:
            self._add_section("Changes", changes_combined, is_staged=False,
                              actions=[
                                  ("action_discard.svg", "Discard All Changes", "discard_all"),
                                  ("action_stage.svg", "Stage All Changes", "stage_all"),
                              ])

        if not all_files:
            no_changes = QLabel("No changes detected.")
            no_changes.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_changes.setFont(QFont("Segoe UI", 9))
            no_changes.setStyleSheet(f"color: {self.theme['text_disabled']}; padding: 20px;")
            self.changes_layout.insertWidget(
                self.changes_layout.count() - 1, no_changes)

    def _clear_changes(self):
        """Remove all section widgets from the changes layout."""
        while self.changes_layout.count() > 1:  # keep the stretch
            item = self.changes_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self._sections.clear()

    def _add_section(self, title: str, files, is_staged: bool, actions: list):
        """Add a collapsible section with file items."""
        section_actions = [(a[0], a[1], a[2]) for a in actions]

        header = SCMSectionHeader(title, len(files), self.theme,
                                  actions=section_actions, parent=self)
        header.action_clicked.connect(
            lambda action: self._on_section_action(action, title))

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        for f in files:
            item = SCMFileItemWidget(f, self.theme, is_staged=is_staged, parent=content)
            item.stage_clicked.connect(self._stage_file)
            item.unstage_clicked.connect(self._unstage_file)
            item.discard_clicked.connect(self._discard_file)
            item.open_clicked.connect(self.file_opened.emit)
            content_layout.addWidget(item)

        idx = self.changes_layout.count() - 1  # before stretch
        self.changes_layout.insertWidget(idx, header)
        self.changes_layout.insertWidget(idx + 1, content)

        self._sections[title] = (header, content)

    def _toggle_section(self, title: str):
        """Toggle visibility of a section's content."""
        if title in self._sections:
            header, content = self._sections[title]
            content.setVisible(header.expanded)

    # ── Section actions ────────────────────────────────────────

    def _on_section_action(self, action: str, section_title: str):
        if action == "stage_all":
            self._stage_all()
        elif action == "unstage_all":
            self._unstage_all()
        elif action == "discard_all":
            self._discard_all()

    def _stage_file(self, path: str):
        try:
            self.git.stage_file(path)
            self._refresh()
        except Exception as e:
            self._show_status(f"Error staging: {e}")

    def _unstage_file(self, path: str):
        try:
            self.git.unstage_file(path)
            self._refresh()
        except Exception as e:
            self._show_status(f"Error unstaging: {e}")

    def _discard_file(self, path: str):
        """Discard changes with confirmation."""
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "Discard Changes",
            f"Are you sure you want to discard changes to\n{path}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Check if untracked
                files = self.git.status()
                file_obj = next((f for f in files if f.path == path), None)
                if file_obj and file_obj.is_untracked:
                    self.git.discard_untracked(path)
                else:
                    self.git.discard_file(path)
                self._refresh()
            except Exception as e:
                self._show_status(f"Error discarding: {e}")

    def _stage_all(self):
        try:
            self.git.stage_all()
            self._refresh()
        except Exception as e:
            self._show_status(f"Error: {e}")

    def _unstage_all(self):
        try:
            self.git.unstage_all()
            self._refresh()
        except Exception as e:
            self._show_status(f"Error: {e}")

    def _discard_all(self):
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "Discard All Changes",
            "Are you sure you want to discard ALL changes?\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                files = self.git.status()
                for f in files:
                    if f.is_untracked:
                        self.git.discard_untracked(f.path)
                    elif f.is_unstaged:
                        self.git.discard_file(f.path)
                self._refresh()
            except Exception as e:
                self._show_status(f"Error: {e}")

    # ── Commit ─────────────────────────────────────────────────

    def _commit(self):
        message = self.commit_input.text().strip()
        if not message:
            self._show_status("Please enter a commit message.")
            return

        # Check if anything is staged
        staged = self.git.get_staged_files()
        if not staged:
            # Auto-stage all if nothing staged (like VS Code behavior)
            from PyQt6.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                self, "No Staged Changes",
                "There are no staged changes.\nWould you like to stage all changes and commit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.git.stage_all()
            else:
                return

        try:
            result = self.git.commit(message)
            self.commit_input.clear()
            self._show_status(f"✓ {result.splitlines()[0] if result else 'Committed'}")
            self._refresh()
        except Exception as e:
            self._show_status(f"Commit failed: {e}")

    # ── Push / Pull / Sync ─────────────────────────────────────

    def _sync(self):
        """Sync = pull then push."""
        try:
            remotes = self.git.get_remotes()
            if not remotes:
                self._show_status("No remote configured. Use git remote add.")
                return
            self._show_status("Syncing...")
            try:
                self.git.pull()
            except Exception:
                pass  # may fail if no upstream
            try:
                branch = self.git.current_branch()
                self.git.push(set_upstream=True, branch=branch)
            except Exception as e:
                self._show_status(f"Push failed: {e}")
                return
            self._refresh()
            self._show_status("✓ Synced")
        except Exception as e:
            self._show_status(f"Sync error: {e}")

    # ── UI helpers ─────────────────────────────────────────────

    def _show_status(self, text: str):
        self.status_msg.setText(text)
        self.status_msg.show()
        QTimer.singleShot(5000, lambda: self.status_msg.hide())

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(self.theme['sidebar_bg']))
        p.end()


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


class ExtensionItemWidget(QWidget):
    """Single extension row in the search/installed list — VS Code style."""

    install_clicked = pyqtSignal(object)
    uninstall_clicked = pyqtSignal(str)
    theme_apply_clicked = pyqtSignal(object)  # emits ext_info dict

    def __init__(self, ext_info: dict, theme: dict, installed: bool = False, parent=None):
        super().__init__(parent)
        self.ext_info = ext_info
        self.theme = theme
        self.installed = installed
        self.setFixedHeight(72)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        root = QHBoxLayout(self)
        root.setContentsMargins(12, 8, 12, 8)
        root.setSpacing(10)

        # Icon placeholder (colored square with first letter)
        icon_label = QLabel()
        icon_label.setFixedSize(36, 36)
        display_name = ext_info.get("displayName", ext_info.get("name", "?"))
        letter = display_name[0].upper() if display_name else "?"
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet(f"""
            background: #2d2d30;
            border-radius: 4px;
            color: {theme.get('accent', '#ffffff')};
            font-size: 16px;
            font-weight: bold;
        """)
        icon_label.setText(letter)
        root.addWidget(icon_label)

        # Text column
        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(2)

        name_row = QHBoxLayout()
        name_row.setSpacing(6)
        name_lbl = QLabel(display_name)
        name_lbl.setStyleSheet(f"color: {theme['text_primary']}; font-size: 13px; font-weight: 600;")
        name_row.addWidget(name_lbl)

        version = ext_info.get("version", "")
        if version:
            ver_lbl = QLabel(f"v{version}")
            ver_lbl.setStyleSheet(f"color: {theme['text_disabled']}; font-size: 11px;")
            name_row.addWidget(ver_lbl)
        name_row.addStretch()
        text_col.addLayout(name_row)

        desc = ext_info.get("description", "")
        if len(desc) > 80:
            desc = desc[:77] + "..."
        desc_lbl = QLabel(desc)
        desc_lbl.setStyleSheet(f"color: {theme['text_secondary']}; font-size: 11px;")
        desc_lbl.setWordWrap(True)
        text_col.addWidget(desc_lbl)

        publisher = ext_info.get("namespace", ext_info.get("publisher", ""))
        dl_count = ext_info.get("downloadCount", 0)
        pub_text = publisher
        if dl_count > 0:
            if dl_count >= 1_000_000:
                pub_text += f"  ·  {dl_count / 1_000_000:.1f}M installs"
            elif dl_count >= 1_000:
                pub_text += f"  ·  {dl_count / 1_000:.0f}K installs"
            else:
                pub_text += f"  ·  {dl_count} installs"
        if pub_text:
            pub_lbl = QLabel(pub_text)
            pub_lbl.setStyleSheet(f"color: {theme['text_disabled']}; font-size: 10px;")
            text_col.addWidget(pub_lbl)

        root.addLayout(text_col, 1)

        # Action button
        if installed:
            # Show buttons based on what the extension contributes
            btn_col = QVBoxLayout()
            btn_col.setSpacing(4)

            # Check if this extension contributes themes
            contributes = ext_info.get("contributes", {})
            themes_list = contributes.get("themes", [])
            has_languages = bool(contributes.get("languages", []))
            has_snippets = bool(contributes.get("snippets", []))
            has_grammars = bool(contributes.get("grammars", []))

            if themes_list:
                apply_btn = QPushButton("Apply")
                apply_btn.setFixedSize(60, 22)
                apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                apply_btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {theme.get('accent', '#ffffff')};
                        color: {theme.get('accent_fg', '#000000')};
                        border: none;
                        border-radius: 3px;
                        font-size: 11px;
                        font-weight: 600;
                        padding: 2px 8px;
                    }}
                    QPushButton:hover {{
                        background: {theme.get('accent_hover', '#e0e0e0')};
                    }}
                """)
                apply_btn.clicked.connect(lambda: self.theme_apply_clicked.emit(ext_info))
                btn_col.addWidget(apply_btn)
            elif has_languages or has_snippets or has_grammars:
                # Show "Enabled" label for language/snippet extensions
                enabled_lbl = QLabel("✓ Enabled")
                enabled_lbl.setFixedSize(60, 22)
                enabled_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                enabled_lbl.setStyleSheet(f"""
                    color: #89d185;
                    font-size: 10px;
                    font-weight: 600;
                """)
                btn_col.addWidget(enabled_lbl)

            uninstall_btn = QPushButton("Uninstall")
            uninstall_btn.setFixedSize(60, 22)
            uninstall_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            uninstall_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {theme['text_secondary']};
                    border: 1px solid {theme['border']};
                    border-radius: 3px;
                    font-size: 11px;
                    padding: 2px 8px;
                }}
                QPushButton:hover {{
                    background: #3c3c3c;
                }}
            """)
            uninstall_btn.clicked.connect(
                lambda: self.uninstall_clicked.emit(ext_info.get("id", "")))
            btn_col.addWidget(uninstall_btn)
            root.addLayout(btn_col)
        else:
            install_btn = QPushButton("Install")
            install_btn.setFixedSize(60, 24)
            install_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            install_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {theme.get('accent', '#ffffff')};
                    color: {theme.get('accent_fg', '#000000')};
                    border: none;
                    border-radius: 3px;
                    font-size: 11px;
                    font-weight: 600;
                    padding: 3px 10px;
                }}
                QPushButton:hover {{
                    background: {theme.get('accent_hover', '#e0e0e0')};
                }}
            """)
            install_btn.clicked.connect(lambda: self.install_clicked.emit(ext_info))
            root.addWidget(install_btn)

    def paintEvent(self, event):
        p = QPainter(self)
        # Bottom border line
        p.setPen(QPen(QColor(self.theme.get('border', '#3a3a3c')), 1))
        p.drawLine(12, self.height() - 1, self.width() - 12, self.height() - 1)
        p.end()


class ExtensionsPanel(QWidget):
    """VS Code-style Extensions panel — search marketplace, install, manage."""

    def __init__(self, theme: dict, parent=None):
        super().__init__(parent)
        self.theme = theme
        self._installed_ids = set()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = SidebarHeader("Extensions", theme, self)
        header.add_action("action_refresh.svg", "Refresh", self._refresh_installed)
        layout.addWidget(header)

        # Search bar
        search_container = QWidget()
        search_container.setFixedHeight(40)
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(10, 6, 10, 6)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search Extensions in Marketplace...")
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {theme['input_bg']};
                color: {theme['input_fg']};
                border: 1px solid {theme['input_border']};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border-color: {theme['input_border_focus']};
            }}
        """)
        self.search_input.returnPressed.connect(self._on_search)
        search_layout.addWidget(self.search_input)
        layout.addWidget(search_container)

        # Status label (shows "Searching...", "No results", etc.)
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet(
            f"color: {theme['text_secondary']}; font-size: 11px; padding: 4px;")
        self.status_label.hide()
        layout.addWidget(self.status_label)

        # ── Installed section ──
        installed_header = QLabel("  INSTALLED")
        installed_header.setFixedHeight(26)
        installed_header.setStyleSheet(f"""
            color: {theme['sidebar_header_fg']};
            font-size: 11px;
            font-weight: 600;
            padding-left: 10px;
            padding-top: 6px;
        """)
        layout.addWidget(installed_header)

        self.installed_scroll = QScrollArea()
        self.installed_scroll.setWidgetResizable(True)
        self.installed_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.installed_scroll.setStyleSheet("background: transparent;")

        self.installed_container = QWidget()
        self.installed_layout = QVBoxLayout(self.installed_container)
        self.installed_layout.setContentsMargins(0, 0, 0, 0)
        self.installed_layout.setSpacing(0)
        self.installed_layout.addStretch()
        self.installed_scroll.setWidget(self.installed_container)
        layout.addWidget(self.installed_scroll)

        # ── Marketplace results section ──
        self.marketplace_header = QLabel("  MARKETPLACE")
        self.marketplace_header.setFixedHeight(26)
        self.marketplace_header.setStyleSheet(f"""
            color: {theme['sidebar_header_fg']};
            font-size: 11px;
            font-weight: 600;
            padding-left: 10px;
            padding-top: 6px;
        """)
        self.marketplace_header.hide()
        layout.addWidget(self.marketplace_header)

        self.results_scroll = QScrollArea()
        self.results_scroll.setWidgetResizable(True)
        self.results_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.results_scroll.setStyleSheet("background: transparent;")

        self.results_container = QWidget()
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setContentsMargins(0, 0, 0, 0)
        self.results_layout.setSpacing(0)
        self.results_layout.addStretch()
        self.results_scroll.setWidget(self.results_container)
        self.results_scroll.hide()
        layout.addWidget(self.results_scroll)

        layout.addStretch()

        # Load installed on init
        QTimer.singleShot(500, self._refresh_installed)

    # ── Search ──
    def _on_search(self):
        query = self.search_input.text().strip()
        if not query:
            return

        self.status_label.setText("Searching marketplace...")
        self.status_label.show()
        self.marketplace_header.hide()
        self.results_scroll.hide()

        # Run search in background thread
        import threading

        def _do_search():
            from app.core.extension_manager import search_extensions
            results = search_extensions(query)
            # Schedule UI update on main thread
            QTimer.singleShot(0, lambda: self._show_search_results(results))

        t = threading.Thread(target=_do_search, daemon=True)
        t.start()

    def _show_search_results(self, results: list):
        self.status_label.hide()

        # Clear old results
        while self.results_layout.count() > 1:
            item = self.results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not results:
            self.status_label.setText("No extensions found.")
            self.status_label.show()
            return

        self.marketplace_header.show()
        self.results_scroll.show()

        for ext_info in results:
            ext_id = f"{ext_info.get('namespace', '')}.{ext_info.get('name', '')}"
            is_installed = ext_id in self._installed_ids

            if is_installed:
                continue  # Don't show already-installed in marketplace results

            item = ExtensionItemWidget(ext_info, self.theme, installed=False)
            item.install_clicked.connect(self._install_extension)
            # Insert before the stretch
            self.results_layout.insertWidget(self.results_layout.count() - 1, item)

    # ── Install ──
    def _install_extension(self, ext_info: dict):
        ext_id = f"{ext_info.get('namespace', '')}.{ext_info.get('name', '')}"
        download_url = ext_info.get("downloadUrl", "")

        if not download_url:
            self.status_label.setText("No download URL available.")
            self.status_label.show()
            return

        self.status_label.setText(f"Installing {ext_info.get('displayName', ext_id)}...")
        self.status_label.show()

        import threading

        def _do_install():
            from app.core.extension_manager import download_vsix, install_extension
            vsix = download_vsix(download_url, ext_id)
            result = None
            if vsix:
                result = install_extension(vsix, ext_id)
                try:
                    vsix.unlink()
                except Exception:
                    pass

            QTimer.singleShot(0, lambda: self._on_install_complete(ext_id, result))

        t = threading.Thread(target=_do_install, daemon=True)
        t.start()

    def _on_install_complete(self, ext_id: str, result):
        if result:
            self.status_label.setText(f"Installed {ext_id} ✓")
            self.status_label.show()
            self._refresh_installed()
            # Re-run current search to update buttons
            if self.search_input.text().strip():
                self._on_search()
        else:
            self.status_label.setText(f"Failed to install {ext_id}")
            self.status_label.show()

        QTimer.singleShot(3000, lambda: self.status_label.hide())

    # ── Uninstall ──
    def _uninstall_extension(self, ext_id: str):
        from app.core.extension_manager import uninstall_extension
        ok = uninstall_extension(ext_id)
        if ok:
            self.status_label.setText(f"Uninstalled {ext_id} ✓")
            self.status_label.show()
            QTimer.singleShot(3000, lambda: self.status_label.hide())
        self._refresh_installed()

    # ── Refresh installed list ──
    def _refresh_installed(self):
        from app.core.extension_manager import list_installed

        # Clear old items
        while self.installed_layout.count() > 1:
            item = self.installed_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        installed = list_installed()
        self._installed_ids = set()

        for ext in installed:
            ext_id = ext.get("id", "")
            self._installed_ids.add(ext_id)

            item = ExtensionItemWidget(ext, self.theme, installed=True)
            item.uninstall_clicked.connect(self._uninstall_extension)
            item.theme_apply_clicked.connect(self._apply_theme)
            self.installed_layout.insertWidget(self.installed_layout.count() - 1, item)

    # ── Apply theme from extension ──
    def _apply_theme(self, ext_info: dict):
        """Apply a VS Code theme from an installed extension to ALL open editors."""
        from app.core.extension_manager import get_themes_from_extension

        ext_path = ext_info.get("path", "")
        if not ext_path:
            self.status_label.setText("Error: extension path not found.")
            self.status_label.show()
            QTimer.singleShot(3000, lambda: self.status_label.hide())
            return

        themes = get_themes_from_extension(ext_path)
        if not themes:
            self.status_label.setText("No themes found in this extension.")
            self.status_label.show()
            QTimer.singleShot(3000, lambda: self.status_label.hide())
            return

        # Pick best theme — prefer first dark theme
        if len(themes) == 1:
            chosen = themes[0]
        else:
            dark_themes = [t for t in themes if "dark" in t.get("uiTheme", "").lower()]
            chosen = dark_themes[0] if dark_themes else themes[0]

        colors = chosen["colors"]

        # Find the MainWindow's editor_tabs and apply globally
        count = 0
        app = QApplication.instance()
        if app:
            for w in app.topLevelWidgets():
                if hasattr(w, 'editor_tabs'):
                    count = w.editor_tabs.apply_extension_theme_to_all(colors)
                    break

        if count > 0:
            self.status_label.setText(f"✓ Applied: {chosen['label']}")
        else:
            self.status_label.setText(f"✓ Theme saved: {chosen['label']}  — open a Python file to see it")

        self.status_label.show()
        QTimer.singleShot(5000, lambda: self.status_label.hide())


class Sidebar(QWidget):
    """Main sidebar that switches between panels."""

    file_opened = pyqtSignal(str)
    terminal_requested = pyqtSignal(str)
    find_in_folder_requested = pyqtSignal(str)
    workspace_action_requested = pyqtSignal(str, str)
    file_close_requested = pyqtSignal(str)
    scm_count_changed = pyqtSignal(int)

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
        self.explorer_panel.find_in_folder_requested.connect(self.find_in_folder_requested.emit)
        self.explorer_panel.workspace_action_requested.connect(self.workspace_action_requested.emit)
        self.explorer_panel.file_close_requested.connect(self.file_close_requested.emit)
        self.explorer_panel.scm_count_changed.connect(self.scm_count_changed.emit)
        
        self.search_panel = SearchPanel(theme, self)
        self.scm_panel = SourceControlPanel(theme, self)
        self.scm_panel.file_opened.connect(self.file_opened.emit)
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
        self.scm_panel.set_folder(path)

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(self.theme['sidebar_bg']))
        p.end()
