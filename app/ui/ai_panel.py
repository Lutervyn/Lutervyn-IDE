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
    QSizePolicy, QComboBox, QDialog, QMenu
)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer, QObject, QPoint, QPointF, QEvent, QByteArray
from PyQt6.QtGui import QFont, QColor, QPainter, QPolygon, QPolygonF, QPen, QBrush, QPixmap, QIcon, QClipboard
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
    "You are Lutervyn AI, a highly intelligent coding agent. You act as an expert pair programmer.\n\n"
    "REASONING PROTOCOL:\n"
    "- ALWAYS BEGIN EVERY RESPONSE WITH A `<thought>` BLOCK.\n"
    "- In the `<thought>` block, analyze the query and explain your plan.\n\n"
    "TOOL PROTOCOL:\n"
    "- [READ_FILE: path] - Read a file. ALWAYS read before editing.\n"
    "- [WRITE_FILE: path] - Apply edits to a file using SEARCH/REPLACE blocks.\n"
    "- [RUN_TERMINAL: command] - Execute a command in the terminal. Use for building, testing, or running.\n"
    "- [PROJECT_SUMMARY] - Get a high-level map of the project (files + important classes/functions).\n"
    "- [DRAFT_INSERT: path, line, code] - Propose a code insertion at a specific line (Ctrl+K style).\n\n"
    "EDITING WORKFLOW (AIDER-STYLE):\n"
    "When using [WRITE_FILE], provide one or more SEARCH/REPLACE blocks. This is much more reliable than rewriting the whole file.\n\n"
    "Format:\n"
    "[WRITE_FILE: path]\n"
    "<<<<<<< SEARCH\n"
    "(exact existing code to find)\n"
    "=======\n"
    "(new code to replace it with)\n"
    ">>>>>>> REPLACE\n"
    "[/WRITE_FILE]\n\n"
    "RULES:\n"
    "1. **SEARCH block must match EXACTLY** (whitespace, indentation, comments).\n"
    "2. If creating a NEW file, leave the SEARCH block empty.\n"
    "3. Use multiple blocks for changes in different parts of the same file.\n"
    "4. For long changes, you can use `...` to elide unchanged middle parts in SEARCH and REPLACE blocks.\n"
    "5. ALWAYS [READ_FILE] first. NEVER edit a file you haven't seen.\n\n"
    "CONTEXT AWARENESS:\n"
    "- I will provide you with the 'ACTIVE EDITOR' file. Prioritize reasoning about this file.\n"
    "- If you need to edit other files, ensure you [READ_FILE] them first."
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
    full_thought = [] # Accumulate thought content
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
                full_thought.append(reasoning)
                if on_thought: on_thought(reasoning)
                
            text = delta.get("content", "")
            if text:
                full.append(text)
                if on_chunk: on_chunk(text)
        except (json.JSONDecodeError, KeyError, IndexError):
            continue
    # Post-process for reasoning.
    # CRITICAL: We look for thoughts that came in both the dedicated reasoning 
    # field AND those that might have been streamed into the content field.
    final_text = "".join(full)
    thought_str = "".join(full_thought).strip()
    
    # If the model sent reasoning inside <thought> tags in the main content:
    # We must extract it and move it to the official reasoning block.
    if "<thought>" in final_text.lower():
        import re
        match = re.search(r"<thought>(.*?)(?:</thought>|$)", final_text, re.DOTALL | re.IGNORECASE)
        if match:
            extracted = match.group(1).strip()
            # If we don't already have thoughts via the dedicated field, use this.
            if len(extracted) > len(thought_str):
                thought_str = extracted
            # Remove the thinking from the displayed text to prevent "formality" duplicates.
            final_text = re.sub(r"<thought>.*?(?:</thought>|$)", "", final_text, flags=re.DOTALL | re.IGNORECASE).strip()

    if thought_str and "<thought>" not in final_text.lower():
         # Normalize it back into the response for historical saving/restoring
         final_text = f"<thought>\n{thought_str}\n</thought>\n\n{final_text}"
            
    return final_text.strip(), {} 


# ── Signal bridge (thread → GUI) ─────────────────────────────────────────────
class _Signals(QObject):
    chunk    = pyqtSignal(str)
    thought  = pyqtSignal(str)
    done     = pyqtSignal(str, int, int)  # full_text, prompt_tokens, completion_tokens
    error    = pyqtSignal(str)
    status   = pyqtSignal(str)
    system   = pyqtSignal(str) 
    tool     = pyqtSignal(str, str, str) # type (READ/WRITE), path, status (START/DONE/ERROR)
    diff     = pyqtSignal(str, str, str) # path, original_content, new_content
    file_clicked = pyqtSignal(str)       # path
    credits  = pyqtSignal(str)
    models_loaded = pyqtSignal(list)
    clear_chat = pyqtSignal()
    open_inline_diff = pyqtSignal(str, str, str) # path, original, updated
    clear_streaming = pyqtSignal()
    run_terminal = pyqtSignal(str) # Command to run
    draft_insert = pyqtSignal(str, int, str) # path, line, code


# ── Tool Action Widget (Cursor Style) ─────────────────────────────────────────
class ToolActionWidget(QFrame):
    clicked = pyqtSignal(str)
    open_diff_requested = pyqtSignal(str) # path

    def __init__(self, action_type, path, parent=None):
        super().__init__(parent)
        self.path = path
        self.setStyleSheet("""
            QFrame {
                background: transparent; border: none; margin: 1px 0;
            }
        """)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 2, 4, 2)
        lay.setSpacing(6)

        # Subtle bullet/icon
        icon_lbl = QLabel()
        kind = "READ"
        if "WRITE" in action_type: kind = "WRITE"
        elif "CREATE" in action_type: kind = "FOLDER"
        icon_lbl.setPixmap(create_tool_icon(kind))
        lay.addWidget(icon_lbl)

        # Action Type (Analyzed / Edited / Created)
        self.action_lbl = QLabel("Working...")
        self.action_lbl.setStyleSheet("color: #8e8e93; font-size: 11px; font-weight: 500;")
        lay.addWidget(self.action_lbl)

        # File Link
        self.path_btn = QPushButton(os.path.basename(path))
        self.path_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.path_btn.setStyleSheet("""
            QPushButton { 
                background: transparent; border: none; color: #3794ff; 
                font-size: 11px; text-align: left; padding: 0;
            }
            QPushButton:hover { text-decoration: underline; }
        """)
        self.path_btn.clicked.connect(lambda: self.clicked.emit(self.path))
        lay.addWidget(self.path_btn)

        # Stats (+8 -5)
        self.stats_lbl = QLabel("")
        self.stats_lbl.setStyleSheet("font-size: 10px; margin-left: 4px;")
        lay.addWidget(self.stats_lbl)

        lay.addStretch()

        # Open Diff Action
        self.diff_btn = QPushButton("Open diff")
        self.diff_btn.hide()
        self.diff_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.diff_btn.setStyleSheet("""
            QPushButton {
                background: transparent; border: none; color: #666; font-size: 10px;
            }
            QPushButton:hover { color: #aaa; }
        """)
        self.diff_btn.clicked.connect(lambda: self.open_diff_requested.emit(self.path))
        lay.addWidget(self.diff_btn)

    def set_status(self, status, is_error=False):
        status = status.strip()
        
        if is_error:
            self.action_lbl.setText("Error")
            self.action_lbl.setStyleSheet("color: #f14c4c; font-size: 11px;")
            self.stats_lbl.setText(status)
            return

        if "ANALYZED" in status.upper() or "DONE" in status.upper() and self.action_lbl.text() == "Working...":
            self.action_lbl.setText("Analyzed")
            self.stats_lbl.setText("")
        elif "EDITED" in status.upper():
            self.action_lbl.setText("Edited")
            # Extract stats if present e.g. "Edited +8 -5"
            parts = status.split(" ")
            if len(parts) > 1:
                stats = " ".join(parts[1:])
                # Style + as green, - as red
                styled_stats = stats.replace("+", "<span style='color:#6a9955;'>+</span>").replace("-", "<span style='color:#f14c4c;'>-</span>")
                self.stats_lbl.setTextFormat(Qt.TextFormat.RichText)
                self.stats_lbl.setText(styled_stats)
            self.diff_btn.show()
        elif "CREATED" in status.upper():
            self.action_lbl.setText("Created")
        elif "START" in status.upper() or "WORKING" in status.upper():
            self.action_lbl.setText("Working...")
        else:
            self.action_lbl.setText(status)

# ── Consolidated Diff Review ──────────────────────────────────────────────────
class MultiDiffReviewWidget(QFrame):
    accepted = pyqtSignal(list) # list of paths
    discarded = pyqtSignal(list) # list of paths
    file_clicked = pyqtSignal(str)

    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.files = [] # list of (path, original, updated)
        self.setStyleSheet("""
            QFrame {
                background: #1e1e1e; border: 1px solid #333; border-radius: 6px; margin: 4px 0;
            }
        """)
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(0, 0, 0, 0)
        self.lay.setSpacing(0)

        # Header
        hdr = QFrame()
        hdr.setFixedHeight(28)
        hdr.setStyleSheet("background: #252526; border-top-left-radius: 6px; border-top-right-radius: 6px;")
        hlay = QHBoxLayout(hdr)
        hlay.setContentsMargins(10, 0, 10, 0)
        self.title = QLabel("Review Edits")
        self.title.setStyleSheet("color: #ccc; font-weight: bold; font-size: 11px;")
        hlay.addWidget(self.title)
        hlay.addStretch()
        self.lay.addWidget(hdr)

        # File List Area
        self.file_container = QFrame()
        self.flay = QVBoxLayout(self.file_container)
        self.flay.setContentsMargins(4, 4, 4, 4)
        self.flay.setSpacing(2)
        self.lay.addWidget(self.file_container)

        # Actions
        actions = QFrame()
        actions.setFixedHeight(32)
        actions.setStyleSheet("background: #252526; border-bottom-left-radius: 6px; border-bottom-right-radius: 6px;")
        alay = QHBoxLayout(actions)
        alay.setContentsMargins(10, 0, 10, 0)
        
        self.discard_btn = QPushButton("Discard All")
        self.discard_btn.setStyleSheet("""
            QPushButton { background: #3e3e3e; color: #ccc; border-radius: 4px; padding: 2px 10px; font-size: 10px; }
            QPushButton:hover { background: #4e4e4e; color: white; }
        """)
        self.discard_btn.clicked.connect(lambda: self.discarded.emit([f[0] for f in self.files]))
        
        self.accept_btn = QPushButton("Accept All")
        self.accept_btn.setStyleSheet("""
            QPushButton { background: #0e639c; color: white; border-radius: 4px; padding: 2px 10px; font-size: 10px; font-weight: bold; }
            QPushButton:hover { background: #1177bb; }
        """)
        self.accept_btn.clicked.connect(lambda: self.accepted.emit([f[0] for f in self.files]))
        
        alay.addStretch()
        alay.addWidget(self.discard_btn)
        alay.addWidget(self.accept_btn)
        self.lay.addWidget(actions)

    def add_diff(self, path, original, updated):
        self.files.append((path, original, updated))
        self.title.setText(f"Review Edits ({len(self.files)} files)")
        
        # Add a small row for each file
        row = QFrame()
        row.setStyleSheet("background: #2d2d2d; border-radius: 4px;")
        rlay = QHBoxLayout(row)
        rlay.setContentsMargins(8, 4, 8, 4)
        
        flbl = QPushButton(os.path.basename(path))
        flbl.setStyleSheet("background: transparent; color: #3794ff; font-size: 11px; text-align: left;")
        flbl.clicked.connect(lambda: self.file_clicked.emit(path))
        rlay.addWidget(flbl, 1)
        
        # Show a tiny diff preview or icon
        stat = QLabel(f"+{len(updated.splitlines())} lines")
        stat.setStyleSheet("color: #6a9955; font-size: 10px;")
        rlay.addWidget(stat)
        
        self.flay.addWidget(row)

        dv = DiffViewWidget(path, original, updated, self)
        dv.setStyleSheet("border: none; margin: 0; background: transparent;")
        # Hide internal actions of DiffViewWidget if we consolidate
        if hasattr(dv, 'accept_btn'): 
            dv.accept_btn.hide()
            dv.discard_btn.hide()
            # Shrink header if it exists and has a fixed height
            header_frame = dv.findChild(QFrame)
            if header_frame:
                header_frame.setFixedHeight(24) # Shrink header
        self.flay.addWidget(dv)

# ── Diff View / Review Widget ──────────────────────────────────────────────────
class DiffViewWidget(QFrame):
    accepted = pyqtSignal(str) # path
    discarded = pyqtSignal(str) # path

    def __init__(self, path, original, updated, parent=None):
        super().__init__(parent)
        self.path = path
        self.original = original
        self.updated = updated
        
        self.setStyleSheet("""
            QFrame {
                background: #1e1e1e; border: 1px solid #333; border-radius: 6px; margin: 8px 0;
            }
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Header
        hdr = QFrame()
        hdr.setFixedHeight(24)
        hdr.setStyleSheet("background: #2d2d2d; border-top-left-radius: 6px; border-top-right-radius: 6px;")
        hlay = QHBoxLayout(hdr)
        hlay.setContentsMargins(8, 0, 8, 0)
        
        title = QLabel(f"Review: {os.path.basename(path)}")
        title.setStyleSheet("color: #aaa; font-weight: bold; font-size: 10px;")
        hlay.addWidget(title)
        hlay.addStretch()
        lay.addWidget(hdr)

        # Diff Content
        import difflib
        diff = difflib.unified_diff(original.splitlines(), updated.splitlines(), lineterm='')
        diff_text = "\n".join([line for line in diff if not line.startswith(('---', '+++', '@@'))])
        
        self.browser = QTextBrowser()
        self.browser.setReadOnly(True)
        self.browser.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff) # Let parent scroll?
        self.browser.setStyleSheet("""
            QTextBrowser { 
                background: transparent; border: none; padding: 10px;
                font-family: 'Consolas', monospace; font-size: 12px;
            }
        """)
        
        # Colorize diff
        html = []
        for line in diff_text.splitlines():
            if line.startswith('+'): html.append(f'<div style="background:#1e3a1e; color:#d4d4d4;">{_html.escape(line)}</div>')
            elif line.startswith('-'): html.append(f'<div style="background:#3e1e1e; color:#d4d4d4;">{_html.escape(line)}</div>')
            else: html.append(f'<div>{_html.escape(line)}</div>')
        
        self.browser.setHtml(f'<div style="white-space: pre;">{"".join(html)}</div>')
        # Simple height estimate
        self.browser.setFixedHeight(min(300, max(60, len(html) * 18 + 20)))
        lay.addWidget(self.browser)

        # Actions
        actions = QFrame()
        actions.setStyleSheet("background: #252526; border-bottom-left-radius: 6px; border-bottom-right-radius: 6px;")
        alay = QHBoxLayout(actions)
        alay.setContentsMargins(8, 4, 8, 4)
        
        self.discard_btn = QPushButton("Discard")
        self.discard_btn.setStyleSheet("""
            QPushButton { background: #3e3e3e; color: #ccc; border-radius: 4px; padding: 2px 8px; font-size: 10px; }
            QPushButton:hover { background: #4e4e4e; color: white; }
        """)
        self.discard_btn.clicked.connect(lambda: self.discarded.emit(path))
        
        self.accept_btn = QPushButton("Accept")
        self.accept_btn.setStyleSheet("""
            QPushButton { background: #0e639c; color: white; border-radius: 4px; padding: 2px 8px; font-size: 10px; font-weight: bold; }
            QPushButton:hover { background: #1177bb; }
        """)
        self.accept_btn.clicked.connect(lambda: self.accepted.emit(path))
        
        alay.addStretch()
        alay.addWidget(self.discard_btn)
        alay.addWidget(self.accept_btn)
        lay.addWidget(actions)

def _md_to_html(md, fg="#fff"):
    """Simplified markdown to styled HTML (code handled by CodeBlockWidget)."""
    html_final = _html.escape(md)
    # Inline code
    html_final = re.sub(r'`([^`]+)`',
        r'<code style="background:rgba(255,255,255,0.06); padding:2px 5px; border:1px solid rgba(255,255,255,0.05); '
        r'border-radius:4px; font-family:\'Cascadia Code\',\'Consolas\',monospace; font-size:11.5px; color:#e0e0e0;">\1</code>', html_final)
    # Bold
    html_final = re.sub(r'\*\*(.+?)\*\*', r'<b style="color:#ffffff; font-weight:700;">\1</b>', html_final)
    # Italic
    html_final = re.sub(r'\*(.+?)\*', r'<i style="color:#cccccc;">\1</i>', html_final)
    # Lists
    html_final = re.sub(r'^[-•] (.+)$', r'<div style="margin-left:14px; margin-top:2px;">• \1</div>', html_final, flags=re.MULTILINE)
    # Lines
    html_final = html_final.replace("\n", "<br>")
    return (
        f'<div style="font-family:\'Inter\',\'Segoe UI\',sans-serif; font-size:13px; color:{fg}; '
        f'line-height:1.6; white-space: pre-wrap; word-wrap: break-word; letter-spacing: 0.1px;">{html_final}</div>'
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
        header.setFixedHeight(34)
        header.setStyleSheet("""
            background-color: rgba(45, 45, 48, 0.8); 
            border-top-left-radius: 8px; 
            border-top-right-radius: 8px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        """)
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
            QLabel {
                color: #d4d4d4; 
                font-family: 'Cascadia Code', 'Consolas', 'Courier New', monospace; 
                font-size: 12px; 
                padding: 16px; 
                line-height: 1.5;
                background-color: rgba(30, 30, 32, 0.4);
                border-bottom-left-radius: 8px;
                border-bottom-right-radius: 8px;
            }
        """)
        lay.addWidget(self.content)

    def _copy_code(self):
        QApplication.clipboard().setText(self._code)
        self.copy_btn.setText("Copied!")
        QTimer.singleShot(2000, lambda: self.copy_btn.setText("Copy"))

    def get_code(self):
        return self._code

    def set_code(self, code, lang=""):
        self._code = code
        self.content.setText(code)
        # Update header lang if needed
        lang_lbl = self.findChild(QLabel) # The first one is lang_lbl
        if lang_lbl:
            lang_lbl.setText(lang.upper() or "CODE")


# ── Chat bubble ──────────────────────────────────────────────────────────────
class ChatBubble(QFrame):
    def __init__(self, text, is_user, theme, parent=None):
        super().__init__(parent)
        self._theme = theme
        self._is_user = is_user
        self._widgets = [] # Track added widgets for clearing
        self._full_md = "" # Track raw markdown including tags
        
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
        self.thought_box.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.02); 
                border-left: 2px solid rgba(255,255,255,0.1); 
                margin: 8px 4px; 
                border-radius: 0px;
                border-top-right-radius: 8px; 
                border-bottom-right-radius: 8px;
            }
        """)
        tlay = QVBoxLayout(self.thought_box)
        tlay.setContentsMargins(0, 0, 0, 0)
        tlay.setSpacing(0)

        # Thought Header
        self.thought_header = QPushButton("  🧠 Thought")
        self.thought_header.setCheckable(True)
        self.thought_header.setChecked(False)
        self.thought_header.setStyleSheet("""
            QPushButton {
                background: transparent; border: none; text-align: left;
                color: #8e8e93; font-size: 11px; font-weight: 500;
                padding: 4px 6px;
            }
            QPushButton:hover { color: #ccc; }
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
            self.setStyleSheet(f"""
                ChatBubble {{
                    background: rgba(255, 255, 255, 0.05);
                    border: 1px solid rgba(255, 255, 255, 0.03);
                    border-radius: 12px; 
                    margin: 4px 12px;
                }}
            """)
        else:
            self.setStyleSheet("""
                ChatBubble {
                    background: transparent;
                    border: none;
                    margin: 2px 12px;
                }
            """)
        
        # Add a subtle fade-in animation
        from PyQt6.QtCore import QPropertyAnimation, QEasingCurve
        from PyQt6.QtWidgets import QGraphicsOpacityEffect
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)
        self._anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._anim.setDuration(300)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.start()

        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)

        # Initial text rendering (now that all components are ready)
        if text and text != "…":
            self.set_content(text)

    def set_content(self, text, images=None):
        """Render text and images with incremental updates."""
        parts = self._parse_markdown(text)
        
        # Incremental update: if parts match mostly, only touch the last one
        if len(parts) == len(self._widgets):
            for i, (ptype, content, lang) in enumerate(parts):
                w = self._widgets[i]
                if ptype == "text" and isinstance(w, QLabel):
                    # Check if the text actually changed (avoid re-setting the same HTML)
                    new_html = _md_to_html(content, self._theme.get('text_bright', '#fff'))
                    if w.text() != new_html:
                        w.setText(new_html)
                elif ptype == "code" and isinstance(w, CodeBlockWidget):
                    if w.get_code() != content:
                        w.set_code(content, lang)
        else:
            # Full rebuild (only when part structure changes)
            for w in self._widgets:
                w.deleteLater()
            self._widgets.clear()
            
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
        """Live-append and extract reasoning from various formats."""
        self._full_md = md
        
        display_md = self._full_md
        thought_content = ""
        
        # 1. Standard <thought> tags (Multi-turn friendly)
        import re
        all_thoughts = re.findall(r"<thought>(.*?)(?:</thought>|$)", self._full_md, re.DOTALL | re.IGNORECASE)
        if all_thoughts:
            thought_content = "\n\n---\n\n".join(t.strip() for t in all_thoughts if t.strip())
            # Clean display_md by removing ALL thought blocks
            display_md = re.sub(r"<thought>.*?(?:</thought>|$)", "", self._full_md, flags=re.DOTALL | re.IGNORECASE).strip()
        
        # 2. Fallback: Catch code blocks with reasoning-related languages
        # This catches ```thought, ```reasoning, ```thinking
        code_thought_match = re.search(r"```(?:thought|reasoning|thinking)\n?(.*?)(?:```|$)", display_md, re.DOTALL | re.IGNORECASE)
        if code_thought_match:
            if not thought_content:
                thought_content = code_thought_match.group(1).strip()
            display_md = re.sub(r"```(?:thought|reasoning|thinking).*?(?:```|$)", "", display_md, flags=re.DOTALL | re.IGNORECASE).strip()
            
        if thought_content or "<thought" in self._full_md.lower():
            self.append_thought(thought_content)
        
        # Hide Tool Tags in display (they are handled by signals)
        display_md = re.sub(r'\[(?:WRITE_FILE|WRITE|READ_FILE|READ|CREATE_FOLDER)[^\]]*\].*?\[/(?:WRITE_FILE|WRITE)\]', '🛠️ *Applying changes...*', display_md, flags=re.DOTALL | re.IGNORECASE)
        display_md = re.sub(r'\[(?:WRITE_FILE|WRITE|READ_FILE|READ|CREATE_FOLDER)[^\]]*\]', '🛠️ *Tool call...*', display_md, flags=re.IGNORECASE)
        
        self.set_content(display_md) 
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
        if not md.strip():
            # Show "Thinking..." state if empty but we just started
            self.thought_box.show()
            self.thought_header.setText("  🧠 Thinking...")
            return
            
        import time
        if not self.thought_start_time:
            self.thought_start_time = time.time()
            self.thought_box.show()
            
        self.thought_body.setText(md)
        
        # Update header with timer or final status
        elapsed = int(time.time() - self.thought_start_time)
        has_closed = "</thought>" in self._full_md or "```" in self._full_md and (self._full_md.count("```") % 2 == 0)
        
        if has_closed:
             self.thought_header.setText(f"  🧠 Thought ({elapsed}s)")
        else:
             self.thought_header.setText(f"  🧠 Thinking... ({elapsed}s)")
        
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
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#7b61ff"))
    p.drawEllipse(2, 2, 12, 12)
    p.setBrush(QColor("white"))
    pts = [QPointF(8, 4), QPointF(9, 7), QPointF(12, 8), QPointF(9, 9), QPointF(8, 12), QPointF(7, 9), QPointF(4, 8), QPointF(7, 7)]
    p.drawPolygon(QPolygonF(pts))
    p.end()
    return QIcon(pix)

def create_vision_icon():
    """Create a camera/eye icon for vision models."""
    pix = QPixmap(16, 16)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor("#888"), 1.2))
    p.drawEllipse(3, 4, 10, 8)
    p.drawEllipse(6, 6, 4, 4)
    p.end()
    return QIcon(pix)

def create_history_icon():
    """Create a minimalist 'clock/history' icon."""
    pix = QPixmap(16, 16)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor("#888"), 1.2))
    p.drawEllipse(2, 2, 12, 12)
    p.drawLine(8, 8, 8, 4)
    p.drawLine(8, 8, 11, 8)
    p.end()
    return QIcon(pix)

def create_tool_icon(kind):
    """Create minimalist professional icons for tools (READ/WRITE/FOLDER)."""
    pix = QPixmap(14, 14)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor("#888"), 1))
    
    if kind == "READ": # Document icon
        p.drawRect(3, 2, 8, 10)
        p.drawLine(5, 5, 9, 5)
        p.drawLine(5, 7, 9, 7)
        p.drawLine(5, 9, 7, 9)
    elif kind == "WRITE": # Pencil/Edit icon (Minimal pen)
        p.drawLine(4, 10, 10, 4)
        p.drawLine(10, 4, 11, 3)
        p.setPen(QPen(QColor("#3794ff"), 1.5))
        p.drawPoint(4, 10)
    elif kind == "FOLDER": # Folder icon
        p.drawPolygon(QPolygon([QPoint(2, 4), QPoint(6, 4), QPoint(7, 6), QPoint(12, 6), QPoint(12, 11), QPoint(2, 11)]))

    p.end()
    return pix


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


# ── History Manager ───────────────────────────────────────────────────────────
class HistoryManager:
    """Manages saving and loading of chat sessions to disk."""
    def __init__(self):
        self.history_dir = os.path.join(os.path.expanduser("~"), ".lutervyn", "chat_history")
        os.makedirs(self.history_dir, exist_ok=True)

    def save_session(self, session_id, history):
        """Save a session to a JSON file."""
        if not history or len(history) <= 1: return # Don't save empty/system-only
        path = os.path.join(self.history_dir, f"{session_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)

    def load_session(self, session_id):
        """Load a session from disk."""
        path = os.path.join(self.history_dir, f"{session_id}.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def list_sessions(self):
        """Return a list of (session_id, title, timestamp)."""
        sessions = []
        for fname in os.listdir(self.history_dir):
            if fname.endswith(".json"):
                sid = fname[:-5]
                path = os.path.join(self.history_dir, fname)
                mtime = os.path.getmtime(path)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        hist = json.load(f)
                        # Find first user message for title
                        title = "Untitled Chat"
                        for msg in hist:
                            if msg["role"] == "user":
                                content = msg["content"]
                                if isinstance(content, list):
                                    for p in content:
                                        if isinstance(p, dict) and p.get("type") == "text":
                                            title = p["text"][:40] + "..."
                                            break
                                else:
                                    title = content[:40] + "..."
                                break
                        sessions.append({"id": sid, "title": title, "time": mtime})
                except: continue
        return sorted(sessions, key=lambda x: x["time"], reverse=True)


# ── Main Panel ────────────────────────────────────────────────────────────────
class AiPanel(QWidget):
    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.history = [{"role": "system", "content": SYSTEM_PROMPT}]
        self._streaming_text = ""
        self._streaming_thought = ""
        self._current_bubble = None
        self._attached_images = [] # Store base64 data strings
        self._attached_files = []  # Store absolute paths
        self._abort_requested = False
        self._history_manager = HistoryManager()
        self._current_session_id = str(int(time.time()))
        self._sig = _Signals()
        self._sig.chunk.connect(self._on_chunk)
        self._sig.thought.connect(self._on_thought_token)
        self._sig.done.connect(self._on_done)
        self._sig.error.connect(self._on_error)
        self._sig.status.connect(self._on_status)
        self._sig.system.connect(self._on_system_msg)
        self._sig.tool.connect(self._on_tool_update)
        self._sig.run_terminal.connect(self._on_run_terminal_requested) # Placeholder for internal use
        self._sig_run_terminal = self._sig.run_terminal # Export for MainWindow
        self._sig_draft_insert = self._sig.draft_insert # Export for MainWindow
        self._terminal_buffer = [] # Store last 50 lines of terminal output
        self._sig.diff.connect(self._on_diff_review)
        self._sig.credits.connect(self._on_credits)
        self._sig.models_loaded.connect(self._on_models_loaded)
        self._sig.clear_streaming.connect(self._on_clear_streaming)
        self._recent_files = [] # Track last 10 visited files
        self._last_active_file = None
        self.setMinimumWidth(180) # Allow shrinking
        self._init_ui()
        QTimer.singleShot(500, self._greet)

    def _apply_search_replace(self, file_path, file_content, diff_content):
        """
        Applies Aider-style SEARCH/REPLACE blocks.
        If no SEARCH blocks found, returns diff_content as-is (full rewrite).
        """
        import re
        # Match <<<<<<< SEARCH (content) ======= (content) >>>>>>> REPLACE
        blocks = re.findall(r"<<<<<<< SEARCH\n?([\s\S]*?)\n?=======\n?([\s\S]*?)\n?>>>>>>> REPLACE", diff_content)
        
        if not blocks:
            return diff_content
            
        new_content = file_content
        for search, replace in blocks:
            # 1. Exact match
            if search in new_content:
                new_content = new_content.replace(search, replace, 1)
            else:
                # 2. Fuzzy match: Ignore trailing whitespace on each line
                search_lines = search.splitlines()
                content_lines = new_content.splitlines()
                match_found = False
                for i in range(len(content_lines) - len(search_lines) + 1):
                    window = content_lines[i : i + len(search_lines)]
                    if all(s.rstrip() == c.rstrip() for s, c in zip(search_lines, window)):
                        # Matches! Replace this window with the new content
                        prefix = content_lines[:i]
                        suffix = content_lines[i + len(search_lines) :]
                        new_content = "\n".join(prefix + [replace] + suffix)
                        match_found = True
                        break
                
                if not match_found:
                    print(f"[AiPanel] Warning: Search block failed to match in {file_path}")
        
        return new_content

    def _on_clear_streaming(self):
        """Reset streaming buffer and thought timer for a fresh turn."""
        self._streaming_text = ""
        self._streaming_thought = ""
        if self._current_bubble:
            self._current_bubble.thought_start_time = 0

    # ── UI setup ──────────────────────────────────────────────────────────
    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        t = self.theme  # shorthand

        # Header
        header = QFrame()
        header.setFixedHeight(45) # Taller for premium feel
        header.setStyleSheet(f"""
            QFrame {{
                background: rgba(30,30,32, 0.7); 
                backdrop-filter: blur(10px); 
                border-bottom: 1px solid rgba(255,255,255,0.05);
            }}
        """)
        hdr_lay = QHBoxLayout(header)
        hdr_lay.setContentsMargins(15, 0, 10, 0)
        
        self.title_lbl = QLabel("LUTERVYN AI")
        self.title_lbl.setStyleSheet("""
            color: #ffffff; 
            font-weight: 800; 
            font-size: 11px; 
            letter-spacing: 1px;
            font-family: 'Inter', 'Segoe UI', sans-serif;
        """)
        hdr_lay.addWidget(self.title_lbl)
        hdr_lay.addStretch()

        # History Button (Custom Icon)
        self.history_btn = QPushButton()
        self.history_btn.setFixedSize(24, 24)
        self.history_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.history_btn.setIcon(create_history_icon())
        self.history_btn.setStyleSheet("""
            QPushButton { background: transparent; border: none; padding: 2px; }
            QPushButton:hover { background: #3e3e42; border-radius: 4px; }
        """)
        self.history_btn.clicked.connect(self._toggle_history)
        hdr_lay.addWidget(self.history_btn)
        
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setFixedSize(45, 22)
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.setStyleSheet("""
            QPushButton { background: transparent; color: #888; border: none; font-size: 10px; font-weight: bold; }
            QPushButton:hover { color: white; background: #3e3e42; border-radius: 4px; }
        """)
        self.clear_btn.clicked.connect(self._clear_conversation)
        hdr_lay.addWidget(self.clear_btn)
        root.addWidget(header)

        # History Sidebar (Embedded)
        self.history_sidebar = QFrame()
        self.history_sidebar.setFixedWidth(200)
        self.history_sidebar.setStyleSheet(f"background: {t.get('sidebar_bg', '#252526')}; border-right: 1px solid #333;")
        self.history_sidebar.hide()
        
        # We need a horizontal layout for [Sidebar | Chat]
        content_box = QWidget()
        content_lay = QHBoxLayout(content_box)
        content_lay.setContentsMargins(0,0,0,0)
        content_lay.setSpacing(0)
        
        # --- Sidebar UI ---
        slay = QVBoxLayout(self.history_sidebar)
        slay.setContentsMargins(10, 15, 10, 15)
        
        stitle = QLabel("CHAT HISTORY")
        stitle.setStyleSheet("""
            color: #888; 
            font-size: 10px; 
            font-weight: 800; 
            letter-spacing: 0.5px;
            margin-bottom: 8px;
            font-family: 'Inter', sans-serif;
        """)
        slay.addWidget(stitle)
        
        self.history_list = QScrollArea()
        self.history_list.setWidgetResizable(True)
        self.history_list.setFrameShape(QFrame.Shape.NoFrame)
        self.history_list.setStyleSheet("background: transparent;")
        
        self.history_content = QWidget()
        self.history_vlay = QVBoxLayout(self.history_content)
        self.history_vlay.setContentsMargins(0, 0, 0, 0)
        self.history_vlay.setSpacing(2)
        self.history_vlay.addStretch()
        
        self.history_list.setWidget(self.history_content)
        slay.addWidget(self.history_list)
        
        content_lay.addWidget(self.history_sidebar)
        
        # Main Chat Scroll Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet(f"background: {t.get('bg_darkest', '#1e1e1e')};")
        
        self.chat_box = QWidget()
        self.chat_box.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.MinimumExpanding)
        self.chat_lay = QVBoxLayout(self.chat_box)
        self.chat_lay.setContentsMargins(10, 5, 10, 5)
        self.chat_lay.setSpacing(10)
        self.chat_lay.addStretch()
        self.scroll.setWidget(self.chat_box)
        
        content_lay.addWidget(self.scroll, 1)
        root.addWidget(content_box, 1)

        # ── Consolidated Input Container (Cursor-style) ───────────────────
        input_frame = QFrame()
        input_frame.setStyleSheet(f"background: #1e1e1e; border-top: 1px solid rgba(255,255,255,0.03);")
        input_root = QVBoxLayout(input_frame)
        input_root.setContentsMargins(12, 10, 12, 12) # More generous margins

        self.input_container = QFrame()
        self.input_container.setObjectName("inputContainer")
        self.input_container.setStyleSheet("""
            QFrame#inputContainer {
                background-color: rgba(45, 45, 48, 0.4); 
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 14px;
            }
            QFrame#inputContainer:focus-within {
                border: 1px solid rgba(0, 122, 255, 0.5);
                background-color: rgba(45, 45, 48, 0.5);
            }
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
            QTextEdit {
                background: transparent;
                color: #ffffff;
                border: none;
                font-family: 'Inter', 'Segoe UI', sans-serif;
                font-size: 13px;
                padding: 12px 14px 4px 14px;
                line-height: 1.5;
            }
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
        self.model_combo.setStyleSheet("""
            QComboBox {
                background: rgba(255, 255, 255, 0.05);
                color: #aeaeb2;
                border: 1px solid rgba(255,255,255,0.03);
                border-radius: 6px;
                padding: 0 15px 0 8px;
                font-family: 'Inter', 'Segoe UI', sans-serif; 
                font-size: 11px; 
                font-weight: 500;
            }
            QComboBox:hover {
                background: rgba(255, 255, 255, 0.1);
                color: #ffffff;
                border: 1px solid rgba(255,255,255,0.1);
            }
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

    def _clear_conversation(self):
        """Reset history and UI."""
        self.history = [{"role": "system", "content": SYSTEM_PROMPT}]
        # Remove all widgets from chat_lay except the stretch
        while self.chat_lay.count() > 1:
            item = self.chat_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._greet()
        self._current_session_id = str(int(time.time()))

    def _load_session(self, sid):
        """Restore a session from history."""
        hist = self._history_manager.load_session(sid)
        if hist:
            self._current_session_id = sid
            self.history = hist
            # Rebuild UI
            while self.chat_lay.count() > 1:
                item = self.chat_lay.takeAt(0)
                if item.widget(): item.widget().deleteLater()
            
            for msg in hist:
                if msg["role"] == "system": continue
                content = msg["content"]
                # Handle multimodal content (list of parts)
                if isinstance(content, list):
                    text = ""
                    for part in content:
                        if isinstance(part, dict) and part.get("type") == "text":
                            text = part["text"]
                            break
                    content = text or "(media message)"
                self._add_bubble(content, msg["role"] == "user")
            
            QTimer.singleShot(100, self._scroll_down)
            # Close history sidebar after selection
            self.history_sidebar.hide()

    def _resolve_path(self, path):
        """
        Smart path resolution. If path doesn't exist, search the workspace
        for a file with the same basename. (Ported from Aider logic)
        """
        root_dir = os.getcwd()
        full_path = os.path.normpath(os.path.join(root_dir, path))
        if os.path.exists(full_path):
            return full_path
            
        # If not found, search workspace for basename match
        basename = os.path.basename(path)
        for root, dirs, files in os.walk(root_dir):
            if '.git' in dirs: dirs.remove('.git')
            if '.gemini' in dirs: dirs.remove('.gemini')
            if basename in files:
                return os.path.join(root, basename)
        
        return full_path # Fallback to original guess

    def _greet(self):
        if not API_KEY:
            self._add_bubble(
                "⚠️ **API Key Missing!**\nPlease create an `api_key.txt` file in the project root and paste your OpenRouter key there to start using the AI.", False
            )
        else:
            self._add_bubble(
                "Hi! I'm **Lutervyn AI**. Ask me anything about your code.", False
            )

    def _get_active_file(self):
        """Returns the path of the currently active file in the editor."""
        win = self.window()
        if hasattr(win, "editor_tabs"):
            f = win.editor_tabs.get_current_file_path()
            if f and f != self._last_active_file:
                self._last_active_file = f
                if f in self._recent_files: self._recent_files.remove(f)
                self._recent_files.insert(0, f)
                if len(self._recent_files) > 10: self._recent_files.pop()
            return f
        return None

    def _get_open_files(self):
        """Returns a list of all unique open file paths."""
        win = self.window()
        if hasattr(win, "editor_tabs"):
            paths = []
            for i in range(win.editor_tabs.tabs.count()):
                widget = win.editor_tabs.tabs.widget(i)
                path = None
                if hasattr(widget, "editor") and hasattr(widget.editor, "file_path"):
                    path = widget.editor.file_path
                elif hasattr(widget, "file_path"):
                    path = widget.file_path
                if path and path not in paths:
                    paths.append(path)
            return paths
        return []

    def _scan_workspace_list(self):
        """Returns a concise list of files in the workspace (ignoring noise)."""
        root_dir = os.getcwd()
        file_list = []
        for root, dirs, files in os.walk(root_dir):
            # Ignore noise
            for d in [".git", "__pycache__", ".gemini", "node_modules", ".venv", "venv", "build", "dist"]:
                if d in dirs: dirs.remove(d)
            
            for f in files:
                rel = os.path.relpath(os.path.join(root, f), root_dir)
                file_list.append(rel)
                if len(file_list) > 300: # Cap to avoid context overflow
                    file_list.append("... (and more)")
                    return file_list
        return file_list

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
        self._streaming_thought = ""
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
            
            # Phase 1: Context Injection (Awareness Layer)
            root_dir = os.getcwd()
            file_list = self._scan_workspace_list()
            active_file = self._get_active_file()
            open_files = self._get_open_files()
            
            context_sections = []
            context_sections.append(f"WORKSPACE FILES:\n- " + "\n- ".join(file_list))
            
            if open_files:
                rel_open = []
                for f in open_files:
                    try: rel_open.append(os.path.relpath(f, root_dir))
                    except: rel_open.append(f)
                context_sections.append(f"OPEN TABS:\n- " + "\n- ".join(rel_open))

            if active_file:
                try:
                    rel_active = os.path.relpath(active_file, root_dir)
                    context_sections.append(f"ACTIVE EDITOR: {rel_active} (Focused)")
                except:
                    context_sections.append(f"ACTIVE EDITOR: {active_file}")
            
            if self._recent_files:
                rel_recent = []
                for f in self._recent_files:
                    if f == active_file: continue
                    try: rel_recent.append(os.path.relpath(f, root_dir))
                    except: rel_recent.append(f)
                if rel_recent:
                    context_sections.append(f"RECENTLY VISITED:\n- " + "\n- ".join(rel_recent))

            context_msg = f"{SYSTEM_PROMPT}\n\n" + "\n\n".join(context_sections)
            
            if self._terminal_buffer:
                context_msg += "\n\nRECENT TERMINAL OUTPUT:\n" + "\n".join(self._terminal_buffer)

            # Fresh copy of history starting with injected system prompt
            current_history = list(self.history)
            if current_history:
                current_history[0]["content"] = context_msg

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
                    elif any(word in last_text.lower() for word in ["logic", "why", "code", "create", "read", "tell", "explain", "analyze", "how", "what"]):
                        active_model = "anthropic/claude-3-5-sonnet-20241022"
                    else:
                        active_model = "google/gemini-2.0-flash-001"

                self._streaming_text_raw = ""  # Reset raw buffer for this turn
                self._sig.status.emit("🧠 Thinking..." if not is_agent else "🕵️ Agent working...")
                
                def on_chunk(ch): 
                    self._sig.chunk.emit(ch)
                    # Real-time <thought> extraction from content stream
                    # Some models (Gemini) embed <thought> directly in content
                    self._streaming_text_raw = getattr(self, '_streaming_text_raw', '') + ch
                    if '<thought>' in self._streaming_text_raw.lower() and '</thought>' not in self._streaming_text_raw.lower():
                        # We're inside a thought block - extract and forward to thought UI
                        import re
                        m = re.search(r'<thought>(.*?)$', self._streaming_text_raw, re.DOTALL | re.IGNORECASE)
                        if m:
                            self._sig.thought.emit(m.group(1))
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
                # Pre-process: Strip code fences that wrap tool tags
                # Some models wrap [WRITE_FILE]...[/WRITE_FILE] inside ```...```
                tool_text = full
                tool_text = re.sub(r'```(?:\w*)\n(\[(?:WRITE_FILE|WRITE|READ_FILE|READ|CREATE_FOLDER)\s*[:\s])', r'\1', tool_text)
                tool_text = re.sub(r'\[/(?:WRITE_FILE|WRITE)\]\s*\n?```', '[/WRITE_FILE]', tool_text)
                
                # 1. CREATE_FOLDER
                folder_matches = re.finditer(r"\[CREATE_FOLDER\s*[:\s]*([^\]]+)\]", tool_text, re.IGNORECASE)
                for m in folder_matches:
                    path = m.group(1).strip()
                    self._sig.tool.emit("CREATE", path, "START")
                    try:
                        os.makedirs(os.path.join(root_dir, path), exist_ok=True)
                        self._sig.tool.emit("CREATE", path, "DONE")
                    except Exception as e:
                        self._sig.tool.emit("CREATE", path, f"Error: {e}")

                # 2. WRITE_FILE
                write_matches = list(re.finditer(r"\[(?:WRITE_FILE|WRITE)\s*[:\s]*([^\]]+)\](.*?)\n?\[/(?:WRITE_FILE|WRITE)\]", tool_text, re.DOTALL | re.IGNORECASE))

                if write_matches:
                    for m in write_matches:
                        path = m.group(1).strip()
                        content = m.group(2)
                        # Strip leading newline and common prefixes models add
                        content = content.strip()
                        # Remove 'content:' prefix if present
                        if content.lower().startswith('content:'):
                            content = content[8:].strip()
                        # Remove wrapping code fences if present
                        if content.startswith('```'):
                            lines = content.split('\n')
                            if lines[0].startswith('```'):
                                lines = lines[1:]  # Remove opening fence
                            if lines and lines[-1].strip() == '```':
                                lines = lines[:-1]  # Remove closing fence
                            content = '\n'.join(lines)
                        self._sig.tool.emit("WRITE", path, "START")
                        try:
                            full_path = self._resolve_path(path)
                            os.makedirs(os.path.dirname(full_path), exist_ok=True)
                            
                            original_content = ""
                            if os.path.exists(full_path):
                                import shutil
                                shutil.copy2(full_path, full_path + ".agent.bak")
                                with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                                    original_content = f.read()

                            with open(full_path, "w", encoding="utf-8") as f:
                                # Apply search/replace if applicable
                                final_content = self._apply_search_replace(path, original_content, content)
                                f.write(final_content)
                                content = final_content # Update content for diff calculation
                            
                            # Calculate stats for the chip
                            import difflib
                            diff = list(difflib.unified_diff(original_content.splitlines(), content.splitlines()))
                            added = sum(1 for line in diff if line.startswith('+') and not line.startswith('+++'))
                            removed = sum(1 for line in diff if line.startswith('-') and not line.startswith('---'))
                            
                            self._sig.tool.emit("WRITE", path, f"EDITED +{added} -{removed}")
                            self._sig.diff.emit(full_path, original_content, content)
                        except Exception as e:
                            self._sig.tool.emit("WRITE", path, f"Error: {e}")

                # 3. RUN_TERMINAL
                run_matches = list(re.finditer(r"\[RUN_TERMINAL\s*[:\s]*([^\]]+)\]", tool_text, re.IGNORECASE))
                for m in run_matches:
                    cmd = m.group(1).strip()
                    self._sig.tool.emit("RUN", cmd, "DONE")
                    self._sig.run_terminal.emit(cmd)

                # 4. PROJECT_SUMMARY (Triggers turn)
                if "[PROJECT_SUMMARY]" in tool_text.upper():
                    summary = []
                    for f in self._scan_workspace_list()[:20]: # Limit to first 20 for brevity
                        fpath = os.path.join(os.getcwd(), f)
                        syms = self._extract_symbols(fpath)
                        if syms:
                            summary.append(f"{f}: {', '.join(syms)}")
                        else:
                            summary.append(f"{f}")
                    
                    self._sig.chunk.emit(" 🗺️ summarizing...")
                    current_history.append({"role": "user", "content": "PROJECT STRUCTURE & SYMBOLS:\n" + "\n".join(summary)})
                    continue

                # 5. DRAFT_INSERT
                draft_matches = list(re.finditer(r"\[DRAFT_INSERT\s*[:\s]*([^,]+),\s*(\d+),\s*(.*?)\]", tool_text, re.DOTALL | re.IGNORECASE))
                for m in draft_matches:
                    path = m.group(1).strip()
                    line = int(m.group(2))
                    code = m.group(3).strip()
                    self._sig.tool.emit("DRAFT", path, f"AT LINE {line}")
                    self._sig.draft_insert.emit(path, line, code)

                # 6. READ_FILE (Triggers another turn)
                read_matches = list(re.finditer(r"\[(?:READ_FILE|READ)\s*[:\s]*([^\]]+)\]", tool_text, re.IGNORECASE))
                if read_matches:
                    read_results = []
                    for m in read_matches:
                        path = m.group(1).strip()
                        self._sig.tool.emit("READ", path, "START")
                        try:
                            fpath = self._resolve_path(path)
                            # Large file protection
                            if os.path.exists(fpath):
                                fsize = os.path.getsize(fpath) / 1024 # KB
                                if fsize > 1024: # > 1MB
                                    read_results.append(f"Error reading {path}: File too large ({int(fsize)}KB). Suggest reading specific parts.")
                                    self._sig.tool.emit("READ", path, "TOO LARGE")
                                    continue

                            with open(fpath, "r", encoding="utf-8") as f:
                                # Truncate if extreme (e.g. > 10000 lines)
                                lines = f.readlines()
                                if len(lines) > 5000:
                                    content = "".join(lines[:5000]) + "\n\n[... TRUNCATED DUE TO LENGTH ...]\n"
                                else:
                                    content = "".join(lines)
                            
                            read_results.append(f"--- CONTENT OF {path} ---\n{content}\n--- END {path} ---")
                            self._sig.tool.emit("READ", path, "ANALYZED")
                        except Exception as e:
                            read_results.append(f"Error reading {path}: {e}")
                            self._sig.tool.emit("READ", path, f"Error: {e}")
                    
                    self._sig.chunk.emit(" …") # Visual indicator of auto-turn
                    current_history.append({"role": "user", "content": "\n\n".join(read_results)})
                    continue 

                # No more tools found that require immediate turnaround
                break

            # Finalize
            self.history = current_history
            self._history_manager.save_session(self._current_session_id, self.history)
            self._sig.done.emit(full, cumulative_usage["prompt_tokens"], cumulative_usage["completion_tokens"])
            
        except Exception as e:
            self._sig.error.emit(str(e))

    # ── Slots (main thread) ───────────────────────────────────────────────
    def _on_terminal_output(self, text):
        """Buffer terminal output for AI context."""
        if not text: return
        self._terminal_buffer.extend(text.splitlines())
        # Keep last 50 lines
        if len(self._terminal_buffer) > 50:
            self._terminal_buffer = self._terminal_buffer[-50:]

    def _on_run_terminal_requested(self, command):
        """Execute a command suggested by the AI (called internally if needed)."""
        # This is primarily for MainWindow to connect to, but we can log it
        print(f"[AiPanel] Run Terminal requested: {command}")

    def _on_chunk(self, text):
        self._streaming_text += text
        if self._current_bubble:
            self._current_bubble.append_text(self._streaming_text)
        self._scroll_down()

    def _on_thought_token(self, thought):
        self._streaming_thought += thought
        if self._current_bubble:
            self._current_bubble.append_thought(self._streaming_thought)
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
        if self._current_bubble and ("thinking" in msg.lower() or "working" in msg.lower()):
            self._current_bubble.append_thought("") # Trigger the "Thinking..." pulse

    def _on_system_msg(self, msg):
        """Append a system message (e.g. tool execution) to the chat."""
        self._add_bubble(f"🛠️ **System**: {msg}", False)

    def _on_tool_update(self, action, path, status):
        """Render/Update a ToolActionWidget in the chat."""
        # Check if we can update the existing one
        last_item = self.chat_lay.itemAt(self.chat_lay.count() - 2)
        if last_item and isinstance(last_item.widget(), ToolActionWidget) and last_item.widget().path == path:
            last_item.widget().set_status(status, "Error" in status)
            return

        self.chat_lay.takeAt(self.chat_lay.count() - 1)
        w = ToolActionWidget(action, path, self.chat_box)
        w.clicked.connect(self._sig.file_clicked.emit) # Forward
        w.open_diff_requested.connect(self._on_open_diff_requested)
        w.set_status("Working..." if status == "START" else status, "Error" in status)
        self.chat_lay.addWidget(w)
        self.chat_lay.addStretch()
        self._scroll_down()

    def _on_open_diff_requested(self, path):
        """Find the MultiDiffReviewWidget that contains this path and scroll to it."""
        for i in range(self.chat_lay.count() - 1, -1, -1):
            item = self.chat_lay.itemAt(i)
            if item and item.widget():
                w = item.widget()
                if isinstance(w, MultiDiffReviewWidget):
                    if any(p[0] == path for p in w.files):
                        self.scroll.ensureWidgetVisible(w)
                        return

    def _toggle_history(self):
        """Toggle the slide-out history sidebar."""
        visible = self.history_sidebar.isVisible()
        self.history_sidebar.setVisible(not visible)
        if not visible:
            self._update_history_ui()

    def _update_history_ui(self):
        """Rebuild the history list from disk."""
        # Clear current list
        while self.history_vlay.count() > 1:
            item = self.history_vlay.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            
        sessions = self._history_manager.list_sessions()
        for s in sessions[:20]:
            btn = QPushButton(s['title'])
            btn.setFixedHeight(30)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            # Shorten title
            if len(s['title']) > 28:
                btn.setText(s['title'][:25] + "...")
            
            btn.setStyleSheet(f"""
                QPushButton {{ 
                    background: transparent; border: none; color: #aaa; 
                    text-align: left; padding: 0 8px; font-size: 10px; border-radius: 4px;
                }}
                QPushButton:hover {{ background: #37373d; color: white; }}
                {"QPushButton { background: #37373d; color: white; }" if s['id'] == self._current_session_id else ""}
            """)
            btn.clicked.connect(lambda checked, sid=s['id']: self._load_session(sid))
            self.history_vlay.insertWidget(self.history_vlay.count()-1, btn)

    def _show_history(self):
        """Deprecated."""
        pass

    def _on_diff_review(self, path, original, updated):
        """Render a MultiDiffReviewWidget and also trigger inline diff if possible."""
        # 1. Existing Sidebar Review
        last_item = self.chat_lay.itemAt(self.chat_lay.count() - 2)
        if last_item and isinstance(last_item.widget(), MultiDiffReviewWidget):
            last_item.widget().add_diff(path, original, updated)
        else:
            self.chat_lay.takeAt(self.chat_lay.count() - 1)
            w = MultiDiffReviewWidget(self.theme, self.chat_box)
            w.file_clicked.connect(self._on_file_clicked)
            w.accepted.connect(self._apply_all_diffs)
            w.discarded.connect(self._discard_all_diffs)
            w.add_diff(path, original, updated)
            self.chat_lay.addWidget(w)
            self.chat_lay.addStretch()
            self._scroll_down()

        # 2. Trigger Inline Editor Diff (The Cursor Way)
        self._sig.open_inline_diff.emit(path, original, updated)

    def _on_file_clicked(self, path):
        # We can emit to global signals if we had access to the main IDE, 
        # but for now we'll simulate opening by a system message or just logging.
        self._sig.system.emit(f"Opening `{os.path.basename(path)}`...")
        print(f"DEBUG: Opening file {path}")

    def _apply_all_diffs(self, paths):
        sender = self.sender()
        if sender:
            idx = self.chat_lay.indexOf(sender)
            if idx != -1:
                self.chat_lay.takeAt(idx)
                sender.deleteLater()
                lbl = QLabel(f"✅ Edits applied to {len(paths)} files")
                lbl.setStyleSheet("color: #4ec9b0; font-size: 11px; margin: 4px;")
                self.chat_lay.insertWidget(idx, lbl)

    def _discard_all_diffs(self, paths):
        for path in paths:
            self._discard_diff(path) # Use existing single-file discard logic
        
        sender = self.sender()
        if sender:
            idx = self.chat_lay.indexOf(sender)
            if idx != -1:
                self.chat_lay.takeAt(idx)
                sender.deleteLater()
                lbl = QLabel(f"❌ Edits discarded for {len(paths)} files")
                lbl.setStyleSheet("color: #f14c4c; font-size: 11px; margin: 4px;")
                self.chat_lay.insertWidget(idx, lbl)

    def _apply_diff(self, path):
        # The file is actually already written in our current WRITE_FILE implementation.
        # So "Accept" just removes the widget and confirms.
        # In a more advanced version, we'd write to a temp file first.
        # For now, we'll just show success.
        sender = self.sender()
        if sender:
            # Replace widget with a success message
            idx = self.chat_lay.indexOf(sender)
            if idx != -1:
                self.chat_lay.takeAt(idx)
                sender.deleteLater()
                lbl = QLabel(f"✅ Edits applied to `{os.path.basename(path)}`")
                lbl.setStyleSheet("color: #4ec9b0; font-size: 12px; margin: 5px;")
                self.chat_lay.insertWidget(idx, lbl)

    def _discard_diff(self, path):
        # Restore from backup
        bak_path = path + ".agent.bak"
        if os.path.exists(bak_path):
            try:
                import shutil
                shutil.copy2(bak_path, path)
                os.remove(bak_path)
                
                sender = self.sender()
                if sender:
                    idx = self.chat_lay.indexOf(sender)
                    if idx != -1:
                        self.chat_lay.takeAt(idx)
                        sender.deleteLater()
                        lbl = QLabel(f"❌ Edits discarded for `{os.path.basename(path)}`")
                        lbl.setStyleSheet("color: #f14c4c; font-size: 12px; margin: 5px;")
                        self.chat_lay.insertWidget(idx, lbl)
            except Exception as e:
                self._add_bubble(f"Error restoring backup: {e}", False)

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
        
        auto_icon = create_auto_icon()
        vision_icon = create_vision_icon()
        
        # Always add Auto first
        self.model_combo.addItem(auto_icon, "Auto (Smart)", "auto")
        
        if not models:
            for name, mid in MODELS:
                # Add vision icon to known vision models if fallback
                if any(v in mid.lower() for v in ["gpt-4o", "claude-3-5", "gemini-1.5"]):
                    self.model_combo.addItem(vision_icon, name, mid)
                else:
                    self.model_combo.addItem(name, mid)
            self.model_combo.setCurrentIndex(0)
            return

        for display, mid, price, vision, free in models:
            clean_display = display.replace("✦ ", "").replace("✨ ", "").replace(" (Free)", "")
            if free:
                 clean_display += " (Free)"
                 
            if vision:
                self.model_combo.addItem(vision_icon, clean_display, mid)
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
