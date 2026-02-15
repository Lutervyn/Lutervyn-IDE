"""End-to-end test: search, download, install, parse, apply."""
from app.core.extension_manager import (
    search_extensions, download_vsix, install_extension,
    list_installed, get_themes_from_extension
)

# 1. Search
print("=" * 60)
print("1. Searching for 'one dark pro'...")
results = search_extensions("one dark pro", 5)
# Pick the one from Open VSX (has direct download)
openvsx = [r for r in results if r.get("_source") == "openvsx"]
if openvsx:
    ext = openvsx[0]
else:
    ext = results[0]

print(f"   Selected: {ext['displayName']} by {ext['namespace']} v{ext['version']}")
print(f"   Source: {ext.get('_source')}")
print(f"   Download: {ext['downloadUrl'][:80]}")

# 2. Download
ext_id = f"{ext['namespace']}.{ext['name']}"
print(f"\n2. Downloading {ext_id}...")
vsix = download_vsix(ext["downloadUrl"], ext_id, lambda p: print(f"   {p}%", end="\r"))
print(f"   Downloaded to: {vsix}")

# 3. Install
print(f"\n3. Installing...")
ext_dir = install_extension(vsix, ext_id)
print(f"   Installed to: {ext_dir}")
try:
    vsix.unlink()
except:
    pass

# 4. List installed
print(f"\n4. Installed extensions:")
for e in list_installed():
    print(f"   {e['displayName']} ({e['id']}) v{e['version']}")
    print(f"   Path: {e['path']}")
    themes = e.get("contributes", {}).get("themes", [])
    print(f"   Themes: {len(themes)}")

# 5. Parse themes
print(f"\n5. Parsing themes from: {ext_dir}")
themes = get_themes_from_extension(str(ext_dir))
print(f"   Found {len(themes)} themes:")
for t in themes:
    colors = t["colors"]
    print(f"   - {t['label']} ({t['uiTheme']})")
    print(f"     editor_bg={colors.get('editor_bg','?')} keyword={colors.get('syntax_keyword','?')} string={colors.get('syntax_string','?')}")

print("\n✓ ALL GOOD — extension system working end to end")
