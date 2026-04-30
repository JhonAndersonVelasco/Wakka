"""
Wakka — Cache Manager
Handles pacman and yay cache cleanup.
"""
from __future__ import annotations
import shutil
import subprocess
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal, QThread

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
        self.orphan_count: int = self._get_orphan_count()

    def _get_orphan_count(self) -> int:
        try:
            # pacman -Qdtq lists orphan packages
            result = subprocess.check_output(["pacman", "-Qdtq"], text=True, stderr=subprocess.DEVNULL)
            return len(result.strip().split("\n")) if result.strip() else 0
        except (subprocess.CalledProcessError, FileNotFoundError):
            return 0

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

class CacheInfoWorker(QObject):
    finished = pyqtSignal(object)

    def run(self):
        info = CacheInfo()
        self.finished.emit(info)

class CacheManager(QObject):
    cache_info_ready = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cache_helper = "/usr/bin/wakka-cache-helper"
        self._worker_thread = None

    def get_cache_info(self):
        """Inicia el cálculo de tamaños de caché en segundo plano"""
        try:
            if self._worker_thread and self._worker_thread.isRunning():
                return
        except RuntimeError:
            # El objeto C++ subyacente fue eliminado por deleteLater
            self._worker_thread = None

        self._worker_thread = QThread()
        self._worker = CacheInfoWorker()
        self._worker.moveToThread(self._worker_thread)
        
        self._worker_thread.started.connect(self._worker.run)
        self._worker.finished.connect(self.on_worker_finished)
        self._worker.finished.connect(self._worker_thread.quit)
        self._worker_thread.finished.connect(self._worker_thread.deleteLater)
        self._worker_thread.finished.connect(self._clear_worker_thread)
        
        self._worker_thread.start()

    def _clear_worker_thread(self):
        self._worker_thread = None

    def on_worker_finished(self, info):
        self.cache_info_ready.emit(info)

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

    def clean_all(self, keep: int = 2) -> subprocess.Popen:
        """Limpia todo: pacman (versiones y desinstalados), AUR y huérfanos"""
        # Primero limpiamos AUR en espacio de usuario
        try:
            if YAY_CACHE.exists():
                shutil.rmtree(YAY_CACHE, ignore_errors=True)
        except Exception:
            pass
        
        # Luego ejecutamos las limpiezas de root
        return subprocess.Popen(
            ["pkexec", self._cache_helper, "clean-all", str(keep)],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
