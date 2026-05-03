"""E-Mail-Kommunikation - Senden und Verlauf."""

from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtCore import Qt, Signal, QDate, QObject, QRunnable, QThreadPool

from db_manager import Database, to_iso
from icon_manager import IconManager
from apple_theme import AppleTheme
from ui.utils import create_card_widget, NumericTableWidgetItem, configure_responsive_table
from ui.dialogs.embedded_dialog_host import exec_embedded_dialog

class EmailPage(QtWidgets.QWidget):
    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        title = QtWidgets.QLabel("E-Mail-Kommunikation")
        title.setProperty("class", "page-title")
        layout.addWidget(title)
        
        tabs = QtWidgets.QTabWidget()
        
        tab_new = QtWidgets.QWidget()
        tab_new_layout = QtWidgets.QVBoxLayout(tab_new)
        tab_new_layout.setContentsMargins(0, 0, 0, 0)

        tab_new_scroll = QtWidgets.QScrollArea()
        tab_new_scroll.setWidgetResizable(True)
        tab_new_scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        tab_new_layout.addWidget(tab_new_scroll)

        tab_new_content = QtWidgets.QWidget()
        tab_new_scroll.setWidget(tab_new_content)
        tab_new_content_layout = QtWidgets.QVBoxLayout(tab_new_content)
        tab_new_content_layout.setContentsMargins(0, 0, 0, 0)
        tab_new_content_layout.setSpacing(20)
        
        empfaenger_card = create_card_widget()
        empfaenger_layout = QtWidgets.QVBoxLayout(empfaenger_card)
        
        empf_title = QtWidgets.QLabel("Empfänger auswählen")
        empf_title.setStyleSheet("font-size: 16px; font-weight: 600; margin-bottom: 12px;")
        empfaenger_layout.addWidget(empf_title)
        
        self._email_recipient_hint = QtWidgets.QLabel(
            "Pro Depot werden automatisch alle Ansprechpartner als Empfänger hinzugefügt."
        )
        self._email_recipient_hint.setWordWrap(True)
        empfaenger_layout.addWidget(self._email_recipient_hint)
        
        depot_controls = QtWidgets.QHBoxLayout()
        
        self.depot_list = QtWidgets.QListWidget()
        self.depot_list.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
        self.depot_list.setMinimumHeight(170)
        depot_controls.addWidget(self.depot_list)
        
        depot_buttons = QtWidgets.QVBoxLayout()
        self.btn_select_all = QtWidgets.QPushButton(" Alle auswählen")
        self.btn_select_all.setIcon(IconManager.get_icon("check"))
        self.btn_select_none = QtWidgets.QPushButton(" Alle abwählen")
        self.btn_select_none.setIcon(IconManager.get_icon("x"))
        depot_buttons.addWidget(self.btn_select_all)
        depot_buttons.addWidget(self.btn_select_none)
        depot_buttons.addStretch()
        depot_controls.addLayout(depot_buttons)
        
        empfaenger_layout.addLayout(depot_controls)
        
        self.label_empfaenger_count = QtWidgets.QLabel("Ausgewählte Empfänger: 0")
        empfaenger_layout.addWidget(self.label_empfaenger_count)
        
        self.text_empfaenger_preview = QtWidgets.QTextEdit()
        self.text_empfaenger_preview.setReadOnly(True)
        self.text_empfaenger_preview.setMinimumHeight(90)
        self.text_empfaenger_preview.setMaximumHeight(180)
        self.text_empfaenger_preview.setPlaceholderText("Empfänger werden hier angezeigt...")
        empfaenger_layout.addWidget(self.text_empfaenger_preview)
        
        tab_new_content_layout.addWidget(empfaenger_card)
        
        content_card = create_card_widget()
        content_layout = QtWidgets.QFormLayout(content_card)
        content_layout.setSpacing(16)
        
        self.line_betreff = QtWidgets.QLineEdit()
        self.line_betreff.setPlaceholderText("z.B. Inventur-Checkliste ND-Hub")
        content_layout.addRow("Betreff:", self.line_betreff)
        
        self.text_nachricht = QtWidgets.QPlainTextEdit()
        self.text_nachricht.setPlaceholderText(
            "Sehr geehrte Damen und Herren,\n\n"
            "hiermit möchten wir Sie über ...\n\n"
            "Mit freundlichen Grüßen"
        )
        self.text_nachricht.setMinimumHeight(200)
        content_layout.addRow("Nachricht:", self.text_nachricht)

        self.check_send_now = QtWidgets.QCheckBox(
            "Sofort per SMTP senden (Konfiguration: Grundeinstellungen → E-Mail-Versand)"
        )
        content_layout.addRow("Versand:", self.check_send_now)
        
        tab_new_content_layout.addWidget(content_card)
        
        button_layout = QtWidgets.QHBoxLayout()
        self.btn_create_email = QtWidgets.QPushButton(" E-Mail in Outlook erstellen")
        self.btn_create_email.setIcon(IconManager.get_icon("mail"))
        self.btn_create_email.setObjectName("btn_save")
        self.btn_create_email.setMinimumHeight(44)
        button_layout.addStretch()
        button_layout.addWidget(self.btn_create_email)
        tab_new_content_layout.addLayout(button_layout)
        
        tabs.addTab(tab_new, "Neue E-Mail")
        tabs.setTabIcon(0, IconManager.get_icon("mail"))
        
        tab_verlauf = QtWidgets.QWidget()
        tab_verlauf_layout = QtWidgets.QVBoxLayout(tab_verlauf)
        tab_verlauf_layout.setContentsMargins(0, 0, 0, 0)
        
        verlauf_card = create_card_widget()
        verlauf_card_layout = QtWidgets.QVBoxLayout(verlauf_card)
        
        self.table_verlauf = QtWidgets.QTableWidget()
        self.table_verlauf.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table_verlauf.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        configure_responsive_table(self.table_verlauf)
        verlauf_card_layout.addWidget(self.table_verlauf)
        
        verlauf_buttons = QtWidgets.QHBoxLayout()
        self.btn_show_details = QtWidgets.QPushButton(" Details anzeigen")
        self.btn_show_details.setIcon(IconManager.get_icon("eye"))
        self.btn_refresh_verlauf = QtWidgets.QPushButton("Aktualisieren")
        self.btn_refresh_verlauf.setIcon(IconManager.get_icon("refresh"))
        self.btn_refresh_verlauf.setObjectName("btn_secondary")
        verlauf_buttons.addWidget(self.btn_show_details)
        verlauf_buttons.addStretch()
        verlauf_buttons.addWidget(self.btn_refresh_verlauf)
        verlauf_card_layout.addLayout(verlauf_buttons)
        
        tab_verlauf_layout.addWidget(verlauf_card)
        
        tabs.addTab(tab_verlauf, "Verlauf")
        tabs.setTabIcon(1, IconManager.get_icon("clock"))
        
        layout.addWidget(tabs)
        
        self.btn_select_all.clicked.connect(self.select_all_depots)
        self.btn_select_none.clicked.connect(self.select_no_depots)
        self.depot_list.itemSelectionChanged.connect(self.update_empfaenger_preview)
        self.btn_create_email.clicked.connect(self.create_outlook_email)
        self.btn_refresh_verlauf.clicked.connect(self.refresh_verlauf_with_toast)
        self.btn_show_details.clicked.connect(self.show_email_details)
        
        self._apply_email_hint_styles()
        # Initialisierung entkoppeln, damit Seitenwechsel nicht "hängt".
        QtCore.QTimer.singleShot(0, self._load_initial_data)

    def _apply_email_hint_styles(self) -> None:
        c = AppleTheme.current_colors()
        self._email_recipient_hint.setStyleSheet(
            f"color: {c['secondary_label']}; font-size: 12px; margin-bottom: 12px;"
        )
        self.label_empfaenger_count.setStyleSheet(
            f"font-weight: 600; color: {c['blue']}; margin-top: 8px;"
        )

    def refresh_theme(self) -> None:
        self._apply_email_hint_styles()

    def _load_initial_data(self):
        self.refresh_depot_list()
        self.refresh_verlauf()

    def _toast(self, message: str, level: str = "info"):
        host = self.window()
        if hasattr(host, "show_toast"):
            host.show_toast(message, level)

    def refresh_depot_list(self):
        self.depot_list.clear()
        depots = self.db.list_depots()
        for row in depots:
            if len(row) < 2:
                continue
            depot_id = row[0]
            name = row[1]
            item = QtWidgets.QListWidgetItem(f"{name}")
            item.setData(Qt.UserRole, depot_id)
            self.depot_list.addItem(item)

    def select_all_depots(self):
        for i in range(self.depot_list.count()):
            self.depot_list.item(i).setSelected(True)

    def select_no_depots(self):
        self.depot_list.clearSelection()

    def update_empfaenger_preview(self):
        selected_items = self.depot_list.selectedItems()
        if not selected_items:
            self.label_empfaenger_count.setText("Ausgewählte Empfänger: 0")
            self.text_empfaenger_preview.clear()
            return
        
        depot_ids = [item.data(Qt.UserRole) for item in selected_items]
        kontakte = self.db.get_kontakte_by_depot_ids(depot_ids)
        
        if not kontakte:
            self.label_empfaenger_count.setText("Keine E-Mail-Adressen vorhanden")
            self.text_empfaenger_preview.setPlainText("Für die ausgewählten Depots sind keine Ansprechpartner mit E-Mail-Adressen hinterlegt.")
            return
        
        self.label_empfaenger_count.setText(f"Ausgewählte Empfänger: {len(kontakte)}")
        
        preview_text = ""
        current_depot = None
        for k_id, name, rolle, email, depot_name, depot_id in kontakte:
            if depot_name != current_depot:
                current_depot = depot_name
                preview_text += f"\n📍 {depot_name}\n"
            preview_text += f"   • {name} ({rolle}) - {email}\n"
        
        self.text_empfaenger_preview.setPlainText(preview_text.strip())

    def create_outlook_email(self):
        selected_items = self.depot_list.selectedItems()
        if not selected_items:
            QtWidgets.QMessageBox.warning(self, "Keine Depots ausgewählt", 
                                         "Bitte wählen Sie mindestens ein Depot aus.")
            return
        
        betreff = self.line_betreff.text().strip()
        nachricht = self.text_nachricht.toPlainText().strip()
        
        if not betreff:
            QtWidgets.QMessageBox.warning(self, "Kein Betreff", 
                                         "Bitte geben Sie einen Betreff ein.")
            return
        
        depot_ids = [item.data(Qt.UserRole) for item in selected_items]
        kontakte = self.db.get_kontakte_by_depot_ids(depot_ids)
        
        if not kontakte:
            QtWidgets.QMessageBox.warning(self, "Keine Empfänger", 
                                         "Für die ausgewählten Depots sind keine E-Mail-Adressen hinterlegt.")
            return
        
        emails = [k[3] for k in kontakte]
        depot_names = list(set([k[4] for k in kontakte]))
        send_now = bool(self.check_send_now.isChecked())

        try:
            if send_now:
                missing = self.db.smtp_settings_missing_for_send()
                if missing:
                    QtWidgets.QMessageBox.warning(
                        self,
                        "SMTP nicht konfiguriert",
                        "Für den direkten Versand fehlen Angaben:\n\n• "
                        + "\n• ".join(missing)
                        + "\n\nBitte unter Grundeinstellungen → Tab „E-Mail-Versand“ ergänzen.",
                    )
                    return

                email_id = self.db.add_email_verlauf(
                    betreff=betreff,
                    nachricht=nachricht,
                    depot_names=", ".join(depot_names),
                    emails="; ".join(emails),
                    anzahl=len(emails),
                    send_now=True,
                    delivery_status="queued",
                    delivery_channel="smtp",
                )
                try:
                    self.db.send_smtp_email(betreff, nachricht, emails)
                    self.db.update_email_verlauf_delivery(int(email_id), "sent", "smtp", None)
                except Exception as send_exc:
                    self.db.update_email_verlauf_delivery(int(email_id), "failed", "smtp", str(send_exc))
                    QtWidgets.QMessageBox.critical(self, "SMTP-Versand", str(send_exc))
                    self.refresh_verlauf()
                    return

                QtWidgets.QMessageBox.information(
                    self,
                    "Gesendet",
                    f"Die Nachricht wurde per SMTP an {len(emails)} Empfänger versendet.",
                )
                self._toast("E-Mail per SMTP gesendet.", "success")
            else:
                self.db.add_email_verlauf(
                    betreff=betreff,
                    nachricht=nachricht,
                    depot_names=", ".join(depot_names),
                    emails="; ".join(emails),
                    anzahl=len(emails),
                    send_now=False,
                    delivery_status="draft",
                    delivery_channel="outlook",
                )
                QtWidgets.QMessageBox.information(
                    self,
                    "Entwurf gespeichert",
                    f"Eintrag mit {len(emails)} Empfänger(n) im Verlauf gespeichert.\n\n"
                    "Zum direkten Versand aktivieren Sie „Sofort per SMTP senden“ und hinterlegen Sie den Server "
                    "unter Grundeinstellungen → E-Mail-Versand.",
                )
                self._toast(f"E-Mail-Entwurf für {len(emails)} Empfänger gespeichert.", "success")

            self.line_betreff.clear()
            self.text_nachricht.clear()
            self.check_send_now.setChecked(False)
            self.depot_list.clearSelection()
            self.refresh_verlauf()

        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Fehler",
                str(e),
            )

    def refresh_verlauf(self):
        host = self.window()
        busy_op_id = -1
        if hasattr(host, "_begin_busy_operation"):
            busy_op_id = host._begin_busy_operation("Lade E-Mail-Verlauf ...", delay_ms=0)
        self.table_verlauf.setUpdatesEnabled(False)
        try:
            verlauf = self.db.get_email_verlauf(limit=50)
            
            headers = ["ID", "Datum", "Betreff", "Depots", "Empfänger", "Status"]
            self.table_verlauf.clear()
            self.table_verlauf.setColumnCount(len(headers))
            self.table_verlauf.setRowCount(len(verlauf))
            self.table_verlauf.setHorizontalHeaderLabels(headers)
            
            for r, (email_id, datum, betreff, depots, anzahl, delivery_status) in enumerate(verlauf):
                self.table_verlauf.setItem(r, 0, QtWidgets.QTableWidgetItem(str(email_id)))
                self.table_verlauf.setItem(r, 1, QtWidgets.QTableWidgetItem(datum))
                self.table_verlauf.setItem(r, 2, QtWidgets.QTableWidgetItem(betreff))
                self.table_verlauf.setItem(r, 3, QtWidgets.QTableWidgetItem(depots))
                self.table_verlauf.setItem(r, 4, QtWidgets.QTableWidgetItem(str(anzahl)))
                self.table_verlauf.setItem(r, 5, QtWidgets.QTableWidgetItem(str(delivery_status or "draft")))
            
            configure_responsive_table(
                self.table_verlauf,
                stretch_columns=[2, 3],
                content_columns=[1, 4, 5],
            )
            self.table_verlauf.resizeColumnToContents(1)
            self.table_verlauf.resizeColumnToContents(4)
            self.table_verlauf.resizeColumnToContents(5)
            self.table_verlauf.setColumnWidth(0, 50)
            self.table_verlauf.setColumnHidden(0, True)
        finally:
            self.table_verlauf.setUpdatesEnabled(True)
            if hasattr(host, "_end_busy_operation"):
                host._end_busy_operation(busy_op_id)

    def refresh_verlauf_with_toast(self):
        self.refresh_verlauf()
        rows = self.table_verlauf.rowCount() if hasattr(self, "table_verlauf") else 0
        self._toast(f"E-Mail-Verlauf aktualisiert ({rows} Einträge).", "info")

    def show_email_details(self):
        row = self.table_verlauf.currentRow()
        if row < 0:
            QtWidgets.QMessageBox.information(self, "Keine Auswahl", "Bitte wählen Sie eine E-Mail aus.")
            return
        
        email_id = int(self.table_verlauf.item(row, 0).text())
        details = self.db.get_email_details(email_id)
        
        if not details:
            return
        
        datum, betreff, nachricht, depots, emails, anzahl, send_now, delivery_status, delivery_channel, delivery_error = details
        
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle(f"E-Mail Details - {betreff}")
        dialog.resize(760, 560)
        
        layout = QtWidgets.QVBoxLayout(dialog)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        layout.addWidget(scroll)

        dialog_content = QtWidgets.QWidget()
        scroll.setWidget(dialog_content)
        content_layout = QtWidgets.QVBoxLayout(dialog_content)
        
        info_layout = QtWidgets.QFormLayout()
        info_layout.addRow("Datum:", QtWidgets.QLabel(datum))
        info_layout.addRow("Betreff:", QtWidgets.QLabel(betreff))
        info_layout.addRow("Depots:", QtWidgets.QLabel(depots))
        info_layout.addRow("Anzahl Empfänger:", QtWidgets.QLabel(str(anzahl)))
        info_layout.addRow("Send-Now:", QtWidgets.QLabel("Ja" if int(send_now or 0) else "Nein"))
        info_layout.addRow("Status:", QtWidgets.QLabel(str(delivery_status or "-")))
        info_layout.addRow("Kanal:", QtWidgets.QLabel(str(delivery_channel or "-")))
        if delivery_error:
            info_layout.addRow("Fehler:", QtWidgets.QLabel(str(delivery_error)))
        content_layout.addLayout(info_layout)
        
        content_layout.addWidget(QtWidgets.QLabel("Empfänger:"))
        email_text = QtWidgets.QTextEdit()
        email_text.setReadOnly(True)
        email_text.setPlainText(emails.replace("; ", "\n"))
        email_text.setMinimumHeight(120)
        email_text.setMaximumHeight(220)
        content_layout.addWidget(email_text)
        
        content_layout.addWidget(QtWidgets.QLabel("Nachricht:"))
        msg_text = QtWidgets.QTextEdit()
        msg_text.setReadOnly(True)
        msg_text.setPlainText(nachricht)
        msg_text.setMinimumHeight(220)
        content_layout.addWidget(msg_text)
        
        btn_close = QtWidgets.QPushButton("Schließen")
        btn_close.clicked.connect(dialog.accept)
        layout.addWidget(btn_close)
        
        exec_embedded_dialog(self, dialog)


