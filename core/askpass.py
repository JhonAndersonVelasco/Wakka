#!/usr/bin/env python3
"""
Wakka — Standalone Password Dialog (SUDO_ASKPASS)
Custom QDialog for a professional "pkexec-like" experience.
"""
import sys
import re
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton
)
from PyQt6.QtCore import Qt, QTranslator, QLocale
from PyQt6.QtGui import QIcon

# Import theme helper for standalone dialog
try:
    from ui.styles.theme import style_askpass_dialog, style_text
except ImportError:
    # Fallback for standalone execution
    style_askpass_dialog = None
    style_text = None

class PasswordDialog(QDialog):
    def __init__(self, prompt: str):
        super().__init__()
        self.setWindowTitle(self.tr("Wakka — Autenticación"))
        self.setMinimumWidth(450)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

        # Icon
        self.setWindowIcon(QIcon.fromTheme("dialog-password", QIcon.fromTheme("lock")))

        self._setup_ui(prompt)

    def _setup_ui(self, prompt: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(16)

        # Header with icon and prompt
        header = QHBoxLayout()
        icon_lbl = QLabel()
        pm = QIcon.fromTheme("dialog-password").pixmap(32, 32)
        if pm.isNull():
             pm = QIcon.fromTheme("lock").pixmap(32, 32)
        icon_lbl.setPixmap(pm)

        msg_lbl = QLabel(self._normalize_prompt(prompt))
        msg_lbl.setWordWrap(True)
        if style_text:
            msg_lbl.setStyleSheet(style_text("text_primary", size=13, weight="bold"))
        else:
            msg_lbl.setStyleSheet("font-weight: bold; font-size: 13px;")

        header.addWidget(icon_lbl)
        header.addSpacing(16)
        header.addWidget(msg_lbl)
        header.addStretch()
        layout.addLayout(header)

        # Password input
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText(self.tr("Contraseña de administrador"))
        self.password_input.setFixedHeight(30)
        self.password_input.returnPressed.connect(self.accept)
        layout.addWidget(self.password_input)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton(self.tr("Cancelar"))
        cancel_btn.setMinimumWidth(90)
        cancel_btn.clicked.connect(self.reject)

        accept_btn = QPushButton(self.tr("Aceptar"))
        accept_btn.setMinimumWidth(90)
        accept_btn.setObjectName("PrimaryButton") # Styling hint
        accept_btn.setDefault(True)
        accept_btn.clicked.connect(self.accept)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(accept_btn)
        layout.addLayout(btn_layout)

        # Apply theme-based styling if available, otherwise use fallback
        if style_askpass_dialog:
            self.setStyleSheet(style_askpass_dialog())
        else:
            self.setStyleSheet("""
                QDialog { background-color: #1a1c24; color: #e8ecf4; }
                QLabel { color: #e8ecf4; }
                QLineEdit {
                    background-color: #242730;
                    border: 1px solid rgba(255,255,255,0.1);
                    border-radius: 4px;
                    padding: 4px 8px;
                    color: #ffffff;
                }
                QPushButton {
                    padding: 6px 12px;
                    border-radius: 4px;
                    background-color: #2d313d;
                    color: #ffffff;
                    border: 1px solid rgba(255,255,255,0.05);
                }
                QPushButton#PrimaryButton {
                    background-color: #7c6af7;
                    font-weight: bold;
                }
            """)

    def _normalize_prompt(self, prompt: str) -> str:
        prompt = (prompt or "").strip()
        match = re.match(r"^\[sudo\]\s*(?:contraseña|password)\s*(?:para|for)\s*(.+?):?$",
                         prompt, flags=re.IGNORECASE)
        if match:
            user = match.group(1)
            return self.tr("Enter sudo password for %1").replace("%1", user)
        return prompt or self.tr("Password required:")

def main():
    app = QApplication(sys.argv)

    # Load Translator
    i18n_path = Path(__file__).resolve().parent.parent / "i18n"
    locale = QLocale.system().name().split('_')[0]  # 'es', 'en', etc.

    translator = QTranslator()
    if translator.load(f"wakka_{locale}.qm", str(i18n_path)):
        app.installTranslator(translator)

    prompt = sys.argv[1] if len(sys.argv) > 1 else "Password required:"

    dlg = PasswordDialog(prompt)
    if dlg.exec() == QDialog.DialogCode.Accepted:
        pwd = dlg.password_input.text()
        if pwd:
            print(pwd)
            sys.exit(0)

    sys.exit(1)

if __name__ == "__main__":
    main()
