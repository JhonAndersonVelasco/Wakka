from PyQt6.QtCore import Qt, pyqtSignal, QLocale, QProcess, QThread, QCoreApplication
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QComboBox, QCheckBox,
    QSpinBox, QLineEdit, QScrollArea, QFrame,
    QFormLayout, QListView,
    QFileDialog, QMessageBox, QApplication, QTextEdit
)
from PyQt6.QtGui import QPainter, QColor

from core.config_manager import ConfigManager
import sys
from pathlib import Path
import shutil
import subprocess
from gui.dialogs.translation_editor import TranslationEditorDialog

def style_subtitle(size: int) -> str:
    return f"font-size: {size}px; color: gray;"

def style_label(size: int) -> str:
    return f"font-size: {size}px; color: gray;"

def style_text(role: str, size: int = 12, weight: str = "normal") -> str:
    return f"font-size: {size}px; font-weight: {weight};"

def style_accent_label(size: int) -> str:
    return f"font-size: {size}px; color: #2196F3; font-weight: bold;"

def style_status(status_type: str, size: int) -> str:
    colors = {"success": "#4CAF50", "danger": "#f44336", "info": "#2196F3"}
    return f"font-size: {size}px; color: {colors.get(status_type, 'gray')};"

class SettingsWorker(QThread):
    finished = pyqtSignal(list)
    status_msg = pyqtSignal(str)

    def __init__(self, yay_wrapper):
        super().__init__()
        self.yay = yay_wrapper

    def run(self):
        self.status_msg.emit(QCoreApplication.translate("SettingsWorker", "Cargando configuración de Wakka..."))
        packages = self.yay.get_installed_packages()
        self.finished.emit(packages)

class MultiLinePlaceholderEdit(QTextEdit):
    def __init__(self, placeholder="", parent=None):
        super().__init__(parent)
        self.custom_placeholder = placeholder

    def paintEvent(self, event):
        super().paintEvent(event)
        # Si el editor está vacío, dibujamos el placeholder manualmente
        if not self.toPlainText():
            painter = QPainter(self.viewport())
            # Color gris típico de placeholder
            painter.setPen(QColor(150, 150, 150))
            
            # Ajustamos el margen para que no choque con el borde (4px suele ser el default)
            rect = self.viewport().rect().adjusted(5, 3, -5, -3)
            
            # Qt.TextWordWrap permite que el texto fluya si es muy largo
            painter.drawText(rect, Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignTop|Qt.TextFlag.TextWordWrap, self.custom_placeholder)

class SettingsTab(QWidget):
    theme_changed     = pyqtSignal(str)
    language_changed  = pyqtSignal(str)
    autostart_changed = pyqtSignal(bool)
    shutdown_updates_changed = pyqtSignal(bool)
    schedule_changed  = pyqtSignal(bool, dict)
    status_msg        = pyqtSignal(str)

    def __init__(self, config: ConfigManager, parent=None):
        super().__init__(parent)
        self._config = config
        
        # Initial states for tracking changes
        self._initial_theme = "system"
        self._initial_lang = "auto"
        self._initial_autostart = True

        self._setup_ui()
        self._load_values()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self._scroll = QScrollArea()
        self._scroll.setObjectName("SettingsScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setStyleSheet("#SettingsScroll { background-color: transparent; }")

        self._content = QWidget()
        self._content.setObjectName("SettingsContent")
        self._content.setStyleSheet("#SettingsContent { background-color: transparent; }")
        inner = QVBoxLayout(self._content)
        inner.setContentsMargins(24, 24, 24, 40)
        inner.setSpacing(20)

        self._scroll.setWidget(self._content)
        root.addWidget(self._scroll)

        # ── General ──
        general = QGroupBox(self.tr("General"))
        gf = QVBoxLayout(general)
        g_form = QFormLayout()

        self._theme_combo = QComboBox()
        self._theme_combo.setView(QListView())
        self._theme_combo.addItems([self.tr("Sistema"), self.tr("Oscuro"), self.tr("Claro")])
        self._theme_combo.setToolTip(self.tr("Selecciona el tema de la aplicación."))
        self._theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        g_form.addRow(self.tr("Tema visual:"), self._theme_combo)

        self._autostart_chk = QCheckBox(self.tr("Iniciar con el sistema (bandeja del sistema)"))
        self._autostart_chk.setToolTip(self.tr("Inicia Wakka en la bandeja del sistema al arrancar el equipo."))
        self._autostart_chk.stateChanged.connect(self._on_autostart_toggled)
        g_form.addRow(self._autostart_chk)
        
        gf.addLayout(g_form)
        
        # Integrando Administrador de Idiomas en General
        gf.addSpacing(15)
        
        t_info = QLabel(
            self.tr("Selecciona el idioma activo (requiere reinicio). "
            "Genera, importa o edita traducciones comunitarias personalizadas:")
        )
        t_info.setWordWrap(True)
        t_info.setStyleSheet(style_subtitle(12) + " margin-bottom: 4px;")
        gf.addWidget(t_info)

        # ── Selector de idioma tipo combo ──
        lang_row = QHBoxLayout()
        lang_row.setContentsMargins(0, 0, 0, 0)
        lang_row.setSpacing(8)

        self._lang_combo = QComboBox()
        self._lang_combo.setView(QListView())
        self._lang_combo.setMinimumWidth(280)
        self._lang_combo.setFixedHeight(34)
        self._lang_combo.currentIndexChanged.connect(self._handle_restart_setting_change)
        lang_row.addWidget(self._lang_combo)

        self._lang_edit_btn = QPushButton("✎")
        self._lang_edit_btn.setFixedSize(34, 34)
        self._lang_edit_btn.setToolTip(self.tr("Editar en Qt Linguist"))
        self._lang_edit_btn.clicked.connect(self._on_edit_current_lang)
        lang_row.addWidget(self._lang_edit_btn)

        self._lang_del_btn = QPushButton("🗑️")
        self._lang_del_btn.setFixedSize(34, 34)
        self._lang_del_btn.setToolTip(self.tr("Eliminar traducción local"))
        self._lang_del_btn.clicked.connect(self._on_delete_current_lang)
        lang_row.addWidget(self._lang_del_btn)

        lang_row.addStretch()
        gf.addLayout(lang_row)
        gf.addSpacing(8)

        code_row = QHBoxLayout()
        self._trans_code = QLineEdit()
        self._trans_code.setPlaceholderText(self.tr("de, pt..."))
        self._trans_code.setFixedWidth(60)

        gen_btn = QPushButton(self.tr("➕ Construir (.ts)"))
        gen_btn.setToolTip(self.tr("Generar/Agregar nueva plantilla lingüística"))
        gen_btn.clicked.connect(self._generate_ts)

        code_row.addWidget(self._trans_code)
        code_row.addWidget(gen_btn)
        code_row.addStretch()

        gf.addLayout(code_row)

        # Añadimos un pequeño stretch al final de la sección General para que no se expanda
        gf.addStretch()

        # ── Actualizaciones ──
        updates = QGroupBox(self.tr("Actualizaciones"))
        uf = QFormLayout(updates)

        self._notif_chk = QCheckBox(self.tr("Mostrar notificaciones"))
        self._notif_chk.setToolTip(self.tr("Habilita o deshabilita notificaciones en el sistema."))
        self._notif_chk.stateChanged.connect(
            lambda s: self._config.set("notifications", s == Qt.CheckState.Checked.value)
        )
        self._shutdown_chk = QCheckBox(self.tr("Instalar al apagar el equipo"))
        self._shutdown_chk.setToolTip(
            self.tr("Requiere habilitar el servicio systemd wakka-shutdown.service. "
                    "Wakka intentará actualizar paquetes oficiales y AUR al apagar; "
                    "si yay no puede ejecutarse sin interacción, hará fallback a paquetes oficiales.")
        )
        self._shutdown_chk.stateChanged.connect(self._on_shutdown_updates)

        self._bg_download_chk = QCheckBox(self.tr("Descargar actualizaciones en segundo plano"))
        self._bg_download_chk.setToolTip(
            self.tr("Inicia la descarga de paquetes automáticamente cuando se detectan actualizaciones. "
                    "Esto hace que la instalación sea mucho más rápida.")
        )
        self._bg_download_chk.stateChanged.connect(
            lambda s: self._config.set("background_download", s == Qt.CheckState.Checked.value)
        )

        # Agrupamos todos los elementos de control en un solo VBox sin anidados para evitar gaps
        chk_vbox = QVBoxLayout()
        chk_vbox.setContentsMargins(0, 0, 0, 0)
        chk_vbox.setSpacing(2) # Espaciado muy estrecho para los checks
        chk_vbox.addWidget(self._notif_chk)
        chk_vbox.addWidget(self._shutdown_chk)
        chk_vbox.addWidget(self._bg_download_chk)

        uf.addRow(chk_vbox)

        self._update_freq = QComboBox()
        self._update_freq.setView(QListView())
        self._update_freq.addItems([
            self.tr("Al iniciar"), self.tr("Cada 6 horas"), self.tr("Cada 12 horas"),
            self.tr("Diariamente"), self.tr("Semanalmente"), self.tr("Mensualmente"),
            self.tr("Manualmente")
        ])
        self._update_freq.setToolTip(self.tr("Frecuencia con la que se revisan automáticamente las actualizaciones."))
        self._update_freq.currentIndexChanged.connect(self._on_schedule_changed)

        search_row = QHBoxLayout()
        search_row.setContentsMargins(0, 0, 0, 0)
        search_row.addWidget(self._update_freq)

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

        search_row.addWidget(self._sched_lbl_pre)
        search_row.addWidget(self._sched_hourly_combo)
        search_row.addWidget(self._sched_day)
        search_row.addWidget(self._sched_lbl_mid)
        search_row.addWidget(self._sched_hour)
        search_row.addStretch()

        self._sched_lbl_pre.hide()
        self._sched_lbl_mid.hide()
        self._sched_hourly_combo.hide()
        self._sched_day.hide()
        self._sched_hour.hide()

        uf.addRow(self.tr("Buscar actualizaciones:"), search_row)

        self._sched_hour.valueChanged.connect(self._save_schedule_state)
        self._sched_day.currentIndexChanged.connect(self._save_schedule_state)

        # ── pacman.conf ──
        pacman = QGroupBox(self.tr("Editar pacman.conf"))
        pf = QVBoxLayout(pacman)

        self._parallel_spin = QSpinBox()
        self._parallel_spin.setRange(1, 20)
        self._parallel_spin.setValue(5)
        self._parallel_spin.setToolTip(self.tr("Descarga paquetes simultáneamente para aumentar velocidad (edita pacman.conf)."))

        parallel_row = QHBoxLayout()
        parallel_row.addWidget(QLabel(self.tr("Descargas paralelas:")))
        parallel_row.addWidget(self._parallel_spin)
        parallel_row.addStretch()

        ignore_lbl = QLabel(self.tr("Paquetes omitidos en actualizaciones (IgnorePkg) separados por espacio:"))
        ignore_lbl.setStyleSheet(style_text("text_primary") + " margin-top: 8px;")
        self._ignore_input = QLineEdit()
        self._ignore_input.setPlaceholderText("pkg1 pkg2")
        self._ignore_input.setToolTip(self.tr("Nombres exactos de paquetes que deseas excluir de las actualizaciones."))

        repos_lbl = QLabel(self.tr("Repositorios de terceros (ej: [chaotic-aur]):"))
        repos_lbl.setStyleSheet(style_text("text_primary") + " margin-top: 8px;")
        
        self._custom_repos = MultiLinePlaceholderEdit("[chaotic-aur]\nInclude = /etc/pacman.d/chaotic-mirrorlist")
        self._custom_repos.setToolTip(self.tr("Añade las cabeceras de tus repositorios. Omite [core], [extra] y [multilib]."))
        self._custom_repos.setFixedHeight(120)

        pacman_btn_layout = QHBoxLayout()
        pacman_btn_layout.addStretch()
        self._apply_pacman_btn = QPushButton(self.tr("Aplicar todo en pacman.conf"))
        self._apply_pacman_btn.setToolTip(self.tr("Guarda y escribe todos los cambios en el archivo del sistema."))
        self._apply_pacman_btn.clicked.connect(self._apply_pacman_all)
        pacman_btn_layout.addWidget(self._apply_pacman_btn)
        pacman_btn_layout.addStretch()

        pf.addLayout(parallel_row)
        pf.addWidget(ignore_lbl)
        pf.addWidget(self._ignore_input)
        pf.addWidget(repos_lbl)
        pf.addWidget(self._custom_repos)
        # pacman_status was here
        pf.addLayout(pacman_btn_layout)

        top_layout = QHBoxLayout()
        top_layout.setSpacing(20)
        top_layout.addWidget(general)
        top_layout.addWidget(updates)

        inner.addLayout(top_layout)
        inner.addWidget(pacman)
        inner.addStretch()

    def _load_values(self):
        # Load directly
        self._initial_theme = self._config.get("theme", "system")
        self._theme_combo.blockSignals(True)
        if self._initial_theme == "system":
            self._theme_combo.setCurrentIndex(0)
        elif self._initial_theme == "dark":
            self._theme_combo.setCurrentIndex(1)
        else:
            self._theme_combo.setCurrentIndex(2)
        self._theme_combo.blockSignals(False)

        self._initial_autostart = self._config.is_autostart_actually_enabled()
        # Actualizamos la configuración interna para que coincida con la realidad
        self._config.set("autostart", self._initial_autostart)
        self._autostart_chk.blockSignals(True)
        self._autostart_chk.setChecked(self._initial_autostart)
        self._autostart_chk.blockSignals(False)

        self._initial_lang = self._config.get("language", "auto")
        self._load_languages_list()

        self._notif_chk.blockSignals(True)
        self._notif_chk.setChecked(self._config.get("notifications", True))
        self._notif_chk.blockSignals(False)

        self._update_freq.blockSignals(True)
        policy = self._get_update_policy()
        self._update_freq.setCurrentIndex(self._update_policy_to_index(policy))
        self._update_freq.blockSignals(False)

        self._update_schedule_ui_only(policy)

        sched = self._config.get("update_schedule", {})
        self._sched_hourly_combo.blockSignals(True)
        idx = 0
        if sched.get("interval_hours", 6) == 12:
            idx = 1
        self._sched_hourly_combo.setCurrentIndex(idx)
        self._sched_hourly_combo.blockSignals(False)

        day_map = {
            "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
            "friday": 4, "saturday": 5, "sunday": 6
        }
        saved_day = sched.get("day", "saturday")
        self._sched_day.blockSignals(True)
        if policy == "monthly":
            self._sched_day.setCurrentIndex(self._month_day_to_index(saved_day))
        else:
            self._sched_day.setCurrentIndex(day_map.get(saved_day, 5) if isinstance(saved_day, str) else saved_day)
        self._sched_day.blockSignals(False)

        self._sched_hour.blockSignals(True)
        self._sched_hour.setValue(sched.get("hour", 10))
        self._sched_hour.blockSignals(False)

        self._parallel_spin.blockSignals(True)
        self._parallel_spin.setValue(self._config.get_parallel_downloads())
        self._parallel_spin.blockSignals(False)

        self._ignore_input.blockSignals(True)
        self._ignore_input.setText(" ".join(self._config.get_ignored_packages()))
        self._ignore_input.blockSignals(False)
        
        self._custom_repos.blockSignals(True)
        self._custom_repos.setPlainText(self._config.get_custom_repositories())
        self._custom_repos.blockSignals(False)

        self._shutdown_chk.blockSignals(True)
        self._shutdown_chk.setChecked(self._config.get("shutdown_updates", False))
        self._shutdown_chk.blockSignals(False)

        self._bg_download_chk.blockSignals(True)
        self._bg_download_chk.setChecked(self._config.get("background_download", True))
        self._bg_download_chk.blockSignals(False)

    def _set_status(self, text: str, status_type: str = "info"):
        """Emite un mensaje de estado a la barra de estado."""
        if text:
            self.status_msg.emit(text)

    def _on_theme_changed(self, idx):
        self._handle_restart_setting_change()

    def _on_autostart_toggled(self, state: int):
        enabled = state == Qt.CheckState.Checked.value
        self._config.set_autostart(enabled)
        self.autostart_changed.emit(enabled)
        # Sincronizamos el estado inicial para que no afecte al botón de "Aplicar"
        self._initial_autostart = enabled

    def _handle_restart_setting_change(self):
        # 1. Obtener valores nuevos
        idx = self._theme_combo.currentIndex()
        cur_theme = "system" if idx == 0 else ("dark" if idx == 1 else "light")

        cur_lang = self._initial_lang
        combo_data = self._lang_combo.currentData()
        if combo_data:
            cur_lang = combo_data

        # Actualizar botones de acción según el idioma seleccionado
        self._update_lang_actions(cur_lang)

        # 2. Comprobar si realmente ha cambiado algo
        if cur_theme == self._initial_theme and cur_lang == self._initial_lang:
            return

        # 3. Guardar cambios en ConfigManager
        self._config.set("theme", cur_theme)
        self._config.set("language", cur_lang)

        # 4. Forzar el reinicio
        msg = QMessageBox(self)
        msg.setWindowTitle(self.tr("Cambio realizado"))
        msg.setText(self.tr("Para aplicar el nuevo tema o idioma, es necesario reiniciar Wakka.\n\n¿Deseas reiniciar el programa ahora?"))
        yes_btn = msg.addButton(self.tr("Sí"), QMessageBox.ButtonRole.YesRole)
        no_btn = msg.addButton(self.tr("No"), QMessageBox.ButtonRole.NoRole)
        msg.setIcon(QMessageBox.Icon.Question)
        msg.exec()
        if msg.clickedButton() == yes_btn:
            QProcess.startDetached(sys.executable, sys.argv)
            QApplication.quit()
        else:
            self._initial_theme = cur_theme
            self._initial_lang = cur_lang

    # ─── Language Management Methods ──────────────────────────────────────────

    def _load_languages_list(self):
        """Puebla el combo de idiomas con nombre nativo, código y tipo."""
        self._lang_combo.blockSignals(True)
        self._lang_combo.clear()

        i18n_dir = Path(__file__).resolve().parent.parent.parent / "i18n"
        langs = set()

        if i18n_dir.exists():
            for f in i18n_dir.glob("*.ts"):
                code = f.stem.replace("wakka_", "")
                if code != "template":
                    langs.add(code)
            for f in i18n_dir.glob("*.qm"):
                code = f.stem.replace("wakka_", "")
                if code != "template":
                    langs.add(code)

        fixed_order = ["auto", "es_ES", "en_US", "es", "en"]
        discovered = sorted([l for l in langs if l not in fixed_order])
        all_langs = []
        for code in fixed_order:
            if code == "auto" or code in langs:
                all_langs.append(code)
        all_langs.extend(discovered)

        for code in all_langs:
            label, tooltip = self._build_lang_item(code, i18n_dir)
            self._lang_combo.addItem(label, userData=code)
            idx = self._lang_combo.count() - 1
            self._lang_combo.setItemData(idx, tooltip, Qt.ItemDataRole.ToolTipRole)

        # Seleccionar el idioma activo
        active = self._initial_lang
        for i in range(self._lang_combo.count()):
            if self._lang_combo.itemData(i) == active:
                self._lang_combo.setCurrentIndex(i)
                break

        self._lang_combo.blockSignals(False)
        self._update_lang_actions(active)

    def _build_lang_item(self, code: str, i18n_dir: Path):
        """Devuelve (label_text, tooltip) para un código de idioma."""
        BUILTIN = ["auto", "es", "en", "es_ES", "en_US"]

        if code == "auto":
            name = self.tr("Automático")
            badge = "🌐"
            type_label = self.tr("Sistema")
            tooltip = self.tr("Usa el idioma configurado en el sistema operativo")
        else:
            locale = QLocale(code)
            native = locale.nativeLanguageName().title()
            name = native if native else code
            has_ts = (i18n_dir / f"{code}.ts").exists() or (i18n_dir / f"wakka_{code}.ts").exists()
            has_qm = (i18n_dir / f"{code}.qm").exists() or (i18n_dir / f"wakka_{code}.qm").exists()

            if code in BUILTIN:
                badge = "⭐"
                type_label = self.tr("Incluido")
                tooltip = self.tr("Traducción oficial incluida con Wakka")
            elif has_qm and has_ts:
                badge = "✅"
                type_label = self.tr("Personalizado")
                tooltip = self.tr("Traducción comunitaria o personal compilada y lista")
            elif has_ts:
                badge = "🔧"
                type_label = self.tr("En progreso")
                tooltip = self.tr("Traducción parcial sin compilar (.ts sin .qm)")
            else:
                badge = "📦"
                type_label = self.tr("Binario")
                tooltip = self.tr("Solo binario compilado (.qm), sin fuentes")

        label = f"{badge}  {name}   [{code}]   {type_label}"
        return label, tooltip

    def _update_lang_actions(self, code: str):
        """Activa/desactiva los botones de editar y eliminar según el idioma."""
        BUILTIN = ["auto", "es", "en", "es_ES", "en_US"]
        is_custom = code not in BUILTIN
        i18n_dir = Path(__file__).resolve().parent.parent.parent / "i18n"
        has_ts = (i18n_dir / f"{code}.ts").exists() or (i18n_dir / f"wakka_{code}.ts").exists()

        self._lang_edit_btn.setEnabled(is_custom and has_ts)
        self._lang_del_btn.setEnabled(is_custom)

    def _on_edit_current_lang(self):
        code = self._lang_combo.currentData()
        if code:
            self._open_linguist_code(code)

    def _on_delete_current_lang(self):
        code = self._lang_combo.currentData()
        if code:
            self._remove_translation(code)

    def _generate_ts(self):
        code = self._trans_code.text().strip().lower()
        if not code:
            self._set_status(self.tr("⛔ Ingresa un código (ej. fr)"), "danger")
            return

        root = Path(__file__).resolve().parent.parent.parent
        i18n_dir = root / "i18n"
        i18n_dir.mkdir(exist_ok=True)
        out_file = i18n_dir / f"wakka_{code}.ts"

        try:
            cmd = ["pylupdate6"] + [str(p) for p in root.rglob("*.py")] + ["-ts", str(out_file)]
            process = subprocess.run(cmd, capture_output=True, text=True)
            if process.returncode == 0:
                self._set_status(self.tr("✓ Plantilla creada: {0}").format(out_file.name), "success")
                self._load_languages_list()
                self._open_linguist_code(code)
            else:
                self._set_status(self.tr("Error: {0}").format(process.stderr.strip()), "danger")
        except FileNotFoundError:
            self._set_status(self.tr("⛔ Falta pylupdate6 (instala python-pyqt6 o pyqt6-tools)"), "danger")

    def _open_linguist_code(self, code: str):
        i18n_dir = Path(__file__).resolve().parent.parent.parent / "i18n"
        ts_file = i18n_dir / f"wakka_{code}.ts"
        if not ts_file.exists():
            ts_file = i18n_dir / f"{code}.ts"

        if not ts_file.exists():
            status_msg = self.tr("⛔ El archivo .ts no existe.")
            self._set_status(status_msg, "danger")
            return

        dialog = TranslationEditorDialog(str(ts_file), self)
        if dialog.exec():
            # Si el dialogo terminó con accept(), recargamos la lista por si acaso
            self._load_languages_list()

    def _remove_translation(self, code: str):
        i18n_dir = Path(__file__).resolve().parent.parent.parent / "i18n"
        try:
            ts_f = i18n_dir / f"wakka_{code}.ts"
            qm_f = i18n_dir / f"wakka_{code}.qm"
            if ts_f.exists(): ts_f.unlink()
            if qm_f.exists(): qm_f.unlink()
            
            if self._initial_lang == code:
                 self._initial_lang = "auto"
                 self._config.set("language", "auto")

            self._load_languages_list()
            self._set_status(self.tr("✓ Idioma {0} eliminado.").format(code), "success")
        except Exception as e:
            self._set_status(self.tr("Error borrando: {0}").format(e), "danger")

    def _import_translation(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, self.tr("Importar archivo de traducción"), "", "Translation (*.ts *.qm)"
        )
        if file_path:
            src = Path(file_path)
            dest = Path(__file__).resolve().parent.parent.parent / "i18n" / src.name
            dest.parent.mkdir(exist_ok=True)
            try:
                shutil.copy(src, dest)
                self._set_status(self.tr("✓ Importado: {0}").format(src.name), "success")
                self._load_languages_list()
                if dest.suffix == ".ts":
                    self._open_linguist_code(dest.stem.replace("wakka_", ""))
            except Exception as e:
                self._set_status(self.tr("Error importando: {0}").format(e), "danger")

    def _compile_translations(self):
        root = Path(__file__).resolve().parent.parent.parent
        i18n_dir = root / "i18n"
        ts_files = list(i18n_dir.glob("*.ts"))
        if not ts_files:
            self._set_status(self.tr("No hay archivos .ts en i18n/"), "danger")
            return

        try:
            cmd = ["lrelease"] + [str(f) for f in ts_files]
            process = subprocess.run(cmd, capture_output=True, text=True)
            if process.returncode == 0:
                self._set_status(self.tr("✓ {0} idioma(s) compilado(s)").format(len(ts_files)), "success")
                self._load_languages_list()
            else:
                self._set_status(self.tr("Error compilando: {0}").format(process.stderr.strip()), "danger")
        except FileNotFoundError:
            self._set_status(self.tr("⛔ Falta lrelease (instala qt6-tools)"), "danger")

    # ─── Other Setting Management Methods ─────────────────────────────────────

    def _on_schedule_changed(self):
        idx = self._update_freq.currentIndex()
        policy = self._index_to_update_policy(idx)

        self._config.set("update_policy", policy)
        self._config.set("check_updates_on_start", policy == "boot")

        self._update_schedule_ui_only(policy)
        self._save_schedule_state()

    def _update_schedule_ui_only(self, policy: str):
        self._shutdown_chk.setEnabled(policy != "manual")

        self._sched_lbl_pre.hide()
        self._sched_lbl_mid.hide()
        self._sched_hourly_combo.hide()
        self._sched_day.hide()
        self._sched_hour.hide()

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
        idx = self._update_freq.currentIndex()
        policy = self._index_to_update_policy(idx)

        day_keys = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        day_idx = self._sched_day.currentIndex()
        day_str = day_keys[day_idx] if 0 <= day_idx < len(day_keys) else "saturday"
        if policy == "monthly":
            day_str = self._month_day_from_index(day_idx)

        interval_hours = 6
        frequency = policy
        if policy == "every_6_hours":
            frequency = "hourly"
            interval_hours = 6
        elif policy == "every_12_hours":
            frequency = "hourly"
            interval_hours = 12

        sched = {
            "enabled": policy not in ["boot", "manual"],
            "frequency": frequency,
            "interval_hours": interval_hours,
            "day": day_str,
            "hour": self._sched_hour.value()
        }
        self._config.set("update_schedule", sched)
        self.schedule_changed.emit(sched["enabled"], sched)

    def _get_update_policy(self) -> str:
        policy = self._config.get("update_policy")
        if policy in {"boot", "every_6_hours", "every_12_hours", "daily", "weekly", "monthly", "manual"}:
            return policy
        if policy == "hourly":
            sched = self._config.get("update_schedule", {})
            return "every_12_hours" if sched.get("interval_hours", 6) == 12 else "every_6_hours"

        if self._config.get("check_updates_on_start", True):
            return "boot"

        sched = self._config.get("update_schedule", {})
        if not sched.get("enabled", False):
            return "manual"

        if sched.get("frequency") == "hourly":
            return "every_12_hours" if sched.get("interval_hours", 6) == 12 else "every_6_hours"

        return sched.get("frequency", "daily")

    def _index_to_update_policy(self, idx: int) -> str:
        policies = [
            "boot",
            "every_6_hours",
            "every_12_hours",
            "daily",
            "weekly",
            "monthly",
            "manual",
        ]
        return policies[idx] if 0 <= idx < len(policies) else "boot"

    def _update_policy_to_index(self, policy: str) -> int:
        idx_map = {
            "boot": 0,
            "every_6_hours": 1,
            "every_12_hours": 2,
            "daily": 3,
            "weekly": 4,
            "monthly": 5,
            "manual": 6,
        }
        return idx_map.get(policy, 0)

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

    def _on_shutdown_updates(self, state: int):
        enabled = state == Qt.CheckState.Checked.value
        ok, msg = self._config.set_shutdown_updates(enabled)
        if ok:
            status_msg = self.tr("Servicio habilitado ✓") if enabled else self.tr("Servicio deshabilitado")
            self._set_status(status_msg, "success")
        else:
            if msg == "Cancelled":
                # Si se canceló, revertimos el estado del checkbox sin mostrar error
                self._shutdown_chk.blockSignals(True)
                self._shutdown_chk.setChecked(not enabled)
                self._shutdown_chk.blockSignals(False)
            else:
                self._set_status(self.tr("Error: {0}").format(msg), "danger")
        
        if ok:
            self.shutdown_updates_changed.emit(enabled)

    def _apply_pacman_all(self):
        # Recolectamos todos los valores de la UI
        parallel = self._parallel_spin.value()
        
        # Obtenemos el estado actual de Color en pacman.conf
        actual_color = self._config.get_color_enabled()
        
        ignore_pkgs = self._ignore_input.text().split()
        custom_repos = self._custom_repos.toPlainText()

        # Aplicamos todo en una sola llamada (un solo pkexec)
        ok, msg = self._config.apply_pacman_conf_changes(parallel, actual_color, ignore_pkgs, custom_repos)

        if ok:
            self._set_status(self.tr("Guardado correctamente en pacman.conf ✓"), "success")
        elif msg == "Cancelled":
            self._set_status(self.tr("Operación cancelada por el usuario."), "info")
        else:
            self._set_status(self.tr("Error al guardar: {0}").format(msg), "danger")
