#!/usr/bin/env python
"""
Wakka — Standalone Password Dialog (SUDO_ASKPASS)
"""
import sys
import re
import time
import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton
)
from PyQt6.QtCore import Qt, QTranslator, QLocale
from PyQt6.QtGui import QIcon

STATE_FILE = Path("/tmp/wakka_sudo_attempt")
MAX_ATTEMPTS = 3

try:
    from ..ui.styles.theme import style_askpass_dialog, style_text
except ImportError:
    try:
        from ui.styles.theme import style_askpass_dialog, style_text
    except ImportError:
        style_askpass_dialog = None
        style_text = None


class PasswordDialog(QDialog):
    def __init__(self, prompt: str, attempt: int = 1, failed: bool = False):
        super().__init__()
        self.attempt = attempt
        self.failed = failed
        self.setWindowTitle(self.tr("Wakka — Autenticación"))
        self.setMinimumWidth(450)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.CustomizeWindowHint |
            Qt.WindowType.WindowTitleHint
        )
        self.setWindowIcon(QIcon.fromTheme("dialog-password", QIcon.fromTheme("lock")))
        self._setup_ui(prompt)

    def _setup_ui(self, prompt: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(16)

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
            msg_lbl.setStyleSheet("font-weight: bold; font-size: 13px; color: #e8ecf4;")

        header.addWidget(icon_lbl)
        header.addSpacing(16)
        header.addWidget(msg_lbl)
        header.addStretch()
        layout.addLayout(header)

        self.status_lbl = QLabel()
        self.status_lbl.setWordWrap(True)

        if self.failed:
            self.status_lbl.setText(self.tr("Contraseña incorrecta. Intento {} de {}.").format(
                self.attempt, MAX_ATTEMPTS
            ))
            self.status_lbl.setStyleSheet("color: #ff6b6b; font-weight: 600; font-size: 13px;")
        else:
            self.status_lbl.setText(self.tr("Intento {} de {}.").format(
                self.attempt, MAX_ATTEMPTS
            ))
            self.status_lbl.setStyleSheet("color: #94a3b8; font-size: 13px;")

        layout.addWidget(self.status_lbl)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText(self.tr("Contraseña de administrador"))
        self.password_input.setMinimumHeight(42)
        self.password_input.setStyleSheet("""
        QLineEdit {
            padding: 10px 14px;
            font-size: 14px;
        }
        """)
        self.password_input.returnPressed.connect(self._on_submit)
        layout.addWidget(self.password_input)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton(self.tr("Cancelar"))
        cancel_btn.setMinimumWidth(90)
        cancel_btn.setMinimumHeight(36)
        cancel_btn.clicked.connect(self.reject)

        accept_btn = QPushButton(self.tr("Aceptar"))
        accept_btn.setMinimumWidth(90)
        accept_btn.setMinimumHeight(36)
        accept_btn.setObjectName("PrimaryButton")
        accept_btn.setDefault(True)
        accept_btn.clicked.connect(self._on_submit)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(accept_btn)
        layout.addLayout(btn_layout)

        if style_askpass_dialog:
            self.setStyleSheet(style_askpass_dialog())
        else:
            self.setStyleSheet("""
            QDialog { background-color: #161b27; }
            QLineEdit {
                background-color: #1a2035;
                border: 1px solid rgba(255,255,255,0.07);
                border-radius: 8px;
                color: #e8ecf4;
            }
            QLineEdit:focus { border-color: #7c6af7; }
            QPushButton {
                background-color: #7c6af7;
                border: none;
                border-radius: 8px;
                color: white;
                font-weight: 600;
                padding: 10px 24px;
            }
            QPushButton:hover { background-color: #9d8fff; }
            QPushButton:pressed { background-color: #5c4ed6; }
            """)

    def _normalize_prompt(self, prompt: str) -> str:
        prompt = (prompt or "").strip()
        match = re.match(r"^\[sudo\]\s*(?:contraseña|password)\s*(?:para|for)\s*(.+?):?$",
                         prompt, flags=re.IGNORECASE)
        if match:
            user = match.group(1)
            return self.tr("Ingrese la contraseña de sudo para %1").replace("%1", user)
        return prompt or self.tr("Contraseña obligatoria:")

    def showEvent(self, event):
        super().showEvent(event)
        self.activateWindow()
        self.raise_()
        self.password_input.setFocus()

    def _on_submit(self):
        pwd = self.password_input.text()
        if not pwd:
            self.status_lbl.setText(self.tr("La contraseña no puede estar vacía."))
            self.status_lbl.setStyleSheet("color: #ff6b6b; font-weight: 600; font-size: 13px;")
            return
        self.accept()

    def reject(self):
        _clear_state()
        super().reject()


def _read_state() -> tuple[int, bool]:
    try:
        if STATE_FILE.exists():
            data = json.loads(STATE_FILE.read_text())
            if time.time() - data.get("ts", 0) > 300:
                return 1, False
            return data.get("attempt", 1), data.get("failed", False)
    except Exception:
        pass
    return 1, False


def _write_state(attempt: int, failed: bool):
    try:
        STATE_FILE.write_text(json.dumps({
            "attempt": attempt,
            "failed": failed,
            "ts": time.time()
        }))
    except Exception:
        pass


def _clear_state():
    try:
        STATE_FILE.unlink(missing_ok=True)
    except Exception:
        pass


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)

    i18n_path = Path(__file__).resolve().parent.parent / "i18n"
    locale = QLocale.system().name().split('_')[0]
    translator = QTranslator()
    if translator.load(f"wakka_{locale}.qm", str(i18n_path)):
        app.installTranslator(translator)

    # Leer estado previo
    prev_attempt, prev_failed = _read_state()

    if STATE_FILE.exists() and prev_failed:
        attempt = min(prev_attempt + 1, MAX_ATTEMPTS)
        failed = True
    else:
        attempt = prev_attempt if STATE_FILE.exists() else 1
        failed = False

    # Límite de intentos
    if attempt > MAX_ATTEMPTS:
        _clear_state()
        sys.exit(1)

    _write_state(attempt, failed)

    prompt = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "Password required:"
    dlg = PasswordDialog(prompt, attempt, failed)

    dlg.show()
    dlg.activateWindow()
    dlg.raise_()
    dlg.password_input.setFocus()

    if dlg.exec() == QDialog.DialogCode.Accepted:
        pwd = dlg.password_input.text()
        if pwd:
            sys.stdout.write(pwd + "\n")
            sys.stdout.flush()
            app.quit()
            sys.exit(0)

    app.quit()
    sys.exit(1)


if __name__ == "__main__":
    main()

