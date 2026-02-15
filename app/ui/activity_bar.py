"""
ActivityBar - The vertical icon bar on the far left (like VS Code).
Shows icons for: Explorer, Search, Source Control, Run/Debug, Extensions.
"""

import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton,
                              QSizePolicy, QSpacerItem)
from PyQt6.QtCore import pyqtSignal, Qt, QSize, QRect
from PyQt6.QtGui import QIcon, QPainter, QColor, QPixmap


class ActivityBarButton(QPushButton):
    """A single icon button in the activity bar, loading SVG icons."""

    def __init__(self, icon_name: str, tooltip: str, view_id: str, parent=None):
        super().__init__(parent)
        self.view_id = view_id
        self.icon_name = icon_name
        self._active = False
        self.setToolTip(tooltip)
        self.setFixedSize(48, 48)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setCheckable(True)
        
        # Load Icon
        self._icon_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "assets", "icons", icon_name
        )
        self._load_icon()

    def _load_icon(self):
        if os.path.exists(self._icon_path):
            # Create QIcon from SVG
            self.setIcon(QIcon(self._icon_path))
            self.setIconSize(QSize(24, 24))
        else:
            self.setText("?") # Fallback

    def set_active(self, active: bool):
        self._active = active
        self.setChecked(active)
        self.update()

    def set_badge(self, text: str):
        self.badge_text = text
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # Background on hover
        if self.underMouse() and not self._active:
            painter.fillRect(self.rect(), QColor(self.parent().theme.get('bg_hover', '#1c1c1e')))

        # Active indicator (left border bar)
        if self._active:
            painter.fillRect(0, 10, 2, self.height() - 20, QColor(self.parent().theme.get('activitybar_active_fg', '#ffffff')))

        # Draw Icon (Tinted)
        if os.path.exists(self._icon_path):
            # Target color
            if self._active:
                color = QColor(self.parent().theme.get('activitybar_active_fg', '#ffffff'))
            else:
                color = QColor(self.parent().theme.get('activitybar_fg', '#858585'))

            pixmap = QIcon(self._icon_path).pixmap(24, 24)
            
            # Create a tinted pixmap
            # 1. Fill with color
            tinted = QPixmap(24, 24)
            tinted.fill(Qt.GlobalColor.transparent)
            p = QPainter(tinted)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            p.drawPixmap(0, 0, pixmap)
            # 2. SourceIn: Keep source (color) where destination (icon) is opaque? 
            # Actually easier: Draw icon, then fill rect with color using SourceIn
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
            p.fillRect(tinted.rect(), color)
            p.end()

            # Center and draw
            x = (self.width() - 24) // 2
            y = (self.height() - 24) // 2
            painter.drawPixmap(x, y, tinted)

        # Draw Badge
        if getattr(self, 'badge_text', None):
            painter.setBrush(QColor("#007acc")) # VS Code blue badge color
            painter.setPen(Qt.PenStyle.NoPen)
            
            # Adjust badge size based on text length
            text_width = painter.fontMetrics().horizontalAdvance(str(self.badge_text))
            badge_width = max(16, text_width + 8)
            # Position at bottom-right of icon area
            badge_rect = QRect(self.width() - badge_width - 4, self.height() - 22, badge_width, 16)
            
            painter.drawRoundedRect(badge_rect, 8, 8)
            
            painter.setPen(QColor("#ffffff"))
            font = painter.font()
            font.setPointSize(8)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, str(self.badge_text))

        painter.end()



class ActivityBar(QWidget):
    """The vertical activity bar on the far left of the IDE."""

    view_changed = pyqtSignal(str)  # Emits view_id when clicked

    VIEWS = [
        ("files.svg", "Explorer (Ctrl+Shift+E)", "explorer"),
        ("search.svg", "Search (Ctrl+Shift+F)", "search"),
        ("scm.svg",  "Source Control (Ctrl+Shift+G)", "scm"),
        ("debug.svg",  "Run and Debug (Ctrl+Shift+D)", "debug"),
        ("extensions.svg",  "Extensions (Ctrl+Shift+X)", "extensions"),
    ]

    def __init__(self, theme: dict, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.buttons: list[ActivityBarButton] = []
        self._current_view = "explorer"

        self.setFixedWidth(48)
        self.setStyleSheet(f"""
            ActivityBar {{
                background-color: {theme['activitybar_bg']};
                border-right: 1px solid {theme['border']};
            }}
            QPushButton {{
                border: none;
                background: transparent;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Top buttons
        for icon, tooltip, view_id in self.VIEWS:
            btn = ActivityBarButton(icon, tooltip, view_id, self)
            btn.clicked.connect(lambda checked, vid=view_id: self._on_click(vid))
            layout.addWidget(btn)
            self.buttons.append(btn)

        # Spacer pushes bottom buttons down
        layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Policy.Minimum,
                                         QSizePolicy.Policy.Expanding))

        # Bottom button: Account & Settings
        account_btn = ActivityBarButton("account.svg", "Accounts", "accounts", self)
        layout.addWidget(account_btn)
        self.buttons.append(account_btn)

        settings_btn = ActivityBarButton("settings.svg", "Settings (Ctrl+,)", "settings", self)
        settings_btn.clicked.connect(lambda: self._on_click("settings"))
        layout.addWidget(settings_btn)
        self.buttons.append(settings_btn)

        # Set initial active
        self.buttons[0].set_active(True)

    def set_badge(self, view_id: str, text: str):
        """Set a notification badge on a specific view button."""
        for btn in self.buttons:
            if btn.view_id == view_id:
                btn.set_badge(text)
                break

    def _on_click(self, view_id: str):
        if self._current_view == view_id:
            # Toggle sidebar visibility
            self.view_changed.emit("__toggle__")
            return

        self._current_view = view_id
        for btn in self.buttons:
            if btn.view_id in ["accounts", "settings"]:
                 # Don't highlight bottom buttons as main views for now
                 btn.set_active(False) 
            else:
                btn.set_active(btn.view_id == view_id)
        
        self.view_changed.emit(view_id)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(self.theme['activitybar_bg']))
        # Right border
        painter.setPen(QColor(self.theme['border']))
        painter.drawLine(self.width() - 1, 0, self.width() - 1, self.height())
        painter.end()
