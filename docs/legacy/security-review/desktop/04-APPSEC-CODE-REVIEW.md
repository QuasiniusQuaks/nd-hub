!!! warning "Archiviert"
    Diese Originaldatei ist archiviert. Der aktuelle, konsolidierte Stand befindet sich in der Enterprise-Dokumentation (siehe Hauptnavigation links).

# Phase 4: Anwendungs-Security (Code-Review-Kurzfassung)

## Authentifizierung und Sitzungen

| Bereich | Befund |
|---------|--------|
| [security_manager.py](../security_manager.py) | bcrypt mit PBKDF2-Fallback; Account-Lockout und `failed_attempts`; Initial-Admin über Umgebungsvariable `ND_HUB_INITIAL_ADMIN_PASSWORD` – in **Produktionsumgebungen** nur kontrolliert setzen und nach Erstlogin rotieren. |
| [backend/auth.py](../backend/auth.py) | `TokenStore` in-memory, TTL, `secrets.token_urlsafe` – bei Prozessneustart alle Sessions weg; für verteiltes Deployment nicht geeignet ohne Persistenz/Sticky Sessions. |
| Login-UI | Siehe `ui/dialogs/login_dialog.py` – konsistent mit lokalem `SecurityManager` / Backend-Modus. |

## Autorisierung

| Bereich | Befund |
|---------|--------|
| [backend/app.py](../backend/app.py) | `require_permission` mit Abgleich gegen Rollen- und JSON-`permissions`; Admin-Bypass explizit. Manuelle Prüfung empfohlen, ob **jede** schreibende Route einen passenden Guard hat. |
| Depot-Scope | `user_depot_permissions` und Cross-Institution-Helfer in `SecurityManager` – alle neuen DB-Schreibpfade müssen dieselbe Policy nutzen. |

## Secrets at rest

| Speicherort | Inhalt | Risiko |
|-------------|--------|--------|
| [core/config_manager.py](../core/config_manager.py) → `settings.ini` | `backend_token`, Pfade | Klartext auf Benutzerprofil; OS-Rechte und Vollfestplattenverschlüsselung sind die Hauptschutzlinie. |
| SQLite (`db_manager` App-Settings) | SMTP-Passwort, Host, … | Gleiches Schutzniveau wie Datenbankdatei; keine zusätzliche Feldverschlüsselung im Review festgestellt. |

## SQL und dynamische Fragmente

- Bandit **B608** an mehreren Stellen: häufig **kontrollierte** Spaltenlisten (`UPDATE … SET` mit gebauter Liste aus festen Keys) oder Migrationen mit internen Namen – trotzdem **Whitelist-Disziplin** beibehalten.
- Kritische Kandidaten für manuelle Prüfung: nutzergesteuerte Sortier-/Filterstrings in [ui/pages/page_auswertungen.py](../ui/pages/page_auswertungen.py), dynamische Spalten in [db_manager.py](../db_manager.py) / [verfallmanager.py](../verfallmanager.py).

## Dateien und Import

- [ui/pages/page_import.py](../ui/pages/page_import.py): Nutzer wählt Dateien über Dialog; Parsing über pandas/openpyxl – Risiken: **große Dateien** (DoS), **Excel-Formeln** als Payload; Größenlimits und Validierung der Spalten prüfen/ergänzen.
- Backup/Export-Pfade: auf Path-Traversal und Schreibziele prüfen (nicht vollständig im Sprint enumeriert).

## Embedded Backend

- [run_backend.py](../run_backend.py): Host/Port über Umgebungsvariablen; Default typischerweise localhost – in Produktion nicht ohne TLS/Reverse-Proxy exponieren.
- Statische Dateien und Upload-Endpunkte in `backend/app.py`: bei Erweiterungen auf MIME-Sniffing und Größenlimits achten.
