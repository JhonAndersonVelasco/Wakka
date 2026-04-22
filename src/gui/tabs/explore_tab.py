from PyQt6.QtCore import pyqtSignal, Qt, QThread, QCoreApplication, QTimer
from PyQt6.QtGui import QIcon, QColor, QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, 
    QTableWidgetItem, QFileDialog, QHeaderView, 
    QAbstractItemView, QLabel, QCheckBox, QScrollArea, QFrame, 
    QGridLayout, QGroupBox, QStackedWidget
)
from gui.widgets import PackageTable
from pathlib import Path
import subprocess
import shutil

# --- Workers ---

class SuggestionsWorker(QThread):
    finished = pyqtSignal(dict)
    status_msg = pyqtSignal(str)

    def __init__(self, yay):
        super().__init__()
        self.yay = yay

    def run(self):
        # El callback permite que la UI reciba actualizaciones de texto
        results = self.yay.get_popular_suggestions(progress_callback=self.status_msg.emit)
        self.finished.emit(results)

class SearchWorker(QThread):
    finished = pyqtSignal(list)
    status_msg = pyqtSignal(str)

    def __init__(self, yay_wrapper, query):
        super().__init__()
        self.yay = yay_wrapper
        self.query = query

    def run(self):
        self.status_msg.emit(QCoreApplication.translate("SearchWorker", "Cargando resultados de búsqueda para '{0}'...").format(self.query))
        packages = self.yay.search_packages(self.query)
        self.finished.emit(packages)

# --- Components ---

class PackageCard(QFrame):
    install_clicked = pyqtSignal(str)
    info_clicked = pyqtSignal(str, str)  # nombre, descripción

    def __init__(self, package, parent=None):
        super().__init__(parent)
        self.package = package
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setStyleSheet("""
            PackageCard {
                background-color: palette(base);
                border-radius: 8px;
                border: 1px solid palette(mid);
                padding: 12px;
            }
            PackageCard:hover {
                border: 2px solid #2196F3;
            }
        """)
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout(self)

        # Info
        info_layout = QVBoxLayout()

        name_label = QLabel(f"<b>{self.package.name}</b>")
        name_label.setFont(QFont("Sans", 11, QFont.Weight.Bold))
        info_layout.addWidget(name_label)

        desc_label = QLabel(self.package.description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: palette(text); opacity: 0.8;")
        info_layout.addWidget(desc_label)

        meta_label = QLabel(self.tr("Versión: {0} • {1}").format(self.package.version, self.package.repo))
        meta_label.setStyleSheet("color: gray; font-size: 10px;")
        info_layout.addWidget(meta_label)

        layout.addLayout(info_layout, stretch=1)

        # Botones
        btn_layout = QVBoxLayout()

        info_btn = QPushButton(self.tr("ℹ️ Info"))
        info_btn.setToolTip(self.tr("Abrir la wiki de Arch y archlinux.org (solo nombre del paquete)"))
        info_btn.clicked.connect(lambda: self.info_clicked.emit(
            self.package.name,
            self.package.description
        ))
        btn_layout.addWidget(info_btn)

        install_btn = QPushButton(self.tr("⬇️ Instalar"))
        install_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 4px;
                padding: 6px 12px;
            }
            QPushButton:hover { background-color: #45a049; }
        """)
        install_btn.clicked.connect(lambda: self.install_clicked.emit(self.package.name))
        btn_layout.addWidget(install_btn)

        layout.addLayout(btn_layout)

# --- Main Tab ---

class ExploreTab(QWidget):
    install_package = pyqtSignal(str)
    install_selected = pyqtSignal(list)
    install_local = pyqtSignal(str)
    show_info = pyqtSignal(str, str)
    status_msg = pyqtSignal(str)

    def __init__(self, yay_wrapper, parent=None):
        super().__init__(parent)
        self.yay = yay_wrapper
        self.is_showing_suggestions = True
        self.search_worker = None # Mantener referencia al worker activo
        
        # Timer para búsqueda automática (debounce)
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.do_search)

        self.setup_ui()
        # Carga inicial de sugerencias
        QTimer.singleShot(100, self.load_suggestions)

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # --- Header y Búsqueda ---
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(10, 10, 10, 10)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.tr("Buscar aplicaciones o explorar categorías..."))
        self.search_input.setFixedHeight(35)
        self.search_input.setStyleSheet("font-size: 14px; padding: 5px; border-radius: 6px;")
        self.search_input.returnPressed.connect(self.do_search)
        self.search_input.textChanged.connect(self._on_search_text_changed)
        header_layout.addWidget(self.search_input, stretch=1)

        search_btn = QPushButton(self.tr("Buscar"))
        search_btn.setIcon(QIcon.fromTheme("edit-find"))
        search_btn.setFixedHeight(35)
        search_btn.clicked.connect(self.do_search)
        header_layout.addWidget(search_btn)

        local_btn = QPushButton(self.tr("📂 Instalar local"))
        local_btn.setFixedHeight(35)
        local_btn.clicked.connect(self.install_local_package)
        header_layout.addWidget(local_btn)

        self.install_selected_btn = QPushButton("⬇️ Instalar seleccionados")
        self.install_selected_btn.setFixedHeight(35)
        self.install_selected_btn.clicked.connect(self.on_install_selected)
        self.install_selected_btn.setEnabled(False)
        self.install_selected_btn.hide() # Solo visible en modo búsqueda
        header_layout.addWidget(self.install_selected_btn)

        layout.addLayout(header_layout)

        # --- Área de Contenido Stacker ---
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        # -> Vista 1: Sugerencias
        self.suggestions_scroll = QScrollArea()
        self.suggestions_scroll.setWidgetResizable(True)
        self.suggestions_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.suggestions_scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid palette(mid);
                border-radius: 8px;
                background-color: palette(base);
            }
        """)
        
        self.suggestions_container = QWidget()
        self.suggestions_container.setObjectName("SuggestionsContainer")
        self.suggestions_container.setStyleSheet("#SuggestionsContainer { background-color: transparent; }")
        self.suggestions_layout = QVBoxLayout(self.suggestions_container)
        self.suggestions_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.suggestions_layout.setSpacing(20)
        self.suggestions_layout.setContentsMargins(15, 15, 15, 15)
        
        self.suggestions_scroll.setWidget(self.suggestions_container)
        self.stack.addWidget(self.suggestions_scroll)

        # -> Vista 2: Tabla de Resultados
        self.search_table = PackageTable()
        self.search_table.setStyleSheet("""
            PackageTable {
                border: 1px solid palette(mid);
                border-radius: 8px;
                background-color: palette(base);
            }
            QHeaderView::section {
                background-color: palette(alternate-base);
                padding: 4px;
                border: none;
                border-bottom: 1px solid palette(mid);
            }
        """)
        self.search_table.setColumnCount(7)
        self.search_table.setHorizontalHeaderLabels([
            "", self.tr("Nombre"), self.tr("Versión"), self.tr("Repositorio"), self.tr("Votos"), self.tr("Popularidad"), self.tr("Acciones")
        ])
        header = self.search_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.search_table.enter_pressed.connect(self._on_search_table_enter)
        self.stack.addWidget(self.search_table)

    def _on_search_text_changed(self, text):
        if not text.strip():
            self.search_timer.stop()
            if not self.is_showing_suggestions:
                self.show_suggestions_view()
        else:
            # Iniciar/Reiniciar el timer de búsqueda automática
            self.search_timer.start(600)

    def show_suggestions_view(self):
        self.is_showing_suggestions = True
        self.stack.setCurrentWidget(self.suggestions_scroll)
        self.install_selected_btn.hide()
        # Solo cargamos si el layout está vacío (primer uso)
        if self.suggestions_layout.count() <= 1: 
            self.load_suggestions()

    def show_search_view(self):
        self.is_showing_suggestions = False
        self.stack.setCurrentWidget(self.search_table)
        self.install_selected_btn.show()

    # --- Lógica de Sugerencias ---

    def load_suggestions(self, force=False):
        # Evitar recargas si ya tenemos contenido, a menos que se fuerce
        if not force and self.suggestions_layout.count() > 1:
            return

        self.clear_layout(self.suggestions_layout)
        
        self.loading_label = QLabel(self.tr("🔍 Buscando recomendaciones en la Arch Wiki..."))
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label.setStyleSheet("font-size: 14px; color: #2196F3; padding: 50px;")
        self.suggestions_layout.addWidget(self.loading_label)

        self.sug_worker = SuggestionsWorker(self.yay)
        self.sug_worker.status_msg.connect(self.status_msg.emit)
        self.sug_worker.finished.connect(self.on_suggestions_finished)
        self.sug_worker.start()

    def on_suggestions_finished(self, suggestions_by_category):
        self.clear_layout(self.suggestions_layout)
        if not suggestions_by_category:
            empty = QLabel(self.tr("No se pudieron cargar las sugerencias."))
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.suggestions_layout.addWidget(empty)
            return

        for category, packages in suggestions_by_category.items():
            if not packages: continue
            
            translated_cat = QCoreApplication.translate("WikiCategories", category)
            group_box = QGroupBox(translated_cat)
            group_box.setStyleSheet("QGroupBox { font-weight: bold; margin-top: 10px; }")
            grid = QGridLayout(group_box)
            grid.setSpacing(15)

            for i, pkg in enumerate(packages):
                card = PackageCard(pkg)
                card.install_clicked.connect(self.install_package.emit)
                card.info_clicked.connect(self.show_info.emit)
                grid.addWidget(card, i // 2, i % 2)
            self.suggestions_layout.addWidget(group_box)
        
        self.suggestions_layout.addStretch(1)

    # --- Lógica de Búsqueda ---

    def do_search(self):
        query = self.search_input.text().strip()
        if not query:
            self.show_suggestions_view()
            return

        self.search_timer.stop() # Detener el timer si se disparó por Enter
        
        # Si ya hay una búsqueda en curso, intentar detenerla
        if self.search_worker and self.search_worker.isRunning():
            self.search_worker.terminate()
            self.search_worker.wait()

        self.show_search_view()
        self.search_table.setSortingEnabled(False)
        self.search_table.setRowCount(0)
        
        self.search_worker = SearchWorker(self.yay, query)
        self.search_worker.status_msg.connect(self.status_msg.emit)
        self.search_worker.finished.connect(self.on_search_finished)
        self.search_worker.start()

    def on_search_finished(self, results):
        self.search_input.setEnabled(True)
        self.search_table.setRowCount(len(results))

        for i, pkg in enumerate(results):
            # Checkbox
            cb = QCheckBox()
            cb.stateChanged.connect(self.update_selection_status)
            container = QWidget()
            cb_layout = QHBoxLayout(container)
            cb_layout.addWidget(cb)
            cb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cb_layout.setContentsMargins(0, 0, 0, 0)
            self.search_table.setCellWidget(i, 0, container)

            # Nombre
            name_item = QTableWidgetItem(pkg.name)
            name_item.setToolTip(pkg.description)
            self.search_table.setItem(i, 1, name_item)
            self.search_table.setItem(i, 2, QTableWidgetItem(pkg.version))
            
            repo_item = QTableWidgetItem(pkg.repo)
            if pkg.repo == "aur": repo_item.setForeground(QColor("#FF9800"))
            self.search_table.setItem(i, 3, repo_item)

            v_item = QTableWidgetItem()
            try: v_item.setData(Qt.ItemDataRole.DisplayRole, int(pkg.votes))
            except: v_item.setData(Qt.ItemDataRole.DisplayRole, 0)
            self.search_table.setItem(i, 4, v_item)

            p_item = QTableWidgetItem()
            try: p_item.setData(Qt.ItemDataRole.DisplayRole, float(pkg.popularity))
            except: p_item.setData(Qt.ItemDataRole.DisplayRole, 0.0)
            self.search_table.setItem(i, 5, p_item)

            # Acciones
            actions = QWidget()
            al = QHBoxLayout(actions)
            al.setContentsMargins(2, 0, 2, 0)
            al.setSpacing(4)
            
            info_btn = QPushButton("ℹ️")
            info_btn.setFixedWidth(30)
            info_btn.clicked.connect(lambda ch, p=pkg: self.show_info.emit(p.name, p.description))
            al.addWidget(info_btn)

            inst_text = self.tr("Reinstalar") if pkg.installed else self.tr("Instalar")
            inst_btn = QPushButton(inst_text)
            inst_btn.setStyleSheet("background-color: #4CAF50; color: white;" if not pkg.installed else "background-color: #2196F3; color: white;")
            inst_btn.clicked.connect(lambda ch, n=pkg.name: self.install_package.emit(n))
            al.addWidget(inst_btn)

            self.search_table.setCellWidget(i, 6, actions)

        self.search_table.setSortingEnabled(True)
        self.search_table.sortByColumn(5, Qt.SortOrder.DescendingOrder)
        self.update_selection_status()

    def _on_search_table_enter(self, row):
        # Al presionar Enter, instalar el paquete de esa fila
        name_item = self.search_table.item(row, 1)
        if name_item:
            self.install_package.emit(name_item.text())

    def update_selection_status(self):
        selected_count = 0
        for i in range(self.search_table.rowCount()):
            container = self.search_table.cellWidget(i, 0)
            if container and container.findChild(QCheckBox).isChecked():
                selected_count += 1
        self.install_selected_btn.setEnabled(selected_count > 0)
        self.install_selected_btn.setText(self.tr("⬇️ Instalar seleccionados ({0})").format(selected_count))

    def on_install_selected(self):
        selected = []
        for i in range(self.search_table.rowCount()):
            container = self.search_table.cellWidget(i, 0)
            if container and container.findChild(QCheckBox).isChecked():
                selected.append(self.search_table.item(i, 1).text())
        if selected:
            self.install_selected.emit(selected)

    def install_local_package(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, self.tr("Seleccionar paquete"), "",
            self.tr("Arch Linux (*.pkg.tar.zst);;Debian (*.deb);;RPM (*.rpm);;Todos los archivos (*)")
        )
        if file_path: self.install_local.emit(file_path)

    def clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                if item.widget(): item.widget().deleteLater()
                elif item.layout(): self.clear_layout(item.layout())

    def refresh_view(self):
        self.search_input.clear()
        self.search_input.setFocus()
        self.load_suggestions(force=False)

