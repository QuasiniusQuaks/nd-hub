!!! warning "Archiviert"
    Diese Originaldatei ist archiviert. Der aktuelle, konsolidierte Stand befindet sich in der Enterprise-Dokumentation (siehe Hauptnavigation links).

# Release and Acceptance Report

Stand: 2026-04-23

Dieses Dokument fasst den finalen Umsetzungs- und Abnahmestand fuer `ndhub-web/backend` zusammen.

## Umgesetzte Bloecke

- Desktop/Web-Paritaetsmatrix aktualisiert und mit Ist-Stand synchronisiert
- Bewegungsverlauf gehaertet (Filter-Paritaet, Persistenz, CSV-Export, Attachment-UX)
- Import produktionsfaehig gehaertet (idempotent, Dry-Run, Fehlerklassifizierung)
- E-Mail-Flow gehaertet (Draft-Fallback + optionaler SMTP-Liveversand)
- Backup/Restore gehaertet (Restore-Limits, Formatvalidierung, bessere Audit-Daten)
- Report-Exporte gehaertet (Datumsvalidierung, kontextreiche Export-Dateinamen)
- User-Admin gehaertet (Selbstschutz, letzter aktiver Admin gegen Herabstufung/Deaktivierung)
- Session/Security-Acceptance-Checks abgeschlossen
- Hybrid-Sync v1 inkl. E2E-Tests abgeschlossen

## Finaler Regressionstatus

Erfolgreich ausgefuehrte Gesamtsuite:

```bash
PYTHONPATH="ndhub-web" ./.venv-sync-tests/bin/python -m pytest \
  ndhub-web/backend/tests/test_stability_acceptance.py \
  ndhub-web/backend/tests/test_user_admin_hardening.py \
  ndhub-web/backend/tests/test_report_export_hardening.py \
  ndhub-web/backend/tests/test_backup_restore_hardening.py \
  ndhub-web/backend/tests/test_import_idempotency.py \
  ndhub-web/backend/tests/test_email_delivery.py \
  ndhub-web/backend/tests/test_bewegungen_filters.py \
  ndhub-web/backend/tests/test_sync_ops_stats.py \
  ndhub-web/backend/tests/test_sync_hybrid_e2e.py
```

Ergebnis: **28 passed**

## Bewusste Grenzen (bekannt)

- Session-Store ist in-memory (`TokenStore`); Prozessneustart invalidiert aktive Tokens.
- Sync v1 synchronisiert keine binaeren Attachment-Dateien.
- SMTP-Liveversand ist optional und ueber Environment konfigurierbar (`draft` bleibt Fallback).
- MariaDB-Cutover ist umgesetzt, produktive Betriebs-Haertung unter Last bleibt weiterhin ein Betriebs-/Ops-Thema.

## Go-Live Checklist (empfohlen)

- Environment-Werte final setzen (`.env`, inkl. SMTP/Backup/DB-Engine)
- Falls MariaDB: Cutover-Runbook und Smoke-Checklist in Reihenfolge ausfuehren
- Einmal komplette Stability/Acceptance-Suite in Zielumgebung laufen lassen
- Backup-Restore Test in Zielumgebung verifizieren (inkl. Dateigroesse/Formatfehler)
- SMTP Testversand (oder bewusst `draft`-Mode dokumentieren)
- Monitoring/Alerting auf `401`, `403`, Restore-Fehler, Import-Fehlerquote und Sync-Fehler aktivieren

## Abnahmefazit

Der definierte Umsetzungsumfang (Parity, Hardening, Regression, Stability-Acceptance) ist abgeschlossen.
Das Backend ist fuer den naechsten produktionsnahen Rollout- bzw. Abnahmezyklus vorbereitet.
