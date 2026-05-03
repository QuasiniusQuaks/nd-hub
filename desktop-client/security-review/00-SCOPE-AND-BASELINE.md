# Phase 0: Scope und Baseline

## Scope (in)

- Gesamter Ordner **desktop-client** inklusive eingebettetem FastAPI-Backend unter `backend/` (Python) und statischer SPA unter `backend/web/app.js`.
- **Out of scope** für dieses Artefakt-Paket: Betriebssystem-Härtung, Remote-Infrastruktur eines separaten Sync-Servers (nur Client-seitige Annahmen), rechtliche DSGVO-Folgenabschätzung.

## Reproduzierbare Audit-Baseline

| Feld | Wert (Stand Review-Lauf) |
|------|---------------------------|
| Host-OS | Linux x86_64 (Review-Umgebung) |
| Python | 3.12.x (siehe lokales `python3 --version`) |
| Installationsmethode | Frisches venv `.security-review-venv/` im Desktop-Client-Ordner |
| Abhängigkeiten | `requirements.txt` + `requirements-dev.txt` |

Die **konkret aufgelösten Versionen** stehen in [baseline-freeze.txt](baseline-freeze.txt). Ohne Freeze können sich durch obere Versionsgrenzen in `requirements.txt` andere transitive Pakete ergeben; für formale Audits oder Retests immer aus diesem Freeze oder einem frischen `pip freeze` nach identischer Resolver-Umgebung arbeiten.

## Hinweise

- `pywin32` wird auf Nicht-Windows-Plattformen nicht installiert; Windows-Builds separat mit gleicher Prozedur prüfen.
- Die Baseline enthält **Dev-Pakete** (pytest, bandit, pip-audit). Die **Produktions-Laufzeit** installiert üblicherweise nur `requirements.txt`; CVEs nur in Dev-Paketen sind im Bericht entsprechend eingestuft.
