# Pull Request

## Zusammenfassung

<!-- Was wurde geändert? 1-3 Sätze. -->

## Typ der Änderung

- [ ] 🐛 Bugfix (non-breaking change, behebt ein Issue)
- [ ] ⚡ Performance-Verbesserung (non-breaking, ohne API-Änderung)
- [ ] 🔒 Security-Fix (non-breaking, schließt eine Lücke)
- [ ] ✨ Neues Feature (non-breaking, neue Funktionalität)
- [ ] 💥 Breaking Change (bestehende Funktionalität/API ändert sich)
- [ ] 📚 Doku/Refactor (keine funktionalen Änderungen)

## Bezug

<!-- Link zu Issue, Audit oder Befund. Beispiel: "Architektur-Audit 2026-06-16, Befund #3" -->

## Tests

- [ ] Bestehende Tests laufen weiterhin grün
- [ ] Neue Tests hinzugefügt (Liste mit Dateinamen)
- [ ] Manuelle Smoke-Tests durchgeführt

```bash
# Befehl zum Reproduzieren der Tests:
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/unit/ -v --no-header -p no:cacheprovider --no-cov
```

## Performance-Impact (falls relevant)

| Szenario | Vorher | Nachher | Speedup |
|---|---|---|---|
| Heatmap-Render, 50 Depots × 100 Präparate | 0.85s | 0.08s | ~10× |
| Sync-Cycle, 200 Outbox-Einträge | UI freeze 5–10s | non-blocking | n/a |
| Backend-Token-Lookup | settings.ini I/O | keyring (in-memory) | ~100× |

## Security-Impact (falls relevant)

- [ ] Kein Klartext-Secret mehr in Konfigurationsdateien
- [ ] Migration-Pfad für bestehende Secrets dokumentiert
- [ ] Token-Rotation dokumentiert (Dashboard → Key widerrufen → neu generieren)

## Backwards-Kompatibilität

- [ ] Keine API-Änderungen — bestehende Caller funktionieren unverändert
- [ ] Legacy-Migration automatisch (z. B. settings.ini → secure_token_store)
- [ ] Falls Breaking Change: Migrations-Guide im Beschreibungstext

## Checkliste

- [ ] Code folgt dem Stil des Repos (Ruff-Konfiguration)
- [ ] Self-review durchgeführt
- [ ] Kommentare zu nicht-offensichtlichen Stellen ergänzt
- [ ] Doku aktualisiert (mkdocs.yml, README, docstrings)
- [ ] Keine Debug-Prints oder commented-out Code übrig

## Screenshots (falls UI-Änderung)

<!-- Vor/Nach-Screenshot anhängen, falls relevant -->
