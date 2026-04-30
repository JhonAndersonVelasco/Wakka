import os
import re
import signal
import subprocess

from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QPushButton,
    QLabel,
    QProgressBar,
)
from PyQt6.QtCore import QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QPalette, QTextCursor


class WorkerThread(QThread):
    output_ready = pyqtSignal(str)
    finished_work = pyqtSignal(int)

    def __init__(self, process: subprocess.Popen | None):
        super().__init__()
        self.process = process

    def run(self) -> None:
        if not self.process:
            self.finished_work.emit(-1)
            return
        stdout = self.process.stdout
        try:
            if stdout is not None:
                for line in iter(stdout.readline, ""):
                    if line:
                        self.output_ready.emit(line.strip())
        finally:
            if self.process.poll() is None:
                self.process.wait()
        rc = self.process.returncode
        self.finished_work.emit(rc if rc is not None else -1)


_PHASES = [
    (re.compile(r"resolviendo dependencias|resolving dependencies", re.I), 2, 8),
    (re.compile(r"verificando conflictos|checking for conflicts", re.I), 8, 12),
    (re.compile(r"descargando|downloading", re.I), 12, 60),
    (re.compile(r"verificando integridad|checking integrity|checking package", re.I), 60, 68),
    (re.compile(r"verificando llaves|checking keyring|loading package", re.I), 68, 72),
    (re.compile(r"instalando|installing|actualizando|upgrading", re.I), 72, 95),
    (re.compile(r"configurando|running post", re.I), 95, 98),
]

_DL_COUNTER = re.compile(r"\((\d+)/(\d+)\)")


class TerminalDialog(QDialog):
    def __init__(self, command_description, process=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Wakka - {0}").format(command_description))
        self.setModal(True)
        self.setMinimumSize(1000, 600)
        self.process = process

        self.auto_close_allowed = True
        self.operation_succeeded = False

        self._progress_value = 0
        self._dl_phase_active = False

        self._apply_palette_colors()

        self.setup_ui()
        self.setup_worker()

    def _apply_palette_colors(self) -> None:
        app = QApplication.instance()
        if self.parent():
            pal = self.parent().palette()
        elif app:
            pal = app.palette()
        else:
            pal = QPalette()
        base = pal.color(QPalette.ColorRole.Base)
        lum = base.red() * 0.299 + base.green() * 0.587 + base.blue() * 0.114
        if lum < 128:
            self._term_bg = base.name()
            self._term_fg = QColor("#66ff99")
            self._term_err = QColor("#ff6666")
            self._term_warn = QColor("#ffcc66")
        else:
            self._term_bg = base.name()
            self._term_fg = QColor("#0d5c2e")
            self._term_err = QColor("#b00020")
            self._term_warn = QColor("#b8860b")

        hl = pal.color(QPalette.ColorRole.Highlight)
        hl_text = pal.color(QPalette.ColorRole.HighlightedText)
        self._header_bg = hl.name()
        self._header_fg = hl_text.name()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        header = QLabel(self.tr("<b>Operación:</b> {0}").format(self.windowTitle()))
        header.setStyleSheet(
            f"font-size: 14px; padding: 10px; background-color: {self._header_bg}; color: {self._header_fg};"
        )
        layout.addWidget(header)

        self.terminal = QTextEdit()
        self.terminal.setReadOnly(True)
        self.terminal.setStyleSheet(
            f"""
            QTextEdit {{
                background-color: {self._term_bg};
                color: {self._term_fg.name()};
                font-family: 'Monospace', 'Courier New', monospace;
                font-size: 14px;
                padding: 10px;
                border: none;
            }}
            """
        )
        layout.addWidget(self.terminal)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(1)
        layout.addWidget(self.progress)

        btn_layout = QHBoxLayout()
        self.cancel_btn = QPushButton(self.tr("Cancelar"))
        self.cancel_btn.clicked.connect(self.cancel_operation)
        btn_layout.addWidget(self.cancel_btn)

        self.close_btn = QPushButton(self.tr("Cerrar"))
        self.close_btn.setEnabled(False)
        self.close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.close_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def setup_worker(self):
        if self.process:
            self.worker = WorkerThread(self.process)
            self.worker.output_ready.connect(self.append_output)
            self.worker.finished_work.connect(self.on_finished)
            self.worker.start()

    def _advance_progress(self, target: int):
        if target > self._progress_value:
            self._progress_value = target
            self.progress.setValue(self._progress_value)

    def _parse_progress(self, line: str):
        m = _DL_COUNTER.search(line)
        if m:
            current, total = int(m.group(1)), int(m.group(2))
            if total > 0:
                self._advance_progress(12 + int((current / total) * 48))
            return
        for pattern, start, end in _PHASES:
            if pattern.search(line):
                self._advance_progress(start)
                break

    # Patrones que indican un error real que debe bloquear el cierre automático.
    # Son lo suficientemente específicos para no capturar mensajes informativos
    # de herramientas como gdb-add-index, makepkg o yay que usan "error" en
    # contextos no fatales (p.ej. "No debugging symbols", "Error while writing index").
    _REAL_ERROR_PATTERNS = [
        re.compile(r"^error:", re.I),                        # pacman/yay: "error: ..."
        re.compile(r"^==> error:", re.I),                    # makepkg: "==> ERROR: ..."
        re.compile(r"failed to (install|commit|download|synchronize)", re.I),
        re.compile(r"transaction failed|could not satisfy|conflicting files", re.I),
        re.compile(r"^fatal:", re.I),                        # git u otros
    ]

    def _is_real_error(self, text: str) -> bool:
        return any(p.search(text) for p in self._REAL_ERROR_PATTERNS)

    def append_output(self, text):
        self._parse_progress(text)

        lower = text.lower()
        if self._is_real_error(text):
            self.terminal.setTextColor(self._term_err)
            self.auto_close_allowed = False
        elif "warning" in lower or "advertencia" in lower:
            self.terminal.setTextColor(self._term_warn)
        else:
            self.terminal.setTextColor(self._term_fg)

        self.terminal.insertPlainText(text + "\n")
        self.terminal.moveCursor(QTextCursor.MoveOperation.End)

    def on_finished(self, return_code):
        self.operation_succeeded = return_code == 0
        self.progress.setValue(100)
        self.cancel_btn.setEnabled(False)
        self.close_btn.setEnabled(True)

        if self.operation_succeeded and self.auto_close_allowed:
            self.terminal.setTextColor(self._term_fg)
            self.append_output(self.tr("\n✅ Completado."))
            QTimer.singleShot(5000, self.accept)
        elif self.operation_succeeded:
            # Terminó bien pero hubo líneas de error no fatales (ej. gdb-add-index)
            self.terminal.setTextColor(self._term_fg)
            self.append_output(self.tr("\n✅ Completado con advertencias."))
            #self.close_btn.setFocus()
            QTimer.singleShot(30000, self.accept)
        else:
            self.progress.setStyleSheet("QProgressBar::chunk { background-color: #f44336; }")
            self.terminal.setTextColor(self._term_warn)
            self.append_output(self.tr("\n⚠️ Proceso detenido. Revisa los errores arriba."))
            self.close_btn.setFocus()

    def cancel_operation(self):
        if self.process and self.process.poll() is None:
            os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            self.auto_close_allowed = False
            self.cancel_btn.setEnabled(False)
            self.close_btn.setEnabled(True)

    def closeEvent(self, event):
        if self.process and self.process.poll() is None:
            event.ignore()
        else:
            super().closeEvent(event)
