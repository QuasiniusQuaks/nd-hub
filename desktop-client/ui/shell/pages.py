"""MainWindow shell helpers (Issue #93)."""
from __future__ import annotations

import logging

from PySide6 import QtCore, QtWidgets

from ui.shell.constants import PageIndex

logger = logging.getLogger("ND-Hub")

def _init_pages(self) -> None:
    """Erstellt Stack-Platzhalter und lädt Seiten bei Bedarf."""
    self._page_instances = {}
    self._settings_backup_checked = False
    self.page_dashboard = None
    self.page_grundeinstellungen = None

    for _ in range(len(PageIndex)):
        self.stack.addWidget(QtWidgets.QWidget())

    self._ensure_page_loaded(PageIndex.DASHBOARD)
    self.stack.setCurrentIndex(PageIndex.DASHBOARD)
    self.set_active_button(PageIndex.DASHBOARD)


def _create_page_instance(self, idx: int):
    """Erzeugt eine Seite lazily beim ersten Aufruf."""
    if idx == PageIndex.DASHBOARD:
        from apple_dashboard import AppleDashboard
        page = AppleDashboard(self.db, self.verfallmanager)
        page.requestedPage.connect(self.switch_to_page)
        self.page_dashboard = page
        return page
    if idx == PageIndex.MOVEMENTS:
        from ui.pages.page_bewegungen import BewegungenPage
        return BewegungenPage(self.db, self.attachment_folder, security=self.security)
    if idx == PageIndex.HISTORIE:
        from ui.pages.page_historie import BewegungshistoriePage
        return BewegungshistoriePage(self.db)
    if idx == PageIndex.AUSWERTUNGEN:
        from ui.pages.analytics.analytics_page import AnalyticsPage
        return AnalyticsPage(self.db)
    if idx == PageIndex.IMPORT:
        from ui.pages.page_import import ImportPage
        return ImportPage(self.db)
    if idx == PageIndex.EMAIL:
        from ui.pages.page_email import EmailPage
        return EmailPage(self.db)
    if idx == PageIndex.GRUNDEINSTELLUNGEN:
        from ui.pages.page_grundeinstellungen import GrundeinstellungenPage
        page = GrundeinstellungenPage(self.db, security=self.security)
        self.page_grundeinstellungen = page
        return page
    raise ValueError(f"Unbekannter PageIndex: {idx}")


def _ensure_page_loaded(self, idx: int):
    """Stellt sicher, dass die gewünschte Seite im Stack geladen ist."""
    if idx in self._page_instances:
        return self._page_instances[idx]
    page = self._create_page_instance(idx)
    placeholder = self.stack.widget(idx)
    self.stack.insertWidget(idx, page)
    if placeholder is not None:
        self.stack.removeWidget(placeholder)
        placeholder.deleteLater()
    self._page_instances[idx] = page
    self._install_page_enhancements(page)
    return page


def switch_to_page(self, idx: int) -> None:
    """Zentrale Methode zum Seitenwechsel mit Zugriffskontrolle"""
    current_page = self.stack.currentWidget() if hasattr(self, "stack") else None
    if current_page is not None and self.stack.currentIndex() != idx:
        if not self._confirm_discard_unsaved_changes(current_page):
            return

    # Zugriffskontrolle für geschützte Seiten
    if idx == PageIndex.GRUNDEINSTELLUNGEN:
        if not self.security.is_admin():
            QtWidgets.QMessageBox.warning(
                self,
                "Keine Berechtigung",
                f"Nur Administratoren haben Zugriff auf die Grundeinstellungen.\n\n"
                f"Ihre Rolle: {self.security.get_current_role()}"
            )
            return

    busy_op_id = -1
    try:
        page_name = PageIndex(idx).name.replace("_", " ").title() if idx in PageIndex._value2member_map_ else "Seite"
        heavy_pages = {PageIndex.AUSWERTUNGEN, PageIndex.HISTORIE, PageIndex.EMAIL}
        busy_delay_ms = 0 if idx in heavy_pages else 120
        busy_op_id = self._begin_busy_operation(f"Lade {page_name} ...", delay_ms=busy_delay_ms)
        # Navigation durchführen
        page = self._ensure_page_loaded(idx)
        self.stack.setCurrentWidget(page)
        self.set_active_button(idx)
        self._apply_write_mode_to_page(page)

        if idx == PageIndex.GRUNDEINSTELLUNGEN and not self._settings_backup_checked:
            try:
                if not self.db.is_read_only_mode():
                    self.page_grundeinstellungen.check_auto_backup()
            finally:
                self._settings_backup_checked = True
    except Exception as e:
        logger.error("Seitenwechsel fehlgeschlagen (idx=%s): %s", idx, e, exc_info=True)
        QtWidgets.QMessageBox.critical(
            self,
            "Seite konnte nicht geladen werden",
            "Die gewünschte Seite konnte nicht geöffnet werden.\n\n"
            f"Fehler: {e}\n\n"
            "Bitte prüfen Sie die Logdatei für Details."
        )
        self._ensure_page_loaded(PageIndex.DASHBOARD)
        self.stack.setCurrentIndex(PageIndex.DASHBOARD)
        self.set_active_button(PageIndex.DASHBOARD)
    finally:
        self._end_busy_operation(busy_op_id)

    # Log bei Navigation (optional)
    # logger.debug(f"Seite gewechselt: Index {idx}")


def _install_page_enhancements(self, page: QtWidgets.QWidget) -> None:
    """Registriert Dirty-Tracking/Hooks einmalig pro Seite."""
    if page is None or getattr(page, "_ndh_page_enhanced", False):
        return
    page._ndh_page_enhanced = True
    page._has_unsaved_changes = False

    def _mark_dirty(*_args, p=page):
        self._mark_page_dirty(p)

    for widget in page.findChildren(QtWidgets.QWidget):
        if isinstance(widget, QtWidgets.QLineEdit):
            widget.textChanged.connect(_mark_dirty)
        elif isinstance(widget, (QtWidgets.QTextEdit, QtWidgets.QPlainTextEdit)):
            widget.textChanged.connect(_mark_dirty)
        elif isinstance(widget, QtWidgets.QComboBox):
            widget.currentIndexChanged.connect(_mark_dirty)
        elif isinstance(widget, (QtWidgets.QSpinBox, QtWidgets.QDoubleSpinBox)):
            widget.valueChanged.connect(_mark_dirty)
        elif isinstance(widget, (QtWidgets.QDateEdit, QtWidgets.QDateTimeEdit, QtWidgets.QTimeEdit)):
            widget.dateTimeChanged.connect(_mark_dirty)
        elif isinstance(widget, (QtWidgets.QCheckBox, QtWidgets.QRadioButton)):
            widget.toggled.connect(_mark_dirty)

    for btn in page.findChildren(QtWidgets.QPushButton):
        obj = (btn.objectName() or "").lower()
        text = (btn.text() or "").strip().lower()
        if obj in {"btn_save", "btn_add", "btn_delete"} or any(
            token in text for token in ("speichern", "anlegen", "hinzufügen", "erstellen", "übernehmen")
        ):
            btn.clicked.connect(lambda _=False, p=page: QtCore.QTimer.singleShot(250, lambda: self._clear_page_dirty(p)))


def _mark_page_dirty(self, page: QtWidgets.QWidget) -> None:
    if page is not None:
        page._has_unsaved_changes = True


def _clear_page_dirty(self, page: QtWidgets.QWidget) -> None:
    if page is not None:
        page._has_unsaved_changes = False


def _page_has_unsaved_changes(self, page: QtWidgets.QWidget) -> bool:
    return bool(getattr(page, "_has_unsaved_changes", False))


def _confirm_discard_unsaved_changes(self, page: QtWidgets.QWidget) -> bool:
    """Fragt vor Seitenwechsel/Beenden bei ungespeicherten Änderungen."""
    if page is None or not self._page_has_unsaved_changes(page):
        return True
    reply = QtWidgets.QMessageBox.question(
        self,
        "Ungespeicherte Änderungen",
        "Es gibt ungespeicherte Änderungen auf der aktuellen Seite.\n"
        "Möchten Sie diese verwerfen und fortfahren?",
        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        QtWidgets.QMessageBox.No,
    )
    if reply == QtWidgets.QMessageBox.Yes:
        self._clear_page_dirty(page)
        self.show_toast("Ungespeicherte Änderungen verworfen.", "warning", 2200)
        return True
    return False

