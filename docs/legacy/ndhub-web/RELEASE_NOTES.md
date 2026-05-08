!!! warning "Archiviert"
    Diese Originaldatei ist archiviert. Der aktuelle, konsolidierte Stand befindet sich in der Enterprise-Dokumentation (siehe Hauptnavigation links).

# Release Notes

## ND-Hub Web/Backend - Parity and Hardening Milestone

Datum: 2026-04-23

### Highlights

- Desktop/Web-Paritaet fuer Kernfluesse deutlich angehoben und dokumentiert.
- Bewegungsverlauf vollstaendig gehaertet (Filter, Persistenz, CSV, Attachment-UX).
- Import produktionsnäher gemacht (idempotent, Dry-Run, Fehlerklassifizierung).
- E-Mail-Flow erweitert (Draft-Fallback + optionaler SMTP-Liveversand).
- Backup/Restore und Report-Exporte operativ gehaertet.
- User-Admin-Schutzregeln erweitert (Selbstschutz, letzter aktiver Admin).
- Session/Security-Acceptance und Hybrid-Sync-v1-Regression erfolgreich abgeschlossen.

### Backend/API Changes

- Neue/erweiterte Endpunkte fuer:
  - Sync-Operations (`/sync/status`, `/sync/pull`, `/sync/push`, `/sync/ops/stats`)
  - Bewegungsverlauf-Export (`/bewegungen/export.csv`)
  - E-Mail-Delivery-Status (`/emails/delivery/status`)
- Report-Exporte mit kontextreichen Dateinamen und strikter Datumsvalidierung.
- Import-Execute mit Fingerprint-Deduplizierung und `dry_run`.
- Backup-Restore mit Upload-Groessenlimit und Dateiformat-Validierung.

### Frontend/Web Changes

- Persistente Verlauf-Filter pro User + Reset-Flow.
- Stabilere Attachment-Bedienung (Open/Download/Fehlermeldungen).
- Import-UX mit Fehlerzusammenfassung und Dry-Run-Hinweisen.
- E-Mail-UI mit Versandmodus-Anzeige und `send_now`-Unterstuetzung bei SMTP.
- Backup-Restore-UX engine-aware fuer SQLite/MariaDB-Dateiformate.

### Quality Gate

- Vollstaendige Stability/Acceptance-Suite erfolgreich:
  - `28 passed`
- Suite umfasst Session/Security, User-Admin, Reports, Backup/Restore,
  Import, E-Mail, Bewegungen und Hybrid-Sync-E2E.

### Known Constraints

- Session-Store ist weiterhin in-memory (Token verfallen bei Prozessneustart).
- Sync v1 beinhaltet keine binaere Attachment-Dateisynchronisation.
- SMTP-Liveversand ist optional und per Environment konfigurierbar.

### Suggested Release Tag

- `v0.9.0-parity-hardening`
