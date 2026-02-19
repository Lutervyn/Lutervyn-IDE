"""
Lutervyn IDE - Theme & Styling
VS Code/iOS-inspired dark/light theme system
"""

DARK_THEME = {
    "name": "Lutervyn Modern Dark",

    # Base colors (Modern VS Code 2024)
    "bg_darkest": "#1f1f1f",  # Editor Background
    "bg_dark": "#181818",     # UI Foundation (Sidebar/Panel/Status)
    "bg_medium": "#2d2d2d",   # Inputs/Hover
    "bg_light": "#2b2b2b",    # Borders
    "bg_hover": "#2a2d2e",
    "bg_active": "#37373d",
    "bg_selection": "#264f78",

    # Text
    "text_primary": "#cccccc",
    "text_secondary": "#999999",
    "text_disabled": "#777777",
    "text_bright": "#ffffff",

    # Borders
    "border": "#2b2b2b",        # Subtle separators
    "border_light": "#2b2b2b",

    # Accent
    "accent": "#007acc",        # VS Code Blue
    "accent_hover": "#1177bb",
    "accent_fg": "#ffffff",

    # Activity bar (Matches Sidebar for cohesive modern look)
    "activitybar_bg": "#181818",
    "activitybar_fg": "#858585",
    "activitybar_active_fg": "#ffffff",
    "activitybar_active_border": "#ffffff",
    "activitybar_badge_bg": "#007acc",
    "activitybar_badge_fg": "#ffffff",

    # Sidebar
    "sidebar_bg": "#181818",
    "sidebar_fg": "#cccccc",
    "sidebar_header_bg": "#181818",
    "sidebar_header_fg": "#bbbbbb",

    # Editor
    "editor_bg": "#1f1f1f",
    "editor_fg": "#d4d4d4",
    "editor_line_highlight": "#2a2d2e",
    "editor_selection": "#264f78",
    "editor_gutter_bg": "#1f1f1f",
    "editor_gutter_fg": "#858585",

    # Tabs
    "tab_active_bg": "#1f1f1f", # Blends with editor
    "tab_active_fg": "#ffffff",
    "tab_active_border_top": "#007acc",
    "tab_inactive_bg": "#181818", # Blends with sidebar
    "tab_inactive_fg": "#8e8e8e",
    "tab_bar_bg": "#181818",

    # Panel (terminal / output)
    "panel_bg": "#1f1f1f",
    "panel_fg": "#d4d4d4",
    "panel_header_bg": "#181818",
    "panel_border": "#2b2b2b",

    # Status bar
    "statusbar_bg": "#181818",
    "statusbar_fg": "#cccccc",
    "statusbar_hover_bg": "#2a2d2e",

    # Scrollbar
    "scrollbar_bg": "transparent",
    "scrollbar_thumb": "#4e4e4e",
    "scrollbar_thumb_hover": "#5e5e5e",

    # Terminal
    "terminal_bg": "#1f1f1f",
    "terminal_fg": "#d4d4d4",
    "terminal_cursor": "#d4d4d4",

    # Title bar
    "titlebar_bg": "#181818", # Modern VS Code uses a cohesive title bar
    "titlebar_fg": "#cccccc",

    # Input / Search
    "input_bg": "#2b2b2b",
    "input_fg": "#cccccc",
    "input_border": "#2b2b2b",
    "input_border_focus": "#007acc",

    # Minimap
    "minimap_bg": "#1f1f1f",

    # Breadcrumb
    "breadcrumb_bg": "#1f1f1f",
    "breadcrumb_fg": "#a9a9a9",

    # Syntax colors — VS Code Modern palette
    "syntax_keyword": "#c586c0",
    "syntax_keyword2": "#569cd6",
    "syntax_string": "#ce9178",
    "syntax_number": "#b5cea8",
    "syntax_comment": "#6a9955",
    "syntax_function": "#dcdcaa",
    "syntax_class": "#4ec9b0",
    "syntax_variable": "#9cdcfe",
    "syntax_operator": "#d4d4d4",
    "syntax_decorator": "#dcdcaa",
    "syntax_builtin": "#4ec9b0",
    "syntax_self": "#569cd6",

    # Problems panel
    "problem_error": "#f14c4c",
    "problem_warning": "#cca700",
    "problem_info": "#3794ff",
    "problem_file_fg": "#cccccc",
    "problem_msg_fg": "#cccccc",
    "problem_source_fg": "#858585",
    "problem_position_fg": "#858585",

    # Git
    "git_modified": "#e2c08d",
    "git_added": "#73c991",
    "git_deleted": "#c74e39",
    "git_untracked": "#73c991",
    "git_renamed": "#4ec9b0",
    "git_conflict": "#e4676b",
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

    # Problems panel (VS Code light theme colors)
    "problem_error": "#e51400",
    "problem_warning": "#bf8803",
    "problem_info": "#1a85ff",
    "problem_file_fg": "#1e1e1e",
    "problem_msg_fg": "#1e1e1e",
    "problem_source_fg": "#616161",
    "problem_position_fg": "#616161",

    # Git / Source Control
    "git_modified": "#c6a029",
    "git_added": "#2ea043",
    "git_deleted": "#c74e39",
    "git_untracked": "#2ea043",
    "git_renamed": "#4ec9b0",
    "git_conflict": "#e4676b",
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
        border-radius: 6px;
        padding: 4px;
        font-family: 'Segoe UI', sans-serif;
        font-size: 11px; /* Reduced font size */
    }}
    QMenu::item {{
        background-color: transparent;
        color: {theme['text_primary']};
        padding: 4px 24px 4px 8px; /* Reduced vertical padding */
        border-radius: 4px;
        margin: 1px 2px; /* Reduced margin */
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
        margin: 2px 6px; /* Reduced separator margin */
    }}
    
    /* ===== SCROLLBAR (VS Code Style — thin, only visible on hover) ===== */
    QScrollBar:vertical {{
        background: transparent;
        width: 14px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: rgba(121, 121, 121, 0.4);
        min-height: 20px;
        border-radius: 0px; 
        margin: 0px;
        margin-left: 7px; /* Thin bar pushed right — 7px wide */
    }}
    QScrollBar::handle:vertical:hover {{
        background: rgba(121, 121, 121, 0.7);
        margin-left: 4px; /* Wider on hover */
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
        height: 14px;
        margin: 0;
    }}
    QScrollBar::handle:horizontal {{
        background: rgba(121, 121, 121, 0.4);
        min-width: 20px;
        border-radius: 0px;
        margin: 0px;
        margin-top: 7px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: rgba(121, 121, 121, 0.7);
        margin-top: 4px;
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
        padding: 2px 4px; /* VS Code density */
        border: none;
        border-radius: 0px; 
        margin: 0px; 
    }}
    QTreeView::item:hover {{
        background-color: {theme['bg_active']}; /* Better contrast */
    }}
    QTreeView::item:selected {{
        background-color: {theme['bg_selection']};
        color: {theme['text_bright']};
    }}
    QTreeView::branch {{
        background-color: {theme['sidebar_bg']};
        border-image: none;
        image: none;
        border: none;
    }}
    QTreeView::branch:has-siblings:!adjoins-item {{
        border-image: none;
        image: none;
    }}
    QTreeView::branch:has-siblings:adjoins-item {{
        border-image: none;
        image: none;
    }}
    QTreeView::branch:!has-children:!has-siblings:adjoins-item {{
        border-image: none;
        image: none;
    }}
    QTreeView::branch:has-children:!has-siblings:closed,
    QTreeView::branch:closed:has-children:has-siblings {{
        image: none;
        border-image: none;
    }}
    QTreeView::branch:open:has-children:!has-siblings,
    QTreeView::branch:open:has-children:has-siblings {{
        image: none;
        border-image: none;
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
        background-color: {theme['border']}; /* Subtle hairline separator */
    }}
    QSplitter::handle:horizontal {{
        width: 1px;
    }}
    QSplitter::handle:vertical {{
        height: 1px;
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
        padding: 6px 14px; /* Reduced padding */
        border: none;
        border-right: 1px solid {theme['border']};
        min-width: 80px;
        height: 31px; /* VS Code official height */
        font-size: 12px;
    }}
    QTabBar::tab:selected {{
        background-color: {theme['tab_active_bg']};
        color: {theme['tab_active_fg']};
        border-top: 2px solid {theme['tab_active_border_top']}; /* Matches Modern VS Code benchmark */
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