import os
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from gui.main_window import MainWindow
from i18n.translator import Translator
from core.config_manager import ConfigManager
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt


def load_app_icon() -> QIcon:
    icon = QIcon.fromTheme("wakka")

    if icon.isNull():
        candidates = [
            "/usr/share/icons/hicolor/scalable/apps/wakka.svg",
            os.path.join(os.path.dirname(__file__), "resources", "wakka.svg"),
            os.path.join(os.getcwd(), "src", "resources", "wakka.svg"),
            os.path.join(os.getcwd(), "resources", "wakka.svg"),
        ]
        for path in candidates:
            if os.path.exists(path):
                icon = QIcon(path)
                break

        if icon.isNull():
            icon = QIcon.fromTheme("package-manager")

    return icon

def apply_theme(app, theme_name):
    if theme_name == "system":
        return
        
    app.setStyle("Fusion")
    if theme_name == "dark":
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(45, 45, 45))
        palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Base, QColor(30, 30, 30))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(45, 45, 45))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(45, 45, 45))
        palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
        palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
        app.setPalette(palette)
    elif theme_name == "light":
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(245, 245, 245))
        palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.black)
        palette.setColor(QPalette.ColorRole.Base, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 220))
        palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.black)
        palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.black)
        palette.setColor(QPalette.ColorRole.Button, QColor(245, 245, 245))
        palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.black)
        palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
        palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.white)
        app.setPalette(palette)

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Wakka")
    app.setDesktopFileName("wakka")

    # Cargar traducciones (Wakka + Qt Base)
    translator = Translator()
    translator.load(app)

    icon = load_app_icon()

    # Aplicar Tema
    config = ConfigManager()
    apply_theme(app, config.get("theme", "system"))

    app.setWindowIcon(icon)

    window = MainWindow()
    window.setWindowIcon(icon)
    
    # Si se inicia con --tray, no mostramos la ventana principal
    if "--tray" not in sys.argv:
        window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
    