import os
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QColor, QPixmap, QPainter, QAction, QFont
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QRect

class TrayIcon(QObject):
    show_window = pyqtSignal()
    quit_app = pyqtSignal()
    update_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tray = QSystemTrayIcon(parent)
        self.update_count = 0
        self.create_menu()
        self.update_icon()
        self.tray.activated.connect(self.on_activated)

    def create_menu(self):
        self.menu = QMenu()

        self.open_action = QAction(self.tr("Abrir Wakka"), self)
        self.open_action.setIcon(QIcon.fromTheme("window-new"))
        self.open_action.triggered.connect(self.show_window.emit)
        self.menu.addAction(self.open_action)

        self.update_action = QAction(self.tr("Sistema actualizado"), self)
        self.update_action.setIcon(QIcon.fromTheme("software-update-available"))
        self.update_action.setEnabled(False)  # deshabilitado hasta que haya actualizaciones
        self.update_action.triggered.connect(self.update_requested.emit)
        self.menu.addAction(self.update_action)

        self.menu.addSeparator()

        self.quit_action = QAction(self.tr("Salir"), self)
        self.quit_action.setIcon(QIcon.fromTheme("application-exit"))
        self.quit_action.triggered.connect(self.quit_app.emit)
        self.menu.addAction(self.quit_action)

        self.tray.setContextMenu(self.menu)

    def set_update_count(self, count: int):
        self.update_count = count
        self.update_icon()
        if count > 0:
            self.update_action.setText(self.tr("Actualizar el sistema ({0})").format(count))
            self.update_action.setEnabled(True)
        else:
            self.update_action.setText(self.tr("Sistema actualizado"))
            self.update_action.setEnabled(False)

    def update_icon(self):
        """Genera icono con badge de notificación sobre el logo de Wakka"""
        # Intentar cargar desde el tema del sistema primero
        icon = QIcon.fromTheme("wakka")

        # Fallback a la ruta de instalación local si no está en el tema todavía
        if icon.isNull():
            fallback_path = "/usr/share/icons/hicolor/scalable/apps/wakka.svg"
            if os.path.exists(fallback_path):
                icon = QIcon(fallback_path)
            else:
                icon = QIcon.fromTheme("package-manager")

        if self.update_count > 0:
            # Crear un pixmap de alta resolución basado en el icono original
            pixmap = icon.pixmap(48, 48)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            # Dibujar un círculo rojo para el badge (esquina superior derecha)
            badge_size = 22
            badge_rect = QRect(48 - badge_size, 0, badge_size, badge_size)

            painter.setBrush(QColor("#f44336")) # Rojo vibrante
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(badge_rect)

            # Dibujar el número de actualizaciones
            painter.setPen(QColor("white"))
            painter.setFont(QFont("Sans Serif", 9, QFont.Weight.Bold))
            painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, str(self.update_count))
            painter.end()

            self.tray.setIcon(QIcon(pixmap))
            self.tray.setToolTip(self.tr("Wakka - {0} actualizaciones").format(self.update_count))
        else:
            self.tray.setIcon(icon)
            self.tray.setToolTip(self.tr("Wakka - Gestor de paquetes"))

    def show_notification(self, title: str, message: str):
        self.tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 5000)

    def on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            # Al hacer clic sencillo, alternamos visibilidad
            parent = self.parent()
            if parent:
                if parent.isVisible():
                    parent.hide()
                else:
                    parent.showNormal()
                    parent.activateWindow()

    def show(self):
        self.tray.show()