# ND-Hub – Enterprise Edition v0.39

ND-Hub ist eine professionelle Apotheken-Verwaltungssoftware, die für höchste Stabilität, Sicherheit und Benutzerfreundlichkeit entwickelt wurde. Diese Dokumentation beschreibt die Enterprise-Hardening-Maßnahmen und die Software-Architektur.

## 🚀 Key Features (Enterprise Grade)

- **Modern UI**: Apple-inspiriertes Design mit dynamischem Dark Mode und flüssigen Animationen.
- **Robustes Path-Management**: Verwendet den `ConfigManager`, um Daten (`APPDATA`) strikt von Programmdateien zu trennen. Kompatibel mit Windows Restricted Environments.
- **Globales Error Handling**: Unbehandelte Exceptions werden abgefangen, geloggt und in einem professionellen Dialog angezeigt, statt die App kommentarlos zu beenden.
- **Sicherheits-Architektur**: Integrierter `SecurityManager` mit `bcrypt`-Hashing, Account-Sperrung und erzwungenem Passwortwechsel.
- **Asset-Modularisierung**: Große Binär-Assets (Logos) sind in separate Module ausgelagert, um die Code-Wartbarkeit zu erhöhen.
- **Datenbank-Performance**: SQLite mit WAL-Mode und optimierten PRAGMA-Einstellungen für reibungslose Zugriffe.

## 📂 Projektstruktur

```text
V36/
├── core/                   # Core Logik & Infrastruktur
│   ├── config_manager.py   # Globales Pfad- & Einstellungsmanagement
│   ├── error_handler.py    # Globaler Exception Hook & Dialoge
│   └── security_manager.py # Authentifizierung & Kryptographie
├── ui/                     # Benutzeroberfläche
│   ├── resources.py        # Base64 Assets
│   ├── pages/              # Modulare UI-Seiten
│   └── dialogs/            # Modale Dialoge
├── nd_hub.py               # Haupteinstiegspunkt & Orchestrator
├── db_manager.py           # Datenbank-Abstraktionsschicht
└── build_windows_exe.py    # PyInstaller Build-Script
```

## 🛠 Installation & Entwicklung

### Abhängigkeiten installieren
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Entwicklungs-Tooling (Lint, Tests, Security)
```bash
pip install -r requirements-dev.txt
ruff check .
ruff format --check .
pytest
```

CI erzwingt zusätzlich:
- Lint + Format-Check auf Linux und Windows (Python 3.10/3.11)
- Test-Coverage mit Mindestschwelle (aktuell 30 % für Kernmodule)
- Security-Scan (`bandit`) und Dependency-Audit (`pip-audit`)

Performance-Tests laufen separat und optional:
- Lokal: `pytest -m performance --no-cov`
- GitHub Actions: manueller Workflow `Performance Tests` per `workflow_dispatch`

### Anwendung starten
```bash
python nd_hub.py
```

## 🔒 Konfiguration

Die Konfiguration wird zentral in der `settings.ini` im Anwendungsdaten-Verzeichnis verwaltet:
- **Windows**: `%APPDATA%/ND-Hub/settings.ini`
- **Linux**: `~/.ND-Hub/settings.ini`

Dort können Administratoren den Pfad zur Netzwerk-Datenbank oder das Log-Level anpassen.

---
© 2025 ND-Hub Enterprise Team. Alle Rechte vorbehalten.
