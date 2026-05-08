!!! warning "Archiviert"
    Diese Originaldatei ist archiviert. Der aktuelle, konsolidierte Stand befindet sich in der Enterprise-Dokumentation (siehe Hauptnavigation links).

# ND-Hub Desktop Client – Security Review Artefakte

Dieses Verzeichnis enthält die **Durchführung** des Security-Review-Plans (Baseline, Scans, Inventare, Befunde). Die Plan-Datei in `.cursor/plans/` wird nicht versioniert bzw. nicht hier gespiegelt.

## Inhalt

| Datei / Artefakt | Zweck |
|------------------|--------|
| [00-SCOPE-AND-BASELINE.md](00-SCOPE-AND-BASELINE.md) | Scope, reproduzierbare Umgebung, `pip freeze` |
| [baseline-freeze.txt](baseline-freeze.txt) | Konkrete Paketversionen (generiert) |
| [pip-audit-report.txt](pip-audit-report.txt) | Rohausgabe `pip-audit` |
| [bandit-report.json](bandit-report.json) | SAST (nur Anwendungscode, keine venv) |
| [01-SUPPLY-CHAIN-AND-SAST.md](01-SUPPLY-CHAIN-AND-SAST.md) | Malware/Supply-Chain, Bandit-Auswertung, JS, Build |
| [02-DEPENDENCY-CVE-MATRIX.md](02-DEPENDENCY-CVE-MATRIX.md) | CVE-Matrix, Upgrades, EOL-Hinweise |
| [03-NETWORK-DATA-DISCLOSURE.md](03-NETWORK-DATA-DISCLOSURE.md) | Netzwerk, „Telemetrie“, Logging |
| [04-APPSEC-CODE-REVIEW.md](04-APPSEC-CODE-REVIEW.md) | AuthN/Z, Secrets, SQL/Import, Backend |
| [05-FINDINGS-AND-RETEST.md](05-FINDINGS-AND-RETEST.md) | Priorisierte Befunde, OWASP/CWE, Retest |

## Erneut ausführen

```bash
cd desktop-client
python3 -m venv .security-review-venv
. .security-review-venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pip freeze > security-review/baseline-freeze.txt
pip-audit --desc | tee security-review/pip-audit-report.txt
bandit -r core nd_hub.py db_manager.py security_manager.py user_management.py apple_dashboard.py apple_theme.py icon_manager.py responsive_widgets.py verfall_widget.py verfallmanager.py populate_nd_hub.py run_backend.py run_notfalldepots.py backend/app.py backend/auth.py backend/config.py backend/database.py ui tools -f json -o security-review/bandit-report.json -q
```

Python-Version und OS bei Änderungen dokumentieren; bei Release erneut `pip-audit` und ggf. `pip freeze` aktualisieren.
