"""
Wakka — Cache Manager
Handles pacman and yay cache cleanup, both manual and scheduled.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, QProcess, pyqtSignal, QProcessEnvironment


PACMAN_CACHE = Path("/var/cache/pacman/pkg/")
YAY_CACHE = Path.home() / ".cache" / "yay"
PARU_CACHE = Path.home() / ".cache" / "paru"


def _dir_size(path: Path) -> int:
    """Return total size in bytes of a directory tree."""
    if not path.exists():
        return 0
    total = 0
    for p in path.rglob("*"):
        if p.is_file():
            try:
                total += p.stat().st_size
            except OSError:
                pass
    return total


def fmt_size(size_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


class CacheInfo:
    def __init__(self):
        self.pacman_size: int = _dir_size(PACMAN_CACHE)
        self.yay_size: int = _dir_size(YAY_CACHE)
        self.paru_size: int = _dir_size(PARU_CACHE)

    @property
    def total_size(self) -> int:
        return self.pacman_size + self.yay_size + self.paru_size

    @property
    def pacman_size_str(self) -> str:
        return fmt_size(self.pacman_size)

    @property
    def yay_size_str(self) -> str:
        return fmt_size(self.yay_size)

    @property
    def total_size_str(self) -> str:
        return fmt_size(self.total_size)


class CacheManager(QObject):
    output_line = pyqtSignal(str, bool)       # (text, is_error)
    operation_finished = pyqtSignal(bool, str)
    cache_info_ready = pyqtSignal(object)     # CacheInfo

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pkexec = shutil.which("pkexec")
        self._paccache = shutil.which("paccache")
        self._process: Optional[QProcess] = None

    @property
    def is_busy(self) -> bool:
        return self._process is not None and self._process.state() != QProcess.ProcessState.NotRunning

    def get_cache_info(self):
        """Emit current cache size info (runs in main thread, fast)."""
        info = CacheInfo()
        self.cache_info_ready.emit(info)

    def clean_pacman_cache(self, keep: int = 2):
        """
        Clean pacman cache keeping `keep` versions per package.
        Requires paccache (pacman-contrib) + pkexec.
        """
        if not self._paccache:
            self.operation_finished.emit(
                False, "paccache no está instalado (instala pacman-contrib)"
            )
            return
        self._run_privileged(
            [self._paccache, "-r", f"-k{keep}"],
            label="Limpieza caché pacman",
            ignore_codes=[0, 1]
        )

    def clean_pacman_uninstalled(self):
        """Remove all cached packages that are not currently installed."""
        if not self._paccache:
            self.operation_finished.emit(False, "paccache no disponible")
            return
        self._run_privileged(
            [self._paccache, "-ruk0"],
            label="Eliminar caché desinstalados",
            ignore_codes=[0, 1]
        )

    def clean_yay_cache(self):
        """Remove yay's build cache (user-owned, no pkexec needed)."""
        try:
            for cache_dir in (YAY_CACHE, PARU_CACHE):
                if cache_dir.exists():
                    shutil.rmtree(cache_dir, ignore_errors=True)
                    self.output_line.emit(f"Eliminado: {cache_dir}\n", False)
            self.operation_finished.emit(True, "Caché de AUR eliminado")
        except Exception as e:
            self.operation_finished.emit(False, str(e))

    def clean_orphans(self):
        """Remove orphan packages (pacman -Qdtq | pkexec pacman -Rns -)."""
        try:
            result = subprocess.run(
                ["pacman", "-Qdtq"], capture_output=True, text=True
            )
            orphans = result.stdout.strip().split()
            if not orphans:
                self.output_line.emit("No hay paquetes huérfanos.\n", False)
                self.operation_finished.emit(True, "Sin huérfanos")
                return
            self._run_privileged(
                ["pacman", "-Rns", "--noconfirm"] + orphans,
                label=f"Eliminar {len(orphans)} paquete(s) huérfano(s)",
            )
        except Exception as e:
            self.operation_finished.emit(False, str(e))

    # ─── Internal ─────────────────────────────────────────────────────────────

    def _run_privileged(self, cmd: list[str], *, label: str, ignore_codes: list[int] = None):
        if self._process and self._process.state() != QProcess.ProcessState.NotRunning:
            return

        ignore_codes = ignore_codes or [0]

        # Use sudo -A with our askpass
        askpass_path = Path(__file__).resolve().parent / "askpass.py"
        full_cmd = ["sudo", "-A"] + cmd

        process = QProcess(self)
        self._process = process
        
        env = QProcessEnvironment.systemEnvironment()
        env.insert("SUDO_ASKPASS", str(askpass_path))
        display = os.getenv("DISPLAY")
        if display is not None:
            env.insert("DISPLAY", display)
        process.setProcessEnvironment(env)
        
        process.setProgram(full_cmd[0])
        process.setArguments(full_cmd[1:])
        self.output_line.emit(f"→ {label}\n", False)

        def on_out():
            data = bytes(process.readAllStandardOutput()).decode("utf-8", "replace")
            for line in data.splitlines(keepends=True):
                self.output_line.emit(line, False)

        def on_err():
            data = bytes(process.readAllStandardError()).decode("utf-8", "replace")
            for line in data.splitlines(keepends=True):
                self.output_line.emit(line, True)

        def on_done(code, _):
            ok = code in ignore_codes
            self.operation_finished.emit(ok, "OK" if ok else f"Error {code}")
            if self._process == process:
                self._process = None

        process.readyReadStandardOutput.connect(on_out)
        process.readyReadStandardError.connect(on_err)
        process.finished.connect(on_done)
        process.start()
