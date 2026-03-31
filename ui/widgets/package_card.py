"""
Wakka — Package Card Widget
A rich card UI for displaying a package with install/remove actions.
"""
from __future__ import annotations

from PyQt6.QtCore import pyqtSignal, Qt, QSize
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QCheckBox, QSizePolicy,
)
from ui.styles.icons import get_icon
from core.package_manager import Package, PkgSource, PkgStatus


class PackageCard(QWidget):
    """
    A single row/card representing a package.
    Emits install/remove/select signals.
    """
    install_requested = pyqtSignal(str)    # package name
    remove_requested = pyqtSignal(str)
    info_requested = pyqtSignal(str)
    selection_changed = pyqtSignal(str, bool)  # name, selected

    def __init__(self, package: Package, show_checkbox: bool = True, parent=None):
        super().__init__(parent)
        self.setObjectName("PackageCard")
        self._pkg = package
        self._show_checkbox = show_checkbox
        self._setup_ui()
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    @property
    def package(self) -> Package:
        return self._pkg

    def update_package(self, pkg: Package):
        self._pkg = pkg
        self._refresh()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(12)

        # Checkbox
        if self._show_checkbox:
            self._checkbox = QCheckBox()
            self._checkbox.setChecked(self._pkg.selected)
            self._checkbox.stateChanged.connect(self._on_check)
            layout.addWidget(self._checkbox)

        # Info column
        info_col = QVBoxLayout()
        info_col.setSpacing(3)

        # Name + badges row
        name_row = QHBoxLayout()
        name_row.setSpacing(6)

        self._name_label = QLabel(self._pkg.name)
        self._name_label.setObjectName("PkgName")

        name_row.addWidget(self._name_label)
        name_row.addWidget(self._make_source_badge())

        if self._pkg.status == PkgStatus.INSTALLED:
            installed_badge = QLabel(self.tr("instalado"))
            installed_badge.setObjectName("BadgeInstalled")
            name_row.addWidget(installed_badge)

        name_row.addStretch()
        info_col.addLayout(name_row)

        # Version / update arrow
        if self._pkg.status == PkgStatus.UPGRADABLE:
            ver_text = f"{self._pkg.installed_version}  →  {self._pkg.new_version}"
        else:
            ver_text = self._pkg.version

        self._version_label = QLabel(ver_text)
        self._version_label.setObjectName("PkgVersion")
        info_col.addWidget(self._version_label)

        # Description
        if self._pkg.description:
            self._desc_label = QLabel(self._pkg.description)
            self._desc_label.setObjectName("PkgDesc")
            self._desc_label.setWordWrap(True)
            self._desc_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            info_col.addWidget(self._desc_label)

        layout.addLayout(info_col)
        layout.addStretch()

        # Action buttons
        btn_col = QVBoxLayout()
        btn_col.setSpacing(4)
        btn_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        if self._pkg.status == PkgStatus.NOT_INSTALLED:
            self._action_btn = QPushButton(self.tr("Instalar"))
            self._action_btn.setObjectName("PrimaryButton")
            self._action_btn.clicked.connect(lambda: self.install_requested.emit(self._pkg.name))
        elif self._pkg.status == PkgStatus.UPGRADABLE:
            self._action_btn = QPushButton(self.tr("Actualizar"))
            self._action_btn.setObjectName("SuccessButton")
            self._action_btn.clicked.connect(lambda: self.install_requested.emit(self._pkg.name))
        else:
            self._action_btn = QPushButton(self.tr("Desinstalar"))
            self._action_btn.setObjectName("DangerButton")
            self._action_btn.clicked.connect(lambda: self.remove_requested.emit(self._pkg.name))

        self._action_btn.setFixedHeight(32)
        self._action_btn.setMinimumWidth(110)

        self._info_btn = QPushButton()
        self._info_btn.setIcon(get_icon("info", "#8892a4", 14))
        self._info_btn.setFixedSize(32, 32)
        self._info_btn.setToolTip(self.tr("Ver información"))
        self._info_btn.clicked.connect(lambda: self.info_requested.emit(self._pkg.name))

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        btn_row.addWidget(self._action_btn)
        btn_row.addWidget(self._info_btn)
        btn_col.addLayout(btn_row)
        layout.addLayout(btn_col)

    def _make_source_badge(self) -> QLabel:
        if self._pkg.source == PkgSource.AUR:
            badge = QLabel("AUR")
            badge.setObjectName("BadgeAUR")
        else:
            badge = QLabel(self.tr("Oficial"))
            badge.setObjectName("BadgeOfficial")
        return badge

    def _on_check(self, state):
        checked = state == Qt.CheckState.Checked.value
        self._pkg.selected = checked
        self.selection_changed.emit(self._pkg.name, checked)

    def _refresh(self):
        self._name_label.setText(self._pkg.name)
        self._update_action_button_text()

    def _update_action_button_text(self):
        if self._pkg.status == PkgStatus.NOT_INSTALLED:
            self._action_btn.setText(self.tr("Instalar"))
        elif self._pkg.status == PkgStatus.UPGRADABLE:
            self._action_btn.setText(self.tr("Actualizar"))
        else:
            self._action_btn.setText(self.tr("Desinstalar"))

    def set_busy(self, busy: bool):
        self._action_btn.setEnabled(not busy)
        if busy:
            self._action_btn.setText(self.tr("..."))
        else:
            self._update_action_button_text()
