# API Reference

Diese Sektion listet alle relevanten REST-Endpunkte des `ndhub-web`
Backends, das Fehlerschema sowie die Konventionen fuer Pagination,
Filterung und Idempotenz.

## Inhalt

- [REST-Endpunkte](01-rest-endpoints.md)
- [Fehlerbehandlung](02-error-model.md)
- [Pagination & Filter](03-pagination-filtering.md)

!!! tip "Authentifizierung"
    Mit Ausnahme von `GET /health` und `POST /auth/login` setzt jeder
    Endpunkt einen gueltigen Bearer-Token voraus. Schreibendpunkte fuer
    Stammdaten erwarten zusaetzlich Adminrechte oder die jeweiligen
    Permissions.
