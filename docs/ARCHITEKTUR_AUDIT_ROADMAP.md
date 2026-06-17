# Roadmap: Architektur-Audit (Wellen 1 + 2)

## Welle 1 — Architektur-Audit Desktop-Client (2026-06-16)

Befund nach systematischer Inspektion von 22.622 LOC, 51 Python-Dateien.
Vollständiger Audit-Bericht im Conversation-Log (Quasinius × Caligula, 2026-06-16).

### Status (Welle 1)

| Prio | Befund | Aufwand | Status | Branch / PR |
|---|---|---|---|---|
| **P0** | #1 — SQLi / SSRF / Secrets / Dependencies | 4h | ✅ fertig | PR #1 |
| **P0** | #2 — Matrix-Lookup O(n²) → O(1) | 15 min | ✅ fertig | PR #20 |
| **P0** | #3 — Backend-Token im Klartext in settings.ini | 2h | ✅ fertig | PR #21 |
| **P0** | #4 — Sync blockiert UI-Thread | 4h | ✅ fertig | PR #22 |
| **P1** | #5 — Ungenutzte Imports | 30 min | ✅ fertig | PR #23 |
| **P1** | #6 — Passwort-Timing-Attacke (Desktop) | 3h | ✅ fertig | PR #24 |
| **P1** | #7 — Backup-Restore async | 1h | ✅ fertig | PR #27 |
| **P1** | #8 — `Cache`-Klasse mit totem Feld | 10 min | ✅ fertig | PR #23 |
| **P1** | #10 — Verfall-Manager Schema-Fallback | 1h | ✅ fertig | PR #24 |
| **P1** | #16 — 107× `except Exception` broad catches | 1 Tag | ✅ fertig | PR #25 |
| **P1** | #17 — `lru_cache` auf Instanz-Methoden | 1h | ✅ fertig (Doku + Helper) | PR #25 |
| **P1** | #18 — 3 parallele SQLite-Connections | 1 Tag | ✅ fertig | PR #28 |
| **P2** | #9 — `QTimer.singleShot(0)` Pseudo-Async | 4h | ✅ fertig (durch Sync-Worker) | PR #22 |
| **P2** | #11 — `lru_cache` Selbstdokumentation | 30 min | ✅ fertig | PR #25 |
| **P2** | #12 — `disconnect()`-Anti-Pattern | 30 min | ✅ fertig | PR #23 |
| **P2** | #13 — Logging-Setup via `print()` | 30 min | ✅ fertig | PR #23 |

**Welle 1: 11 PRs gemerged, 15 Issues closed in 4 Sessions.**

---

## Welle 2 — Tiefen-Audit Web-Security + Threading + Dependencies (2026-06-17)

Befund nach systematischer Inspektion des **Web-Backends** (4575 LOC `app.py`, 883 LOC `security_manager.py`) und Threading-Lücken im Desktop-Client. Tools: `ruff`, `bandit`, `ast.parse`.

### Status (Welle 2)

| Prio | Issue | Befund | Aufwand | Status |
|---|---|---|---|---|
| **P0** | [#29](https://github.com/QuasiniusQuaks/nd-hub/issues/29) | Timing-Attacke auf Web `verify_password` (== statt hmac.compare_digest) | 1-2h | 🟡 offen |
| **P0** | [#30](https://github.com/QuasiniusQuaks/nd-hub/issues/30) | SyntaxError in 2 Web-Test-Dateien (`gitleaks:allow,` Bug) | 30min | 🟡 offen |
| **P0** | [#31](https://github.com/QuasiniusQuaks/nd-hub/issues/31) | Kein CORS / Security-Header / TrustedHost im FastAPI | 2-3h | 🟡 offen |
| **P0** | [#32](https://github.com/QuasiniusQuaks/nd-hub/issues/32) | Kein Rate-Limit auf `/auth/login` (Brute-Force) | 3-4h | 🟡 offen |
| **P1** | [#33](https://github.com/QuasiniusQuaks/nd-hub/issues/33) | Auth-Worker fehlt (Issue #15 nur halb umgesetzt) | 2-3h | 🟡 offen |
| **P1** | [#34](https://github.com/QuasiniusQuaks/nd-hub/issues/34) | `class DB` Constants-Container → `Enum`/`Final` | 2h | 🟡 offen |
| **P1** | [#35](https://github.com/QuasiniusQuaks/nd-hub/issues/35) | 9× `@lru_cache` → `cachetools.TTLCache` migrieren | 3-4h | 🟡 offen |
| **P1** | [#36](https://github.com/QuasiniusQuaks/nd-hub/issues/36) | 4× bare `except:` in `page_import.py` typisieren | 30min | 🟡 offen |
| **P1** | [#37](https://github.com/QuasiniusQuaks/nd-hub/issues/37) | `ndhub-web/requirements.txt` unvollständig | 30min | 🟡 offen |
| **P2** | [#38](https://github.com/QuasiniusQuaks/nd-hub/issues/38) | Verdreifachte `# nosec B310` Annotation | 5min | 🟢 trivial |
| **P2** | [#39](https://github.com/QuasiniusQuaks/nd-hub/issues/39) | 518 ruff-Lint-Errors systematisch fixen | 2-3h | 🟡 offen |
| **P2** | [#40](https://github.com/QuasiniusQuaks/nd-hub/issues/40) | TODO/FIXME/HACK Inventar erstellen | 1-2h | 🟡 offen |

Sprint-Plan: siehe [#41](https://github.com/QuasiniusQuaks/nd-hub/issues/41).

### Tool-Befunde der Welle 2

| Tool | Ergebnis | Bewertung |
|---|---|---|
| `ruff check` | **518 Errors** | 254 auto-fixbar, Rest manuell |
| `bandit` | **534 Issues** (533 Low, 1 Medium) | 1 Medium = Hardcoded `/tmp/test.pdf` in Test (harmlos) |
| `ast.parse` | **2 SyntaxError** in Web-Tests | Tests laufen still nicht → Issue #30 |
| `grep except:` | **4× bare except** im Desktop-Client | Issue #36 |
| `grep lru_cache` | **9× @lru_cache** in db_manager.py | Issue #35 (Doku schon in PR #25, Migration offen) |

### Methodik Welle 2

Anders als Welle 1 (rein Desktop-Client) habe ich hier **beide Codebasen** systematisch inspiziert:

1. **Web-Layer (FastAPI, 152 Endpoints)**: Auth-Middleware, Rate-Limit, CORS, Security-Header.
2. **DB-Layer (SqliteRepository, Database, SecurityManager)**: Connection-Lifecycle, lru_cache-Migration.
3. **Tests (pytest)**: Sammelt die Suite, prüft auf Syntax-Fehler, asserts.
4. **Dependencies (requirements.txt)**: Diff zwischen Code-Imports und requirements-Einträgen.
5. **Style (ruff)**: Sammelt alle Lint-Errors für späteres Bulk-Cleanup.

### Empfohlene Reihenfolge (Welle 2)

#### Sprint 1 (1 Tag, P0-Security-Bundle)
PR #X: **P0-Security-Bundle** — #29, #30, #31, #32 als 4 Commits
- Atomic-reviewable, alle security-relevant

#### Sprint 2 (2-3 Tage, P1-Architektur-Bundle)
PR #Y: **Auth-Worker + Login-Threading** — #33
PR #Z: **DB-Cleanup + Dependency-Hygiene** — #34, #35, #36, #37 als 4 Commits

#### Sprint 3 (1 Tag, P2-Polish-Bundle)
PR #W: **Polish** — #38, #39, #40 als 3 Commits

### Strategie (gilt für beide Wellen)

- **Kein Big-Bang-Refactor.** Jeder Befund ist ein eigener Branch, eigener PR, eigene Review.
- **Reihenfolge: kleine, isolierte Fixes zuerst.** Das schafft Reviewer-Vertrauen.
- **Sammel-PRs pragmatisch erlaubt** für thematisch verwandte Fixes (siehe Sprint-Plan #41).
- **Bei jedem PR:** Vor dem Open CI-Status grün, Tests lokal grün, dann `gh pr create` mit PR-Template.
- **Senior-Quality-Gates:** ruff clean, bandit clean, ast.parse clean, mind. 1 Test pro Issue.

### Konventionen

- Branch-Naming: `type/issue-N-kurzname` (z. B. `fix/issue-29-web-password-timing`)
- Commit-Messages: Conventional Commits (`fix:`, `perf:`, `security:`, `chore:`, `refactor:`) + Issue-Ref
- PR-Template: siehe `docs/PULL_REQUEST_TEMPLATE.md`
- Tests: Jeder PR muss neue Tests für die geänderte Logik mitbringen (Coverage-Maintenance)
