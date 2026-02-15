import os
import json
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QScrollArea, 
                             QTreeWidget, QTreeWidgetItem, QHeaderView,
                             QHBoxLayout, QPushButton, QSlider,
                             QFrame)
from PyQt6.QtCore import Qt, QSize, QUrl, pyqtSignal, QEvent
from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor, QFont, QWheelEvent
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
    """Video player with basic controls."""
    def __init__(self, file_path: str, theme: dict, parent=None):
        super().__init__(file_path, theme, parent)
        self.media_player = QMediaPlayer()
        self.video_widget = QVideoWidget()
        self.audio_output = QAudioOutput()
        self.media_player.setVideoOutput(self.video_widget)
        self.media_player.setAudioOutput(self.audio_output)
        self.layout.addWidget(self.video_widget)
        
        controls = QWidget()
        controls.setFixedHeight(40)
        controls.setStyleSheet(f"background: {theme['sidebar_bg']}; border-top: 1px solid {theme['border']};")
        ctrl_layout = QHBoxLayout(controls)
        ctrl_layout.setContentsMargins(10, 0, 10, 0)
        
        self.play_btn = QPushButton("Play")
        self.play_btn.setFixedSize(60, 24)
        self.play_btn.clicked.connect(self._toggle_playback)
        ctrl_layout.addWidget(self.play_btn)
        
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.media_player.positionChanged.connect(self.slider.setValue)
        self.media_player.durationChanged.connect(self.slider.setMaximum)
        self.slider.sliderMoved.connect(self.media_player.setPosition)
        ctrl_layout.addWidget(self.slider)
        self.layout.addWidget(controls)
        
        self.media_player.setSource(QUrl.fromLocalFile(file_path))
        self.media_player.play()

    def _toggle_playback(self):
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
            self.play_btn.setText("Play")
        else:
            self.media_player.play()
            self.play_btn.setText("Pause")

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
