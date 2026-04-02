"""
Wakka — Cache Manager
Handles pacman and yay cache cleanup, both manual and scheduled.
"""
from __future__ import annotations
import shutil
from pathlib import Path
from typing import Optional
from PyQt6.QtCore import QObject, pyqtSignal
from .privilege_helper import PrivilegeHelper

PACMAN_CACHE = Path("/var/cache/pacman/pkg/")
YAY_CACHE = Path.home() / ".cache" / "yay"
PARU_CACHE = Path.home() / ".cache" / "paru"

def _dir_size(path: Path) -> int:
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
    output_line = pyqtSignal(str, bool)
    operation_finished = pyqtSignal(bool, str)
    cache_info_ready = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.priv = PrivilegeHelper(parent)
        self.priv.output_line.connect(self.output_line)
        self.priv.operation_finished.connect(self._on_priv_finished)
        self._paccache = shutil.which("paccache")

    def _on_priv_finished(self, success: bool, msg: str, operation: str):
        self.operation_finished.emit(success, msg)

    @property
    def is_busy(self) -> bool:
        return self.priv.is_busy

    def get_cache_info(self):
        info = CacheInfo()
        self.cache_info_ready.emit(info)

    def clean_pacman_cache(self, keep: int = 2):
        if not self._paccache:
            self.operation_finished.emit(False, "paccache no está instalado (instala pacman-contrib)")
            return
        self.priv.run_async(
            [self._paccache, "-r", f"-k{keep}"],
            operation="Limpieza caché pacman",
            ignore_codes=[0, 1]
        )

    def clean_pacman_uninstalled(self):
        if not self._paccache:
            self.operation_finished.emit(False, "paccache no disponible")
            return
        self.priv.run_async(
            [self._paccache, "-ruk0"],
            operation="Eliminar caché desinstalados",
            ignore_codes=[0, 1]
        )

    def clean_yay_cache(self):
        try:
            for cache_dir in (YAY_CACHE, PARU_CACHE):
                if cache_dir.exists():
                    shutil.rmtree(cache_dir, ignore_errors=True)
                    self.output_line.emit(f"Eliminado: {cache_dir}\n", False)
            self.operation_finished.emit(True, "Caché de AUR eliminado")
        except Exception as e:
            self.operation_finished.emit(False, str(e))

    def clean_orphans(self):
        import subprocess
        try:
            result = subprocess.run(
                ["pacman", "-Qdtq"], capture_output=True, text=True
            )
            orphans = result.stdout.strip().split()
            if not orphans:
                self.output_line.emit("No hay paquetes huérfanos.\n", False)
                self.operation_finished.emit(True, "Sin huérfanos")
                return
            self.priv.run_async(
                ["pacman", "-Rns", "--noconfirm"] + orphans,
                operation=f"Eliminar {len(orphans)} paquete(s) huérfano(s)",
            )
        except Exception as e:
            self.operation_finished.emit(False, str(e))