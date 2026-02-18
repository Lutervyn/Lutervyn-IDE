"""
Lutervyn IDE

Run this file to start the IDE:
    python run_ide.py
"""

import sys
import os
import traceback

# Ensure the app package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def run():
    try:
        from PyQt6.QtWidgets import QApplication

        app = QApplication(sys.argv)
        app.setApplicationName("Lutervyn IDE")
        app.setOrganizationName("Lutervyn")

        from app.main_window import MainWindow
        window = MainWindow()

        # Start maximized (fill screen, don't cover taskbar)
        screen = app.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            window.setGeometry(avail)
            window.title_bar.set_maximized_state(True)

        window.show()

        # If a path was passed as argument, open it
        args = sys.argv[1:]
        if args:
            target = args[0]
            if os.path.isdir(target):
                window.cmd_open_folder_path(target)
            elif os.path.isfile(target):
                window._open_file(target)

        sys.exit(app.exec())
    except Exception:
        traceback.print_exc()
        input("Press Enter to exit...")


if __name__ == "__main__":
    run()
