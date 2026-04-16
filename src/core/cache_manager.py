"""
Wakka — Cache Manager
Handles pacman and yay cache cleanup.
"""
from __future__ import annotations
import shutil
import subprocess
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal

PACMAN_CACHE = Path("/var/cache/pacman/pkg/")
YAY_CACHE = Path.home() / ".cache" / "yay"

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

    @property
    def total_size(self) -> int:
        return self.pacman_size + self.yay_size

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
    cache_info_ready = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cache_helper = "/usr/bin/wakka-cache-helper"

    def get_cache_info(self):
        self.cache_info_ready.emit(CacheInfo())
        
    def get_cache_info_sync(self):
        return CacheInfo()

    def clean_pacman_cache(self, keep: int = 2) -> subprocess.Popen:
        return subprocess.Popen(
            ["pkexec", self._cache_helper, "clean-pacman-cache", str(keep)],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )

    def clean_pacman_uninstalled(self) -> subprocess.Popen:
        return subprocess.Popen(
            ["pkexec", self._cache_helper, "clean-pacman-uninstalled"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )

    def clean_yay_cache(self) -> subprocess.Popen:
        try:
            if YAY_CACHE.exists():
                shutil.rmtree(YAY_CACHE, ignore_errors=True)
            return subprocess.Popen(["echo", "Caché de compilación AUR eliminado satisfactoriamente."], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        except Exception as e:
            return subprocess.Popen(["echo", f"Error limpiando caché de AUR: {e}"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    def clean_orphans(self) -> subprocess.Popen:
        return subprocess.Popen(
            ["pkexec", self._cache_helper, "clean-orphans"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
