# Webanwendung: Frontend

Das Frontend besteht aus zwei Schichten:

1. **Legacy Web-MVP**: statisches HTML/CSS/JS (`backend/web/`).
2. **React/Vite Frontend (Islands-Strategie)**: progressives Aufruesten
   ueber Vite-Builds (`frontend-react/`).

## Stack

| Komponente | Version |
|---|---|
| Vite | 5.x |
| React | 18.3 |
| TypeScript | 5.6 |
| Leaflet | 1.9 (Karten / Geo) |

## Build-Pfad

```bash
cd ndhub-web/frontend-react
npm install
npm run build
```

Der Build legt die Assets unter:

- `../backend/web/react/ndhub-react.js`
- `../backend/web/react/ndhub-react.css`

Der ND-Hub-Backend-Container liefert sowohl die Legacy- als auch die
React-Assets aus.

## Entwicklung

```bash
cd ndhub-web/frontend-react
npm run dev
```

Vite stellt einen Dev-Server bereit. Fuer lokale Tests gegen das
Backend wird zusaetzlich `python run_backend.py` benoetigt.

## Funktionsbereiche im Browser

- Login + Session
- Dashboard (KPIs)
- Depots / Praeparate / Zuordnungen / Kontakte
- Bewegungen + Verlauf + CSV-Export
- Verfall-Uebersicht und Notifications
- E-Mail Drafts und Versandstatus
- Reports (Bestand, Bewegungen, Ranking, Matrix, Verfall)
- Backup/Restore (Admin)
- Karten-Ansicht (`/map/institutions`) bei aktivem
  `ND_HUB_FEATURE_INSTITUTION_MAP`

## UX-Hinweise

- Persistente Filterauswahl pro Benutzer (z. B. Verlauf).
- Engine-aware Backup/Restore-UI (akzeptiert `*.mariadb.json` oder
  `*.json`).
- Klare Statusanzeigen fuer SMTP-Liveversand vs. Draft-Modus.

## Browser-Empfehlung

- Aktuelle Versionen von Chrome, Edge oder Firefox.
- Mobile/Tablet ist durch das responsive Layout grundsaetzlich nutzbar,
  aber fuer Hauptarbeitsplatz nicht primaer optimiert.
