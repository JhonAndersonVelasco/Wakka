"""
Wakka — Cache Management Page
Shows cache sizes with visual breakdown and provides manual/auto clean options.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QSpinBox, QFrame, QScrollArea,
)
from ..styles.icons import get_icon
from ..styles.theme import (
    style_transparent_bg, style_separator, style_icon_text,
    style_text, style_label, style_subtitle, style_status, get_color,
)
from core.cache_manager import CacheInfo, fmt_size
from core.config_manager import ConfigManager


class CachePage(QWidget):
    clean_pacman_requested     = pyqtSignal(int)   # keep N versions
    clean_pacman_uninstalled   = pyqtSignal()
    clean_yay_requested        = pyqtSignal()
    clean_orphans_requested    = pyqtSignal()
    refresh_requested          = pyqtSignal()

    def __init__(self, config: ConfigManager, parent=None):
        super().__init__(parent)
        self._config = config
        self._setup_ui()

    def _setup_ui(self):
        # ── Global layout ──
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        # ── Scroll area ──
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setStyleSheet(style_transparent_bg())

        self._content = QWidget()
        self._content.setStyleSheet(style_transparent_bg())
        layout = QVBoxLayout(self._content)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        self._scroll.setWidget(self._content)
        root.addWidget(self._scroll)

        # ── Cache Overview ────────────────────────────────────────────────
        overview = QGroupBox(self.tr("Caché del sistema"))
        ov_layout = QVBoxLayout(overview)
        ov_layout.setSpacing(14)

        # Total size banner
        total_row = QHBoxLayout()
        self._total_icon = QLabel("🗄️")
        self._total_icon.setStyleSheet(style_icon_text(32))
        total_col = QVBoxLayout()
        self._total_label = QLabel("—")
        self._total_label.setObjectName("CacheSizeLabel")
        self._total_sub = QLabel(self.tr("tamaño total de caché"))
        self._total_sub.setObjectName("CacheSizeSub")
        total_col.addWidget(self._total_label)
        total_col.addWidget(self._total_sub)
        total_row.addWidget(self._total_icon)
        total_row.addSpacing(12)
        total_row.addLayout(total_col)
        total_row.addStretch()

        refresh_btn = QPushButton()
        refresh_btn.setToolTip(self.tr("Actualizar tamaños"))
        refresh_btn.setIcon(get_icon("refresh", "#8892a4"))
        refresh_btn.setFixedSize(36, 36)
        refresh_btn.clicked.connect(self.refresh_requested)
        total_row.addWidget(refresh_btn)
        ov_layout.addLayout(total_row)

        # Breakdown
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(style_separator())
        ov_layout.addWidget(separator)

        breakdown = QHBoxLayout()
        breakdown.setSpacing(30)

        self._pacman_lbl = self._make_size_item("📦", self.tr("pacman"), "—")
        self._yay_lbl    = self._make_size_item("🔨", self.tr("AUR (yay)"), "—")

        breakdown.addLayout(self._pacman_lbl["layout"])
        breakdown.addLayout(self._yay_lbl["layout"])
        breakdown.addStretch()
        ov_layout.addLayout(breakdown)

        # ── Pacman Cache Actions ──────────────────────────────────────────
        pacman_group = QGroupBox(self.tr("Caché de Pacman"))
        pg_layout = QVBoxLayout(pacman_group)
        pg_layout.setSpacing(10)

        keep_row = QHBoxLayout()
        keep_lbl = QLabel(self.tr("Conservar versiones por paquete:"))
        keep_lbl.setStyleSheet(style_text("text_primary"))
        self._keep_spin = QSpinBox()
        self._keep_spin.setRange(0, 10)
        keep_val = self._config.get("cache.keep_versions", 2)
        self._keep_spin.setValue(keep_val)
        self._keep_spin.setFixedWidth(70)
        self._keep_spin.setToolTip(self.tr(
            "Número de versiones de paquete que se conservan en la caché de Pacman."
        ))
        self._keep_spin.valueChanged.connect(
            lambda v: self._config.set("cache.keep_versions", v)
        )
        keep_row.addWidget(keep_lbl)
        keep_row.addWidget(self._keep_spin)
        keep_row.addStretch()

        clean_pacman_btn = QPushButton(self.tr("🧹 Limpiar versiones antiguas de caché de Pacman"))
        clean_pacman_btn.setToolTip(self.tr(
            "Elimina versiones antiguas de la caché de pacman manteniendo las últimas versiones por paquete."
        ))
        clean_pacman_btn.clicked.connect(
            lambda: self.clean_pacman_requested.emit(self._keep_spin.value())
        )

        clean_uninst_btn = QPushButton(self.tr("🗑 Eliminar caché de desinstalados"))
        clean_uninst_btn.setToolTip(self.tr(
            "Elimina los archivos de caché de paquetes desinstalados en Pacman."
        ))
        clean_uninst_btn.clicked.connect(self.clean_pacman_uninstalled)

        pg_layout.addLayout(keep_row)
        pg_layout.addWidget(clean_pacman_btn)
        pg_layout.addWidget(clean_uninst_btn)

        # ── AUR Cache Actions ─────────────────────────────────────────────
        aur_group = QGroupBox(self.tr("Caché de AUR"))
        ag_layout = QVBoxLayout(aur_group)

        aur_info = QLabel(self.tr(
            "Elimina los directorios de compilación de yay/paru en ~/.cache/. Se recrearán automáticamente en la próxima instalación de AUR."
        ))
        aur_info.setWordWrap(True)
        aur_info.setStyleSheet(style_subtitle(12))

        clean_aur_btn = QPushButton(self.tr("🧹 Limpiar caché AUR"))
        clean_aur_btn.setToolTip(self.tr(
            "Elimina el caché de compilación de AUR para yay/paru."
        ))
        clean_aur_btn.clicked.connect(self.clean_yay_requested)

        ag_layout.addWidget(aur_info)
        ag_layout.addWidget(clean_aur_btn)

        # ── Orphans ───────────────────────────────────────────────────────
        orphan_group = QGroupBox(self.tr("Paquetes huérfanos"))
        or_layout = QVBoxLayout(orphan_group)

        or_info = QLabel(self.tr(
            "Los paquetes huérfanos fueron instalados como dependencias y ya no son necesarios."
        ))
        or_info.setWordWrap(True)
        or_info.setStyleSheet(style_subtitle(12))

        clean_orphan_btn = QPushButton(self.tr("🗑 Eliminar paquetes huérfanos"))
        clean_orphan_btn.setObjectName("DangerButton")
        clean_orphan_btn.clicked.connect(self.clean_orphans_requested)

        or_layout.addWidget(or_info)
        or_layout.addWidget(clean_orphan_btn)

        # ── Status ────────────────────────────────────────────────────────
        self._status = QLabel("")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(overview)
        layout.addWidget(pacman_group)
        layout.addWidget(aur_group)
        layout.addWidget(orphan_group)
        layout.addWidget(self._status)
        layout.addStretch()

    def _make_size_item(self, emoji: str, name: str, size: str) -> dict:
        layout = QVBoxLayout()
        layout.setSpacing(2)
        icon = QLabel(emoji)
        icon.setStyleSheet(style_icon_text(20))
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet(style_label(11))
        size_lbl = QLabel(size)
        size_lbl.setStyleSheet(style_text("text_primary", size=16, weight="600"))
        layout.addWidget(icon)
        layout.addWidget(name_lbl)
        layout.addWidget(size_lbl)
        return {"layout": layout, "size_lbl": size_lbl}

    # ─── Public API ────────────────────────────────────────────────────────

    def update_cache_info(self, info: CacheInfo):
        self._total_label.setText(info.total_size_str)
        self._pacman_lbl["size_lbl"].setText(info.pacman_size_str)
        self._yay_lbl["size_lbl"].setText(info.yay_size_str)

    def set_status(self, text: str, ok: bool = True):
        status_type = "success" if ok else "danger"
        self._status.setText(text)
        self._status.setStyleSheet(style_status(status_type, size=13) + " font-weight: 600;")
