# Contributing Guide

Diese Richtlinie gilt für alle Code-Beiträge im `nd-hub`-Repository.

## Inline-Marker für Tech-Debt

Um technische Schulden nachvollziehbar zu halten, verwenden wir ausschließlich
die folgenden Kommentar-Marker:

| Marker | Bedeutung | Beispiel |
|--------|-----------|----------|
| `TODO(name)` | Geplante Arbeit, die noch aussteht | `# TODO(caligula): Login-Formular auf QLineEdit-Echo prüfen` |
| `FIXME(name)` | Bekannter Bug, der behoben werden muss | `# FIXME(quasinius): Race-Condition im Sync-Worker` |
| `HACK(name)` | Bewusstes Anti-Pattern mit Begründung | `# HACK(caligula): Workaround für PySide6-Qt-Version < 6.5` |
| `XXX(name)`  | Stelle, die nochmal geprüft werden sollte | `# XXX(quasinius): Ist diese Annahme unter Linux gültig?` |

Regeln:

1. **Immer einen Namen angeben.** `# TODO` ohne Verantwortlichen ist nicht erlaubt.
2. **Beschreibung auf den Punkt bringen.** Ein Satz reicht meist.
3. **Nicht als Ersatz für Issues verwenden.** Alles, was mehr als einen Tag Arbeit
   oder Team-Abstimmung braucht, gehört in ein GitHub-Issue (Label `tech-debt`).
4. **Inventar aktuell halten.** `tools/extract_todos.py` erzeugt `docs/TECH_DEBT.md`.

## Linting

Vor jedem Commit:

```bash
./tools/lint.sh
```

`ruff` muss mit 0 Fehlern durchlaufen.

## Branch-Namen

- `fix/issue-<nr>-<kurzbeschreibung>` für Bugfixes
- `feat/issue-<nr>-<kurzbeschreibung>` für Features
- `docs/<kurzbeschreibung>` für reine Dokumentation
