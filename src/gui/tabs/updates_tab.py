from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QCheckBox, QPushButton, QLabel,
                             QHeaderView, QAbstractItemView)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QColor

class UpdatesTab(QWidget):
    install_selected = pyqtSignal(list)  # Lista de nombres de paquetes
    install_all = pyqtSignal()
    show_info = pyqtSignal(str, str)
    refresh_requested = pyqtSignal()

    def __init__(self, yay_wrapper, parent=None):
        super().__init__(parent)
        self.yay = yay_wrapper
        self.packages = []
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Header
        header = QHBoxLayout()
        header.addWidget(QLabel(self.tr("<h2>Actualizaciones disponibles</h2>")))

        self.count_label = QLabel(self.tr("(0 paquetes)"))
        header.addWidget(self.count_label)
        header.addStretch()

        # Botones
        self.btn_refresh = QPushButton(self.tr("Refrescar"))
        self.btn_refresh.setIcon(QIcon.fromTheme("view-refresh"))
        self.btn_refresh.clicked.connect(self.refresh_requested.emit)
        header.addWidget(self.btn_refresh)

        self.btn_update_all = QPushButton(self.tr("Actualizar todo"))
        self.btn_update_all.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #45a049; }
        """)
        self.btn_update_all.clicked.connect(self.install_all.emit)
        header.addWidget(self.btn_update_all)

        self.btn_update_selected = QPushButton(self.tr("Actualizar seleccionados"))
        self.btn_update_selected.clicked.connect(self.on_update_selected)
        header.addWidget(self.btn_update_selected)

        layout.addLayout(header)

        # Tabla
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "", self.tr("Nombre"), self.tr("V. Actual"), self.tr("V. Nueva"), self.tr("Acciones")
        ])

        # Ajuste de columnas
        header_view = self.table.horizontalHeader()
        header_view.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        self.load_updates()

    def load_updates(self):
        self.table.setSortingEnabled(False)
        self.packages = self.yay.get_available_updates()
        self.table.setRowCount(len(self.packages))

        for i, pkg in enumerate(self.packages):
            # Checkbox
            cb = QCheckBox()
            cb.stateChanged.connect(self.update_selection_status)
            container = QWidget()
            cb_layout = QHBoxLayout(container)
            cb_layout.addWidget(cb)
            cb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cb_layout.setContentsMargins(0, 0, 0, 0)
            self.table.setCellWidget(i, 0, container)

            # Nombre
            name_item = QTableWidgetItem(pkg.name)
            name_item.setToolTip(pkg.description)
            self.table.setItem(i, 1, name_item)

            # Versión actual
            self.table.setItem(i, 2, QTableWidgetItem(pkg.install_date or self.tr("Desconocida")))

            # Nueva versión
            self.table.setItem(i, 3, QTableWidgetItem(pkg.version))

            # Acciones
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(2, 0, 2, 0)
            actions_layout.setSpacing(4)
            actions_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            info_btn = QPushButton("ℹ️")
            info_btn.setFixedWidth(28)
            info_btn.setToolTip(self.tr("Preguntar a google"))
            info_btn.clicked.connect(lambda checked, p=pkg: self.show_info.emit(p.name, p.description))
            actions_layout.addWidget(info_btn)

            update_btn = QPushButton(self.tr("Actualizar"))
            update_btn.setStyleSheet("background-color: #4CAF50; color: white;")
            update_btn.clicked.connect(lambda checked, n=pkg.name: self.install_selected.emit([n]))
            actions_layout.addWidget(update_btn)

            self.table.setCellWidget(i, 4, actions_widget)

        self.count_label.setText(self.tr("({0} paquetes)").format(len(self.packages)))
        self.btn_update_all.setEnabled(len(self.packages) > 0)
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(1, Qt.SortOrder.AscendingOrder)
        self.update_selection_status()

    def update_selection_status(self):
        selected_count = 0
        for i in range(self.table.rowCount()):
            container = self.table.cellWidget(i, 0)
            if container:
                cb = container.findChild(QCheckBox)
                if cb and cb.isChecked():
                    selected_count += 1
        self.btn_update_selected.setEnabled(selected_count > 0)
        self.btn_update_selected.setText(self.tr("Actualizar seleccionados ({0})").format(selected_count))

    def on_update_selected(self):
        selected = []
        for i in range(self.table.rowCount()):
            container = self.table.cellWidget(i, 0)
            if container:
                cb = container.findChild(QCheckBox)
                if cb and cb.isChecked():
                    selected.append(self.table.item(i, 1).text())
        if selected:
            self.install_selected.emit(selected)

    def get_update_count(self):
        return len(self.packages)

    def refresh_view(self):
        self.load_updates()
