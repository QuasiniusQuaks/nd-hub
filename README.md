# ND-Hub

Zwei parallel gepflegte Entwicklungslinien:

| Ordner | Inhalt |
|--------|--------|
| [`desktop-client/`](desktop-client/) | PySide6-Desktopanwendung (ND-Hub Client), eingebettetes FastAPI-Backend für lokale Web-Hilfen. Einstieg: `desktop-client/README.md`. |
| [`ndhub-web/`](ndhub-web/) | Web-MVP (React/Vite + FastAPI), Docker und MariaDB-Pfad. Einstieg: `ndhub-web/backend/README.md`. |

## Schnellstart (lokal)

**Desktop-Client** (Python-Umgebung, Abhängigkeiten siehe `desktop-client/requirements.txt`):

```bash
cd desktop-client
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python run_notfalldepots.py
```

**ndhub-web** (Frontend bauen, Backend starten – Details in den jeweiligen READMEs):

```bash
cd ndhub-web/frontend-react && npm install && npm run build
cd ../.. && cd ndhub-web && python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python run_backend.py
```

## Historie

Dieses Repository wurde mit einer **orphan**-Wurzel neu aufgesetzt: Es enthält nur noch **`desktop-client`** und **`ndhub-web`**. Ältere Versionsordner (`V1`–`V39` usw.) und frühere Monorepo-Pfade liegen nur noch in Archiv-Branches bzw. Backups außerhalb dieses `main`.

Archiv-Zweig (lokal, vor Aufräumen): `archive/monorepo-pre-stage3` (Zeiger auf den letzten Stand vor Stufe 3).
