"""Patch main_window.py to add cmd_open_folder_path method."""
import os

filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app", "main_window.py")
content = open(filepath, "r", encoding="utf-8").read()

old = '''    def cmd_open_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Open Folder")
        if folder:
            self._current_folder = folder
            self.sidebar.set_root_folder(folder)
            self.sidebar.switch_view("explorer")
            self.setWindowTitle(f"{os.path.basename(folder)} - {self.APP_NAME}")

    def cmd_save(self):'''

new = '''    def cmd_open_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Open Folder")
        if folder:
            self.cmd_open_folder_path(folder)

    def cmd_open_folder_path(self, folder):
        """Open a folder directly by path (used by context menu integration)."""
        if folder and os.path.isdir(folder):
            self._current_folder = folder
            self.sidebar.set_root_folder(folder)
            self.sidebar.switch_view("explorer")
            self.setWindowTitle(f"{os.path.basename(folder)} - {self.APP_NAME}")

    def cmd_save(self):'''

if old in content:
    content = content.replace(old, new)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"PATCHED OK — {filepath}")
else:
    print("ERROR: Could not find the target string to replace")

# Verify
content2 = open(filepath, "r", encoding="utf-8").read()
print("Has cmd_open_folder_path:", "cmd_open_folder_path" in content2)
