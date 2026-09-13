# Roadmap: Architektur-Audit (Wellen 1–5)

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

| Prio | Issue | Befund | Aufwand | Status | Branch / PR |
|---|---|---|---|---|---|
| **P0** | [#29](https://github.com/QuasiniusQuaks/nd-hub/issues/29) | Timing-Attacke auf Web `verify_password` (== statt hmac.compare_digest) | 1-2h | ✅ fertig | PR #44 |
| **P0** | [#30](https://github.com/QuasiniusQuaks/nd-hub/issues/30) | SyntaxError in 2 Web-Test-Dateien (`gitleaks:allow,` Bug) | 30min | ✅ fertig | PR #43 |
| **P0** | [#31](https://github.com/QuasiniusQuaks/nd-hub/issues/31) | Kein CORS / Security-Header / TrustedHost im FastAPI | 2-3h | ✅ fertig | PR #45 |
| **P0** | [#32](https://github.com/QuasiniusQuaks/nd-hub/issues/32) | Kein Rate-Limit auf `/auth/login` (Brute-Force) | 3-4h | ✅ fertig | PR #48 |
| **P1** | [#33](https://github.com/QuasiniusQuaks/nd-hub/issues/33) | Auth-Worker fehlt (Issue #15 nur halb umgesetzt) | 2-3h | ✅ fertig | PR #47 |
| **P1** | [#34](https://github.com/QuasiniusQuaks/nd-hub/issues/34) | `class DB` Constants-Container → `Enum`/`Final` | 2h | ✅ fertig | PR #46 |
| **P1** | [#35](https://github.com/QuasiniusQuaks/nd-hub/issues/35) | 9× `@lru_cache` → `cachetools.TTLCache` migrieren | 3-4h | ✅ fertig | PR #46 |
| **P1** | [#36](https://github.com/QuasiniusQuaks/nd-hub/issues/36) | 4× bare `except:` in `page_import.py` typisieren | 30min | ✅ fertig | PR #46 |
| **P1** | [#37](https://github.com/QuasiniusQuaks/nd-hub/issues/37) | `ndhub-web/requirements.txt` unvollständig | 30min | ✅ fertig | PR #46 |
| **P2** | [#38](https://github.com/QuasiniusQuaks/nd-hub/issues/38) | Verdreifachte `# nosec B310` Annotation | 5min | ✅ fertig | PR #50 |
| **P2** | [#39](https://github.com/QuasiniusQuaks/nd-hub/issues/39) | 518 ruff-Lint-Errors systematisch fixen | 2-3h | ✅ fertig | PR #51 |
| **P2** | [#40](https://github.com/QuasiniusQuaks/nd-hub/issues/40) | TODO/FIXME/HACK Inventar erstellen | 1-2h | ✅ fertig | PR #52 |

**Welle 2: 11 PRs gemerged (#43–#53), 12 Issues closed (#29–#40).**

Zusätzliche PRs über den Sprint-Plan hinaus:
- [PR #49](https://github.com/QuasiniusQuaks/nd-hub/pull/49): README-Update "Audit-Follow-up 2026-07"
- [PR #53](https://github.com/QuasiniusQuaks/nd-hub/pull/53): Post-Merge ruff-Cleanup (23 verbleibende Lint-Errors)

### Verifikation nach Sprint-Abschluss (2026-06-20)

| Tool | Ergebnis | Bewertung |
|---|---|---|
| `ruff check` | **0 Errors** | ✅ clean (PR #51 + #53) |
| `bandit` | **603 Low + 1 Medium** | ✅ Medium = Hardcoded `/tmp/test.pdf` in Test (harmlos, bekannt) |
| `ast.parse` | **0 SyntaxErrors** | ✅ Issue #30 Fix verifiziert |
| `pytest desktop-client/tests/unit/` | **23/23 passed** (Welle-2-relevant) | ✅ clean; 7 Failures in `test_sync_worker.py` sind PySide6-Stub-Pitfall (Welle-1 #4) |
| `pytest ndhub-web/` | **1 pre-existing Failure** | ⚠️ `test_session_token_invalid_after_app_restart` — schon seit Initial-Commit `f0d39a8` rot (TokenStore file-based, Test erwartet in-memory); KEIN Welle-2-Problem |

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

---

## Welle 3 — Modularisierung Router/DB + Quality Gates (audit-2026-07-2)

Kontext: Nach Security-Wellen 1+2 wurden Domain-Router nach `shared/routers/*`
gezogen, `create_app` nach `app_factory.py` ausgelagert und `db_manager` in
Mixins unter `core/db/*` zerlegt (Issues #60–#69 geschlossen).

### Status (Welle 3)

| Prio | Issue | Befund | Status |
|---|---|---|---|
| **P1** | [#66](https://github.com/QuasiniusQuaks/nd-hub/issues/66) / PRs #87–#90 | `db_manager` Mixins (Analytics, Sync, Setup, CRUD) | ✅ fertig |
| **P1** | [#60](https://github.com/QuasiniusQuaks/nd-hub/issues/60) / #61 | Shared-Router + `app_factory` | ✅ fertig |
| **P1** | [#67](https://github.com/QuasiniusQuaks/nd-hub/issues/67) | Setup-Wizard Package-Split | ✅ fertig |
| **P1** | [#91](https://github.com/QuasiniusQuaks/nd-hub/issues/91) | Doku-Drift v0.5 / shared / core/db | ✅ fertig (PR #98) |
| **P1** | [#92](https://github.com/QuasiniusQuaks/nd-hub/issues/92) | CI: Ruff / pytest / Bandit | ✅ fertig (PR #98) |
| **P2** | [#70](https://github.com/QuasiniusQuaks/nd-hub/issues/70) | Web `database.py` + `mariadb_repository.py` Konsolidierung | ✅ fertig (PR #102) |
| **P2** | [#93](https://github.com/QuasiniusQuaks/nd-hub/issues/93) | Desktop-UI-Monolithen splitten | ✅ fertig (PRs #99 #100) |
| **P2** | [#94](https://github.com/QuasiniusQuaks/nd-hub/issues/94) | Dual-Stack security/helpers sharen | ✅ fertig (PR #101) |
| **P2** | [#95](https://github.com/QuasiniusQuaks/nd-hub/issues/95) | Lint-Regression nach Router-Split | ✅ fertig (2026-07-26) |
| **P2** | [#96](https://github.com/QuasiniusQuaks/nd-hub/issues/96) | Web create_app-Rest / factory slim | ✅ fertig (PR #99) |

**Welle 3 geschlossen (2026-07-26).** Label `audit-2026-07-2`.

---

## Welle 4 — Wartbarkeit, Stabilität, Sicherheit (audit-2026-09)

Sprint: [#120](https://github.com/QuasiniusQuaks/nd-hub/issues/120). Stand nach P2-Abschluss.

| Prio | Issue | Befund | Status | PR |
|---|---|---|---|---|
| **P0** | [#104](https://github.com/QuasiniusQuaks/nd-hub/issues/104) | Compose MariaDB-Passwörter fail-closed | ✅ | #121 |
| **P0** | [#105](https://github.com/QuasiniusQuaks/nd-hub/issues/105) | dockerignore `.env` / DB-Dateien | ✅ | #122 |
| **P1** | [#106](https://github.com/QuasiniusQuaks/nd-hub/issues/106) | cryptography-Pin Desktop | ✅ | #123 |
| **P1** | [#107](https://github.com/QuasiniusQuaks/nd-hub/issues/107) | Web-requirements ohne GUI-Stack | ✅ | #124 |
| **P1** | [#108](https://github.com/QuasiniusQuaks/nd-hub/issues/108) | Compose Port 8000 auf Loopback | ✅ | #125 |
| **P1** | [#109](https://github.com/QuasiniusQuaks/nd-hub/issues/109) | Image-Publish erst nach grüner CI | ✅ | #126 |
| **P1** | [#110](https://github.com/QuasiniusQuaks/nd-hub/issues/110) | Web-DB Domain-Mixins | ✅ | #127 |
| **P1** | [#111](https://github.com/QuasiniusQuaks/nd-hub/issues/111) | `main.tsx` Inseln | ✅ | #128 |
| **P1** | [#112](https://github.com/QuasiniusQuaks/nd-hub/issues/112) | Shared lockout-policy | ✅ | #131 |
| **P1** | [#113](https://github.com/QuasiniusQuaks/nd-hub/issues/113) | Kein Legacy-`sqlite3.connect` | ✅ | #129 |
| **P1** | [#114](https://github.com/QuasiniusQuaks/nd-hub/issues/114) | `processEvents`-Reste | ✅ | #130 |
| **P2** | [#115](https://github.com/QuasiniusQuaks/nd-hub/issues/115) | ALTER/PRAGMA SQL-Literale | ✅ | #132 |
| **P2** | [#116](https://github.com/QuasiniusQuaks/nd-hub/issues/116) | except-Hotspots typisieren | ✅ | #133 |
| **P2** | [#117](https://github.com/QuasiniusQuaks/nd-hub/issues/117) | CI Coverage-Gate + Sync-Worker-Kern | ✅ | #134 |
| **P2** | [#118](https://github.com/QuasiniusQuaks/nd-hub/issues/118) | Dockerfile nur Runtime-Artefakt | ✅ | #135 |
| **P2** | [#119](https://github.com/QuasiniusQuaks/nd-hub/issues/119) | Diese Roadmap + README | ✅ | #136 |

---

## Welle 5 — Publish-Heilung, CI-Build, Secret-Hygiene (audit-welle-5)

Sprint: [#137](https://github.com/QuasiniusQuaks/nd-hub/issues/137). Audit 2026-09-13 nach Welle 4.

| Prio | Issue | Befund | Status | PR |
|---|---|---|---|---|
| **P0** | [#138](https://github.com/QuasiniusQuaks/nd-hub/issues/138) | Dockerfile Node 20.14 vs Vite 8 (GHCR-Publish rot) | ✅ | #143 |
| **P1** | [#139](https://github.com/QuasiniusQuaks/nd-hub/issues/139) | CI-Job `frontend-build` (`npm ci` + `npm run build`) | ✅ | #143 |
| **P1** | [#140](https://github.com/QuasiniusQuaks/nd-hub/issues/140) | npm audit nanoid/postcss (Build-Zeit) | ✅ | #143 |
| **P1** | [#141](https://github.com/QuasiniusQuaks/nd-hub/issues/141) | Generiertes Admin-Passwort nicht loggen | ✅ | #145 |
| **P1** | [#142](https://github.com/QuasiniusQuaks/nd-hub/issues/142) | `__CHANGE_ME__` als Deploy-Passwort ablehnen | ✅ | #145 |

GHCR-Publish nach #143/#145: grün (u. a. [34768056885](https://github.com/QuasiniusQuaks/nd-hub/actions/runs/34768056885)). P2-Monolithen bewusst nicht in diesem Sprint.
