# Desktop Client: Konfiguration

Die Konfiguration des Desktop Clients erfolgt zentral ueber eine
`settings.ini` im Anwendungsdaten-Verzeichnis.

## Pfade

| Plattform | Datenverzeichnis | Konfigdatei |
|---|---|---|
| Windows | `%APPDATA%/ND-Hub/` | `%APPDATA%/ND-Hub/settings.ini` |
| Linux | `~/.ND-Hub/` | `~/.ND-Hub/settings.ini` |

Im selben Verzeichnis liegen auch:

- `nd_hub.db` (lokale SQLite-Datenbank)
- `logs/` (Log-Dateien)
- ggf. lokale Anhaenge und Backups (Pfad konfigurierbar).

## Wichtige Konfigurationsschluessel (`[General]`)

| Schluessel | Bedeutung | Standard |
|---|---|---|
| `database_path` | Pfad zur SQLite-Datenbank. | `~/.ND-Hub/nd_hub.db` |
| `log_level` | Logging-Level (`INFO`/`DEBUG`/`WARNING`). | `INFO` |
| `theme` | UI-Theme (`light`/`dark`). | `light` |
| `operating_mode` | Betriebsmodus (`local_only`/`hybrid_sync`/`remote_only`). | `local_only` |
| `backend_url` | URL der Webanwendung im Hybrid-/Remote-Modus. | leer |
| `backend_token` | Bearer-Token fuer Sync. | leer |
| `sync_interval_seconds` | Intervall fuer Auto-Sync. | `120` |
| `sync_cursor` | Letzter erfolgreicher Pull-Cursor. | `0` |

## Beispiel `settings.ini`

```ini
[General]
database_path = C:\Users\me\AppData\Roaming\ND-Hub\nd_hub.db
log_level = INFO
theme = light
operating_mode = hybrid_sync
backend_url = https://ndhub.example.org
backend_token = eyJhbGciOi...
sync_interval_seconds = 120
sync_cursor = 0
```

## Setup-Wizard

Beim ersten Start oeffnet sich der Setup-Wizard. Er fuehrt durch:

1. Datenpfad bestaetigen oder anpassen (`database_path`).
2. Auswahl des Betriebsmodus (lokal, hybrid, remote).
3. Hinterlegen von `backend_url` und `backend_token` (bei Hybrid/Remote).
4. Anlage des initialen Admin-Benutzers (mit erzwungenem Passwortwechsel
   bei erstem Login).
5. Optional: Setup-Schritte fuer Stammdaten (Depots, Praeparate, Kontakte)
   ueber gefuehrte Dialoge.

Der Wizard merkt sich Fortschritt und Entwurf in den Settings
(`setup_wizard_completed`, `setup_wizard_last_step`,
`setup_wizard_draft`).

## Sicherheitseinstellungen

| Bereich | Konfiguration |
|---|---|
| Passwortpolitik | erzwungener Passwortwechsel bei Erstanmeldung. |
| Account-Sperre | Sperre nach mehrfach falschen Logins, manuelle Freigabe durch Admin. |
| Audit | Aktiviert per Default fuer alle relevanten Aktionen. |

Details siehe [Security / AuthN & AuthZ](../security/01-authn-authz.md).

## SMTP-Einstellungen

Fuer den optionalen E-Mail-Versand werden SMTP-Parameter in der
Datenbank (`einstellungen`-Tabelle) verwaltet. Die Felder sind durch das
`DB`-Modul vordefiniert (`smtp_host`, `smtp_port`, `smtp_username`,
`smtp_password`, `smtp_use_tls`, `smtp_use_ssl`,
`smtp_from_address`, `smtp_from_name`).

## Logging

- Log-Verzeichnis: `~/.ND-Hub/logs/`
- Standard-Level: `INFO`. Fuer Detailanalysen ueber `settings.ini`
  auf `DEBUG` aenderbar.
- Bei kritischen Fehlern erscheint zusaetzlich der globale Fehlerdialog.
