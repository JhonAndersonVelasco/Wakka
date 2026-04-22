from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QTabWidget, QApplication, QMessageBox
from PyQt6.QtGui import QIcon

from core.yay_wrapper import YayWrapper
from core.system_tray import TrayIcon
from core.package_info_client import PackageInfoClient
from core.config_manager import ConfigManager
from core.cache_manager import CacheManager
from gui.tabs.explore_tab import ExploreTab
from gui.tabs.updates_tab import UpdatesTab
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
        self.package_info = PackageInfoClient()
        self.config_mgr = ConfigManager()
        self.cache_mgr = CacheManager(self)
        self.tray = TrayIcon(self.yay, self.config_mgr, self.cache_mgr, self)
        self._operation_in_progress = False

        self.setup_ui()
        self.setup_tray()
        self._sync_tray_with_updates_tab()

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Tabs principales
        self.tabs = QTabWidget()

        # Tab 1: Explorar (Sugerencias + Buscar)
        self.explore_tab = ExploreTab(self.yay)
        self.explore_tab.install_package.connect(self.install_package)
        self.explore_tab.install_selected.connect(self.install_packages)
        self.explore_tab.show_info.connect(self.show_package_info)
        self.explore_tab.install_local.connect(self.install_local_package)
        self.explore_tab.status_msg.connect(self.set_status_message)
        self.tabs.addTab(self.explore_tab, self.tr("🌍 Explorar"))

        # Tab 2: Actualizaciones
        self.updates_tab = UpdatesTab(self.yay)
        self.updates_tab.install_selected.connect(self.install_packages)
        self.updates_tab.install_all.connect(self.update_all)
        self.updates_tab.show_info.connect(self.show_package_info)
        self.updates_tab.refresh_requested.connect(self.run_full_refresh)
        self.updates_tab.status_msg.connect(self.set_status_message)
        self.updates_tab.updates_updated.connect(lambda pkgs: self.tray.set_update_count(len(pkgs)))
        self.tray.next_check_countdown.connect(self.updates_tab.set_countdown)
        self.tabs.addTab(self.updates_tab, self.tr("⬆️ Actualizaciones"))

        # Tab 3: Instaladas
        self.installed_tab = InstalledTab(self.yay)
        self.installed_tab.remove_package.connect(self.remove_package)
        self.installed_tab.remove_selected.connect(self.remove_packages)
        self.installed_tab.show_info.connect(self.show_package_info)
        self.installed_tab.status_msg.connect(self.set_status_message)
        self.tabs.addTab(self.installed_tab, self.tr("📦 Instaladas"))

        # Tab 4: Limpieza
        self.cache_tab = CacheTab(self.config_mgr)
        self.cache_tab.clean_pacman_requested.connect(self.run_clean_pacman)
        self.cache_tab.clean_pacman_uninstalled.connect(self.run_clean_pacman_uninstalled)
        self.cache_tab.clean_yay_requested.connect(self.run_clean_yay)
        self.cache_tab.clean_orphans_requested.connect(self.run_clean_orphans)
        self.cache_tab.refresh_requested.connect(self.refresh_cache_info)
        self.cache_tab.status_msg.connect(self.set_status_message)
        self.cache_mgr.cache_info_ready.connect(self.cache_tab.update_cache_info)
        self.tabs.addTab(self.cache_tab, self.tr("🧹 Limpieza"))

        # Tab 5: Configuración
        self.settings_tab = SettingsTab(self.config_mgr)
        self.settings_tab.status_msg.connect(self.set_status_message)
        self.tabs.addTab(self.settings_tab, self.tr("⚙️ Configuración"))
        
        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.set_status_message(self.tr("Aplicaciones y librerías recomendadas por la Arch Wiki"))

        layout.addWidget(self.tabs)
        
        # Refresco inicial de caché al iniciar la aplicación
        self.refresh_cache_info()

    def set_status_message(self, message):
        self.statusBar().showMessage(message, 30000)  # Muestra el mensaje por 30 segundos

    def _on_tab_changed(self, index):
        if self.tabs.widget(index) == self.explore_tab:
            self.set_status_message(self.tr("Explorar sugerencias y buscar paquetes en repositorios oficiales y AUR"))
        elif self.tabs.widget(index) == self.updates_tab:
            self.set_status_message(self.tr("Actualizaciones disponibles para el sistema"))
        elif self.tabs.widget(index) == self.installed_tab:
            self.set_status_message(self.tr("Lista de paquetes instalados en el sistema"))
        elif self.tabs.widget(index) == self.cache_tab:
            self.set_status_message(self.tr("Limpiar y gestionar la caché de paquetes para liberar espacio en disco"))
        elif self.tabs.widget(index) == self.settings_tab:
            self.set_status_message(self.tr("Configuración de Wakka y de pacman.conf"))

    def setup_tray(self):
        self.tray.show_window.connect(self.show)
        self.tray.quit_app.connect(self.quit_application)
        self.tray.update_requested.connect(self.update_all)
        self.tray.updates_checked.connect(self.on_updates_checked)
        self.tray.show()

    def on_updates_checked(self, updates):
        """Callback cuando el tray termina de chequear actualizaciones"""
        self.updates_tab.set_packages(updates)
        if self.isVisible():
            self.refresh_cache_info()

    def install_package(self, package_name):
        if self._operation_in_progress: return
        if not self._ensure_not_locked(): return
        process = self.yay.install([package_name])
        self._run_terminal_operation(
            self.tr("Instalando {0}").format(package_name),
            process,
            self._refresh_after_package_change,
        )

    def install_packages(self, packages):
        if self._operation_in_progress: return
        if not self._ensure_not_locked(): return
        process = self.yay.install(packages)
        self._run_terminal_operation(
            self.tr("Instalando {0} paquetes").format(len(packages)),
            process,
            self._refresh_after_package_change,
        )

    def install_local_package(self, file_path):
        if self._operation_in_progress: return
        if not self._ensure_not_locked(): return
        process = self.yay.install_local_package(file_path)
        self._run_terminal_operation(
            self.tr("Instalando {0}").format(file_path),
            process,
            self._refresh_after_package_change,
        )

    def remove_package(self, package_name):
        if self._operation_in_progress: return
        if not self._ensure_not_locked(): return
        process = self.yay.remove([package_name])
        self._run_terminal_operation(
            self.tr("Desinstalando {0}").format(package_name),
            process,
            self._refresh_after_package_change,
        )

    def remove_packages(self, packages):
        if self._operation_in_progress: return
        if not self._ensure_not_locked(): return
        process = self.yay.remove(packages)
        self._run_terminal_operation(
            self.tr("Desinstalando {0} paquetes").format(len(packages)),
            process,
            self._refresh_after_package_change,
        )

    def update_all(self):
        if self._operation_in_progress: return
        if not self._ensure_not_locked(): return
        process = self.yay.update_system()
        self._run_terminal_operation(
            self.tr("Actualizando sistema completo"),
            process,
            self._refresh_after_package_change,
        )

    def run_full_refresh(self):
        if self._operation_in_progress: return
        if not self._ensure_not_locked(): return
        process = self.yay.refresh_databases()
        self._run_terminal_operation(
            self.tr("Sincronizando bases de datos"),
            process,
            self._refresh_updates_state,
        )

    def show_package_info(self, name, description):
        self.package_info.explain_package(name, description)

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
        if not self._ensure_not_locked(): return
        process = self.cache_mgr.clean_orphans()
        self._run_terminal_operation(
            self.tr("Eliminando paquetes huérfanos"),
            process,
            self.cache_tab.refresh_view,
        )

    def _ensure_not_locked(self) -> bool:
        """Verifica el archivo de bloqueo y pregunta al usuario si desea eliminarlo."""
        if not self.yay.is_locked():
            return True

        reply = QMessageBox.question(
            self,
            self.tr("Wakka"),
            self.tr("Se ha detectado el archivo de bloqueo de Pacman (db.lck).\n"
                   "Esto sucede si otra instancia de Pacman o Yay está corriendo o terminó de forma inesperada.\n\n"
                   "¿Desea eliminar el bloqueo para continuar?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.yay.unlock():
                self.statusBar().showMessage(self.tr("Archivo de bloqueo eliminado."), 5000)
                return True
            else:
                QMessageBox.critical(
                    self, 
                    self.tr("Error"), 
                    self.tr("No se pudo eliminar el archivo de bloqueo.\n\n"
                           "Asegúrese de ingresar la contraseña correctamente y que el helper esté instalado.")
                )
        
        return False

    def _run_terminal_operation(self, description, process, on_success=None):
        """Ejecuta la operación en el diálogo de terminal y gestiona el estado de la barra."""
        self._operation_in_progress = True
        self.tray.set_busy(True)
        
        # Notifica que comienza una operación larga
        self.statusBar().showMessage(self.tr("Iniciando: {0}...").format(description), 0)

        dialog = TerminalDialog(description, process=process, parent=self)
        if dialog.exec() and dialog.operation_succeeded and on_success:
            # Notifica que finaliza con éxito y llama al callback de actualización
            self.statusBar().showMessage(self.tr("Operación completada: {0}").format(description), 3000)
            on_success()
        else:
            # Notifica en caso de fallo o cancelación
            error_msg = self.tr("Error o cancelado durante la operación: {0}").format(description)
            self.statusBar().showMessage(error_msg, 5000)
        
        self._operation_in_progress = False
        self.tray.set_busy(False)

    def _refresh_after_package_change(self):
        """Refresca todos los tabs y actualiza el estado de la barra."""
        # Actualización del estado en la barra antes de refrescar todo
        self.statusBar().showMessage(self.tr("Actualizando sistema..."), 5000)

        self._refresh_updates_state()
        self.installed_tab.refresh_view()
        self.explore_tab.refresh_view()
        self.cache_tab.refresh_view()

    def _refresh_updates_state(self):
        """Actualiza la vista de actualizaciones y sincroniza el estado de la bandeja."""
        # Notifica que se están actualizando las bases de datos/paquetes
        self.statusBar().showMessage(self.tr("Verificando actualizaciones del sistema..."), 5000)

        self.updates_tab.refresh_view()
        self._sync_tray_with_updates_tab()

    def _sync_tray_with_updates_tab(self):
        self.tray.set_update_count(self.updates_tab.get_update_count())

    def refresh_cache_info(self):
        self.cache_mgr.get_cache_info()

    def refresh_all(self):
        """Actualiza todos los tabs con opcional de yield entre operaciones para UI responsive."""
        self._refresh_after_package_change()

    def quit_application(self):
        """Solicita confirmación antes de salir completamente."""
        reply = QMessageBox(self)
        reply.setWindowTitle(self.tr("Salir de Wakka"))
        reply.setWindowIcon(QIcon.fromTheme("application-exit"))
        reply.setText(self.tr("¿Cerrar Wakka?"))
        reply.setInformativeText(
            self.tr("Si cierras Wakka suspenderás las actualizaciones y limpiezas automáticas del sistema.\n"
                    "Puedes minimizarlo a la bandeja para que continúe trabajando en segundo plano.")
        )
        reply.setIcon(QMessageBox.Icon.Warning)

        btn_quit   = reply.addButton(self.tr("Cerrar Wakka"),       QMessageBox.ButtonRole.DestructiveRole)
        btn_tray   = reply.addButton(self.tr("Minimizar a bandeja"), QMessageBox.ButtonRole.AcceptRole)
        btn_cancel = reply.addButton(self.tr("Cancelar"),            QMessageBox.ButtonRole.RejectRole)

        btn_quit.setIcon(QIcon.fromTheme("application-exit"))
        btn_tray.setIcon(QIcon.fromTheme("go-down"))
        btn_cancel.setIcon(QIcon.fromTheme("dialog-cancel"))

        reply.setDefaultButton(btn_tray)
        reply.exec()

        clicked = reply.clickedButton()
        if clicked == btn_quit:
            self.tray.tray.hide()
            QApplication.quit()
        elif clicked == btn_tray:
            self.hide()
            if self.config_mgr.get("notifications", True):
                self.tray.show_notification(
                    self.tr("Wakka sigue ejecutándose"),
                    self.tr("La aplicación se ha minimizado a la bandeja del sistema")
                )
        # Si canceló, no hace nada

    def closeEvent(self, event):
        """Cerrar la ventana = minimizar a bandeja (comportamiento normal)."""
        event.ignore()
        self.hide()
        if self.config_mgr.get("notifications", True):
            self.tray.show_notification(
                self.tr("Wakka sigue ejecutándose"),
                self.tr("La aplicación se ha minimizado a la bandeja del sistema")
            )
