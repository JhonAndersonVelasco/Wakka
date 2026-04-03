"""
Wakka — Browse / Search Page
Search official repos and AUR, filter by source.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QScrollArea, QFrame, QPushButton, QComboBox
)
from ..widgets.package_card import PackageCard
from ..styles.icons import get_icon
from ..styles.theme import style_transparent_bg, style_loading, style_icon_text, style_subtitle, style_filter_border
from modules.package_manager import Package, PkgSource


class BrowsePage(QWidget):
    """
    Browse and search packages from official repositories and AUR.

    Features:
        - Real-time search with debouncing
        - Filter by source (all, official, AUR)
        - Sort by votes, popularity, name, or modified date
        - Pagination support
        - Package card display with install/remove actions

    Signals:
        install_requested: Emitted when user requests package installation
        remove_requested: Emitted when user requests package removal
        search_requested: Emitted when search query is submitted
        info_requested: Emitted when package details are requested
    """

    install_requested = pyqtSignal(str)
    remove_requested  = pyqtSignal(str)
    search_requested  = pyqtSignal(str, str, str, int)
    info_requested    = pyqtSignal(str)

    _FILTERS = ["all", "official", "aur"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._packages: list[Package] = []
        self._cards: list[PackageCard] = []
        self._active_filter = "all"
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._do_search)
        self._search_query = ""
        self._current_page = 1
        self._page_size = 50
        self._sort = "votes"
        self._sort_direction = "desc"
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Search row ───────────────────────────────────────────────────────
        search_row = QWidget()
        search_row.setFixedHeight(60)
        sr = QHBoxLayout(search_row)
        sr.setContentsMargins(20, 0, 20, 0)
        sr.setSpacing(10)

        self._search = QLineEdit()
        self._search.setObjectName("SearchBar")
        # ✅ FIXED: Using tr() for translatable string
        self._search.setPlaceholderText(
            self.tr("Buscar paquetes en repos oficiales y AUR...")
        )
        self._search.textChanged.connect(lambda: self._search_timer.start(400))
        self._search.returnPressed.connect(self._do_search)

        self._search_btn = QPushButton()
        self._search_btn.setIcon(get_icon("browse", "#8892a4"))
        self._search_btn.setFixedSize(36, 36)
        self._search_btn.clicked.connect(self._do_search)

        sr.addWidget(self._search)
        sr.addWidget(self._search_btn)

        # ── Filter tabs ──────────────────────────────────────────────────────
        filter_row = QWidget()
        filter_row.setFixedHeight(44)
        filter_row.setStyleSheet(style_filter_border())
        fr = QHBoxLayout(filter_row)
        fr.setContentsMargins(20, 0, 20, 0)
        fr.setSpacing(0)

        labels = {
            "all":      self.tr("Todos"),
            "official": self.tr("Oficiales"),
            "aur":      self.tr("AUR"),
        }
        self._filter_btns: dict[str, QPushButton] = {}
        for key, label in labels.items():
            btn = QPushButton(label)
            btn.setObjectName("FilterTab")
            btn.setCheckable(False)
            btn.setProperty("active", key == self._active_filter)
            btn.clicked.connect(lambda _, k=key: self._set_filter(k))
            self._filter_btns[key] = btn
            fr.addWidget(btn)
        fr.addStretch()

        self._count_label = QLabel("")
        self._count_label.setObjectName("StatusInfo")
        fr.addWidget(self._count_label)
        fr.addSpacing(16)

        # ── Sort criteria selector ────────────────────────────────────────
        sort_criteria_selector = QComboBox()
        sort_criteria_selector.addItem(self.tr("Votos"), "votes")
        sort_criteria_selector.addItem(self.tr("Popularidad"), "popularity")
        sort_criteria_selector.addItem(self.tr("Nombre"), "name")
        sort_criteria_selector.addItem(self.tr("Modificado"), "modified")
        sort_criteria_selector.setCurrentIndex(0)  # Set default to "Votos"
        sort_criteria_selector.currentIndexChanged.connect(
            lambda index: self.set_sort_criteria(sort_criteria_selector.itemData(index))
        )
        sort_criteria_selector.setToolTip(self.tr("Ordenar paquetes por el criterio seleccionado."))
        fr.addWidget(sort_criteria_selector)

        sort_direction_selector = QComboBox()
        sort_direction_selector.addItem(self.tr("Descendente"), "desc")
        sort_direction_selector.addItem(self.tr("Ascendente"), "asc")
        sort_direction_selector.setCurrentIndex(0)  # Default to descending
        sort_direction_selector.currentIndexChanged.connect(
            lambda index: self.set_sort_direction(sort_direction_selector.itemData(index))
        )
        sort_direction_selector.setToolTip(self.tr("Selecciona la dirección de ordenación de los paquetes."))
        fr.addWidget(sort_direction_selector)

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

        # ── States ─────────────────────────────────────────────────────────
        self._hint_widget = self._make_hint()
        self._loading_label = QLabel(self.tr("Buscando..."))
        self._loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._loading_label.setStyleSheet(style_loading())
        self._loading_label.hide()

        layout.addWidget(search_row)
        layout.addWidget(filter_row)
        layout.addWidget(self._hint_widget)
        layout.addWidget(self._loading_label)
        layout.addWidget(self._scroll)
        self._scroll.hide()

        self._pagination_row = QWidget()
        self._pagination_row.setFixedHeight(48)
        pr_layout = QHBoxLayout(self._pagination_row)
        pr_layout.setContentsMargins(20, 0, 20, 0)
        pr_layout.setSpacing(8)

        self._prev_page_btn = QPushButton(self.tr("Anterior"))
        self._prev_page_btn.setFixedSize(100, 32)
        self._prev_page_btn.clicked.connect(self._previous_page)
        self._next_page_btn = QPushButton(self.tr("Siguiente"))
        self._next_page_btn.setFixedSize(100, 32)
        self._next_page_btn.clicked.connect(self._next_page)
        self._page_label = QLabel("")
        self._page_label.setObjectName("StatusInfo")

        pr_layout.addWidget(self._prev_page_btn)
        pr_layout.addWidget(self._page_label)
        pr_layout.addWidget(self._next_page_btn)
        pr_layout.addStretch()
        self._pagination_row.hide()

        layout.addWidget(self._pagination_row)

    def _make_hint(self) -> QWidget:
        w = QWidget()
        vl = QVBoxLayout(w)
        vl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl = QLabel("🔍")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(style_icon_text(48))
        # ✅ FIXED: Using tr() for translatable string
        sub = QLabel(self.tr("Escribe el nombre de un paquete para buscar en los repositorios oficiales y AUR"))
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setWordWrap(True)
        sub.setStyleSheet(style_subtitle(13))
        vl.addWidget(lbl)
        vl.addWidget(sub)
        return w

    # ─── Public API ────────────────────────────────────────────────────────

    def set_results(self, packages: list[Package]):
        """
        Set search results and rebuild package cards.

        Args:
            packages: List of Package objects from search results
        """
        self._packages = packages
        self._current_page = 1
        self._rebuild_cards()
        self._loading_label.hide()

    def set_searching(self, searching: bool):
        """
        Toggle searching state UI.

        Args:
            searching: True if search is in progress
        """
        if searching:
            self._loading_label.show()
            self._hint_widget.hide()
            self._scroll.hide()
        else:
            self._loading_label.hide()

    def set_busy(self, busy: bool):
        """
        Set busy state for all package cards.

        Args:
            busy: True if operations are in progress
        """
        for card in self._cards:
            card.set_busy(busy)

    def set_privileged_operation_running(self, running: bool):
        """Disable/enable buttons that require privileged operations."""
        for card in self._cards:
            card.set_busy(running)

    def focus_search(self):
        """Set focus to search input field."""
        self._search.setFocus()

    # ─── Internal ─────────────────────────────────────────────────────────

    def set_sort_criteria(self, criteria: str):
        """
        Set sort criteria and trigger search if query exists.

        Args:
            criteria: Sort field ('votes', 'popularity', 'name', 'modified')
        """
        self._sort = criteria or "votes"
        self._current_page = 1
        if self._search_query:
            self.search_requested.emit(
                self._search_query,
                self._sort,
                self._sort_direction,
                self._current_page,
            )
        else:
            self._rebuild_cards()

    def set_sort_direction(self, direction: str):
        """
        Set sort direction and trigger search if query exists.

        Args:
            direction: Sort direction ('asc' or 'desc')
        """
        self._sort_direction = direction or "desc"
        self._current_page = 1
        if self._search_query:
            self.search_requested.emit(
                self._search_query,
                self._sort,
                self._sort_direction,
                self._current_page,
            )
        else:
            self._rebuild_cards()

    def _do_search(self):
        """Execute search with current query and emit signal."""
        q = self._search.text().strip()
        if q:
            self._search_query = q
            self._current_page = 1
            self.search_requested.emit(q, self._sort, self._sort_direction, self._current_page)
            self.set_searching(True)

    def _set_filter(self, key: str):
        """
        Set active filter and rebuild cards.

        Args:
            key: Filter key ('all', 'official', 'aur')
        """
        self._active_filter = key
        for k, btn in self._filter_btns.items():
            btn.setProperty("active", k == key)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self._current_page = 1
        self._rebuild_cards()

    def _filtered(self) -> list[Package]:
        """
        Filter packages based on active filter and status.

        Returns:
            List of filtered Package objects
        """
        from modules.package_manager import PkgStatus

        if self._active_filter == "official":
            filtered = [
                p for p in self._packages
                if p.source == PkgSource.OFFICIAL and p.status == PkgStatus.NOT_INSTALLED
            ]
        elif self._active_filter == "aur":
            filtered = [
                p for p in self._packages
                if p.source == PkgSource.AUR and p.status == PkgStatus.NOT_INSTALLED
            ]
        else:
            filtered = [p for p in self._packages if p.status == PkgStatus.NOT_INSTALLED]

        # Sorting is performed via backend using yay --sortby, but local fallback is done here.
        if self._sort == "name":
            filtered = sorted(
                filtered,
                key=lambda x: x.name.lower(),
                reverse=self._sort_direction == "desc",
            )
        return filtered

    def _rebuild_cards(self):
        """Rebuild package cards based on filtered results and pagination."""
        for card in self._cards:
            self._content_layout.removeWidget(card)
            card.deleteLater()
        self._cards.clear()

        filtered = self._filtered()
        if not filtered and not self._packages:
            self._hint_widget.show()
            self._scroll.hide()
            self._count_label.setText("")
            return

        self._hint_widget.hide()
        self._scroll.show()

        n = len(filtered)
        page_count = max(1, (n + self._page_size - 1) // self._page_size)
        if self._current_page > page_count:
            self._current_page = page_count

        start = (self._current_page - 1) * self._page_size
        end = min(start + self._page_size, n)
        for pkg in filtered[start:end]:
            card = PackageCard(pkg, show_checkbox=False)
            card.install_requested.connect(self.install_requested)
            card.remove_requested.connect(self.remove_requested)
            card.info_requested.connect(self.info_requested)
            self._cards.append(card)
            self._content_layout.insertWidget(
                self._content_layout.count() - 1, card
            )

        if n > self._page_size:
            # ✅ FIXED: Using tr() with proper placeholder replacement
            self._count_label.setText(
                self.tr("Mostrando %1-%2 de %3 resultados")
                .replace("%1", str(start + 1))
                .replace("%2", str(end))
                .replace("%3", str(n))
            )
        else:
            self._count_label.setText(
                self.tr("%1 resultado(s)").replace("%1", str(n))
            )

        self._page_label.setText(
            self.tr("Página %1 de %2").replace("%1", str(self._current_page)).replace("%2", str(page_count))
        )
        self._prev_page_btn.setEnabled(self._current_page > 1)
        self._next_page_btn.setEnabled(self._current_page < page_count)
        self._pagination_row.setVisible(page_count > 1)

    def _previous_page(self):
        """Navigate to previous page of results."""
        if self._current_page > 1:
            self._current_page -= 1
            self._rebuild_cards()

    def _next_page(self):
        """Navigate to next page of results."""
        total = len(self._filtered())
        page_count = max(1, (total + self._page_size - 1) // self._page_size)
        if self._current_page < page_count:
            self._current_page += 1
            self._rebuild_cards()