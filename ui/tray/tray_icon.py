"""
Wakka — System Tray Icon
QSystemTrayIcon with update badge, context menu, and DE detection.
Works on KDE/Xfce/LXQt. On GNOME requires KStatusNotifierItem extension.
"""
from __future__ import annotations

from PyQt6.QtCore import pyqtSignal, QObject
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu

from ui.styles.icons import get_tray_icon, get_icon
from ui.styles.theme import style_menu


class TrayIcon(QObject):
    open_requested   = pyqtSignal()
    update_requested = pyqtSignal()
    quit_requested   = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._update_count = 0

        self._tray = QSystemTrayIcon(self)
        self._tray.setIcon(get_tray_icon(False))
        self._tray.setToolTip(self.tr("Wakka — Administrador de paquetes"))
        self._tray.activated.connect(self._on_activated)

        self._build_menu()
        self._tray.setContextMenu(self._menu)
        self._tray.show()

    def _build_menu(self):
        self._menu = QMenu()
        self._menu.setStyleSheet(style_menu())

        open_action = self._menu.addAction(
            get_icon("installed", "#9d8fff"), self.tr("Abrir Wakka")
        )
        open_action.triggered.connect(self.open_requested)

        self._menu.addSeparator()

        self._updates_action = self._menu.addAction(
            get_icon("updates", "#8892a4"), self.tr("Sin actualizaciones pendientes")
        )
        self._updates_action.triggered.connect(self._on_update_requested)

        self._menu.addSeparator()

        quit_action = self._menu.addAction(
            get_icon("power", "#f05252"), self.tr("Salir")
        )
        quit_action.triggered.connect(self.quit_requested)

    # ─── Public API ────────────────────────────────────────────────────────────

    def set_update_count(self, count: int):
        self._update_count = count
        self._tray.setIcon(get_tray_icon(count > 0))

        if count == 0:
            self._updates_action.setText(self.tr("Sistema al día"))
            self._updates_action.setIcon(get_icon("check", "#2dd98a"))
            self._tray.setToolTip(self.tr("Wakka — Sistema al día"))
        elif count == 1:
            self._updates_action.setText(self.tr("Actualizar 1 paquete ahora"))
            self._updates_action.setIcon(get_icon("arrow_up", "#2dd98a"))
            self._tray.setToolTip(self.tr("Wakka — 1 actualización disponible"))
        else:
            self._updates_action.setText(self.tr("Actualizar %1 paquetes ahora").replace("%1", str(count)))
            self._updates_action.setIcon(get_icon("arrow_up", "#2dd98a"))
            self._tray.setToolTip(self.tr("Wakka — %1 actualizaciones disponibles").replace("%1", str(count)))

    def _on_update_requested(self):
        if self._update_count > 0:
            self.update_requested.emit()

    def set_busy(self, busy: bool):
        """Show a 'working' spinner state."""
        if busy:
            self._tray.setToolTip(self.tr("Wakka — Instalando actualizaciones..."))

    def notify(self, title: str, message: str, icon_type=QSystemTrayIcon.MessageIcon.Information):
        if QSystemTrayIcon.isSystemTrayAvailable():
            self._tray.showMessage(title, message, icon_type, 5000)

    def notify_updates(self, count: int):
        if count > 0:
            self.notify(
                "Wakka",
                self.tr("Hay %1 actualización(es) disponible(s)").replace("%1", str(count)),
                QSystemTrayIcon.MessageIcon.Information,
            )

    def is_available(self) -> bool:
        return QSystemTrayIcon.isSystemTrayAvailable()

    # ─── Internal ──────────────────────────────────────────────────────────────

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.open_requested.emit()
        elif reason == QSystemTrayIcon.ActivationReason.MiddleClick:
            self.update_requested.emit()
