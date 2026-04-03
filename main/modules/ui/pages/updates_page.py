"""
Wakka — Updates Page
Shows available system updates with yay -Qu output.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QFrame, QCheckBox,
)
from main.modules.ui.widgets.package_card import PackageCard
from main.modules.ui.styles.icons import get_icon
from main.modules.ui.styles.theme import style_transparent_bg, style_icon_text, style_title, style_subtitle
from modules.package_manager import Package


class UpdatesPage(QWidget):
    update_all_requested = pyqtSignal()
    update_selected_requested = pyqtSignal(list)     # list[str]
    check_requested = pyqtSignal()
    info_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._packages: list[Package] = []
        self._cards: list[PackageCard] = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Toolbar ─────────────────────────────────────────────────────────
        toolbar = QWidget()
        toolbar.setFixedHeight(60)
        toolbar.setStyleSheet(style_transparent_bg())
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(20, 0, 20, 0)
        tb_layout.setSpacing(10)

        self._select_all = QCheckBox(self.tr("Seleccionar todo"))
        self._select_all.stateChanged.connect(self._on_select_all)

        self._count_label = QLabel("")
        self._count_label.setObjectName("StatusInfo")

        self._check_btn = QPushButton()
        self._check_btn.setIcon(get_icon("refresh", "#8892a4"))
        self._check_btn.setToolTip(self.tr("Buscar actualizaciones"))
        self._check_btn.setFixedSize(36, 36)
        self._check_btn.clicked.connect(self.check_requested)

        self._update_selected_btn = QPushButton(self.tr("Actualizar seleccionados"))
        self._update_selected_btn.setObjectName("PrimaryButton")
        self._update_selected_btn.setEnabled(False)
        self._update_selected_btn.clicked.connect(self._on_update_selected)

        self._update_all_btn = QPushButton(self.tr("Actualizar todo"))
        self._update_all_btn.setObjectName("SuccessButton")
        self._update_all_btn.setEnabled(False)
        self._update_all_btn.clicked.connect(self.update_all_requested)

        tb_layout.addWidget(self._select_all)
        tb_layout.addWidget(self._count_label)
        tb_layout.addStretch()
        tb_layout.addWidget(self._check_btn)
        tb_layout.addWidget(self._update_selected_btn)
        tb_layout.addWidget(self._update_all_btn)

        # ── Content area ────────────────────────────────────────────────────
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._content = QWidget()
        self._content.setStyleSheet(style_transparent_bg())
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(20, 10, 20, 20)
        self._content_layout.setSpacing(6)
        self._content_layout.addStretch()

        self._scroll.setWidget(self._content)

        # Empty state
        self._empty_widget = self._make_empty_state()

        layout.addWidget(toolbar)
        layout.addWidget(self._empty_widget)
        layout.addWidget(self._scroll)
        self._scroll.hide()

    def _make_empty_state(self) -> QWidget:
        w = QWidget()
        vl = QVBoxLayout(w)
        vl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vl.setSpacing(16)

        icon_lbl = QLabel("✨")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet(style_icon_text(48))

        title = QLabel(self.tr("El sistema está al día"))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(style_title(18))

        sub = QLabel(self.tr("No hay actualizaciones disponibles. Pulsa el botón de refrescar para volver a comprobar."))
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setWordWrap(True)
        sub.setStyleSheet(style_subtitle(13))

        vl.addStretch()
        vl.addWidget(icon_lbl)
        vl.addWidget(title)
        vl.addWidget(sub)
        vl.addStretch()
        return w

    # ─── Public API ────────────────────────────────────────────────────────

    def set_packages(self, packages: list[Package]):
        self._packages = packages
        self._rebuild_cards()

    def set_loading(self, loading: bool):
        self._check_btn.setEnabled(not loading)
        if loading:
            self._count_label.setText(self.tr("Buscando actualizaciones..."))
            self._count_label.setObjectName("StatusInfo")
        else:
            self._update_count_label()

    def set_busy(self, busy: bool):
        self._update_all_btn.setEnabled(not busy and bool(self._packages))
        self._check_btn.setEnabled(not busy)
        for card in self._cards:
            card.set_busy(busy)

    def set_privileged_operation_running(self, running: bool):
        """Disable/enable buttons that require privileged operations."""
        self._update_all_btn.setEnabled(not running and bool(self._packages))
        self._update_selected_btn.setEnabled(not running and any(p.selected for p in self._packages))
        for card in self._cards:
            card.set_busy(running)

    # ─── Internal ─────────────────────────────────────────────────────────

    def _rebuild_cards(self):
        # Clear old cards
        for card in self._cards:
            self._content_layout.removeWidget(card)
            card.deleteLater()
        self._cards.clear()

        if not self._packages:
            self._scroll.hide()
            self._empty_widget.show()
            self._update_all_btn.setEnabled(False)
            self._update_selected_btn.setEnabled(False)
            self._select_all.setEnabled(False)
        else:
            self._empty_widget.hide()
            self._scroll.show()
            self._update_all_btn.setEnabled(True)
            self._select_all.setEnabled(True)

            for pkg in self._packages:
                card = PackageCard(pkg, show_checkbox=True)
                card.install_requested.connect(
                    lambda name: self.update_selected_requested.emit([name])
                )
                card.selection_changed.connect(self._on_selection_changed)
                card.info_requested.connect(self.info_requested)
                self._cards.append(card)
                self._content_layout.insertWidget(
                    self._content_layout.count() - 1, card
                )

        self._update_count_label()

    def _update_count_label(self):
        n = len(self._packages)
        if n == 0:
            self._count_label.setText("")
        elif n == 1:
            self._count_label.setText(self.tr("1 actualización disponible"))
        else:
            self._count_label.setText(self.tr("%1 actualizaciones disponibles").replace("%1", str(n)))

    def _on_select_all(self, state):
        checked = state == Qt.CheckState.Checked.value
        for pkg in self._packages:
            pkg.selected = checked
        for card in self._cards:
            card._checkbox.blockSignals(True)
            card._checkbox.setChecked(checked)
            card._checkbox.blockSignals(False)
        self._refresh_selected_btn()

    def _on_selection_changed(self, _name: str, _checked: bool):
        self._refresh_selected_btn()

    def _refresh_selected_btn(self):
        n = sum(1 for p in self._packages if p.selected)
        self._update_selected_btn.setEnabled(n > 0)
        if n > 0:
            self._update_selected_btn.setText(self.tr("Actualizar (%1)").replace("%1", str(n)))
        else:
            self._update_selected_btn.setText(self.tr("Actualizar seleccionados"))

    def _on_update_selected(self):
        selected = [p.name for p in self._packages if p.selected]
        if selected:
            self.update_selected_requested.emit(selected)
