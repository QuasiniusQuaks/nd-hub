# Desktop Client: UI-Seiten

Diese Seite gibt eine Karte aller modularen UI-Seiten und Dialoge im
Desktop Client. Sie ist nuetzlich fuer Schulungen, QA und neue
Entwickler.

## Hauptseiten (`desktop-client/ui/pages/`)

| Seite | Datei | Inhalt |
|---|---|---|
| Bewegungen | `page_bewegungen.py` | Erfassung von Zugang/Abgang/Vernichtung mit Anhaengen. |
| Historie | `page_historie.py` | Verlauf, Filter, persistente Filterauswahl, CSV-Export, Anhang-Voransicht. |
| Import | `page_import.py` | CSV/XLS-Import mit Preview, Fehlerklassifizierung, Dry-Run. |
| E-Mail | `page_email.py` | Empfaengervorschau, Draft-/SMTP-Versand, Verlauf. |
| Auswertungen | `page_auswertungen.py` | Reports (Bestand, Bewegungen, Ranking, Matrix, Verfall) inkl. Export. |
| Grundeinstellungen | `page_grundeinstellungen/_hauptseite.py` | Container fuer alle Admin-Tabs. |

### Tabs unter Grundeinstellungen (`page_grundeinstellungen/`)

| Tab | Datei | Inhalt |
|---|---|---|
| Depots | `depots_tab.py` | CRUD und Suche fuer Depots. |
| Praeparate | `praeparate_tab.py` | CRUD und Suche fuer Praeparate. |
| Zuordnungen | `zuordnungen_tab.py` | Depot-Praeparat-Zuordnungen mit Sollbestand. |
| Kontakte | `kontakte_tab.py` | Ansprechpartner pro Depot. |
| Benutzerverwaltung | `user_management_tab.py` | User CRUD, Reset, Unlock, Rollen. |
| User-Dialoge | `user_management_dialogs.py` | Detaildialoge fuer Userpflege. |
| Audit-Logs | `audit_logs_tab.py` | Filterbarer Audit-Trail. |
| Backup | `backup_tab.py` | Manuelle/automatische Backups, Restore. |

## Dialoge (`desktop-client/ui/dialogs/`)

| Dialog | Datei | Inhalt |
|---|---|---|
| Login | `login_dialog.py` | Login, Passwortwechsel, Sperrhinweise. |
| Setup-Wizard | `setup_wizard_dialog.py` | Mehrstufige Erstkonfiguration. |
| Embedded Dialog Host | `embedded_dialog_host.py` | Patches fuer modale Subdialoge. |
| Verfall-Detail | `verfall_detail_dialog.py` | Detailansicht zu einem Verfallseintrag. |
| PPT-Export | `dialog_ppt_export.py` | Konfiguration fuer PPTX-Exporte. |
| Basisdialoge | `basic_dialogs.py` | Wiederverwendbare modale Dialoge. |

## Querverweise

- Setup-Wizard und Konfigurationsverhalten: siehe
  [Konfiguration](03-configuration.md).
- Funktionsumfang pro Bereich: siehe [Funktionen](04-features.md).
- Sicherheits- und Auditlogik im Hintergrund: siehe
  [Security / AuthN & AuthZ](../security/01-authn-authz.md).
