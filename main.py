"""
Wakka — Main Entry Point
Initializes the Qt application, loads i18n, creates all components.
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

# ─── Qt HiDPI (must be set BEFORE QApplication) ──────────────────────────────
os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")

from PyQt6.QtCore import QTranslator, QLocale, QLibraryInfo
from PyQt6.QtWidgets import QApplication, QMessageBox

# Add parent dir to sys.path so we can import 'wakka' as a package even if run directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config_manager import ConfigManager
from core.package_manager import PackageManager
from core.cache_manager import CacheManager
from core.scheduler import UpdateScheduler
from core.constants import APP_NAME, APP_ID, APP_VERSION, APP_DOMAIN, SUPPORTED_AUR_HELPERS
from ui.main_window import MainWindow
from ui.tray.tray_icon import TrayIcon

log = logging.getLogger("wakka")


def _setup_logging():
    level = logging.DEBUG if os.getenv("WAKKA_DEBUG") else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _load_translations(app: QApplication, language: str):
    """Load Qt translations for the configured language."""
    translator = QTranslator(app)

    if language == "auto":
        locale = QLocale.system().name()  # e.g. "es_ES"
        lang_code = locale.split("_")[0]  # "es"
    else:
        lang_code = language

    # Try to load app-specific translation
    i18n_dir = Path(__file__).parent / "i18n"
    qm_file = i18n_dir / f"wakka_{lang_code}.qm"
    loaded_translation = False

    if qm_file.exists() and translator.load(str(qm_file)):
        app.installTranslator(translator)
        log.info(f"Loaded translation: {qm_file.name}")
        loaded_translation = True
    else:
        if qm_file.exists():
            log.warning(f"Could not load translation: {qm_file}")
        else:
            log.info(f"No translation file for language: {lang_code}")

    if not loaded_translation and lang_code != "en":
        fallback_qm = i18n_dir / "wakka_en.qm"
        if fallback_qm.exists() and translator.load(str(fallback_qm)):
            app.installTranslator(translator)
            log.info(f"Loaded fallback translation: {fallback_qm.name}")
            loaded_translation = True
        elif fallback_qm.exists():
            log.warning(f"Could not load fallback translation: {fallback_qm}")

    # Also load Qt standard translations (buttons, dialogs)
    qt_translator = QTranslator(app)
    qt_path = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    if qt_translator.load(f"qt_{lang_code}", qt_path):
        app.installTranslator(qt_translator)
    elif lang_code != "en":
        qt_translator = QTranslator(app)
        qt_translator.load("qt_en", qt_path)
        app.installTranslator(qt_translator)


def _check_yay():
    """Warn if no supported AUR helper is installed."""
    import shutil
    return any(shutil.which(helper) for helper in SUPPORTED_AUR_HELPERS)


def main():
    _setup_logging()

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName(APP_NAME.lower())
    app.setOrganizationDomain(APP_DOMAIN)
    app.setDesktopFileName("wakka")

    # Don't quit when all windows are closed (tray keeps it alive)
    app.setQuitOnLastWindowClosed(False)

    # ── Config (must be first) ────────────────────────────────────────────
    config = ConfigManager()

    # ── i18n ─────────────────────────────────────────────────────────────
    language = config.get("language", "auto")
    _load_translations(app, language)

    # ── File arguments (direct package install support) ────────────────
    file_paths = [arg for arg in sys.argv[1:] if not arg.startswith("-")]
    start_in_tray = any(arg in sys.argv[1:] for arg in ("--tray", "--hidden", "--minimized"))

    # ── Check dependencies ────────────────────────────────────────────────
    if not _check_yay():
        from PyQt6.QtCore import QCoreApplication
        msg = QMessageBox()
        msg.setWindowTitle(QCoreApplication.translate("Main", "Wakka — Dependencia faltante"))
        msg.setText(
            QCoreApplication.translate("Main", "No se encontró yay ni paru en el sistema.\n\n") +
            QCoreApplication.translate("Main", "Wakka requiere yay (o paru) como backend AUR.\n") +
            QCoreApplication.translate("Main", "Instala yay desde AUR antes de usar Wakka.")
        )
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.exec()
        # Allow limited functionality

    # ── Core components ───────────────────────────────────────────────────
    pkg_manager   = PackageManager(language)
    cache_manager = CacheManager()
    scheduler     = UpdateScheduler()

    # ── Main Window ───────────────────────────────────────────────────────
    window = MainWindow(pkg_manager, cache_manager, config, scheduler)
    restart_requested = False

    if file_paths:
        pkg_manager.install_files(file_paths)

    def on_restart_requested():
        nonlocal restart_requested
        restart_requested = True
        app.quit()

    window.restart_requested.connect(on_restart_requested)

    # ── Tray Icon ─────────────────────────────────────────────────────────
    if QApplication.instance() and hasattr(app, 'platformName'):
        tray = TrayIcon()

        # Wire tray ↔ window
        tray.open_requested.connect(window.show_and_raise)
        tray.update_requested.connect(window.trigger_update_all)
        tray.quit_requested.connect(app.quit)
        window.update_count_changed.connect(tray.set_update_count)
        window.update_count_changed.connect(
            lambda n: tray.notify_updates(n) if n > 0 and config.get("notifications", True) else None
        )

        # GNOME warning
        desktop = os.getenv("XDG_CURRENT_DESKTOP", "").upper()
        if "GNOME" in desktop and not tray.is_available():
            log.warning("System tray not available — GNOME may need KStatusNotifierItem extension")
    else:
        tray = None

    # ── Autostart ─────────────────────────────────────────────────────────
    if config.get("autostart", True):
        config.set_autostart(True)

    # ── Initial display ───────────────────────────────────────────────────
    # Autostart launches use tray; normal launches show the main window.
    lockfile = Path.home() / ".local" / "share" / "wakka" / ".first_run"
    if not lockfile.exists():
        lockfile.parent.mkdir(parents=True, exist_ok=True)
        lockfile.touch()

    if start_in_tray and tray and tray.is_available():
        window.hide()
    else:
        window.show()

    log.info("Wakka started successfully")
    app.aboutToQuit.connect(pkg_manager.cancel)

    exit_code = app.exec()
    if restart_requested:
        os.execv(sys.executable, [sys.executable] + sys.argv)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
