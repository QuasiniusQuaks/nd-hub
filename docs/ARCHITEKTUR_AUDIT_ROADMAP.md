# Roadmap: Architektur-Audit Desktop-Client (2026-06-16)

Befund nach systematischer Inspektion von 22.622 LOC, 51 Python-Dateien.
Vollständiger Audit-Bericht im Conversation-Log (Quasinius × Caligula, 2026-06-16).

## Status

| Prio | Befund | Aufwand | Status | Branch |
|---|---|---|---|---|
| **P0** | #3 — Matrix-Lookup O(n²) → O(1) | 15 min | ✅ fertig | `perf/heatmap-matrix-lookup` |
| **P0** | #2 — Backend-Token im Klartext in settings.ini | 2 h | ✅ fertig | `security/sync-token-keyring` |
| **P0** | #1 — Sync blockiert UI-Thread | 4 h | ✅ fertig | `perf/sync-threadpool` |
| **P1** | #5 — 48 ungenutzte Imports | 30 min | 🟡 offen | `chore/remove-unused-imports` (geplant) |
| **P1** | #6 — 107× `except Exception` broad catches | 1 Tag | 🟡 offen | `refactor/typed-exception-handling` (geplant) |
| **P1** | #7 — Passwort-Timing-Attacke (`==` statt `hmac.compare_digest`) | 3 h | 🟡 offen | `security/password-timing-attack` (geplant) |
| **P1** | #8 — `@lru_cache` auf Instanz-Methoden riskant | 1 h | 🟡 offen | `refactor/cachetools-ttl-cache` (geplant) |
| **P1** | #9 — `time.sleep(2)` im Backup-Restore blockiert UI | 1 h | 🟡 offen | `perf/backup-async-worker` (geplant) |
| **P1** | #4 — 3 parallele SQLite-Connections auf dieselbe Datei | 1 Tag | 🟡 offen | `refactor/single-db-connection` (geplant) |
| **P2** | #10 — `Cache`-Klasse mit totem Feld | 10 min | 🟢 trivial | inline-Fix |
| **P2** | #11 — `QTimer.singleShot(0)` als Pseudo-Async | 4 h | 🟢 polish | in Auswertungen-Refactor |
| **P2** | #12 — Verfall-Manager mit Fallback auf nicht-existente Spalte | 1 h | 🟢 polish | `fix/verfall-schema-detect` |
| **P2** | #13 — `lru_cache`-Selbstdokumentation | 30 min | 🟢 trivial | inline-Kommentar |
| **P2** | #14 — `try/except TypeError: pass` auf `disconnect()` | 30 min | 🟢 trivial | inline-Fix |
| **P2** | #15 — Logging-Fehler geht via `print()` statt Logger | 30 min | 🟢 trivial | inline-Fix |

## Empfohlene Bearbeitungs-Reihenfolge (P1)

### Sprint 1 (1 Tag, isolierte Quick-Wins)

1. **#5 — Ungenutzte Imports entfernen** (30 min)
   - Risiko: niedrig (linter zeigt alle ungenutzten Stellen)
   - Top-Kandidaten: `QRunnable`, `QThreadPool`, `Signal`, `QObject`, `QDate`, `QFrame`, `QColor`, `QSize`
   - **Branch:** `chore/remove-unused-imports`
   - **Tests:** keine neuen erforderlich (linter-only)

2. **#10 — `Cache`-Klasse auflösen** (10 min)
   - Risiko: niedrig (Funktion ist eh nur Inline-Cache)
   - **Branch:** `chore/remove-dead-cache-class`
   - **Tests:** keine

3. **#14 — `disconnect()`-Anti-Pattern** (30 min)
   - Risiko: niedrig (nur Style-Fix)
   - **Branch:** `chore/qt-disconnect-cleanup`

### Sprint 2 (1 Tag, Security)

4. **#7 — Passwort-Timing-Attacke** (3 h)
   - `hmac.compare_digest()` für Hash-Vergleich
   - Login-Pfad in `QThreadPool` (PBKDF2 mit 600k Iterationen ist spürbar)
   - **Branch:** `security/password-timing-attack`
   - **Tests:** test_security_manager.py (Login-Dauer unter 100ms)

5. **#9 — Backup-Restore async** (1 h)
   - `time.sleep(2)` durch `QThreadPool`-Job + Progress-Signal
   - **Branch:** `perf/backup-async-worker`
   - **Tests:** Smoke-Test, dass UI während Restore responsive bleibt

### Sprint 3 (1-2 Tage, Architektur)

6. **#4 — SQLite-Connection-Konsolidierung** (1 Tag)
   - Verfall-Manager und Security-Manager als Methoden auf `Database`
   - **Risiko:** mittel — viele Stellen, die `self.conn` direkt nutzen
   - **Branch:** `refactor/single-db-connection`
   - **Tests:** Migration-Test, der vor/nach dem Refactor identische Ergebnisse liefert

7. **#8 — `cachetools` mit TTL** (1 h)
   - `@lru_cache` auf Instanz-Methoden → `cachetools.func.ttl_cache`
   - **Branch:** `refactor/cachetools-ttl-cache`
   - **Tests:** Cache-Invalidation-Tests

8. **#6 — Typed Exception Handling** (1 Tag)
   - Konkrete Exception-Klassen fangen, schmaler
   - Zentraler Decorator `@swallow_exceptions(log_level)`
   - **Risiko:** mittel (107 Stellen, manche sind echte Bug-Schutz-Schilde)
   - **Branch:** `refactor/typed-exception-handling`

### Sprint 4 (1 Tag, Polish)

9. **#11, #12, #13, #15 — Polish-Pakete** (zusammen 5-6 h)

## Strategie

- **Kein Big-Bang-Refactor.** Jeder Befund ist ein eigener Branch, eigener PR, eigene Review.
- **Reihenfolge: kleine, isolierte Fixes zuerst** (Sprint 1). Das schafft Reviewer-Vertrauen.
- **Architektur-Refactors (#4, #6) zuletzt**, wenn Security/Performance-Fixes bereits gemerged sind.
- **Bei jedem PR:** Vor dem Open CI-Status grün, Tests lokal grün, dann `gh pr create` mit PR-Template.

## Konventionen

- Branch-Naming: `type/kurz-beschreibung` (z. B. `perf/heatmap-matrix-lookup`)
- Commit-Messages: Conventional Commits (`fix:`, `perf:`, `security:`, `chore:`, `refactor:`)
- PR-Template: siehe `docs/PULL_REQUEST_TEMPLATE.md`
- Tests: Jeder PR muss neue Tests für die geänderte Logik mitbringen (Coverage-Maintenance)
