"""
Lutervyn IDE - Windows Context Menu Integration
================================================
Adds "Open with Lutervyn IDE" to the Windows right-click context menu
for files, folders, and directory backgrounds.

Run as Administrator:
    python install_context_menu.py

To uninstall:
    python install_context_menu.py --uninstall
"""

import sys
import os
import winreg
import ctypes


def is_admin():
    """Check if running with Administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def get_paths():
    """Get the paths needed for registry entries."""
    ide_dir = os.path.dirname(os.path.abspath(__file__))
    run_script = os.path.join(ide_dir, "run_ide.py")
    icon_path = os.path.join(ide_dir, "assets", "logo.ico")

    # Fall back to png if ico doesn't exist
    if not os.path.exists(icon_path):
        icon_path = os.path.join(ide_dir, "assets", "logo.png")

    # Find python executable
    python_exe = sys.executable

    return python_exe, run_script, icon_path, ide_dir


def install_context_menu():
    """Add Lutervyn IDE to the Windows right-click context menu."""
    python_exe, run_script, icon_path, ide_dir = get_paths()

    menu_text = "Open with Lutervyn IDE"
    command = f'"{python_exe}" "{run_script}" "%V"'

    entries = [
        # 1) Right-click on a FILE → Open with Lutervyn IDE
        (winreg.HKEY_CLASSES_ROOT, r"*\shell\LutervynIDE"),
        # 2) Right-click on a FOLDER → Open with Lutervyn IDE
        (winreg.HKEY_CLASSES_ROOT, r"Directory\shell\LutervynIDE"),
        # 3) Right-click on FOLDER BACKGROUND → Open with Lutervyn IDE
        (winreg.HKEY_CLASSES_ROOT, r"Directory\Background\shell\LutervynIDE"),
    ]

    print("=" * 55)
    print("  Lutervyn IDE - Context Menu Installer")
    print("=" * 55)
    print()
    print(f"  Python:     {python_exe}")
    print(f"  IDE Script: {run_script}")
    print(f"  Icon:       {icon_path}")
    print()

    for root_key, key_path in entries:
        try:
            # Create the shell key
            key = winreg.CreateKey(root_key, key_path)
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, menu_text)
            winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, icon_path)
            winreg.CloseKey(key)

            # Create the command subkey
            cmd_key = winreg.CreateKey(root_key, key_path + r"\command")

            # For directory background, use %V to get current directory
            if "Background" in key_path:
                bg_command = f'"{python_exe}" "{run_script}" "%V"'
                winreg.SetValueEx(cmd_key, "", 0, winreg.REG_SZ, bg_command)
            else:
                winreg.SetValueEx(cmd_key, "", 0, winreg.REG_SZ, command)

            winreg.CloseKey(cmd_key)

            print(f"  [OK] {key_path}")

        except PermissionError:
            print(f"  [FAIL] {key_path} — Need Administrator privileges!")
            return False
        except Exception as e:
            print(f"  [FAIL] {key_path} — {e}")
            return False

    print()
    print("  Context menu installed successfully!")
    print("  Right-click any file or folder to see 'Open with Lutervyn IDE'")
    print()
    return True


def uninstall_context_menu():
    """Remove Lutervyn IDE from the Windows right-click context menu."""
    entries = [
        (winreg.HKEY_CLASSES_ROOT, r"*\shell\LutervynIDE"),
        (winreg.HKEY_CLASSES_ROOT, r"Directory\shell\LutervynIDE"),
        (winreg.HKEY_CLASSES_ROOT, r"Directory\Background\shell\LutervynIDE"),
    ]

    print("=" * 55)
    print("  Lutervyn IDE - Context Menu Uninstaller")
    print("=" * 55)
    print()

    for root_key, key_path in entries:
        try:
            # Delete command subkey first
            try:
                winreg.DeleteKey(root_key, key_path + r"\command")
            except FileNotFoundError:
                pass

            # Delete shell key
            winreg.DeleteKey(root_key, key_path)
            print(f"  [OK] Removed {key_path}")

        except FileNotFoundError:
            print(f"  [--] {key_path} (not found, skipping)")
        except PermissionError:
            print(f"  [FAIL] {key_path} — Need Administrator privileges!")
            return False
        except Exception as e:
            print(f"  [FAIL] {key_path} — {e}")
            return False

    print()
    print("  Context menu entries removed successfully!")
    print()
    return True


def main():
    # Check for admin
    if not is_admin():
        print()
        print("  ERROR: This script must be run as Administrator!")
        print()
        print("  How to run:")
        print("    1. Open PowerShell as Administrator")
        print("    2. cd to this folder")
        print("    3. Run: python install_context_menu.py")
        print()

        # Try to re-launch as admin
        try:
            answer = input("  Try to relaunch as Administrator? (y/n): ").strip().lower()
            if answer == "y":
                ctypes.windll.shell32.ShellExecuteW(
                    None, "runas", sys.executable,
                    f'"{os.path.abspath(__file__)}" {" ".join(sys.argv[1:])}',
                    None, 1
                )
                return
        except Exception:
            pass
        return

    # Check args
    if "--uninstall" in sys.argv or "--remove" in sys.argv:
        uninstall_context_menu()
    else:
        install_context_menu()

    input("  Press Enter to close...")


if __name__ == "__main__":
    main()
