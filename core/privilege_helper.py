#!/usr/bin/env python3
"""
Wakka — Privilege Helper
Centralized sudo/pkexec execution with SUDO_ASKPASS integration.
"""
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Callable
from PyQt6.QtCore import QObject, QProcess, QProcessEnvironment, pyqtSignal

ASKPASS_PATH = Path(__file__).parent / "askpass.py"

class PrivilegeHelper(QObject):
    """Unified privileged command execution for Wakka."""

    output_line = pyqtSignal(str, bool)  # (text, is_error)
    operation_finished = pyqtSignal(bool, str, str)  # (success, message, operation)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sudo = shutil.which("sudo")
        self._pkexec = shutil.which("pkexec")
        self._process: Optional[QProcess] = None

    @property
    def is_busy(self) -> bool:
        return self._process is not None and self._process.state() != QProcess.ProcessState.NotRunning

    def _build_env(self) -> dict[str, str]:
        """Build environment with SUDO_ASKPASS, DISPLAY, and LC_ALL."""
        env = os.environ.copy()
        env["SUDO_ASKPASS"] = str(ASKPASS_PATH)

        display = os.getenv("DISPLAY")
        if display:
            env["DISPLAY"] = display

        env.setdefault("LC_ALL", "es_ES.UTF-8")
        return env

    def _build_qprocess_env(self) -> QProcessEnvironment:
        """Build QProcessEnvironment with same settings."""
        env = QProcessEnvironment.systemEnvironment()
        env.insert("SUDO_ASKPASS", str(ASKPASS_PATH))

        display = os.getenv("DISPLAY")
        if display:
            env.insert("DISPLAY", display)

        env.insert("LC_ALL", "es_ES.UTF-8")
        return env

    # ─── Synchronous (subprocess) ─────────────────────────────────────

    def run_sync(self, cmd: list[str], timeout: int = 60) -> tuple[bool, str, str]:
        """
        Run command with sudo -A synchronously.
        Returns: (success, stdout, stderr)
        """
        if not self._sudo:
            return False, "", "sudo no encontrado"

        try:
            result = subprocess.run(
                [self._sudo, "-A"] + cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=self._build_env()
            )
            return result.returncode == 0, result.stdout, result.stderr.strip()
        except subprocess.TimeoutExpired:
            return False, "", f"Timeout ({timeout}s)"
        except Exception as e:
            return False, "", str(e)

    def run_sync_pkexec(self, cmd: list[str], timeout: int = 60) -> tuple[bool, str, str]:
        """Run command with pkexec synchronously (alternative to sudo)."""
        if not self._pkexec:
            return False, "", "pkexec no encontrado"

        try:
            result = subprocess.run(
                [self._pkexec] + cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=self._build_env()
            )
            return result.returncode == 0, result.stdout, result.stderr.strip()
        except Exception as e:
            return False, "", str(e)

    # ─── Asynchronous (QProcess) ──────────────────────────────────────

    def run_async(self, cmd: list[str], operation: str = "",
                  ignore_codes: list[int] = None, silent: bool = False):
        """
        Run command with sudo -A asynchronously via QProcess.
        Streams output via output_line signal.
        """
        if self.is_busy:
            if not silent:
                self.output_line.emit("[wakka] Operación en progreso...\n", True)
            return

        if not self._sudo:
            self.operation_finished.emit(False, "sudo no encontrado", operation)
            return

        ignore_codes = ignore_codes or [0]
        process = QProcess(self)
        self._process = process

        process.setProcessEnvironment(self._build_qprocess_env())
        process.setProgram(self._sudo)
        process.setArguments(["-A"] + cmd)

        stdout_acc, stderr_acc = [], []

        def on_stdout():
            try:
                data = bytes(process.readAllStandardOutput()).decode("utf-8", errors="replace")
                stdout_acc.append(data)
                if not silent:
                    for line in data.splitlines(keepends=True):
                        self.output_line.emit(line, False)
            except RuntimeError:
                pass

        def on_stderr():
            try:
                data = bytes(process.readAllStandardError()).decode("utf-8", errors="replace")
                stderr_acc.append(data)
                if not silent:
                    for line in data.splitlines(keepends=True):
                        self.output_line.emit(line, True)
            except RuntimeError:
                pass

        def on_finished(exit_code, _):
            try:
                success = exit_code in ignore_codes
                msg = "OK" if success else f"Error (código {exit_code})"
                self.operation_finished.emit(success, msg, operation)
                if self._process == process:
                    self._process = None
            except RuntimeError:
                pass

        process.readyReadStandardOutput.connect(on_stdout)
        process.readyReadStandardError.connect(on_stderr)
        process.finished.connect(on_finished)
        process.start()

    def cancel(self):
        """Terminate current async operation."""
        if self._process and self._process.state() != QProcess.ProcessState.NotRunning:
            self._process.terminate()
            self._process.waitForFinished(3000)
            if self._process.state() != QProcess.ProcessState.NotRunning:
                self._process.kill()