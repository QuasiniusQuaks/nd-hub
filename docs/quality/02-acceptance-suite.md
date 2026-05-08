# Acceptance-Suite

Die Acceptance-Suite ist das **Quality-Gate** fuer Releases der
Webanwendung. Sie buendelt funktionale, Sicherheits-, Audit- und
Sync-Pruefungen.

## Statusstand

- Resultat: **`28 passed`** (Stand letzter Sprint-Abschluss).
- Laufzeit: ca. 6 s in einer typischen Entwicklungsumgebung.
- Quality-Gate: ohne Fehler/Warnungen. Bei roten Tests **kein** Release.

## Inhalte der Suite

- `test_stability_acceptance.py`
    - Health/Login,
    - Verfall-Notifications-Polling,
    - Onboarding-Status,
    - Backup-/Restore-Mismatch-Erkennung,
    - Import-Idempotenz und Dry-Run,
    - Konsistenz Verfall <-> Bewegungen.
- `test_user_admin_hardening.py`
    - Admin/User-Listing,
    - Reset-Password-Mindestlaenge,
    - Self-Toggle-Schutz,
    - Last-Admin-Schutz,
    - Forbidden-Behavior fuer Non-Admins.
- `test_report_export_hardening.py`
    - Datumsvalidierung,
    - PPTX-Export,
    - Verfall-CSV mit Datumsbereich.
- `test_backup_restore_hardening.py`
    - Pre-Restore-Snapshot,
    - Format-Mismatch,
    - Groessen-Limits.
- `test_import_idempotency.py`
    - Re-Submit gleicher Fingerprint,
    - Fehlerklassifizierung,
    - Excel-Vorlage.
- `test_email_delivery.py`
    - SMTP-Liveversand-Statusmodelle,
    - Recipients-Preview, Drafts.
- `test_bewegungen_filters.py`
    - Filterkombinationen fuer Verlauf,
    - CSV-Export-Konsistenz.
- `test_sync_ops_stats.py`
    - Permissions fuer `/sync/ops/stats`.
- `test_sync_hybrid_e2e.py`
    - Push/Pull-Endpunkte mit reale Hybrid-Sync-Konstellation.

## Bekannte Grenzen (Hinweise)

- Frontend-E2E (Browser) ist nicht im Scope der Backend-Suite.
- In-memory Token-Store wird nicht ueber Prozessgrenzen getestet.
- Sync v1 transportiert keine binaeren Attachment-Dateien.

## Empfohlener Release-Schritt

1. Lint und Format gruen.
2. Acceptance-Suite gruen (`28 passed`).
3. Performance-Tests bei Bedarf separat ausfuehren.
4. Smoke-Test gegen den Container-Stack.
5. Release-Notes auf dem aktuellen Stand
   ([Projekt / Release Notes](../project/03-release-notes.md)).

## Re-Run Anleitung

```bash
PYTHONPATH="ndhub-web" \
  ./.venv-sync-tests/bin/python -m pytest \
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

Erwartetes Ergebnis: `28 passed`.
