"""
Wakka — Package Info Dialog
Detailed view of package metadata and AI review link.
"""
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
import webbrowser
import urllib.parse
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QTextBrowser, QPushButton, QDialogButtonBox, QFrame
)
from ..styles.icons import get_icon
from ..styles.theme import (
    style_icon_text, style_title, style_subtitle,
    style_browser, style_ai_card, style_text,
)

class PackageInfoDialog(QDialog):
    def __init__(self, name: str, info_text: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Detalles de %1").replace("%1", name))
        self.setMinimumSize(540, 600)
        self._name = name
        self._setup_ui(info_text)

    def _setup_ui(self, info_text: str):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header = QHBoxLayout()
        icon_lbl = QLabel("📦")
        icon_lbl.setStyleSheet(style_icon_text(32))

        title_col = QVBoxLayout()
        name_lbl = QLabel(self._name)
        name_lbl.setStyleSheet(style_title(20))
        subtitle = QLabel(self.tr("Información detallada del sistema"))
        subtitle.setStyleSheet(style_subtitle(13))

        title_col.addWidget(name_lbl)
        title_col.addWidget(subtitle)
        header.addWidget(icon_lbl)
        header.addLayout(title_col)
        header.addStretch()
        layout.addLayout(header)

        # Info text area
        self._browser = QTextBrowser()
        self._browser.setPlainText(info_text)
        self._browser.setStyleSheet(style_browser())
        layout.addWidget(self._browser)

        # AI Review Section
        ai_card = QFrame()
        ai_card.setObjectName("AICard")
        ai_card.setStyleSheet(style_ai_card())
        ai_layout = QVBoxLayout(ai_card)
        ai_layout.setContentsMargins(16, 16, 16, 16)

        ai_title = QLabel(self.tr("✨ Reseña Sugerida (IA)"))
        ai_title.setStyleSheet(style_text("accent", weight="bold"))
        ai_desc = QLabel(self.tr("¿Quieres saber para qué sirve exactamente este paquete? Consulta una reseña generada por IA en tu navegador."))
        ai_desc.setWordWrap(True)
        ai_desc.setStyleSheet(style_subtitle(11))

        self._ai_btn = QPushButton(self.tr("Ver reseña por IA"))
        self._ai_btn.setObjectName("PrimaryButton")
        self._ai_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._ai_btn.setStyleSheet("margin-top: 8px;")
        self._ai_btn.clicked.connect(self._on_ai_query)

        ai_layout.addWidget(ai_title)
        ai_layout.addWidget(ai_desc)
        ai_layout.addWidget(self._ai_btn)
        layout.addWidget(ai_card)

        # Buttons
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btns.button(QDialogButtonBox.StandardButton.Close).setText(self.tr("Cerrar"))
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _on_ai_query(self):
        """Opens Google Search with a pre-filled question about the package."""
        pregunta1 = self.tr("Para qué sirve el paquete ")
        pregunta2 = f"'{self._name}'"
        pregunta3 = self.tr(" en Arch Linux? Reseña breve y utilitaria.")
        pregunta = pregunta1 + pregunta2 + pregunta3
        base_url = "https://www.google.com/search"
        query_param = urllib.parse.urlencode({'q': pregunta})
        full_url = f"{base_url}?{query_param}"
        webbrowser.open(full_url)
