"""
Wakka — Settings Page
All app and system configuration in one place.
"""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

from PyQt6.QtCore import Qt, pyqtSignal, QLocale
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QComboBox, QCheckBox,
    QSpinBox, QLineEdit, QScrollArea, QFrame,
    QFormLayout, QDialog, QDialogButtonBox, QFileDialog,
    QListView, QRadioButton, QButtonGroup,
)
from ..styles.icons import get_icon
from ..styles.theme import (
    style_transparent_bg, style_subtitle, style_label,
    style_text, style_accent_label, style_status,
)
from modules.config_manager import ConfigManager
from modules.repo_manager import RepoManager, Repository


class SettingsPage(QWidget):
    settings_changed  = pyqtSignal()
    theme_changed     = pyqtSignal(str)
    language_changed  = pyqtSignal(str)
    restart_requested = pyqtSignal()
    autostart_changed = pyqtSignal(bool)
    shutdown_updates_changed = pyqtSignal(bool)
    schedule_changed  = pyqtSignal(bool, dict)

    def __init__(self, config: ConfigManager, repo_manager: RepoManager, parent=None):
        super().__init__(parent)
        self._config = config
        self._repo_mgr = repo_manager
        self._setup_ui()
        self._load_values()

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
        inner = QVBoxLayout(self._content)
        inner.setContentsMargins(24, 24, 24, 40)
        inner.setSpacing(20)

        self._scroll.setWidget(self._content)
        root.addWidget(self._scroll)

        # ── Appearance ────────────────────────────────────────────────────
        appear = QGroupBox(self.tr("Apariencia"))
        af = QFormLayout(appear)

        self._theme_combo = QComboBox()
        self._theme_combo.setView(QListView())
        self._theme_combo.addItems([self.tr("Oscuro"), self.tr("Claro")])
        self._theme_combo.setToolTip(self.tr(
            "Selecciona el tema de la interfaz de la aplicación."
        ))
        self._theme_combo.currentIndexChanged.connect(self._on_theme)
        af.addRow(self.tr("Tema:"), self._theme_combo)

        # ── General ───────────────────────────────────────────────────────
        general = QGroupBox(self.tr("General"))
        gf = QFormLayout(general)

        self._autostart_chk = QCheckBox(self.tr("Iniciar con el sistema (bandeja del sistema)"))
        self._autostart_chk.stateChanged.connect(
            lambda s: self.autostart_changed.emit(s == Qt.CheckState.Checked.value)
        )
        gf.addRow(self._autostart_chk)

        # ── Idiomas ──────────────────────────────────────────────────
        translations = QGroupBox(self.tr("Idiomas"))
        tf = QVBoxLayout(translations)

        t_info = QLabel(self.tr(
            "Selecciona el idioma activo (reinicio requerido). Genera, importa o edita traducciones:"
        ))
        t_info.setWordWrap(True)
        t_info.setStyleSheet(style_subtitle(12) + " margin-bottom: 4px;")
        tf.addWidget(t_info)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        lbl_act = QLabel(self.tr("Activo"))
        lbl_act.setFixedWidth(50)
        lbl_lang = QLabel(self.tr("Idioma"))
        lbl_lang.setFixedWidth(130)
        lbl_c = QLabel(self.tr("Código"))
        lbl_c.setFixedWidth(50)
        lbl_act.setStyleSheet(style_label(11))
        lbl_lang.setStyleSheet(style_label(11))
        lbl_c.setStyleSheet(style_label(11))
        header_row.addWidget(lbl_act)
        header_row.addWidget(lbl_lang)
        header_row.addWidget(lbl_c)
        header_row.addStretch()
        tf.addLayout(header_row)

        self._lang_list_widget = QWidget()
        self._lang_list_layout = QVBoxLayout(self._lang_list_widget)
        self._lang_list_layout.setContentsMargins(0, 0, 0, 0)
        self._lang_list_layout.setSpacing(4)

        self._lang_group = QButtonGroup(self)
        self._lang_group.buttonClicked.connect(self._on_language_radio)

        tf.addWidget(self._lang_list_widget)
        tf.addSpacing(8)

        # Buttons in ONE line
        code_row = QHBoxLayout()
        self._trans_code = QLineEdit()
        self._trans_code.setPlaceholderText("de, pt...")
        self._trans_code.setFixedWidth(60)

        gen_btn = QPushButton(self.tr("➕ Construir (.ts)"))
        gen_btn.setToolTip(self.tr("Generar/Agregar nueva plantilla"))
        gen_btn.clicked.connect(self._generate_ts)

        import_btn = QPushButton(self.tr("📥 Importar"))
        import_btn.clicked.connect(self._import_translation)

        compile_btn = QPushButton(self.tr("🔨 Compilar (.qm)"))
        compile_btn.setObjectName("PrimaryButton")
        compile_btn.clicked.connect(self._compile_translations)

        code_row.addWidget(self._trans_code)
        code_row.addWidget(gen_btn)
        code_row.addWidget(import_btn)
        code_row.addStretch()
        code_row.addWidget(compile_btn)

        tf.addLayout(code_row)

        self._trans_status = QLabel("")
        self._trans_status.setStyleSheet(style_subtitle(11))
        tf.addWidget(self._trans_status)

        self._restart_btn = QPushButton(self.tr("Reiniciar ahora"))
        self._restart_btn.setObjectName("PrimaryButton")
        self._restart_btn.setVisible(False)
        self._restart_btn.clicked.connect(self._on_restart_now)
        tf.addWidget(self._restart_btn)

        # ── Actualizaciones ─────────────────────────────────────────────
        updates = QGroupBox(self.tr("Actualizaciones"))
        uf = QFormLayout(updates)

        self._notif_chk = QCheckBox(self.tr("Mostrar notificaciones"))
        self._notif_chk.stateChanged.connect(
            lambda s: self._config.set("notifications", s == Qt.CheckState.Checked.value)
        )
        uf.addRow(self._notif_chk)

        self._shutdown_chk = QCheckBox(self.tr("Instalar al apagar el equipo"))
        self._shutdown_chk.setToolTip(self.tr("Requiere habilitar el servicio systemd wakka-shutdown.service"))
        self._shutdown_chk.stateChanged.connect(self._on_shutdown_updates)
        self._shutd_status = QLabel("")
        self._shutd_status.setStyleSheet(style_subtitle(11))

        shut_layout = QVBoxLayout()
        shut_layout.setContentsMargins(0, 0, 0, 0)
        shut_layout.setSpacing(0)
        shut_layout.addWidget(self._shutdown_chk)
        shut_layout.addWidget(self._shutd_status)
        uf.addRow(shut_layout)

        self._update_freq = QComboBox()
        self._update_freq.setView(QListView())
        self._update_freq.addItems([
            self.tr("Al iniciar"),
            self.tr("Cada hora"),
            self.tr("Diariamente"),
            self.tr("Semanalmente"),
            self.tr("Mensualmente"),
            self.tr("Manualmente")
        ])
        self._update_freq.setToolTip(self.tr(
            "Selecciona la frecuencia de comprobación de actualizaciones."
        ))
        self._update_freq.currentIndexChanged.connect(self._on_schedule_changed)

        search_row = QHBoxLayout()
        search_row.setContentsMargins(0, 0, 0, 0)
        search_row.addWidget(self._update_freq)

        self._sched_lbl_pre = QLabel("")
        self._sched_val_spin = QSpinBox()
        self._sched_lbl_mid = QLabel("")
        self._sched_day = QComboBox()
        self._sched_day.setView(QListView())
        self._sched_day.addItems([
            self.tr("Lunes"), self.tr("Martes"), self.tr("Miércoles"),
            self.tr("Jueves"), self.tr("Viernes"), self.tr("Sábado"), self.tr("Domingo")
        ])
        self._sched_day.setToolTip(self.tr(
            "Selecciona el día de la semana para buscar actualizaciones."
        ))
        self._sched_hour = QSpinBox()
        self._sched_hour.setRange(0, 23)
        self._sched_hour.setSuffix(self.tr(":00 h"))

        search_row.addWidget(self._sched_lbl_pre)
        search_row.addWidget(self._sched_val_spin)
        search_row.addWidget(self._sched_day)
        search_row.addWidget(self._sched_lbl_mid)
        search_row.addWidget(self._sched_hour)
        search_row.addStretch()

        self._sched_lbl_pre.hide()
        self._sched_lbl_mid.hide()
        self._sched_val_spin.hide()
        self._sched_day.hide()
        self._sched_hour.hide()

        uf.addRow(self.tr("Buscar actualizaciones:"), search_row)

        self._sched_val_spin.valueChanged.connect(self._save_schedule_state)
        self._sched_hour.valueChanged.connect(self._save_schedule_state)
        self._sched_day.currentIndexChanged.connect(self._save_schedule_state)

        # ── pacman.conf ───────────────────────────────────────────────────
        pacman = QGroupBox(self.tr("pacman.conf"))
        pf = QVBoxLayout(pacman)

        self._parallel_spin = QSpinBox()
        self._parallel_spin.setRange(1, 20)
        self._parallel_spin.setValue(5)

        parallel_row = QHBoxLayout()
        parallel_row.addWidget(QLabel(self.tr("Descargas paralelas:")))
        parallel_row.addWidget(self._parallel_spin)
        apply_parallel = QPushButton(self.tr("Aplicar"))
        apply_parallel.clicked.connect(self._apply_parallel)
        parallel_row.addWidget(apply_parallel)
        parallel_row.addStretch()

        # IgnorePkg
        ignore_lbl = QLabel(self.tr("Paquetes omitidos en actualizaciones (IgnorePkg):"))
        ignore_lbl.setStyleSheet(style_text("text_primary") + " margin-top: 8px;")
        self._ignore_input = QLineEdit()
        self._ignore_input.setPlaceholderText(self.tr("pkg1 pkg2 pkg3 (separados por espacio)"))

        ignore_row = QHBoxLayout()
        ignore_row.addWidget(self._ignore_input)
        apply_ignore = QPushButton(self.tr("Guardar"))
        apply_ignore.clicked.connect(self._apply_ignored)
        ignore_row.addWidget(apply_ignore)

        self._pacman_status = QLabel("")
        self._pacman_status.setStyleSheet(style_subtitle(11))

        pf.addLayout(parallel_row)
        pf.addWidget(ignore_lbl)
        pf.addLayout(ignore_row)
        pf.addWidget(self._pacman_status)

        # ── Repositories ──────────────────────────────────────────────────
        repos_group = QGroupBox(self.tr("Repositorios"))
        rg = QVBoxLayout(repos_group)

        self._repo_list_widget = QWidget()
        self._repo_list_layout = QVBoxLayout(self._repo_list_widget)
        self._repo_list_layout.setContentsMargins(0, 0, 0, 0)
        self._repo_list_layout.setSpacing(4)

        add_repo_btn = QPushButton(self.tr("➕ Añadir repositorio"))
        add_repo_btn.setObjectName("PrimaryButton")
        add_repo_btn.clicked.connect(self._open_add_repo_dialog)

        refresh_repos_btn = QPushButton(self.tr("🔄 Refrescar bases de datos"))
        refresh_repos_btn.clicked.connect(self._refresh_databases)

        self._repo_status = QLabel("")
        self._repo_status.setStyleSheet(style_subtitle(11))

        rg.addWidget(self._repo_list_widget)
        rg.addWidget(add_repo_btn)
        rg.addWidget(refresh_repos_btn)
        rg.addWidget(self._repo_status)

        inner.addWidget(appear)
        inner.addWidget(general)
        inner.addWidget(translations)
        inner.addWidget(updates)
        inner.addWidget(pacman)
        inner.addWidget(repos_group)
        inner.addStretch()

    # ─── Load values from config ──────────────────────────────────────────

    def _load_values(self):
        theme = self._config.get("theme", "dark")
        self._theme_combo.setCurrentIndex(0 if theme == "dark" else 1)

        self._load_languages_list()

        self._autostart_chk.blockSignals(True)
        self._autostart_chk.setChecked(self._config.get("autostart", True))
        self._autostart_chk.blockSignals(False)

        self._notif_chk.blockSignals(True)
        self._notif_chk.setChecked(self._config.get("notifications", True))
        self._notif_chk.blockSignals(False)

        # Update controls
        self._update_freq.blockSignals(True)
        policy = self._config.get("update_policy", "boot")
        idx_map = {"boot": 0, "hourly": 1, "daily": 2, "weekly": 3, "monthly": 4, "manual": 5}
        self._update_freq.setCurrentIndex(idx_map.get(policy, 0))
        self._update_freq.blockSignals(False)

        sched = self._config.get("schedule", {})
        self._sched_val_spin.blockSignals(True)
        self._sched_val_spin.setValue(sched.get("interval_hours", 2))
        self._sched_val_spin.blockSignals(False)

        day_map = {
            "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
            "friday": 4, "saturday": 5, "sunday": 6
        }
        saved_day = sched.get("day", "saturday")
        self._sched_day.blockSignals(True)
        self._sched_day.setCurrentIndex(day_map.get(saved_day, 5) if isinstance(saved_day, str) else saved_day)
        self._sched_day.blockSignals(False)

        self._sched_hour.blockSignals(True)
        self._sched_hour.setValue(sched.get("hour", 10))
        self._sched_hour.blockSignals(False)

        # pacman.conf
        self._parallel_spin.blockSignals(True)
        self._parallel_spin.setValue(self._config.get_parallel_downloads())
        self._parallel_spin.blockSignals(True)

        self._ignore_input.blockSignals(True)
        self._ignore_input.setText(" ".join(self._config.get_ignored_packages()))
        self._ignore_input.blockSignals(False)

        self._shutdown_chk.blockSignals(True)
        self._shutdown_chk.setChecked(self._config.get("shutdown_updates", False))
        self._shutdown_chk.blockSignals(False)

        # Reset labels to standard status
        self._pacman_status.setText("")
        self._repo_status.setText("")

        # Repos
        self._load_repos()

    def _load_repos(self):
        for i in reversed(range(self._repo_list_layout.count())):
            w = self._repo_list_layout.itemAt(i).widget()
            if w:
                w.deleteLater()
        repos = self._repo_mgr.list_repos()
        for repo in repos:
            row = self._make_repo_row(repo)
            self._repo_list_layout.addWidget(row)

    def _load_languages_list(self):
        for i in reversed(range(self._lang_list_layout.count())):
            w = self._lang_list_layout.itemAt(i).widget()
            if w:
                w.deleteLater()

        for btn in self._lang_group.buttons():
            self._lang_group.removeButton(btn)

        i18n_dir = Path(__file__).resolve().parent.parent.parent / "i18n"
        langs = set()

        if i18n_dir.exists():
            for f in i18n_dir.glob("wakka_*.ts"):
                langs.add(f.stem.replace("wakka_", ""))
            for f in i18n_dir.glob("wakka_*.qm"):
                langs.add(f.stem.replace("wakka_", ""))

        all_langs = ["auto", "es", "en"] + list(langs)
        unique_langs = []
        for l in all_langs:
            if l not in unique_langs:
                unique_langs.append(l)

        active_lang = self._config.get("language", "auto")

        for code in unique_langs:
            row = self._make_lang_row(code, code == active_lang, i18n_dir)
            self._lang_list_layout.addWidget(row)

    def _make_lang_row(self, code: str, is_active: bool, i18n_dir: Path) -> QWidget:
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)

        rb = QRadioButton()
        rb.setChecked(is_active)
        rb.setProperty("lang_code", code)
        self._lang_group.addButton(rb)
        rb.setFixedWidth(50)

        name = self.tr("Automático") if code == "auto" else (QLocale(code).nativeLanguageName().title() or code)
        lbl_name = QLabel(f"<b>{name}</b>")
        lbl_name.setStyleSheet(style_text("text_primary"))
        lbl_name.setFixedWidth(130)

        lbl_code = QLabel(code)
        lbl_code.setStyleSheet(style_label(11))
        lbl_code.setFixedWidth(50)

        layout.addWidget(rb)
        layout.addWidget(lbl_name)
        layout.addWidget(lbl_code)

        has_ts = (i18n_dir / f"wakka_{code}.ts").exists()
        has_qm = (i18n_dir / f"wakka_{code}.qm").exists()

        if code not in ["auto", "es", "en"]:
            status_text = ""
            if has_qm and has_ts: status_text = self.tr("[Integrado]")
            elif has_ts: status_text = self.tr("[En Progreso]")
            elif has_qm: status_text = self.tr("[Binario]")

            s_lbl = QLabel(status_text)
            s_lbl.setStyleSheet(style_accent_label(10))
            layout.addWidget(s_lbl)
            layout.addStretch()

            edit_btn = QPushButton()
            edit_btn.setIcon(get_icon("edit", "#e8ecf4", 14))
            edit_btn.setFixedSize(28, 28)
            edit_btn.setToolTip(self.tr("Editar en Qt Linguist"))
            if has_ts:
                edit_btn.clicked.connect(lambda _, c=code: self._open_linguist_code(c))
            else:
                edit_btn.setEnabled(False)
            layout.addWidget(edit_btn)

            del_btn = QPushButton()
            del_btn.setIcon(get_icon("trash", "#f05252", 14))
            del_btn.setFixedSize(28, 28)
            del_btn.setToolTip(self.tr("Eliminar idioma local"))
            del_btn.clicked.connect(lambda _, c=code: self._remove_translation(c))
            layout.addWidget(del_btn)
        else:
            # Status labels
            is_native = code in ["es", "en"]
            s_text = self.tr("[Nativo]") if is_native else self.tr("[Sistema]")
            s_lbl = QLabel(s_text)
            s_lbl.setStyleSheet(style_accent_label(10))
            s_lbl.setFixedWidth(60)
            layout.addWidget(s_lbl)
            layout.addStretch()

        return w

    def _make_repo_row(self, repo: Repository) -> QWidget:
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)

        name_lbl = QLabel(f"<b>{repo.name}</b>")
        name_lbl.setStyleSheet(style_text("text_primary"))
        server_lbl = QLabel(repo.servers[0] if repo.servers else "—")
        server_lbl.setStyleSheet(style_label(11))

        enabled_chk = QCheckBox()
        enabled_chk.setChecked(repo.enabled)
        enabled_chk.setToolTip(self.tr("Habilitado"))
        enabled_chk.stateChanged.connect(
            lambda s, r=repo: self._toggle_repo(r, s == Qt.CheckState.Checked.value)
        )

        layout.addWidget(enabled_chk)
        layout.addWidget(name_lbl)
        layout.addSpacing(8)
        layout.addWidget(server_lbl)
        layout.addStretch()

        if not repo.is_official:
            del_btn = QPushButton()
            del_btn.setIcon(get_icon("trash", "#f05252", 14))
            del_btn.setFixedSize(28, 28)
            del_btn.setToolTip(self.tr("Eliminar repositorio"))
            del_btn.clicked.connect(lambda _, r=repo: self._remove_repo(r))
            layout.addWidget(del_btn)

        return w

    # ─── Event handlers ───────────────────────────────────────────────────

    def _on_theme(self, index: int):
        theme = "dark" if index == 0 else "light"
        self._config.set("theme", theme)
        self.theme_changed.emit(theme)

    def _on_language_radio(self, btn):
        lang = btn.property("lang_code")
        if lang:
            current = self._config.get("language", "auto")
            self._config.set("language", lang)
            self.language_changed.emit(lang)
            if lang != current:
                self._trans_status.setText(self.tr("Idioma cambiado. Pulsa Reiniciar ahora para aplicar los cambios."))
                self._restart_btn.setVisible(True)
                self._restart_btn.setEnabled(True)

    def _on_restart_now(self):
        self.restart_requested.emit()

    def set_restart_pending(self, pending: bool):
        if pending:
            self._restart_btn.setEnabled(False)
            self._trans_status.setText(
                self.tr("Hay un proceso en curso. Se reiniciará cuando termine.")
            )
        else:
            self._restart_btn.setEnabled(True)
            self._trans_status.setText(self.tr("Idioma cambiado. Pulsa Reiniciar ahora para aplicar los cambios."))

    def _on_schedule_changed(self):
        idx = self._update_freq.currentIndex()
        policies = ["boot", "hourly", "daily", "weekly", "monthly", "manual"]
        policy = policies[idx] if idx < len(policies) else "boot"

        self._config.set("update_policy", policy)
        self._config.set("check_updates_on_start", policy == "boot")

        self._shutdown_chk.setEnabled(policy != "manual")

        self._sched_lbl_pre.hide()
        self._sched_lbl_mid.hide()
        self._sched_val_spin.hide()
        self._sched_day.hide()
        self._sched_hour.hide()

        if policy == "hourly":
            self._sched_val_spin.setRange(1, 48)
            self._sched_lbl_pre.setText(self.tr("cada"))
            self._sched_val_spin.setSuffix(self.tr(" hrs"))
            self._sched_lbl_pre.show()
            self._sched_val_spin.show()
        elif policy == "daily":
            self._sched_lbl_pre.setText(self.tr("a las"))
            self._sched_lbl_pre.show()
            self._sched_hour.show()
        elif policy == "weekly":
            self._sched_day.clear()
            self._sched_day.addItems([
                self.tr("Lunes"), self.tr("Martes"), self.tr("Miércoles"),
                self.tr("Jueves"), self.tr("Viernes"), self.tr("Sábado"), self.tr("Domingo")
            ])
            self._sched_lbl_pre.setText(self.tr("cada"))
            self._sched_lbl_mid.setText(self.tr("a las"))
            self._sched_lbl_pre.show()
            self._sched_day.show()
            self._sched_lbl_mid.show()
            self._sched_hour.show()
        elif policy == "monthly":
            self._sched_day.clear()
            self._sched_day.addItems([self.tr("día %1").replace("%1", str(i)) for i in range(1, 32)])
            self._sched_lbl_pre.setText(self.tr("el"))
            self._sched_lbl_mid.setText(self.tr("a las"))
            self._sched_lbl_pre.show()
            self._sched_day.show()
            self._sched_lbl_mid.show()
            self._sched_hour.show()

        self._save_schedule_state()

    def _save_schedule_state(self):
        idx = self._update_freq.currentIndex()
        policies = ["boot", "hourly", "daily", "weekly", "monthly", "manual"]
        policy = policies[idx] if idx < len(policies) else "boot"

        day_keys = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        day_idx = self._sched_day.currentIndex()
        day_str = day_keys[day_idx] if 0 <= day_idx < len(day_keys) else "saturday"

        sched = {
            "enabled": policy not in ["boot", "manual"],
            "frequency": policy,
            "interval_hours": self._sched_val_spin.value(),
            "day": day_str,
            "hour": self._sched_hour.value()
        }
        self._config.set("schedule", sched)
        self.schedule_changed.emit(sched["enabled"], sched)

    def _on_shutdown_updates(self, state: int):
        enabled = state == Qt.CheckState.Checked.value
        ok, msg = self._config.set_shutdown_updates(enabled)
        if ok:
            status = self.tr("Servicio habilitado ✓") if enabled else self.tr("Servicio deshabilitado")
            self._shutd_status.setText(status)
            self._shutd_status.setStyleSheet(style_status("success", 11))
        else:
            self._shutd_status.setText(self.tr("Error: %1").replace("%1", msg))
            self._shutd_status.setStyleSheet(style_status("danger", 11))
        self.shutdown_updates_changed.emit(enabled)

    def _apply_parallel(self):
        ok, msg = self._config.set_parallel_downloads(self._parallel_spin.value())
        self._pacman_status.setText(self.tr("Guardado ✓") if ok else self.tr("Error: %1").replace("%1", msg))
        self._pacman_status.setStyleSheet(style_status("success" if ok else "danger", 11))

    def _apply_ignored(self):
        pkgs = self._ignore_input.text().split()
        ok, msg = self._config.set_ignored_packages(pkgs)
        self._pacman_status.setText(self.tr("Guardado ✓") if ok else self.tr("Error: %1").replace("%1", msg))
        self._pacman_status.setStyleSheet(style_status("success" if ok else "danger", 11))

    def _open_add_repo_dialog(self):
        dlg = AddRepoDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            name, server, sig = dlg.values()
            ok, msg = self._repo_mgr.add_repo(name, server, sig)
            if ok:
                self._repo_status.setText(self.tr("✓ Repositorio '%1' añadido").replace("%1", name))
                self._repo_status.setStyleSheet(style_status("success", 11))
                self._load_repos()
            else:
                self._repo_status.setText(self.tr("Error: %1").replace("%1", msg))
                self._repo_status.setStyleSheet(style_status("danger", 11))

    def _remove_repo(self, repo: Repository):
        ok, msg = self._repo_mgr.remove_repo(repo.name)
        if ok:
            self._repo_status.setText(self.tr("✓ Repositorio '%1' eliminado").replace("%1", repo.name))
            self._repo_status.setStyleSheet(style_status("success", 11))
            self._load_repos()
        else:
            self._repo_status.setText(self.tr("Error: %1").replace("%1", msg))
            self._repo_status.setStyleSheet(style_status("danger", 11))

    def _toggle_repo(self, repo: Repository, enabled: bool):
        if enabled:
            self._repo_mgr.enable_repo(repo.name)
        else:
            self._repo_mgr.disable_repo(repo.name)

    def _refresh_databases(self):
        ok, msg = self._repo_mgr.refresh_databases()
        self._repo_status.setText(self.tr("Bases de datos actualizadas ✓") if ok else self.tr("Error: %1").replace("%1", msg))
        self._repo_status.setStyleSheet(style_status("success" if ok else "danger", 11))

    # ─── Translations handlers ─────────────────────────────────────────────────

    def _generate_ts(self):
        code = self._trans_code.text().strip().lower()
        if not code:
            self._trans_status.setText(self.tr("⛔ Ingresa un código (ej. fr)"))
            self._trans_status.setStyleSheet(style_status("danger", 11))
            return

        root = Path(__file__).resolve().parent.parent.parent
        i18n_dir = root / "i18n"
        i18n_dir.mkdir(exist_ok=True)
        out_file = i18n_dir / f"wakka_{code}.ts"

        try:
            cmd = ["pylupdate6"] + [str(p) for p in root.rglob("*.py")] + ["-ts", str(out_file)]
            process = subprocess.run(cmd, capture_output=True, text=True)
            if process.returncode == 0:
                self._trans_status.setText(self.tr("✓ Plantilla creada: %1").replace("%1", out_file.name))
                self._trans_status.setStyleSheet(style_status("success", 11))
                self._load_languages_list()
                self._open_linguist_code(code)
            else:
                self._trans_status.setText(self.tr("Error: %1").replace("%1", process.stderr.strip()))
                self._trans_status.setStyleSheet(style_status("danger", 11))
        except FileNotFoundError:
            self._trans_status.setText(self.tr("⛔ Falta pylupdate6 (instala python-pyqt6 o pyqt6-tools)"))
            self._trans_status.setStyleSheet(style_status("danger", 11))

    def _open_linguist_code(self, code: str):
        ts_file = Path(__file__).resolve().parent.parent.parent / "i18n" / f"wakka_{code}.ts"
        if not ts_file.exists():
            self._trans_status.setText(self.tr("⛔ La plantilla no existe."))
            self._trans_status.setStyleSheet(style_status("danger", 11))
            return

        try:
            subprocess.Popen(["linguist", str(ts_file)])
            self._trans_status.setText(self.tr("Abriendo %1 en Linguist...").replace("%1", ts_file.name))
            self._trans_status.setStyleSheet(style_status("info", 11))
        except FileNotFoundError:
            self._trans_status.setText(self.tr("⛔ Falta Linguist (instala qt6-tools o qt5-tools)"))
            self._trans_status.setStyleSheet(style_status("danger", 11))

    def _remove_translation(self, code: str):
        i18n_dir = Path(__file__).resolve().parent.parent.parent / "i18n"
        try:
            ts_f = i18n_dir / f"wakka_{code}.ts"
            qm_f = i18n_dir / f"wakka_{code}.qm"
            if ts_f.exists(): ts_f.unlink()
            if qm_f.exists(): qm_f.unlink()
            self._load_languages_list()
            self._trans_status.setText(self.tr("✓ Idioma %1 eliminado.").replace("%1", code))
            self._trans_status.setStyleSheet(style_status("success", 11))
        except Exception as e:
            self._trans_status.setText(self.tr("Error borrando: %1").replace("%1", str(e)))
            self._trans_status.setStyleSheet(style_status("danger", 11))

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
                self._trans_status.setText(self.tr("✓ Importado: %1").replace("%1", src.name))
                self._trans_status.setStyleSheet(style_status("success", 11))
                self._load_languages_list()
                if dest.suffix == ".ts":
                    self._open_linguist_code(dest.stem.replace("wakka_", ""))
            except Exception as e:
                self._trans_status.setText(self.tr("Error importando: %1").replace("%1", str(e)))
                self._trans_status.setStyleSheet(style_status("danger", 11))

    def _compile_translations(self):
        root = Path(__file__).resolve().parent.parent.parent
        i18n_dir = root / "i18n"
        ts_files = list(i18n_dir.glob("*.ts"))
        if not ts_files:
            self._trans_status.setText(self.tr("No hay archivos .ts en i18n/"))
            self._trans_status.setStyleSheet(style_status("danger", 11))
            return

        try:
            cmd = ["lrelease"] + [str(f) for f in ts_files]
            process = subprocess.run(cmd, capture_output=True, text=True)
            if process.returncode == 0:
                self._trans_status.setText(self.tr("✓ %1 idioma(s) compilado(s)").replace("%1", str(len(ts_files))))
                self._trans_status.setStyleSheet(style_status("success", 11))
                self._load_languages_list()
            else:
                self._trans_status.setText(self.tr("Error compilando: %1").replace("%1", process.stderr.strip()))
                self._trans_status.setStyleSheet(style_status("danger", 11))
        except FileNotFoundError:
            self._trans_status.setText(self.tr("⛔ Falta lrelease (instala qt6-tools)"))
            self._trans_status.setStyleSheet(style_status("danger", 11))


class AddRepoDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Añadir repositorio"))
        self.setMinimumWidth(450)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        form = QFormLayout()
        self._name = QLineEdit()
        self._name.setPlaceholderText("chaotic-aur")
        self._server = QLineEdit()
        self._server.setPlaceholderText("https://...")
        self._sig = QComboBox()
        self._sig.addItems([
            self.tr("Opcional TrustAll"), self.tr("Opcional"),
            self.tr("Obligatorio"), self.tr("Nunca")
        ])
        self._sig.setToolTip(self.tr(
            "Selecciona el nivel de firma requerido para el repositorio."
        ))
        form.addRow(self.tr("Nombre:"), self._name)
        form.addRow(self.tr("URL del servidor:"), self._server)
        form.addRow(self.tr("Nivel de firma:"), self._sig)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)

        layout.addLayout(form)
        layout.addWidget(btns)

    def values(self) -> tuple[str, str, str]:
        return self._name.text(), self._server.text(), self._sig.currentText()
