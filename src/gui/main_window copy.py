from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QTabWidget, QApplication, QMessageBox
from PyQt6.QtCore import QTimer
import datetime
import calendar

from core.yay_wrapper import YayWrapper
from core.system_tray import TrayIcon
from core.google_client import GoogleClient
from core.config_manager import ConfigManager
from core.cache_manager import CacheManager
from gui.tabs.suggestions_tab import SuggestionsTab
from gui.tabs.updates_tab import UpdatesTab
from gui.tabs.search_tab import SearchTab
from gui.tabs.installed_tab import InstalledTab
from gui.tabs.cache_tab import CacheTab
from gui.tabs.settings_tab import SettingsTab
from gui.dialogs.terminal_dialog import TerminalDialog

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr("Wakka - Gestor de Paquetes"))
        self.setMinimumSize(1200, 800)

        self.yay = YayWrapper()
        self.google = GoogleClient()
        self.config_mgr = ConfigManager()
        self.cache_mgr = CacheManager(self)
        self.tray = TrayIcon(self)

        self.setup_ui()
        self.setup_tray()
        self._last_update_hour = -1
        self._last_clean_hour = -1

        self.check_initial_updates()

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Tabs principales
        self.tabs = QTabWidget()

        # Tab 1: Sugerencias
        self.suggestions_tab = SuggestionsTab(self.yay)
        self.suggestions_tab.install_package.connect(self.install_package)
        self.suggestions_tab.show_info.connect(self.show_package_info)
        self.tabs.addTab(self.suggestions_tab, self.tr("⭐ Sugerencias"))

        # Tab 2: Actualizaciones
        self.updates_tab = UpdatesTab(self.yay)
        self.updates_tab.install_selected.connect(self.install_packages)
        self.updates_tab.install_all.connect(self.update_all)
        self.updates_tab.show_info.connect(self.show_package_info)
        self.updates_tab.refresh_requested.connect(self.run_full_refresh)
        self.tabs.addTab(self.updates_tab, self.tr("⬆️ Actualizaciones"))

        # Tab 3: Buscar
        self.search_tab = SearchTab(self.yay)
        self.search_tab.install_package.connect(self.install_package)
        self.search_tab.install_selected.connect(self.install_packages)
        self.search_tab.show_info.connect(self.show_package_info)
        self.search_tab.install_local.connect(self.install_local_package)
        self.tabs.addTab(self.search_tab, self.tr("🔍 Buscar"))

        # Tab 4: Instaladas
        self.installed_tab = InstalledTab(self.yay)
        self.installed_tab.remove_package.connect(self.remove_package)
        self.installed_tab.remove_selected.connect(self.remove_packages)
        self.installed_tab.show_info.connect(self.show_package_info)
        self.tabs.addTab(self.installed_tab, self.tr("📦 Instaladas"))

        # Tab 5: Limpieza
        self.cache_tab = CacheTab(self.config_mgr)
        self.cache_tab.clean_pacman_requested.connect(self.run_clean_pacman)
        self.cache_tab.clean_pacman_uninstalled.connect(self.run_clean_pacman_uninstalled)
        self.cache_tab.clean_yay_requested.connect(self.run_clean_yay)
        self.cache_tab.clean_orphans_requested.connect(self.run_clean_orphans)
        self.cache_tab.refresh_requested.connect(self.refresh_cache_info)
        self.tabs.addTab(self.cache_tab, self.tr("🧹 Limpieza"))

        # Tab 6: Configuración
        self.settings_tab = SettingsTab(self.config_mgr)
        self.tabs.addTab(self.settings_tab, self.tr("⚙️ Configuración"))

        layout.addWidget(self.tabs)
        self.refresh_cache_info()

        # Status bar
        self.statusBar().showMessage(self.tr("Listo"))

    def setup_tray(self):
        self.tray.show_window.connect(self.show)
        self.tray.quit_app.connect(self.quit_application)
        self.tray.update_requested.connect(self.update_all)
        self.tray.show()

        # Timer para chequear actualizaciones (Tick cada 15 min)
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._scheduler_tick)
        self.update_timer.start(900000)

    def check_initial_updates(self):
        QTimer.singleShot(1000, self.check_updates_silent)

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
        """Decide si se debe ejecutar la comprobación basándose en la configuración"""
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
            if target_day_str == "Último día del mes":
                last_day = calendar.monthrange(now.year, now.month)[1]
                if now.day == last_day:
                    is_target_day = True
            else:
                try:
                    num = int(target_day_str.replace("día ", ""))
                    if now.day == num:
                        is_target_day = True
                except ValueError:
                    pass
            
            return is_target_day and now.hour == target_h and now.hour != last_hour
            
        return False

    def _run_auto_clean(self, keep: int):
        """ 
        Ejecutamos las limpiezas de forma secuencial o simplemente las disparamos. 
        Nota: pkexec pedirá contraseña si el sistema lo requiere.
        """
        self.cache_mgr.clean_pacman_cache(keep)
        self.cache_mgr.clean_yay_cache()
        self.cache_mgr.clean_orphans()
        
        if self.config_mgr.get("notifications", True):
            self.tray.show_notification(
                self.tr("Limpieza automática"),
                self.tr("Se ha ejecutado la limpieza programada del sistema.")
            )
        
        # Refrescar la UI si la pestaña de caché está visible
        self.refresh_cache_info()

    def check_updates_silent(self):
        updates = self.yay.get_available_updates()
        count = len(updates)
        self.tray.set_update_count(count)

        if count > 0 and self.config_mgr.get("notifications", True):
            self.tray.show_notification(
                self.tr("Actualizaciones disponibles"),
                self.tr("Hay {0} paquetes listos para actualizar").format(count)
            )

    def install_package(self, package_name):
        dialog = TerminalDialog(self.tr("Instalando {0}").format(package_name), parent=self)
        process = self.yay.install([package_name])
        dialog.process = process
        dialog.setup_worker()
        dialog.exec()
        self.refresh_all()

    def install_packages(self, packages):
        dialog = TerminalDialog(self.tr("Instalando {0} paquetes").format(len(packages)), parent=self)
        process = self.yay.install(packages)
        dialog.process = process
        dialog.setup_worker()
        dialog.exec()
        self.refresh_all()

    def install_local_package(self, file_path):
        dialog = TerminalDialog(self.tr("Instalando {0}").format(file_path), parent=self)
        process = self.yay.install_local_package(file_path)
        dialog.process = process
        dialog.setup_worker()
        dialog.exec()

    def remove_package(self, package_name):
        dialog = TerminalDialog(self.tr("Desinstalando {0}").format(package_name), parent=self)
        process = self.yay.remove([package_name])
        dialog.process = process
        dialog.setup_worker()
        dialog.exec()
        self.refresh_all()

    def remove_packages(self, packages):
        dialog = TerminalDialog(self.tr("Desinstalando {0} paquetes").format(len(packages)), parent=self)
        process = self.yay.remove(packages)
        dialog.process = process
        dialog.setup_worker()
        dialog.exec()
        self.refresh_all()

    def update_all(self):
        dialog = TerminalDialog(self.tr("Actualizando sistema completo"), parent=self)
        process = self.yay.update_system()
        dialog.process = process
        dialog.setup_worker()
        dialog.exec()
        self.refresh_all()

    def run_full_refresh(self):
        dialog = TerminalDialog(self.tr("Sincronizando bases de datos"), parent=self)
        process = self.yay.refresh_databases()
        dialog.process = process
        dialog.setup_worker()
        dialog.exec()
        self.refresh_all()

    def show_package_info(self, name, description):
        self.google.explain_package(name, description)

    def run_clean_pacman(self, keep):
        dialog = TerminalDialog(self.tr("Limpiando caché de Pacman"), parent=self)
        process = self.cache_mgr.clean_pacman_cache(keep)
        dialog.process = process
        dialog.setup_worker()
        dialog.exec()
        self.refresh_cache_info()

    def run_clean_pacman_uninstalled(self):
        dialog = TerminalDialog(self.tr("Limpiando caché de paquetes desinstalados"), parent=self)
        process = self.cache_mgr.clean_pacman_uninstalled()
        dialog.process = process
        dialog.setup_worker()
        dialog.exec()
        self.refresh_cache_info()

    def run_clean_yay(self):
        dialog = TerminalDialog(self.tr("Limpiando caché de AUR"), parent=self)
        process = self.cache_mgr.clean_yay_cache()
        dialog.process = process
        dialog.setup_worker()
        dialog.exec()
        self.refresh_cache_info()

    def run_clean_orphans(self):
        dialog = TerminalDialog(self.tr("Eliminando paquetes huérfanos"), parent=self)
        process = self.cache_mgr.clean_orphans()
        dialog.process = process
        dialog.setup_worker()
        dialog.exec()
        self.refresh_cache_info()

    def refresh_cache_info(self):
        # Obtain info and update the cache tab
        info = self.cache_mgr.get_cache_info_sync()
        self.cache_tab.update_cache_info(info)

    def refresh_all(self):
        self.updates_tab.load_updates()
        self.installed_tab.load_packages()
        self.suggestions_tab.load_suggestions()
        self.check_updates_silent()

    def quit_application(self):
        self.tray.tray.hide()
        QApplication.quit()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        if self.config_mgr.get("notifications", True):
            self.tray.show_notification(
                self.tr("Wakka sigue ejecutándose"),
                self.tr("La aplicación se ha minimizado a la bandeja del sistema")
            )
