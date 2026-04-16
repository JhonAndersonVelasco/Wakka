from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QTabWidget, QApplication, QMessageBox
from PyQt6.QtCore import QTimer

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
        self.tray = TrayIcon(self.yay, self.config_mgr, self.cache_mgr, self)

        self.setup_ui()
        self.setup_tray()
        self._sync_tray_with_updates_tab()
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

        # Status bar
        self.statusBar().showMessage(self.tr("Listo"))

    def setup_tray(self):
        self.tray.show_window.connect(self.show)
        self.tray.quit_app.connect(self.quit_application)
        self.tray.update_requested.connect(self.update_all)
        self.tray.updates_checked.connect(self.on_updates_checked)
        self.tray.show()

    def check_initial_updates(self):
        QTimer.singleShot(1000, self.tray.check_updates_silent)

    def on_updates_checked(self, count):
        """Callback cuando el tray termina de chequear actualizaciones"""
        if self.isVisible():
            self.refresh_cache_info()

    def install_package(self, package_name):
        process = self.yay.install([package_name])
        self._run_terminal_operation(
            self.tr("Instalando {0}").format(package_name),
            process,
            self._refresh_after_package_change,
        )

    def install_packages(self, packages):
        process = self.yay.install(packages)
        self._run_terminal_operation(
            self.tr("Instalando {0} paquetes").format(len(packages)),
            process,
            self._refresh_after_package_change,
        )

    def install_local_package(self, file_path):
        process = self.yay.install_local_package(file_path)
        self._run_terminal_operation(
            self.tr("Instalando {0}").format(file_path),
            process,
            self._refresh_after_package_change,
        )

    def remove_package(self, package_name):
        process = self.yay.remove([package_name])
        self._run_terminal_operation(
            self.tr("Desinstalando {0}").format(package_name),
            process,
            self._refresh_after_package_change,
        )

    def remove_packages(self, packages):
        process = self.yay.remove(packages)
        self._run_terminal_operation(
            self.tr("Desinstalando {0} paquetes").format(len(packages)),
            process,
            self._refresh_after_package_change,
        )

    def update_all(self):
        process = self.yay.update_system()
        self._run_terminal_operation(
            self.tr("Actualizando sistema completo"),
            process,
            self._refresh_after_package_change,
        )

    def run_full_refresh(self):
        process = self.yay.refresh_databases()
        self._run_terminal_operation(
            self.tr("Sincronizando bases de datos"),
            process,
            self._refresh_updates_state,
        )

    def show_package_info(self, name, description):
        self.google.explain_package(name, description)

    def run_clean_pacman(self, keep):
        process = self.cache_mgr.clean_pacman_cache(keep)
        self._run_terminal_operation(
            self.tr("Limpiando caché de Pacman"),
            process,
            self.cache_tab.refresh_view,
        )

    def run_clean_pacman_uninstalled(self):
        process = self.cache_mgr.clean_pacman_uninstalled()
        self._run_terminal_operation(
            self.tr("Limpiando caché de paquetes desinstalados"),
            process,
            self.cache_tab.refresh_view,
        )

    def run_clean_yay(self):
        process = self.cache_mgr.clean_yay_cache()
        self._run_terminal_operation(
            self.tr("Limpiando caché de AUR"),
            process,
            self.cache_tab.refresh_view,
        )

    def run_clean_orphans(self):
        process = self.cache_mgr.clean_orphans()
        self._run_terminal_operation(
            self.tr("Eliminando paquetes huérfanos"),
            process,
            self.cache_tab.refresh_view,
        )

    def _run_terminal_operation(self, description, process, on_success=None):
        dialog = TerminalDialog(description, process=process, parent=self)
        if dialog.exec() and dialog.operation_succeeded and on_success:
            on_success()

    def _refresh_after_package_change(self):
        self._refresh_updates_state()
        self.installed_tab.refresh_view()
        self.suggestions_tab.refresh_view()
        self.search_tab.refresh_view()
        self.cache_tab.refresh_view()

    def _refresh_updates_state(self):
        self.updates_tab.refresh_view()
        self._sync_tray_with_updates_tab()

    def _sync_tray_with_updates_tab(self):
        self.tray.set_update_count(self.updates_tab.get_update_count())

    def refresh_cache_info(self):
        info = self.cache_mgr.get_cache_info_sync()
        self.cache_tab.update_cache_info(info)

    def refresh_all(self):
        """Actualiza todos los tabs con opcional de yield entre operaciones para UI responsive."""
        self._refresh_after_package_change()

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
