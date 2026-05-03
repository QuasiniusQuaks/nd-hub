# ND-Hub Webanwendung – Security Review (gleiche Kriterien wie Desktop Client)

Struktur analog zum Review unter `desktop-client/security-review/`: **Scope/Baseline**, **Supply Chain / SAST**, **Abhängigkeiten (CVE)**, **Netzwerk & Datenabflüsse**, **AppSec**, **Befunde & Retest**.

## Komponenten

| Teil | Technologie | Artefakte |
|------|-------------|-----------|
| Frontend | Vite 5 + React 18 + TypeScript, Leaflet ([`frontend-react/`](../frontend-react/)) | `npm audit`, [baseline-npm-ls.txt](baseline-npm-ls.txt), [npm-audit-vulnerabilities.json](npm-audit-vulnerabilities.json) |
| Backend | FastAPI + uvicorn (Kopie/Erweiterung unter [`backend/`](../backend/), siehe [`requirements.txt`](../requirements.txt)) | [baseline-backend-freeze.txt](baseline-backend-freeze.txt), [pip-audit-backend.txt](pip-audit-backend.txt) |
| Deployment | Docker Compose + MariaDB ([`docker-compose.yml`](../docker-compose.yml)) | siehe [04-APPSEC-AND-OPS.md](04-APPSEC-AND-OPS.md) |

## Erneut ausführen

**Frontend** (im Ordner `ndhub-web/frontend-react`):

```bash
npm install
npm audit --json > ../security-review/npm-audit-full.json
npm ls --depth=0 > ../security-review/baseline-npm-ls.txt
```

**Backend** (im Ordner `ndhub-web`):

```bash
python3 -m venv .audit-venv
. .audit-venv/bin/activate
pip install -U pip pip-audit
pip install -r requirements.txt
export PIPAPI_PYTHON_LOCATION="$(pwd)/.audit-venv/bin/python3"
pip-audit --desc | tee security-review/pip-audit-backend.txt
pip freeze > security-review/baseline-backend-freeze.txt
```

## Index

- [00-SCOPE-AND-BASELINE.md](00-SCOPE-AND-BASELINE.md)
- [01-SUPPLY-CHAIN-AND-SAST.md](01-SUPPLY-CHAIN-AND-SAST.md)
- [02-DEPENDENCY-CVE-MATRIX.md](02-DEPENDENCY-CVE-MATRIX.md)
- [03-NETWORK-DATA-DISCLOSURE.md](03-NETWORK-DATA-DISCLOSURE.md)
- [04-APPSEC-AND-OPS.md](04-APPSEC-AND-OPS.md)
- [05-FINDINGS-AND-RETEST.md](05-FINDINGS-AND-RETEST.md)
