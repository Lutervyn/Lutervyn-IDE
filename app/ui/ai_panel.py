import os
import sys
import threading
import importlib.resources
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextBrowser, 
                               QTextEdit, QPushButton, QLabel, QFrame, QScrollArea,
                               QStackedWidget)
from PyQt6.QtCore import pyqtSignal, Qt, QObject, QTimer, QSize, QRect
from PyQt6.QtGui import QFont, QColor, QIcon, QPainter, QLinearGradient

# --- DEPENDENCY SHIMS ---
# Shim 'importlib_resources'
try:
    import importlib_resources
except ImportError:
    import importlib.resources as importlib_resources
    sys.modules['importlib_resources'] = importlib_resources

# Shim 'shtab' (Aider uses it for shell completion, which we don't need in a GUI)
try:
    import shtab
except ImportError:
    class MockShtab:
        def add_argument_to(self, *args, **kwargs): pass
    sys.modules['shtab'] = MockShtab()

# Add Aider paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AIDER_PATH = os.path.join(BASE_DIR, "Ai integration")
if AIDER_PATH not in sys.path:
    sys.path.append(AIDER_PATH)

class MarkdownBubble(QTextBrowser):
    """Custom text browser for markdown bubbles with better styling."""
    def __init__(self, text, is_user, theme, parent=None):
        super().__init__(parent)
        self.setOpenExternalLinks(True)
        self.setMarkdown(text)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        fg = theme['text_bright'] if not is_user else "white"
        
        self.setStyleSheet(f"""
            QTextBrowser {{
                background-color: transparent;
                color: {fg};
                border: none;
                font-family: 'Segoe UI', Tahoma, sans-serif;
                font-size: 13px;
                padding: 0px;
            }}
        """)
        
        self.document().contentsChanged.connect(self._adjust_height)

    def _adjust_height(self):
        doc_height = self.document().size().height()
        self.setFixedHeight(int(doc_height) + 12)

class ChatMessage(QFrame):
    """A single chat message bubble with Cursor style."""
    def __init__(self, text, is_user, theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.is_user = is_user
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)
        
        # Header / Author
        author_layout = QHBoxLayout()
        author_icon = QLabel("👤" if is_user else "✨")
        author_icon.setFixedSize(16, 16)
        
        author_label = QLabel("You" if is_user else "Lutervyn AI")
        author_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        author_label.setStyleSheet(f"color: {theme['text_secondary']}; opacity: 0.8;")
        
        author_layout.addWidget(author_icon)
        author_layout.addWidget(author_label)
        author_layout.addStretch()
        layout.addLayout(author_layout)
        
        # Content
        self.content = MarkdownBubble(text, is_user, theme, self)
        layout.addWidget(self.content)
        
        bg_color = theme['bg_hover']
        border_color = theme['border']
        
        self.setStyleSheet(f"""
            ChatMessage {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 8px;
                margin: 4px 12px;
            }}
        """)
        
        if is_user:
            self.setStyleSheet(f"""
                ChatMessage {{ 
                    border: 1px solid {theme['accent']}; 
                    background-color: rgba(0, 120, 215, 0.1); 
                    border-radius: 8px;
                    margin: 4px 12px;
                }}
            """)

class AiPanel(QWidget):
    """The AI Sidebar panel (Lutervyn AI)."""
    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.coder = None
        self._init_ui()
        QTimer.singleShot(500, self._init_coder)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setStyleSheet(f"background-color: {self.theme['sidebar_bg']};")

        # --- HEADER ---
        header = QFrame()
        header.setFixedHeight(35)
        header.setStyleSheet(f"border-bottom: 1px solid {self.theme['border']};")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(15, 0, 15, 0)
        
        title = QLabel("LUTERVYN AI")
        title.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {self.theme['text_bright']}; letter-spacing: 1px;")
        h_layout.addWidget(title)
        h_layout.addStretch()
        layout.addWidget(header)

        # --- CONTENT ---
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet("background: transparent; border: none;")
        
        self.chat_container = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setContentsMargins(0, 10, 0, 10)
        self.chat_layout.setSpacing(8)
        self.chat_layout.addStretch()
        
        self.scroll.setWidget(self.chat_container)
        layout.addWidget(self.scroll, 1)

        # --- INPUT AREA ---
        input_wrapper = QFrame()
        input_wrapper.setContentsMargins(12, 0, 12, 12)
        input_wrapper_layout = QVBoxLayout(input_wrapper)
        
        self.input_card = QFrame()
        self.input_card.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme['input_bg']};
                border: 1px solid {self.theme['input_border']};
                border-radius: 8px;
            }}
        """)
        card_layout = QVBoxLayout(self.input_card)
        card_layout.setContentsMargins(10, 10, 10, 8)
        card_layout.setSpacing(5)
        
        self.input_edit = QTextEdit()
        self.input_edit.setPlaceholderText("Ask Lutervyn AI to edit code...")
        self.input_edit.setMaximumHeight(150)
        self.input_edit.setFrameShape(QFrame.Shape.NoFrame)
        self.input_edit.setFont(QFont("Segoe UI", 10))
        self.input_edit.setStyleSheet("background: transparent; border: none; color: white; padding: 0;")
        self.input_edit.installEventFilter(self)
        card_layout.addWidget(self.input_edit)
        
        footer_layout = QHBoxLayout()
        self.status_label = QLabel("Initializing...")
        self.status_label.setFont(QFont("Segoe UI", 8))
        self.status_label.setStyleSheet(f"color: {self.theme['text_disabled']};")
        footer_layout.addWidget(self.status_label)
        
        footer_layout.addStretch()
        
        self.send_btn = QPushButton("Send")
        self.send_btn.setFixedSize(50, 24)
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['accent']};
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11px;
            }}
            QPushButton:hover {{ background-color: {self.theme['bg_selection']}; }}
            QPushButton:disabled {{ background-color: {self.theme['border']}; color: {self.theme['text_disabled']}; }}
        """)
        self.send_btn.clicked.connect(self._on_send)
        footer_layout.addWidget(self.send_btn)
        
        card_layout.addLayout(footer_layout)
        input_wrapper_layout.addWidget(self.input_card)
        layout.addWidget(input_wrapper)

    def _init_coder(self):
        try:
            self.status_label.setText("Starting...")
            from aider.main import main as cli_main
            
            # This is the core aider engine
            self.coder = cli_main(return_coder=True)
            self.status_label.setText("Lutervyn AI Ready")
            self.send_btn.setEnabled(True)
            
            self._add_message("Hello! I'm Lutervyn AI. Ask me to implement features, fix bugs, or explain code. I can edit files directly in your workspace.", False)
            
        except Exception as e:
            self.status_label.setText("Error")
            self._add_message(f"### Startup Error\n{e}", False)

    def _add_message(self, text, is_user):
        self.chat_layout.takeAt(self.chat_layout.count() - 1)
        bubble = ChatMessage(text, is_user, self.theme, self)
        self.chat_layout.addWidget(bubble)
        self.chat_layout.addStretch()
        QTimer.singleShot(100, lambda: self.scroll.verticalScrollBar().setValue(
            self.scroll.verticalScrollBar().maximum()))

    def _on_send(self):
        prompt = self.input_edit.toPlainText().strip()
        if not prompt or not self.coder:
            return
            
        self.input_edit.clear()
        self._add_message(prompt, True)
        
        self.send_btn.setEnabled(False)
        self.status_label.setText("Thinking...")
        
        self.current_ai_bubble = ChatMessage("", False, self.theme, self)
        self.chat_layout.takeAt(self.chat_layout.count() - 1)
        self.chat_layout.addWidget(self.current_ai_bubble)
        self.chat_layout.addStretch()
        
        self.ai_response_text = ""
        threading.Thread(target=self._run_aider, args=(prompt,), daemon=True).start()

    def _run_aider(self, prompt):
        try:
            for chunk in self.coder.run_stream(prompt):
                self.ai_response_text += chunk
                QTimer.singleShot(0, lambda: self.current_ai_bubble.content.setMarkdown(self.ai_response_text))
            
            QTimer.singleShot(0, self._on_complete)
        except Exception as e:
            QTimer.singleShot(0, lambda: self._add_message(f"**Error:** {e}", False))
            QTimer.singleShot(0, self._on_complete)

    def _on_complete(self):
        self.send_btn.setEnabled(True)
        self.status_label.setText("Lutervyn AI Ready")
        QTimer.singleShot(100, lambda: self.scroll.verticalScrollBar().setValue(
            self.scroll.verticalScrollBar().maximum()))

    def eventFilter(self, obj, event):
        if obj == self.input_edit and event.type() == event.Type.KeyPress:
            if event.key() == Qt.Key.Key_Return and not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
                self._on_send()
                return True
        return super().eventFilter(obj, event)
