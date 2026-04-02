"""
Wakka — Shutdown Progress Overlay
Full-screen overlay shown while installing updates on shutdown.
Auto-detects Plymouth; falls back to Qt overlay.
"""
from __future__ import annotations

import shutil
import subprocess
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QLinearGradient, QBrush
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from ..styles.theme import (
    style_overlay_logo, style_overlay_status, style_overlay_package,
    style_progress_bar, style_status, get_color,
)


def _plymouth_available() -> bool:
    return shutil.which("plymouth") is not None


def plymouth_message(text: str):
    """Send a message to Plymouth if it's running."""
    try:
        subprocess.run(["plymouth", "message", "--text", text], timeout=3)
    except Exception:
        pass


def plymouth_set_progress(pct: int):
    """Set Plymouth progress (0-100)."""
    try:
        subprocess.run(["plymouth", "system-update", f"--progress={pct}"], timeout=3)
    except Exception:
        pass


class ShutdownOverlay(QWidget):
    """
    Full-screen Qt overlay for shutdown update progress.
    Used when Plymouth is not available.
    """
    cancel_requested = pyqtSignal()

    def __init__(self):
        super().__init__(None, Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint |
                         Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowState(Qt.WindowState.WindowFullScreen)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self._setup_ui()
        self._dots = 0
        self._dot_timer = QTimer(self)
        self._dot_timer.timeout.connect(self._animate_dots)
        self._dot_timer.start(500)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(24)

        # Wakka logo text
        logo = QLabel("⚡ Wakka")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setStyleSheet(style_overlay_logo())

        # Status message
        self._status = QLabel(self.tr("Instalando actualizaciones..."))
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status.setStyleSheet(style_overlay_status())

        # Package being processed
        self._pkg_label = QLabel("")
        self._pkg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._pkg_label.setStyleSheet(style_overlay_package())
        self._pkg_label.setWordWrap(True)

        # Progress bar
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)  # Indeterminate
        self._progress.setFixedWidth(420)
        self._progress.setFixedHeight(6)
        self._progress.setTextVisible(False)
        self._progress.setStyleSheet(style_progress_bar())

        # Warning
        self._warning = QLabel(self.tr("⚠ Por favor no apagues el equipo manualmente"))
        self._warning.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._warning.setStyleSheet(style_status("warning", 11))

        layout.addStretch()
        layout.addWidget(logo)
        layout.addSpacing(8)
        layout.addWidget(self._status)
        layout.addWidget(self._pkg_label)
        layout.addSpacing(12)
        layout.addWidget(self._progress, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(16)
        layout.addWidget(self._warning)
        layout.addStretch()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0, QColor("#0a0d14"))
        grad.setColorAt(1, QColor("#111520"))
        painter.fillRect(self.rect(), QBrush(grad))

    def set_message(self, text: str):
        self._status.setText(text)

    def set_package(self, pkg_name: str):
        self._pkg_label.setText(pkg_name)

    def set_progress(self, current: int, total: int):
        if total > 0:
            self._progress.setRange(0, total)
            self._progress.setValue(current)
        else:
            self._progress.setRange(0, 0)  # Indeterminate

    def set_done(self):
        self._dot_timer.stop()
        self._status.setText(self.tr("✓ Actualizaciones completadas"))
        self._pkg_label.setText(self.tr("El sistema se apagará en unos segundos..."))
        self._progress.setRange(0, 1)
        self._progress.setValue(1)
        self._warning.setText("")
        self._status.setStyleSheet(style_status("success", 16) + " font-weight: 600;")

    def _animate_dots(self):
        self._dots = (self._dots + 1) % 4
        dots = "." * self._dots
        base = self.tr("Instalando actualizaciones")
        self._status.setText(f"{base}{dots}")
