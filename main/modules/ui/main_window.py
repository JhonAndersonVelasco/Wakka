"""
Wakka — Main Window
The primary application window with sidebar navigation.
"""
from __future__ import annotations

from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QStackedWidget, QFrame, QApplication,
)

from main.modules.ui.styles.theme import (
    build_qss, get_colors, set_current_theme,
    style_separator
)
from main.modules.ui.pages import UpdatesPage, InstalledPage, BrowsePage, CachePage, SettingsPage, HelpPage
from main.modules.ui.widgets.package_info_dialog import PackageInfoDialog
from main.modules.ui.widgets.terminal_widget import TerminalWidget
from main.modules.ui.styles.icons import get_icon, get_logo_icon
from modules.package_manager import PackageManager
from modules.cache_manager import CacheManager
from modules.config_manager import ConfigManager
from modules.repo_manager import RepoManager
from modules.scheduler import UpdateScheduler
from modules.constants import (
    NAV_ITEMS, PAGE_INDEX, DEFAULT_WINDOW_SIZE, MIN_WINDOW_SIZE,
    SIDEBAR_WIDTH, ICON_SIZE_SMALL, ICON_SIZE_LOGO, ICON_SIZE_LOGO_LARGE,
)


class MainWindow(QMainWindow):
    # Signals forwarded to tray
    update_count_changed = pyqtSignal(int)
    restart_requested = pyqtSignal()
    privileged_operation_active = pyqtSignal(bool)  # True when privileged op running

    def __init__(
        self,
        pkg_manager: PackageManager,
        cache_manager: CacheManager,
        config: ConfigManager,
        scheduler: UpdateScheduler,
        parent=None,
    ):
        super().__init__(parent)
        self._pkg = pkg_manager
        self._cache = cache_manager
        self._config = config
        self._scheduler = scheduler
        self._repo_mgr = RepoManager()
        self._scheduler = scheduler
        self._current_page = "updates"
        self._last_update_count = -1
        self._pending_restart = False

        self.setWindowTitle("Wakka")
        self.setWindowIcon(get_logo_icon(ICON_SIZE_LOGO_LARGE))
        self.setMinimumSize(*MIN_WINDOW_SIZE)
        self.resize(*DEFAULT_WINDOW_SIZE)

        # Apply theme
        theme = self._config.get("theme", "dark")
        set_current_theme(theme)
        QApplication.instance().setStyleSheet(build_qss(theme))
        self._fix_tooltip_palette(theme)

        self._build_ui()
        self._connect_signals()

    # ─── UI Construction ──────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("MainWindow")
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._updates_page  = UpdatesPage()
        self._installed_page = InstalledPage()
        self._browse_page   = BrowsePage()
        self._cache_page    = CachePage(self._config)
        self._settings_page = SettingsPage(self._config, self._repo_mgr)
        self._help_page = HelpPage()

        self._updates_page.info_requested.connect(self._show_package_info)
        self._installed_page.info_requested.connect(self._show_package_info)
        self._browse_page.info_requested.connect(self._show_package_info)

        # ── Sidebar ───────────────────────────────────────────────────────
        self._sidebar = self._build_sidebar()
        root.addWidget(self._sidebar)

        # ── Right side ────────────────────────────────────────────────────
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # Header
        self._header = self._build_header()
        right_layout.addWidget(self._header)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(style_separator())

        # Pages stack
        self._stack = QStackedWidget()

        self._stack.addWidget(self._updates_page)    # 0
        self._stack.addWidget(self._installed_page)  # 1
        self._stack.addWidget(self._browse_page)     # 2
        self._stack.addWidget(self._cache_page)      # 3
        self._stack.addWidget(self._settings_page)   # 4
        self._stack.addWidget(self._help_page)       # 5

        # Terminal widget (collapsible, at bottom)
        self._terminal = TerminalWidget()

        right_layout.addWidget(sep)
        right_layout.addWidget(self._stack, stretch=1)
        right_layout.addWidget(self._terminal)

        root.addWidget(right, stretch=1)

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Logo
        logo_widget = QWidget()
        logo_layout = QVBoxLayout(logo_widget)
        logo_layout.setContentsMargins(20, 24, 20, 8)
        logo_layout.setSpacing(2)

        logo_row = QHBoxLayout()
        logo_icon = QLabel()
        logo_icon.setPixmap(get_logo_icon(ICON_SIZE_LOGO).pixmap(ICON_SIZE_LOGO, ICON_SIZE_LOGO))
        logo_text = QLabel("Wakka")
        logo_text.setObjectName("SidebarLogo")
        logo_row.addWidget(logo_icon)
        logo_row.addWidget(logo_text)
        logo_row.addStretch()

        from __init__ import __version__
        version_lbl = QLabel(f"v{__version__}")
        version_lbl.setObjectName("SidebarVersion")

        logo_layout.addLayout(logo_row)
        logo_layout.addWidget(version_lbl)
        layout.addWidget(logo_widget)

        # Nav separator
        nav_sep = QFrame()
        nav_sep.setFrameShape(QFrame.Shape.HLine)
        nav_sep.setStyleSheet(f"{style_separator()} margin: 0 10px;")
        layout.addWidget(nav_sep)
        layout.addSpacing(8)

        # Nav buttons
        self._nav_btns: dict[str, QPushButton] = {}
        for key, icon_key, label in NAV_ITEMS:
            btn = QPushButton()
            btn.setObjectName("NavButton")
            btn.setFixedHeight(40)
            btn.setCheckable(False)
            btn.setProperty("active", key == self._current_page)
            btn.clicked.connect(lambda _, k=key: self._navigate(k))

            btn_layout = QHBoxLayout(btn)
            btn_layout.setContentsMargins(16, 0, 12, 0)
            btn_layout.setSpacing(10)

            icon_lbl = QLabel()
            icon_lbl.setPixmap(get_icon(icon_key, "#8892a4", ICON_SIZE_SMALL).pixmap(ICON_SIZE_SMALL, ICON_SIZE_SMALL))

            # Use explicit tr() for each label so lupdate can find them
            tr_labels = {
                "updates":   self.tr("Actualizaciones"),
                "installed": self.tr("Instalados"),
                "browse":    self.tr("Explorar"),
                "cache":     self.tr("Caché"),
                "settings":  self.tr("Configuración"),
                "help":      self.tr("Ayuda"),
            }
            text_lbl = QLabel(tr_labels.get(key, label))
            text_lbl.setStyleSheet("background: transparent; border: none; font-weight: 500;")

            btn_layout.addWidget(icon_lbl)
            btn_layout.addWidget(text_lbl)

            if key == "updates":
                self._update_count_lbl = QLabel("")
                self._update_count_lbl.setObjectName("UpdateBadge")
                self._update_count_lbl.setFixedSize(20, 20)
                self._update_count_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self._update_count_lbl.hide()
                btn_layout.addStretch()
                btn_layout.addWidget(self._update_count_lbl)
            else:
                btn_layout.addStretch()

            self._nav_btns[key] = btn
            layout.addWidget(btn)

        layout.addStretch()

        # Bottom: quick update button
        self._quick_update_btn = QPushButton(self.tr("⚡ Actualizar todo"))
        self._quick_update_btn.setObjectName("PrimaryButton")
        self._quick_update_btn.setFixedHeight(36)
        self._quick_update_btn.setContentsMargins(10, 0, 10, 0)
        self._quick_update_btn.setEnabled(False)
        self._quick_update_btn.clicked.connect(self._on_update_all)
        ql = QHBoxLayout()
        ql.setContentsMargins(12, 0, 12, 16)
        ql.addWidget(self._quick_update_btn)
        layout.addLayout(ql)

        return sidebar

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setObjectName("Header")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 0, 20, 0)

        self._page_title = QLabel(self.tr("Actualizaciones"))
        self._page_title.setObjectName("PageTitle")

        self._busy_label = QLabel("")
        self._busy_label.setObjectName("StatusWarning")

        layout.addWidget(self._page_title)
        layout.addStretch()
        layout.addWidget(self._busy_label)

        return header

    def _show_package_info(self, name: str):
        """Fetch package details and show the info dialog."""
        info = self._pkg.get_package_details(name)
        dlg = PackageInfoDialog(name, info, self)
        dlg.exec()

    # ─── Navigation ────────────────────────────────────────────────────────────

    def _navigate(self, page: str):
        self._current_page = page
        titles = {
            "updates":   self.tr("Actualizaciones"),
            "installed": self.tr("Instalados"),
            "browse":    self.tr("Explorar"),
            "cache":     self.tr("Caché"),
            "settings":  self.tr("Configuración"),
            "help":      self.tr("Ayuda"),
        }
        self._stack.setCurrentIndex(PAGE_INDEX[page])
        self._page_title.setText(titles[page])

        for key, btn in self._nav_btns.items():
            btn.setProperty("active", key == page)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        # Trigger data loads on page switch
        if page == "installed":
            self._load_installed()
        elif page == "cache":
            self._cache.get_cache_info()
        elif page == "browse":
            self._browse_page.focus_search()

    # ─── Signal Connection ─────────────────────────────────────────────────────

    def _connect_signals(self):
        # Package manager → UI
        self._pkg.output_line.connect(self._terminal.append_line)
        self._pkg.operation_started.connect(self._on_op_started)
        self._pkg.operation_finished.connect(self._on_op_finished)
        self._pkg.installed_packages_ready.connect(self._on_packages_found)
        self._pkg.search_results_ready.connect(self._on_search_results)
        self._pkg.updates_found.connect(self._on_updates_found)

        # Cache manager
        self._cache.output_line.connect(self._terminal.append_line)
        self._cache.operation_finished.connect(self._on_cache_op_done)
        self._cache.cache_info_ready.connect(self._cache_page.update_cache_info)
        self._cache.operation_started.connect(lambda: self.privileged_operation_active.emit(True))

        # Connect privileged operation signal to all pages
        self.privileged_operation_active.connect(self._updates_page.set_privileged_operation_running)
        self.privileged_operation_active.connect(self._installed_page.set_privileged_operation_running)
        self.privileged_operation_active.connect(self._browse_page.set_privileged_operation_running)
        self.privileged_operation_active.connect(self._cache_page.set_privileged_operation_running)
        self.privileged_operation_active.connect(self._settings_page.set_privileged_operation_running)

        # Terminal
        self._terminal.cancel_requested.connect(self._pkg.cancel)

        # Updates page
        self._updates_page.update_all_requested.connect(self._on_update_all)
        self._updates_page.update_selected_requested.connect(self._pkg.update_selected)
        self._updates_page.check_requested.connect(self._check_updates)

        self._installed_page.remove_requested.connect(lambda name: self._pkg.uninstall([name]))
        self._installed_page.remove_multiple_requested.connect(self._pkg.uninstall)
        self._installed_page.refresh_requested.connect(self._load_installed)

        self._settings_page.restart_requested.connect(self._on_restart_requested)

        # Browse page
        self._browse_page.install_requested.connect(lambda n: self._pkg.install([n]))
        self._browse_page.remove_requested.connect(lambda n: self._pkg.uninstall([n]))
        self._browse_page.search_requested.connect(
            lambda q, sort, direction, page: self._pkg.search(
                q,
                sort=sort,
                page=page,
                direction=direction,
            )
        )
        # Dedicated signals now, no need to connect search results to a generic handler

        # Cache page
        self._cache_page.clean_pacman_requested.connect(self._cache.clean_pacman_cache)
        self._cache_page.clean_pacman_uninstalled.connect(self._cache.clean_pacman_uninstalled)
        self._cache_page.clean_yay_requested.connect(self._cache.clean_yay_cache)
        self._cache_page.clean_orphans_requested.connect(self._cache.clean_orphans)
        self._cache_page.refresh_requested.connect(self._cache.get_cache_info)

        # Settings page
        self._settings_page.theme_changed.connect(self._apply_theme)
        self._settings_page.autostart_changed.connect(self._config.set_autostart)
        self._settings_page.schedule_changed.connect(lambda enabled, cfg: self._scheduler.apply_schedule(enabled, cfg))

        # Scheduler
        self._scheduler.check_requested.connect(self._check_updates)

        # Initial data load
        self._check_updates()
        if self._config.get("check_updates_on_start", True):
            pass  # Already triggered above

    # ─── Handlers ──────────────────────────────────────────────────────────────

    def _on_op_started(self, op: str):
        self._terminal.set_busy(True)
        self._terminal.clear()
        self._busy_label.setText(self.tr("⏳ Procesando..."))
        self.privileged_operation_active.emit(True)
        self._updates_page.set_busy(True)
        self._installed_page.set_busy(True)
        self._browse_page.set_busy(True)

    def _on_op_finished(self, success: bool, message: str, op: str):
        self._terminal.set_busy(False)
        if success:
            self._busy_label.setText("")
            self._terminal.set_status(self.tr("✓ Completado"), "#2dd98a")
            self._terminal.collapse()
        else:
            self._busy_label.setText(self.tr("⚠ %1").replace("%1", message))
            self._terminal.set_status(self.tr("✗ Error"), "#f05252")
        self.privileged_operation_active.emit(False)
        self._updates_page.set_busy(False)
        self._installed_page.set_busy(False)
        self._browse_page.set_busy(False)

        self._check_restart_pending()
        # Avoid infinite loops: check updates only if it was an action that might change them
        if op not in ["check_updates", "search", "list_installed"]:
            self._check_updates(silent=True)
            # Auto-refresh installed list if something changed
            if "uninstall" in op or "install" in op or "update" in op:
                self._load_installed()
                if self._browse_page._search_query:
                    self._pkg.search(
                        self._browse_page._search_query,
                        sort=self._browse_page._sort,
                        direction=self._browse_page._sort_direction,
                        page=self._browse_page._current_page,
                    )

    def _on_packages_found(self, packages: list):
        self._installed_page.set_packages(packages)
        self._installed_page.set_loading(False)

    def _on_search_results(self, packages: list):
        self._browse_page.set_results(packages)
        self._browse_page.set_searching(False)

    def _on_updates_found(self, updates: list):
        self._updates_page.set_packages(updates)
        self._updates_page.set_loading(False)

        n = len(updates)
        if n != self._last_update_count:
            self._last_update_count = n
            self.update_count_changed.emit(n)
            self._quick_update_btn.setEnabled(n > 0)

        if n > 0:
            self._update_count_lbl.setText(str(n))
            self._update_count_lbl.show()
        else:
            self._update_count_lbl.hide()

    def _on_cache_op_done(self, success: bool, message: str):
        self._cache_page.set_status(
            self.tr("✓ Completado") if success else self.tr("Error: %1").replace("%1", message),
            ok=success
        )
        self._terminal.set_busy(False)
        self._terminal.collapse()
        self.privileged_operation_active.emit(False)
        self._cache.get_cache_info()
        self._check_restart_pending()

    def _on_update_all(self):
        self._pkg.update_all()

    def _on_restart_requested(self):
        if self._pkg.is_busy or self._cache.is_busy:
            self._pending_restart = True
            self._settings_page.set_restart_pending(True)
            return

        self.restart_requested.emit()

    def _check_restart_pending(self):
        if self._pending_restart and not self._pkg.is_busy and not self._cache.is_busy:
            self._pending_restart = False
            self.restart_requested.emit()

    def _check_updates(self, silent: bool = False):
        self._updates_page.set_loading(not silent)
        self._pkg.check_updates(silent=silent)

    def _load_installed(self):
        self._installed_page.set_loading(True)
        self._installed_page.clear_search()
        self._pkg.get_installed()

    def _apply_theme(self, theme: str):
        self._config.set("theme", theme)
        set_current_theme(theme)
        QApplication.instance().setStyleSheet(build_qss(theme))
        self._fix_tooltip_palette(theme)

    def _fix_tooltip_palette(self, theme: str):
        colors = get_colors(theme)
        # Convertimos tus strings hex a QColor
        bg_color = QColor(colors['bg_input'])
        text_color = QColor(colors['text_primary'])

        palette = QApplication.palette() # Obtenemos la paleta global

        # Forzamos los roles de ToolTip para que sean opacos
        palette.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.ToolTipBase, bg_color)
        palette.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.ToolTipText, text_color)
        # En Linux/KDE a veces usa Window/WindowText para el fondo del tooltip
        palette.setColor(QPalette.ColorGroup.Inactive, QPalette.ColorRole.ToolTipBase, bg_color)

        QApplication.setPalette(palette)

    # ─── Public API (called by tray) ───────────────────────────────────────────

    def show_and_raise(self):
        self.show()
        self.activateWindow()
        self.raise_()

    def trigger_update_all(self):
        self._on_update_all()

    def trigger_check_updates(self):
        self._check_updates()

