"""
Lutervyn IDE — VS Code Extension Manager
==========================================
Downloads and parses VS Code extensions from the marketplace.
VSIX files are just ZIP archives containing:
  - package.json          → metadata, contributes.themes, contributes.languages
  - themes/*.json         → TextMate-style tokenColors (scope → color mappings)
  - syntaxes/*.tmLanguage → TextMate grammars (optional)

We parse the theme JSON and map TextMate scopes → QScintilla style numbers.
"""

import os
import sys
import json
import zipfile
import shutil
import urllib.request
import urllib.parse
import threading
from pathlib import Path
from typing import Optional


# ══════════════════════════════════════════════════════════════
# PATHS
# ══════════════════════════════════════════════════════════════
def _extensions_dir() -> Path:
    """Where installed extensions live."""
    base = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    d = base / "extensions"
    d.mkdir(exist_ok=True)
    return d


def _cache_dir() -> Path:
    """Temp dir for downloaded .vsix files."""
    d = _extensions_dir() / ".cache"
    d.mkdir(exist_ok=True)
    return d


# ══════════════════════════════════════════════════════════════
# MARKETPLACE API
# ══════════════════════════════════════════════════════════════
# VS Code Marketplace (official, has everything)
MARKETPLACE_API = "https://marketplace.visualstudio.com/_apis/public/gallery/extensionquery"

# Open VSX Registry (open-source alternative — used for downloading .vsix)
OPENVSX_API = "https://open-vsx.org/api"
OPENVSX_SEARCH = "https://open-vsx.org/api/-/search"


def _search_vscode_marketplace(query: str, max_results: int = 20) -> list[dict]:
    """Search the official VS Code Marketplace.
    
    Uses the gallery API with POST request + JSON body.
    Downloads come from Open VSX (since VS Code marketplace needs auth for VSIX).
    """
    try:
        body = json.dumps({
            "filters": [{
                "criteria": [
                    {"filterType": 8, "value": "Microsoft.VisualStudio.Code"},
                    {"filterType": 10, "value": query},
                ],
                "pageNumber": 1,
                "pageSize": max_results,
                "sortBy": 0,  # 0 = relevance
                "sortOrder": 0,
            }],
            "assetTypes": [],
            "flags": 914,  # include versions, files, properties, stats
        }).encode("utf-8")

        req = urllib.request.Request(
            MARKETPLACE_API,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json;api-version=6.0-preview.1",
            },
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())

        results = []
        for ext in data.get("results", [{}])[0].get("extensions", []):
            publisher = ext.get("publisher", {}).get("publisherName", "")
            name = ext.get("extensionName", "")
            display_name = ext.get("displayName", name)
            desc = ext.get("shortDescription", "")
            version = ""
            icon_url = ""

            # Get latest version
            versions = ext.get("versions", [])
            if versions:
                version = versions[0].get("version", "")
                # Find icon
                for f in versions[0].get("files", []):
                    if f.get("assetType") == "Microsoft.VisualStudio.Services.Icons.Default":
                        icon_url = f.get("source", "")

            # Stats
            download_count = 0
            avg_rating = 0
            for stat in ext.get("statistics", []):
                if stat.get("statisticName") == "install":
                    download_count = int(stat.get("value", 0))
                elif stat.get("statisticName") == "averagerating":
                    avg_rating = stat.get("value", 0)

            # Build download URL — VS Code marketplace direct VSIX link
            download_url = (
                f"https://{publisher}.gallery.vsassets.io/_apis/public/gallery/"
                f"publisher/{publisher}/extension/{name}/{version}/"
                f"assetbyname/Microsoft.VisualStudio.Services.VSIXPackage"
            )

            results.append({
                "name": name,
                "namespace": publisher,
                "displayName": display_name,
                "description": desc,
                "version": version,
                "iconUrl": icon_url,
                "downloadUrl": download_url,
                "downloadCount": download_count,
                "averageRating": avg_rating,
                "categories": ext.get("categories", []),
                "_source": "marketplace",
            })

        return results

    except Exception as e:
        print(f"[ExtensionManager] VS Code Marketplace search error: {e}")
        return []


def _search_openvsx(query: str, max_results: int = 20) -> list[dict]:
    """Search Open VSX Registry for extensions."""
    try:
        params = urllib.parse.urlencode({
            "query": query,
            "size": max_results,
            "sortBy": "relevance",
            "sortOrder": "desc",
        })
        url = f"{OPENVSX_SEARCH}?{params}"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode())

        results = []
        for ext in data.get("extensions", []):
            info = {
                "name": ext.get("name", ""),
                "namespace": ext.get("namespace", ""),
                "displayName": ext.get("displayName", ext.get("name", "")),
                "description": ext.get("description", ""),
                "version": ext.get("version", ""),
                "iconUrl": "",
                "downloadUrl": "",
                "downloadCount": ext.get("downloadCount", 0),
                "averageRating": ext.get("averageRating", 0),
                "categories": [],
                "_source": "openvsx",
            }

            files = ext.get("files", {})
            if "icon" in files:
                info["iconUrl"] = files["icon"]
            if "download" in files:
                info["downloadUrl"] = files["download"]

            if not info["downloadUrl"] and info["namespace"] and info["name"] and info["version"]:
                info["downloadUrl"] = (
                    f"{OPENVSX_API}/{info['namespace']}/{info['name']}/{info['version']}/file/"
                    f"{info['namespace']}.{info['name']}-{info['version']}.vsix"
                )

            results.append(info)

        return results

    except Exception as e:
        print(f"[ExtensionManager] Open VSX search error: {e}")
        return []


def search_extensions(query: str, max_results: int = 20) -> list[dict]:
    """Search VS Code Marketplace for extensions.
    
    Uses the official VS Code Marketplace API (fast, reliable, has everything).
    Returns list of dicts with:
        name, namespace, displayName, description, version, iconUrl, downloadUrl,
        downloadCount, averageRating, categories
    """
    # Use VS Code Marketplace directly — it's fast and has all extensions
    results = _search_vscode_marketplace(query, max_results)
    
    # Sort by download count (most popular first)
    results.sort(key=lambda x: x.get("downloadCount", 0), reverse=True)
    
    return results[:max_results]


def get_extension_detail(namespace: str, name: str) -> Optional[dict]:
    """Get detailed info about a specific extension from Open VSX."""
    try:
        url = f"{OPENVSX_API}/{namespace}/{name}"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        files = data.get("files", {})
        return {
            "name": data.get("name", ""),
            "namespace": data.get("namespace", ""),
            "displayName": data.get("displayName", ""),
            "description": data.get("description", ""),
            "version": data.get("version", ""),
            "iconUrl": files.get("icon", ""),
            "downloadUrl": files.get("download", ""),
            "categories": data.get("categories", []),
            "tags": data.get("tags", []),
            "license": data.get("license", ""),
            "repository": data.get("repository", ""),
            "engines": data.get("engines", {}),
        }
    except Exception as e:
        print(f"[ExtensionManager] Detail error: {e}")
        return None


# ══════════════════════════════════════════════════════════════
# DOWNLOAD & INSTALL
# ══════════════════════════════════════════════════════════════
def download_vsix(download_url: str, ext_id: str, progress_callback=None) -> Optional[Path]:
    """Download a .vsix file. Returns path to downloaded file or None."""
    if not download_url:
        return None

    cache = _cache_dir()
    filename = f"{ext_id}.vsix"
    dest = cache / filename

    try:
        req = urllib.request.Request(download_url)

        def _report(block_num, block_size, total_size):
            if progress_callback and total_size > 0:
                progress_callback(min(100, int(block_num * block_size * 100 / total_size)))

        urllib.request.urlretrieve(download_url, str(dest), reporthook=_report)
        return dest

    except Exception as e:
        print(f"[ExtensionManager] Download error: {e}")
        return None


def install_extension(vsix_path: Path, ext_id: str) -> Optional[Path]:
    """Extract a .vsix (ZIP) to the extensions directory.
    
    VSIX structure:
        [Content_Types].xml
        extension.vsixmanifest
        extension/
            package.json
            themes/
            syntaxes/
            ...
    """
    ext_dir = _extensions_dir() / ext_id

    # Remove old version if exists
    if ext_dir.exists():
        shutil.rmtree(ext_dir, ignore_errors=True)

    try:
        with zipfile.ZipFile(vsix_path, 'r') as zf:
            # Extract only the extension/ subtree
            for member in zf.namelist():
                if member.startswith("extension/"):
                    # Strip the "extension/" prefix
                    rel_path = member[len("extension/"):]
                    if not rel_path:
                        continue

                    target = ext_dir / rel_path
                    if member.endswith("/"):
                        target.mkdir(parents=True, exist_ok=True)
                    else:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with zf.open(member) as src, open(target, 'wb') as dst:
                            dst.write(src.read())

        return ext_dir

    except Exception as e:
        print(f"[ExtensionManager] Install error: {e}")
        return None


def uninstall_extension(ext_id: str) -> bool:
    """Remove an installed extension."""
    ext_dir = _extensions_dir() / ext_id
    if ext_dir.exists():
        shutil.rmtree(ext_dir, ignore_errors=True)
        return True
    return False


def list_installed() -> list[dict]:
    """List all installed extensions with their metadata."""
    extensions = []
    ext_base = _extensions_dir()

    for entry in ext_base.iterdir():
        if entry.is_dir() and entry.name != ".cache":
            pkg_json = entry / "package.json"
            if pkg_json.exists():
                try:
                    with open(pkg_json, 'r', encoding='utf-8') as f:
                        pkg = json.load(f)

                    extensions.append({
                        "id": entry.name,
                        "path": str(entry),
                        "name": pkg.get("name", entry.name),
                        "displayName": pkg.get("displayName", entry.name),
                        "description": pkg.get("description", ""),
                        "version": pkg.get("version", ""),
                        "publisher": pkg.get("publisher", ""),
                        "categories": pkg.get("categories", []),
                        "contributes": pkg.get("contributes", {}),
                    })
                except Exception:
                    pass

    return extensions


# ══════════════════════════════════════════════════════════════
# THEME PARSING — VS Code theme JSON → Lutervyn color dict
# ══════════════════════════════════════════════════════════════

# Map TextMate scopes → our Lutervyn theme keys
SCOPE_TO_THEME_KEY = {
    # Keywords
    "keyword": "syntax_keyword",
    "keyword.control": "syntax_keyword",
    "keyword.control.import": "syntax_keyword",
    "keyword.control.flow": "syntax_keyword",
    "keyword.operator": "syntax_operator",
    "keyword.operator.logical": "syntax_keyword",
    "keyword.operator.logical.python": "syntax_keyword",

    # Storage (def, class, function, var, let, const)
    "storage": "syntax_keyword2",
    "storage.type": "syntax_keyword2",
    "storage.modifier": "syntax_keyword2",
    "storage.type.function": "syntax_keyword2",
    "storage.type.class": "syntax_keyword2",

    # Strings
    "string": "syntax_string",
    "string.quoted": "syntax_string",
    "string.quoted.single": "syntax_string",
    "string.quoted.double": "syntax_string",
    "string.template": "syntax_string",
    "string.regexp": "syntax_string",

    # Numbers
    "constant.numeric": "syntax_number",
    "constant.numeric.integer": "syntax_number",
    "constant.numeric.float": "syntax_number",
    "constant.numeric.hex": "syntax_number",

    # Constants (True, False, None, null, undefined)
    "constant.language": "syntax_keyword2",
    "constant.language.python": "syntax_keyword2",
    "constant.language.boolean": "syntax_keyword2",
    "constant.language.null": "syntax_keyword2",

    # Comments
    "comment": "syntax_comment",
    "comment.line": "syntax_comment",
    "comment.block": "syntax_comment",
    "comment.documentation": "syntax_comment",

    # Functions
    "entity.name.function": "syntax_function",
    "entity.name.function.python": "syntax_function",
    "support.function": "syntax_function",
    "meta.function-call": "syntax_function",

    # Classes / Types
    "entity.name.class": "syntax_class",
    "entity.name.type": "syntax_class",
    "entity.name.type.class": "syntax_class",
    "support.class": "syntax_class",
    "support.type": "syntax_class",
    "entity.other.inherited-class": "syntax_class",

    # Variables
    "variable": "syntax_variable",
    "variable.other": "syntax_variable",
    "variable.parameter": "syntax_variable",
    "variable.other.readwrite": "syntax_variable",

    # Variable.language (self, this, cls)
    "variable.language": "syntax_self",
    "variable.language.self": "syntax_self",
    "variable.language.this": "syntax_self",
    "variable.language.special.self": "syntax_self",

    # Decorators
    "entity.name.function.decorator": "syntax_decorator",
    "meta.decorator": "syntax_decorator",
    "punctuation.definition.decorator": "syntax_decorator",

    # Built-in types/functions
    "support.type.python": "syntax_builtin",
    "support.function.builtin": "syntax_builtin",

    # Operators
    "keyword.operator.assignment": "syntax_operator",
    "keyword.operator.comparison": "syntax_operator",
    "keyword.operator.arithmetic": "syntax_operator",

    # Punctuation (generally not colored specially, but captured for completeness)
    "punctuation": "syntax_operator",

    # Editor colors (from "colors" section of theme JSON)
    "editor.background": "editor_bg",
    "editor.foreground": "editor_fg",
    "editor.lineHighlightBackground": "editor_line_highlight",
    "editor.selectionBackground": "editor_selection",
    "editorLineNumber.foreground": "editor_gutter_fg",
    "editorLineNumber.activeForeground": "editor_gutter_fg",
    "activityBar.background": "activitybar_bg",
    "activityBar.foreground": "activitybar_active_fg",
    "sideBar.background": "sidebar_bg",
    "sideBar.foreground": "sidebar_fg",
    "tab.activeBackground": "tab_active_bg",
    "tab.activeForeground": "tab_active_fg",
    "tab.inactiveBackground": "tab_inactive_bg",
    "tab.inactiveForeground": "tab_inactive_fg",
    "statusBar.background": "statusbar_bg",
    "statusBar.foreground": "statusbar_fg",
    "terminal.background": "terminal_bg",
    "terminal.foreground": "terminal_fg",
    "panel.background": "panel_bg",
    "panelTitle.activeForeground": "panel_fg",
    "titleBar.activeBackground": "titlebar_bg",
    "titleBar.activeForeground": "titlebar_fg",
    "input.background": "input_bg",
    "input.foreground": "input_fg",
    "input.border": "input_border",
    "focusBorder": "input_border_focus",
    "minimap.background": "minimap_bg",
}


def parse_vscode_theme(theme_json_path: str) -> dict:
    """Parse a VS Code theme JSON file and return a Lutervyn-compatible color dict.
    
    VS Code themes have:
        {
            "name": "...",
            "type": "dark" | "light",
            "colors": { "editor.background": "#1E1E1E", ... },
            "tokenColors": [
                {
                    "name": "Comments",
                    "scope": "comment" | ["comment", "comment.block"],
                    "settings": { "foreground": "#6A9955", "fontStyle": "italic" }
                },
                ...
            ]
        }
    """
    with open(theme_json_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # VS Code theme files can have // comments and trailing commas
    # Strip them for valid JSON
    content = _strip_json_comments(content)

    try:
        theme_data = json.loads(content)
    except json.JSONDecodeError as e:
        print(f"[ThemeParser] JSON parse error in {theme_json_path}: {e}")
        return {}

    result = {}
    theme_type = theme_data.get("type", "dark")
    result["_type"] = theme_type
    result["_name"] = theme_data.get("name", "Unknown")

    # 1. Parse "colors" section → editor/UI colors
    colors = theme_data.get("colors", {})
    for vscode_key, lutervyn_key in SCOPE_TO_THEME_KEY.items():
        if vscode_key in colors:
            result[lutervyn_key] = colors[vscode_key]

    # 2. Parse "tokenColors" section → syntax colors
    token_colors = theme_data.get("tokenColors", [])
    for rule in token_colors:
        scopes = rule.get("scope", [])
        settings = rule.get("settings", {})
        fg = settings.get("foreground")

        if not fg:
            continue

        # scope can be a string or list
        if isinstance(scopes, str):
            scopes = [s.strip() for s in scopes.split(",")]

        for scope in scopes:
            scope = scope.strip()
            # Try exact match first, then prefix match
            if scope in SCOPE_TO_THEME_KEY:
                result[SCOPE_TO_THEME_KEY[scope]] = fg
            else:
                # Try matching by prefix (e.g., "keyword.control.python" → "keyword.control")
                parts = scope.split(".")
                for i in range(len(parts), 0, -1):
                    prefix = ".".join(parts[:i])
                    if prefix in SCOPE_TO_THEME_KEY:
                        key = SCOPE_TO_THEME_KEY[prefix]
                        # Don't overwrite if we already have a more specific match
                        if key not in result:
                            result[key] = fg
                        break

    return result


def get_themes_from_extension(ext_dir: str) -> list[dict]:
    """Extract all themes contributed by an extension.
    
    Reads package.json → contributes.themes, then parses each theme file.
    Returns list of {label, path, uiTheme, colors}.
    """
    pkg_path = os.path.join(ext_dir, "package.json")
    if not os.path.exists(pkg_path):
        return []

    try:
        with open(pkg_path, 'r', encoding='utf-8') as f:
            pkg = json.load(f)
    except Exception:
        return []

    contributed_themes = pkg.get("contributes", {}).get("themes", [])
    themes = []

    for theme_entry in contributed_themes:
        label = theme_entry.get("label", "Unknown")
        theme_path = theme_entry.get("path", "")
        ui_theme = theme_entry.get("uiTheme", "vs-dark")

        # Resolve relative path
        full_path = os.path.normpath(os.path.join(ext_dir, theme_path))

        if not os.path.exists(full_path):
            continue

        colors = parse_vscode_theme(full_path)
        colors["_label"] = label
        colors["_uiTheme"] = ui_theme

        themes.append({
            "label": label,
            "path": full_path,
            "uiTheme": ui_theme,
            "colors": colors,
        })

    return themes


def get_all_available_themes() -> list[dict]:
    """Scan all installed extensions and collect available themes."""
    all_themes = []
    for ext_info in list_installed():
        ext_path = ext_info["path"]
        themes = get_themes_from_extension(ext_path)
        for theme in themes:
            theme["extension_id"] = ext_info["id"]
            theme["extension_name"] = ext_info.get("displayName", ext_info["name"])
        all_themes.extend(themes)
    return all_themes


# ══════════════════════════════════════════════════════════════
# APPLY THEME to QScintilla editor
# ══════════════════════════════════════════════════════════════
def apply_vscode_theme_to_editor(editor, theme_colors: dict) -> None:
    """Apply parsed VS Code theme colors to a QScintilla editor widget.
    
    Only changes SYNTAX text colors (keywords, strings, comments, etc.).
    Does NOT touch background, selection, gutter, or any editor chrome.
    """
    from PyQt6.QtGui import QColor
    from PyQt6.Qsci import QsciLexerPython, QsciScintilla

    lexer = editor.lexer()

    if lexer is None:
        return

    if not isinstance(lexer, QsciLexerPython):
        # Non-Python lexer — nothing to change (no syntax mapping)
        return

    # ── Python syntax colors ONLY ──
    color_map = {
        QsciLexerPython.Comment: ("syntax_comment", "#6A9955"),
        QsciLexerPython.CommentBlock: ("syntax_comment", "#6A9955"),
        QsciLexerPython.Number: ("syntax_number", "#B5CEA8"),
        QsciLexerPython.DoubleQuotedString: ("syntax_string", "#CE9178"),
        QsciLexerPython.SingleQuotedString: ("syntax_string", "#CE9178"),
        QsciLexerPython.TripleSingleQuotedString: ("syntax_string", "#CE9178"),
        QsciLexerPython.TripleDoubleQuotedString: ("syntax_string", "#CE9178"),
        QsciLexerPython.Keyword: ("syntax_keyword", "#C586C0"),
        QsciLexerPython.ClassName: ("syntax_class", "#4EC9B0"),
        QsciLexerPython.FunctionMethodName: ("syntax_function", "#DCDCAA"),
        QsciLexerPython.Operator: ("syntax_operator", "#D4D4D4"),
        QsciLexerPython.Identifier: ("syntax_variable", "#9CDCFE"),
        QsciLexerPython.UnclosedString: ("syntax_string", "#CE9178"),
        QsciLexerPython.HighlightedIdentifier: ("syntax_keyword2", "#569CD6"),
        QsciLexerPython.Decorator: ("syntax_decorator", "#DCDCAA"),
    }

    # F-string styles
    for fstyle in [QsciLexerPython.DoubleQuotedFString,
                   QsciLexerPython.SingleQuotedFString,
                   QsciLexerPython.TripleSingleQuotedFString,
                   QsciLexerPython.TripleDoubleQuotedFString]:
        color_map[fstyle] = ("syntax_string", "#CE9178")

    for style_id, (key, fallback) in color_map.items():
        color = theme_colors.get(key, fallback)
        lexer.setColor(QColor(color), style_id)

    # Force QScintilla to re-render all text with new colors
    editor.SendScintilla(QsciScintilla.SCI_COLOURISE, 0, -1)


def merge_theme_colors(base_theme: dict, vscode_colors: dict) -> dict:
    """Merge parsed VS Code colors into the base Lutervyn theme.
    
    Only overrides keys that exist in vscode_colors.
    Preserves all base_theme keys that aren't in the VS Code theme.
    """
    merged = dict(base_theme)
    for key, value in vscode_colors.items():
        if key.startswith("_"):
            continue  # Skip metadata keys
        if key in merged:
            merged[key] = value
    return merged


# ══════════════════════════════════════════════════════════════
# JSON COMMENT STRIPPER
# ══════════════════════════════════════════════════════════════
def _strip_json_comments(text: str) -> str:
    """Remove // and /* */ comments from JSON-with-comments (JSONC).
    
    VS Code theme files use JSONC format which allows comments.
    """
    result = []
    i = 0
    in_string = False
    string_char = None

    while i < len(text):
        c = text[i]

        # Handle strings
        if in_string:
            result.append(c)
            if c == '\\' and i + 1 < len(text):
                result.append(text[i + 1])
                i += 2
                continue
            if c == string_char:
                in_string = False
            i += 1
            continue

        # Check for string start
        if c in ('"', "'"):
            in_string = True
            string_char = c
            result.append(c)
            i += 1
            continue

        # Check for comments
        if c == '/' and i + 1 < len(text):
            next_c = text[i + 1]

            # Line comment //
            if next_c == '/':
                # Skip until end of line
                while i < len(text) and text[i] != '\n':
                    i += 1
                continue

            # Block comment /* */
            if next_c == '*':
                i += 2
                while i < len(text) - 1:
                    if text[i] == '*' and text[i + 1] == '/':
                        i += 2
                        break
                    i += 1
                else:
                    i = len(text)
                continue

        result.append(c)
        i += 1

    # Also handle trailing commas (common in VS Code JSON)
    text = "".join(result)
    # Remove trailing commas before } or ]
    import re
    text = re.sub(r',\s*([\]}])', r'\1', text)

    return text


# ══════════════════════════════════════════════════════════════
# ASYNC HELPERS (for UI thread safety)
# ══════════════════════════════════════════════════════════════
class ExtensionWorker(threading.Thread):
    """Background worker for downloading/installing extensions."""

    def __init__(self, action: str, callback=None, **kwargs):
        super().__init__(daemon=True)
        self.action = action
        self.callback = callback
        self.kwargs = kwargs
        self.result = None
        self.error = None

    def run(self):
        try:
            if self.action == "search":
                self.result = search_extensions(
                    self.kwargs.get("query", ""),
                    self.kwargs.get("max_results", 20)
                )
            elif self.action == "download_install":
                url = self.kwargs.get("download_url", "")
                ext_id = self.kwargs.get("ext_id", "")
                progress = self.kwargs.get("progress_callback")

                vsix_path = download_vsix(url, ext_id, progress)
                if vsix_path:
                    ext_dir = install_extension(vsix_path, ext_id)
                    self.result = str(ext_dir) if ext_dir else None
                    # Clean up vsix
                    try:
                        vsix_path.unlink()
                    except Exception:
                        pass
                else:
                    self.error = "Download failed"

            elif self.action == "uninstall":
                self.result = uninstall_extension(self.kwargs.get("ext_id", ""))

        except Exception as e:
            self.error = str(e)

        if self.callback:
            self.callback(self.result, self.error)
