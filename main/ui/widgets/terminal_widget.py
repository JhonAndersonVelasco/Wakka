"""
Wakka — Terminal Output Widget
Displays real-time output from yay/pacman commands with ANSI color stripping,
syntax highlighting, and a collapsible panel.
"""
from __future__ import annotations

from PyQt6.QtCore import pyqtSignal, Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QColor, QTextCharFormat, QTextCursor, QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QLabel, QSizePolicy,
)
from ..styles.icons import get_icon
from ..styles.theme import style_terminal_header, style_terminal_status, get_color
import re


_ANSI_ESCAPE = re.compile(r"\x1B\[[0-9;]*m")


def _strip_ansi(text: str) -> str:
    return _ANSI_ESCAPE.sub("", text)


_COLOR_STDOUT = QColor(get_color("text_primary"))
_COLOR_STDERR = QColor(get_color("danger"))
_COLOR_SUCCESS = QColor(get_color("success"))
_COLOR_CMD = QColor(get_color("accent"))
_COLOR_WARN = QColor(get_color("warning"))


def _colorize(text: str) -> QColor:
    """Pick a color based on the content of the line."""
    t = text.lower()
    if any(k in t for k in ("error", "fehler", "erro", "erreur")):
        return _COLOR_STDERR
    if any(k in t for k in ("warning", "advertencia", "avertissement")):
        return _COLOR_WARN
    if any(k in t for k in ("installed", "instalado", "complete", "done", "listo", "ok")):
        return _COLOR_SUCCESS
    if t.startswith("→") or t.startswith("::"):
        return _COLOR_CMD
    return _COLOR_STDOUT


class TerminalWidget(QWidget):
    """
    Collapsible panel showing live output from package operations.
    """
    cancel_requested = pyqtSignal()

    PANEL_HEIGHT = 220

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TerminalWidget")
        self._collapsed = True
        self._setup_ui()

    def _setup_ui(self):
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Header bar ────────────────────────────────────────────────────────
        header = QWidget()
        header.setObjectName("TerminalWidget")
        header.setFixedHeight(36)
        header.setCursor(Qt.CursorShape.PointingHandCursor)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(14, 0, 14, 0)

        term_icon = QLabel()
        term_icon.setPixmap(get_icon("terminal", "#8892a4", 14).pixmap(14, 14))

        self._title = QLabel(self.tr("Consola"))
        self._title.setStyleSheet(style_terminal_header())

        self._status_label = QLabel("")
        self._status_label.setStyleSheet(style_terminal_status())

        self._cancel_btn = QPushButton(self.tr("Cancelar"))
        self._cancel_btn.setObjectName("DangerButton")
        self._cancel_btn.setMinimumWidth(80)
        self._cancel_btn.setFixedHeight(24)
        self._cancel_btn.setStyleSheet("padding: 0 10px; font-size: 11px;")
        self._cancel_btn.setVisible(False)
        self._cancel_btn.clicked.connect(self.cancel_requested)

        self._toggle_btn = QPushButton()
        self._toggle_btn.setFixedSize(24, 24)
        self._toggle_btn.clicked.connect(self._toggle)
        self._update_toggle_icon()

        h_layout.addWidget(term_icon)
        h_layout.addSpacing(6)
        h_layout.addWidget(self._title)
        h_layout.addSpacing(8)
        h_layout.addWidget(self._status_label)
        h_layout.addStretch()
        h_layout.addWidget(self._cancel_btn)
        h_layout.addSpacing(8)
        h_layout.addWidget(self._toggle_btn)

        # ── Output area ───────────────────────────────────────────────────────
        self._output = QTextEdit()
        self._output.setObjectName("TerminalOutput")
        self._output.setReadOnly(True)
        self._output.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)

        font = QFont()
        font.setFamilies(["JetBrains Mono", "Fira Code", "Cascadia Code", "monospace"])
        font.setPointSize(10)
        self._output.setFont(font)
        self._output.setFixedHeight(0)

        main_layout.addWidget(header)
        main_layout.addWidget(self._output)

        # Click on header toggles
        header.mousePressEvent = lambda _: self._toggle()

    # ─── Public API ───────────────────────────────────────────────────────────

    def append_line(self, text: str, is_error: bool = False):
        """Append a line of output with appropriate coloring."""
        clean = _strip_ansi(text)
        clean = clean.replace("\r\n", "\n").replace("\r", "\n")
        if not clean.strip() and '\n' not in clean:
            return

        fmt = QTextCharFormat()
        if is_error:
            fmt.setForeground(_COLOR_STDERR)
        else:
            fmt.setForeground(_colorize(clean))

        cursor = self._output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(clean, fmt)
        self._output.setTextCursor(cursor)
        self._output.ensureCursorVisible()

        # Auto-expand when output starts coming in
        if self._collapsed and clean.strip():
            self.expand()

    def set_status(self, text: str, color: str | None = None):
        self._status_label.setText(text)
        self._status_label.setStyleSheet(style_terminal_status(color))

    def set_busy(self, busy: bool):
        self._cancel_btn.setVisible(busy)
        if busy:
            self.set_status(self.tr("En progreso..."), "#f5a623")
        else:
            self.set_status("", "#8892a4")

    def clear(self):
        self._output.clear()

    # ─── Collapse / Expand ────────────────────────────────────────────────────

    def _toggle(self):
        if self._collapsed:
            self.expand()
        else:
            self.collapse()

    def expand(self):
        self._collapsed = False
        self._animate_height(0, self.PANEL_HEIGHT)
        self._update_toggle_icon()

    def collapse(self):
        self._collapsed = True
        self._animate_height(self._output.height(), 0)
        self._update_toggle_icon()

    def _animate_height(self, start: int, end: int):
        anim = QPropertyAnimation(self._output, b"maximumHeight", self)
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.setDuration(200)
        anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        # Also fix the minimum
        if end > 0:
            self._output.setMinimumHeight(end)
        anim.finished.connect(lambda: self._output.setMinimumHeight(end))
        anim.start()

    def _update_toggle_icon(self):
        icon_name = "chevron_up" if self._collapsed else "chevron_down"
        self._toggle_btn.setIcon(get_icon(icon_name, "#8892a4", 14))
