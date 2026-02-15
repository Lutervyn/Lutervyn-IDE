"""
Custom Title Bar - VS Code-style integrated title bar.
Layout: [Logo] [Menus...] [spacer] [Search Bar] [spacer] [Min] [Max] [Close]
"""

import os
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QLabel, QPushButton,
                              QMenuBar, QMenu, QSizePolicy, QLineEdit)
from PyQt6.QtCore import Qt, QPoint, pyqtSignal
from PyQt6.QtGui import (QPixmap, QFont, QColor, QPainter, QMouseEvent,
                          QPen)


class TitleBarButton(QPushButton):
    """Window control button (minimize / maximize / close)."""

    def __init__(self, icon_type: str, theme: dict, parent=None):
        super().__init__(parent)
        self.icon_type = icon_type
        self.theme = theme
        self._hovered = False
        self.setFixedSize(46, 30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background on hover
        if self._hovered:
            if self.icon_type == "close":
                painter.fillRect(self.rect(), QColor("#e81123"))
            else:
                painter.fillRect(self.rect(), QColor(self.theme['bg_hover']))

        # Draw icon
        pen_color = "#ffffff" if (self._hovered and self.icon_type == "close") else self.theme['text_primary']
        painter.setPen(QPen(QColor(pen_color), 1))

        cx = self.width() // 2
        cy = self.height() // 2

        if self.icon_type == "minimize":
            # Horizontal line ─
            painter.drawLine(cx - 5, cy, cx + 5, cy)

        elif self.icon_type == "maximize":
            # Square □
            painter.drawRect(cx - 5, cy - 4, 10, 9)

        elif self.icon_type == "restore":
            # Two overlapping squares ⧉
            painter.drawRect(cx - 3, cy - 5, 8, 8)
            painter.drawRect(cx - 5, cy - 3, 8, 8)

        elif self.icon_type == "close":
            # X mark ✕
            painter.drawLine(cx - 4, cy - 4, cx + 4, cy + 4)
            painter.drawLine(cx + 4, cy - 4, cx - 4, cy + 4)

        painter.end()


class TitleBarSearchBar(QLineEdit):
    """Centered search bar in title bar (Command Palette trigger)."""

    def __init__(self, theme: dict, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Lutervyn Search (Ctrl+P)")
        self.setReadOnly(True) # It acts as a button to open palette
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedWidth(400)
        self.setFixedHeight(22)
        
        # Style
        self.setStyleSheet(f"""
            QLineEdit {{
                background-color: {theme['input_bg']};
                color: {theme['text_secondary']};
                border: 1px solid {theme['border']};
                border-radius: 6px;
                padding: 0px 8px;
                font-size: 12px;
            }}
            QLineEdit:hover {{
                background-color: {theme['bg_hover']};
                border: 1px solid {theme['border_light']};
            }}
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Trigger command palette via parent window
            # We need to find the main window or emit a signal
            # Walking up to MainWindow
            win = self.window()
            if hasattr(win, "cmd_command_palette"):
                win.cmd_command_palette()
        super().mousePressEvent(event)


class CustomTitleBar(QWidget):
    """
    VS Code-style custom title bar.
    Layout: [Logo] [Menus...] [Spacer] [Search Bar] [Spacer] [Min] [Max] [Close]
    """

    # Signals for window controls
    minimize_clicked = pyqtSignal()
    maximize_clicked = pyqtSignal()
    close_clicked = pyqtSignal()

    def __init__(self, theme: dict, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.setFixedHeight(30)
        self._dragging = False
        self._drag_position = QPoint()
        self._is_maximized = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # === Logo icon ===
        self.logo_label = QLabel()
        logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)))), "assets", "logo.png")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path).scaled(
                18, 18, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation)
            self.logo_label.setPixmap(pixmap)
        else:
            self.logo_label.setText("⟨/⟩")
            font = QFont("Segoe UI", 10, QFont.Weight.Bold)
            font.setFamilies(["Segoe UI", "SF Pro Text", "Helvetica Neue", "Arial", "sans-serif"])
            self.logo_label.setFont(font)

        self.logo_label.setFixedSize(36, 30)
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo_label.setStyleSheet("background: transparent; padding-left: 6px;")
        layout.addWidget(self.logo_label)

        # === Menu bar (embedded) ===
        self.menu_bar = QMenuBar()
        self.menu_bar.setNativeMenuBar(False) # CRITICAL: Force in-window rendering
        self.menu_bar.setFixedHeight(30)
        self.menu_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        
        # Ensure text is visible on black background
        self.menu_bar.setStyleSheet(f"""
            QMenuBar {{
                background-color: transparent;
                color: {theme['text_primary']};
                font-family: 'Segoe UI';
                font-size: 11px;
            }}
            QMenuBar::item {{
                background: transparent;
                color: {theme['text_primary']};
                padding: 4px 10px;
            }}
            QMenuBar::item:selected {{
                background-color: {theme['bg_hover']};
            }}
        """)
        layout.addWidget(self.menu_bar)

        # === Left Spacer ===
        layout.addStretch(1)

        # === Search Bar ===
        self.search_bar = TitleBarSearchBar(theme, self)
        layout.addWidget(self.search_bar)

        # === Right Spacer ===
        layout.addStretch(1)

        # === Window control buttons ===
        self.btn_minimize = TitleBarButton("minimize", theme, self)
        self.btn_minimize.clicked.connect(self.minimize_clicked.emit)
        layout.addWidget(self.btn_minimize)

        self.btn_maximize = TitleBarButton("maximize", theme, self)
        self.btn_maximize.clicked.connect(self.maximize_clicked.emit)
        layout.addWidget(self.btn_maximize)

        self.btn_close = TitleBarButton("close", theme, self)
        self.btn_close.clicked.connect(self.close_clicked.emit)
        layout.addWidget(self.btn_close)

    def set_title(self, title: str):
        pass # Title is no longer shown in the bar

    def set_maximized_state(self, is_maximized: bool):
        self._is_maximized = is_maximized
        self.btn_maximize.icon_type = "restore" if is_maximized else "maximize"
        self.btn_maximize.update()

    def get_menu_bar(self) -> QMenuBar:
        return self.menu_bar

    # --- Dragging the window ---

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            # Only start drag if clicking on empty areas
            widget_at = self.childAt(event.pos())
            # If clicking directly on the title bar widget (background) or logo
            if widget_at is None or widget_at == self.logo_label:
                self._dragging = True
                self._drag_position = event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._dragging:
            window = self.window()
            # If maximized, restore first before dragging
            if window.isMaximized():
                window.showNormal()
                self.set_maximized_state(False)
                # Adjust drag position to keep cursor relative
                self._drag_position = QPoint(self.width() // 2, 15)
            window.move(event.globalPosition().toPoint() - self._drag_position)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._dragging = False
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        # Double-click title bar to maximize/restore
        widget_at = self.childAt(event.pos())
        if widget_at is None or widget_at == self.logo_label:
            self.maximize_clicked.emit()
        super().mouseDoubleClickEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(self.theme['titlebar_bg']))
        # Bottom border
        painter.setPen(QColor(self.theme['border']))
        painter.drawLine(0, self.height() - 1, self.width(), self.height() - 1)
        painter.end()
