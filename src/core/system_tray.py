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

class TrayDownloadWorker(QThread):
    finished = pyqtSignal(bool)

    def __init__(self, yay_wrapper):
        super().__init__()
        self.yay = yay_wrapper

    def run(self):
        try:
            # Descargamos todo sin especificar paquetes para que yay -Sw haga su magia
            process = self.yay.download_updates()
            process.wait()
            self.finished.emit(process.returncode == 0)
        except Exception:
            self.finished.emit(False)

class TrayIcon(QObject):
    show_window = pyqtSignal()
    quit_app = pyqtSignal()
    update_requested = pyqtSignal()
    updates_checked = pyqtSignal(list)
    download_finished = pyqtSignal(bool)
    next_check_countdown = pyqtSignal(str) # Señal con el tiempo restante formateado

    def __init__(self, yay_wrapper, config_mgr, cache_mgr, parent=None):
        super().__init__(parent)
        self.yay = yay_wrapper
        self.config_mgr = config_mgr
        self.cache_mgr = cache_mgr
        
        self.tray = QSystemTrayIcon(parent)
        self.update_count = 0
        self._last_update_hour = -1
        self._last_clean_hour = -1
        self._download_in_progress = False
        self._is_busy = False
        
        self.create_menu()
        self.update_icon()
        self.tray.activated.connect(self.on_activated)
        
        # Timer para chequear actualizaciones (Tick cada 15 min)
        self.scheduler_timer = QTimer()
        self.scheduler_timer.timeout.connect(self._scheduler_tick)
        self.scheduler_timer.start(900000)  # 15 minutos

        # Timer para la cuenta regresiva en la UI (Tick cada 1 seg)
        self.countdown_timer = QTimer()
        self.countdown_timer.timeout.connect(self._update_countdown)
        self.countdown_timer.start(1000)

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
            if self._download_in_progress:
                self.update_action.setText(self.tr("Descargando actualizaciones ({0})...").format(count))
                self.update_action.setEnabled(False)
            else:
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

            # Color azul si está descargando, rojo si está listo
            color = "#2196F3" if self._download_in_progress else "#f44336"
            painter.setBrush(QColor(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(badge_rect)

            painter.setPen(QColor("white"))
            painter.setFont(QFont("Sans Serif", 9, QFont.Weight.Bold))
            painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, str(self.update_count))
            painter.end()

            self.tray.setIcon(QIcon(pixmap))
            
            tool_tip = self.tr("Wakka - {0} actualizaciones").format(self.update_count)
            if self._download_in_progress:
                tool_tip += " " + self.tr("(descargando...)")
            self.tray.setToolTip(tool_tip)
        else:
            self.tray.setIcon(icon)
            self.tray.setToolTip(self.tr("Wakka - Gestor de paquetes"))

    def show_notification(self, title: str, message: str):
        self.tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.NoIcon, 5000)

    def on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self._is_busy:
                return

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

    def _update_countdown(self):
        """Calcula el tiempo restante y lo emite a la UI"""
        seconds = self._get_seconds_until_next_check()
        if seconds <= 0:
            self.next_check_countdown.emit(self.tr("Comprobando..."))
            return

        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        
        if h > 0:
            time_str = f"{h:02d}:{m:02d}:{s:02d}"
        else:
            time_str = f"{m:02d}:{s:02d}"
            
        self.next_check_countdown.emit(time_str)

    def _get_seconds_until_next_check(self) -> int:
        """Calcula los segundos que faltan para el próximo evento programado"""
        update_sched = self.config_mgr.get("update_schedule", {})
        if not update_sched.get("enabled", False):
            return -1

        now = datetime.datetime.now()
        freq = update_sched.get("frequency", "daily")
        
        try:
            if freq == "hourly":
                interval = update_sched.get("interval_hours", 6)
                # Próxima hora que sea múltiplo del intervalo
                next_h = ((now.hour // interval) + 1) * interval
                if next_h >= 24:
                    next_check = now.replace(hour=0, minute=0, second=0) + datetime.timedelta(days=1)
                else:
                    next_check = now.replace(hour=next_h, minute=0, second=0)
                
            elif freq == "daily":
                target_h = update_sched.get("hour", 12)
                next_check = now.replace(hour=target_h, minute=0, second=0)
                if next_check <= now:
                    next_check += datetime.timedelta(days=1)
                    
            elif freq == "weekly":
                day_map = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
                           "friday": 4, "saturday": 5, "sunday": 6}
                target_d = day_map.get(update_sched.get("day", "saturday"), 5)
                target_h = update_sched.get("hour", 12)
                next_check = now.replace(hour=target_h, minute=0, second=0)
                days_ahead = target_d - now.weekday()
                if days_ahead <= 0: # Target day is today or has passed this week
                    days_ahead += 7
                next_check += datetime.timedelta(days=days_ahead)
                
            elif freq == "monthly":
                target_day_str = str(update_sched.get("day", "1"))
                target_h = update_sched.get("hour", 12)
                
                # Simplificación: asumimos el día X del mes actual o siguiente
                if target_day_str == "last":
                    day = calendar.monthrange(now.year, now.month)[1]
                else:
                    day = int(target_day_str.replace("día ", ""))
                
                next_check = now.replace(day=day, hour=target_h, minute=0, second=0)
                if next_check <= now:
                    # Ir al próximo mes
                    if now.month == 12:
                        next_check = next_check.replace(year=now.year + 1, month=1)
                    else:
                        next_check = next_check.replace(month=now.month + 1)
            else:
                return -1
                
            diff = next_check - now
            return int(diff.total_seconds())
        except Exception:
            return -1

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

        if count > 0:
            if self.config_mgr.get("notifications", True):
                self.show_notification(
                    self.tr("Actualizaciones disponibles"),
                    self.tr("Hay {0} paquetes listos para actualizar").format(count)
                )
            
            # Iniciar descarga en segundo plano si está activado
            if self.config_mgr.get("background_download", True) and not self._download_in_progress:
                self.start_background_download()

    def start_background_download(self):
        if self._download_in_progress:
            return

        self._download_in_progress = True
        self.update_icon()
        self.set_update_count(self.update_count) # Actualiza texto del menú

        self.download_worker = TrayDownloadWorker(self.yay)
        self.download_worker.finished.connect(self.on_download_finished)
        self.download_worker.start()

    def on_download_finished(self, success):
        self._download_in_progress = False
        self.update_icon()
        self.set_update_count(self.update_count)
        self.download_finished.emit(success)

        if success and self.config_mgr.get("notifications", True):
            self.show_notification(
                self.tr("Descarga finalizada"),
                self.tr("Las actualizaciones han sido descargadas y están listas para instalar.")
            )

    def set_busy(self, busy: bool):
        """Desactiva o activa las acciones del tray según si hay una operación en curso"""
        self._is_busy = busy
        
        if busy:
            self.open_action.setEnabled(False)
            self.update_action.setEnabled(False)
            self.update_action.setText(self.tr("Operación en curso..."))
            self.quit_action.setEnabled(False)
        else:
            self.open_action.setEnabled(True)
            self.quit_action.setEnabled(True)
            # Restauramos el estado normal según el contador de actualizaciones
            self.set_update_count(self.update_count)

    def show(self):
        self.tray.show()
