from PyQt6.QtCore import Qt, pyqtSignal, QThread, QCoreApplication
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QSpinBox, QFrame, QScrollArea,
    QCheckBox, QComboBox, QListView
)
from PyQt6.QtGui import QIcon
from core.cache_manager import CacheInfo
from core.config_manager import ConfigManager

# Estilos básicos
def style_transparent_bg() -> str:
    return "" # Not used directly

def style_separator() -> str:
    return "background-color: palette(mid); max-height: 1px;"

def style_icon_text(size: int) -> str:
    return f"font-size: {size}px;"

def style_text(role: str, size: int = 12, weight: str = "normal") -> str:
    return f"font-size: {size}px; font-weight: {weight};"

def style_label(size: int) -> str:
    return f"font-size: {size}px; color: gray;"

def style_subtitle(size: int) -> str:
    return f"font-size: {size}px; color: gray;"

def style_status(status_type: str, size: int) -> str:
    colors = {"success": "#4CAF50", "danger": "#f44336", "info": "#2196F3"}
    return f"font-size: {size}px; color: {colors.get(status_type, 'gray')};"

class CacheWorker(QThread):
    finished = pyqtSignal(list)
    status_msg = pyqtSignal(str)

    def __init__(self, yay_wrapper):
        super().__init__()
        self.yay = yay_wrapper

    def run(self):
        self.status_msg.emit(QCoreApplication.translate("InstalledWorker", "Administrar el caché de paquetes..."))
        packages = self.yay.get_installed_packages()
        self.finished.emit(packages)

class CacheTab(QWidget):
    clean_pacman_requested     = pyqtSignal(int)
    clean_pacman_uninstalled   = pyqtSignal()
    clean_yay_requested        = pyqtSignal()
    clean_orphans_requested    = pyqtSignal()
    refresh_requested          = pyqtSignal()
    status_msg                 = pyqtSignal(str)

    def __init__(self, config: ConfigManager, parent=None):
        super().__init__(parent)
        self._config = config
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        
        # Header
        header = QLabel(self.tr("🧹 Limpieza del Sistema"))
        header.setStyleSheet("font-size: 20px; font-weight: bold; margin: 10px;")
        root.addWidget(header)

        subtitle = QLabel(self.tr("Elimina archivos innecesarios y huérfanos para liberar espacio en el disco"))
        subtitle.setStyleSheet("color: gray; margin-left: 10px; margin-bottom: 20px;")
        root.addWidget(subtitle)

        self._scroll = QScrollArea()
        self._scroll.setObjectName("CacheScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setStyleSheet("#CacheScroll { background-color: transparent; }")

        self._content = QWidget()
        self._content.setObjectName("CacheContent")
        self._content.setStyleSheet("#CacheContent { background-color: transparent; }")
        layout = QVBoxLayout(self._content)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        self._scroll.setWidget(self._content)
        root.addWidget(self._scroll)

        overview = QGroupBox(self.tr("Caché del sistema"))
        ov_layout = QVBoxLayout(overview)
        ov_layout.setSpacing(14)

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

        refresh_btn = QPushButton(self.tr("Refrescar"))
        refresh_btn.setIcon(QIcon.fromTheme("view-refresh"))
        refresh_btn.setToolTip(self.tr("Actualizar tamaños de almacenamiento"))
        refresh_btn.clicked.connect(self.refresh_requested.emit)
        total_row.addWidget(refresh_btn)
        ov_layout.addLayout(total_row)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(style_separator())
        ov_layout.addWidget(separator)

        breakdown = QHBoxLayout()
        breakdown.setSpacing(30)

        self._pacman_lbl = self._make_size_item("📦", "pacman", "—")
        self._yay_lbl    = self._make_size_item("🔨", self.tr("AUR (yay)"), "—")

        breakdown.addLayout(self._pacman_lbl["layout"])
        breakdown.addLayout(self._yay_lbl["layout"])
        breakdown.addStretch()
        ov_layout.addLayout(breakdown)

        # Programación de limpieza
        sched_group = QGroupBox(self.tr("Programación de limpieza"))
        sg_layout = QVBoxLayout(sched_group)
        
        self._auto_clean_chk = QCheckBox(self.tr("Limpiar automáticamente"))
        self._auto_clean_chk.setToolTip(self.tr("Habilita la limpieza automática de caché y paquetes huérfanos."))
        self._auto_clean_chk.setChecked(self._config.get("cache.auto_clean", False))
        self._auto_clean_chk.stateChanged.connect(self._on_auto_clean_changed)
        
        freq_lbl = QLabel(self.tr("Frecuencia:"))
        self._freq_combo = QComboBox()
        self._freq_combo.setView(QListView())
        self._freq_combo.setMinimumWidth(120)
        self._freq_combo.addItems([
            self.tr("Diariamente"), self.tr("Semanalmente"), self.tr("Mensualmente")
        ])
        self._freq_combo.setEnabled(self._auto_clean_chk.isChecked())
        
        self._sched_lbl_pre = QLabel("")
        self._sched_hourly_combo = QComboBox()
        self._sched_hourly_combo.setView(QListView())
        self._sched_hourly_combo.addItems([self.tr("cada 6 horas"), self.tr("cada 12 horas")])
        self._sched_lbl_mid = QLabel("")
        self._sched_day = QComboBox()
        self._sched_day.setView(QListView())
        self._sched_day.addItems([self.tr("Lunes"), self.tr("Martes"), self.tr("Miércoles"), self.tr("Jueves"), self.tr("Viernes"), self.tr("Sábado"), self.tr("Domingo")])
        self._sched_hour = QSpinBox()
        self._sched_hour.setRange(0, 23)
        self._sched_hour.setSuffix(":00 h")

        freq_row = QHBoxLayout()
        freq_row.addWidget(freq_lbl)
        freq_row.addWidget(self._freq_combo)
        freq_row.addWidget(self._sched_lbl_pre)
        freq_row.addWidget(self._sched_hourly_combo)
        freq_row.addWidget(self._sched_day)
        freq_row.addWidget(self._sched_lbl_mid)
        freq_row.addWidget(self._sched_hour)
        freq_row.addStretch()
        
        sg_layout.addWidget(self._auto_clean_chk)
        sg_layout.addLayout(freq_row)

        # Cargar valores iniciales
        self._load_schedule_values()

        # Conectar señales
        self._freq_combo.currentIndexChanged.connect(self._on_freq_changed)
        self._sched_hourly_combo.currentIndexChanged.connect(self._save_schedule_state)
        self._sched_day.currentIndexChanged.connect(self._save_schedule_state)
        self._sched_hour.valueChanged.connect(self._save_schedule_state)

        pacman_group = QGroupBox(self.tr("Caché de Pacman"))
        pg_layout = QVBoxLayout(pacman_group)
        pg_layout.setSpacing(10)

        keep_row = QHBoxLayout()
        keep_lbl = QLabel(self.tr("Conservar versiones por paquete:"))
        keep_lbl.setStyleSheet(style_text("text_primary"))
        self._keep_spin = QSpinBox()
        self._keep_spin.setRange(0, 10)
        self._keep_spin.setToolTip(self.tr("Número de versiones de paquete antiguas a conservar."))
        keep_val = self._config.get("cache.keep_versions", 2)
        self._keep_spin.setValue(keep_val)
        self._keep_spin.setFixedWidth(70)
        self._keep_spin.valueChanged.connect(
            lambda v: self._config.set("cache.keep_versions", v)
        )
        keep_row.addWidget(keep_lbl)
        keep_row.addWidget(self._keep_spin)
        keep_row.addStretch()

        clean_pacman_btn = QPushButton(self.tr("🧹 Limpiar versiones antiguas de caché de Pacman"))
        clean_pacman_btn.setToolTip(self.tr("Elimina instalaciones antiguas, útil para liberar espacio sin borrar todo."))
        clean_pacman_btn.clicked.connect(
            lambda: self.clean_pacman_requested.emit(self._keep_spin.value())
        )

        clean_uninst_btn = QPushButton(self.tr("🗑 Eliminar caché de desinstalados"))
        clean_uninst_btn.setToolTip(self.tr("Elimina la caché estricta de todos los programas que ya no tienes en tu sistema."))
        clean_uninst_btn.clicked.connect(self.clean_pacman_uninstalled.emit)

        pg_layout.addLayout(keep_row)
        pg_layout.addWidget(clean_pacman_btn)
        pg_layout.addWidget(clean_uninst_btn)

        aur_group = QGroupBox(self.tr("Caché de AUR"))
        ag_layout = QVBoxLayout(aur_group)

        clean_aur_btn = QPushButton(self.tr("🧹 Limpiar caché AUR"))
        clean_aur_btn.setToolTip(self.tr("Elimina los directorios de compilación de yay en ~/.cache/yay/"))
        clean_aur_btn.clicked.connect(self.clean_yay_requested.emit)

        ag_layout.addWidget(clean_aur_btn)

        orphan_group = QGroupBox(self.tr("Paquetes huérfanos"))
        or_layout = QVBoxLayout(orphan_group)

        clean_orphan_btn = QPushButton(self.tr("🗑 Eliminar paquetes huérfanos"))
        clean_orphan_btn.setToolTip(self.tr("Los paquetes huérfanos fueron instalados como dependencias y ya no son necesarios."))
        clean_orphan_btn.setStyleSheet("background-color: #f44336; color: white;")
        clean_orphan_btn.clicked.connect(self.clean_orphans_requested.emit)

        or_layout.addWidget(clean_orphan_btn)

        self._status = QLabel("")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(overview)
        layout.addWidget(sched_group)
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

    def update_cache_info(self, info: CacheInfo):
        self._total_label.setText(info.total_size_str)
        self._pacman_lbl["size_lbl"].setText(info.pacman_size_str)
        self._yay_lbl["size_lbl"].setText(info.yay_size_str)
        self.status_msg.emit(self.tr("Cálculo de caché completado"))

    def refresh_view(self):
        self.status_msg.emit(self.tr("Calculando espacio en caché..."))
        self.refresh_requested.emit()

    def _on_auto_clean_changed(self, state):
        enabled = state == Qt.CheckState.Checked.value
        self._config.set("cache.auto_clean", enabled)
        self._freq_combo.setEnabled(enabled)
        self._save_schedule_state()

    def _on_freq_changed(self):
        idx = self._freq_combo.currentIndex()
        policies = ["daily", "weekly", "monthly"]
        policy = policies[idx] if idx < len(policies) else "daily"
        self._update_schedule_ui_only(policy)
        self._save_schedule_state()

    def _load_schedule_values(self):
        sched = self._config.get("cache.schedule", {})
        policy = sched.get("frequency", "monthly")
        
        self._freq_combo.blockSignals(True)
        idx_map = {"daily": 0, "weekly": 1, "monthly": 2}
        self._freq_combo.setCurrentIndex(idx_map.get(policy, 2))
        self._freq_combo.blockSignals(False)

        self._update_schedule_ui_only(policy)

        self._sched_hourly_combo.blockSignals(True)
        self._sched_hourly_combo.setCurrentIndex(0 if sched.get("interval_hours", 6) == 6 else 1)
        self._sched_hourly_combo.blockSignals(False)

        day_map = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6}
        saved_day = sched.get("day", "saturday")
        self._sched_day.blockSignals(True)
        if policy == "monthly":
            self._sched_day.setCurrentIndex(self._month_day_to_index(saved_day))
        else:
            self._sched_day.setCurrentIndex(day_map.get(saved_day, 5) if isinstance(saved_day, str) else saved_day)
        self._sched_day.blockSignals(False)

        self._sched_hour.blockSignals(True)
        self._sched_hour.setValue(sched.get("hour", 12))
        self._sched_hour.blockSignals(False)

    def _update_schedule_ui_only(self, policy: str):
        self._sched_lbl_pre.hide()
        self._sched_lbl_mid.hide()
        self._sched_hourly_combo.hide()
        self._sched_day.hide()
        self._sched_hour.hide()

        enabled = self._auto_clean_chk.isChecked()
        if not enabled: return

        if policy == "daily":
            self._sched_lbl_pre.setText(self.tr("a las"))
            self._sched_lbl_pre.show()
            self._sched_hour.show()
        elif policy == "weekly":
            if self._sched_day.count() == 0 or "día" in self._sched_day.itemText(0):
                self._sched_day.blockSignals(True)
                self._sched_day.clear()
                self._sched_day.addItems([self.tr("Lunes"), self.tr("Martes"), self.tr("Miércoles"), self.tr("Jueves"), self.tr("Viernes"), self.tr("Sábado"), self.tr("Domingo")])
                self._sched_day.blockSignals(False)
            self._sched_lbl_pre.setText(self.tr("cada"))
            self._sched_lbl_mid.setText(self.tr("a las"))
            self._sched_lbl_pre.show()
            self._sched_day.show()
            self._sched_lbl_mid.show()
            self._sched_hour.show()
        elif policy == "monthly":
            if self._sched_day.count() == 0 or self.tr("Lunes") in self._sched_day.itemText(0):
                self._sched_day.blockSignals(True)
                self._sched_day.clear()
                items_mes = [self.tr("día {0}").format(i) for i in range(1, 28)]
                items_mes.append(self.tr("Último día del mes"))
                self._sched_day.addItems(items_mes)
                self._sched_day.blockSignals(False)
            self._sched_lbl_pre.setText(self.tr("el"))
            self._sched_lbl_mid.setText(self.tr("a las"))
            self._sched_lbl_pre.show()
            self._sched_day.show()
            self._sched_lbl_mid.show()
            self._sched_hour.show()

    def _save_schedule_state(self):
        idx = self._freq_combo.currentIndex()
        policies = ["daily", "weekly", "monthly"]
        policy = policies[idx] if idx < len(policies) else "daily"

        day_keys = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        day_idx = self._sched_day.currentIndex()
        day_str = day_keys[day_idx] if 0 <= day_idx < len(day_keys) else "saturday"
        
        if policy == "monthly":
            day_str = self._month_day_from_index(day_idx)

        sched = {
            "enabled": self._auto_clean_chk.isChecked(),
            "frequency": policy,
            "day": day_str,
            "hour": self._sched_hour.value()
        }
        self._config.set("cache.schedule", sched)

    def _month_day_from_index(self, idx: int) -> str:
        if idx < 0:
            return "1"
        if idx >= 27:
            return "last"
        return str(idx + 1)

    def _month_day_to_index(self, day_value) -> int:
        if isinstance(day_value, int):
            return min(max(day_value - 1, 0), 27)
        if isinstance(day_value, str):
            if day_value == "last":
                return 27
            if day_value.isdigit():
                return min(max(int(day_value) - 1, 0), 27)
            if day_value == "Último día del mes":
                return 27
            if day_value.startswith("día "):
                try:
                    return min(max(int(day_value.replace("día ", "")) - 1, 0), 27)
                except ValueError:
                    return 0
        return 0
