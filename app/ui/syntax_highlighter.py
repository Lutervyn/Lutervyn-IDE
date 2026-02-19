"""
Syntax Highlighter - A utility to provide beautiful syntax highlighting for multiple languages.
Used by the AI Panel to render code blocks with premium aesthetics.
"""

import re
import html as _html

# VS Code Dark+ inspired color palette
COLORS = {
    'python': {
        'keyword': '#c586c0',   # Purple (control)
        'keyword2': '#569cd6',  # Blue (storage/def/class)
        'function': '#dcdcaa',  # Yellow
        'class': '#4ec9b0',     # Teal
        'string': '#ce9178',    # Orange
        'comment': '#6a9955',   # Green
        'number': '#b5cea8',    # Light Green
        'default': '#d4d4d4',   # Light Gray
        'builtin': '#4ec9b0',   # Teal
        'variable': '#9cdcfe',  # Light Blue
    },
    'html': {
        'tag': '#569cd6',       # Blue
        'attribute': '#9cdcfe', # Light Blue
        'value': '#ce9178',     # Orange
        'comment': '#6a9955',   # Green
        'bracket': '#808080',   # Grey
        'default': '#d4d4d4',
    },
    'css': {
        'selector': '#d7ba7d',  # Light Yellow/Tan
        'property': '#9cdcfe',  # Light Blue
        'value': '#ce9178',     # Orange
        'unit': '#b5cea8',      # Light Green
        'comment': '#6a9955',   # Green
        'default': '#d4d4d4',
    },
    'js': {
        'keyword': '#c586c0',
        'keyword2': '#569cd6',
        'function': '#dcdcaa',
        'string': '#ce9178',
        'number': '#b5cea8',
        'comment': '#6a9955',
        'variable': '#9cdcfe',
        'default': '#d4d4d4',
    }
}

class SyntaxHighlighter:
    """Provides HTML-based syntax highlighting for various languages."""

    @staticmethod
    def highlight(code: str, lang: str = "") -> str:
        lang = lang.lower().strip()
        if lang in ('python', 'py'):
            return SyntaxHighlighter._highlight_python(code)
        elif lang in ('html', 'htm'):
            return SyntaxHighlighter._highlight_html(code)
        elif lang in ('css',):
            return SyntaxHighlighter._highlight_css(code)
        elif lang in ('javascript', 'js', 'ts', 'typescript'):
            return SyntaxHighlighter._highlight_js(code)
        
        # Default fallback: Just escape HTML
        return f'<span style="color:{COLORS.get("python", {}).get("default", "#D4D4D4")}">{_html.escape(code)}</span>'

    @staticmethod
    def _highlight_python(code: str) -> str:
        c = COLORS['python']
        
        # 1. Escape HTML first
        h = _html.escape(code)
        
        # 2. Syntax patterns (simplified but effective for UI)
        patterns = [
            (r'(?m)^#.*$', f'<span style="color:{c["comment"]}">\\g<0></span>'),                   # Comments
            (r'\"\"\"[\s\S]*?\"\"\"', f'<span style="color:{c["comment"]}">\\g<0></span>'),      # Triple quotes
            (r'\'\'\'[\s\S]*?\'\'\'', f'<span style="color:{c["comment"]}">\\g<0></span>'),
            (r'(?<!\w)(class|def|if|elif|else|for|while|try|except|finally|return|import|from|with|as|pass|break|continue|in|is|not|and|or|lambda|yield|async|await|assert|global|nonlocal|del)(?!\w)', 
             f'<span style="color:{c["keyword"]}">\\1</span>'),                                    # Keywords
            (r'(?<!\w)(self|None|True|False|print|len|range|enumerate|zip|open|list|dict|set|tuple|int|str|float|bool|type)(?!\w)', 
             f'<span style="color:{c["builtin"]}">\\1</span>'),                                    # Builtins/Constants
            (r'(\b\d+\b)', f'<span style="color:{c["number"]}">\\1</span>'),                        # Numbers
            (r'(".*?"|\'.*?\')', f'<span style="color:{c["string"]}">\\1</span>'),                  # Strings
            (r'(?<=def\s)(\w+)', f'<span style="color:{c["function"]}">\\1</span>'),               # Functions
            (r'(?<=class\s)(\w+)', f'<span style="color:{c["class"]}">\\1</span>'),               # Classes
        ]
        
        # Custom logic for regex replacement in HTML (be careful with existing tags)
        # For a truly robust highlighter we'd use a lexer, but regex suffices for "beautiful" previews.
        for pattern, replacement in patterns:
            # Note: This simple sequence can double-wrap. 
            # In a production app we'd use a single pass with a master regex.
            pass

        # Since we're doing "beautiful UI", let's use a slightly better approach:
        # We will tokenize and then join.
        
        return h # Placeholder for now, real implementation below

    @staticmethod
    def get_html(code: str, lang: str = "") -> str:
        """Returns the fully formatted HTML for the code block."""
        # For now, we will use a simple rule-based highlighter that doesn't break the HTML
        lang = lang.lower()
        palette = COLORS.get(lang if lang in COLORS else 'python')
        
        escaped = _html.escape(code)
        
        if lang in ('python', 'py'):
            # Simple but safe regex highlighting for escaped HTML
            
            # Keywords (def, class, etc - blue)
            expr2 = r'\b(def|class|async|await)\b'
            escaped = re.sub(expr2, rf'<span style="color:{palette["keyword2"]}">\1</span>', escaped)
            
            # Keywords (control - purple)
            expr = r'\b(if|elif|else|for|while|return|import|from|with|as|try|except|finally|pass|break|continue|yield|del|in|is|not|and|or|lambda|assert|global|nonlocal)\b'
            escaped = re.sub(expr, rf'<span style="color:{palette["keyword"]}">\1</span>', escaped)

            # Builtins & Classes (Teal)
            expr3 = r'\b(print|self|None|True|False|dict|list|set|tuple|str|int|float|bool|type|len|range|enumerate|zip|open|next|iter|min|max|sum|any|all)\b'
            escaped = re.sub(expr3, rf'<span style="color:{palette["builtin"]}">\1</span>', escaped)

            # Numbers (Light Green)
            escaped = re.sub(r'\b(\d+)\b', rf'<span style="color:{palette["number"]}">\1</span>', escaped)
            
            # Strings
            escaped = re.sub(r'(&quot;.*?&quot;|\'.*?\')', rf'<span style="color:{palette["string"]}">\1</span>', escaped)
            
            # Comments
            escaped = re.sub(r'(#.*$)', rf'<span style="color:{palette["comment"]}">\1</span>', escaped, flags=re.MULTILINE)
        elif lang in ('html', 'htm', 'xml'):
            # Tags (angle brackets - grey)
            escaped = re.sub(r'(&lt;/?|/?&gt;)', rf'<span style="color:{palette["bracket"]}">\1</span>', escaped)
            # Tag names (blue)
            escaped = re.sub(rf'(?<=color:{palette["bracket"]}">)(&lt;/?)([\w:-]+)', rf'\1<span style="color:{palette["tag"]}">\2</span>', escaped)
            # Attributes (light blue)
            escaped = re.sub(r'(\s+)([\w:-]+)(?==)', rf'\1<span style="color:{palette["attribute"]}">\2</span>', escaped)
            # Values (orange)
            escaped = re.sub(r'(=)(&quot;.*?&quot;|&apos;.*?&apos;)', rf'\1<span style="color:{palette["value"]}">\2</span>', escaped)
            # Comments (green)
            escaped = re.sub(r'(&lt;!--.*?--&gt;)', rf'<span style="color:{palette["comment"]}">\1</span>', escaped, flags=re.DOTALL)
        elif lang in ('css',):
            # Selectors (tan/yellow)
            escaped = re.sub(r'^([\s\S]*?)(?=\{)', lambda m: re.sub(r'(\.[\w-]+|#[\w-]+|\b\w+\b)', rf'<span style="color:{palette["selector"]}">\1</span>', m.group(1)), escaped, flags=re.MULTILINE)
            # Properties (light blue)
            escaped = re.sub(r'([\w-]+)(?=:)', rf'<span style="color:{palette["property"]}">\1</span>', escaped)
            # Values (orange)
            escaped = re.sub(r'(?<=:)([^;]+)', lambda m: re.sub(r'(&quot;.*?&quot;|\'.*?\'|\b[\w-]+\b)', rf'<span style="color:{palette["value"]}">\1</span>', m.group(1)), escaped)
            # Units (light green)
            escaped = re.sub(r'(\d+)(px|em|rem|%|vh|vw|s|ms)', rf'<span style="color:{palette["number"]}">\1</span><span style="color:{palette["unit"]}">\2</span>', escaped)
            # Comments (green)
            escaped = re.sub(r'(/\*[\s\S]*?\*/)', rf'<span style="color:{palette["comment"]}">\1</span>', escaped)

        return f'<div style="white-space: pre; font-family:\'Cascadia Code\',\'Consolas\',monospace; font-size:12px; line-height:1.5; color:{palette["default"]};">{escaped}</div>'
