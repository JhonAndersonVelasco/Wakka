"""
widgets.py — Widgets reutilizables compartidos entre las pestañas.
"""
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QCheckBox, QTableWidget, QAbstractItemView
from PyQt6.QtCore import Qt, pyqtSignal
from typing import Callable, Optional

class PackageTable(QTableWidget):
    """
    Tabla personalizada para paquetes que maneja atajos de teclado y 
    desactiva la edición directa de celdas.
    """
    enter_pressed = pyqtSignal(int) # Emite la fila seleccionada

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setAlternatingRowColors(True)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            # Alternar checkbox en la primera columna
            row = self.currentRow()
            if row >= 0:
                container = self.cellWidget(row, 0)
                if container:
                    cb = container.findChild(QCheckBox)
                    if cb:
                        cb.setChecked(not cb.isChecked())
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            # Emitir señal de acción principal
            row = self.currentRow()
            if row >= 0:
                self.enter_pressed.emit(row)
        else:
            super().keyPressEvent(event)

def make_checkbox_widget(
    callback: Optional[Callable] = None,
    parent: Optional[QWidget] = None,
) -> tuple[QWidget, QCheckBox]:
    """
    Crea un widget contenedor con un QCheckBox centrado, listo para
    insertar en una celda de QTableWidget.

    Args:
        callback: Función opcional que se conecta a `stateChanged`.
        parent:   Widget padre opcional.

    Returns:
        Tupla ``(container, checkbox)`` para poder acceder al checkbox
        directamente sin necesidad de ``findChild``.
    """
    cb = QCheckBox(parent)
    container = QWidget(parent)
    layout = QHBoxLayout(container)
    layout.addWidget(cb)
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.setContentsMargins(0, 0, 0, 0)
    if callback is not None:
        cb.stateChanged.connect(callback)
    return container, cb
