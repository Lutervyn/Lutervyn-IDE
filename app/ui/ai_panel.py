"""
Lutervyn AI Panel — Direct OpenRouter Integration
No aider, no shims, no mocks. Pure stdlib + PyQt6.
"""

import os
import sys
import json
import threading
import urllib.request
import urllib.error
import base64

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextBrowser,
    QTextEdit, QPushButton, QLabel, QFrame, QScrollArea,
    QSizePolicy, QComboBox, QDialog
)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer, QObject, QPoint, QEvent
from PyQt6.QtGui import QFont, QColor, QPainter, QPolygon, QPen, QBrush, QPixmap, QIcon


# ── OpenRouter Client (stdlib only) ──────────────────────────────────────────
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL  = "google/gemini-2.0-flash-001"

def get_api_key():
    """Load API key from api_key.txt if it exists."""
    try:
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "api_key.txt")
        if os.path.exists(path):
            with open(path, "r") as f:
                return f.read().strip()
    except Exception:
        pass
    # Fallback/Hardcoded (not recommended for production)
    return "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"

API_KEY = get_api_key()

# Available models (display name → OpenRouter ID)
MODELS = [
    ("GPT-4o Mini",          "openai/gpt-4o-mini"),
    ("GPT-4o",               "openai/gpt-4o"),
    ("Claude 3.5 Sonnet",    "anthropic/claude-3.5-sonnet"),
    ("Claude 3.5 Haiku",     "anthropic/claude-3.5-haiku"),
    ("Gemini 2.0 Flash",     "google/gemini-2.0-flash-001"),
    ("DeepSeek V3",          "deepseek/deepseek-chat"),
    ("Llama 3.3 70B",        "meta-llama/llama-3.3-70b-instruct"),
]

SYSTEM_PROMPT = (
    "You are Lutervyn AI, a helpful coding assistant embedded in the Lutervyn IDE. "
    "You help users write, debug, and understand code. Be concise and helpful. "
    "Format code blocks with triple backticks and specify the language."
)


def chat_completion(model, messages, on_chunk=None, abort_check=None):
    """
    Calls OpenRouter with streaming.
    abort_check: optional callable that returns True if we should stop.
    Returns the full response text.
    If on_chunk is provided, streams chunks to it for live updates.
    """
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "stream": on_chunk is not None,
    }).encode("utf-8")

    req = urllib.request.Request(OPENROUTER_URL, data=payload, headers={
        "Authorization": f"Bearer {get_api_key()}",
        "Content-Type":  "application/json",
        "HTTP-Referer":  "https://lutervyn.com",
        "X-Title":       "Lutervyn IDE",
    })

    try:
        resp = urllib.request.urlopen(req, timeout=60)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenRouter {e.code}: {body}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error: {e.reason}") from e

    if on_chunk is None:
        # ── Non-streaming ──
        data = json.loads(resp.read().decode("utf-8"))
        usage = data.get("usage", {})
        return data["choices"][0]["message"]["content"], usage

    # ── Streaming (SSE) ──
    full = []
    for raw_line in resp:
        line = raw_line.decode("utf-8").strip()
        if not line or not line.startswith("data: "):
            continue
        payload_str = line[6:]
        if payload_str == "[DONE]":
            break
        try:
            # Check for manual abort
            if abort_check and abort_check():
                break

            obj = json.loads(payload_str)
            delta = obj["choices"][0].get("delta", {})
            text = delta.get("content", "")
            if text:
                full.append(text)
                on_chunk(text)
        except (json.JSONDecodeError, KeyError, IndexError):
            continue
    return "".join(full), {}


# ── Signal bridge (thread → GUI) ─────────────────────────────────────────────
class _Signals(QObject):
    chunk    = pyqtSignal(str)
    done     = pyqtSignal(str, int, int)  # full_text, prompt_tokens, completion_tokens
    error    = pyqtSignal(str)
    status   = pyqtSignal(str)
    credits  = pyqtSignal(str)
    models_loaded = pyqtSignal(list)


# ── Markdown → HTML helper ───────────────────────────────────────────────────
import re as _re
import html as _html

def _md_to_html(md, fg="#fff"):
    """Lightweight markdown to styled HTML."""
    # If it contains our injected image data, don't escape it
    if "src=\"data:image/" in md and "<img" in md:
        # We trust our own injected HTML
        html_final = md
    else:
        html_final = _html.escape(md)
    
    # 1. Code blocks
    def _code_block(m):
        code = m.group(2)
        return (
            '<pre style="background:#1a1a2e; padding:10px; border-radius:6px; '
            'font-family:Consolas,monospace; font-size:12px; color:#e0e0e0; '
            f'margin:6px 0; overflow-x:auto;">{code}</pre>'
        )
    html_final = _re.sub(r'```(\w*)\n(.*?)```', _code_block, html_final, flags=_re.DOTALL)
    
    # Inline code
    html_final = _re.sub(r'`([^`]+)`',
        r'<code style="background:#1a1a2e; padding:2px 5px; border-radius:3px; '
        r'font-family:Consolas,monospace; font-size:12px; color:#e0e0e0;">\1</code>', html_final)
    # Bold
    html_final = _re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', html_final)
    # Italic
    html_final = _re.sub(r'\*(.+?)\*', r'<i>\1</i>', html_final)
    # Bullet lists
    html_final = _re.sub(r'^[-•] (.+)$', r'<div style="margin-left:12px;">• \1</div>', html_final, flags=_re.MULTILINE)
    # Numbered lists
    html_final = _re.sub(r'^(\d+)\. (.+)$', r'<div style="margin-left:12px;">\1. \2</div>', html_final, flags=_re.MULTILINE)
    # Headers
    html_final = _re.sub(r'^### (.+)$', r'<div style="font-size:14px; font-weight:bold; margin:6px 0;">\1</div>', html_final, flags=_re.MULTILINE)
    html_final = _re.sub(r'^## (.+)$', r'<div style="font-size:15px; font-weight:bold; margin:8px 0;">\1</div>', html_final, flags=_re.MULTILINE)
    html_final = _re.sub(r'^# (.+)$', r'<div style="font-size:16px; font-weight:bold; margin:10px 0;">\1</div>', html_final, flags=_re.MULTILINE)
    
    html_final = html_final.replace("\n", "<br>")
    return (
        f'<div style="font-family:Segoe UI,SF Pro Text,Helvetica Neue,Arial,sans-serif;'
        f' font-size:13px; color:{fg}; line-height:1.5;">{html_final}</div>'
    )


# ── Chat bubble ──────────────────────────────────────────────────────────────
class ChatBubble(QFrame):
    def __init__(self, text, is_user, theme, parent=None):
        super().__init__(parent)
        self._theme = theme
        self._is_user = is_user
        lay = QVBoxLayout(self)
        lay.setSpacing(0)

        if is_user:
            lay.setContentsMargins(10, 6, 10, 6)
        else:
            lay.setContentsMargins(12, 2, 12, 2)

        # Message body
        self.body = QLabel()
        self.body.setWordWrap(True)
        self.body.setTextFormat(Qt.TextFormat.RichText)
        self.body.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextBrowserInteraction
        )
        self.body.setStyleSheet(
            "background: transparent; padding: 0; margin: 0; border: none;"
        )
        self.body.setText(_md_to_html(text, theme.get('text_bright', '#fff')))
        self.body.setMinimumWidth(0) # IMPORTANT: Prevents layout stalling during resize
        lay.addWidget(self.body)

        # Image row (widget based for better rendering)
        self.img_container = QWidget()
        self.img_lay = QHBoxLayout(self.img_container)
        self.img_lay.setContentsMargins(0, 8, 0, 4)
        self.img_lay.setSpacing(10)
        self.img_lay.addStretch()
        self.img_container.hide()
        lay.addWidget(self.img_container)

        # Styling: grey filled box for user, transparent for AI
        if is_user:
            self.setStyleSheet(
                f"background: {theme.get('bg_active', '#2c2c2e')};"
                " border: none;"
                " border-radius: 8px; margin: 2px 8px;"
            )
        else:
            self.setStyleSheet(
                "background: transparent; border: none; margin: 0px 8px;"
            )
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)

    def set_content(self, text, images=None):
        """Render text and images."""
        fg = self._theme.get('text_bright', '#fff')
        self.body.setText(_md_to_html(text, fg))
        
        if images:
            self.img_container.show()
            # Clear old
            while self.img_lay.count() > 1:
                item = self.img_lay.takeAt(0)
                if item.widget(): item.widget().deleteLater()
            
            for img_data in images:
                lbl = QLabel()
                lbl.setFixedSize(160, 100)
                lbl.setStyleSheet("border: 1px solid #333; border-radius: 6px; background: #000;")
                
                # Convert base64 to pixmap
                try:
                    pdata = img_data.split(",")[-1]
                    ba = Qt.QtCore.QByteArray.fromBase64(pdata.encode())
                    pix = QPixmap()
                    pix.loadFromData(ba)
                    lbl.setPixmap(pix.scaled(160, 100, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
                except:
                    lbl.setText("Error")
                
                self.img_lay.insertWidget(self.img_lay.count()-1, lbl)
        else:
            self.img_container.hide()

    def append_text(self, md):
        """Live-append for streaming."""
        self.body.setText(_md_to_html(md, self._theme.get('text_bright', '#fff')))
        # Force layout recalculation if parented
        if self.parentWidget():
            self.parentWidget().adjustSize()


def create_auto_icon():
    """Create a beautiful ✨ styled magic wand/star icon."""
    pix = QPixmap(16, 16)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    # Draw a 4-pointed star
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(QColor("#ffab00"))) # Gold/Star color
    
    path = QPolygon()
    path << QPoint(8, 0) << QPoint(10, 6) << QPoint(16, 8) << QPoint(10, 10) \
         << QPoint(8, 16) << QPoint(6, 10) << QPoint(0, 8) << QPoint(6, 6)
    painter.drawPolygon(path)
    painter.end()
    return QIcon(pix)


# ── Custom Input (Handles drops/pasting) ─────────────────────────────────────
class AiInput(QTextEdit):
    image_dropped = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                if path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif')):
                    self.image_dropped.emit(path)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)


# ── Vision Icon Helper ───────────────────────────────────────────────────────
def create_vision_icon():
    """Create a small 'V' icon for vision-capable models."""
    pix = QPixmap(16, 16)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    # Draw a small blue square with a 'V'
    painter.setBrush(QBrush(QColor("#007aff")))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(0, 0, 16, 16, 3, 3)
    
    painter.setPen(QPen(QColor("white"), 1.5))
    # Draw 'V'
    painter.drawLine(4, 5, 8, 11)
    painter.drawLine(8, 11, 12, 5)
    painter.end()
    return QIcon(pix)


# ── Image Preview Overlay ────────────────────────────────────────────────────
# ── Image Preview Overlay ────────────────────────────────────────────────────
class ImagePreviewDialog(QDialog):
    def __init__(self, pixmap, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Popup | Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # We don't use full-screen geometry anymore
        # Calculate size based on image and screen
        screen_geo = self.screen().availableGeometry()
        max_w, max_h = screen_geo.width() * 0.8, screen_geo.height() * 0.8
        
        scaled_pix = pixmap.scaled(int(max_w), int(max_h), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.setFixedSize(scaled_pix.width() + 40, scaled_pix.height() + 60)
        
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        
        # Main container with border and shadow effect
        self.container = QFrame()
        self.container.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border: 1px solid #333;
                border-radius: 12px;
            }
        """)
        container_lay = QVBoxLayout(self.container)
        container_lay.setContentsMargins(10, 10, 10, 10)
        container_lay.setSpacing(10)
        
        # Header-ish area
        hdr = QHBoxLayout()
        title = QLabel("Image Preview")
        title.setStyleSheet("color: #888; font-size: 11px; border: none; background: transparent;")
        hdr.addWidget(title)
        hdr.addStretch()
        
        btn_close = QPushButton("×")
        btn_close.setFixedSize(20, 20)
        btn_close.setStyleSheet("QPushButton { color: #888; font-size: 18px; border: none; background: transparent; } QPushButton:hover { color: white; }")
        btn_close.clicked.connect(self.accept)
        hdr.addWidget(btn_close)
        container_lay.addLayout(hdr)
        
        # Image label
        img_lbl = QLabel()
        img_lbl.setPixmap(scaled_pix)
        img_lbl.setStyleSheet("border: none; background: transparent;")
        img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_lay.addWidget(img_lbl)
        
        lay.addWidget(self.container)
        
        # Center the dialog on the application window
        if parent:
            parent_geo = parent.window().geometry()
            self.move(parent_geo.center() - self.rect().center())
        else:
            self.move(screen_geo.center() - self.rect().center())

    def mousePressEvent(self, event):
        # Close if clicking outside the container or anywhere if preferred
        if not self.container.underMouse():
            self.accept()
        super().mousePressEvent(event)


# ── Send Button (Custom Painted) ──────────────────────────────────────────────
class SendButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(28, 28)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.is_stop = False

    def set_stop_mode(self, stop):
        self.is_stop = stop
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Build theme-ready colors
        theme = {}
        if hasattr(self.parent(), 'theme'):
            theme = self.parent().theme
        elif hasattr(self.parent().parent(), 'theme'):
            theme = self.parent().parent().theme

        # Circle background on hover
        if self.underMouse() and self.isEnabled():
            painter.setBrush(QBrush(QColor(theme.get('bg_hover', '#3a3a3c'))))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(self.rect().adjusted(1, 1, -1, -1))

        # Main circle fill
        if not self.isEnabled():
            bg_color = QColor(theme.get('bg_active', '#252526')) 
            arrow_color = QColor(theme.get('text_disabled', '#444446'))
        else:
            # Blue circle (Cursor style)
            # Enabled + Hover: White BG, blue arrow
            # Enabled: Blue BG, white arrow
            bg_color = QColor("#ffffff") if self.underMouse() else QColor("#007aff")
            arrow_color = QColor("#007aff") if self.underMouse() else QColor("#ffffff")

        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.PenStyle.NoPen)
        # Slightly inset the circle
        painter.drawEllipse(self.rect().adjusted(3, 3, -3, -3))

        center_x, center_y = 14, 14

        if self.is_stop:
            # Draw a stop square
            size = 8
            painter.setBrush(QBrush(arrow_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(center_x - size//2, center_y - size//2, size, size)
        else:
            # Arrow icon
            painter.setPen(QPen(arrow_color, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            # Draw a small sharp right arrow
            painter.drawLine(center_x - 3, center_y, center_x + 4, center_y) # Line
            painter.drawLine(center_x + 1, center_y - 3, center_x + 4, center_y) # Tip T
            painter.drawLine(center_x + 1, center_y + 3, center_x + 4, center_y) # Tip B


# ── Main Panel ────────────────────────────────────────────────────────────────
class AiPanel(QWidget):
    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.history = [{"role": "system", "content": SYSTEM_PROMPT}]
        self._streaming_text = ""
        self._current_bubble = None
        self._attached_images = [] # Store base64 data strings
        self._abort_requested = False
        self._sig = _Signals()
        self._sig.chunk.connect(self._on_chunk)
        self._sig.done.connect(self._on_done)
        self._sig.error.connect(self._on_error)
        self._sig.status.connect(self._on_status)
        self._sig.credits.connect(self._on_credits)
        self._sig.models_loaded.connect(self._on_models_loaded)
        self.setMinimumWidth(180) # Allow shrinking
        self._init_ui()
        QTimer.singleShot(500, self._greet)

    # ── UI setup ──────────────────────────────────────────────────────────
    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        t = self.theme  # shorthand

        # Header
        hdr = QLabel("  Lutervyn AI")
        hdr.setFixedHeight(32)
        hdr.setStyleSheet(
            f"background: {t.get('sidebar_bg', '#252526')};"
            f" color: {t.get('text_bright', '#fff')};"
            " font-weight: bold; font-size: 13px;"
        )
        root.addWidget(hdr)

        # Scroll area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet(
            f"background: {t.get('bg_darkest', '#1e1e1e')};"
        )
        self.chat_box = QWidget()
        self.chat_lay = QVBoxLayout(self.chat_box)
        self.chat_lay.setContentsMargins(0, 4, 0, 4)
        self.chat_lay.setSpacing(2)
        self.chat_lay.addStretch()
        self.scroll.setWidget(self.chat_box)
        root.addWidget(self.scroll, 1)

        # ── Consolidated Input Container (Cursor-style) ───────────────────
        input_frame = QFrame()
        input_frame.setStyleSheet(f"background: {t.get('sidebar_bg', '#000')};")
        input_root = QVBoxLayout(input_frame)
        input_root.setContentsMargins(8, 2, 8, 10) # Room at bottom

        self.input_container = QFrame()
        self.input_container.setObjectName("inputContainer")
        self.input_container.setStyleSheet(f"""
            QFrame#inputContainer {{
                background-color: #252526; /* Neutral VS Code Grey */
                border: 1px solid #333333;
                border-radius: 12px;
            }}
            QFrame#inputContainer:hover {{
                border: 1px solid #454545;
            }}
        """)
        container_lay = QVBoxLayout(self.input_container)
        container_lay.setContentsMargins(0, 0, 0, 6) # Flush at top, padding at bottom/sides
        container_lay.setSpacing(0)

        # Image Previews (Integrated inside the container)
        self.preview_lay = QHBoxLayout()
        self.preview_lay.setContentsMargins(10, 8, 10, 8)
        self.preview_lay.setSpacing(10)
        self.preview_container = QWidget()
        self.preview_container.setObjectName("previewContainer")
        self.preview_container.setLayout(self.preview_lay)
        self.preview_container.setStyleSheet("QWidget#previewContainer { background: transparent; }")
        self.preview_container.setVisible(False)
        container_lay.addWidget(self.preview_container)

        # Separator Line (Only visible when images are present)
        self.preview_sep = QFrame()
        self.preview_sep.setFixedHeight(1)
        self.preview_sep.setStyleSheet("background-color: #333333; border: none; margin: 0;")
        self.preview_sep.setVisible(False)
        container_lay.addWidget(self.preview_sep)

        # 1. Text Edit (Top)
        self.input_edit = AiInput() # Use custom subclass
        self.input_edit.setPlaceholderText("Ask anything…")
        self.input_edit.setMaximumHeight(80) # Shorter
        self.input_edit.setMinimumHeight(24) # Slightly taller for better line height
        self.input_edit.setFrameShape(QFrame.Shape.NoFrame)
        self.input_edit.setStyleSheet("""
            background: transparent;
            color: white;
            border: none;
            font-family: 'Segoe UI', sans-serif;
            font-size: 13px;
            padding: 8px 10px;
        """)
        self.input_edit.textChanged.connect(self._update_send_state)
        self.input_edit.image_dropped.connect(self._attach_image)
        container_lay.addWidget(self.input_edit)

        # 2. Bottom Row (Model Selector + Status + Send)
        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(10, 4, 6, 0)
        bottom_row.setSpacing(8)

        # Model Selector (Minimal)
        self.model_combo = QComboBox()
        self.model_combo.addItem("Fetching Models...", None)
        self.model_combo.setFixedHeight(22)
        self.model_combo.setMinimumWidth(120)
        self.model_combo.setStyleSheet(f"""
            QComboBox {{
                background: rgba(255, 255, 255, 0.05);
                color: {t.get('text_secondary', '#aeaeb2')};
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 0 20px 0 6px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 11px;
            }}
            QComboBox:hover {{
                background: rgba(255, 255, 255, 0.1);
                color: white;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 14px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 3px solid transparent;
                border-right: 3px solid transparent;
                border-top: 5px solid #8e8e93;
                margin-top: 1px;
                margin-right: 2px;
            }}
            QComboBox QAbstractItemView {{
                background-color: #252526;
                color: white;
                selection-background-color: #37373d;
                border: 1px solid #454545;
                border-radius: 6px;
                outline: none;
                padding: 4px;
            }}
        """)
        bottom_row.addWidget(self.model_combo)

        # Credits Label
        self.credits_label = QLabel("…")
        self.credits_label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.credits_label.setStyleSheet("background: transparent; border: none; color: #8e8e93; font-size: 10px;")
        bottom_row.addWidget(self.credits_label)

        bottom_row.addStretch()

        # Status Label
        self.status_label = QLabel("Ready")
        self.status_label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.status_label.setStyleSheet("background: transparent; border: none; color: #8e8e93; font-size: 10px;")
        bottom_row.addWidget(self.status_label)

        # Send Button
        self.send_btn = SendButton(self.input_container)
        self.send_btn.setEnabled(False) # Disabled by default
        self.send_btn.clicked.connect(self._on_send)
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        bottom_row.addWidget(self.send_btn)

        container_lay.addLayout(bottom_row)
        input_root.addWidget(self.input_container)

        root.addWidget(input_frame)

        # Fetch models and credits on startup
        threading.Thread(target=self._fetch_models, daemon=True).start()
        threading.Thread(target=self._fetch_credits, daemon=True).start()

    # ── Greeting ──────────────────────────────────────────────────────────
    def _greet(self):
        self._add_bubble(
            "Hi! I'm **Lutervyn AI**. Ask me anything about your code.", False
        )

    # ── Chat logic ────────────────────────────────────────────────────────
    def _add_bubble(self, text, is_user, images=None):
        self.chat_lay.takeAt(self.chat_lay.count() - 1)  # remove stretch
        b = ChatBubble(text, is_user, self.theme, self.chat_box)
        if is_user and images:
            b.set_content(text, images)
        self.chat_lay.addWidget(b)
        self.chat_lay.addStretch()
        QTimer.singleShot(50, self._scroll_down)
        return b

    def _on_send(self):
        if self.send_btn.is_stop:
            self._abort_requested = True
            self.status_label.setText("Stopping…")
            self.send_btn.setEnabled(False)
            return

        text = self.input_edit.toPlainText().strip()
        if not text and not self._attached_images:
            return
            
        images = list(self._attached_images)
        self.input_edit.clear()
        self._clear_attachments() # Clear UI and storage
        self._update_send_state()
        self._add_bubble(text or "(Analyze Image)", True, images)

        # Construct Multimodal Message
        if images:
            content = [{"type": "text", "text": text or "Analyze this image."}]
            for img in images:
                content.append({"type": "image_url", "image_url": {"url": img}})
        else:
            content = text

        self.history.append({"role": "user", "content": content})
        self._streaming_text = ""
        self._current_bubble = self._add_bubble("…", False)

        self._abort_requested = False
        self.send_btn.set_stop_mode(True)
        self.send_btn.setEnabled(True) # Keep enabled for stop
        self.status_label.setText("Analyzing…")

        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        """Runs on a background thread."""
        try:
            model = self.model_combo.currentData() or DEFAULT_MODEL
            
            # Phase 1: Model Selection
            self._sig.status.emit("🔍 Selecting best engine...")
            
            # ✨ Intelligent Model Selection logic
            if model == "auto":
                last_msg = self.history[-1]["content"]
                has_images = False
                last_text = ""
                
                if isinstance(last_msg, list):
                    for part in last_msg:
                        if isinstance(part, dict):
                            if part.get("type") == "image_url":
                                has_images = True
                            elif part.get("type") == "text":
                                last_text = part.get("text", "")
                else:
                    last_text = str(last_msg)

                # Reasoning/Thinking check (Prioritize Claude for complex tasks)
                is_reasoning = any(word in last_text.lower() for word in ["deep", "think", "logic", "proof", "math", "verify", "why"])
                
                if has_images:
                    model = "anthropic/claude-3-5-sonnet-20241022" 
                elif is_reasoning or "complex" in last_text.lower() or len(last_text) > 2000:
                    model = "anthropic/claude-3-5-sonnet-20241022"
                else:
                    # Default fast model
                    model = "google/gemini-2.0-flash-001"

            self._sig.status.emit("🧠 Thinking...")
            
            def on_chunk(ch):
                self._sig.chunk.emit(ch)
            
            def abort_check():
                return self._abort_requested

            # USE LOCAL COPY FOR THREAD SAFETY
            messages_copy = list(self.history)
            full, usage = chat_completion(model, messages_copy, on_chunk=on_chunk, abort_check=abort_check)
            pt = usage.get("prompt_tokens", 0)
            ct = usage.get("completion_tokens", 0)
            self._sig.done.emit(full, pt, ct)
        except Exception as e:
            self._sig.error.emit(str(e))

    # ── Slots (main thread) ───────────────────────────────────────────────
    def _on_chunk(self, text):
        self._streaming_text += text
        if self._current_bubble:
            self._current_bubble.append_text(self._streaming_text)
        self._scroll_down()

    def _on_done(self, full, prompt_tokens, completion_tokens):
        self.history.append({"role": "assistant", "content": full})
        if self._current_bubble:
            self._current_bubble.append_text(full)
        self.send_btn.set_stop_mode(False)
        self.send_btn.setEnabled(True)
        
        # Get current model name for reporting
        model_name = self.model_combo.currentText()
        total = prompt_tokens + completion_tokens
        
        if total > 0:
            self.status_label.setText(f"Ready ({model_name}: {total:,} tkn)")
        else:
            self.status_label.setText("Ready")
            
        self._scroll_down()

    def _on_error(self, msg):
        if self._current_bubble:
            if "401" in msg:
                err_msg = "Invalid API Key. Please check your `api_key.txt` file."
            elif "text" in msg.lower():
                err_msg = "Context processing error. Try starting a new chat."
            else:
                err_msg = f"**Error:** {msg}"
            self._current_bubble.append_text(err_msg)
        self.send_btn.set_stop_mode(False)
        self.send_btn.setEnabled(True)
        self.status_label.setText("Error — see chat")

    def _on_status(self, msg):
        self.status_label.setText(msg)

    def _update_send_state(self):
        """Enable/disable send button based on text content or images."""
        has_text = bool(self.input_edit.toPlainText().strip())
        has_images = len(self._attached_images) > 0
        self.send_btn.setEnabled(has_text or has_images)

    def _scroll_down(self):
        # Smart scroll: Only force scroll if we're already near the bottom
        bar = self.scroll.verticalScrollBar()
        # If user is more than 100px from the bottom, don't yank them down
        if bar.maximum() - bar.value() > 100:
            return

        for delay in [10, 50, 150]:
            QTimer.singleShot(delay, lambda: bar.setValue(bar.maximum()))

    def _fetch_credits(self):
        """Background thread to fetch credits."""
        try:
            current_key = get_api_key()
            req = urllib.request.Request("https://openrouter.ai/api/v1/key", headers={
                "Authorization": f"Bearer {current_key}",
            })
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = resp.read().decode("utf-8")
                data = json.loads(raw)
                d = data.get("data", {})
                
                # Some keys show 'limit' instead of 'limit_remaining'
                limit = d.get("limit_remaining")
                if limit is None:
                    limit = d.get("limit")
                
                # If we still can't find a limit, but we have usage, it might be a paid key
                usage = d.get("usage", 0)
                
                if limit is not None:
                    # Show exactly what's left
                    txt = f"${float(limit):.4f}"
                else:
                    # Fallback to usage if limit is truly null/unlimited
                    txt = f"${float(usage):.4f} used"
                
                self._sig.credits.emit(txt)
        except Exception as e:
            # Fallback for display
            self._sig.credits.emit("Balance")

    def _on_credits(self, txt):
        self.credits_label.setText(txt)

    def _fetch_models(self):
        """Fetch all models from OpenRouter, prioritizing free ones."""
        try:
            req = urllib.request.Request("https://openrouter.ai/api/v1/models")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = data.get("data", [])
                
                # Whitelist of vision-capable model keywords/IDs
                VISION_MODELS = [
                    "gpt-4o", "claude-3-5", "claude-3-opus", "claude-3-sonnet", 
                    "claude-3-haiku", "gemini-1.5", "gemini-2.0", "pixtral", 
                    "llama-3.2-11b-vision", "llama-3.2-90b-vision"
                ]

                processed = []
                for m in models:
                    name = m.get("name", "Unknown")
                    mid = m.get("id", "")
                    pricing = m.get("pricing", {})
                    is_free = float(pricing.get("prompt", "0")) == 0 and float(pricing.get("completion", "0")) == 0
                    
                    # Detect vision support
                    has_vision = any(v in mid.lower() for v in VISION_MODELS)
                    
                    if is_free:
                        display = f"✦ {name} (Free)"
                        processed.append((display, mid, 0, has_vision, True))
                    else:
                        p_prompt = float(pricing.get("prompt", 0)) * 1_000_000
                        display = f"{name} (${p_prompt:.2f}/M)"
                        processed.append((display, mid, p_prompt, has_vision, False))
                
                # Sort: Free first, then by price
                processed.sort(key=lambda x: x[2])
                self._sig.models_loaded.emit(processed)
        except Exception:
            self._sig.models_loaded.emit([])

    def _on_models_loaded(self, models):
        self.model_combo.clear()
        if not models:
            for name, mid in MODELS:
                self.model_combo.addItem(name, mid)
            return

        icon = create_vision_icon()
        auto_icon = create_auto_icon()
        # Add "Auto (Recommended)" at the top (remove emoji from label as icon exists)
        self.model_combo.addItem(auto_icon, "Auto (Recommended)", "auto")
        
        for display, mid, price, vision, free in models:
            # Clean up display (remove emoji if present)
            display = display.replace("✦ ", "").replace("✨ ", "")
            if vision:
                self.model_combo.addItem(icon, display, mid)
            else:
                self.model_combo.addItem(display, mid)
        
        self.model_combo.setCurrentIndex(0) # Default to Auto

    # ── Drag & Drop / Image Handling ─────────────────────────────────────
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        # Fallback for parent level drop
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                if path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    self._attach_image(path)
            event.acceptProposedAction()

    def _attach_image(self, path):
        if len(self._attached_images) >= 8:
            self.status_label.setText("Max 8 images")
            QTimer.singleShot(2000, lambda: self.status_label.setText("Ready"))
            return
            
        try:
            with open(path, "rb") as f:
                data = f.read()
                ext = os.path.splitext(path)[1][1:]
                b64 = base64.b64encode(data).decode("utf-8")
                img_str = f"data:image/{ext};base64,{b64}"
                self._attached_images.append(img_str)
                self._refresh_previews()
        except Exception as e:
            print(f"Error attaching image: {e}")

    def _refresh_previews(self):
        # Clear preview layout
        while self.preview_lay.count():
            item = self.preview_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not self._attached_images:
            self.preview_container.setVisible(False)
            self.preview_sep.setVisible(False)
            self._update_send_state()
            return

        self.preview_container.setVisible(True)
        self.preview_sep.setVisible(True)
        
        for i, img_data in enumerate(self._attached_images):
            # Thumbnail container
            thumb = QFrame()
            thumb.setFixedSize(54, 54)
            thumb.setStyleSheet("background: #2d2d2d; border: 1px solid #3e3e3e; border-radius: 8px;")
            thumb.setCursor(Qt.CursorShape.PointingHandCursor)
            
            lbl = QLabel(thumb)
            lbl.setFixedSize(46, 46)
            lbl.move(4, 4)
            lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents) # Let clicks go to 'thumb'
            
            pix = QPixmap()
            if img_data.startswith("data:"):
                try:
                    b64_part = img_data.split(",")[1]
                    pix.loadFromData(base64.b64decode(b64_part))
                except: pass
            
            if not pix.isNull():
                scaled_pix = pix.scaled(46, 46, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                lbl.setPixmap(scaled_pix)
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Click to preview
            # We'll use a dynamic property to store the pixmap and open on click
            thumb.setProperty("full_pixmap", pix)
            thumb.mousePressEvent = lambda e, p=pix: self._show_image_preview(p)

            # Remove button - small 'x' at corner
            btn_remove = QPushButton("×", thumb)
            btn_remove.setFixedSize(16, 16)
            btn_remove.move(40, -2)
            btn_remove.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_remove.setStyleSheet("""
                QPushButton {
                    background: #444;
                    color: #ccc;
                    border-radius: 8px;
                    border: 1px solid #555;
                    font-size: 14px;
                    line-height: 14px;
                    padding: 0;
                    margin: 0;
                }
                QPushButton:hover {
                    background: #ff4d4d;
                    color: white;
                }
            """)
            btn_remove.clicked.connect(lambda checked, idx=i: self._remove_attachment(idx))
            
            self.preview_lay.addWidget(thumb)
            
        self.preview_lay.addStretch()
        self._update_send_state()

    def _show_image_preview(self, pixmap):
        if not pixmap or pixmap.isNull():
            return
        dlg = ImagePreviewDialog(pixmap, self)
        dlg.exec()

    def _remove_attachment(self, index):
        if 0 <= index < len(self._attached_images):
            self._attached_images.pop(index)
            self._refresh_previews()

    def _clear_attachments(self):
        self._attached_images = []
        self._refresh_previews()
