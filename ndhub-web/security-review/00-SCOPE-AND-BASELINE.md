# Phase 0: Scope und Baseline

## Scope (in)

- **Frontend:** [`ndhub-web/frontend-react/`](../frontend-react/) (Quelle baut nach [`ndhub-web/backend/web/react/`](../backend/web/react/) gemäß [`vite.config.ts`](../frontend-react/vite.config.ts)).
- **Backend:** [`ndhub-web/backend/`](../backend/) inkl. gebündelter Web-Assets (`backend/web/`), Python-Einstieg [`run_backend.py`](../run_backend.py), [`requirements.txt`](../requirements.txt).
- **Betrieb:** [`docker-compose.yml`](../docker-compose.yml), [`Dockerfile`](../Dockerfile).

## Out of scope

- Vollständiger Pentest aller API-Routen (nur orientierende Code-/Konfig-Prüfung).
- MariaDB-Härtung jenseits der Compose-Datei (nur Compose-Hinweise).

## Baseline (Review-Lauf)

| Komponente | Methode | Datei |
|------------|---------|--------|
| npm, direkte Dependencies | `npm ls --depth=0` | [baseline-npm-ls.txt](baseline-npm-ls.txt) |
| npm advisories | `npm audit --json` (Auszug `vulnerabilities`) | [npm-audit-vulnerabilities.json](npm-audit-vulnerabilities.json) |
| Python (Backend) | venv `.audit-venv/` + `pip freeze` | [baseline-backend-freeze.txt](baseline-backend-freeze.txt) |

Python-Version: 3.12.x (lokal). Nach Änderung an `package-lock.json` oder `requirements.txt` Baseline und Scans erneuern.
