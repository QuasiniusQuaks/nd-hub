# Desktop Client: Ueberblick

## Steckbrief

| Eigenschaft | Wert |
|---|---|
| Sprache | Python 3.10+ (Tests laufen auf 3.10/3.11) |
| UI-Framework | PySide6 (Qt 6) |
| Datenbank lokal | SQLite (WAL-Mode, optimierte PRAGMAs) |
| Eingebettetes Backend | FastAPI (lokal, optional) |
| Sicherheit | bcrypt, Account-Sperre, erzwungener Passwortwechsel |
| Build | PyInstaller + Inno Setup (Windows) |
| Lieferform | Quellcode oder Windows-Installer |

## Hauptmerkmale

- **Modernes UI** im Apple-inspirierten Design mit dynamischem Dark Mode.
- **Robustes Path-Management** ueber den `ConfigManager`. Daten und Code
  sind strikt getrennt.
- **Globales Error-Handling** mit professionellem Fehlerdialog statt
  abrupten Anwendungsabbruechen.
- **Setup-Wizard** fuer eine gefuehrte Erstkonfiguration.
- **Hybrid-Modus** ueber Sync-Service, alternativ vollstaendiger
  Local-only-Betrieb ohne Backend.
- **Audit-Tab** und Backup-/Restore-Funktionen direkt in der UI.

## Architektur in Kurzform

```mermaid
flowchart LR
    subgraph desktopApp["Desktop Client"]
        ndhub["nd_hub.py (MainWindow)"]
        ui["ui/pages + ui/dialogs"]
        core["core/config_manager + error_handler"]
        sync["core/sync_service + data_access_layer"]
        dbm["db_manager.py"]
    end
    subgraph local["Lokale Persistenz"]
        sqliteFile["SQLite (~/.ND-Hub)"]
        attachments["lokale Anhaenge"]
        settings["settings.ini"]
    end
    subgraph remote["Optional: Web-Backend"]
        api["ndhub-web FastAPI"]
    end
    ui --> ndhub
    ndhub --> core
    core --> dbm
    dbm --> sqliteFile
    ndhub --> sync
    sync --> api
    core --> settings
    ui --> attachments
```

## Betriebsmodi

| Modus | Beschreibung | Wann sinnvoll? |
|---|---|---|
| `local_only` | Vollstaendig lokal, keine Backend-Abhaengigkeit. | Einzelarbeitsplaetze ohne zentrale Web-Instanz. |
| `hybrid_sync` | Lokal-zuerst, synchronisiert mit Web-Backend, wenn erreichbar. | Standorte mit zentraler Plattform und Offline-Anforderung. |
| `remote_only` | Nur Online; Schreibzugriff erfordert Backend. | Sonderfaelle ohne Offline-Bedarf. |

Details zur Sync-Mechanik siehe
[Migration & Sync / Hybrid-Sync](../migration-and-sync/03-hybrid-sync.md).

## Beziehung zur Webanwendung

Der Desktop Client teilt mit `ndhub-web` denselben fachlichen Kern.
Wesentliche Aenderungen an Domaenenregeln werden serverseitig gehalten.
Eine vollstaendige, fortgeschriebene Funktionsparitaet siehe
[Projekt / Parity-Matrix](../project/02-parity-matrix.md).
