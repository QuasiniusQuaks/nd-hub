!!! warning "Archiviert"
    Diese Originaldatei ist archiviert. Der aktuelle, konsolidierte Stand befindet sich in der Enterprise-Dokumentation (siehe Hauptnavigation links).

# Desktop-to-Web Parity Plan (1:1)

Dieses Dokument bildet den realen Stand der Feature-Paritaet zwischen Desktop-Client
und `ndhub-web` ab. Stand: nach Sprint-6 Umsetzung (inkrementell fortgeschrieben).

## Paritaetsprinzip

- Gleiches Fachverhalten vor erweitertem UX-Umfang.
- API/Server validieren dieselben Regeln wie Desktop.
- Web ersetzt Desktop-spezifische OS-Funktionen durch sichere Web-Aequivalente.
- DB-Migrationen (SQLite -> MariaDB) duerfen Fachverhalten nicht veraendern.

## Statusdefinition

- `done`: fachlich in Web + API vorhanden und nutzbar.
- `teilweise`: vorhanden, aber mit offenen Luecken, Trade-offs oder Hardening-Bedarf.
- `offen`: noch nicht oder nur als Zielbild vorhanden.

## Feature-Matrix Desktop vs Web

| Cluster | Desktop-Referenz | Web/API-Referenz | Status | Kommentar |
|---|---|---|---|---|
| Auth Login/Logout | `desktop-client/nd_hub.py`, `desktop-client/security_manager.py` | `backend/app.py` (`/auth/login`, `/auth/logout`, `/auth/me`) | done | Rollen und Permission-Pruefung aktiv. |
| Passwortwechsel / Sicherheitsregeln | `desktop-client/security_manager.py`, `desktop-client/ui/dialogs/login_dialog.py` | `backend/app.py` (`/auth/change-password`) | done | Security-Checks vorhanden. |
| Avatar | `desktop-client/ui/pages/page_grundeinstellungen/user_management_tab.py` | `backend/app.py` (`/auth/avatar`) | done | Upload/Delete plus Anzeige im Web vorhanden. |
| Benutzerverwaltung | `desktop-client/ui/pages/page_grundeinstellungen/user_management_tab.py` | `backend/app.py` (`/users*`) + `backend/web/app.js` | done | CRUD, reset, unlock, activity vorhanden. |
| Audit-Logs | Desktop Admin-Flow | `backend/app.py` (`/audit-logs`) + `backend/web/app.js` | done | Filter und Paging vorhanden. |
| Depots CRUD | `desktop-client/ui/pages/page_grundeinstellungen/depots_tab.py` | `backend/app.py` (`/depots`) | done | inkl. Such-/Paging-Parameter. |
| Praeparate CRUD | `desktop-client/ui/pages/page_grundeinstellungen/praeparate_tab.py` | `backend/app.py` (`/praeparate`) | done | inkl. Such-/Paging-Parameter. |
| Zuordnungen Depot-Praeparat | `desktop-client/ui/pages/page_grundeinstellungen/zuordnungen_tab.py` | `backend/app.py` (`/depots/{id}/zuordnungen`) | done | Sollbestand und Assignment vorhanden. |
| Kontakte pro Depot | `desktop-client/ui/pages/page_grundeinstellungen/kontakte_tab.py` | `backend/app.py` (`/depots/{id}/kontakte`, `/kontakte/{id}`) | done | Web-Verwaltung vorhanden. |
| Bewegungen erfassen | `desktop-client/ui/pages/page_bewegungen.py` | `backend/app.py` (`/bewegungen`, `/depots/{id}/praeparate`) | done | Typ-spezifische Regeln vorhanden. |
| PDF-Anhang an Bewegung | `desktop-client/ui/pages/page_bewegungen.py` | `backend/app.py` (`/bewegungen/{id}/attachment`) + `backend/web/app.js` | done | Upload, Inline-View, Download, Dateivalidierung und robustere Fehler-UX aktiv. |
| Historie/Filter/Paging | `desktop-client/ui/pages/page_historie.py` | `backend/app.py` (`/bewegungen`) + `backend/web/app.js` | done | Filter inkl. Depot/Praeparat/Attachment/Datum, robustes Paging, Filter-Reset und persistente Filterauswahl pro User. |
| Historie CSV-Export | `desktop-client/ui/pages/page_historie.py` | `backend/app.py` (`/bewegungen/export.csv`) + `backend/web/app.js` | done | Export uebernimmt aktive Verlauf-Filter. |
| "Ordner oeffnen" (Desktop-OS) | `desktop-client/ui/pages/page_historie.py` | Web-Download/Inline-Flow | teilweise | Kein direkter Dateisystemzugriff im Browser (bewusster Unterschied). |
| Import Preview/Execute | `desktop-client/ui/pages/page_import.py` | `backend/app.py` (`/imports/bewegungen/preview`, `/execute`) | done | CSV/XLS(X) abgedeckt. |
| Import Template | `desktop-client/ui/pages/page_import.py` | `backend/app.py` (`/imports/bewegungen/template`) | done | Excel-Vorlage vorhanden. |
| E-Mail Empfaenger Preview | `desktop-client/ui/pages/page_email.py` | `backend/app.py` (`/emails/recipients-preview`) | done | Kontaktaggregation je Depot vorhanden. |
| E-Mail Draft + History | `desktop-client/ui/pages/page_email.py` | `backend/app.py` (`/emails/drafts`, `/emails/history`) + `backend/web/app.js` | done | Draft-/History-Flow vorhanden. |
| Realversand (SMTP/Outlook) | Desktop hatte Outlook-Idee | Web derzeit Draft-zentriert | teilweise | Optionales Versandmodul noch nicht produktiv eingebunden. |
| Dashboard KPI/Overview | `desktop-client/apple_dashboard.py` | `backend/app.py` (`/dashboard/overview`) + `backend/web/app.js` | done | KPI und Aktivitaeten vorhanden. |
| Verfall-Overview + Export | `desktop-client/verfallmanager.py`, `desktop-client/verfall_widget.py` | `backend/app.py` (`/verfall/overview`, export.csv) | done | Kategorien + Export vorhanden. |
| Verfall-Notifications | Desktop Dashboard-Warnungen | `backend/app.py` (`/notifications/verfall`) + `backend/web/app.js` | done | Polling-Notifications vorhanden. |
| Reports Bewegungen/Bestand/Ranking/Matrix/Verfall | `desktop-client/ui/pages/page_auswertungen.py` | `backend/app.py` (`/reports/*`) + `backend/web/app.js` | done | Datenendpunkte vorhanden. |
| Report-Exporte CSV/PDF/PPTX | `desktop-client/ui/pages/page_auswertungen.py`, `desktop-client/tools/ppt_exporter.py` | `backend/app.py` (`/reports/*/export.*`) | done | Alle Exportformate vorhanden. |
| Backup list/create/download/restore | `desktop-client/ui/pages/page_grundeinstellungen/backup_tab.py` | `backend/app.py` (`/admin/backup/*`) + `backend/web/app.js` | done | Web-Admin-Flows vorhanden. |
| Auto-Backup | Desktop + Backend-Task | `backend/app.py` (Startup + `ND_HUB_AUTO_BACKUP_HOURS`) | done | Intervallgesteuert vorhanden. |
| Session-Persistenz fuer HA/Restart | Desktop lokal, Session anders | `backend/auth.py` (in-memory TokenStore) | teilweise | Fuer Multi-Instanz/Restart-Haerte noch auszubauen. |
| MariaDB-Unterstuetzung | n/a | `backend/mariadb_repository.py`, `backend/db_manager.py`, `backend/security_manager.py` | teilweise | Repository-Adapter, Migrationstool und Cutover-Runbook vorhanden; produktive Cutover-/Betriebs-Haertung bleibt offen. |
| Desktop<->Backend Sync v1 | `desktop-client/core/data_access_layer.py`, `desktop-client/core/sync_service.py` | `backend/app.py` (`/sync/status`, `/sync/pull`, `/sync/push`, `/sync/ops/stats`) | done | Hybrid-Sync mit lokaler Outbox, Cursor-Pull, idempotentem Push und E2E-Tests umgesetzt (Attachment-Dateisync weiterhin bewusst ausserhalb v1). |

## Priorisierte Restarbeiten (aus Matrix)

1. Session-Hardening fuer Container-Neustarts und horizontalen Betrieb.
2. E-Mail-Realversand als optionales Modul (Draft-only bleibt fallback).
3. MariaDB-Cutover und Betriebs-Hardening (Deadlock-/Rollback-/Backup-Routinen unter Last).
4. Web-Ersatz fuer "Ordner oeffnen" klar dokumentieren und UX-seitig absichern.
5. Paritaetsabnahme mit Regressionstestpaket (API + Web + Hybrid-Sync End-to-End).

## Referenzdokumente

- Docker-Zielprofil: `backend/DOCKER_TARGET_PROFILE.md`
- MariaDB-Migrationsspezifikation: `backend/MARIADB_MIGRATION_SPEC.md`
- Sync-Contract v1: `backend/SYNC_CONTRACT_V1.md`

