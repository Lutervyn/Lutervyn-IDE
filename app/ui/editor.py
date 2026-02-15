"""
Code Editor - Tabbed editor area with QScintilla-based code editing.
Features: Python syntax highlighting, line numbers, code folding,
auto-indent, bracket matching, current line highlight.
"""

import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
                              QLabel, QSizePolicy, QTabBar, QPushButton,
                              QScrollBar, QFrame)
from PyQt6.QtCore import pyqtSignal, Qt, QFileInfo, QPoint, QTimer, QRect
from PyQt6.QtGui import QFont, QColor, QPainter, QMouseEvent, QPen, QBrush
from PyQt6.Qsci import (QsciScintilla, QsciLexerPython, QsciLexerJSON,
                          QsciLexerHTML, QsciLexerCSS, QsciLexerJavaScript,
                          QsciLexerMarkdown, QsciLexerBash, QsciLexerBatch,
                          QsciLexerYAML, QsciLexerSQL, QsciLexerXML)
from app.ui.media_widgets import (ImagePreviewWidget, SVGPreviewWidget, 
                                  VideoPreviewWidget, JSONPreviewWidget)


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
        font = QFont("Cascadia Code", 11)
        font.setFamilies(["Cascadia Code", "Consolas", "Fira Code", "Droid Sans Mono", "Monospace"])
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)

        # Line numbers — margin 0
        self.setMarginType(0, QsciScintilla.MarginType.NumberMargin)
        self.setMarginWidth(0, "00000")  # Room for 5-digit line numbers
        self.setMarginsFont(font)  # Same monospace font as editor

        # Current line highlight
        self.setCaretLineVisible(True)

        # Indentation
        self.setIndentationsUseTabs(False)
        self.setTabWidth(4)
        self.setAutoIndent(True)
        self.setIndentationGuides(False)

        # Brace matching
        self.setBraceMatching(QsciScintilla.BraceMatch.StrictBraceMatch)

        # Code folding — use plain arrow style (VS Code-like), shown in margin 2
        self.setFolding(QsciScintilla.FoldStyle.PlainFoldStyle, 2)
        # Keep fold margin at fixed width (so code never shifts)
        # but hide the arrow symbols by default — show only on hover
        self._fold_margin_width = 14
        self.setMarginWidth(2, self._fold_margin_width)
        self._fold_visible = False
        self.setMouseTracking(True)

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
        bg = QColor(theme['editor_bg'])
        fg = QColor(theme['editor_fg'])
        gutter_fg = QColor(theme['editor_gutter_fg'])
        bg_hex = theme['editor_bg']

        # Paper (background) and text color
        self.setPaper(bg)
        self.setColor(fg)

        # Vertical scrollbar hidden — minimap replaces it
        # Horizontal scrollbar kept for wide lines
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet(f"""
            QsciScintilla {{
                border: none;
            }}
            QScrollBar:horizontal {{
                background: {bg_hex};
                height: 10px;
                margin: 0;
                border: none;
            }}
            QScrollBar::handle:horizontal {{
                background: rgba(121, 121, 121, 0.4);
                min-width: 20px;
                border-radius: 0px;
                margin: 0px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: rgba(121, 121, 121, 0.7);
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
                background: none;
                border: none;
            }}
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                background: {bg_hex};
            }}
        """)

        # Margins — line numbers
        self.setMarginsBackgroundColor(bg)
        self.setMarginsForegroundColor(gutter_fg)

        # Caret line
        self.setCaretLineBackgroundColor(QColor(theme['editor_line_highlight']))
        self.setCaretForegroundColor(fg)

        # Selection
        self.setSelectionBackgroundColor(QColor(theme['editor_selection']))

        # Fold margin — match editor background so it blends in
        self.setFoldMarginColors(bg, bg)

        # Fold marker colors — store for hover toggling
        # By default arrows are invisible (same color as bg).
        # On hover they become visible (gray).
        self._bg_int = bg.blue() << 16 | bg.green() << 8 | bg.red()
        self._arrow_visible_int = 0xc5c5c5   # gray when visible
        self._arrow_hidden_int = self._bg_int  # invisible = same as bg

        SC_MARKNUM_FOLDEROPEN = 31
        SC_MARKNUM_FOLDER = 30
        SC_MARKNUM_FOLDERSUB = 29
        SC_MARKNUM_FOLDERTAIL = 28
        SC_MARKNUM_FOLDEREND = 25
        SC_MARKNUM_FOLDEROPENMID = 26
        SC_MARKNUM_FOLDERMIDTAIL = 27

        SC_MARK_ARROWDOWN = 6
        SC_MARK_ARROW = 7
        SC_MARK_EMPTY = 22

        self._fold_arrow_ids = [SC_MARKNUM_FOLDER, SC_MARKNUM_FOLDEROPEN,
                                SC_MARKNUM_FOLDEREND, SC_MARKNUM_FOLDEROPENMID]

        SCI_MARKERDEFINE = 2040
        SCI_MARKERSETFORE = 2041
        SCI_MARKERSETBACK = 2042

        # Define marker shapes
        for marker_id, symbol in [
            (SC_MARKNUM_FOLDER, SC_MARK_ARROW),
            (SC_MARKNUM_FOLDEROPEN, SC_MARK_ARROWDOWN),
            (SC_MARKNUM_FOLDERSUB, SC_MARK_EMPTY),
            (SC_MARKNUM_FOLDERTAIL, SC_MARK_EMPTY),
            (SC_MARKNUM_FOLDEREND, SC_MARK_ARROW),
            (SC_MARKNUM_FOLDEROPENMID, SC_MARK_ARROWDOWN),
            (SC_MARKNUM_FOLDERMIDTAIL, SC_MARK_EMPTY),
        ]:
            self.SendScintilla(SCI_MARKERDEFINE, marker_id, symbol)
            self.SendScintilla(SCI_MARKERSETBACK, marker_id, self._bg_int)

        # Start with arrows HIDDEN (fore color = bg color = invisible)
        for mid in self._fold_arrow_ids:
            self.SendScintilla(SCI_MARKERSETFORE, mid, self._arrow_hidden_int)

        # Edge line
        self.setEdgeColor(QColor(theme['border']))

        # Indentation guides
        self.setIndentationGuidesBackgroundColor(QColor(theme['border']))
        self.setIndentationGuidesForegroundColor(QColor(theme['border']))

        # Matched brace
        self.setMatchedBraceBackgroundColor(QColor(theme['bg_active']))
        self.setMatchedBraceForegroundColor(QColor(theme['text_bright']))

    def _show_fold_arrows(self):
        """Make fold arrows visible (gray)."""
        if not self._fold_visible:
            self._fold_visible = True
            SCI_MARKERSETFORE = 2041
            for mid in self._fold_arrow_ids:
                self.SendScintilla(SCI_MARKERSETFORE, mid, self._arrow_visible_int)

    def _hide_fold_arrows(self):
        """Make fold arrows invisible (same color as background)."""
        if self._fold_visible:
            self._fold_visible = False
            SCI_MARKERSETFORE = 2041
            for mid in self._fold_arrow_ids:
                self.SendScintilla(SCI_MARKERSETFORE, mid, self._arrow_hidden_int)

    def mouseMoveEvent(self, event):
        """Show fold arrows when mouse is near the gutter area."""
        x = event.position().x() if hasattr(event.position(), 'x') else event.x()
        gutter_end = self.marginWidth(0) + self.marginWidth(1) + self.marginWidth(2)
        if x < gutter_end + 5:
            self._show_fold_arrows()
        else:
            self._hide_fold_arrows()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        """Hide fold arrows when mouse leaves the editor."""
        self._hide_fold_arrows()
        super().leaveEvent(event)

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

        # Python-specific syntax colors — VS Code Dark+ exact match
        if isinstance(lexer, QsciLexerPython):
            t = self.theme

            # ── VS Code Dark+ actual mapping (from official theme JSON) ──
            # scope "keyword.control" → #C586C0 (PURPLE) – if/for/while/return/import/from/try/except/...
            # scope "storage" / "storage.type" → #569cd6 (BLUE) – def/class
            # scope "variable.language" (self) → #569cd6 (BLUE)
            # scope "variable" → #9CDCFE (LIGHT BLUE) – variables, parameters
            # scope "entity.name.function" → #DCDCAA (YELLOW) – function names
            # scope "support.class" / "entity.name.type" → #4EC9B0 (TEAL) – class names / types
            # scope "comment" → #6A9955 (GREEN)
            # scope "string" → #CE9178 (ORANGE)
            # scope "constant.numeric" → #B5CEA8 (LIGHT GREEN)
            # scope "keyword.operator" → #D4D4D4 (GRAY)
            # scope "constant.language" (None/True/False) → #569CD6 (BLUE)
            #
            # QScintilla keyword set 0 → style 5 (Keyword)
            # QScintilla keyword set 1 → style 14 (HighlightedIdentifier)
            #
            # Strategy:
            #   Set 0 (style 5 = Keyword, PURPLE #C586C0): control-flow + import/from + operators
            #   Set 1 (style 14 = HighlightedIdentifier, BLUE #569cd6): def, class, self, None/True/False
            #   Builtins like print, len, open → keep as normal identifiers (light blue #9CDCFE)
            #     because VS Code colors them yellow only when CALLED (semantic highlighting)
            #     and we can't replicate semantic highlighting in QScintilla.

            # Style 0  — Default text
            lexer.setColor(QColor("#D4D4D4"), QsciLexerPython.Default)
            # Style 1  — Comments
            lexer.setColor(QColor("#6A9955"), QsciLexerPython.Comment)
            # Style 12 — Block comments
            lexer.setColor(QColor("#6A9955"), QsciLexerPython.CommentBlock)
            # Style 2  — Numbers
            lexer.setColor(QColor("#B5CEA8"), QsciLexerPython.Number)
            # Style 3  — Double-quoted strings
            lexer.setColor(QColor("#CE9178"), QsciLexerPython.DoubleQuotedString)
            # Style 4  — Single-quoted strings
            lexer.setColor(QColor("#CE9178"), QsciLexerPython.SingleQuotedString)
            # Style 6  — Triple single-quoted strings
            lexer.setColor(QColor("#CE9178"), QsciLexerPython.TripleSingleQuotedString)
            # Style 7  — Triple double-quoted strings
            lexer.setColor(QColor("#CE9178"), QsciLexerPython.TripleDoubleQuotedString)
            # Style 5  — Keywords set 0 → PURPLE (control flow + import/from)
            lexer.setColor(QColor("#C586C0"), QsciLexerPython.Keyword)
            # Style 8  — Class names → TEAL
            lexer.setColor(QColor("#4EC9B0"), QsciLexerPython.ClassName)
            # Style 9  — Function/method names → YELLOW
            lexer.setColor(QColor("#DCDCAA"), QsciLexerPython.FunctionMethodName)
            # Style 10 — Operators → LIGHT GRAY
            lexer.setColor(QColor("#D4D4D4"), QsciLexerPython.Operator)
            # Style 11 — Identifiers (variables, params) → LIGHT BLUE
            lexer.setColor(QColor("#9CDCFE"), QsciLexerPython.Identifier)
            # Style 13 — Unclosed strings
            lexer.setColor(QColor("#CE9178"), QsciLexerPython.UnclosedString)
            # Style 14 — Highlighted identifiers / keyword set 1
            #            (def, class, self, None, True, False) → BLUE
            lexer.setColor(QColor("#569CD6"), QsciLexerPython.HighlightedIdentifier)
            # Style 15 — Decorators → YELLOW
            lexer.setColor(QColor("#DCDCAA"), QsciLexerPython.Decorator)
            # Style 16-19 — F-strings
            lexer.setColor(QColor("#CE9178"), QsciLexerPython.DoubleQuotedFString)
            lexer.setColor(QColor("#CE9178"), QsciLexerPython.SingleQuotedFString)
            lexer.setColor(QColor("#CE9178"), QsciLexerPython.TripleSingleQuotedFString)
            lexer.setColor(QColor("#CE9178"), QsciLexerPython.TripleDoubleQuotedFString)

            # Set paper for all styles
            for i in range(40):
                lexer.setPaper(QColor(t['editor_bg']), i)
                lexer.setFont(font, i)

        self.setLexer(lexer)

        # ── Override keyword sets AFTER setLexer ──
        # Must be done after setLexer() so Scintilla has the lexer active
        if isinstance(lexer, QsciLexerPython):
            # Set 0 → style 5 (Keyword) = PURPLE #C586C0
            # Control-flow keywords — matches VS Code "keyword.control" scope
            kw_set1 = (
                "and as assert async await break continue del elif else "
                "except finally for from global if import in is lambda "
                "nonlocal not or pass raise return try while with yield"
            )
            # Set 1 → style 14 (HighlightedIdentifier) = BLUE #569CD6
            # Storage / definition keywords + variable.language + constant.language
            # matches VS Code "storage" + "variable.language" + "constant.language" scopes
            kw_set2 = (
                "def class self cls None True False"
            )
            self.SendScintilla(QsciScintilla.SCI_SETKEYWORDS, 0, kw_set1.encode())
            self.SendScintilla(QsciScintilla.SCI_SETKEYWORDS, 1, kw_set2.encode())

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


class Minimap(QsciScintilla):
    """VS Code-style minimap — a tiny read-only overview of the code on the right side."""

    def __init__(self, editor: CodeEditorWidget, theme: dict, parent=None):
        super().__init__(parent)
        self.editor = editor
        self.theme = theme
        self._dragging = False

        # Tiny font for minimap (1px effectively — Scintilla renders glyphs)
        mini_font = QFont("Cascadia Code", 1)
        mini_font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(mini_font)

        # Fixed width — VS Code minimap is about 60-80px
        self.setFixedWidth(70)
        self.setReadOnly(True)

        # Hide all margins (no line numbers, no fold margin)
        self.setMarginWidth(0, 0)
        self.setMarginWidth(1, 0)
        self.setMarginWidth(2, 0)

        # No horizontal scrollbar, vertical scrollbar shown as VS Code-style thin bar on right
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setFrameShape(QFrame.Shape.NoFrame)

        # No caret, no selection highlight, no current line
        self.setCaretWidth(0)
        self.setCaretLineVisible(False)

        # No folding
        self.setFolding(QsciScintilla.FoldStyle.NoFoldStyle)

        # No edge line
        self.setEdgeMode(QsciScintilla.EdgeMode.EdgeNone)

        # Word wrap off
        self.setWrapMode(QsciScintilla.WrapMode.WrapNone)

        # Match editor background
        bg = QColor(theme['editor_bg'])
        self.setPaper(bg)
        self.setColor(QColor(theme['editor_fg']))

        # Apply same lexer/colors as the editor
        self._mirror_lexer()

        # Sync content
        self.setText(editor.text())

        # Connect to editor changes
        editor.textChanged.connect(self._sync_text)
        editor.verticalScrollBar().valueChanged.connect(self._sync_scroll)

        # When user drags the minimap scrollbar, scroll the editor too
        self._syncing = False
        self.verticalScrollBar().valueChanged.connect(self._scrollbar_dragged)

        # Style — no border, VS Code scrollbar on right edge
        bg_hex = theme['editor_bg']
        self.setStyleSheet(f"""
            QsciScintilla {{
                border: none;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 14px;
                margin: 0;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(121, 121, 121, 0.4);
                min-height: 20px;
                border-radius: 0px;
                margin: 0px;
                margin-left: 7px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: rgba(121, 121, 121, 0.7);
                margin-left: 4px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
                background: none;
                border: none;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: transparent;
            }}
            QScrollBar:horizontal {{
                width: 0px;
                height: 0px;
            }}
        """)

    def _mirror_lexer(self):
        """Copy the lexer and syntax colors from the main editor."""
        ext = os.path.splitext(self.editor.file_path or "")[1].lower()
        lexer_class = LEXER_MAP.get(ext)
        if lexer_class is None:
            return

        lexer = lexer_class(self)
        mini_font = QFont("Cascadia Code", 1)
        mini_font.setStyleHint(QFont.StyleHint.Monospace)
        lexer.setDefaultFont(mini_font)
        lexer.setDefaultPaper(QColor(self.theme['editor_bg']))
        lexer.setDefaultColor(QColor(self.theme['editor_fg']))

        if isinstance(lexer, QsciLexerPython):
            # Apply same colors as main editor
            lexer.setColor(QColor("#D4D4D4"), QsciLexerPython.Default)
            lexer.setColor(QColor("#6A9955"), QsciLexerPython.Comment)
            lexer.setColor(QColor("#6A9955"), QsciLexerPython.CommentBlock)
            lexer.setColor(QColor("#B5CEA8"), QsciLexerPython.Number)
            lexer.setColor(QColor("#CE9178"), QsciLexerPython.DoubleQuotedString)
            lexer.setColor(QColor("#CE9178"), QsciLexerPython.SingleQuotedString)
            lexer.setColor(QColor("#CE9178"), QsciLexerPython.TripleSingleQuotedString)
            lexer.setColor(QColor("#CE9178"), QsciLexerPython.TripleDoubleQuotedString)
            lexer.setColor(QColor("#C586C0"), QsciLexerPython.Keyword)
            lexer.setColor(QColor("#4EC9B0"), QsciLexerPython.ClassName)
            lexer.setColor(QColor("#DCDCAA"), QsciLexerPython.FunctionMethodName)
            lexer.setColor(QColor("#D4D4D4"), QsciLexerPython.Operator)
            lexer.setColor(QColor("#9CDCFE"), QsciLexerPython.Identifier)
            lexer.setColor(QColor("#569CD6"), QsciLexerPython.HighlightedIdentifier)
            lexer.setColor(QColor("#DCDCAA"), QsciLexerPython.Decorator)
            for style_id in [QsciLexerPython.DoubleQuotedFString,
                             QsciLexerPython.SingleQuotedFString,
                             QsciLexerPython.TripleSingleQuotedFString,
                             QsciLexerPython.TripleDoubleQuotedFString]:
                lexer.setColor(QColor("#CE9178"), style_id)

            for i in range(40):
                lexer.setPaper(QColor(self.theme['editor_bg']), i)
                lexer.setFont(mini_font, i)

        self.setLexer(lexer)

        # Copy keyword sets
        if isinstance(lexer, QsciLexerPython):
            kw_set1 = (
                "and as assert async await break continue del elif else "
                "except finally for from global if import in is lambda "
                "nonlocal not or pass raise return try while with yield"
            )
            kw_set2 = "def class self cls None True False"
            self.SendScintilla(QsciScintilla.SCI_SETKEYWORDS, 0, kw_set1.encode())
            self.SendScintilla(QsciScintilla.SCI_SETKEYWORDS, 1, kw_set2.encode())

    def _sync_text(self):
        """Mirror the editor's text content."""
        self.setReadOnly(False)
        self.setText(self.editor.text())
        self.setReadOnly(True)

    def _sync_scroll(self):
        """Sync minimap scroll to show the same region as the editor."""
        if self._syncing:
            return
        self._syncing = True
        # Get editor's visible region
        first_visible = self.editor.firstVisibleLine()
        total_lines = self.editor.lines()
        visible_lines = self.editor.SendScintilla(
            QsciScintilla.SCI_LINESONSCREEN)

        if total_lines <= 0:
            self._syncing = False
            return

        # Scroll minimap so the editor's viewport is centered
        mini_visible = self.SendScintilla(QsciScintilla.SCI_LINESONSCREEN)
        # Position minimap so editor's first visible line is near the top
        target = max(0, first_visible - mini_visible // 4)
        self.SendScintilla(QsciScintilla.SCI_SETFIRSTVISIBLELINE, target)
        self.update()
        self._syncing = False

    def _scrollbar_dragged(self, value):
        """When user drags the minimap's scrollbar, scroll the editor."""
        if self._syncing:
            return
        self._syncing = True
        # Map minimap scrollbar value to editor scrollbar range
        mini_sb = self.verticalScrollBar()
        editor_sb = self.editor.verticalScrollBar()
        if mini_sb.maximum() > 0:
            ratio = value / mini_sb.maximum()
            editor_sb.setValue(int(ratio * editor_sb.maximum()))
        self._syncing = False

    def paintEvent(self, event):
        """Draw the minimap with a viewport highlight overlay."""
        super().paintEvent(event)

        # Draw the viewport rectangle (shows which part of code is visible in editor)
        p = QPainter(self.viewport())

        first_visible = self.editor.firstVisibleLine()
        visible_lines = self.editor.SendScintilla(QsciScintilla.SCI_LINESONSCREEN)
        mini_first = self.firstVisibleLine()

        line_height = max(1, self.textHeight(0))
        y_start = (first_visible - mini_first) * line_height
        height = visible_lines * line_height

        # Semi-transparent highlight for the visible area
        p.fillRect(QRect(0, y_start, self.width(), height),
                   QColor(255, 255, 255, 20))
        # Top and bottom border of viewport
        p.setPen(QPen(QColor(255, 255, 255, 40), 1))
        p.drawLine(0, y_start, self.width(), y_start)
        p.drawLine(0, y_start + height, self.width(), y_start + height)
        p.end()

    def mousePressEvent(self, event):
        """Click on minimap to scroll editor to that position."""
        self._dragging = True
        self._scroll_editor_to(event)

    def mouseMoveEvent(self, event):
        """Drag on minimap to scroll editor."""
        if self._dragging:
            self._scroll_editor_to(event)

    def mouseReleaseEvent(self, event):
        self._dragging = False

    def _scroll_editor_to(self, event):
        """Scroll the main editor based on click/drag position in minimap."""
        y = event.position().y() if hasattr(event.position(), 'y') else event.y()
        line_height = max(1, self.textHeight(0))
        mini_first = self.firstVisibleLine()
        target_line = mini_first + int(y / line_height)

        visible_lines = self.editor.SendScintilla(QsciScintilla.SCI_LINESONSCREEN)
        # Center the editor on the clicked line
        scroll_to = max(0, target_line - visible_lines // 2)
        self.editor.SendScintilla(QsciScintilla.SCI_SETFIRSTVISIBLELINE, scroll_to)


class EditorWithMinimap(QWidget):
    """Wraps a CodeEditorWidget + Minimap side by side."""

    def __init__(self, editor: CodeEditorWidget, theme: dict, parent=None):
        super().__init__(parent)
        self.editor = editor
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Editor on left — takes all remaining space
        layout.addWidget(editor, 1)
        # Minimap on right — fixed width, no border
        self.minimap = Minimap(editor, theme, self)
        layout.addWidget(self.minimap, 0)

        # No border/separator between editor and minimap
        self.setStyleSheet("QWidget { border: none; }")


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
        self._extension_theme_colors: dict | None = None  # stored VS Code extension theme

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

        ext = os.path.splitext(file_path)[1].lower()
        tab_name = os.path.basename(file_path)
        
        # 1. Media & Special Widgets
        if ext in ['.png', '.jpg', '.jpeg', '.bmp', '.ico']:
            wrapper = ImagePreviewWidget(file_path, self.theme, self)
        elif ext == '.svg':
            wrapper = SVGPreviewWidget(file_path, self.theme, self)
        elif ext in ['.mp4', '.avi', '.mov', '.mkv', '.webm']:
            wrapper = VideoPreviewWidget(file_path, self.theme, self)
        elif ext == '.json':
            # Professional JSON tree view
            wrapper = JSONPreviewWidget(file_path, self.theme, self)
        else:
            # 2. Default Code Editor
            editor = CodeEditorWidget(file_path, self.theme, self)
            wrapper = EditorWithMinimap(editor, self.theme, self)
            # Listen for modifications (only for code editors)
            editor.modificationChanged.connect(
                lambda mod, fp=file_path: self._on_modified(fp, mod))

            # Apply stored extension theme (if user applied one before opening this file)
            self._apply_stored_extension_theme(editor, wrapper)
        
        index = self.tabs.addTab(wrapper, tab_name)
        self.tabs.setCurrentIndex(index)

        # Track it
        self._open_files[file_path] = index
        self.tabs_changed.emit()

    def _apply_stored_extension_theme(self, editor, wrapper):
        """Apply stored extension theme to a newly opened editor + minimap."""
        if self._extension_theme_colors is None:
            return
        from app.core.extension_manager import apply_vscode_theme_to_editor
        apply_vscode_theme_to_editor(editor, self._extension_theme_colors)
        minimap = getattr(wrapper, 'minimap', None)
        if minimap:
            apply_vscode_theme_to_editor(minimap, self._extension_theme_colors)

    def apply_extension_theme_to_all(self, theme_colors: dict):
        """Apply a VS Code extension theme to ALL currently open editors and store for future tabs."""
        from app.core.extension_manager import apply_vscode_theme_to_editor
        self._extension_theme_colors = theme_colors
        count = 0
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if widget is None:
                continue
            editor = getattr(widget, 'editor', None)
            if editor is None:
                continue
            apply_vscode_theme_to_editor(editor, theme_colors)
            count += 1
            minimap = getattr(widget, 'minimap', None)
            if minimap:
                apply_vscode_theme_to_editor(minimap, theme_colors)
        return count

    def _on_modified(self, file_path: str, modified: bool):
        if file_path not in self._open_files: return
        index = self._open_files[file_path]
        tab_name = os.path.basename(file_path)
        if modified:
            self.tabs.setTabText(index, f"● {tab_name}")
        else:
            self.tabs.setTabText(index, tab_name)
        self.file_modified.emit(file_path, modified)

    def _close_tab(self, index: int):
        widget = self.tabs.widget(index)
        path = None
        if isinstance(widget, EditorWithMinimap):
            path = widget.editor.file_path
        elif hasattr(widget, "file_path"):
            path = widget.file_path
            
        if path:
            self._open_files.pop(path, None)

        self.tabs.removeTab(index)
        self.tabs_changed.emit()

        # Rebuild index map
        self._open_files.clear()
        for i in range(self.tabs.count()):
            w = self.tabs.widget(i)
            p = None
            if isinstance(w, EditorWithMinimap):
                p = w.editor.file_path
            elif hasattr(w, "file_path"):
                p = w.file_path
            if p:
                self._open_files[p] = i

        # Show welcome if no tabs left
        if self.tabs.count() == 0:
            welcome = WelcomeTab(self.theme, self)
            self.tabs.addTab(welcome, "Welcome")

    def save_current(self):
        """Save the currently active file."""
        editor = self.get_current_editor()
        if editor:
            return editor.save_file()
        return False

    def get_current_editor(self) -> CodeEditorWidget | None:
        widget = self.tabs.currentWidget()
        if isinstance(widget, EditorWithMinimap):
            return widget.editor
        if isinstance(widget, CodeEditorWidget):
            return widget
        return None

    def get_current_file_path(self) -> str | None:
        widget = self.tabs.currentWidget()
        if isinstance(widget, EditorWithMinimap):
            return widget.editor.file_path
        if hasattr(widget, "file_path"):
            return widget.file_path
        return None
