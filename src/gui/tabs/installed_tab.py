from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QPushButton, QHeaderView, QCheckBox,
                             QAbstractItemView, QMessageBox, QLineEdit, QLabel)
from PyQt6.QtCore import pyqtSignal, Qt, QThread, QCoreApplication
from PyQt6.QtGui import QIcon

class InstalledWorker(QThread):
    finished = pyqtSignal(list)
    status_msg = pyqtSignal(str)

    def __init__(self, yay_wrapper):
        super().__init__()
        self.yay = yay_wrapper

    def run(self):
        self.status_msg.emit(QCoreApplication.translate("InstalledWorker", "Cargando paquetes instalados..."))
        packages = self.yay.get_installed_packages()
        self.finished.emit(packages)

class NumericTableWidgetItem(QTableWidgetItem):
    """Item de tabla que se ordena numéricamente usando UserRole"""
    def __lt__(self, other):
        if isinstance(other, QTableWidgetItem):
            return self.data(Qt.ItemDataRole.UserRole) < other.data(Qt.ItemDataRole.UserRole)
        return super().__lt__(other)

class InstalledTab(QWidget):
    remove_package = pyqtSignal(str)
    remove_selected = pyqtSignal(list)
    show_info = pyqtSignal(str, str)
    status_msg = pyqtSignal(str) # Nueva señal para la barra de estado

    def __init__(self, yay_wrapper, parent=None):
        super().__init__(parent)
        self.yay = yay_wrapper
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Header
        header = QHBoxLayout()
        header.addWidget(QLabel(self.tr("<h2>Aplicaciones instaladas</h2>")))

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.tr("Filtrar instaladas..."))
        self.search_input.textChanged.connect(self.filter_packages)
        header.addWidget(self.search_input)

        refresh_btn = QPushButton("Refrescar")
        refresh_btn.setIcon(QIcon.fromTheme("view-refresh"))
        refresh_btn.clicked.connect(self.load_packages)
        header.addWidget(refresh_btn)

        self.remove_selected_btn = QPushButton("🗑️ Desinstalar seleccionados")
        self.remove_selected_btn.setEnabled(False)
        self.remove_selected_btn.clicked.connect(self.on_remove_selected)
        header.addWidget(self.remove_selected_btn)

        layout.addLayout(header)

        # Tabla
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "", self.tr("Nombre"), self.tr("Versión"), self.tr("Tamaño"), self.tr("Instalado el"), self.tr("Acciones")
        ])

        header_view = self.table.horizontalHeader()
        header_view.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        self.table.setSortingEnabled(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)

        self.loading_label = QLabel(self.tr("Cargando paquetes instalados...")) # Etiqueta de carga inicial
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label.setStyleSheet("font-size: 14px; color: #2196F3; padding: 20px;")
        layout.addWidget(self.loading_label)
        self.loading_label.hide() # Ocultar inicialmente, mostrar al cargar

        self.load_packages()

    def load_packages(self):
        self.table.setRowCount(0) # Limpiar tabla
        self.loading_label.show() # Mostrar mensaje de carga
        self.status_msg.emit(self.tr("Cargando paquetes instalados..."))

        self.worker = InstalledWorker(self.yay)
        self.worker.finished.connect(self.on_loading_finished)
        self.worker.status_msg.connect(self.status_msg.emit) # Conectar el estado del worker al estado de la pestaña
        self.worker.start()

    def on_loading_finished(self, packages):
        self.packages = packages # Almacenar los paquetes cargados
        self.loading_label.hide() # Ocultar mensaje de carga
        self.status_msg.emit(self.tr("Paquetes instalados cargados")) # Limpiar barra de estado después de 3 segundos
        self.update_table(self.packages)

    def _parse_size_to_bytes(self, size_str):
        """Convierte '1723,94 KiB' o '9.87 MiB' a un float para ordenar"""
        try:
            # Reemplazar coma decimal por punto y extraer número y unidad
            s = size_str.replace(',', '.')
            parts = s.split()
            if not parts: return 0
            val = float(parts[0])
            unit = parts[1].upper()
            multipliers = {"B": 1, "KIB": 1024, "MIB": 1024**2, "GIB": 1024**3, "TIB": 1024**4}
            return val * multipliers.get(unit, 1)
        except:
            return 0

    def update_table(self, packages):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(packages))

        for i, pkg in enumerate(packages):
            # Checkbox
            cb = QCheckBox()
            cb.stateChanged.connect(self.update_selection_status)
            container = QWidget()
            cb_layout = QHBoxLayout(container)
            cb_layout.addWidget(cb)
            cb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cb_layout.setContentsMargins(0, 0, 0, 0)
            self.table.setCellWidget(i, 0, container)

            # Nombre + Tooltip
            name_item = QTableWidgetItem(pkg.name)
            name_item.setToolTip(pkg.description or self.tr("Paquete instalado en el sistema"))
            self.table.setItem(i, 1, name_item)

            self.table.setItem(i, 2, QTableWidgetItem(pkg.version))

            # Tamaño de instalación (Ordenable)
            size_item = NumericTableWidgetItem(pkg.size)
            size_bytes = self._parse_size_to_bytes(pkg.size)
            size_item.setData(Qt.ItemDataRole.UserRole, size_bytes)
            self.table.setItem(i, 3, size_item)

            # Fecha de instalación
            self.table.setItem(i, 4, QTableWidgetItem(pkg.install_date))

            # Acciones
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(2, 0, 2, 0)
            actions_layout.setSpacing(4)
            actions_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            info_btn = QPushButton("ℹ️")
            info_btn.setFixedWidth(30)
            info_btn.setToolTip(self.tr("Preguntar a Google sobre este paquete"))
            info_btn.clicked.connect(lambda checked, p=pkg: self.show_info.emit(p.name, p.description))
            actions_layout.addWidget(info_btn)

            remove_btn = QPushButton(self.tr("Desinstalar"))
            remove_btn.setToolTip(self.tr("Desinstalar"))
            remove_btn.setStyleSheet("background-color: #f44336; color: white;")
            remove_btn.clicked.connect(lambda checked, p=pkg.name: self.confirm_remove(p))
            actions_layout.addWidget(remove_btn)

            self.table.setCellWidget(i, 5, actions_widget)

        self.table.setSortingEnabled(True)
        self.table.sortByColumn(1, Qt.SortOrder.AscendingOrder)
        self.update_selection_status()

    def update_selection_status(self):
        selected_count = 0
        for i in range(self.table.rowCount()):
            container = self.table.cellWidget(i, 0)
            if container and container.findChild(QCheckBox).isChecked():
                selected_count += 1
        self.remove_selected_btn.setEnabled(selected_count > 0)
        self.remove_selected_btn.setText(self.tr("🗑️ Desinstalar seleccionados ({0})").format(selected_count))

    def on_remove_selected(self):
        selected = []
        for i in range(self.table.rowCount()):
            container = self.table.cellWidget(i, 0)
            if container and container.findChild(QCheckBox).isChecked():
                selected.append(self.table.item(i, 1).text())

        if selected:
            reply = QMessageBox.question(
                self, self.tr("Confirmar"), self.tr("¿Desinstalar {0} paquetes?").format(len(selected)),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.remove_selected.emit(selected)

    def filter_packages(self, text):
        search_text = text.lower()
        filtered = [
            p for p in self.packages 
            if search_text in p.name.lower() or (p.description and search_text in p.description.lower())
        ]
        self.update_table(filtered)

    def confirm_remove(self, package_name):
        reply = QMessageBox.question(
            self,
            self.tr("Confirmar desinstalación"),
            self.tr("¿Deseas desinstalar {0}?").format(package_name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.remove_package.emit(package_name)

    def refresh_view(self):
        self.load_packages()
