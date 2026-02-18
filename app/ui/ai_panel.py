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

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextBrowser,
    QTextEdit, QPushButton, QLabel, QFrame, QScrollArea,
    QSizePolicy, QComboBox
)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer, QObject, QPoint
from PyQt6.QtGui import QFont, QColor, QPainter, QPolygon, QPen, QBrush


# ── OpenRouter Client (stdlib only) ──────────────────────────────────────────
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL  = "openai/gpt-4o-mini"
API_KEY        = "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"

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


def chat_completion(messages, model=DEFAULT_MODEL, on_chunk=None):
    """
    Send messages to OpenRouter and return the full response text.
    If on_chunk is provided, stream chunks to it for live updates.
    """
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "stream": on_chunk is not None,
    }).encode("utf-8")

    req = urllib.request.Request(OPENROUTER_URL, data=payload, headers={
        "Authorization": f"Bearer {API_KEY}",
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


# ── Markdown → HTML helper ───────────────────────────────────────────────────
import re as _re

def _md_to_html(md, fg="#fff"):
    """Lightweight markdown to styled HTML."""
    html = md.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # Code blocks
    def _code_block(m):
        code = m.group(2).strip()
        return (
            '<pre style="background:#1a1a2e; border-radius:6px; padding:10px; '
            'font-family:Consolas,monospace; font-size:12px; color:#e0e0e0; '
            f'margin:6px 0; overflow-x:auto;">{code}</pre>'
        )
    html = _re.sub(r'```(\w*)\n(.*?)```', _code_block, html, flags=_re.DOTALL)
    # Inline code
    html = _re.sub(r'`([^`]+)`',
        r'<code style="background:#1a1a2e; padding:2px 5px; border-radius:3px; '
        r'font-family:Consolas,monospace; font-size:12px; color:#e0e0e0;">\1</code>', html)
    # Bold
    html = _re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', html)
    # Italic
    html = _re.sub(r'\*(.+?)\*', r'<i>\1</i>', html)
    # Bullet lists
    html = _re.sub(r'^[-•] (.+)$', r'<div style="margin-left:12px;">• \1</div>', html, flags=_re.MULTILINE)
    # Numbered lists
    html = _re.sub(r'^(\d+)\. (.+)$', r'<div style="margin-left:12px;">\1. \2</div>', html, flags=_re.MULTILINE)
    # Headers
    html = _re.sub(r'^### (.+)$', r'<div style="font-size:14px; font-weight:bold; margin:6px 0;">\1</div>', html, flags=_re.MULTILINE)
    html = _re.sub(r'^## (.+)$', r'<div style="font-size:15px; font-weight:bold; margin:8px 0;">\1</div>', html, flags=_re.MULTILINE)
    html = _re.sub(r'^# (.+)$', r'<div style="font-size:16px; font-weight:bold; margin:10px 0;">\1</div>', html, flags=_re.MULTILINE)
    # Line breaks
    html = html.replace("\n", "<br>")
    return (
        f'<div style="font-family:Segoe UI,SF Pro Text,Helvetica Neue,Arial,sans-serif;'
        f' font-size:13px; color:{fg}; line-height:1.5;">{html}</div>'
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
        lay.addWidget(self.body)

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
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)

    def append_text(self, md):
        """Live-append for streaming."""
        self.body.setText(_md_to_html(md, self._theme.get('text_bright', '#fff')))


# ── Send Button (Custom Painted) ──────────────────────────────────────────────
class SendButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(28, 28)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Build theme-ready colors
        # Try to get theme from parent (AiPanel)
        theme = {}
        if hasattr(self.parent(), 'theme'):
            theme = self.parent().theme
        elif hasattr(self.parent().parent(), 'theme'):
            theme = self.parent().parent().theme

        # Hover state
        if self.underMouse() and self.isEnabled():
            painter.setBrush(QBrush(QColor(theme.get('bg_hover', '#3a3a3c'))))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(self.rect().adjusted(2, 2, -2, -2), 6, 6)

        # Arrow color
        if not self.isEnabled():
            color = QColor(theme.get('text_disabled', '#636366'))
        elif self.underMouse():
            color = QColor(theme.get('accent', '#58a6ff')) # Use accent on hover
        else:
            color = QColor(theme.get('text_bright', '#ffffff'))

        painter.setPen(QPen(color, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.setBrush(QBrush(color))

        # Draw a sleek right-pointing arrow (triangle-ish)
        # Center of button is (14, 14)
        poly = QPolygon([
            QPoint(10, 8),   # Top left
            QPoint(20, 14),  # Mid right (tip)
            QPoint(10, 20),  # Bottom left
        ])
        painter.drawPolygon(poly)


# ── Main Panel ────────────────────────────────────────────────────────────────
class AiPanel(QWidget):
    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.history = [{"role": "system", "content": SYSTEM_PROMPT}]
        self._streaming_text = ""
        self._current_bubble = None
        self._sig = _Signals()
        self._sig.chunk.connect(self._on_chunk)
        self._sig.done.connect(self._on_done)
        self._sig.error.connect(self._on_error)
        self._sig.status.connect(self._on_status)
        self._sig.credits.connect(self._on_credits)
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

        # ── Input area (Cursor-style) ────────────────────────────────────
        input_frame = QFrame()
        input_frame.setStyleSheet(
            f"background: {t.get('bg_darkest', '#000')};"
            f" border-top: 1px solid {t.get('border', '#3a3a3c')};"
        )
        input_root = QVBoxLayout(input_frame)
        input_root.setContentsMargins(8, 6, 8, 4)
        input_root.setSpacing(4)

        # Input row: text box + send icon
        input_row = QHBoxLayout()
        input_row.setContentsMargins(0, 0, 0, 0)
        input_row.setSpacing(0)

        self.input_edit = QTextEdit()
        self.input_edit.setPlaceholderText("Ask anything…")
        self.input_edit.setMaximumHeight(72)
        self.input_edit.setMinimumHeight(36)
        self.input_edit.setStyleSheet(
            f"background: {t.get('bg_medium', '#1c1c1e')};"
            f" color: {t.get('text_bright', '#fff')};"
            f" border: 1px solid {t.get('border', '#3a3a3c')};"
            " border-radius: 8px; padding: 8px 10px;"
            " font-family: 'Segoe UI', 'SF Pro Text', sans-serif;"
            " font-size: 13px;"
        )
        input_row.addWidget(self.input_edit, 1)

        # Send button — custom painted arrow
        self.send_btn = SendButton()
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.clicked.connect(self._on_send)
        input_row.addWidget(self.send_btn)

        input_root.addLayout(input_row)

        # Bottom bar: model selector + credits + status
        bottom_bar = QHBoxLayout()
        bottom_bar.setContentsMargins(2, 0, 2, 0)
        bottom_bar.setSpacing(8)

        # Model selector
        self.model_combo = QComboBox()
        for display_name, model_id in MODELS:
            self.model_combo.addItem(display_name, model_id)
        self.model_combo.setFixedHeight(22)
        self.model_combo.setStyleSheet(
            "background: transparent;"
            f" color: {t.get('text_secondary', '#aeaeb2')};"
            " border: none; padding: 0 4px;"
            " font-family: 'Segoe UI', sans-serif; font-size: 11px;"
        )
        bottom_bar.addWidget(self.model_combo)

        # Credits label (fetched from OpenRouter)
        self.credits_label = QLabel("…")
        self.credits_label.setStyleSheet(
            f"color: {t.get('text_disabled', '#636366')};"
            " font-size: 10px; font-family: 'Segoe UI', sans-serif;"
            " background: transparent;"
        )
        bottom_bar.addWidget(self.credits_label)

        bottom_bar.addStretch()

        # Status
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet(
            f"color: {t.get('text_disabled', '#636366')};"
            " font-size: 10px; font-family: 'Segoe UI', sans-serif;"
            " background: transparent;"
        )
        bottom_bar.addWidget(self.status_label)

        input_root.addLayout(bottom_bar)
        root.addWidget(input_frame)

        # Fetch credits on startup
        threading.Thread(target=self._fetch_credits, daemon=True).start()

    # ── Greeting ──────────────────────────────────────────────────────────
    def _greet(self):
        self._add_bubble(
            "Hi! I'm **Lutervyn AI**. Ask me anything about your code.", False
        )

    # ── Chat logic ────────────────────────────────────────────────────────
    def _add_bubble(self, text, is_user):
        self.chat_lay.takeAt(self.chat_lay.count() - 1)  # remove stretch
        b = ChatBubble(text, is_user, self.theme, self.chat_box)
        self.chat_lay.addWidget(b)
        self.chat_lay.addStretch()
        QTimer.singleShot(50, self._scroll_down)
        return b

    def _on_send(self):
        text = self.input_edit.toPlainText().strip()
        if not text:
            return
        self.input_edit.clear()
        self._add_bubble(text, True)

        self.history.append({"role": "user", "content": text})
        self._streaming_text = ""
        self._current_bubble = self._add_bubble("…", False)

        self.send_btn.setEnabled(False)
        self.status_label.setText("Thinking…")

        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        """Runs on a background thread."""
        try:
            model = self.model_combo.currentData() or DEFAULT_MODEL
            def on_chunk(ch):
                self._sig.chunk.emit(ch)

            full, usage = chat_completion(list(self.history), model=model, on_chunk=on_chunk)
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
        self.send_btn.setEnabled(True)
        self.status_label.setText("Ready")
        total = prompt_tokens + completion_tokens
        if total > 0:
            self.status_label.setText(f"Ready ({total:,} tokens)")
        self._scroll_down()

    def _on_error(self, msg):
        if self._current_bubble:
            self._current_bubble.append_text(f"**Error:** {msg}")
        self.send_btn.setEnabled(True)
        self.status_label.setText("Error — try again")

    def _on_status(self, msg):
        self.status_label.setText(msg)

    def _scroll_down(self):
        QTimer.singleShot(50, lambda: self.scroll.verticalScrollBar().setValue(
            self.scroll.verticalScrollBar().maximum()
        ))

    def _fetch_credits(self):
        """Background thread to fetch credits."""
        try:
            req = urllib.request.Request("https://openrouter.ai/api/v1/key", headers={
                "Authorization": f"Bearer {API_KEY}",
            })
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                # OpenRouter returns { "data": { "limit_remaining": 1.23, ... } }
                d = data.get("data", {})
                limit = d.get("limit_remaining")
                if limit is None:
                    txt = "Unlimited"
                else:
                    txt = f"${float(limit):.3f}"
                self._sig.credits.emit(txt)
        except Exception:
            self._sig.credits.emit("Error")

    def _on_credits(self, txt):
        self.credits_label.setText(txt)
