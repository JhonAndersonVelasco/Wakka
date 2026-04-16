from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QFileDialog, QHeaderView, QAbstractItemView, QLabel,
                             QCheckBox)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QIcon, QColor

class SearchTab(QWidget):
    install_package = pyqtSignal(str)
    install_selected = pyqtSignal(list)
    install_local = pyqtSignal(str)
    show_info = pyqtSignal(str, str)

    def __init__(self, yay_wrapper, parent=None):
        super().__init__(parent)
        self.yay = yay_wrapper
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Barra de búsqueda
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel(self.tr("<h2>Buscar paquetes</h2>")))

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.tr("Buscar aplicaciones..."))
        self.search_input.returnPressed.connect(self.do_search)
        search_layout.addWidget(self.search_input)

        search_btn = QPushButton(self.tr("Buscar"))
        search_btn.setIcon(QIcon.fromTheme("edit-find"))
        search_btn.clicked.connect(self.do_search)
        search_layout.addWidget(search_btn)

        # Botón instalar local integrado en el header
        local_btn = QPushButton(self.tr("📂 Instalar local"))
        local_btn.setToolTip(self.tr("Instalar paquete local (.pkg.tar.zst, .deb, .rpm)"))
        local_btn.clicked.connect(self.install_local_package)
        search_layout.addWidget(local_btn)

        self.install_selected_btn = QPushButton("⬇️ Instalar seleccionados")
        self.install_selected_btn.clicked.connect(self.on_install_selected)
        self.install_selected_btn.setEnabled(False)
        search_layout.addWidget(self.install_selected_btn)

        layout.addLayout(search_layout)

        # Resultados
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "", self.tr("Nombre"), self.tr("Versión"), self.tr("Repositorio"), self.tr("Votos"), self.tr("Popularidad"), self.tr("Acciones")
        ])

        # Ajuste inteligente de columnas
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch) # El nombre ocupa el resto

        self.table.setSortingEnabled(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)

    def do_search(self):
        query = self.search_input.text().strip()
        if not query:
            return

        self.table.setSortingEnabled(False)
        self.table.setRowCount(0) # Limpiar resultados anteriores
        results = self.yay.search_packages(query)
        self.table.setRowCount(len(results))

        for i, pkg in enumerate(results):
            # Checkbox de selección
            cb = QCheckBox()
            cb.stateChanged.connect(self.update_selection_status)
            container = QWidget()
            cb_layout = QHBoxLayout(container)
            cb_layout.addWidget(cb)
            cb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cb_layout.setContentsMargins(0, 0, 0, 0)
            self.table.setCellWidget(i, 0, container)

            # Nombre con Tooltip de descripción
            name_item = QTableWidgetItem(pkg.name)
            name_item.setToolTip(pkg.description)
            self.table.setItem(i, 1, name_item)

            # Versión
            self.table.setItem(i, 2, QTableWidgetItem(pkg.version))

            # Repositorio
            repo_item = QTableWidgetItem(pkg.repo)
            if pkg.repo == "aur":
                repo_item.setForeground(QColor("#FF9800"))
            self.table.setItem(i, 3, repo_item)

            # Votos (Numérico para ordenación correcta)
            v_item = QTableWidgetItem()
            try:
                v_item.setData(Qt.ItemDataRole.DisplayRole, int(pkg.votes))
            except:
                v_item.setData(Qt.ItemDataRole.DisplayRole, 0)
            self.table.setItem(i, 4, v_item)

            # Popularidad (Numérico para ordenación correcta)
            p_item = QTableWidgetItem()
            try:
                p_item.setData(Qt.ItemDataRole.DisplayRole, float(pkg.popularity))
            except:
                p_item.setData(Qt.ItemDataRole.DisplayRole, 0.0)
            self.table.setItem(i, 5, p_item)

            # Acciones: Info + Instalar
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

            inst_text = self.tr("Reinstalar") if pkg.installed else self.tr("Instalar")
            inst_btn = QPushButton(inst_text)
            inst_btn.setStyleSheet("background-color: #4CAF50; color: white;" if not pkg.installed else "background-color: #2196F3; color: white;")
            inst_btn.clicked.connect(lambda checked, n=pkg.name: self.install_package.emit(n))
            actions_layout.addWidget(inst_btn)

            self.table.setCellWidget(i, 6, actions_widget)

        self.table.setSortingEnabled(True)
        self.table.sortByColumn(5, Qt.SortOrder.DescendingOrder)
        self.update_selection_status()

    def update_selection_status(self):
        selected_count = 0
        for i in range(self.table.rowCount()):
            container = self.table.cellWidget(i, 0)
            if container and container.findChild(QCheckBox).isChecked():
                selected_count += 1
        self.install_selected_btn.setEnabled(selected_count > 0)
        self.install_selected_btn.setText(self.tr("⬇️ Instalar seleccionados ({0})").format(selected_count))

    def on_install_selected(self):
        selected = []
        for i in range(self.table.rowCount()):
            container = self.table.cellWidget(i, 0)
            if container and container.findChild(QCheckBox).isChecked():
                # Obtenemos el nombre de la columna 1 (Nombre)
                selected.append(self.table.item(i, 1).text())
        if selected:
            self.install_selected.emit(selected)

    def install_local_package(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Seleccionar paquete"),
            "",
            self.tr("Arch Linux (*.pkg.tar.zst);;Debian (*.deb);;RPM (*.rpm);;Todos los archivos (*)")
        )
        if file_path:
            self.install_local.emit(file_path)

    def refresh_view(self):
        if self.search_input.text().strip():
            self.do_search()
