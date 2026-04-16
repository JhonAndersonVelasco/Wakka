from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
                             QFrame, QLabel, QPushButton, QGridLayout, QGroupBox,
                             QProgressBar)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QCoreApplication
from PyQt6.QtGui import QFont
import random

class SuggestionsWorker(QThread):
    finished = pyqtSignal(dict)
    status = pyqtSignal(str)

    def __init__(self, yay):
        super().__init__()
        self.yay = yay

    def run(self):
        # El callback permite que la UI reciba actualizaciones de texto
        results = self.yay.get_popular_suggestions(progress_callback=self.status.emit)
        self.finished.emit(results)

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
        info_btn.setToolTip(self.tr("Preguntar a google sobre esta app"))
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

class SuggestionsTab(QWidget):
    install_package = pyqtSignal(str)
    show_info = pyqtSignal(str, str)
    status_msg = pyqtSignal(str) # Nueva señal para la barra de estado

    def __init__(self, yay_wrapper, parent=None):
        super().__init__(parent)
        self.yay = yay_wrapper
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Header
        header = QLabel(self.tr("📦 Aplicaciones populares recomendadas"))
        header.setStyleSheet("font-size: 20px; font-weight: bold; margin: 10px;")
        layout.addWidget(header)

        subtitle = QLabel(self.tr("Selecciona aplicaciones útiles para instalar en tu sistema"))
        subtitle.setStyleSheet("color: gray; margin-left: 10px; margin-bottom: 20px;")
        layout.addWidget(subtitle)

        # Scroll area para las cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.container = QWidget()
        # Changed from QGridLayout to QVBoxLayout for grouping
        self.main_vbox_layout = QVBoxLayout(self.container)
        self.main_vbox_layout.setAlignment(Qt.AlignmentFlag.AlignTop) # Align content to top
        self.main_vbox_layout.setSpacing(20) # Spacing between groups

        scroll.setWidget(self.container)
        layout.addWidget(scroll)

        self.load_suggestions()

    def clear_layout(self, layout):
        """Helper to clear all widgets from a layout."""
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    self.clear_layout(item.layout())

    def load_suggestions(self):
        self.clear_layout(self.main_vbox_layout)

        # Si ya existe un worker corriendo de una petición anterior, 
        # desconectamos sus señales para que no intente actualizar widgets eliminados
        if hasattr(self, 'worker') and self.worker and self.worker.isRunning():
            self.worker.status.disconnect()

        # Mostrar mensaje de carga inicial
        self.loading_label = QLabel(self.tr("🔍 Buscando recomendaciones en la Arch Wiki..."))
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label.setStyleSheet("font-size: 14px; color: #2196F3; padding: 20px;")
        self.main_vbox_layout.addWidget(self.loading_label)

        # Configurar y lanzar el hilo
        self.worker = SuggestionsWorker(self.yay)
        self.worker.status.connect(self.update_loading_status)
        self.worker.finished.connect(self.on_loading_finished)
        self.worker.start()

    def update_loading_status(self, message):
        try:
            # Verificamos que la etiqueta aún exista (que no haya sido borrada por clear_layout)
            if hasattr(self, 'loading_label') and self.loading_label:
                self.loading_label.setText(self.tr("🔍 {0}").format(message))
            self.status_msg.emit(message)
        except RuntimeError:
            # El objeto C++ fue eliminado por el recolector de Qt, ignoramos la señal
            pass

    def on_loading_finished(self, suggestions_by_category):
        self.clear_layout(self.main_vbox_layout)
        self.status_msg.emit(self.tr("Sugerencias cargadas")) # Emitir a la barra de estado de la ventana principal

        if not suggestions_by_category:
            empty_label = QLabel(self.tr("🎉 ¡Todas las aplicaciones populares ya están instaladas o no se encontraron sugerencias!"))
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setStyleSheet("color: gray; font-size: 16px; padding: 50px;")
            self.main_vbox_layout.addWidget(empty_label)
            return

        for category, packages in suggestions_by_category.items():
            if not packages:
                continue

            # Traducir el nombre de la categoría
            translated_cat = QCoreApplication.translate("WikiCategories", category)
            group_box = QGroupBox(translated_cat)
            group_box.setStyleSheet("QGroupBox { font-weight: bold; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 3px; }")
            category_grid_layout = QGridLayout(group_box)
            category_grid_layout.setSpacing(15)

            for i, pkg in enumerate(packages):
                card = PackageCard(pkg)
                card.install_clicked.connect(self.install_package.emit)
                card.info_clicked.connect(self.show_info.emit)
                category_grid_layout.addWidget(card, i // 2, i % 2) # 2 columns
            self.main_vbox_layout.addWidget(group_box)

        # Add a stretch at the end to push content to the top
        self.main_vbox_layout.addStretch(1)

    def refresh_view(self):
        self.load_suggestions()
