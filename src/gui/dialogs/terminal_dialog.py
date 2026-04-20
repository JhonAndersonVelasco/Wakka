import os
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
        # Leer el stream de salida línea a línea de forma eficiente
        if not self.process:
            return

        try:
            for line in iter(self.process.stdout.readline, ''):
                if line:
                    self.output_ready.emit(line.strip())
        finally:
            # Solo esperar si el proceso existe y no ha terminado ya
            if self.process and self.process.poll() is None:
                self.process.wait()
        self.finished_work.emit(self.process.returncode)

class TerminalDialog(QDialog):
    def __init__(self, command_description, process=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Wakka - {0}").format(command_description))
        self.setModal(True)
        self.setMinimumSize(1000, 600)
        self.process = process
        self.operation_succeeded = False
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

        # Barra de progreso indeterminada
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # Indeterminado
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

    def append_output(self, text):
        # Only move cursor if terminal already has content to avoid UI freeze on empty QTextEdit
        if self.terminal.toPlainText():
            self.terminal.moveCursor(QTextCursor.MoveOperation.End)

        # Colorear según el tipo de mensaje
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
        # 1. Actualizar la UI para reflejar el estado final
        self.progress.setRange(0, 100)
        self.progress.setValue(100)
        self.operation_succeeded = return_code == 0

        if return_code == 0:
            self.append_output(self.tr("\n✅ Operación completada exitosamente"))
            QTimer.singleShot(1000, self.accept)
        else:
            self.append_output(self.tr("\n❌ Operación fallida (código {0})").format(return_code))

        # 2. Deshabilitar botones de acción y habilitar el botón de cerrar (si no se cerró ya)
        self.cancel_btn.setEnabled(False)
        self.close_btn.setEnabled(True)
    
    def cancel_operation(self):
        if self.process and self.process.poll() is None:
            try:
                # Intentar matar el grupo de procesos completo (gracias a start_new_session=True)
                pgid = os.getpgid(self.process.pid)
                os.killpg(pgid, signal.SIGTERM)
                
                # Dar un momento y forzar si es necesario
                QTimer.singleShot(2000, lambda: self._ensure_killed(pgid))
                
                self.append_output(self.tr("\n⚠️ Operación cancelada por el usuario (enviada señal de término)"))
            except Exception as e:
                self.append_output(self.tr("\n❌ Error al intentar cancelar: {0}").format(e))
            
            # Actualizar estado de la operación y UI
            self.operation_succeeded = False
            self.cancel_btn.setEnabled(False)
            self.close_btn.setEnabled(True)

    def _ensure_killed(self, pgid):
        """Asegura que el grupo de procesos esté muerto usando SIGKILL si es necesario"""
        try:
            os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            pass # Ya terminó
        except Exception:
            pass

    def closeEvent(self, event):
        if self.process and self.process.poll() is None:
            event.ignore()  # No cerrar si está corriendo
