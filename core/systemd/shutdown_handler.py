"""
Wakka — Systemd Shutdown Handler
Installs updates before shutdown using systemd inhibit locks + Plymouth/Qt overlay.
This module provides both the in-app handler AND the shutdown helper entry point.
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

# ─── Plymouth helpers ─────────────────────────────────────────────────────────

def plymouth_available() -> bool:
    """Check if Plymouth daemon is running."""
    if not shutil.which("plymouth"):
        return False
    try:
        result = subprocess.run(
            ["plymouth", "--ping"], capture_output=True, timeout=2
        )
        return result.returncode == 0
    except Exception:
        return False


def plymouth_msg(text: str):
    try:
        subprocess.run(["plymouth", "message", "--text", text], timeout=3)
    except Exception:
        pass


def plymouth_progress(pct: int):
    try:
        subprocess.run(
            ["plymouth", "system-update", f"--progress={pct}"], timeout=3
        )
    except Exception:
        pass


# ─── systemd Inhibit Lock ─────────────────────────────────────────────────────

class InhibitLock:
    """
    Acquires a systemd-logind shutdown inhibit lock via D-Bus.
    Context manager usage: `with InhibitLock() as lock: ...`
    """

    def __init__(self, reason: str = "Installing updates"):
        self._fd: Optional[int] = None
        self._reason = reason

    def acquire(self) -> bool:
        try:
            import dbus
            bus = dbus.SystemBus()
            logind = bus.get_object("org.freedesktop.login1",
                                    "/org/freedesktop/login1")
            iface = dbus.Interface(logind, "org.freedesktop.login1.Manager")
            fd = iface.Inhibit(
                "shutdown",
                "Wakka Package Manager",
                self._reason,
                "block",
            )
            self._fd = fd.take()
            return True
        except Exception as e:
            log.warning(f"Could not acquire inhibit lock: {e}")
            return False

    def release(self):
        if self._fd is not None:
            try:
                os.close(self._fd)
            except OSError:
                pass
            self._fd = None

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *_):
        self.release()


# ─── Shutdown Helper (runs as systemd service) ────────────────────────────────

def shutdown_main():
    """
    Entry point for wakka-shutdown-helper.
    Called by wakka-shutdown.service during system shutdown/reboot.
    This runs as the user (not root) but yay handles sudo internally.
    """
    logging.basicConfig(level=logging.INFO,
                        format="[wakka-shutdown] %(levelname)s %(message)s")

    # Import here to avoid heavy deps loading if not needed
    from ..config_manager import ConfigManager
    from ..package_manager import PackageManager

    config = ConfigManager()

    # Only run if feature is enabled
    if not config.get("shutdown_updates", False):
        log.info("Shutdown updates disabled, exiting.")
        sys.exit(0)

    # Check for pending updates
    pm = PackageManager()
    updates = pm.check_updates_sync()

    if not updates:
        log.info("No pending updates, exiting.")
        sys.exit(0)

    log.info(f"Found {len(updates)} pending update(s). Installing...")

    has_plym = plymouth_available()
    overlay = None

    if not has_plym:
        # Try to show a Qt fullscreen overlay
        try:
            from PyQt6.QtWidgets import QApplication
            from ...ui.widgets.progress_overlay import ShutdownOverlay
            qt_app = QApplication.instance() or QApplication(sys.argv)
            overlay = ShutdownOverlay()
            overlay.show()
            qt_app.processEvents()
        except Exception as e:
            log.warning(f"Could not show Qt overlay: {e}")

    def notify(msg: str, pct: int = -1):
        log.info(msg)
        if has_plym:
            plymouth_msg(msg)
            if pct >= 0:
                plymouth_progress(pct)
        elif overlay:
            overlay.set_message(msg)
            try:
                from PyQt6.QtWidgets import QApplication
                QApplication.instance().processEvents()
            except Exception:
                pass

    notify("Wakka: Instalando actualizaciones del sistema...", 0)

    yay = shutil.which("yay") or shutil.which("paru") or shutil.which("pacman")
    if not yay:
        notify("Error: yay no encontrado")
        sys.exit(1)

    try:
        result = subprocess.run(
            [yay, "-Syu", "--noconfirm", "--color", "never"],
            check=False,
            timeout=3600,  # 1 hour max
        )
        if result.returncode == 0:
            notify("Wakka: Actualizaciones instaladas correctamente.", 100)
        else:
            notify(f"Wakka: Error al instalar actualizaciones (código {result.returncode})")
    except subprocess.TimeoutExpired:
        notify("Wakka: Tiempo de espera agotado al instalar actualizaciones.")
    except Exception as e:
        notify(f"Wakka: Error inesperado: {e}")

    if overlay:
        overlay.set_done()
        try:
            import time
            time.sleep(3)
        except Exception:
            pass

    sys.exit(0)


# ─── In-app Inhibit Manager ───────────────────────────────────────────────────

class ShutdownInhibitManager:
    """
    Used by the main app to hold a shutdown inhibit lock during updates.
    """

    def __init__(self):
        self._lock = InhibitLock("Wakka está instalando actualizaciones")

    def acquire(self):
        acquired = self._lock.acquire()
        if acquired:
            log.info("Shutdown inhibit lock acquired.")
        return acquired

    def release(self):
        self._lock.release()
        log.info("Shutdown inhibit lock released.")
