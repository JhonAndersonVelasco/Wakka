import os
import re
import signal
import subprocess
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QLabel, QProgressBar, QMessageBox
    )
from PyQt6.QtCore import QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QTextCursor, QColor

class WorkerThread(QThread):
    output_ready = pyqtSignal(str)
    finished_work = pyqtSignal(int)

    def __init__(self, process):
        super().__init__()
        self.process = process

    def run(self):
        if not self.process:
            return
        try:
            for line in iter(self.process.stdout.readline, ''):
                if line:
                    self.output_ready.emit(line.strip())
        finally:
            if self.process and self.process.poll() is None:
                self.process.wait()
        self.finished_work.emit(self.process.returncode)


# Fases de instalación con su rango aproximado en la barra (inicio%, fin%)
_PHASES = [
    # Resolución de dependencias
    (re.compile(r"resolviendo dependencias|resolving dependencies", re.I),        2,  8),
    (re.compile(r"verificando conflictos|checking for conflicts", re.I),          8, 12),
    # Descarga (actualizamos con contadores reales cuando aparezcan)
    (re.compile(r"descargando|downloading", re.I),                               12, 60),
    # Integridad y llaves
    (re.compile(r"verificando integridad|checking integrity|checking package", re.I), 60, 68),
    (re.compile(r"verificando llaves|checking keyring|loading package", re.I),   68, 72),
    # Instalación / actualización
    (re.compile(r"instalando|installing|actualizando|upgrading", re.I),          72, 95),
    (re.compile(r"configurando|running post", re.I),                             95, 98),
]

# Patrón: "Descargando X (n/N)"  o  "(n/N)"  — yay usa esto para cada paquete
_DL_COUNTER = re.compile(r"\((\d+)/(\d+)\)")

# Patrón porcentaje explícito: "##########  75%"  o similar
_PCT_LINE = re.compile(r"(\d{1,3})%")


class TerminalDialog(QDialog):
    def __init__(self, command_description, process=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Wakka - {0}").format(command_description))
        self.setModal(True)
        self.setMinimumSize(1000, 600)
        self.process = process
        self.operation_succeeded = False

        # Estado del progreso
        self._progress_value = 0
        self._dl_phase_active = False

        self.setup_ui()
        self.setup_worker()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Header
        header = QLabel(self.tr("<b>Operación:</b> {0}").format(self.windowTitle()))
        header.setStyleSheet("font-size: 14px; padding: 10px; background-color: #2196F3; color: white;")
        layout.addWidget(header)

        # Terminal output
        self.terminal = QTextEdit()
        self.terminal.setReadOnly(True)
        self.terminal.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #00ff00;
                font-family: 'Monospace', 'Courier New';
                font-size: 14px;
                padding: 10px;
                border: none;
            }
        """)
        layout.addWidget(self.terminal)

        # Barra de progreso (empieza en 1%, determinada)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(1)
        self.progress.setTextVisible(True)
        self.progress.setFormat(self.tr("Iniciando...  %p%"))
        layout.addWidget(self.progress)

        # Botones
        btn_layout = QHBoxLayout()

        self.cancel_btn = QPushButton(self.tr("Cancelar operación"))
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 10px 20px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #da190b; }
        """)
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

    # ── Progreso real ────────────────────────────────────────────────────────

    def _advance_progress(self, target: int):
        """Mueve la barra hacia target sin retroceder."""
        if target > self._progress_value:
            self._progress_value = target
            self.progress.setValue(self._progress_value)

    def _parse_progress(self, line: str):
        """Infiere el progreso a partir del texto de salida de yay/pacman."""
        # 1. Contador de descargas: "(n/N)"
        m = _DL_COUNTER.search(line)
        if m:
            current, total = int(m.group(1)), int(m.group(2))
            if total > 0:
                # Mapear n/N dentro del rango de descarga (12%–60%)
                pct = 12 + int((current / total) * 48)
                self._dl_phase_active = True
                self._advance_progress(pct)
                self.progress.setFormat(
                    self.tr("Descargando {0}/{1}  %p%").format(current, total)
                )
            return

        # 2. Porcentaje explícito en línea (ej. barras de pacman)
        m = _PCT_LINE.search(line)
        if m and not self._dl_phase_active:
            raw_pct = int(m.group(1))
            # Pacman usa 0-100% en la fase de instalación (72%–95%)
            mapped = 72 + int((raw_pct / 100) * 23)
            self._advance_progress(min(mapped, 95))
            return

        # 3. Fase por palabras clave
        for pattern, start, end in _PHASES:
            if pattern.search(line):
                # Al entrar en una nueva fase avanzamos al inicio de esa fase
                self._advance_progress(start)
                label = line[:40].strip() or self.progress.format()
                if "descargando" in line.lower() or "downloading" in line.lower():
                    self._dl_phase_active = True
                else:
                    self._dl_phase_active = False
                self.progress.setFormat(f"{label[:30]}…  %p%")
                break

    # ── Salida de texto ──────────────────────────────────────────────────────

    def append_output(self, text):
        # Parsear progreso antes de pintar
        self._parse_progress(text)

        if self.terminal.toPlainText():
            self.terminal.moveCursor(QTextCursor.MoveOperation.End)

        if "error" in text.lower() or "failed" in text.lower():
            self.terminal.setTextColor(QColor("#ff4444"))
        elif "warning" in text.lower():
            self.terminal.setTextColor(QColor("#ffaa00"))
        elif "installing" in text.lower() or "upgrading" in text.lower():
            self.terminal.setTextColor(QColor("#00aaff"))
        else:
            self.terminal.setTextColor(QColor("#00ff00"))

        self.terminal.insertPlainText(text + "\n")
        self.terminal.ensureCursorVisible()

    def on_finished(self, return_code):
        self.progress.setRange(0, 100)
        self.progress.setValue(100)
        self.progress.setFormat("100%")
        self.operation_succeeded = return_code == 0

        if return_code == 0:
            self.append_output(self.tr("\n✅ Operación completada exitosamente"))
            QTimer.singleShot(1000, self.accept)
        else:
            self.append_output(self.tr("\n❌ Operación fallida (código {0})").format(return_code))

        self.cancel_btn.setEnabled(False)
        self.close_btn.setEnabled(True)

    def cancel_operation(self):
        if self.process and self.process.poll() is None:
            try:
                pgid = os.getpgid(self.process.pid)
                os.killpg(pgid, signal.SIGTERM)
                QTimer.singleShot(2000, lambda: self._ensure_killed(pgid))
                self.append_output(self.tr("\n⚠️ Operación cancelada por el usuario (enviada señal de término)"))
            except Exception as e:
                self.append_output(self.tr("\n❌ Error al intentar cancelar: {0}").format(e))

            self.operation_succeeded = False
            self.cancel_btn.setEnabled(False)
            self.close_btn.setEnabled(True)

    def _ensure_killed(self, pgid):
        try:
            os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except Exception:
            pass

    def closeEvent(self, event):
        if self.process and self.process.poll() is None:
            event.ignore()
