from __future__ import annotations

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QFrame,
)
from ..styles.theme import style_text, style_separator, style_title


class HelpPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        title = QLabel(self.tr("Ayuda rápida"))
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        body1 = self.tr("Para empezar, utiliza la barra lateral para revisar actualizaciones, ver paquetes instalados, explorar nuevos paquetes y limpiar la caché del sistema.")
        body2 = self.tr("Haz clic en cada sección para acceder rápidamente a las acciones disponibles y encuentra las opciones de la aplicación en Configuración.")
        body = QLabel(body1 + "\n" + body2)
        body.setWordWrap(True)
        body.setStyleSheet(style_text("text_primary", size=13))
        layout.addWidget(body)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(style_separator())
        layout.addWidget(separator)

        about_title = QLabel(self.tr("Acerca de"))
        about_title.setStyleSheet(style_title(14) + " margin-bottom: 8px;")
        layout.addWidget(about_title)

        about_text1 = self.tr("Wakka te ayuda a gestionar paquetes en sistemas basados en Arch con una interfaz sencilla.")
        about_text2 = self.tr("Usa la barra lateral para explorar actualizaciones, paquetes instalados, repositorios y opciones de caché.")
        about_text3 = self.tr("Esta sección ofrece una visión general del programa.")
        about_text4 = "Jhon Velasco\njhandervelbux@gmail.com\n© 2026 Wakka —"
        about_text5 = self.tr(" un asistente ligero para gestionar paquetes en sistemas basados en Arch.")
        about_text = QLabel(about_text1 +"\n" + about_text2 + "\n" + about_text3 + "\n\n" + about_text4 + about_text5)
        about_text.setWordWrap(True)
        about_text.setStyleSheet(style_text("text_primary", size=13))
        layout.addWidget(about_text)

        layout.addStretch()

        donate_btn = QPushButton(self.tr("Donar"))
        donate_btn.setFixedHeight(38)
        donate_btn.setObjectName("PrimaryButton")
        donate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        donate_btn.clicked.connect(self._open_donate_link)
        layout.addWidget(donate_btn, alignment=Qt.AlignmentFlag.AlignLeft)

    def _open_donate_link(self) -> None:
        QDesktopServices.openUrl(QUrl("https://www.paypal.com/donate/?hosted_button_id=FX7FC6R7WJ85W"))
