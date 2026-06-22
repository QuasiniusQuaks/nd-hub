# Desktop Client: Build & Distribution

Der Desktop Client wird primaer als Quellcode (fuer Linux/macOS-Betrieb)
und als Windows-Installer (PyInstaller + Inno Setup) ausgeliefert.

## Aktuelle Version

- App-Version: **`0.5`**
- Build-Skript: `desktop-client/build_windows_exe.py`
- Inno-Setup-Skript: `desktop-client/setup_nd-hub-V05.iss`
- PyInstaller-Spec: `desktop-client/ND-Hub.spec`

## Build (Windows-Installer)

### Voraussetzungen

- Python 3.10/3.11 (64-bit)
- `requirements.txt` und `requirements-dev.txt` installiert
- Inno Setup 6+
- Optional: `icon.ico` im Projektordner

### Build-Schritte

```bash
cd desktop-client
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
python build_windows_exe.py
```

Das Skript:

1. installiert/aktualisiert `pyinstaller`,
2. aktualisiert die Abhaengigkeiten gemaess `requirements*.txt`,
3. ruft PyInstaller mit den Optionen
   `--noconfirm --windowed --name=ND-Hub --clean` auf,
4. legt das Resultat unter `dist/ND-Hub/` ab.

Anschliessend kann mit Inno Setup das Installer-Skript
`setup_nd-hub-V05.iss` kompiliert werden.

## Build (Linux/macOS-Quellcodebetrieb)

```bash
cd desktop-client
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python run_notfalldepots.py
```

`run_notfalldepots.py` aktiviert eine vorhandene `.venv/` automatisch
und reicht den Aufruf an `nd_hub.py` weiter.

## Distribution

| Kanal | Beschreibung |
|---|---|
| Windows-Installer | `setup_nd-hub-V05.exe` (aus Inno Setup), Empfehlung fuer Endkunden. |
| Quellcode (Repo) | Fuer technische Anwender und Pilot-Setups. |
| Hybrid-Bereitstellung | Desktop pro Arbeitsplatz + Web-Backend zentral. |

## Versionierung

- Versionsnummer wird zentral im Build-Skript (`APP_VERSION`) und im
  Inno-Setup-Skript gefuehrt.
- README-Header und Hauptdokumentation werden bei jedem Release auf die
  aktuelle Version angepasst.

## Pruefliste vor Release

1. Tests gruen (`pytest`, ggf. Performance-Tests separat).
2. Lint und Format gruen (`ruff check` / `ruff format --check`).
3. Security-Scans aktualisiert (`bandit`, `pip-audit`).
4. Versionsnummer in `build_windows_exe.py`, `setup_nd-hub-V05.iss` und
   in der Doku konsistent.
5. Smoke-Test des Installers in einer sauberen Windows-Umgebung.
6. Restore-Test eines bestehenden Backups in der neuen Version.
