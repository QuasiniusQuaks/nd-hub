"""Einrichtungswizard container: 7 Schritte, transaktionaler Abschluss.

Issue #67: split from monolithic setup_wizard_dialog.py into step mixins.
"""
from __future__ import annotations

from typing import Any

from PySide6 import QtCore, QtWidgets

from apple_theme import AppleTheme
from db_manager import Database
from ui.dialogs.setup_wizard.chrome import ChromeMixin
from ui.dialogs.setup_wizard.draft import DraftMixin
from ui.dialogs.setup_wizard.navigation import NavigationMixin
from ui.dialogs.setup_wizard.step_backend import BackendStepMixin
from ui.dialogs.setup_wizard.step_depots import DepotsStepMixin
from ui.dialogs.setup_wizard.step_depots_form import DepotsFormMixin
from ui.dialogs.setup_wizard.step_institution import InstitutionStepMixin
from ui.dialogs.setup_wizard.step_praeparate import PraeparateStepMixin
from ui.dialogs.setup_wizard.step_review import ReviewStepMixin


def _apply_mixins(*mixins: type):
    """Attach mixin methods without multi-inheritance.

    Multi-inheritance with ``QtWidgets.QDialog`` breaks under the PySide6 test
    stub (MagicMock metaclass conflict). Real PySide would be fine; attach keeps
    both environments working while still splitting code by step module.
    """

    def decorator(cls: type) -> type:
        for mixin in mixins:
            for name, value in mixin.__dict__.items():
                if name.startswith("__"):
                    continue
                setattr(cls, name, value)
        return cls

    return decorator


@_apply_mixins(
    BackendStepMixin,
    InstitutionStepMixin,
    PraeparateStepMixin,
    DepotsStepMixin,
    DepotsFormMixin,
    ReviewStepMixin,
    DraftMixin,
    NavigationMixin,
    ChromeMixin,
)
class SetupWizardDialog(QtWidgets.QDialog):
    """Fuenf-Schritt-Assistent; Schritt 3/4 teilen eine Depot-Oberflaeche (innerer Stack).

    Tatsaechlich 7 logische Steps: Backend, Institution, Praeparate,
    Depot-Stamm, Depot-Kontakte, Depot-Zuordnungen, Review.

    Implementation is split across step modules (Issue #67).
    """

    _STEP_COUNT = 7

    def __init__(self, parent: QtWidgets.QWidget | None, db: Database) -> None:
        super().__init__(parent)
        self.db = db
        self._backdrop: QtWidgets.QWidget | None = None
        self._last_geocode_query: str = ""
        self._last_geocode_result: tuple[float | None, float | None] = (None, None)
        self._prae_rows: list[dict[str, str]] = []
        self.setWindowTitle("Einrichtungswizard")
        self.setWindowModality(QtCore.Qt.WindowModal)
        self.setModal(True)
        self.setProperty("embedded_fill_ratio", 0.92)
        self.setProperty("embedded_aspect_ratio", "16:9")
        self.setMinimumSize(980, 720)
        self._resize_for_screen_ratio()
        self._step_index = 0
        self._depot_rows: list[dict[str, Any]] = []

        c = AppleTheme.current_colors()
        self._apply_base_styles(c)

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 16)
        root.setSpacing(12)

        self._title = QtWidgets.QLabel("Einrichtungswizard")
        self._title.setStyleSheet(
            f"font-size: 18px; font-weight: 600; color: {c.get('label', '#111')};"
        )
        root.addWidget(self._title)

        self._subtitle = QtWidgets.QLabel(
            "Richten Sie Institution, Präparate, Notfalldepots, Kontakt (E-Mail/Telefon) und Präparat-Zuordnungen ein. "
            "Zwischenstände werden als Entwurf gespeichert; mit „Abschließen“ werden alle Daten in einem Schritt übernommen."
        )
        self._subtitle.setWordWrap(True)
        self._subtitle.setStyleSheet(
            f"font-size: 13px; color: {c.get('secondary_label', '#666')};"
        )
        root.addWidget(self._subtitle)

        self._step_label = QtWidgets.QLabel()
        self._step_label.setStyleSheet(
            f"font-size: 12px; font-weight: 600; color: {c.get('secondary_label', '#666')};"
        )
        root.addWidget(self._step_label)

        self._stack = QtWidgets.QStackedWidget()
        root.addWidget(self._stack, 1)

        self._page_inst = self._build_institution_page()
        self._page_prae = self._build_praeparate_page()
        self._page_depots = self._build_depots_page()
        self._page_review = self._build_review_page()
        self._page_backend = self._build_backend_page()
        self._stack.addWidget(self._page_backend)
        self._stack.addWidget(self._page_inst)
        self._stack.addWidget(self._page_prae)
        self._stack.addWidget(self._page_depots)
        self._stack.addWidget(self._page_review)

        self._error = QtWidgets.QLabel("")
        self._error.setWordWrap(True)
        self._error.setStyleSheet(f"color: {c.get('red', '#b91c1c')}; font-size: 12px;")
        self._error.hide()
        root.addWidget(self._error)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch()
        self._btn_back = QtWidgets.QPushButton("Zurück")
        self._btn_back.setObjectName("btn_secondary")
        self._btn_back.clicked.connect(self._on_back)
        btn_row.addWidget(self._btn_back)

        self._btn_later = QtWidgets.QPushButton("Später")
        self._btn_later.setObjectName("btn_secondary")
        self._btn_later.clicked.connect(self._on_later)
        btn_row.addWidget(self._btn_later)

        self._btn_next = QtWidgets.QPushButton("Weiter")
        self._btn_next.setObjectName("btn_save")
        self._btn_next.clicked.connect(self._on_next)
        btn_row.addWidget(self._btn_next)

        root.addLayout(btn_row)
        self._load_draft_into_ui()

    def _apply_base_styles(self, colors: dict[str, str]) -> None:
        bg = colors.get("bg_secondary", colors.get("bg_primary", "#f5f5f7"))
        lbl = colors.get("label", "#111")
        inp_bg = colors.get("bg_secondary", "#ffffff")
        sep = colors.get("separator", "#e1e8ed")
        self.setStyleSheet(
            f"QDialog {{ background-color: {bg}; }}"
            f"QDialog QWidget {{ background: transparent; color: {lbl}; }}"
            f"QDialog QLabel {{ background: transparent; color: {lbl}; }}"
            "QDialog QLineEdit, QDialog QPlainTextEdit, QDialog QTableWidget, QDialog QComboBox, QDialog QSpinBox {"
            f"background: {inp_bg};"
            f"color: {lbl};"
            f"border: 2px solid {sep};"
            "min-height: 40px;"
            "padding-top: 4px;"
            "padding-bottom: 4px;"
            "}"
            "QDialog QPushButton {"
            "min-height: 40px;"
            "}"
        )

    def _sync_main_stack_to_step(self) -> None:
        if self._step_index <= 2:
            self._stack.setCurrentIndex(self._step_index)
        elif self._step_index <= 5:
            self._stack.setCurrentIndex(3)
            self._depot_inner_stack.setCurrentIndex(self._step_index - 3)
            self._update_depot_step_hint()
        else:
            self._stack.setCurrentIndex(4)

    def _refresh_step_ui(self) -> None:
        self._step_label.setText(f"Schritt {self._step_index + 1} von {self._STEP_COUNT}")
        self._btn_back.setEnabled(self._step_index > 0)
        if self._step_index < self._STEP_COUNT - 1:
            self._btn_next.setText("Weiter")
        else:
            self._btn_next.setText("Abschließen")
        self._error.hide()
        self._sync_main_stack_to_step()

    def _show_error(self, msg: str) -> None:
        self._error.setText(msg)
        self._error.show()


