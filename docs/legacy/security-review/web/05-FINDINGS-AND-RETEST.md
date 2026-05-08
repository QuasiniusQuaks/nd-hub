!!! warning "Archiviert"
    Diese Originaldatei ist archiviert. Der aktuelle, konsolidierte Stand befindet sich in der Enterprise-Dokumentation (siehe Hauptnavigation links).

# Phase 5: Befunde und Retest

## Kurzfassung

Die **ndhub-web**-SPA hat eine **kleine Dependency-Oberfläche**, speichert das **Bearer-Token in `localStorage`**, und lädt **OpenStreetMap-Kacheln** von externen Servern. **`npm audit`** meldet **moderate** Schwachstellen in **Vite/esbuild** (Schwerpunkt Dev-Server). **Docker Compose** bindet **MariaDB auf Host-Port 3306** – für Produktion typischerweise **zu weit offen**. Backend-Python: nach pip-Upgrade **keine** `pip-audit`-Treffer auf App-Pakete.

## Findings

| ID | Prio | Titel | OWASP / CWE | Ort | Beschreibung | Empfehlung | Retest |
|----|------|-------|-------------|-----|--------------|------------|--------|
| W-01 | P2 | MariaDB auf Host-Port exponiert | ASVS V9 / CWE-200 | `docker-compose.yml` | `3306:3306` erlaubt direkten DB-Zugriff vom Host/Netz | Port-Mapping entfernen oder `127.0.0.1:3306:3306` | Compose-Review, Portscan |
| W-02 | P3 | Vite + esbuild Advisory (moderate) | Supply chain / CWE-22, CWE-346 | `frontend-react` | Dev-Server und Vite-Tooling | Vite-Upgrade (6.4.2+ / 7+ / 8+) planen; Dev nicht öffentlich | `npm audit` clean oder dokumentiert |
| W-03 | P3 | Bearer-Token in localStorage | ASVS V3 / CWE-922 | `main.tsx` | XSS führt zu Session-Diebstahl | CSP + XSS-harte UI; optional HttpOnly-Cookie-Architektur | Pentest-XSS-Versuche |
| W-04 | P3 | OSM Drittanbieter-Requests | Privatsphäre | `main.tsx` Leaflet | IP/Kartenausschnitt an OSM | Hinweis in Privacy Policy; ggf. eigener Tile-Server | Policy-Review |
| W-05 | P3 | `.env` mit Secrets im Arbeitsbaum | CWE-798 | Repo-Root | Risiko bei Commit/Push | `.gitignore` (erledigt); Secrets rotieren falls je committed | `git log -- .env` |
| W-06 | P3 | Schwache Compose-Defaults | CWE-1393 | `docker-compose.yml` | Default-Passwörter | Starke Werte über Deployment-Secrets | Deploy-Checkliste |

## Retest-Checkliste

- [ ] `npm audit` nach Vite-Upgrade erneut ausführen.
- [ ] `npm run build` erfolgreich; gebündelte Assets unter `backend/web/react/`.
- [ ] `pip-audit` im Backend-venv mit aktuellem `pip`.
- [ ] Docker: MariaDB nicht unnötig nach außen; Produktions-`.env` ohne Default-Passwörter.
- [ ] Optional: OWASP ZAP Baseline gegen gestartete Web-App.

## Verweise

- Desktop-Client-Parallele (detaillierter Backend-SQL/Auth-Teil): `desktop-client/security-review/04-APPSEC-CODE-REVIEW.md` und `05-FINDINGS-AND-RETEST.md`.
