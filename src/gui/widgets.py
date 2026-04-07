"""
widgets.py — Widgets reutilizables compartidos entre las pestañas.
"""
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QCheckBox
from PyQt6.QtCore import Qt
from typing import Callable, Optional


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
