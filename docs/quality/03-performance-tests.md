# Performance-Tests

Performance-Tests laufen separat vom regulaeren Quality-Gate, um die
Standard-CI nicht zu verlangsamen und gezielte Aussagen zu Lasten und
Skalierung zu erlauben.

## Lokale Ausfuehrung (Desktop)

```bash
cd desktop-client
pytest -m performance --no-cov
```

`-m performance` filtert die mit dem Marker gekennzeichneten Tests;
`--no-cov` deaktiviert das Coverage-Plugin, das fuer Lasttests
ungeeignet ist.

## CI

- Performance-Tests sind in einem **manuell ausgeloesten** Workflow
  unter GitHub Actions hinterlegt (`Performance Tests`).
- Sie laufen nicht bei jedem Push und nicht bei jedem PR.

## Backend / API-Performance

- Reports und Verlaufsfilter sind die hochfrequenten, kritischen
  Pfade.
- Empfohlene Pruefungen vor groesseren Releases:
    - `GET /bewegungen` mit verschiedenen Filterkombinationen,
    - `GET /reports/*` ueber realistische Zeitraeume,
    - `GET /audit-logs` mit Filterkombinationen.
- Indizes pruefen, wenn p95-Antworten in MariaDB hochlaufen.

## Skalierungs-Empfehlungen

- Volumegroessen pro Volume regelmaessig beobachten
  (`ndhub_data`, `ndhub_uploads`, `ndhub_backups`,
  `ndhub_mariadb_data`).
- Fuer hohe Mehrnutzerlast horizontalen Ausbau planen, dabei externen
  Session-Store fuer Tokens vorsehen.
- Reports auf realistischen Zeitraeumen schneiden, statt grosse
  unbeschraenkte Abfragen zuzulassen.

## Beobachtbarkeit

- Antwortzeiten pro Endpunkt im Reverse Proxy / Monitoring
  beobachten.
- Backups: Dauer und Groesse pro Auto-Backup-Lauf erfassen.
- Sync: Push/Pull-Dauern, abgelehnte/konflikthafte Changes.
