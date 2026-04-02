"""
Wakka — Installed Packages Page
Browse and search all installed packages, with remove action.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QScrollArea, QFrame, QPushButton, QCheckBox,
)
from ..widgets.package_card import PackageCard
from ..styles.icons import get_icon
from ..styles.theme import style_transparent_bg, style_loading
from modules.package_manager import Package, PkgStatus


class InstalledPage(QWidget):
    remove_requested = pyqtSignal(str)
    remove_multiple_requested = pyqtSignal(list)
    refresh_requested = pyqtSignal()
    info_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_packages: list[Package] = []
        self._cards: list[PackageCard] = []
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._apply_filter)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Toolbar ─────────────────────────────────────────────────────────
        toolbar = QWidget()
        toolbar.setFixedHeight(60)
        toolbar.setStyleSheet(style_transparent_bg())
        tb = QHBoxLayout(toolbar)
        tb.setContentsMargins(20, 0, 20, 0)
        tb.setSpacing(10)

        self._search = QLineEdit()
        self._search.setObjectName("SearchBar")
        self._search.setPlaceholderText(self.tr("Buscar paquetes instalados..."))
        self._search.setFixedWidth(350)
        self._search.textChanged.connect(self._on_search)

        self._count_label = QLabel("")
        self._count_label.setObjectName("StatusInfo")

        refresh_btn = QPushButton()
        refresh_btn.setIcon(get_icon("refresh", "#8892a4"))
        refresh_btn.setToolTip(self.tr("Refrescar lista"))
        refresh_btn.setFixedSize(36, 36)
        refresh_btn.clicked.connect(self.refresh_requested)

        self._select_all = QCheckBox(self.tr("Seleccionar visibles"))
        self._select_all.stateChanged.connect(self._on_select_all_changed)
        self._select_all.setToolTip(self.tr("Seleccionar todos los paquetes visibles"))

        self._remove_selected_btn = QPushButton(self.tr("Desinstalar"))
        self._remove_selected_btn.setObjectName("DangerButton")
        self._remove_selected_btn.setIcon(get_icon("trash", "#ffffff", 14))
        self._remove_selected_btn.setEnabled(False)
        self._remove_selected_btn.clicked.connect(self._on_remove_selected)

        tb.addWidget(self._search)
        tb.addWidget(self._count_label)
        tb.addStretch()
        tb.addWidget(self._select_all)
        tb.addSpacing(10)
        tb.addWidget(self._remove_selected_btn)
        tb.addSpacing(10)
        tb.addWidget(refresh_btn)

        # ── Scroll area ──────────────────────────────────────────────────────
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

        # Loading label
        self._loading_label = QLabel(self.tr("Cargando paquetes instalados..."))
        self._loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._loading_label.setStyleSheet(style_loading())

        layout.addWidget(toolbar)
        layout.addWidget(self._loading_label)
        layout.addWidget(self._scroll)
        self._scroll.hide()

    def set_packages(self, packages: list[Package]):
        self._all_packages = packages
        self._apply_filter()
        self._loading_label.hide()
        self._scroll.show()

    def set_loading(self, loading: bool):
        if loading:
            self._loading_label.setText(self.tr("Cargando paquetes instalados..."))
            self._loading_label.show()
            self._scroll.hide()
        else:
            self._loading_label.hide()

    def set_busy(self, busy: bool):
        for card in self._cards:
            card.set_busy(busy)

    def _on_search(self, text: str):
        self._search_timer.start(250)

    def _apply_filter(self):
        query = self._search.text().strip().lower()
        filtered = [
            p for p in self._all_packages
            if not query or query in p.name.lower() or query in p.description.lower()
        ]
        self._select_all.setEnabled(bool(query) and bool(filtered))
        if not query:
            self._select_all.blockSignals(True)
            self._select_all.setChecked(False)
            self._select_all.blockSignals(False)
        self._rebuild_cards(filtered)

    def _rebuild_cards(self, packages: list[Package]):
        for card in self._cards:
            self._content_layout.removeWidget(card)
            card.deleteLater()
        self._cards.clear()

        # Reset selection state
        self._select_all.blockSignals(True)
        self._select_all.setChecked(False)
        self._select_all.blockSignals(False)

        for pkg in packages:
            pkg.status = PkgStatus.INSTALLED  # Ensure status
            card = PackageCard(pkg, show_checkbox=True)
            card.remove_requested.connect(self.remove_requested)
            card.info_requested.connect(self.info_requested)
            card.selection_changed.connect(self._on_selection_changed)
            self._cards.append(card)
            self._content_layout.insertWidget(
                self._content_layout.count() - 1, card
            )

        self._update_count(len(packages))
        self._update_selection_count()

    def _update_count(self, shown: int):
        total = len(self._all_packages)
        if total == shown:
            self._count_label.setText(self.tr("%1 paquetes instalados").replace("%1", str(total)))
        else:
            self._count_label.setText(
                self.tr("%1 de %2 paquetes").replace("%1", str(shown)).replace("%2", str(total))
            )

    def clear_search(self):
        """Reset the search field and selection state."""
        self._search.blockSignals(True)
        self._search.clear()
        self._search.blockSignals(False)

        self._select_all.blockSignals(True)
        self._select_all.setChecked(False)
        self._select_all.blockSignals(False)

        # We don't call _apply_filter here because we usually
        # call clear_search right before set_packages which does it.

    def _on_selection_changed(self):
        self._update_selection_count()

    def _on_select_all_changed(self, state: int):
        checked = state == Qt.CheckState.Checked.value
        for card in self._cards:
            card._checkbox.setChecked(checked) # Direct access for speed or use a method
        self._update_selection_count()

    def _update_selection_count(self):
        selected_names = [c.package.name for c in self._cards if c._checkbox.isChecked()]
        count = len(selected_names)
        self._remove_selected_btn.setEnabled(count > 0)
        if count > 0:
            self._remove_selected_btn.setText(self.tr("Desinstalar (%1)").replace("%1", str(count)))
        else:
            self._remove_selected_btn.setText(self.tr("Desinstalar"))

    def _on_remove_selected(self):
        selected_names = [c.package.name for c in self._cards if c._checkbox.isChecked()]
        if selected_names:
            self.remove_multiple_requested.emit(selected_names)
