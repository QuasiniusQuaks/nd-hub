"""Custom-SQL-Tab — SQL-Editor + Result-Tabelle + Save/Load für Power-User.

Ermöglicht Power-Usern, eigene SQL-Queries auszuführen, zu speichern
und später wieder aufzurufen. Security: nur SELECT/WITH erlaubt.

Issue #42 Phase 4 — Power-User.
"""

from __future__ import annotations

import logging

from apple_theme import AppleTheme
from db_manager import Database
from PySide6 import QtCore, QtWidgets

from ui.utils import configure_responsive_table

from ._base_tab import BaseTab

logger = logging.getLogger(__name__)

# Beispiel-Queries für den Quick-Start
_EXAMPLE_QUERIES = [
    ("Top-10-Abgänge", "SELECT p.name, SUM(b.anzahl) AS gesamt FROM bewegungen b JOIN praeparate p ON p.id = b.praeparat_id WHERE b.typ = 'Abgang' GROUP BY p.name ORDER BY gesamt DESC LIMIT 10"),
    ("Depot-Bestand", "SELECT d.name AS depot, p.name AS praeparat, dp.sollbestand, COALESCE(SUM(CASE WHEN b.typ='Zugang' THEN b.anzahl WHEN b.typ IN ('Abgang','Vernichtung') THEN -b.anzahl ELSE 0 END),0) AS ist FROM depot_praeparate dp JOIN depots d ON d.id=dp.depot_id JOIN praeparate p ON p.id=dp.praeparat_id LEFT JOIN bewegungen b ON b.depot_id=dp.depot_id AND b.praeparat_id=dp.praeparat_id GROUP BY d.name, p.name, dp.sollbestand"),
    ("Verfälle dieses Jahr", "SELECT p.name, b.charge, b.verfall, b.anzahl FROM bewegungen b JOIN praeparate p ON p.id=b.praeparat_id WHERE b.typ='Zugang' AND b.verfall != '' AND strftime('%Y', b.verfall) = strftime('%Y','now') ORDER BY b.verfall"),
]


class TabSqlEditor(BaseTab):
    """Custom-SQL-Tab mit Editor, Result-Tabelle und Saved-Queries-Bibliothek."""

    def __init__(self, db: Database, queries, parent=None) -> None:
        super().__init__(db, queries, parent)

    def refresh(self) -> None:
        self._clear_content()

        # 1. SQL-Editor + Controls
        card_editor = self._make_card("🔍 Custom SQL-Editor")
        self._build_editor(card_editor)
        self.content_layout.addWidget(card_editor)

        # 2. Result-Tabelle
        card_result = self._make_card("Ergebnisse")
        self._result_label = QtWidgets.QLabel("Keine Query ausgeführt.")
        c = AppleTheme.current_colors()
        self._result_label.setStyleSheet(f"font-size: 11px; color: {c['tertiary_label']}; padding: 4px;")
        card_result.layout().addWidget(self._result_label)

        self._result_table = self._create_table([], 0)
        card_result.layout().addWidget(self._result_table)

        # 3. Saved-Queries-Bibliothek
        card_saved = self._make_card("📚 Gespeicherte Queries")
        self._build_saved_queries(card_saved)

        self.content_layout.addStretch()

    def _build_editor(self, card: QtWidgets.QFrame) -> None:
        """Baut den SQL-Editor mit Controls."""
        layout = card.layout()

        # Beispiel-Queries Dropdown
        example_layout = QtWidgets.QHBoxLayout()
        lbl_example = QtWidgets.QLabel("Beispiele:")
        c = AppleTheme.current_colors()
        lbl_example.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {c['secondary_label']};")
        example_layout.addWidget(lbl_example)

        self.combo_examples = QtWidgets.QComboBox()
        self.combo_examples.addItem("— Beispiel wählen —")
        for name, sql in _EXAMPLE_QUERIES:
            self.combo_examples.addItem(name, sql)
        self.combo_examples.currentIndexChanged.connect(self._on_example_selected)
        example_layout.addWidget(self.combo_examples, stretch=1)
        layout.addLayout(example_layout)

        # SQL-Text-Editor
        self.sql_editor = QtWidgets.QPlainTextEdit()
        self.sql_editor.setPlaceholderText(
            "SELECT p.name, SUM(b.anzahl) AS gesamt\nFROM bewegungen b\nJOIN praeparate p ON p.id = b.praeparat_id\nWHERE b.typ = 'Abgang'\nGROUP BY p.name\nORDER BY gesamt DESC"
        )
        self.sql_editor.setStyleSheet(
            f"font-family: 'SF Mono', 'Menlo', 'Consolas', monospace; font-size: 12px; "
            f"background-color: {c.get('card_bg', '#ffffff')}; "
            f"border: 1px solid {c.get('separator', '#e0e0e0')}; border-radius: 8px; padding: 8px;"
        )
        self.sql_editor.setMinimumHeight(120)
        layout.addWidget(self.sql_editor)

        # Buttons
        btn_layout = QtWidgets.QHBoxLayout()

        self.btn_run = QtWidgets.QPushButton("▶ Ausführen")
        self.btn_run.setStyleSheet(
            f"background-color: {c['blue']}; color: white; font-weight: 600; padding: 8px 16px; border-radius: 6px;"
        )
        self.btn_run.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.btn_run.clicked.connect(self._on_run_query)
        btn_layout.addWidget(self.btn_run)

        self.btn_save = QtWidgets.QPushButton("💾 Query speichern")
        self.btn_save.clicked.connect(self._on_save_query)
        btn_layout.addWidget(self.btn_save)

        self.btn_export = QtWidgets.QPushButton("📄 als PDF")
        self.btn_export.clicked.connect(self._on_export_result_pdf)
        btn_layout.addWidget(self.btn_export)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _build_saved_queries(self, card: QtWidgets.QFrame) -> None:
        """Baut die Saved-Queries-Bibliothek."""
        layout = card.layout()

        self.saved_table = self._create_table([], 0)
        self._populate_saved_queries()
        layout.addWidget(self.saved_table)

        # Action-Buttons
        action_layout = QtWidgets.QHBoxLayout()
        self.btn_load = QtWidgets.QPushButton("📂 Laden")
        self.btn_load.clicked.connect(self._on_load_query)
        action_layout.addWidget(self.btn_load)

        self.btn_run_saved = QtWidgets.QPushButton("▶ Ausführen")
        self.btn_run_saved.clicked.connect(self._on_run_saved_query)
        action_layout.addWidget(self.btn_run_saved)

        self.btn_delete_saved = QtWidgets.QPushButton("🗑️ Löschen")
        self.btn_delete_saved.clicked.connect(self._on_delete_saved_query)
        action_layout.addWidget(self.btn_delete_saved)

        action_layout.addStretch()
        layout.addLayout(action_layout)

    def _populate_saved_queries(self) -> None:
        """Lädt gespeicherte Queries in die Tabelle."""
        try:
            queries = self.db.get_saved_queries()
        except Exception:
            queries = []

        headers = ["Name", "Beschreibung", "Erstellt", "Letzte Ausführung"]
        self.saved_table.setColumnCount(len(headers))
        self.saved_table.setHorizontalHeaderLabels(headers)
        self.saved_table.setRowCount(len(queries))

        for i, q in enumerate(queries):
            self.saved_table.setItem(i, 0, QtWidgets.QTableWidgetItem(str(q["name"])))
            self.saved_table.setItem(i, 1, QtWidgets.QTableWidgetItem(str(q["description"] or "—")))
            self.saved_table.setItem(i, 2, QtWidgets.QTableWidgetItem(str(q["created_at"] or "—")))
            self.saved_table.setItem(i, 3, QtWidgets.QTableWidgetItem(str(q["last_run"] or "—")))

    def _on_example_selected(self, index: int) -> None:
        """Beispiel-Query in den Editor laden."""
        if index <= 0:
            return
        sql = self.combo_examples.itemData(index)
        if sql:
            self.sql_editor.setPlainText(sql)

    def _on_run_query(self) -> None:
        """SQL aus dem Editor ausführen."""
        sql = self.sql_editor.toPlainText().strip()
        if not sql:
            return

        # Security: nur SELECT/WITH
        upper = sql.upper()
        if not upper.startswith(("SELECT", "WITH")):
            self._show_error("Nur SELECT/WITH-Statements sind erlaubt.")
            return

        try:
            cursor = self.db.cur.execute(sql)
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
            self._display_results(rows, columns)
        except Exception as e:
            self._show_error(f"SQL-Fehler: {e}")

    def _on_save_query(self) -> None:
        """Aktuelle Query speichern."""
        sql = self.sql_editor.toPlainText().strip()
        if not sql:
            return

        name, ok = QtWidgets.QInputDialog.getText(self, "Query speichern", "Name:")
        if not ok or not name.strip():
            return

        desc, ok = QtWidgets.QInputDialog.getText(self, "Query speichern", "Beschreibung (optional):")
        if not ok:
            desc = ""

        if self.db.save_query(name.strip(), sql, desc):
            self._populate_saved_queries()
            QtWidgets.QMessageBox.information(self, "Gespeichert", f"Query '{name}' gespeichert.")
        else:
            QtWidgets.QMessageBox.warning(self, "Fehler", "Query konnte nicht gespeichert werden.")

    def _on_load_query(self) -> None:
        """Gewählte gespeicherte Query in den Editor laden."""
        row = self.saved_table.currentRow()
        if row < 0:
            return
        name = self.saved_table.item(row, 0).text()
        query = self.db.get_saved_query(name)
        if query:
            self.sql_editor.setPlainText(query["sql_text"])

    def _on_run_saved_query(self) -> None:
        """Gewählte gespeicherte Query direkt ausführen."""
        row = self.saved_table.currentRow()
        if row < 0:
            return
        name = self.saved_table.item(row, 0).text()
        rows, columns = self.db.run_saved_query(name)
        if columns:
            self._display_results(rows, columns)
            self._populate_saved_queries()  # last_run aktualisieren
        else:
            self._show_error(f"Query '{name}' konnte nicht ausgeführt werden.")

    def _on_delete_saved_query(self) -> None:
        """Gewählte gespeicherte Query löschen."""
        row = self.saved_table.currentRow()
        if row < 0:
            return
        name = self.saved_table.item(row, 0).text()
        reply = QtWidgets.QMessageBox.question(
            self, "Löschen", f"Query '{name}' wirklich löschen?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )
        if reply == QtWidgets.QMessageBox.Yes:
            self.db.delete_saved_query(name)
            self._populate_saved_queries()

    def _on_export_result_pdf(self) -> None:
        """Aktuelle Ergebnisse als PDF exportieren."""
        QtWidgets.QMessageBox.information(self, "PDF-Export", "Feature in Entwicklung — folgt in Kürze.")

    def _display_results(self, rows: list, columns: list[str]) -> None:
        """Zeigt Query-Ergebnisse in der Tabelle."""
        self._result_table.setColumnCount(len(columns))
        self._result_table.setHorizontalHeaderLabels(columns)
        self._result_table.setRowCount(len(rows))

        for i, row in enumerate(rows):
            for j, val in enumerate(row):
                self._result_table.setItem(i, j, QtWidgets.QTableWidgetItem(str(val)))

        self._result_label.setText(f"{len(rows)} Zeile(n), {len(columns)} Spalte(n)")

    def _show_error(self, msg: str) -> None:
        """Zeigt eine Fehlermeldung."""
        c = AppleTheme.current_colors()
        self._result_label.setText(f"❌ {msg}")
        self._result_label.setStyleSheet(f"font-size: 12px; color: {c['red']}; padding: 4px;")

    def _create_table(self, headers: list[str], row_count: int) -> QtWidgets.QTableWidget:
        table = QtWidgets.QTableWidget(row_count, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        table.horizontalHeader().setStretchLastSection(True)
        try:
            configure_responsive_table(table)
        except Exception:
            table.resizeColumnsToContents()
        return table
