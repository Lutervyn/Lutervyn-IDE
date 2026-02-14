"""
Lutervyn IDE - Theme & Styling
VS Code/iOS-inspired dark/light theme system
"""

DARK_THEME = {
    "name": "Lutervyn iOS Dark",

    # Base colors (iOS Dark / VS Code Modern)
    "bg_darkest": "#000000",  # Pure Black Sidebar/Panel
    "bg_dark": "#000000",     # Surface (Activity Bar)
    "bg_medium": "#1c1c1e",   # Inputs/Hover
    "bg_light": "#333333",    # Borders
    "bg_hover": "#1c1c1e",
    "bg_active": "#2c2c2e",
    "bg_selection": "#2c2c2e",

    # Text
    "text_primary": "#ffffff",
    "text_secondary": "#aeaeb2",
    "text_disabled": "#636366",
    "text_bright": "#ffffff",

    # Borders
    "border": "#3a3a3c",        # Subtle separators
    "border_light": "#48484a",

    # Accent
    "accent": "#ffffff",        # Monochrome White
    "accent_hover": "#f2f2f7",
    "accent_fg": "#000000",

    # Activity bar
    "activitybar_bg": "#000000",
    "activitybar_fg": "#8e8e93",
    "activitybar_active_fg": "#ffffff",
    "activitybar_active_border": "transparent",
    "activitybar_badge_bg": "#ff3b30", # iOS Red for badges
    "activitybar_badge_fg": "#ffffff",

    # Sidebar
    "sidebar_bg": "#000000",
    "sidebar_fg": "#d1d1d6",
    "sidebar_header_bg": "#000000",
    "sidebar_header_fg": "#aeaeb2",

    # Editor
    "editor_bg": "#000000",      # Pure black for contrast often looks better on OLED/Modern
    "editor_fg": "#d1d1d6",
    "editor_line_highlight": "#1c1c1e",
    "editor_selection": "#2c2c2e", # Subtle gray for selection
    "editor_gutter_bg": "#000000",
    "editor_gutter_fg": "#636366",

    # Tabs
    "tab_active_bg": "#000000",
    "tab_active_fg": "#ffffff",
    "tab_active_border_top": "#ffffff", # Monochrome top line
    "tab_inactive_bg": "#000000",
    "tab_inactive_fg": "#aeaeb2",
    "tab_bar_bg": "#000000",

    # Panel (terminal / output)
    "panel_bg": "#000000",
    "panel_fg": "#d1d1d6",
    "panel_header_bg": "#000000",
    "panel_border": "#3a3a3c",

    # Status bar
    "statusbar_bg": "#000000", # Pure Black
    "statusbar_fg": "#ffffff",
    "statusbar_hover_bg": "#1c1c1e",

    # Scrollbar
    "scrollbar_bg": "transparent",
    "scrollbar_thumb": "#636366",
    "scrollbar_thumb_hover": "#8e8e93",

    # Terminal
    "terminal_bg": "#000000",
    "terminal_fg": "#d1d1d6",
    "terminal_cursor": "#ffffff",

    # Title bar
    "titlebar_bg": "#000000",
    "titlebar_fg": "#d1d1d6",

    # Input / Search
    "input_bg": "#000000",
    "input_fg": "#d1d1d6",
    "input_border": "#3a3a3c",
    "input_border_focus": "#ffffff", # White glow

    # Minimap
    "minimap_bg": "#000000",

    # Breadcrumb
    "breadcrumb_bg": "#000000",
    "breadcrumb_fg": "#aeaeb2",

    # Syntax colors (Defaulting to standard VS Code Dark+)
    "syntax_keyword": "#ffffff",    # Monochrome White
    "syntax_string": "#ce9178",
    "syntax_number": "#b5cea8",
    "syntax_comment": "#6a9955",
    "syntax_function": "#dcdcaa",
    "syntax_class": "#4ec9b0",
    "syntax_variable": "#ffffff",   # Monochrome White
    "syntax_operator": "#d4d4d4",
    "syntax_decorator": "#dcdcaa",
    "syntax_builtin": "#4ec9b0",
    "syntax_self": "#ffffff",
}

LIGHT_THEME = {
    # Placeholder for light theme adjustments if needed
    "name": "Lutervyn Light",
    "bg_darkest": "#f2f2f7",
    "bg_dark": "#ffffff",
    "bg_medium": "#e5e5ea",
    "bg_light": "#d1d1d6",
    "bg_hover": "#e5e5ea",
    "bg_active": "#007aff",
    "bg_selection": "#b3d7ff",
    "text_primary": "#000000",
    "text_secondary": "#3a3a3c",
    "text_disabled": "#8e8e93",
    "text_bright": "#000000",
    "border": "#c6c6c8",
    "border_light": "#d1d1d6",
    "accent": "#007aff",
    "accent_hover": "#0051a8",
    "accent_fg": "#ffffff",
    "activitybar_bg": "#f2f2f7",
    "activitybar_fg": "#8e8e93",
    "activitybar_active_fg": "#007aff",
    "activitybar_active_border": "transparent",
    "activitybar_badge_bg": "#ff3b30",
    "activitybar_badge_fg": "#ffffff",
    "sidebar_bg": "#f2f2f7",
    "sidebar_fg": "#000000",
    "sidebar_header_bg": "#f2f2f7",
    "sidebar_header_fg": "#3a3a3c",
    "editor_bg": "#ffffff",
    "editor_fg": "#000000",
    "editor_line_highlight": "#f2f2f7",
    "editor_selection": "#b3d7ff",
    "editor_gutter_bg": "#ffffff",
    "editor_gutter_fg": "#8e8e93",
    "tab_active_bg": "#ffffff",
    "tab_active_fg": "#000000",
    "tab_active_border_top": "#007aff",
    "tab_inactive_bg": "#f2f2f7",
    "tab_inactive_fg": "#8e8e93",
    "tab_bar_bg": "#f2f2f7",
    "panel_bg": "#ffffff",
    "panel_fg": "#000000",
    "panel_header_bg": "#f2f2f7",
    "panel_border": "#c6c6c8",
    "statusbar_bg": "#007aff",
    "statusbar_fg": "#ffffff",
    "statusbar_hover_bg": "#0051a8",
    "scrollbar_bg": "transparent",
    "scrollbar_thumb": "#c6c6c8",
    "scrollbar_thumb_hover": "#8e8e93",
    "terminal_bg": "#ffffff",
    "terminal_fg": "#000000",
    "terminal_cursor": "#007aff",
    "titlebar_bg": "#f2f2f7",
    "titlebar_fg": "#000000",
    "input_bg": "#ffffff",
    "input_fg": "#000000",
    "input_border": "#c6c6c8",
    "input_border_focus": "#007aff",
    "minimap_bg": "#ffffff",
    "breadcrumb_bg": "#ffffff",
    "breadcrumb_fg": "#3a3a3c",
    "syntax_keyword": "#0000ff",
    "syntax_string": "#a31515",
    "syntax_number": "#098658",
    "syntax_comment": "#008000",
    "syntax_function": "#795e26",
    "syntax_class": "#267f99",
    "syntax_variable": "#001080",
    "syntax_operator": "#333333",
    "syntax_decorator": "#795e26",
    "syntax_builtin": "#267f99",
    "syntax_self": "#0000ff",
}


def get_theme(dark=True):
    return DARK_THEME if dark else LIGHT_THEME


def build_stylesheet(theme: dict) -> str:
    """Generate a complete Qt stylesheet from a theme dictionary."""
    return f"""
    /* ===== GLOBAL ===== */
    QWidget {{
        background-color: {theme['bg_darkest']};
        color: {theme['text_primary']};
        font-family: 'Segoe UI', 'SF Pro Text', 'Helvetica Neue', 'Arial', sans-serif;
        font-size: 13px;
        border: none;
    }}



    /* ===== MENU BAR ===== */
    QMenuBar {{
        background-color: {theme['titlebar_bg']};
        color: {theme['titlebar_fg']};
        padding: 4px 6px;
        border: none;
    }}
    QMenuBar::item {{
        padding: 6px 12px;
        background: transparent;
        border-radius: 4px;
    }}
    QMenuBar::item:selected {{
        background-color: {theme['bg_hover']};
    }}

    /* ===== MENUS & CONTEXT MENUS (Rounded & Shadow) ===== */
    QMenu {{
        background-color: {theme['bg_medium']};
        color: {theme['text_primary']};
        border: 1px solid {theme['border_light']};
        border-radius: 10px;
        padding: 6px;
    }}
    QMenu::item {{
        background-color: transparent;
        color: {theme['text_primary']};
        padding: 6px 30px 6px 10px;
        border-radius: 6px;
        margin: 2px 4px;
    }}
    QMenu::item:selected {{
        background-color: {theme['bg_active']};
        color: white;
    }}
    QMenu::item:disabled {{
        color: {theme['text_disabled']};
    }}
    QMenu::separator {{
        height: 1px;
        background-color: {theme['border']};
        margin: 4px 10px;
    }}
    
    /* ===== SCROLLBAR (VS Code Style) ===== */
    QScrollBar:vertical {{
        background: transparent;
        width: 12px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {theme['scrollbar_thumb']};
        min-height: 20px;
        border-radius: 0px; 
        margin: 2px;
        margin-left: 4px; /* Move it to the right like VS Code */
    }}
    QScrollBar::handle:vertical:hover {{
        background: {theme['scrollbar_thumb_hover']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
        background: none;
    }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: none;
    }}

    QScrollBar:horizontal {{
        background: transparent;
        height: 12px;
        margin: 0;
    }}
    QScrollBar::handle:horizontal {{
        background: {theme['scrollbar_thumb']};
        min-width: 20px;
        border-radius: 0px;
        margin: 2px;
        margin-top: 4px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {theme['scrollbar_thumb_hover']};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
        background: none;
    }}
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
        background: none;
    }}

    /* ===== TREE VIEW (File Explorer) ===== */
    QTreeView, QTreeWidget {{
        background-color: {theme['sidebar_bg']};
        color: {theme['sidebar_fg']};
        border: none;
        outline: none;
        show-decoration-selected: 1;
        padding-top: 5px;
    }}
    QTreeView::item {{
        padding: 4px;
        border: none;
        border-radius: 0px; 
        margin: 0px; 
    }}
    QTreeView::item:hover {{
        background-color: {theme['bg_hover']};
    }}
    QTreeView::item:selected {{
        background-color: {theme['bg_selection']};
        color: {theme['text_bright']};
    }}
    QTreeView::branch {{
        background-color: {theme['sidebar_bg']};
    }}
    QHeaderView::section {{
        background-color: {theme['sidebar_header_bg']};
        color: {theme['sidebar_header_fg']};
        padding: 4px 12px;
        border: none;
        font-weight: 600;
        text-transform: uppercase;
        font-size: 11px;
    }}

    /* ===== SPLITTER ===== */
    QSplitter::handle {{
        background-color: {theme['bg_darkest']};
        border: 1px solid {theme['border']};
    }}
    QSplitter::handle:horizontal {{
        width: 6px;
    }}
    QSplitter::handle:vertical {{
        height: 6px;
    }}
    QSplitter::handle:pressed {{
        background-color: {theme['accent']};
    }}

    /* ===== TAB WIDGET ===== */
    QTabWidget::pane {{
        border: none;
        background-color: {theme['editor_bg']};
    }}
    QTabBar {{
        background-color: {theme['tab_bar_bg']};
        border: none;
    }}
    QTabBar::tab {{
        background-color: {theme['tab_inactive_bg']};
        color: {theme['tab_inactive_fg']};
        padding: 8px 16px;
        border: none;
        border-right: 1px solid {theme['border']};
        min-width: 100px;
        margin-right: 1px;
    }}
    QTabBar::tab:selected {{
        background-color: {theme['tab_active_bg']};
        color: {theme['tab_active_fg']};
        border-top: 2px solid {theme['tab_active_border_top']};
    }}
    QTabBar::tab:hover:!selected {{
        background-color: {theme['bg_hover']};
    }}
    QTabBar::close-button {{
        image: none;
        subcontrol-position: right;
    }}

    /* ===== LINE EDIT / INPUT (Rounded) ===== */
    QLineEdit {{
        background-color: {theme['input_bg']};
        color: {theme['input_fg']};
        border: 1px solid {theme['input_border']};
        border-radius: 6px; /* Rounded inputs */
        padding: 6px 10px;
        selection-background-color: {theme['bg_selection']};
    }}
    QLineEdit:focus {{
        border: 1px solid {theme['input_border_focus']};
    }}

    /* ===== PUSH BUTTON (iOS Style) ===== */
    QPushButton {{
        background-color: {theme['accent']};
        color: {theme['accent_fg']};
        border: none;
        padding: 8px 16px;
        border-radius: 8px;
        font-weight: 600;
    }}
    QPushButton:hover {{
        background-color: {theme['accent_hover']};
    }}
    QPushButton:pressed {{
        background-color: {theme['accent']};
        padding-top: 9px; /* Press effect */
    }}

    /* ===== TOOLTIP ===== */
    QToolTip {{
        background-color: {theme['bg_dark']};
        color: {theme['text_primary']};
        border: 1px solid {theme['border_light']};
        padding: 6px 10px;
        border-radius: 6px;
    }}

    /* ===== STATUS BAR ===== */
    QStatusBar {{
        background-color: {theme['statusbar_bg']};
        color: {theme['statusbar_fg']};
        border: none;
        font-size: 12px;
    }}
    QStatusBar QLabel {{
        color: {theme['statusbar_fg']};
        padding: 0px 8px;
        background: transparent;
    }}

    /* ===== DIALOG ===== */
    QDialog {{
        background-color: {theme['bg_dark']};
    }}

    /* ===== LABEL ===== */
    QLabel {{
        background: transparent;
    }}

    /* ===== TEXT EDIT (terminal, output) ===== */
    QPlainTextEdit, QTextEdit {{
        background-color: {theme['terminal_bg']};
        color: {theme['terminal_fg']};
        border: none;
        font-family: 'Cascadia Code', 'Consolas', 'Fira Code', 'Droid Sans Mono', 'Monospace';
        font-size: 13px;
        selection-background-color: {theme['bg_selection']};
    }}


    """
