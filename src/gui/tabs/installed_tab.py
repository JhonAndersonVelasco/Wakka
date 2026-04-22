from PyQt6.QtCore import pyqtSignal, Qt, QThread, QCoreApplication, QTimer
from PyQt6.QtGui import QIcon, QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QHeaderView, QCheckBox,
    QTableWidgetItem, QMessageBox, QLineEdit, QLabel
)
from gui.widgets import PackageTable, make_checkbox_widget
from datetime import datetime

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
    def __lt__(self, other):
        if isinstance(other, QTableWidgetItem):
            return self.data(Qt.ItemDataRole.UserRole) < other.data(Qt.ItemDataRole.UserRole)
        return super().__lt__(other)

class DateTableWidgetItem(QTableWidgetItem):
    def __lt__(self, other):
        if isinstance(other, QTableWidgetItem):
            return self.data(Qt.ItemDataRole.UserRole) < other.data(Qt.ItemDataRole.UserRole)
        return super().__lt__(other)

class InstalledTab(QWidget):
    remove_package = pyqtSignal(str)
    remove_selected = pyqtSignal(list)
    show_info = pyqtSignal(str, str)
    status_msg = pyqtSignal(str)

    def __init__(self, yay_wrapper, parent=None):
        super().__init__(parent)
        self.yay = yay_wrapper
        self.packages = []
        self.selected_packages = set()  # Almacena nombres de paquetes seleccionados
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 10)
        
        title_layout = QVBoxLayout()
        title_label = QLabel(self.tr("Aplicaciones instaladas"))
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: palette(text);")
        title_layout.addWidget(title_label)
        
        self.count_label = QLabel(self.tr("Cargando..."))
        self.count_label.setStyleSheet("color: gray; font-size: 12px;")
        title_layout.addWidget(self.count_label)
        header.addLayout(title_layout)

        header.addStretch()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.tr("Filtrar instaladas..."))
        self.search_input.setFixedHeight(35)
        self.search_input.setFixedWidth(300)
        self.search_input.setStyleSheet("padding-left: 10px; border-radius: 6px;")
        
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.filter_packages)
        
        self.search_input.textChanged.connect(self._on_search_text_changed)
        header.addWidget(self.search_input)

        refresh_btn = QPushButton("Refrescar")
        refresh_btn.setIcon(QIcon.fromTheme("view-refresh"))
        refresh_btn.setFixedHeight(35)
        refresh_btn.clicked.connect(self.refresh_view)
        header.addWidget(refresh_btn)

        self.remove_selected_btn = QPushButton("🗑️ Desinstalar seleccionados")
        self.remove_selected_btn.setFixedHeight(35)
        self.remove_selected_btn.setEnabled(False)
        self.remove_selected_btn.clicked.connect(self.on_remove_selected)
        header.addWidget(self.remove_selected_btn)

        layout.addLayout(header)

        self.table = PackageTable()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "", self.tr("Nombre"), self.tr("Versión"), self.tr("Tamaño"),
            self.tr("Instalado el"), self.tr("Último uso"), self.tr("Acciones")
        ])

        header_view = self.table.horizontalHeader()
        header_view.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        self.table.enter_pressed.connect(self._on_table_enter)
        layout.addWidget(self.table)

        self.loading_label = QLabel(self.tr("Cargando paquetes instalados..."))
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label.setStyleSheet("font-size: 14px; color: #2196F3; padding: 20px;")
        layout.addWidget(self.loading_label)
        self.loading_label.hide()

        self.load_packages()

    def load_packages(self):
        self.selected_packages.clear() # Reset de selección al cargar de nuevo
        self.table.setRowCount(0)
        self.loading_label.show()
        self.status_msg.emit(self.tr("Cargando paquetes instalados..."))

        self.worker = InstalledWorker(self.yay)
        self.worker.finished.connect(self.on_loading_finished)
        self.worker.status_msg.connect(self.status_msg.emit)
        self.worker.start()

    def on_loading_finished(self, packages):
        self.packages = packages
        self.loading_label.hide()
        self.count_label.setText(self.tr("{0} paquetes instalados").format(len(packages)))
        self.status_msg.emit(self.tr("Paquetes instalados cargados"))
        self.update_table(self.packages)

    def _parse_size_to_bytes(self, size_str):
        try:
            s = size_str.replace(',', '.')
            parts = s.split()
            if not parts: return 0
            val = float(parts[0])
            unit = parts[1].upper()
            multipliers = {"B": 1, "KIB": 1024, "MIB": 1024**2, "GIB": 1024**3, "TIB": 1024**4}
            return val * multipliers.get(unit, 1)
        except:
            return 0

    def _parse_date_to_timestamp(self, date_str):
        if not date_str or date_str == "-":
            return 0
        date_formats = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%b %d %Y", "%d %b %Y", "%B %d %Y", "%d %B %Y", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S"]
        for fmt in date_formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return int(dt.timestamp())
            except ValueError:
                continue
        return 0

    def update_table(self, packages):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(packages))

        for i, pkg in enumerate(packages):
            # Checkbox usando el helper de widgets.py
            container, cb = make_checkbox_widget(
                callback=lambda state, name=pkg.name: self._toggle_selection(name, state),
                parent=self.table
            )
            # Restaurar estado si ya estaba seleccionado
            if pkg.name in self.selected_packages:
                cb.setChecked(True)
            
            self.table.setCellWidget(i, 0, container)

            name_item = QTableWidgetItem(pkg.name)
            name_item.setToolTip(pkg.description or self.tr("Paquete instalado en el sistema"))
            self.table.setItem(i, 1, name_item)

            self.table.setItem(i, 2, QTableWidgetItem(pkg.version))

            size_item = NumericTableWidgetItem(pkg.size)
            size_item.setData(Qt.ItemDataRole.UserRole, self._parse_size_to_bytes(pkg.size))
            self.table.setItem(i, 3, size_item)

            install_date_item = DateTableWidgetItem(pkg.install_date)
            install_date_item.setData(Qt.ItemDataRole.UserRole, self._parse_date_to_timestamp(pkg.install_date))
            self.table.setItem(i, 4, install_date_item)

            last_used_text = pkg.last_used if pkg.last_used else self.tr("-")
            last_used_item = DateTableWidgetItem(last_used_text)
            last_used_item.setData(Qt.ItemDataRole.UserRole, self._parse_date_to_timestamp(pkg.last_used) if pkg.last_used else 0)
            if not pkg.last_used:
                last_used_item.setForeground(QColor("gray"))
            self.table.setItem(i, 5, last_used_item)

            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(2, 0, 2, 0)
            actions_layout.setSpacing(4)

            info_btn = QPushButton("ℹ️")
            info_btn.setFixedWidth(30)
            info_btn.clicked.connect(lambda checked, p=pkg: self.show_info.emit(p.name, p.description))
            actions_layout.addWidget(info_btn)

            remove_btn = QPushButton(self.tr("Desinstalar"))
            remove_btn.setStyleSheet("background-color: #f44336; color: white;")
            remove_btn.clicked.connect(lambda checked, p=pkg.name: self.confirm_remove(p))
            actions_layout.addWidget(remove_btn)

            self.table.setCellWidget(i, 6, actions_widget)

        self.table.sortByColumn(1, Qt.SortOrder.AscendingOrder)
        self.table.setSortingEnabled(True)
        self._update_ui_selection_count()

    def _toggle_selection(self, package_name, state):
        """Maneja la persistencia del set de seleccionados"""
        if state == 2: # Checked
            self.selected_packages.add(package_name)
        else: # Unchecked
            self.selected_packages.discard(package_name)
        self._update_ui_selection_count()

    def _update_ui_selection_count(self):
        count = len(self.selected_packages)
        self.remove_selected_btn.setEnabled(count > 0)
        self.remove_selected_btn.setText(self.tr("🗑️ Desinstalar seleccionados ({0})").format(count))

    def _on_table_enter(self, row):
        name_item = self.table.item(row, 1)
        if name_item:
            self.confirm_remove(name_item.text())

    def on_remove_selected(self):
        if self.selected_packages:
            reply = QMessageBox.question(
                self, self.tr("Confirmar"), self.tr("¿Desinstalar {0} paquetes?").format(len(self.selected_packages)),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                # Emitimos la lista y limpiamos el set
                selected_list = list(self.selected_packages)
                self.remove_selected.emit(selected_list)
                self.selected_packages.clear()

    def _on_search_text_changed(self, text):
        self.search_timer.start(300)

    def filter_packages(self):
        text = self.search_input.text().lower()
        filtered = [
            p for p in self.packages 
            if text in p.name.lower() or (p.description and text in p.description.lower())
        ]
        self.update_table(filtered)

    def confirm_remove(self, package_name):
        reply = QMessageBox.question(
            self, self.tr("Confirmar desinstalación"), self.tr("¿Deseas desinstalar {0}?").format(package_name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.remove_package.emit(package_name)

    def refresh_view(self):
        self.search_input.clear()
        self.selected_packages.clear() # Limpiar selección al refrescar manualmente
        self.load_packages()