"""
Python Runner - Execute Python scripts and capture output.
"""

import sys
import os
from PyQt6.QtCore import QProcess, QObject, pyqtSignal


class PythonRunner(QObject):
    """Runs Python scripts in a subprocess and captures output."""

    output_received = pyqtSignal(str)
    error_received = pyqtSignal(str)
    finished = pyqtSignal(int, str)  # exit_code, status

    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = None

    def run_file(self, file_path: str, python_path: str = None,
                 working_dir: str = None, args: list[str] = None):
        """Run a Python file."""
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            self.stop()

        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
        self.process.readyReadStandardOutput.connect(self._on_stdout)
        self.process.readyReadStandardError.connect(self._on_stderr)
        self.process.finished.connect(self._on_finished)

        python = python_path or sys.executable
        if working_dir:
            self.process.setWorkingDirectory(working_dir)
        else:
            self.process.setWorkingDirectory(os.path.dirname(file_path))

        cmd_args = ["-u", file_path]  # -u for unbuffered output
        if args:
            cmd_args.extend(args)

        self.output_received.emit(f"▶ Running: {python} {file_path}\n")
        self.output_received.emit(f"{'─' * 50}\n")

        self.process.start(python, cmd_args)

    def run_code(self, code: str, python_path: str = None):
        """Run Python code string."""
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            self.stop()

        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
        self.process.readyReadStandardOutput.connect(self._on_stdout)
        self.process.readyReadStandardError.connect(self._on_stderr)
        self.process.finished.connect(self._on_finished)

        python = python_path or sys.executable
        self.process.start(python, ["-u", "-c", code])

    def stop(self):
        """Stop the running process."""
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            self.process.kill()
            self.process.waitForFinished(2000)

    def _on_stdout(self):
        data = self.process.readAllStandardOutput().data()
        text = data.decode("utf-8", errors="replace")
        self.output_received.emit(text)

    def _on_stderr(self):
        data = self.process.readAllStandardError().data()
        text = data.decode("utf-8", errors="replace")
        self.error_received.emit(text)

    def _on_finished(self, exit_code, exit_status):
        status = "finished" if exit_code == 0 else "error"
        self.output_received.emit(f"\n{'─' * 50}\n")
        self.output_received.emit(
            f"Process {status} with exit code {exit_code}\n\n")
        self.finished.emit(exit_code, status)

    def is_running(self) -> bool:
        return (self.process is not None and
                self.process.state() == QProcess.ProcessState.Running)
