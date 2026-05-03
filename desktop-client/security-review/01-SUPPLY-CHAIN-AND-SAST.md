# Phase 1: Supply Chain, Malware-Resilienz und SAST

## 1.1 Dependency Integrity

- `requirements.txt` nutzt **Versionsbereiche** (z. B. `PySide6>=6.7,<6.12`). Empfehlung: für Releases **exakte Pins** oder Lockfile (z. B. `pip-tools compile`) ergänzen, damit Builds und Audits bit-identisch reproduzierbar sind.
- PyPI-Integrität: Standard-`pip` mit Hash-Checking (`requirements.txt` mit `--hash=...`) optional für höchste Strenge.

## 1.2 Transitive Pakete und Typosquatting

- Nach `pip install` alle transitiven Abhängigkeiten in [baseline-freeze.txt](baseline-freeze.txt) prüfen; neue Major-Updates manuell reviewen.
- Neue Dependencies: Pflicht auf **Review** (Name, Maintainer, Download-Statistik, bekannte Supply-Chain-Zwischenfälle).

## 1.3 Bandit (Anwendungscode)

Scan-Umfang (absichtlich **ohne** `.security-review-venv`, **ohne** Tests, nur Projektcode + `ui` + `tools` + ausgewählte `backend/*.py`):

```text
core/ nd_hub.py db_manager.py security_manager.py user_management.py
apple_dashboard.py apple_theme.py icon_manager.py responsive_widgets.py
verfall_widget.py verfallmanager.py populate_nd_hub.py run_backend.py run_notfalldepots.py
backend/app.py backend/auth.py backend/config.py backend/database.py ui tools
```

Rohdaten: [bandit-report.json](bandit-report.json).

**Kurzauswertung:** Keine Bandit-Befunde mit Severity **HIGH**. Wesentliche Kategorien:

| Test-ID | Thema | Vorgehen |
|---------|--------|----------|
| B310 | `urllib.request.urlopen` in Sync- und Verbindungstest-Pfaden | Siehe [03-NETWORK-DATA-DISCLOSURE.md](03-NETWORK-DATA-DISCLOSURE.md) – URL-Schema und HTTPS-Erzwingung prüfen. |
| B608 | String-Konkatenation / f-Strings in SQL | Mit Whitelist/Parametrisierung abgleichen; Detail in [04-APPSEC-CODE-REVIEW.md](04-APPSEC-CODE-REVIEW.md). |
| Diverse LOW | z. B. `try/except: pass`, assert, subprocess | Fallweise bewerten; keine automatische Blockierung. |

## 1.4 JavaScript (`backend/web/app.js`)

- **`fetch`**: relative Pfade (`/auth/login`, `/auth/avatar`, generisch `apiFetch(path)`). Keine fest eingetragenen externen Analytics-URLs im kurzen Stichproben-Review.
- **`eval` / `new Function`**: in der Stichprobe nicht als produktiver Code-Pfad identifiziert; bei Erweiterungen der SPA erneut `grep` ausführen.

## 1.5 Windows-Build (`build_windows_exe.py`)

- Installiert **`requirements-dev.txt` in den Release-Build** (`pip install -r requirements-dev.txt`). Das zieht Test-/Lint-Tools in Produktions-Bundles – **Supply-Chain- und Angriffsflächenvergrößerung**; empfohlen: nur `requirements.txt` für Release-Builds.
- `subprocess.check_call` ohne `shell=True` (gut).
- PyInstaller: Keine Secrets im Skript; Bundle-Inhalt auf eingebettete Konfiguration prüfen.

## 1.6 Malware / Unerwarteter Code (manuell)

Empfohlene wiederkehrende Checks (nicht vollständig automatisiert):

- Suche nach `pickle.loads`, `marshal`, `ctypes`-Aufrufen mit User-Daten, `exec`/`eval` auf dynamischen Strings.
- Prüfung ungewöhnlicher Base64-Blobs oder verschleierter Strings in Commit-Diffs.
