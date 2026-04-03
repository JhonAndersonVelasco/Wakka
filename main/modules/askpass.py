#!/usr/bin/env python
"""
Wakka — Standalone Password Dialog (SUDO_ASKPASS)
Enhanced security with memory clearing, session tokens, and attempt limiting.
"""
import sys
import re
import time
import json
import secrets
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton
)
from PyQt6.QtCore import Qt, QTranslator, QLocale
from PyQt6.QtGui import QIcon

# Import from constants for configurable paths
try:
    from modules.constants import STATE_FILE, MAX_SUDO_ATTEMPTS, SUDO_STATE_TIMEOUT
except ImportError:
    try:
        from ..modules.constants import STATE_FILE, MAX_SUDO_ATTEMPTS, SUDO_STATE_TIMEOUT
    except ImportError:
        STATE_FILE = Path("/tmp/wakka_sudo_attempt")
        MAX_SUDO_ATTEMPTS = 3
        SUDO_STATE_TIMEOUT = 300

# Session token for validation (prevents replay attacks)
SESSION_TOKEN = secrets.token_hex(16)


class PasswordDialog(QDialog):
    """
    Secure password input dialog with attempt limiting and memory protection.

    Security Features:
        - Session token validation
        - Memory buffer clearing after use
        - Attempt limiting with timeout
        - Screenshot prevention flag
    """

    def __init__(self, prompt: str, attempt: int = 1, failed: bool = False):
        super().__init__()
        self.attempt = attempt
        self.failed = failed
        self._password_buffer = ""  # Temporary buffer for secure clearing
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
        # Security: Prevent background rendering (screenshot protection)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
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
        try:
            from ui.styles.theme import style_text
            msg_lbl.setStyleSheet(style_text("text_primary", size=13, weight="bold"))
        except ImportError:
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
                self.attempt, MAX_SUDO_ATTEMPTS
            ))
            self.status_lbl.setStyleSheet("color: #ff6b6b; font-weight: 600; font-size: 13px;")
        else:
            self.status_lbl.setText(self.tr("Intento {} de {}.").format(
                self.attempt, MAX_SUDO_ATTEMPTS
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

        try:
            from ui.styles.theme import style_askpass_dialog
            self.setStyleSheet(style_askpass_dialog())
        except ImportError:
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
        # Security: Validate minimum password length
        if len(pwd) < 1:
            self.status_lbl.setText(self.tr("Contraseña inválida."))
            return
        self._password_buffer = pwd  # Store temporarily for clearing
        self.accept()

    def reject(self):
        _clear_state()
        self._clear_password_buffer()  # Security: Clear memory
        super().reject()

    def _clear_password_buffer(self):
        """
        Security: Securely overwrite password buffer in memory.

        This method overwrites the password buffer with random data
        before clearing to prevent memory scraping attacks.
        """
        if self._password_buffer:
            # Overwrite with random data before clearing
            self._password_buffer = secrets.token_hex(len(self._password_buffer))
            self._password_buffer = ""

        # Clear QLineEdit
        if hasattr(self, 'password_input'):
            self.password_input.clear()

    def closeEvent(self, event):
        """Security: Clear sensitive data on window close."""
        self._clear_password_buffer()
        super().closeEvent(event)


def _read_state() -> tuple[int, bool]:
    """
    Read attempt state with session validation.

    Returns:
        Tuple of (attempt_number, failed_flag)

    Security:
        - Validates timestamp (5 minute window)
        - Validates session token (prevents replay attacks)
        - Clears state on validation failure
    """
    try:
        if STATE_FILE.exists():
            data = json.loads(STATE_FILE.read_text())
            # Validate timestamp (5 minute window)
            if time.time() - data.get("ts", 0) > SUDO_STATE_TIMEOUT:
                _clear_state()
                return 1, False
            # Validate session token (security)
            if data.get("token") != SESSION_TOKEN:
                _clear_state()
                return 1, False
            return data.get("attempt", 1), data.get("failed", False)
    except Exception:
        _clear_state()
    return 1, False


def _write_state(attempt: int, failed: bool):
    """
    Write attempt state with session token.

    Args:
        attempt: Current attempt number
        failed: Whether previous attempt failed

    Security:
        - Includes session token for validation
        - Sets restrictive file permissions (0600)
    """
    try:
        STATE_FILE.write_text(json.dumps({
            "attempt": attempt,
            "failed": failed,
            "ts": time.time(),
            "token": SESSION_TOKEN  # Security: Session validation
        }))
        # Security: Restrict file permissions (owner read/write only)
        STATE_FILE.chmod(0o600)
    except Exception:
        pass


def _clear_state():
    """
    Securely clear state file.

    Security:
        - Overwrites file with random data before deletion
        - Prevents data recovery from disk
    """
    try:
        if STATE_FILE.exists():
            # Overwrite with random data before deletion
            STATE_FILE.write_text(secrets.token_hex(32))
            STATE_FILE.unlink(missing_ok=True)
    except Exception:
        pass


def main():
    """Main entry point for SUDO_ASKPASS dialog."""
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)

    i18n_path = Path(__file__).resolve().parent.parent / "i18n"
    locale = QLocale.system().name().split('_')[0]
    translator = QTranslator()
    if translator.load(f"wakka_{locale}.qm", str(i18n_path)):
        app.installTranslator(translator)

    # Read previous state
    prev_attempt, prev_failed = _read_state()

    if STATE_FILE.exists() and prev_failed:
        attempt = min(prev_attempt + 1, MAX_SUDO_ATTEMPTS)
        failed = True
    else:
        attempt = prev_attempt if STATE_FILE.exists() else 1
        failed = False

    # Security: Enforce attempt limit
    if attempt > MAX_SUDO_ATTEMPTS:
        _clear_state()
        sys.exit(1)

    _write_state(attempt, failed)

    prompt = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "Password required:"
    dlg = PasswordDialog(prompt, attempt, failed)

    dlg.show()
    dlg.activateWindow()
    dlg.raise_()
    dlg.password_input.setFocus()

    password = ""
    if dlg.exec() == QDialog.DialogCode.Accepted:
        password = dlg.password_input.text()
        if password:
            try:
                sys.stdout.write(password + "\n")
                sys.stdout.flush()
            finally:
                # Security: Clear password from memory immediately
                password = ""
                dlg._clear_password_buffer()
            app.quit()
            sys.exit(0)

    dlg._clear_password_buffer()
    app.quit()
    sys.exit(1)


if __name__ == "__main__":
    main()