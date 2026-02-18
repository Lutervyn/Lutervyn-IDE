"""
Lutervyn AI Panel — Direct OpenRouter Integration Pure stdlib + PyQt6.
"""

import os
import sys
import json
import threading
import urllib.request
import urllib.error
import base64
import re
import time
import html as _html

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextBrowser,
    QTextEdit, QPushButton, QLabel, QFrame, QScrollArea,
    QSizePolicy, QComboBox, QDialog
)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer, QObject, QPoint, QEvent, QByteArray
from PyQt6.QtGui import QFont, QColor, QPainter, QPolygon, QPen, QBrush, QPixmap, QIcon, QClipboard
from PyQt6.QtWidgets import QApplication


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
    # Fallback/Hardcoded (DISABLED for security)
    return ""

API_KEY = get_api_key()

# Available models (display name → OpenRouter ID)
MODELS = [
    ("GPT-4o Mini",          "openai/gpt-4o-mini"),
    ("GPT-4o",               "openai/gpt-4o"),
    ("Claude 3.5 Sonnet",    "anthropic/claude-3-5-sonnet"),
    ("Claude 3.5 Haiku",     "anthropic/claude-3-5-haiku"),
    ("Gemini 2.0 Flash",     "google/gemini-2.0-flash-001"),
    ("DeepSeek V3",          "deepseek/deepseek-chat"),
    ("Llama 3.3 70B",        "meta-llama/llama-3.3-70b-instruct"),
]

SYSTEM_PROMPT = (
    "You are Lutervyn AI, a professional coding agent embedded in the Lutervyn IDE. "
    "You have direct access to the workspace and can perform file operations.\n\n"
    "TOOL USE PROTOCOL:\n"
    "1. [READ_FILE: path] - Request to read a file's content. The IDE will provide it in the next turn.\n"
    "2. [WRITE_FILE: path]\ncontent\n[/WRITE_FILE] - Create or overwrite a file with the given content.\n"
    "3. [CREATE_FOLDER: path] - Create a new directory.\n\n"
    "GUIDELINES:\n"
    "- Use these tags in your response. Do not explain them, just use them.\n"
    "- After a [READ_FILE] tag, the IDE will automatically trigger a second turn with the file content.\n"
    "- Always specify the full or relative path as shown in the file tree.\n"
    "- For code edits, prefer complete file writes for now.\n"
    "- Use markdown for your final explanation to the user."
)


def chat_completion(model, messages, on_chunk=None, on_thought=None, abort_check=None):
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
    thought = []
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
            
            # Capture reasoning (OpenRouter / DeepSeek / Gemini style)
            reasoning = delta.get("reasoning") or delta.get("thought")
            if reasoning:
                thought.append(reasoning)
                if on_thought: on_thought(reasoning)
                
            text = delta.get("content", "")
            if text:
                full.append(text)
                if on_chunk: on_chunk(text)
        except (json.JSONDecodeError, KeyError, IndexError):
            continue
    return "".join(full), {} 


# ── Signal bridge (thread → GUI) ─────────────────────────────────────────────
class _Signals(QObject):
    chunk    = pyqtSignal(str)
    thought  = pyqtSignal(str)
    done     = pyqtSignal(str, int, int)  # full_text, prompt_tokens, completion_tokens
    error    = pyqtSignal(str)
    status   = pyqtSignal(str)
    system   = pyqtSignal(str) # For 🛠️ System: Reading... messages
    credits  = pyqtSignal(str)
    models_loaded = pyqtSignal(list)


# ── Markdown → HTML helper ───────────────────────────────────────────────────
def _md_to_html(md, fg="#fff"):
    """Simplified markdown to styled HTML (code handled by CodeBlockWidget)."""
    html_final = _html.escape(md)
    # Inline code
    html_final = re.sub(r'`([^`]+)`',
        r'<code style="background:#2d2d2d; padding:2px 4px; border-radius:3px; '
        r'font-family:Consolas,monospace; font-size:12px; color:#e0e0e0;">\1</code>', html_final)
    # Bold
    html_final = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', html_final)
    # Italic
    html_final = re.sub(r'\*(.+?)\*', r'<i>\1</i>', html_final)
    # Lists
    html_final = re.sub(r'^[-•] (.+)$', r'<div style="margin-left:12px;">• \1</div>', html_final, flags=re.MULTILINE)
    # Lines
    html_final = html_final.replace("\n", "<br>")
    return (
        f'<div style="font-family:Segoe UI; font-size:13px; color:{fg}; '
        f'line-height:1.5; white-space: pre-wrap; word-wrap: break-word;">{html_final}</div>'
    )

# ── Code Block Widget ────────────────────────────────────────────────────────
class CodeBlockWidget(QFrame):
    def __init__(self, code, lang="", theme=None, parent=None):
        super().__init__(parent)
        self._code = code
        self.setStyleSheet(f"""
            QFrame {{
                background-color: #252526;
                border-radius: 6px;
                margin: 6px 0;
            }}
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Header with Language and Copy Button
        header = QFrame()
        header.setFixedHeight(32)
        header.setStyleSheet("background-color: #2d2d2d; border-top-left-radius: 6px; border-top-right-radius: 6px;")
        hlay = QHBoxLayout(header)
        hlay.setContentsMargins(10, 0, 10, 0)
        hlay.setSpacing(10)
        hlay.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        lang_lbl = QLabel(lang.upper() or "CODE")
        lang_lbl.setMinimumWidth(0)
        lang_lbl.setStyleSheet("color: #888; font-size: 10px; font-weight: bold;")
        hlay.addWidget(lang_lbl)
        hlay.addStretch(1) # Stretch in middle

        self.copy_btn = QPushButton("Copy")
        self.copy_btn.setMinimumWidth(40)
        self.copy_btn.setStyleSheet("""
            QPushButton {
                background: transparent; border: none; color: #888; font-size: 11px; padding: 2px 8px;
            }
            QPushButton:hover { color: white; background: #3e3e3e; border-radius: 3px; }
        """)
        self.copy_btn.clicked.connect(self._copy_code)
        hlay.addWidget(self.copy_btn)
        lay.addWidget(header)

        # Code Content
        self.content = QLabel(code)
        self.content.setWordWrap(True)
        self.content.setMinimumWidth(0)
        self.content.setTextFormat(Qt.TextFormat.PlainText) # Keep as text
        self.content.setStyleSheet("""
            color: #d4d4d4; font-family: 'Consolas', 'Courier New', monospace; 
            font-size: 12px; padding: 12px; line-height: 1.4;
        """)
        lay.addWidget(self.content)

    def _copy_code(self):
        QApplication.clipboard().setText(self._code)
        self.copy_btn.setText("Copied!")
        QTimer.singleShot(2000, lambda: self.copy_btn.setText("Copy"))


# ── Chat bubble ──────────────────────────────────────────────────────────────
class ChatBubble(QFrame):
    def __init__(self, text, is_user, theme, parent=None):
        super().__init__(parent)
        self._theme = theme
        self._is_user = is_user
        self._widgets = [] # Track added widgets for clearing
        
        lay = QVBoxLayout(self)
        lay.setSpacing(0)
        lay.setContentsMargins(12, 2, 12, 2) if not is_user else lay.setContentsMargins(10, 6, 10, 6)

        # Main Layout for content
        self.content_lay = QVBoxLayout()
        self.content_lay.setSpacing(8)
        self.content_lay.setContentsMargins(0, 0, 0, 0)
        lay.addLayout(self.content_lay)

        # Reasoning Block (Collapsible)
        self.thought_box = QFrame()
        self.thought_box.setStyleSheet(f"background: {theme.get('bg_active', '#2c2c2e')}; border-left: 2px solid #555; margin: 4px 0; border-radius: 4px;")
        tlay = QVBoxLayout(self.thought_box)
        tlay.setContentsMargins(0, 0, 0, 0)
        tlay.setSpacing(0)

        # Thought Header
        self.thought_header = QPushButton("  > Thought")
        self.thought_header.setCheckable(True)
        self.thought_header.setChecked(False)
        self.thought_header.setStyleSheet("""
            QPushButton {
                background: transparent; border: none; text-align: left;
                color: #aaa; font-size: 12px;
                padding: 6px 4px;
            }
            QPushButton:hover { color: white; }
        """)
        self.thought_header.clicked.connect(self._toggle_thought)
        tlay.addWidget(self.thought_header)

        # Thought Body
        self.thought_body = QLabel()
        self.thought_body.setWordWrap(True)
        self.thought_body.setMinimumWidth(0)
        self.thought_body.setStyleSheet("color: #aaa; font-size: 12px; font-style: italic; padding: 0 10px 8px 10px;")
        tlay.addWidget(self.thought_body)
        self.thought_body.hide()
        
        self.thought_box.hide()
        self.content_lay.addWidget(self.thought_box)
        
        self.thought_start_time = None

        # Image row (Scrollable)
        self.img_scroll = QScrollArea()
        self.img_scroll.setWidgetResizable(True)
        self.img_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.img_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.img_scroll.setFixedHeight(120)
        self.img_scroll.setStyleSheet("background: transparent; border: none;")
        
        self.img_content = QWidget()
        self.img_lay = QHBoxLayout(self.img_content)
        self.img_lay.setContentsMargins(0, 4, 0, 4)
        self.img_lay.setSpacing(10)
        self.img_lay.addStretch()
        
        self.img_scroll.setWidget(self.img_content)
        self.img_scroll.hide()
        lay.addWidget(self.img_scroll)

        # Footer (Usage info)
        self.footer = QLabel()
        self.footer.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.footer.setStyleSheet("color: #555; font-size: 10px; margin-top: 2px;")
        lay.addWidget(self.footer)
        self.footer.hide()

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

        # Initial text rendering (now that all components are ready)
        if text and text != "…":
            self.set_content(text)

    def set_content(self, text, images=None):
        """Render text and images."""
        # Clear existing widgets
        for w in self._widgets:
            w.deleteLater()
        self._widgets.clear()
        
        # Parse and add parts
        parts = self._parse_markdown(text)
        for ptype, content, lang in parts:
            if ptype == "text":
                lbl = QLabel()
                lbl.setWordWrap(True)
                lbl.setMinimumWidth(0)
                lbl.setTextFormat(Qt.TextFormat.RichText)
                lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
                lbl.setStyleSheet("background: transparent; border: none;")
                lbl.setText(_md_to_html(content, self._theme.get('text_bright', '#fff')))
                self.content_lay.addWidget(lbl)
                self._widgets.append(lbl)
            else:
                code_w = CodeBlockWidget(content, lang, self._theme)
                self.content_lay.addWidget(code_w)
                self._widgets.append(code_w)

        if images:
            self.img_scroll.show()
            # Clear old images
            while self.img_lay.count() > 1:
                item = self.img_lay.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            
            for img_data in images:
                lbl = QLabel()
                lbl.setFixedSize(160, 100)
                lbl.setStyleSheet("border: 1px solid #333; border-radius: 6px; background: #000;")
                try:
                    pdata = img_data.split(",")[1] if "," in img_data else img_data
                    raw_data = base64.b64decode(pdata)
                    pix = QPixmap()
                    if pix.loadFromData(raw_data):
                        lbl.setPixmap(pix.scaled(160, 100, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
                    else:
                        lbl.setText("Invalid Image")
                except Exception as e:
                    lbl.setText(f"Error: {type(e).__name__}")
                self.img_lay.insertWidget(self.img_lay.count()-1, lbl)
        else:
            self.img_scroll.hide()

    def append_text(self, md):
        """Live-append for streaming response."""
        self.set_content(md) # Direct re-render for now (streaming chunks can be complex with multi-widget)
        if self.parentWidget():
            self.parentWidget().adjustSize()

    def _parse_markdown(self, md):
        """Split markdown into text and code blocks."""
        import re
        parts = []
        # Pattern for code blocks: ```[lang]\n[code]```
        pattern = r"```(\w*)\n?(.*?)```"
        last_end = 0
        for match in re.finditer(pattern, md, re.DOTALL):
            # Text before code block
            text_before = md[last_end:match.start()].strip()
            if text_before:
                parts.append(("text", text_before, ""))
            
            # Code block
            lang = match.group(1)
            code = match.group(2)
            parts.append(("code", code, lang))
            last_end = match.end()
        
        # Remaining text
        text_after = md[last_end:].strip()
        if text_after:
            # If we're still streaming, the last part might be an incomplete code block?
            # But the regex won't match if it's not closed.
            # So let's check for an opening but no closing.
            if "```" in text_after:
                code_start = text_after.find("```")
                before_unfinished = text_after[:code_start].strip()
                if before_unfinished:
                    parts.append(("text", before_unfinished, ""))
                
                unfinished_code_raw = text_after[code_start+3:]
                # Try to extract language
                lang_match = re.match(r"^(\w+)\n?", unfinished_code_raw)
                if lang_match:
                    lang = lang_match.group(1)
                    code = unfinished_code_raw[len(lang)+1:]
                else:
                    lang = ""
                    code = unfinished_code_raw
                parts.append(("code", code, lang))
            else:
                parts.append(("text", text_after, ""))
                
        return parts

    def append_thought(self, md):
        """Live-append for reasoning/thinking."""
        import time
        if not self.thought_start_time:
            self.thought_start_time = time.time()
            
        self.thought_box.show()
        current = self.thought_body.text()
        self.thought_body.setText(current + md)
        
        # Update header with timer
        elapsed = int(time.time() - self.thought_start_time)
        self.thought_header.setText(f"  > Thought for {elapsed}s")
        
        if self.parentWidget():
            self.parentWidget().adjustSize()

    def finalize_thought(self):
        """Stop the timer and show final count."""
        import time
        if self.thought_start_time:
            elapsed = int(time.time() - self.thought_start_time)
            self.thought_header.setText(f"  > Thought for {elapsed}s")

    def _toggle_thought(self):
        """Expand/collapse reasoning."""
        is_visible = self.thought_body.isVisible()
        self.thought_body.setVisible(not is_visible)
        # Update chevron (simplified)
        txt = self.thought_header.text()
        if not is_visible:
            self.thought_header.setText(txt.replace("> ", "v "))
        else:
            self.thought_header.setText(txt.replace("v ", "> "))
            
        if self.parentWidget():
            self.parentWidget().adjustSize()

    def set_usage(self, tokens, cost):
        """Show tokens and cost at the bottom."""
        if tokens > 0:
            self.footer.setText(f"{tokens} tokens · ${cost:.4f}")
            self.footer.show()


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
    file_dropped  = pyqtSignal(str)

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
                else:
                    self.file_dropped.emit(path)
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
class ImagePreviewDialog(QDialog):
    def __init__(self, pixmap, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Popup | Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
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
        self._attached_files = []  # Store absolute paths
        self._abort_requested = False
        self._sig = _Signals()
        self._sig.chunk.connect(self._on_chunk)
        self._sig.thought.connect(self._on_thought_token)
        self._sig.done.connect(self._on_done)
        self._sig.error.connect(self._on_error)
        self._sig.status.connect(self._on_status)
        self._sig.system.connect(self._on_system_msg)
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
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet(
            f"background: {t.get('bg_darkest', '#1e1e1e')};"
        )
        self.chat_box = QWidget()
        self.chat_box.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.MinimumExpanding)
        self.chat_lay = QVBoxLayout(self.chat_box)
        self.chat_lay.setContentsMargins(8, 4, 8, 4)
        self.chat_lay.setSpacing(10)
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

        # File Chips (Context)
        self.file_chip_lay = QHBoxLayout()
        self.file_chip_lay.setContentsMargins(10, 4, 10, 4)
        self.file_chip_lay.setSpacing(6)
        self.file_chip_container = QWidget()
        self.file_chip_container.setObjectName("fileChipContainer")
        self.file_chip_container.setLayout(self.file_chip_lay)
        self.file_chip_container.setStyleSheet("QWidget#fileChipContainer { background: transparent; }")
        self.file_chip_container.setVisible(False)
        container_lay.addWidget(self.file_chip_container)

        # Separator Line (Only visible when items are present)
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
            font-family: 'Segoe UI', 'Inter', sans-serif;
            font-size: 12px;
            padding: 8px 10px;
        """)
        self.input_edit.textChanged.connect(self._update_send_state)
        self.input_edit.image_dropped.connect(self._attach_image)
        self.input_edit.file_dropped.connect(self._attach_file)
        container_lay.addWidget(self.input_edit)

        # 2. Bottom Row (Model Selector + Status + Send)
        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(10, 4, 6, 0)
        bottom_row.setSpacing(8)

        # Model Selector (Minimal)
        self.model_combo = QComboBox()
        self.model_combo.addItem("Fetching Models...", None)
        self.model_combo.setFixedHeight(26)
        self.model_combo.setMinimumWidth(80) # Much smaller minimum
        self.model_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.model_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.model_combo.setStyleSheet(f"""
            QComboBox {{
                background: rgba(255, 255, 255, 0.05);
                color: {t.get('text_secondary', '#aeaeb2')};
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 0 15px 0 6px; /* Reduced padding */
                font-family: 'Segoe UI', 'Inter', sans-serif; 
                font-size: 10px; 
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

        # Mode Toggles (Ask / Agent)
        self.mode_group = QFrame()
        self.mode_group.setStyleSheet("background: rgba(255, 255, 255, 0.03); border-radius: 4px; padding: 2px;")
        mode_lay = QHBoxLayout(self.mode_group)
        mode_lay.setContentsMargins(2, 2, 2, 2)
        mode_lay.setSpacing(2)

        self.ask_btn = QPushButton("Ask")
        self.agent_btn = QPushButton("Agent")
        
        for btn in [self.ask_btn, self.agent_btn]:
            btn.setCheckable(True)
            btn.setFixedHeight(18)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: transparent; border: none; color: #888; 
                    font-size: 10px; padding: 0 8px; font-weight: bold;
                }
                QPushButton:checked {
                    background: #3e3e3e; color: white; border-radius: 2px;
                }
                QPushButton:hover:!checked { color: #ccc; }
            """)

        self.ask_btn.setChecked(True) # Default
        self.ask_btn.clicked.connect(lambda: self._set_mode("ask"))
        self.agent_btn.clicked.connect(lambda: self._set_mode("agent"))

        mode_lay.addWidget(self.ask_btn)
        mode_lay.addWidget(self.agent_btn)
        bottom_row.addWidget(self.mode_group)

        bottom_row.addStretch()

        # Credits Label (Hidden - usage now shown in message bubble footer)
        self.credits_label = QLabel("")
        self.credits_label.hide()
        
        # Send Button
        self.send_btn = SendButton(self.input_container)
        self.send_btn.setEnabled(False) # Disabled by default
        self.send_btn.clicked.connect(self._on_send)
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setStyleSheet("margin-right: 4px;") # Space from edge
        bottom_row.addWidget(self.send_btn)

        container_lay.addLayout(bottom_row)
        input_root.addWidget(self.input_container)

        root.addWidget(input_frame)

        # Fetch models and credits on startup
        threading.Thread(target=self._fetch_models, daemon=True).start()
        threading.Thread(target=self._fetch_credits, daemon=True).start()

    # ── Greeting ──────────────────────────────────────────────────────────
    def _greet(self):
        if not API_KEY:
            self._add_bubble(
                "⚠️ **API Key Missing!**\nPlease create an `api_key.txt` file in the project root and paste your OpenRouter key there to start using the AI.", False
            )
        else:
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
            self.send_btn.setEnabled(False)
            return

        text = self.input_edit.toPlainText().strip()
        if not text and not self._attached_images:
            return
            
        images = list(self._attached_images)
        files  = list(self._attached_files)
        
        self.input_edit.clear()
        self._clear_attachments() # Clear UI and storage
        self._update_send_state()
        
        # Build prompt suffix with file context
        context_text = ""
        for fpath in files:
            try:
                base = os.path.basename(fpath)
                with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                context_text += f"\n\n--- REFERENCE FILE: {base} ---\n{content}\n--- END {base} ---"
            except Exception as e:
                context_text += f"\n\nError reading attached file {fpath}: {e}"

        final_text = (text or "(Analyze Item)") + context_text
        self._add_bubble(text or "(Analyze Item)", True, images)

        # Construct Multimodal Message
        if images:
            content = [{"type": "text", "text": final_text or "Analyze this image."}]
            for img in images:
                content.append({"type": "image_url", "image_url": {"url": img}})
        else:
            content = final_text

        self.history.append({"role": "user", "content": content})
        self._streaming_text = ""
        self._current_bubble = self._add_bubble("…", False)

        self._abort_requested = False
        self.send_btn.set_stop_mode(True)
        self.send_btn.setEnabled(True) # Keep enabled for stop

        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        """Runs on a background thread with Tool-Use support."""
        try:
            model = self.model_combo.currentData() or DEFAULT_MODEL
            is_agent = self.agent_btn.isChecked()
            
            # Phase 1: Context Injection
            root_dir = os.getcwd()
            file_tree = self._scan_workspace(root_dir)
            
            # Fresh copy of history starting with injected system prompt
            current_history = list(self.history)
            if current_history:
                current_history[0]["content"] = f"{SYSTEM_PROMPT}\n\nCURRENT WORKSPACE:\n{file_tree}"

            max_turns = 5
            turn_count = 0
            cumulative_usage = {"prompt_tokens": 0, "completion_tokens": 0}
            
            while turn_count < max_turns:
                turn_count += 1
                
                # Model Selection logic moved inside loop for auto-turns
                self._sig.status.emit("🔍 Selecting engine...")
                active_model = model
                if active_model == "auto":
                    last_text = ""
                    last_msg = current_history[-1]["content"]
                    if isinstance(last_msg, list):
                        for part in last_msg:
                            if isinstance(part, dict) and part.get("type") == "text":
                                last_text = part.get("text", "")
                    else:
                        last_text = str(last_msg)

                    if is_agent:
                        active_model = "anthropic/claude-3-5-sonnet-20241022"
                    elif any(word in last_text.lower() for word in ["logic", "why", "code", "create", "read"]):
                        active_model = "anthropic/claude-3-5-sonnet-20241022"
                    else:
                        active_model = "google/gemini-2.0-flash-001"

                self._sig.status.emit("🧠 Thinking..." if not is_agent else "🕵️ Agent working...")
                
                def on_chunk(ch): self._sig.chunk.emit(ch)
                def on_thought(th): self._sig.thought.emit(th)
                def abort(): return self._abort_requested

                try:
                    full, usage = chat_completion(active_model, current_history, 
                                                  on_chunk=on_chunk, on_thought=on_thought, abort_check=abort)
                except Exception as e:
                    # 402/429 Failover Logic
                    if any(code in str(e) for code in ["402", "429"]) and model == "auto":
                        self._sig.status.emit("💸 Engine busy/empty. Switching to Free...")
                        # Switch to a reliable free model and retry this turn
                        active_model = "google/gemini-2.0-flash-001"
                        full, usage = chat_completion(active_model, current_history, 
                                                      on_chunk=on_chunk, on_thought=on_thought, abort_check=abort)
                        cumulative_usage["prompt_tokens"] += usage.get("prompt_tokens", 0)
                        cumulative_usage["completion_tokens"] += usage.get("completion_tokens", 0)
                    else:
                        raise e
                
                current_history.append({"role": "assistant", "content": full})
                cumulative_usage["prompt_tokens"] += usage.get("prompt_tokens", 0)
                cumulative_usage["completion_tokens"] += usage.get("completion_tokens", 0)

                # --- TOOL EXECUTION ---
                # 1. CREATE_FOLDER
                folder_matches = re.finditer(r"\[CREATE_FOLDER\s*:\s*([^\]]+)\]", full)
                for m in folder_matches:
                    path = m.group(1).strip()
                    self._sig.system.emit(f"Creating folder `{path}`...")
                    try:
                        os.makedirs(os.path.join(root_dir, path), exist_ok=True)
                        self._sig.status.emit(f"📁 Created folder: {path}")
                    except Exception as e:
                        self._sig.chunk.emit(f"\n\n*Error creating folder {path}: {e}*")

                # 2. WRITE_FILE
                write_matches = re.finditer(r"\[WRITE_FILE\s*:\s*([^\]]+)\](.*?)\n?\[/WRITE_FILE\]", full, re.DOTALL)
                for m in write_matches:
                    path = m.group(1).strip()
                    content = m.group(2).strip()
                    self._sig.system.emit(f"Writing file `{path}`...")
                    try:
                        full_path = os.path.join(root_dir, path)
                        os.makedirs(os.path.dirname(full_path), exist_ok=True)
                        with open(full_path, "w", encoding="utf-8") as f:
                            f.write(content)
                        self._sig.status.emit(f"📝 Wrote file: {path}")
                    except Exception as e:
                        self._sig.chunk.emit(f"\n\n*Error writing file {path}: {e}*")

                # 3. READ_FILE (Triggers another turn)
                read_matches = re.findall(r"\[READ_FILE\s*:\s*([^\]]+)\]", full)
                if read_matches:
                    read_results = []
                    for path in read_matches:
                        path = path.strip()
                        self._sig.system.emit(f"Reading file `{path}`...")
                        try:
                            fpath = os.path.join(root_dir, path)
                            # Large file protection
                            if os.path.exists(fpath):
                                fsize = os.path.getsize(fpath) / 1024 # KB
                                if fsize > 1024: # > 1MB
                                    read_results.append(f"Error reading {path}: File too large ({int(fsize)}KB). Suggest reading specific parts.")
                                    continue

                            with open(fpath, "r", encoding="utf-8") as f:
                                # Truncate if extreme (e.g. > 10000 lines)
                                lines = f.readlines()
                                if len(lines) > 5000:
                                    content = "".join(lines[:5000]) + "\n\n[... TRUNCATED DUE TO LENGTH ...]\n"
                                else:
                                    content = "".join(lines)
                            
                            read_results.append(f"--- CONTENT OF {path} ---\n{content}\n--- END {path} ---")
                        except Exception as e:
                            read_results.append(f"Error reading {path}: {e}")
                    
                    self._sig.chunk.emit(" …") # Visual indicator of auto-turn
                    current_history.append({"role": "user", "content": "\n\n".join(read_results)})
                    continue 

                # No more tools found that require immediate turnaround
                break

            # Finalize
            self.history = current_history
            self._sig.done.emit(full, cumulative_usage["prompt_tokens"], cumulative_usage["completion_tokens"])
            
        except Exception as e:
            self._sig.error.emit(str(e))

    # ── Slots (main thread) ───────────────────────────────────────────────
    def _on_chunk(self, text):
        self._streaming_text += text
        if self._current_bubble:
            self._current_bubble.append_text(self._streaming_text)
        self._scroll_down()

    def _on_thought_token(self, thought):
        if self._current_bubble:
            self._current_bubble.append_thought(thought)
        self._scroll_down()

    def _on_done(self, full, prompt_tokens, completion_tokens):
        # self.history is already updated by the worker to handle complex multi-turn agency
        self._streaming_text = ""
        self.send_btn.set_stop_mode(False)
        self.send_btn.setEnabled(True)
        
        if self._current_bubble:
            self._current_bubble.finalize_thought()
            # Update footer with tokens & approx cost ($0.1/1M tokens avg)
            total = prompt_tokens + completion_tokens
            cost = (total / 1_000_000) * 0.1
            self._current_bubble.set_usage(total, cost)

    def _on_error(self, msg):
        if self._current_bubble:
            if "401" in msg:
                err_msg = "Invalid API Key. Please check your `api_key.txt` file."
            elif "402" in msg:
                err_msg = "Insufficient Credits. To continue for free, switch to a free model like **Gemini 2.0 Flash** in the selector below."
            elif "text" in msg.lower():
                err_msg = "Context processing error. Try starting a new chat."
            else:
                err_msg = f"**Error:** {msg}"
            self._current_bubble.append_text(err_msg)
        self.send_btn.set_stop_mode(False)
        self.send_btn.setEnabled(True)

    def _on_status(self, msg):
        pass # Status reflected in reasoning block now

    def _on_system_msg(self, msg):
        """Append a system message (e.g. tool execution) to the chat."""
        self._add_bubble(f"🛠️ **System**: {msg}", False)

    def _update_send_state(self):
        """Enable/disable send button based on text content, images, or files."""
        has_text = bool(self.input_edit.toPlainText().strip())
        has_images = len(self._attached_images) > 0
        has_files = len(self._attached_files) > 0
        self.send_btn.setEnabled(has_text or has_images or has_files)

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
                
                limit = d.get("limit_remaining")
                if limit is None:
                    limit = d.get("limit")
                
                usage = d.get("usage", 0)
                
                if limit is not None:
                    txt = f"${float(limit):.4f}"
                else:
                    txt = f"${float(usage):.4f} used"
                
                self._sig.credits.emit(txt)
        except Exception as e:
            self._sig.credits.emit("Balance")

    def _on_credits(self, msg):
        pass # Usage shown in footer

    def _fetch_models(self):
        """Fetch all models from OpenRouter, prioritizing free ones."""
        try:
            req = urllib.request.Request("https://openrouter.ai/api/v1/models")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = data.get("data", [])
                
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
                    
                    has_vision = any(v in mid.lower() for v in VISION_MODELS)
                    
                    if is_free:
                        display = f"✦ {name} (Free)"
                        processed.append((display, mid, 0, has_vision, True))
                    else:
                        p_prompt = float(pricing.get("prompt", 0)) * 1_000_000
                        display = f"{name} (${p_prompt:.2f}/M)"
                        processed.append((display, mid, p_prompt, has_vision, False))
                
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
        self.model_combo.addItem(auto_icon, "Auto", "auto")
        
        for display, mid, price, vision, free in models:
            clean_display = display.replace("✦ ", "").replace("✨ ", "").replace(" (Free)", "")
            if free:
                 clean_display += " (Free)"
                 
            if vision:
                self.model_combo.addItem(icon, clean_display, mid)
            else:
                self.model_combo.addItem(clean_display, mid)
        
        self.model_combo.setCurrentIndex(0)

    def _set_mode(self, mode):
        """Toggle between Ask and Agent modes."""
        self.ask_btn.setChecked(mode == "ask")
        self.agent_btn.setChecked(mode == "agent")

    def _scan_workspace(self, root_dir, max_depth=3):
        """Builds a string representation of the project file tree."""
        tree = []
        try:
            for root, dirs, files in os.walk(root_dir):
                level = root.replace(root_dir, '').count(os.sep)
                if level >= max_depth: continue
                
                indent = '  ' * level
                folder = os.path.basename(root)
                if folder == "" or folder.startswith('.'): continue
                if folder in ['__pycache__', 'venv', 'node_modules', 'dist', 'build']: 
                    dirs[:] = [] # Skip
                    continue
                
                tree.append(f"{indent}📁 {folder}/")
                sub_indent = '  ' * (level + 1)
                for f in files:
                    if f.startswith('.'): continue
                    tree.append(f"{sub_indent}📄 {f}")
        except Exception as e:
            return f"Error scanning workspace: {e}"
        return "\n".join(tree)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                if path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif')):
                    self._attach_image(path)
                else:
                    self._attach_file(path)
            event.acceptProposedAction()

    def _attach_image(self, path):
        if len(self._attached_images) >= 8:
            self._add_bubble("⚠️ Max 8 images allowed per message.", False)
            return
            
        try:
            with open(path, "rb") as f:
                data = f.read()
                ext = os.path.splitext(path)[1][1:]
                import base64
                b64 = base64.b64encode(data).decode("utf-8")
                img_str = f"data:image/{ext};base64,{b64}"
                self._attached_images.append(img_str)
                self._refresh_previews()
        except Exception as e:
            print(f"Error attaching image: {e}")

    def _refresh_previews(self):
        while self.preview_lay.count():
            item = self.preview_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not self._attached_images:
            self.preview_container.setVisible(False)
            if not self._attached_files:
                self.preview_sep.setVisible(False)
            return

        self.preview_container.setVisible(True)
        self.preview_sep.setVisible(True)
        
        for i, img_data in enumerate(self._attached_images):
            thumb = QFrame()
            thumb.setFixedSize(54, 54)
            thumb.setStyleSheet("background: #2d2d2d; border: 1px solid #3e3e3e; border-radius: 8px;")
            thumb.setCursor(Qt.CursorShape.PointingHandCursor)
            
            lbl = QLabel(thumb)
            lbl.setFixedSize(46, 46)
            lbl.move(4, 4)
            lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            
            pix = QPixmap()
            if img_data.startswith("data:"):
                try:
                    b64_part = img_data.split(",")[1]
                    import base64
                    pix.loadFromData(base64.b64decode(b64_part))
                except: pass
            
            if not pix.isNull():
                scaled_pix = pix.scaled(46, 46, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                lbl.setPixmap(scaled_pix)
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            thumb.setProperty("full_pixmap", pix)
            thumb.mousePressEvent = lambda e, p=pix: self._show_image_preview(p)

            btn_remove = QPushButton("×", thumb)
            btn_remove.setFixedSize(16, 16)
            btn_remove.move(40, -2)
            btn_remove.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_remove.setStyleSheet("""
                QPushButton {
                    background: #444; color: #ccc; border-radius: 8px; border: 1px solid #555;
                    font-size: 14px; line-height: 14px; padding: 0; margin: 0;
                }
                QPushButton:hover { background: #ff4d4d; color: white; }
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

    def _attach_file(self, path):
        """Attaches a file as a context chip."""
        if path in self._attached_files:
            return
        if len(self._attached_files) >= 10:
            self._add_bubble("⚠️ Max 10 files allowed per message.", False)
            return
        
        # Check size if it's a huge file
        try:
            sz = os.path.getsize(path) / 1024 # KB
            if sz > 500: # 500KB is quite large for raw text context
                self._add_bubble(f"⚠️ `{os.path.basename(path)}` is too large ({int(sz)}KB). Please only attach source files.", False)
                return
        except: pass

        self._attached_files.append(path)
        self._refresh_file_chips()

    def _refresh_file_chips(self):
        """Redraws the small file chips above the input."""
        while self.file_chip_lay.count():
            item = self.file_chip_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not self._attached_files:
            self.file_chip_container.setVisible(False)
            if not self._attached_images:
                self.preview_sep.setVisible(False)
            return

        self.file_chip_container.setVisible(True)
        self.preview_sep.setVisible(True)

        for i, fpath in enumerate(self._attached_files):
            chip = QFrame()
            chip.setFixedHeight(24)
            chip.setStyleSheet("""
                QFrame {
                    background: #3e3e3e; border-radius: 4px; border: 1px solid #555;
                }
                QFrame:hover { background: #4e4e4e; }
            """)
            clay = QHBoxLayout(chip)
            clay.setContentsMargins(6, 0, 6, 0)
            clay.setSpacing(4)

            name = os.path.basename(fpath)
            lbl = QLabel(name)
            lbl.setStyleSheet("color: white; font-size: 11px; border: none; background: transparent;")
            clay.addWidget(lbl)

            btn_del = QPushButton("×")
            btn_del.setFixedSize(14, 14)
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.setStyleSheet("""
                QPushButton { background: transparent; color: #888; border: none; font-size: 14px; padding: 0; }
                QPushButton:hover { color: white; }
            """)
            btn_del.clicked.connect(lambda checked, idx=i: self._remove_file_chip(idx))
            clay.addWidget(btn_del)

            self.file_chip_lay.addWidget(chip)
        
        self.file_chip_lay.addStretch()
        self._update_send_state()

    def _remove_file_chip(self, index):
        if 0 <= index < len(self._attached_files):
            self._attached_files.pop(index)
            self._refresh_file_chips()

    def _clear_attachments(self):
        self._attached_images = []
        self._attached_files = [] # CLEAR FILES TOO
        self._refresh_previews()
        self._refresh_file_chips()
