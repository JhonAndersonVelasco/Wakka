import os
from xml.etree import ElementTree as ET
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QLineEdit, QPushButton, QLabel, 
                             QMessageBox, QHeaderView, QFileDialog)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from core.translator import Translator

class TranslationEditorDialog(QDialog):
    def __init__(self, ts_path, parent=None):
        super().__init__(parent)
        self.ts_path = ts_path
        self.setWindowTitle(f"Wakka Translator - {os.path.basename(ts_path)}")
        self.resize(1100, 750)
        
        self.COLOR_EMPTY = QColor("#fff9c4")  # Amarillo claro
        self.COLOR_FILLED = QColor("#c8e6c9") # Verde claro
        
        self.setup_ui()
        self.load_translations()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Upper Tools
        tools_layout = QHBoxLayout()
        
        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.tr("🔍 Buscar texto..."))
        self.search_input.textChanged.connect(self.filter_table)
        tools_layout.addWidget(self.search_input, 2)
        
        tools_layout.addStretch(1)
        
        # External Work Buttons
        self.btn_export = QPushButton(self.tr("📤 Exportar a .txt"))
        self.btn_export.setToolTip(self.tr("Exporta los textos originales a un archivo para traducirlos externamente."))
        self.btn_export.clicked.connect(self.export_original_texts)
        
        self.btn_import = QPushButton(self.tr("📥 Importar desde .txt"))
        self.btn_import.setToolTip(self.tr("Importa las traducciones desde un archivo (una por línea, conservando el orden)."))
        self.btn_import.clicked.connect(self.import_translations)
        
        tools_layout.addWidget(self.btn_export)
        tools_layout.addWidget(self.btn_import)
        
        layout.addLayout(tools_layout)
        
        # Instructions Label
        info_lbl = QLabel(self.tr("💡 Tip: Si traduces externamente, no borres ni cambies el orden de las líneas del archivo .txt"))
        info_lbl.setStyleSheet("color: #666; font-style: italic; font-size: 11px;")
        layout.addWidget(info_lbl)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels([
            self.tr("Contexto"), 
            self.tr("Texto Original"), 
            self.tr("Traducción")
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        
        # Connect signal for color updates
        self.table.itemChanged.connect(self.on_item_changed)
        layout.addWidget(self.table)
        
        # Bottom Buttons
        btns_layout = QHBoxLayout()
        self.btn_cancel = QPushButton(self.tr("Cancelar"))
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_save = QPushButton(self.tr("Guardar y Compilar"))
        self.btn_save.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; min-width: 150px; padding: 10px;")
        self.btn_save.clicked.connect(self.save_translations)
        
        btns_layout.addStretch()
        btns_layout.addWidget(self.btn_cancel)
        btns_layout.addWidget(self.btn_save)
        layout.addLayout(btns_layout)

    def load_translations(self):
        try:
            tree = ET.parse(self.ts_path)
            root = tree.getroot()
            self.data = [] # List of {node, row}
            
            # Disable signals while loading to avoid color loop
            self.table.blockSignals(True)
            
            row = 0
            for context in root.findall('context'):
                ctx_name = context.find('name').text
                for message in context.findall('message'):
                    source = message.find('source').text
                    translation_node = message.find('translation')
                    
                    is_unfinished = translation_node.get('type') == 'unfinished'
                    translation_text = "" if is_unfinished else (translation_node.text or "")
                    
                    self.table.insertRow(row)
                    
                    # Context
                    ctx_item = QTableWidgetItem(ctx_name)
                    ctx_item.setFlags(ctx_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    ctx_item.setForeground(Qt.GlobalColor.gray)
                    self.table.setItem(row, 0, ctx_item)
                    
                    # Source
                    src_item = QTableWidgetItem(source)
                    src_item.setFlags(src_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.table.setItem(row, 1, src_item)
                    
                    # Translation
                    trans_item = QTableWidgetItem(translation_text)
                    self.table.setItem(row, 2, trans_item)
                    self.update_row_color(row, translation_text)
                    
                    self.data.append({'node': translation_node, 'row': row})
                    row += 1
            
            self.table.blockSignals(False)
            self.tree = tree
            
        except Exception as e:
            QMessageBox.critical(self, self.tr("Error"), f"No se pudo cargar: {e}")

    def on_item_changed(self, item):
        if item.column() == 2:
            self.update_row_color(item.row(), item.text())

    def update_row_color(self, row, text):
        color = self.COLOR_FILLED if text.strip() else self.COLOR_EMPTY
        item = self.table.item(row, 2)
        if item:
            item.setBackground(color)
            item.setForeground(QColor("black"))

    def filter_table(self):
        query = self.search_input.text().lower()
        for i in range(self.table.rowCount()):
            src = self.table.item(i, 1).text().lower()
            trans = self.table.item(i, 2).text().lower()
            self.table.setRowHidden(i, query not in src and query not in trans)

    def export_original_texts(self):
        file_path, _ = QFileDialog.getSaveFileName(self, self.tr("Guardar textos para traducir"), "original_texts.txt", "Text Files (*.txt)")
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    for i in range(self.table.rowCount()):
                        # Escapamos los saltos de línea para que cada celda sea 1 sola línea en el txt
                        text = self.table.item(i, 1).text().replace("\n", "\\n")
                        f.write(text + "\n")
                QMessageBox.information(self, self.tr("Exportación Exitosa"), 
                                        self.tr("Se han exportado {0} líneas.\n\nTradúcelas externamente y NO quites ni cambies el orden de las líneas.").format(self.table.rowCount()))
            except Exception as e:
                QMessageBox.critical(self, self.tr("Error"), f"Error al exportar: {e}")

    def import_translations(self):
        msg = self.tr("⚠️ ATENCIÓN: El archivo debe tener exactamente una traducción por línea y conservar el orden original.\n\n¿Deseas continuar?")
        if QMessageBox.question(self, self.tr("Importar traducciones"), msg) != QMessageBox.StandardButton.Yes:
            return
            
        file_path, _ = QFileDialog.getOpenFileName(self, self.tr("Seleccionar archivo traducido"), "", "Text Files (*.txt)")
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    # Leemos cada línea y des-escapamos los saltos de línea
                    lines = [line.strip("\r\n").replace("\\n", "\n") for line in f.readlines()]
                
                # Si la última línea es vacía (por el último \n), la ignoramos
                if len(lines) > self.table.rowCount() and not lines[-1]:
                    lines.pop()
                
                if len(lines) != self.table.rowCount():
                    QMessageBox.warning(self, self.tr("Error de Formato"), 
                                        self.tr("El archivo tiene {0} líneas, pero se esperan {1}.\nNo se puede importar.").format(len(lines), self.table.rowCount()))
                    return
                
                self.table.blockSignals(True)
                for i, line in enumerate(lines):
                    self.table.item(i, 2).setText(line)
                    self.update_row_color(i, line)
                self.table.blockSignals(False)
                
                QMessageBox.information(self, self.tr("Importación Completa"), self.tr("Las traducciones han sido cargadas en la tabla."))
            except Exception as e:
                QMessageBox.critical(self, self.tr("Error"), f"Error al importar: {e}")

    def save_translations(self):
        # Verificar campos vacíos
        empty_count = 0
        for i in range(self.table.rowCount()):
            if not self.table.item(i, 2).text().strip():
                empty_count += 1
        
        if empty_count > 0:
            msg = self.tr("Hay {0} textos sin traducir (en amarillo).\n\n¿Deseas guardar el progreso de todos modos?").format(empty_count)
            res = QMessageBox.warning(self, self.tr("Campos Vacíos"), msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if res == QMessageBox.StandardButton.No:
                return

        try:
            for item in self.data:
                node = item['node']
                row = item['row']
                new_text = self.table.item(row, 2).text().strip()
                
                if not new_text:
                    node.text = None
                    node.set('type', 'unfinished')
                else:
                    node.text = new_text
                    if 'type' in node.attrib:
                        del node.attrib['type']
            
            self.tree.write(self.ts_path, encoding='utf-8', xml_declaration=True)
            success, msg = Translator.compile_ts(self.ts_path)
            if success:
                QMessageBox.information(self, self.tr("Éxito"), 
                                        self.tr("Cambios guardados y compilados.\nReinicia Wakka para aplicarlos."))
                self.accept()
            else:
                QMessageBox.warning(self, self.tr("Error al Compilar"), msg)
                self.accept()
                
        except Exception as e:
            QMessageBox.critical(self, self.tr("Error"), f"Error al guardar: {e}")

