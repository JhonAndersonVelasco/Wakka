import os
import datetime
import calendar
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QColor, QPixmap, QPainter, QAction, QFont
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QRect, QTimer, QThread, QCoreApplication


def load_app_icon() -> QIcon:
    icon = QIcon.fromTheme("wakka")

    if icon.isNull():
        candidates = [
            "/usr/share/icons/hicolor/scalable/apps/wakka.svg",
            os.path.join(os.path.dirname(__file__), "..", "resources", "wakka.svg"),
            os.path.join(os.getcwd(), "src", "resources", "wakka.svg"),
            os.path.join(os.getcwd(), "resources", "wakka.svg"),
        ]
        for path in candidates:
            if os.path.exists(path):
                icon = QIcon(path)
                break

        if icon.isNull():
            icon = QIcon.fromTheme("package-manager")

    return icon

class TrayUpdatesWorker(QThread):
    finished = pyqtSignal(list)

    def __init__(self, yay_wrapper):
        super().__init__()
        self.yay = yay_wrapper

    def run(self):
        try:
            updates = self.yay.get_available_updates()
            self.finished.emit(updates)
        except Exception:
            self.finished.emit([])

class TrayIcon(QObject):
    show_window = pyqtSignal()
    quit_app = pyqtSignal()
    update_requested = pyqtSignal()
    updates_checked = pyqtSignal(list)

    def __init__(self, yay_wrapper, config_mgr, cache_mgr, parent=None):
        super().__init__(parent)
        self.yay = yay_wrapper
        self.config_mgr = config_mgr
        self.cache_mgr = cache_mgr
        
        self.tray = QSystemTrayIcon(parent)
        self.update_count = 0
        self._last_update_hour = -1
        self._last_clean_hour = -1
        
        self.create_menu()
        self.update_icon()
        self.tray.activated.connect(self.on_activated)
        
        # Timer para chequear actualizaciones (Tick cada 15 min)
        self.scheduler_timer = QTimer()
        self.scheduler_timer.timeout.connect(self._scheduler_tick)
        self.scheduler_timer.start(900000)  # 15 minutos

    def create_menu(self):
        self.menu = QMenu()

        self.open_action = QAction(self.tr("Abrir Wakka"), self)
        self.open_action.setIcon(QIcon.fromTheme("window-new"))
        self.open_action.triggered.connect(self.show_window.emit)
        self.menu.addAction(self.open_action)

        self.update_action = QAction(self.tr("Sistema actualizado"), self)
        self.update_action.setIcon(QIcon.fromTheme("software-update-available"))
        self.update_action.setEnabled(False)
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
        icon = load_app_icon()

        if self.update_count > 0:
            pixmap = icon.pixmap(48, 48)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            badge_size = 22
            badge_rect = QRect(48 - badge_size, 0, badge_size, badge_size)

            painter.setBrush(QColor("#f44336"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(badge_rect)

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
        self.tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.NoIcon, 5000)

    def on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            parent = self.parent()
            if parent:
                if parent.isVisible():
                    parent.hide()
                else:
                    parent.showNormal()
                    parent.activateWindow()

    def _scheduler_tick(self):
        now = datetime.datetime.now()
        
        # 1. Comprobar Actualizaciones
        update_sched = self.config_mgr.get("update_schedule", {})
        if self._should_run_now(update_sched, self._last_update_hour, now):
            self._last_update_hour = now.hour
            self.check_updates_silent()
            
        # 2. Comprobar Limpieza de Caché
        cache_sched = self.config_mgr.get("cache.schedule", {})
        if self._should_run_now(cache_sched, self._last_clean_hour, now):
            self._last_clean_hour = now.hour
            self._run_auto_clean(self.config_mgr.get("cache.keep_versions", 1))

    def _should_run_now(self, sched: dict, last_hour: int, now: datetime.datetime) -> bool:
        if not sched.get("enabled", False):
            return False

        freq = sched.get("frequency", "daily")
        
        if freq == "hourly":
            interval = sched.get("interval_hours", 6)
            return now.hour % interval == 0 and now.hour != last_hour
            
        if freq == "daily":
            target_h = sched.get("hour", 12)
            return now.hour == target_h and now.hour != last_hour
            
        if freq == "weekly":
            day_map = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
                       "friday": 4, "saturday": 5, "sunday": 6}
            target_d = day_map.get(sched.get("day", "saturday"), 5)
            target_h = sched.get("hour", 12)
            return now.weekday() == target_d and now.hour == target_h and now.hour != last_hour
            
        if freq == "monthly":
            target_day_str = str(sched.get("day", "1"))
            target_h = sched.get("hour", 12)
            
            is_target_day = False
            if target_day_str == "last" or target_day_str == "Último día del mes":
                last_day = calendar.monthrange(now.year, now.month)[1]
                if now.day == last_day:
                    is_target_day = True
            else:
                try:
                    normalized_day = target_day_str.replace("día ", "")
                    num = int(normalized_day)
                    if now.day == num:
                        is_target_day = True
                except ValueError:
                    pass
            
            return is_target_day and now.hour == target_h and now.hour != last_hour
            
        return False

    def _run_auto_clean(self, keep: int):
        self.cache_mgr.clean_pacman_cache(keep)
        self.cache_mgr.clean_yay_cache()
        self.cache_mgr.clean_orphans()
        
        if self.config_mgr.get("notifications", True):
            self.show_notification(
                self.tr("Limpieza automática"),
                self.tr("Se ha ejecutado la limpieza programada del sistema.")
            )

    def check_updates_silent(self):
        # Evitar múltiples chequeos simultáneos
        if hasattr(self, 'update_worker') and self.update_worker.isRunning():
            return

        self.update_worker = TrayUpdatesWorker(self.yay)
        self.update_worker.finished.connect(self.on_updates_checked_silent)
        self.update_worker.start()

    def on_updates_checked_silent(self, updates):
        count = len(updates)
        self.set_update_count(count)
        self.updates_checked.emit(updates)

        if count > 0 and self.config_mgr.get("notifications", True):
            self.show_notification(
                self.tr("Actualizaciones disponibles"),
                self.tr("Hay {0} paquetes listos para actualizar").format(count)
            )

    def set_busy(self, busy: bool):
        """Desactiva o activa las acciones del tray según si hay una operación en curso"""
        if busy:
            self.update_action.setEnabled(False)
            self.update_action.setText(self.tr("Operación en curso..."))
        else:
            # Restauramos el estado normal según el contador de actualizaciones
            self.set_update_count(self.update_count)

    def show(self):
        self.tray.show()
