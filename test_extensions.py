"""Test the extension manager search + download."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.extension_manager import (
    search_extensions, _extensions_dir, download_vsix,
    install_extension, list_installed, get_themes_from_extension,
    parse_vscode_theme
)

print(f"Extensions dir: {_extensions_dir()}")
print()

# Search for theme extensions
print("Searching Open VSX for 'dark theme'...")
results = search_extensions("dark theme", 10)
print(f"Found {len(results)} results:")
for r in results:
    print(f"  {r['displayName']} by {r['namespace']} v{r['version']}")
    print(f"    {r['description'][:80]}")
    print(f"    download: {r['downloadUrl'][:80] if r['downloadUrl'] else 'N/A'}")
    print()

print()
print("Searching for 'one dark pro'...")
results2 = search_extensions("one dark pro", 5)
print(f"Found {len(results2)} results:")
for r in results2:
    print(f"  {r['displayName']} by {r['namespace']} v{r['version']}")
    print(f"    download: {r['downloadUrl'][:80] if r['downloadUrl'] else 'N/A'}")
    print()

# Try to download and install the first theme if available
if results2:
    ext = results2[0]
    ext_id = f"{ext['namespace']}.{ext['name']}"
    print(f"Downloading {ext_id}...")
    
    def progress(pct):
        print(f"  {pct}%", end="\r")
    
    vsix = download_vsix(ext['downloadUrl'], ext_id, progress)
    if vsix:
        print(f"\nDownloaded to: {vsix}")
        print(f"Installing...")
        ext_dir = install_extension(vsix, ext_id)
        if ext_dir:
            print(f"Installed to: {ext_dir}")
            
            # List themes
            themes = get_themes_from_extension(str(ext_dir))
            print(f"Found {len(themes)} themes:")
            for t in themes:
                print(f"  - {t['label']} ({t['uiTheme']})")
                print(f"    Colors: {dict(list(t['colors'].items())[:5])}")
            
            # Clean up vsix
            try:
                vsix.unlink()
            except:
                pass
        else:
            print("Install failed!")
    else:
        print("Download failed!")

print()
print("Installed extensions:")
for ext in list_installed():
    print(f"  {ext['displayName']} v{ext['version']}")
    contributes = ext.get('contributes', {})
    themes_count = len(contributes.get('themes', []))
    print(f"    contributes {themes_count} theme(s)")
