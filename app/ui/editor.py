"""
Code Editor - Tabbed editor area with QScintilla-based code editing.
Features: Python syntax highlighting, line numbers, code folding,
auto-indent, bracket matching, current line highlight.
"""

import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
                              QLabel, QSizePolicy, QTabBar, QPushButton)
from PyQt6.QtCore import pyqtSignal, Qt, QFileInfo
from PyQt6.QtGui import QFont, QColor, QPainter
from PyQt6.Qsci import (QsciScintilla, QsciLexerPython, QsciLexerJSON,
                          QsciLexerHTML, QsciLexerCSS, QsciLexerJavaScript,
                          QsciLexerMarkdown, QsciLexerBash, QsciLexerBatch,
                          QsciLexerYAML, QsciLexerSQL, QsciLexerXML)


# Map file extensions to lexer classes
LEXER_MAP = {
    ".py": QsciLexerPython,
    ".pyw": QsciLexerPython,
    ".pyi": QsciLexerPython,
    ".json": QsciLexerJSON,
    ".html": QsciLexerHTML,
    ".htm": QsciLexerHTML,
    ".css": QsciLexerCSS,
    ".js": QsciLexerJavaScript,
    ".ts": QsciLexerJavaScript,
    ".md": QsciLexerMarkdown,
    ".markdown": QsciLexerMarkdown,
    ".sh": QsciLexerBash,
    ".bash": QsciLexerBash,
    ".bat": QsciLexerBatch,
    ".cmd": QsciLexerBatch,
    ".ps1": QsciLexerBatch,
    ".yaml": QsciLexerYAML,
    ".yml": QsciLexerYAML,
    ".sql": QsciLexerSQL,
    ".xml": QsciLexerXML,
    ".toml": None,
    ".ini": None,
    ".cfg": None,
    ".txt": None,
    ".csv": None,
}


class CodeEditorWidget(QsciScintilla):
    """A single code editor pane powered by QScintilla."""

    def __init__(self, file_path: str, theme: dict, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.theme = theme
        self._is_modified = False

        self._setup_editor()
        self._setup_theme(theme)
        self._setup_lexer(file_path)

        # Load file content
        if file_path and os.path.exists(file_path):
            try:
                size = os.path.getsize(file_path)
                # limit: 2MB for full features, 10MB max load
                if size > 10 * 1024 * 1024:
                    self.setText("File too large to open ( > 10MB).")
                    self.setReadOnly(True)
                    return

                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    self.setText(f.read())
                
                # Performance: Disable lexer/folding for files > 2MB
                if size > 2 * 1024 * 1024:
                    self.setLexer(None)
                    self.setFolding(QsciScintilla.FoldStyle.NoFoldStyle)
                    print(f"Large file detected ({size} bytes). Syntax highlighting disabled.")
            except Exception as e:
                self.setText(f"Error reading file: {e}")


        self.setModified(False)
        self.modificationChanged.connect(self._on_modification_changed)

    def _setup_editor(self):
        """Configure editor behavior."""
        # Font stack: VS Code modern default -> VS Code classic -> Others
        font = QFont("Cascadia Code", 11) # Reduced size to fix "zoomed-in" feel
        font.setFamilies(["Cascadia Code", "Consolas", "Fira Code", "Droid Sans Mono", "Monospace"])
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)

        # Line numbers
        self.setMarginType(0, QsciScintilla.MarginType.NumberMargin)
        self.setMarginWidth(0, "0000") # Slimmer margin
        self.setMarginsForegroundColor(QColor("#858585"))

        # Current line highlight
        self.setCaretLineVisible(True)

        # Indentation
        self.setIndentationsUseTabs(False)
        self.setTabWidth(4)
        self.setAutoIndent(True)
        self.setIndentationGuides(False) # Cleaner look without guides

        # Brace matching
        self.setBraceMatching(QsciScintilla.BraceMatch.StrictBraceMatch)

        # Code folding
        self.setFolding(QsciScintilla.FoldStyle.BoxedTreeFoldStyle, 2)

        # Hide edge line (vertical line)
        self.setEdgeMode(QsciScintilla.EdgeMode.EdgeNone)

        # Auto-complete
        self.setAutoCompletionSource(QsciScintilla.AutoCompletionSource.AcsAll)
        self.setAutoCompletionThreshold(2)
        self.setAutoCompletionCaseSensitivity(False)

        # Word wrap off
        self.setWrapMode(QsciScintilla.WrapMode.WrapNone)

        # EOL visibility
        self.setEolVisibility(False)

        # Whitespace
        self.setWhitespaceVisibility(QsciScintilla.WhitespaceVisibility.WsInvisible)

    def _setup_theme(self, theme: dict):
        """Apply theme colors to the editor."""
        # Paper (background) and text color
        self.setPaper(QColor(theme['editor_bg']))
        self.setColor(QColor(theme['editor_fg']))

        # Margins
        self.setMarginsBackgroundColor(QColor(theme['editor_gutter_bg']))
        self.setMarginsForegroundColor(QColor(theme['editor_gutter_fg']))

        # Caret line
        self.setCaretLineBackgroundColor(QColor(theme['editor_line_highlight']))
        self.setCaretForegroundColor(QColor(theme['editor_fg']))

        # Selection
        self.setSelectionBackgroundColor(QColor(theme['editor_selection']))

        # Fold margin
        self.setFoldMarginColors(QColor(theme['editor_gutter_bg']),
                                  QColor(theme['editor_gutter_bg']))

        # Edge line
        self.setEdgeColor(QColor(theme['border']))

        # Indentation guides
        self.setIndentationGuidesBackgroundColor(QColor(theme['border']))
        self.setIndentationGuidesForegroundColor(QColor(theme['border']))

        # Matched brace
        self.setMatchedBraceBackgroundColor(QColor(theme['bg_active']))
        self.setMatchedBraceForegroundColor(QColor(theme['text_bright']))

    def _setup_lexer(self, file_path: str):
        """Set up syntax highlighting based on file extension."""
        ext = os.path.splitext(file_path)[1].lower() if file_path else ""
        lexer_class = LEXER_MAP.get(ext)

        if lexer_class is None:
            return

        lexer = lexer_class(self)

        # Base font (same as editor)
        font = QFont("Cascadia Code", 11)
        font.setFamilies(["Cascadia Code", "Consolas", "Fira Code", "Droid Sans Mono", "Monospace"])
        font.setStyleHint(QFont.StyleHint.Monospace)
        lexer.setDefaultFont(font)


        # Default colors
        lexer.setDefaultPaper(QColor(self.theme['editor_bg']))
        lexer.setDefaultColor(QColor(self.theme['editor_fg']))

        # Python-specific syntax colors
        if isinstance(lexer, QsciLexerPython):
            t = self.theme
            lexer.setColor(QColor(t['editor_fg']), QsciLexerPython.Default)
            lexer.setColor(QColor(t['syntax_comment']), QsciLexerPython.Comment)
            lexer.setColor(QColor(t['syntax_comment']), QsciLexerPython.CommentBlock)
            lexer.setColor(QColor(t['syntax_number']), QsciLexerPython.Number)
            lexer.setColor(QColor(t['syntax_string']), QsciLexerPython.DoubleQuotedString)
            lexer.setColor(QColor(t['syntax_string']), QsciLexerPython.SingleQuotedString)
            lexer.setColor(QColor(t['syntax_string']), QsciLexerPython.TripleSingleQuotedString)
            lexer.setColor(QColor(t['syntax_string']), QsciLexerPython.TripleDoubleQuotedString)
            lexer.setColor(QColor(t['syntax_keyword']), QsciLexerPython.Keyword)
            lexer.setColor(QColor(t['syntax_class']), QsciLexerPython.ClassName)
            lexer.setColor(QColor(t['syntax_function']), QsciLexerPython.FunctionMethodName)
            lexer.setColor(QColor(t['syntax_operator']), QsciLexerPython.Operator)
            lexer.setColor(QColor(t['syntax_decorator']), QsciLexerPython.Decorator)
            lexer.setColor(QColor(t['syntax_string']), QsciLexerPython.DoubleQuotedFString)
            lexer.setColor(QColor(t['syntax_string']), QsciLexerPython.SingleQuotedFString)
            lexer.setColor(QColor(t['syntax_string']), QsciLexerPython.TripleSingleQuotedFString)
            lexer.setColor(QColor(t['syntax_string']), QsciLexerPython.TripleDoubleQuotedFString)

            # Set paper for all styles
            for i in range(40):
                lexer.setPaper(QColor(t['editor_bg']), i)
                lexer.setFont(font, i)

        self.setLexer(lexer)

    def _on_modification_changed(self, modified):
        self._is_modified = modified

    def save_file(self):
        """Save the current file."""
        if self.file_path:
            try:
                with open(self.file_path, "w", encoding="utf-8") as f:
                    f.write(self.text())
                self.setModified(False)
                return True
            except Exception as e:
                print(f"Error saving: {e}")
                return False
        return False


class WelcomeTab(QWidget):
    """Welcome tab shown when no files are open."""

    def __init__(self, theme: dict, parent=None):
        super().__init__(parent)
        self.theme = theme

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Lutervyn IDE")
        title.setFont(QFont("Segoe UI", 28, QFont.Weight.Light))
        title.setStyleSheet(f"color: {theme['text_secondary']};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Python Development Environment")
        subtitle.setFont(QFont("Segoe UI", 14))
        subtitle.setStyleSheet(f"color: {theme['text_disabled']};")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        spacer = QLabel("")
        spacer.setFixedHeight(30)
        layout.addWidget(spacer)

        shortcuts = [
            ("Ctrl+O", "Open File"),
            ("Ctrl+N", "New File"),
            ("Ctrl+K Ctrl+O", "Open Folder"),
            ("Ctrl+Shift+F", "Search Files"),
            ("Ctrl+`", "Toggle Terminal"),
            ("F5", "Run Python File"),
        ]

        for key, desc in shortcuts:
            row = QHBoxLayout()
            row.setAlignment(Qt.AlignmentFlag.AlignCenter)
            key_label = QLabel(key)
            key_label.setFont(QFont("Cascadia Code", 12))
            key_label.setStyleSheet(f"""
                color: {theme['accent']};
                background-color: {theme['bg_medium']};
                padding: 3px 10px;
                border-radius: 3px;
            """)
            key_label.setFixedWidth(180)
            key_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

            desc_label = QLabel(desc)
            desc_label.setFont(QFont("Segoe UI", 12))
            desc_label.setStyleSheet(f"color: {theme['text_secondary']};")
            desc_label.setFixedWidth(180)

            row.addWidget(key_label)
            row.addWidget(desc_label)
            layout.addLayout(row)

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(self.theme['editor_bg']))
        p.end()


class EditorTabs(QWidget):
    """Tabbed editor area that manages multiple open files."""

    file_modified = pyqtSignal(str, bool)  # (file_path, is_modified)
    tabs_changed = pyqtSignal()

    def __init__(self, theme: dict, parent=None):
        super().__init__(parent)
        self.theme = theme
        self._open_files: dict[str, int] = {}  # file_path -> tab index

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Tab widget
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.setDocumentMode(True)
        self.tabs.tabCloseRequested.connect(self._close_tab)
        layout.addWidget(self.tabs)

        # Show welcome tab initially
        welcome = WelcomeTab(theme, self)
        self.tabs.addTab(welcome, "Welcome")

    def open_file(self, file_path: str):
        """Open a file in a new tab, or switch to it if already open."""
        # Normalize path
        file_path = os.path.normpath(file_path)

        # Already open? Switch to it.
        if file_path in self._open_files:
            self.tabs.setCurrentIndex(self._open_files[file_path])
            return

        # Remove welcome tab if it exists
        if self.tabs.count() == 1 and isinstance(self.tabs.widget(0), WelcomeTab):
            self.tabs.removeTab(0)

        # Create editor
        editor = CodeEditorWidget(file_path, self.theme, self)
        tab_name = os.path.basename(file_path)
        index = self.tabs.addTab(editor, tab_name)
        self.tabs.setCurrentIndex(index)

        # Track it
        self._open_files[file_path] = index
        self.tabs_changed.emit()

        # Listen for modifications
        editor.modificationChanged.connect(
            lambda mod, fp=file_path, idx=index: self._on_modified(fp, idx, mod))

    def _on_modified(self, file_path: str, index: int, modified: bool):
        tab_name = os.path.basename(file_path)
        if modified:
            self.tabs.setTabText(index, f"● {tab_name}")
        else:
            self.tabs.setTabText(index, tab_name)
        self.file_modified.emit(file_path, modified)

    def _close_tab(self, index: int):
        widget = self.tabs.widget(index)
        if isinstance(widget, CodeEditorWidget) and widget.file_path:
            self._open_files.pop(widget.file_path, None)

        self.tabs.removeTab(index)
        self.tabs_changed.emit()

        # Rebuild index map
        self._open_files.clear()
        for i in range(self.tabs.count()):
            w = self.tabs.widget(i)
            if isinstance(w, CodeEditorWidget) and w.file_path:
                self._open_files[w.file_path] = i

        # Show welcome if no tabs left
        if self.tabs.count() == 0:
            welcome = WelcomeTab(self.theme, self)
            self.tabs.addTab(welcome, "Welcome")

    def save_current(self):
        """Save the currently active file."""
        widget = self.tabs.currentWidget()
        if isinstance(widget, CodeEditorWidget):
            return widget.save_file()
        return False

    def get_current_editor(self) -> CodeEditorWidget | None:
        widget = self.tabs.currentWidget()
        return widget if isinstance(widget, CodeEditorWidget) else None

    def get_current_file_path(self) -> str | None:
        editor = self.get_current_editor()
        return editor.file_path if editor else None
