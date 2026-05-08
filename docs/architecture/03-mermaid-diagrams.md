# Diagramme

Diese Seite buendelt die wichtigsten Mermaid-Diagramme zu ND-Hub.

## Deployment-Topologie (Web)

```mermaid
flowchart LR
    user["User Browser"] --> proxy["Reverse Proxy / TLS"]
    proxy --> ndhubWeb["ndhub-web Container (FastAPI)"]
    ndhubWeb --> mariadb["mariadb Container (MariaDB 11.4)"]
    ndhubWeb --> volData["Volume ndhub_data"]
    ndhubWeb --> volUploads["Volume ndhub_uploads"]
    ndhubWeb --> volBackups["Volume ndhub_backups"]
    mariadb --> volMaria["Volume ndhub_mariadb_data"]
```

## Login-Flow

```mermaid
sequenceDiagram
    participant U as User
    participant FE as Frontend (Web/Desktop)
    participant API as FastAPI /auth/login
    participant SEC as SecurityManager
    participant DB as Repository

    U->>FE: Username + Passwort
    FE->>API: POST /auth/login
    API->>SEC: verify_password
    SEC->>DB: read user + hash
    DB-->>SEC: user record
    SEC-->>API: ok / locked / invalid
    API-->>FE: bearer token + me-info
    FE-->>U: Login erfolgreich
```

## Bewegung mit PDF-Anhang

```mermaid
sequenceDiagram
    participant U as Fachanwender
    participant FE as Frontend
    participant API as FastAPI
    participant DB as Repository
    participant FS as Attachment Storage

    U->>FE: Bewegung erfassen
    FE->>API: POST /bewegungen
    API->>DB: insert bewegung
    DB-->>API: id
    API-->>FE: bewegung created
    U->>FE: PDF anhaengen
    FE->>API: POST /bewegungen/{id}/attachment
    API->>FS: speichere datei
    API->>DB: update datei_* metadata
    API-->>FE: attachment ok
```

## Hybrid-Sync v1

```mermaid
sequenceDiagram
    participant DC as Desktop Client (hybrid_sync)
    participant SQ as Lokale SQLite + Outbox
    participant API as ndhub-web

    DC->>SQ: lokale Schreib-/Leseoperationen
    Note over DC,SQ: Bei Offline weiterhin nutzbar
    DC->>API: POST /sync/push (batch_id)
    API-->>DC: accepted / rejected / conflicts
    DC->>API: POST /sync/pull (cursor)
    API-->>DC: changes + next_cursor
    DC->>SQ: Aenderungen anwenden
```

## MariaDB-Cutover

```mermaid
flowchart TD
    backupSqlite["1. SQLite-Backup erstellen"] --> migrate["2. python -m backend.tools.migrate_sqlite_to_mariadb"]
    migrate --> compare["3. Row-Count- und Spotchecks"]
    compare -->|ok| switch["4. ND_HUB_DB_ENGINE=mariadb setzen"]
    switch --> smoke["5. Smoke-Test (Login, CRUD, Reports, Backup)"]
    smoke -->|ok| dual["6. ND_HUB_DUAL_WRITE_SQLITE=0 (final)"]
    smoke -->|fail| rollback["Rollback: ND_HUB_DB_ENGINE=sqlite"]
```

## Berechtigungen / Rollen

```mermaid
flowchart LR
    user["User"] --> role["Role: admin | user"]
    role --> coreRights["Permissions: depots.write / praeparate.write / kontakte.write / users.manage / audit.view / backup.manage"]
    user --> depotRights["user_depot_permissions: per Depot can_read/can_write"]
```

## Container-Stack

```mermaid
flowchart LR
    subgraph composeStack["docker compose"]
        ndhubWeb["ndhub-web (FastAPI)\nPort 8000"]
        mariadb["mariadb 11.4\nPort 3306"]
    end
    ndhubWeb -->|depends_on healthy| mariadb
    composeStack --> volumes[(Persistente Volumes)]
```
