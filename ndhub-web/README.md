# ndhub-web

Webprodukt von ND-Hub (FastAPI + React/Vite + Docker).

- Backend: [`backend/README.md`](backend/README.md)
- Frontend: `frontend-react/`
- Compose: `docker-compose.yml` (Default-Engine: **MariaDB**)
- Enterprise-Doku: [`../docs/`](../docs/index.md)

## Schnellstart

```bash
# Backend (Dev, SQLite)
export ND_HUB_DB_ENGINE=sqlite
pip install -r requirements.txt
python run_backend.py

# oder Docker (MariaDB-Stack)
docker compose up -d --build
```

API-Einstieg: `backend/app.py` (Shim) → `backend/app_factory.create_app`.
Domain-Router: `../shared/routers/*`. Web-only: `backend/routers/{sync,institutions,desktop_sync_auth}.py`.
