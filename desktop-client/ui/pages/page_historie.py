"""Bewegungshistorie - Tabellenansicht aller Bewegungen."""
import os

from apple_theme import AppleTheme
from db_manager import Database
from icon_manager import IconManager
from PySide6 import QtWidgets
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices

from ui.utils import NumericTableWidgetItem, configure_responsive_table, create_card_widget


class BewegungshistoriePage(QtWidgets.QWidget):
    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        page_scroll = QtWidgets.QScrollArea()
        page_scroll.setWidgetResizable(True)
        page_scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        layout.addWidget(page_scroll)

        content = QtWidgets.QWidget()
        page_scroll.setWidget(content)

        content_layout = QtWidgets.QVBoxLayout(content)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(20)

        title = QtWidgets.QLabel("Bewegungsverlauf & Dokumente")
        title.setProperty("class", "page-title")
        content_layout.addWidget(title)

        card = create_card_widget()
        card_layout = QtWidgets.QVBoxLayout(card)

        filter_layout = QtWidgets.QHBoxLayout()
        filter_layout.setSpacing(12)

        filter_layout.addWidget(QtWidgets.QLabel("Filter:"))

        self.cb_depot_filter = QtWidgets.QComboBox()
        self.cb_depot_filter.addItem("Alle Depots", None)
        for d in self.db.list_depots():
            self.cb_depot_filter.addItem(d[1], d[0])
        self.cb_depot_filter.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        filter_layout.addWidget(self.cb_depot_filter, 1)

        self.cb_typ_filter = QtWidgets.QComboBox()
        self.cb_typ_filter.addItems(["Alle", "Zugang", "Abgang", "Vernichtung"])
        self.cb_typ_filter.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        filter_layout.addWidget(self.cb_typ_filter, 1)

        self.btn_filter = QtWidgets.QPushButton(" Anwenden")
        self.btn_filter.setIcon(IconManager.get_icon("search"))
        filter_layout.addWidget(self.btn_filter)
        filter_layout.addStretch()

        card_layout.addLayout(filter_layout)

        search_layout = QtWidgets.QHBoxLayout()
        search_layout.setSpacing(12)
        search_layout.addWidget(QtWidgets.QLabel("Suche:"))
        self.e_search = QtWidgets.QLineEdit()
        self.e_search.setPlaceholderText("Volltextsuche (Depot, Präparat, Charge, ...)")
        self.e_search.setClearButtonEnabled(True)
        search_layout.addWidget(self.e_search)
        card_layout.addLayout(search_layout)

        self.table = QtWidgets.QTableWidget()
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setSortingEnabled(True)
        self.table.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        configure_responsive_table(self.table)
        card_layout.addWidget(self.table)

        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.setSpacing(12)
        self.btn_open_pdf = QtWidgets.QPushButton(" PDF öffnen")
        self.btn_open_pdf.setIcon(IconManager.get_icon("file_text"))
        self.btn_open_pdf.setEnabled(False)
        self.btn_open_folder = QtWidgets.QPushButton(" Ordner öffnen")
        self.btn_open_folder.setIcon(IconManager.get_icon("folder"))
        self.btn_open_folder.setObjectName("btn_secondary")
        self.btn_open_folder.setEnabled(False)
        self.btn_refresh = QtWidgets.QPushButton("Aktualisieren")
        self.btn_refresh.setIcon(IconManager.get_icon("refresh"))
        self.btn_refresh.setObjectName("btn_secondary")

        self.lbl_loading = QtWidgets.QLabel("🔍 Suche läuft...")
        self._apply_historie_loading_style()
        self.lbl_loading.setVisible(False)

        btn_layout.addWidget(self.btn_open_pdf)
        btn_layout.addWidget(self.btn_open_folder)
        btn_layout.addStretch()
        btn_layout.addWidget(self.lbl_loading)
        btn_layout.addWidget(self.btn_refresh)
        card_layout.addLayout(btn_layout)

        content_layout.addWidget(card)

        self.btn_filter.clicked.connect(self.refresh)
        self.btn_refresh.clicked.connect(self.refresh_with_toast)
        self.e_search.returnPressed.connect(self.refresh)
        self.btn_open_pdf.clicked.connect(self.open_pdf)
        self.btn_open_folder.clicked.connect(self.open_folder)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)

        self.refresh()

    def _apply_historie_loading_style(self) -> None:
        c = AppleTheme.current_colors()
        self.lbl_loading.setStyleSheet(
            f"color: {c['blue']}; font-weight: bold; font-style: italic; margin-right: 8px;"
        )

    def refresh_theme(self) -> None:
        self._apply_historie_loading_style()

    def _toast(self, message: str, level: str = "info"):
        host = self.window()
        if hasattr(host, "show_toast"):
            host.show_toast(message, level)

    def refresh(self):
        host = self.window()
        busy_op_id = -1
        if hasattr(host, "_begin_busy_operation"):
            busy_op_id = host._begin_busy_operation("Lade Verlauf ...", delay_ms=0)
        self.lbl_loading.setVisible(True)

        # UI Updates pausieren für maximalen Performance-Gewinn
        self.table.setUpdatesEnabled(False)
        self.table.setSortingEnabled(False)
        try:
            depot_id = self.cb_depot_filter.currentData()
            typ = self.cb_typ_filter.currentText()
            search_text = self.e_search.text().lower().strip()

            # Datenbank übernimmt die Text-Suche (1000x schneller als Python-Loops)
            rows = self.db.list_bewegungen_with_attachments(depot_id, typ, search_text)

            headers = ["ID", "Depot", "Präparat", "Typ", "Charge", "Verfall",
                       "Eingang", "Ausgang", "Empfänger", "Anzahl", "PDF"]

            self.table.clear()
            self.table.setColumnCount(len(headers))
            self.table.setRowCount(len(rows))
            self.table.setHorizontalHeaderLabels(headers)

            for r, row in enumerate(rows):
                for c in range(10):
                    val = row[c] if row[c] is not None else ""

                    # Numerische Sortierung für ID (0) und Anzahl (9)
                    if c == 0 or c == 9:
                        item = NumericTableWidgetItem(str(val))
                    else:
                        item = QtWidgets.QTableWidgetItem(str(val))

                    item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                    self.table.setItem(r, c, item)

                # PDF-Spalte (Spalte 10) - Ressourcen-schonend zeichnen (ohne QWidget-Overhead)
                pdf_path = row[10]
                pdf_item = QtWidgets.QTableWidgetItem()
                pdf_item.setFlags(pdf_item.flags() ^ Qt.ItemIsEditable)

                # Kein "os.path.exists()" im Loop aufrufen, da das den Mainthread einfriert!
                if pdf_path:
                    pdf_item.setIcon(IconManager.get_icon("check", color="#27ae60"))
                    pdf_item.setToolTip(f"PDF Eintrag vorhanden: {pdf_path}")
                else:
                    pdf_item.setIcon(IconManager.get_icon("x_circle", color="#e74c3c"))
                    pdf_item.setToolTip("Kein PDF vorhanden")

                pdf_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(r, 10, pdf_item)
                self.table.setRowHeight(r, 44)

            self.table.resizeColumnsToContents()
            configure_responsive_table(
                self.table,
                stretch_columns=[2, 8],
                content_columns=[1, 3, 4, 10],
            )
            self.table.setColumnWidth(0, 60)
            self.table.setColumnHidden(0, True)  # ID-Spalte ausblenden
        finally:
            self.table.setSortingEnabled(True)
            self.table.setUpdatesEnabled(True) # UI Updates wieder freigeben
            self.lbl_loading.setVisible(False)
            if hasattr(host, "_end_busy_operation"):
                host._end_busy_operation(busy_op_id)

    def refresh_with_toast(self):
        self.refresh()
        self._toast(f"Historie aktualisiert ({self.table.rowCount()} Einträge).", "info")

    def on_selection_changed(self):
        row = self.table.currentRow()
        if row >= 0:
            bewegung_id = int(self.table.item(row, 0).text())
            pdf_path = self.db.get_attachment_for_bewegung(bewegung_id)
            has_pdf = pdf_path and os.path.exists(pdf_path)
            self.btn_open_pdf.setEnabled(has_pdf)
            self.btn_open_folder.setEnabled(has_pdf)
        else:
            self.btn_open_pdf.setEnabled(False)
            self.btn_open_folder.setEnabled(False)

    def open_pdf(self):
        row = self.table.currentRow()
        if row < 0:
            return
        bewegung_id = int(self.table.item(row, 0).text())
        pdf_path = self.db.get_attachment_for_bewegung(bewegung_id)
        if not pdf_path or not os.path.exists(pdf_path):
            QtWidgets.QMessageBox.warning(self, "Fehler", "PDF-Datei nicht gefunden.")
            return
        try:
            if os.name == 'nt':
                os.startfile(pdf_path)  # nosec B606: opens user-selected attachment with OS default app
            else:
                QDesktopServices.openUrl(QUrl.fromLocalFile(pdf_path))
            self._toast("PDF-Datei geöffnet.", "success")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Fehler", f"PDF konnte nicht geöffnet werden:\n{e}")

    def open_folder(self):
        row = self.table.currentRow()
        if row < 0:
            return
        bewegung_id = int(self.table.item(row, 0).text())
        pdf_path = self.db.get_attachment_for_bewegung(bewegung_id)
        if not pdf_path or not os.path.exists(pdf_path):
            QtWidgets.QMessageBox.warning(self, "Fehler", "PDF-Datei nicht gefunden.")
            return
        folder = os.path.dirname(pdf_path)
        try:
            if os.name == 'nt':
                os.startfile(folder)  # nosec B606: opens folder containing user-selected attachment
            else:
                QDesktopServices.openUrl(QUrl.fromLocalFile(folder))
            self._toast("Ordner geöffnet.", "success")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Fehler", f"Ordner konnte nicht geöffnet werden:\n{e}")


