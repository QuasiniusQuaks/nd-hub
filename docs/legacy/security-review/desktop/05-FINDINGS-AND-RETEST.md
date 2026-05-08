!!! warning "Archiviert"
    Diese Originaldatei ist archiviert. Der aktuelle, konsolidierte Stand befindet sich in der Enterprise-Dokumentation (siehe Hauptnavigation links).

# Phase 5: Priorisierte Befunde und Retest

## Executive Summary

Der Desktop Client hat **keine eingebaute Hersteller-Telemetrie**; relevante Datenabflüsse sind **Sync (HTTPS empfohlen, aktuell nicht erzwungen)**, **SMTP** und **Logs**. Supply-Chain: ein bekannter CVE in **pytest** (nur Dev, CVE-2025-71176) wurde durch Anhebung der unteren Grenze in `requirements-dev.txt` auf **pytest>=9.0.3** adressiert; `pip-audit` meldet danach keine bekannten Schwachstellen mehr für die Baseline. SAST (Bandit) meldet vor allem **B310** (urlopen) und **B608** (dynamisches SQL) – teils erwartete Muster, teils Verbesserungskandidaten.

## Findings (priorisiert)

| ID | Prio | Titel | OWASP / CWE | betroffene Stelle | Kurzbeschreibung | Empfehlung | Retest |
|----|------|-------|-------------|-------------------|------------------|------------|--------|
| F-01 | P2 | Kein erzwungenes HTTPS für Sync-Backend | ASVS V9, CWE-319 | `BackendSyncConfig`, `BackendApiClient`, UI-URL-Felder | `http://`-Backend möglich → MITM | Nur `https://` akzeptieren oder explizite HTTP-Warnung/Block | Manuell: HTTP-URL wird abgewiesen; Tests |
| F-02 | P3 | Dev-Pakete im Windows-Release-Build | ASVS V10 / Supply Chain | `build_windows_exe.py` | `requirements-dev.txt` wird mitinstalliert | Release nur `requirements.txt` | Diff am Skript; Größe des Bundles prüfen |
| F-03 | P3 | Secrets in Klartext (INI + SQLite) | ASVS V6, CWE-312 | `config_manager`, App-Settings | Token/SMTP-Passwort lesbar mit DB/INI-Zugriff | OS-Schutz, optional DPAPI/Keyring | Threat-Akzeptanz dokumentieren oder Verschlüsselung |
| F-04 | P3 | Dynamisches SQL (B608) | CWE-89 | `db_manager`, `backend/app.py`, `apple_dashboard`, … | Bandit-Flag; viele Pfade parametrisiert | Code-Review pro Fundstelle; Whitelist | Bandit-Warnungen reduzieren oder `# nosec` mit Begründung |
| F-05 | P4 (geschlossen) | pytest CVE (nur CI/Dev) | CVE-2025-71176 | `requirements-dev.txt` | Lokaler UNIX-Angriff auf pytest-Tempdirs | pytest >= 9.0.3 | Erledigt: `pip-audit` clean |
| F-06 | P3 | Initial-Admin via Umgebungsvariable | CWE-798 | `security_manager.py` | `ND_HUB_INITIAL_ADMIN_PASSWORD` | Nur Deployment-Pipeline, nicht dauerhaft | Prozesscheck |

## Retest-Checkliste (nach Fixes)

- [ ] `pip-audit` ohne neue High/Critical in Laufzeit-Dependencies.
- [ ] `bandit` erneut; Medium-Befunde für geänderte Dateien auf 0 oder dokumentiert.
- [ ] Integrationstests (`pytest tests/`) grün.
- [ ] Manuelle Smoke-Tests: Login, Sync-Testbutton, SMTP-Test (falls vorhanden).

## Referenzen

- Detail Supply/SAST: [01-SUPPLY-CHAIN-AND-SAST.md](01-SUPPLY-CHAIN-AND-SAST.md)
- CVE: [02-DEPENDENCY-CVE-MATRIX.md](02-DEPENDENCY-CVE-MATRIX.md)
- Netzwerk: [03-NETWORK-DATA-DISCLOSURE.md](03-NETWORK-DATA-DISCLOSURE.md)
- AppSec: [04-APPSEC-CODE-REVIEW.md](04-APPSEC-CODE-REVIEW.md)
