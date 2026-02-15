import os
import re
import json
import html as html_module
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QScrollArea, 
                             QTreeWidget, QTreeWidgetItem, QHeaderView,
                             QHBoxLayout, QPushButton, QSlider,
                             QFrame, QSplitter, QTextBrowser)
from PyQt6.QtCore import Qt, QSize, QUrl, pyqtSignal, QEvent, QTimer
from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor, QFont, QWheelEvent, QIcon
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtSvgWidgets import QSvgWidget


class BasePreviewWidget(QWidget):
    """Base class for all media preview widgets."""
    def __init__(self, file_path: str, theme: dict, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.theme = theme
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.setStyleSheet(f"background-color: {theme['sidebar_bg']};")

class ZoomableScrollArea(QScrollArea):
    """Custom scroll area that catches Ctrl+Wheel for zooming."""
    zoom_requested = pyqtSignal(int) # -1 for out, 1 for in

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background: transparent;")

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_requested.emit(1)
            elif delta < 0:
                self.zoom_requested.emit(-1)
            event.accept()
        else:
            super().wheelEvent(event)

class ImagePreviewWidget(BasePreviewWidget):
    """Static image preview with Ctrl+Wheel zoom and fit-to-view."""
    def __init__(self, file_path: str, theme: dict, parent=None):
        super().__init__(file_path, theme, parent)
        self.zoom_factor = 1.0
        
        self.scroll = ZoomableScrollArea()
        self.scroll.zoom_requested.connect(self._on_zoom)
        
        self.img_label = QLabel()
        self.img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pixmap = QPixmap(file_path)
        
        if self.pixmap.isNull():
            self.img_label.setText("Could not load image.")
            self.img_label.setStyleSheet(f"color: {theme['text_secondary']};")
        else:
            self.img_label.setPixmap(self.pixmap)
            # Initial fit logic will be triggered on Resize
            
        self.scroll.setWidget(self.img_label)
        self.layout.addWidget(self.scroll)
        
        # Info bar
        self.info_bar = QWidget()
        self.info_bar.setFixedHeight(24)
        self.info_bar.setStyleSheet(f"background: {theme['sidebar_bg']}; border-top: 1px solid {theme['border']};")
        info_layout = QHBoxLayout(self.info_bar)
        info_layout.setContentsMargins(10, 0, 10, 0)
        
        self.size_lbl = QLabel(f"{self.pixmap.width()}x{self.pixmap.height()} | {os.path.getsize(file_path)//1024} KB")
        self.size_lbl.setStyleSheet(f"color: {theme['text_secondary']}; font-size: 11px;")
        info_layout.addWidget(self.size_lbl)
        
        self.zoom_lbl = QLabel("100%")
        self.zoom_lbl.setStyleSheet(f"color: {theme['text_secondary']}; font-size: 11px;")
        info_layout.addStretch()
        info_layout.addWidget(self.zoom_lbl)
        
        self.layout.addWidget(self.info_bar)
        self._initial_fit = True

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._initial_fit and not self.pixmap.isNull():
            self._fit_to_view()
            self._initial_fit = False

    def _fit_to_view(self):
        if self.pixmap.isNull(): return
        viewport_size = self.scroll.viewport().size()
        if viewport_size.width() <= 0 or viewport_size.height() <= 0: return
        
        w_ratio = viewport_size.width() / self.pixmap.width()
        h_ratio = viewport_size.height() / self.pixmap.height()
        self.zoom_factor = min(w_ratio, h_ratio, 1.0) # Start at fit or 100%
        self._update_display()

    def _on_zoom(self, direction):
        if direction > 0:
            self.zoom_factor *= 1.2
        else:
            self.zoom_factor /= 1.2
        self.zoom_factor = max(0.1, min(self.zoom_factor, 10.0))
        self._update_display()

    def _update_display(self):
        if self.pixmap.isNull(): return
        new_w = int(self.pixmap.width() * self.zoom_factor)
        new_h = int(self.pixmap.height() * self.zoom_factor)
        
        scaled = self.pixmap.scaled(new_w, new_h, 
                                   Qt.AspectRatioMode.KeepAspectRatio, 
                                   Qt.TransformationMode.SmoothTransformation)
        self.img_label.setPixmap(scaled)
        self.zoom_lbl.setText(f"{int(self.zoom_factor * 100)}%")

class SVGPreviewWidget(BasePreviewWidget):
    """SVG preview with Ctrl+Wheel zoom."""
    def __init__(self, file_path: str, theme: dict, parent=None):
        super().__init__(file_path, theme, parent)
        self.zoom_factor = 1.0
        
        self.scroll = ZoomableScrollArea()
        self.scroll.zoom_requested.connect(self._on_zoom)
        
        self.svg_widget = QSvgWidget(file_path)
        self.scroll.setWidget(self.svg_widget)
        self.layout.addWidget(self.scroll)
        
        # Initial size
        self.base_size = self.svg_widget.sizeHint()
        self._initial_fit = True

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._initial_fit:
            viewport_size = self.scroll.viewport().size()
            w_ratio = viewport_size.width() / self.base_size.width()
            h_ratio = viewport_size.height() / self.base_size.height()
            self.zoom_factor = min(w_ratio, h_ratio, 1.0)
            self._update_display()
            self._initial_fit = False

    def _on_zoom(self, direction):
        if direction > 0: self.zoom_factor *= 1.2
        else: self.zoom_factor /= 1.2
        self.zoom_factor = max(0.1, min(self.zoom_factor, 10.0))
        self._update_display()

    def _update_display(self):
        new_w = int(self.base_size.width() * self.zoom_factor)
        new_h = int(self.base_size.height() * self.zoom_factor)
        self.svg_widget.setFixedSize(new_w, new_h)

class VideoPreviewWidget(BasePreviewWidget):
    """Video player with VS Code-style controls."""
    def __init__(self, file_path: str, theme: dict, parent=None):
        super().__init__(file_path, theme, parent)
        self.media_player = QMediaPlayer()
        self.video_widget = QVideoWidget()
        self.audio_output = QAudioOutput()
        self.media_player.setVideoOutput(self.video_widget)
        self.media_player.setAudioOutput(self.audio_output)
        
        # Black background for video area
        self.video_container = QFrame()
        self.video_container.setStyleSheet("background-color: black;")
        v_layout = QVBoxLayout(self.video_container)
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.addWidget(self.video_widget)
        self.layout.addWidget(self.video_container)
        
        # Control bar
        self.controls = QFrame()
        self.controls.setFixedHeight(45)
        self.controls.setObjectName("videoControls")
        self.controls.setStyleSheet(f"""
            QFrame#videoControls {{
                background-color: {theme['sidebar_bg']};
                border-top: 1px solid {theme['border']};
            }}
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 4px;
                padding: 4px;
            }}
            QPushButton:hover {{
                background-color: {theme['bg_hover']};
            }}
            QLabel {{
                color: {theme['text_secondary']};
                font-size: 11px;
                font-family: 'Segoe UI', sans-serif;
            }}
            QSlider::groove:horizontal {{
                border: 1px solid {theme['border']};
                height: 4px;
                background: {theme['bg_hover']};
                margin: 2px 0;
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {theme['accent'] if 'accent' in theme else '#007ACC'};
                border: none;
                width: 12px;
                height: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }}
            QSlider::sub-page:horizontal {{
                background: {theme['accent'] if 'accent' in theme else '#007ACC'};
                border-radius: 2px;
            }}
        """)
        
        ctrl_layout = QHBoxLayout(self.controls)
        ctrl_layout.setContentsMargins(15, 0, 15, 0)
        ctrl_layout.setSpacing(10)
        
        # Paths for icons
        self.icons_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets", "icons")
        
        # Play button
        self.play_btn = QPushButton()
        self.play_btn.setFixedSize(30, 30)
        self._update_play_icon(False)
        self.play_btn.clicked.connect(self._toggle_playback)
        ctrl_layout.addWidget(self.play_btn)
        
        # Time label
        self.time_label = QLabel("0:00 / 0:00")
        ctrl_layout.addWidget(self.time_label)
        
        # Seek slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.media_player.positionChanged.connect(self._on_position_changed)
        self.media_player.durationChanged.connect(self._on_duration_changed)
        self.slider.sliderMoved.connect(self.media_player.setPosition)
        ctrl_layout.addWidget(self.slider, 1) # Take most space
        
        # Volume button
        self.volume_btn = QPushButton()
        self.volume_btn.setFixedSize(26, 26)
        self.volume_btn.setIcon(QIcon(os.path.join(self.icons_path, "video_volume.svg")))
        self.volume_btn.clicked.connect(self._toggle_mute)
        ctrl_layout.addWidget(self.volume_btn)
        
        # Volume slider
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setFixedWidth(80)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(100)
        self.volume_slider.valueChanged.connect(lambda v: self.audio_output.setVolume(v / 100.0))
        ctrl_layout.addWidget(self.volume_slider)
        
        self.layout.addWidget(self.controls)
        
        # Initialization
        self.media_player.setSource(QUrl.fromLocalFile(file_path))
        self.media_player.playbackStateChanged.connect(self._on_state_changed)
        self.media_player.play()

    def _update_play_icon(self, playing):
        icon_name = "video_pause.svg" if playing else "video_play.svg"
        icon_path = os.path.join(self.icons_path, icon_name)
        if os.path.exists(icon_path):
            from PyQt6.QtGui import QIcon
            self.play_btn.setIcon(QIcon(icon_path))
            self.play_btn.setIconSize(self.play_btn.size() - QSize(10, 10))

    def _on_state_changed(self, state):
        self._update_play_icon(state == QMediaPlayer.PlaybackState.PlayingState)

    def _toggle_playback(self):
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()

    def _toggle_mute(self):
        is_muted = self.audio_output.isMuted()
        self.audio_output.setMuted(not is_muted)
        icon_name = "video_mute.svg" if not is_muted else "video_volume.svg"
        icon_path = os.path.join(self.icons_path, icon_name)
        if os.path.exists(icon_path):
            from PyQt6.QtGui import QIcon
            self.volume_btn.setIcon(QIcon(icon_path))

    def _on_position_changed(self, position):
        self.slider.setValue(position)
        self._update_time_label()

    def _on_duration_changed(self, duration):
        self.slider.setMaximum(duration)
        self._update_time_label()

    def _update_time_label(self):
        pos = self.media_player.position() // 1000
        dur = self.media_player.duration() // 1000
        
        p_min, p_sec = divmod(pos, 60)
        d_min, d_sec = divmod(dur, 60)
        
        self.time_label.setText(f"{p_min}:{p_sec:02d} / {d_min}:{d_sec:02d}")

    def closeEvent(self, event):
        """Release media player and source to unlock the file."""
        self.media_player.stop()
        self.media_player.setSource(QUrl())
        super().closeEvent(event)

class JSONPreviewWidget(BasePreviewWidget):
    """Structural tree view for JSON data."""
    def __init__(self, file_path: str, theme: dict, parent=None):
        super().__init__(file_path, theme, parent)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Key", "Value", "Type"])
        self.tree.header().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.tree.setAlternatingRowColors(True)
        self.tree.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {theme['sidebar_bg']};
                color: {theme['sidebar_fg']};
                border: none;
                alternate-background-color: #252526;
            }}
            QHeaderView::section {{
                background-color: {theme['sidebar_bg']};
                color: {theme['text_secondary']};
                border: 1px solid {theme['border']};
                padding: 4px;
            }}
        """)
        self.layout.addWidget(self.tree)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self._populate(data, self.tree.invisibleRootItem())
        except Exception as e:
            err = QTreeWidgetItem(["Error", str(e), "Exception"])
            self.tree.addTopLevelItem(err)

    def _populate(self, data, parent_item):
        if isinstance(data, dict):
            for key, value in data.items():
                item = QTreeWidgetItem([str(key), "", "Object" if isinstance(value, dict) else "Array" if isinstance(value, list) else "Value"])
                parent_item.addChild(item)
                self._populate(value, item)
        elif isinstance(data, list):
            for i, value in enumerate(data):
                item = QTreeWidgetItem([f"[{i}]", "", "Object" if isinstance(value, dict) else "Array" if isinstance(value, list) else "Value"])
                parent_item.addChild(item)
                self._populate(value, item)
        else:
            parent_item.setText(1, str(data))
            parent_item.setText(2, type(data).__name__)


def _markdown_to_html(md_text: str, base_path: str = "") -> str:
    """
    Convert Markdown text to HTML.
    Supports: headings, bold, italic, strikethrough, inline code, code blocks,
    links, images, blockquotes, horizontal rules, ordered/unordered lists, tables.
    """
    lines = md_text.split('\n')
    html_lines = []
    in_code_block = False
    code_lang = ""
    code_buffer = []
    in_list = False       # currently inside a <ul> or <ol>
    list_type = ""        # "ul" or "ol"
    in_table = False
    table_buffer = []

    def _close_list():
        nonlocal in_list, list_type
        if in_list:
            html_lines.append(f'</{list_type}>')
            in_list = False
            list_type = ""

    def _close_table():
        nonlocal in_table, table_buffer
        if in_table and table_buffer:
            html_lines.append(_render_table(table_buffer))
            table_buffer = []
            in_table = False

    def _render_table(rows):
        """Render a Markdown table given a list of raw row strings."""
        if len(rows) < 2:
            return '<p>' + html_module.escape('|'.join(rows)) + '</p>'
        result = '<table>\n<thead>\n<tr>'
        header_cells = [c.strip() for c in rows[0].strip('|').split('|')]
        for cell in header_cells:
            result += f'<th>{_inline(cell)}</th>'
        result += '</tr>\n</thead>\n<tbody>\n'
        # rows[1] is the separator row (---|---), skip it
        for row in rows[2:]:
            result += '<tr>'
            cells = [c.strip() for c in row.strip('|').split('|')]
            for cell in cells:
                result += f'<td>{_inline(cell)}</td>'
            result += '</tr>\n'
        result += '</tbody>\n</table>'
        return result

    def _inline(text):
        """Process inline Markdown: bold, italic, code, links, images, strikethrough."""
        # Images ![alt](url)
        text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', lambda m: _img_tag(m.group(2), m.group(1), base_path), text)
        # Links [text](url)
        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
        # Inline code `code`
        text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
        # Bold+Italic ***text*** or ___text___
        text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', text)
        text = re.sub(r'___(.+?)___', r'<strong><em>\1</em></strong>', text)
        # Bold **text** or __text__
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'__(.+?)__', r'<strong>\1</strong>', text)
        # Italic *text* or _text_
        text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
        text = re.sub(r'(?<!\w)_(.+?)_(?!\w)', r'<em>\1</em>', text)
        # Strikethrough ~~text~~
        text = re.sub(r'~~(.+?)~~', r'<del>\1</del>', text)
        return text

    def _img_tag(src, alt, bp):
        """Build <img> tag, resolving relative paths."""
        if not src.startswith(('http://', 'https://', 'data:')):
            full = os.path.normpath(os.path.join(bp, src))
            src = QUrl.fromLocalFile(full).toString()
        return f'<img src="{src}" alt="{html_module.escape(alt)}" style="max-width:100%;">'

    for line in lines:
        # ── Fenced code blocks ──
        if line.strip().startswith('```'):
            if not in_code_block:
                _close_list()
                _close_table()
                in_code_block = True
                code_lang = line.strip()[3:].strip()
                code_buffer = []
            else:
                in_code_block = False
                escaped = html_module.escape('\n'.join(code_buffer))
                lang_cls = f' class="language-{code_lang}"' if code_lang else ''
                html_lines.append(f'<pre><code{lang_cls}>{escaped}</code></pre>')
            continue

        if in_code_block:
            code_buffer.append(line)
            continue

        stripped = line.strip()

        # ── Blank line → close open lists/tables, add spacing ──
        if not stripped:
            _close_list()
            _close_table()
            continue

        # ── Table rows (lines containing | ) ──
        if '|' in stripped and stripped.startswith('|'):
            _close_list()
            in_table = True
            table_buffer.append(stripped)
            continue
        else:
            _close_table()

        # ── Horizontal rule ──
        if re.match(r'^([-*_]\s*){3,}$', stripped):
            _close_list()
            html_lines.append('<hr>')
            continue

        # ── Headings ──
        heading_match = re.match(r'^(#{1,6})\s+(.+)', stripped)
        if heading_match:
            _close_list()
            level = len(heading_match.group(1))
            text = _inline(heading_match.group(2))
            html_lines.append(f'<h{level}>{text}</h{level}>')
            continue

        # ── Blockquotes ──
        if stripped.startswith('>'):
            _close_list()
            text = _inline(stripped.lstrip('>').strip())
            html_lines.append(f'<blockquote><p>{text}</p></blockquote>')
            continue

        # ── Unordered list ──
        ul_match = re.match(r'^(\s*)([-*+])\s+(.+)', line)
        if ul_match:
            _close_table()
            if not in_list or list_type != 'ul':
                _close_list()
                in_list = True
                list_type = 'ul'
                html_lines.append('<ul>')
            html_lines.append(f'<li>{_inline(ul_match.group(3))}</li>')
            continue

        # ── Ordered list ──
        ol_match = re.match(r'^(\s*)(\d+)\.\s+(.+)', line)
        if ol_match:
            _close_table()
            if not in_list or list_type != 'ol':
                _close_list()
                in_list = True
                list_type = 'ol'
                html_lines.append('<ol>')
            html_lines.append(f'<li>{_inline(ol_match.group(3))}</li>')
            continue

        # ── If we were in a list but this line doesn't match, close it ──
        _close_list()

        # ── HTML pass-through (div, img, br, etc.) ──
        if stripped.startswith('<'):
            html_lines.append(line)
            continue

        # ── Normal paragraph ──
        html_lines.append(f'<p>{_inline(stripped)}</p>')

    # Close any remaining open blocks
    if in_code_block:
        escaped = html_module.escape('\n'.join(code_buffer))
        html_lines.append(f'<pre><code>{escaped}</code></pre>')
    _close_list()
    _close_table()

    return '\n'.join(html_lines)


def _build_markdown_css(theme: dict) -> str:
    """Build Markdown CSS compatible with QTextBrowser (Qt Rich Text / CSS 2.1 subset).
    QTextBrowser does NOT support: *, box-sizing, nth-child, ::scrollbar, rgba(), rem, etc.
    Stick to: color, background-color, font-family, font-size, font-weight, font-style,
    margin, padding, border, text-decoration, text-align, white-space."""
    bg = theme.get('editor_bg', '#1e1e1e')
    fg = theme.get('editor_fg', '#d4d4d4')
    border = theme.get('border', '#3a3a3c')
    accent = theme.get('accent', '#58a6ff')
    text_secondary = theme.get('text_secondary', '#8b949e')

    return f"""
    body {{
        font-family: 'Segoe UI', 'Helvetica', 'Arial', sans-serif;
        font-size: 14px;
        color: {fg};
        background-color: {bg};
        margin: 24px 32px;
    }}
    h1 {{
        font-size: 28px;
        font-weight: bold;
        color: #e6edf3;
        margin-top: 24px;
        margin-bottom: 12px;
        border-bottom: 1px solid {border};
        padding-bottom: 8px;
    }}
    h2 {{
        font-size: 22px;
        font-weight: bold;
        color: #e6edf3;
        margin-top: 22px;
        margin-bottom: 10px;
        border-bottom: 1px solid {border};
        padding-bottom: 6px;
    }}
    h3 {{
        font-size: 18px;
        font-weight: bold;
        color: #e6edf3;
        margin-top: 20px;
        margin-bottom: 8px;
    }}
    h4 {{
        font-size: 16px;
        font-weight: bold;
        color: #e6edf3;
        margin-top: 18px;
        margin-bottom: 6px;
    }}
    h5 {{
        font-size: 14px;
        font-weight: bold;
        color: #e6edf3;
        margin-top: 16px;
        margin-bottom: 4px;
    }}
    h6 {{
        font-size: 13px;
        font-weight: bold;
        color: {text_secondary};
        margin-top: 14px;
        margin-bottom: 4px;
    }}
    p {{
        margin-top: 0px;
        margin-bottom: 12px;
    }}
    a {{
        color: {accent};
        text-decoration: none;
    }}
    strong {{
        font-weight: bold;
        color: #e6edf3;
    }}
    em {{
        font-style: italic;
    }}
    del {{
        text-decoration: line-through;
        color: {text_secondary};
    }}
    code {{
        font-family: 'Cascadia Code', 'Consolas', 'Courier New', monospace;
        font-size: 13px;
        background-color: #2d333b;
        color: #e6edf3;
        padding: 2px 5px;
    }}
    pre {{
        background-color: #161b22;
        border: 1px solid {border};
        padding: 14px;
        margin-top: 0px;
        margin-bottom: 14px;
        font-family: 'Cascadia Code', 'Consolas', 'Courier New', monospace;
        font-size: 13px;
        color: #e6edf3;
        white-space: pre;
    }}
    blockquote {{
        margin: 0px 0px 14px 0px;
        padding: 0px 0px 0px 14px;
        color: {text_secondary};
        border-left: 3px solid {border};
    }}
    ul {{
        margin-top: 0px;
        margin-bottom: 14px;
    }}
    ol {{
        margin-top: 0px;
        margin-bottom: 14px;
    }}
    li {{
        margin-top: 3px;
        margin-bottom: 3px;
    }}
    hr {{
        border: none;
        border-top: 2px solid {border};
        margin: 20px 0px;
    }}
    table {{
        border-collapse: collapse;
        margin-top: 0px;
        margin-bottom: 14px;
    }}
    th {{
        font-weight: bold;
        padding: 6px 13px;
        border: 1px solid {border};
        background-color: #21262d;
        color: #e6edf3;
    }}
    td {{
        padding: 6px 13px;
        border: 1px solid {border};
    }}
    img {{
        max-width: 600px;
    }}
    """


class MarkdownPreviewWidget(BasePreviewWidget):
    """
    Markdown file viewer with split pane:
    Left = raw editor (QScintilla), Right = rendered HTML preview (QTextBrowser).
    Live-updates the preview as you type.
    """

    def __init__(self, file_path: str, theme: dict, editor_widget=None, parent=None):
        super().__init__(file_path, theme, parent)

        self._base_path = os.path.dirname(os.path.abspath(file_path))

        # ── Toolbar ──
        toolbar = QFrame()
        toolbar.setFixedHeight(32)
        toolbar.setStyleSheet(f"""
            QFrame {{
                background-color: {theme['sidebar_bg']};
                border-bottom: 1px solid {theme['border']};
            }}
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 4px;
                padding: 4px 10px;
                color: {theme['text_secondary']};
                font-family: 'Segoe UI', sans-serif;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {theme['bg_hover']};
                color: {theme['text_primary']};
            }}
            QPushButton:checked {{
                background-color: {theme['bg_active']};
                color: {theme['text_primary']};
            }}
            QLabel {{
                color: {theme['text_secondary']};
                font-family: 'Segoe UI', sans-serif;
                font-size: 12px;
                padding-left: 10px;
            }}
        """)
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(8, 0, 8, 0)
        tb_layout.setSpacing(4)

        tb_layout.addWidget(QLabel("Markdown Preview"))
        tb_layout.addStretch()

        self.btn_editor = QPushButton("Editor")
        self.btn_editor.setCheckable(True)
        self.btn_split = QPushButton("Split")
        self.btn_split.setCheckable(True)
        self.btn_split.setChecked(True)
        self.btn_preview = QPushButton("Preview")
        self.btn_preview.setCheckable(True)

        self.btn_editor.clicked.connect(lambda: self._set_mode("editor"))
        self.btn_split.clicked.connect(lambda: self._set_mode("split"))
        self.btn_preview.clicked.connect(lambda: self._set_mode("preview"))

        tb_layout.addWidget(self.btn_editor)
        tb_layout.addWidget(self.btn_split)
        tb_layout.addWidget(self.btn_preview)

        self.layout.addWidget(toolbar)

        # ── Splitter: Editor (left) + Preview (right) ──
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(4)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background: {theme['border']};
                width: 4px;
            }}
            QSplitter::handle:hover {{
                background: {theme['accent']};
            }}
            QSplitter::handle:pressed {{
                background: {theme['accent']};
            }}
        """)

        # Left side: code editor (passed in from EditorTabs)
        self.editor = editor_widget
        self._editor_container = QWidget()
        self._editor_layout = QVBoxLayout(self._editor_container)
        self._editor_layout.setContentsMargins(0, 0, 0, 0)
        if self.editor:
            self._editor_layout.addWidget(self.editor)
        self.splitter.addWidget(self._editor_container)

        # Right side: QTextBrowser preview
        self.preview = QTextBrowser()
        self.preview.setOpenExternalLinks(True)
        self.preview.setFrameShape(QFrame.Shape.NoFrame)
        self.preview.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {theme['editor_bg']};
                color: {theme['editor_fg']};
                border: none;
            }}
        """)
        # Set search paths for images (so relative paths resolve)
        self.preview.setSearchPaths([self._base_path])

        self.splitter.addWidget(self.preview)
        self.splitter.setSizes([500, 500])
        self.layout.addWidget(self.splitter, 1)

        # ── Load source ──
        self._md_source = ""
        if file_path and os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    self._md_source = f.read()
            except Exception:
                self._md_source = ""

        # ── Synced scrolling ──
        self._last_scroll_line = -1
        self._scroll_timer = QTimer()
        self._scroll_timer.setInterval(100)
        self._scroll_timer.timeout.connect(self._sync_preview_scroll)

        # Initial render
        self._render_preview()

        # ── Live update: re-render when editor text changes ──
        self._update_timer = QTimer()
        self._update_timer.setSingleShot(True)
        self._update_timer.setInterval(600)
        self._update_timer.timeout.connect(self._on_editor_changed)

        if self.editor:
            self.editor.textChanged.connect(self._schedule_update)
            self._scroll_timer.start()

    def set_editor(self, editor_widget):
        """Attach the QScintilla editor after construction."""
        self.editor = editor_widget
        self._editor_layout.addWidget(self.editor)
        self.editor.textChanged.connect(self._schedule_update)
        self._scroll_timer.start()

    def _schedule_update(self):
        self._update_timer.start()

    def _sync_preview_scroll(self):
        """Sync preview scroll to match editor scroll position."""
        if not self.editor:
            return
        SCI_GETFIRSTVISIBLELINE = 2152
        SCI_LINESONSCREEN = 2370
        first_line = self.editor.SendScintilla(SCI_GETFIRSTVISIBLELINE)
        if first_line == self._last_scroll_line:
            return
        self._last_scroll_line = first_line

        total_lines = self.editor.lines()
        visible_lines = self.editor.SendScintilla(SCI_LINESONSCREEN)
        max_scroll_line = max(1, total_lines - visible_lines)
        ratio = min(1.0, max(0.0, first_line / max_scroll_line))

        sb = self.preview.verticalScrollBar()
        sb.setValue(int(ratio * sb.maximum()))

    def _on_editor_changed(self):
        if self.editor:
            self._md_source = self.editor.text()
            self._render_preview()

    def _render_preview(self):
        """Render the Markdown source into the QTextBrowser."""
        body_html = _markdown_to_html(self._md_source, self._base_path)
        css = _build_markdown_css(self.theme)
        full_html = f'<html><head><style>{css}</style></head><body>{body_html}</body></html>'

        # Save and restore scroll position
        sb = self.preview.verticalScrollBar()
        pos = sb.value()
        self.preview.setHtml(full_html)
        QTimer.singleShot(0, lambda: sb.setValue(pos))

    def _set_mode(self, mode):
        self.btn_editor.setChecked(mode == "editor")
        self.btn_split.setChecked(mode == "split")
        self.btn_preview.setChecked(mode == "preview")

        if mode == "editor":
            self._editor_container.show()
            self.preview.hide()
        elif mode == "preview":
            self._editor_container.hide()
            self.preview.show()
            self._render_preview()
        else:  # split
            self._editor_container.show()
            self.preview.show()
            self.splitter.setSizes([500, 500])
