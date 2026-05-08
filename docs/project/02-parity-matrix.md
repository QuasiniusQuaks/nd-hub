# Parity-Matrix

Diese Seite beschreibt die fachliche Funktions-Paritaet zwischen
**Desktop Client** und **Webanwendung**. Die Daten basieren auf den
zwei Quellen:

- `desktop-client/WEB_DESKTOP_PARITY_MATRIX.md` (laufendes Tracking),
- `ndhub-web/backend/DESKTOP_PARITY_PLAN.md` (Plan/Spezifikation).

## Konvention

| Symbol | Bedeutung |
|---|---|
| `OK` | Funktion in Desktop und Web fachlich gleich. |
| `WEB-NEU` | Funktion zuerst im Web, Desktop noch zu spiegeln. |
| `DESKTOP-NEU` | Funktion zuerst im Desktop, Web zu spiegeln. |
| `LIMITED` | Funktion nutzbar, aber mit dokumentierter Einschraenkung. |
| `N/A` | Nicht anwendbar. |

## Auth, User & Rechte

| Bereich | Desktop | Web | Status |
|---|---|---|---|
| Login (User+Pass) | ja | ja | OK |
| Passwortwechsel (forced) | ja | ja | OK |
| Account-Sperre | ja | ja | OK |
| Rollen Admin/User | ja | ja | OK |
| Letzter-Admin-Schutz | ja | ja | OK |
| Self-Toggle-Schutz | ja | ja | OK |
| Avatar-Upload | ja | ja | OK |
| User-CRUD/Reset/Unlock | ja | ja | OK |

## Stammdaten

| Bereich | Desktop | Web | Status |
|---|---|---|---|
| Depots CRUD + Suche | ja | ja | OK |
| Praeparate CRUD + Suche | ja | ja | OK |
| Zuordnungen (Sollbestand) | ja | ja | OK |
| Kontakte CRUD | ja | ja | OK |
| Institutionen | optional | optional | OK (Feature-Flag) |

## Operativ

| Bereich | Desktop | Web | Status |
|---|---|---|---|
| Bewegungen anlegen | ja | ja | OK |
| Bewegungen Verlauf + Filter | ja | ja | OK |
| CSV-Export Verlauf | ja | ja | OK |
| PDF-Anhaenge (max. 10 MB) | ja | ja | OK |
| Bewegungen-Volltext | ja | ja | OK |
| Persistente Filter pro User | ja | ja | OK |

## Verfall

| Bereich | Desktop | Web | Status |
|---|---|---|---|
| Verfallsuebersicht | ja | ja | OK |
| Verfall CSV-Export | ja | ja | OK |
| Notifications (polling) | ja | ja | OK |

## Reports

| Bereich | Desktop | Web | Status |
|---|---|---|---|
| Bewegungen-Report | ja | ja | OK |
| Bestand-Report | ja | ja | OK |
| Ranking-Report | ja | ja | OK |
| Matrix-Report | ja | ja | OK |
| Verfall-Report | ja | ja | OK |
| Exports CSV/PDF/PPTX | ja | ja | OK |
| Datumsvalidierung | ja | ja | OK |

## Imports

| Bereich | Desktop | Web | Status |
|---|---|---|---|
| Preview + Fehlercodes | ja | ja | OK |
| Idempotenz `import_fingerprint` | ja | ja | OK |
| Dry-Run | ja | ja | OK |
| Excel-Vorlage | ja | ja | OK |

## E-Mail

| Bereich | Desktop | Web | Status |
|---|---|---|---|
| Recipients-Preview | ja | ja | OK |
| Drafts + Verlauf | ja | ja | OK |
| SMTP-Liveversand | ja | ja | OK |
| Versandstatus + Fehler | ja | ja | OK |

## Audit & Backup

| Bereich | Desktop | Web | Status |
|---|---|---|---|
| Audit-Logs Filter/Paging | teilweise | ja | LIMITED (Desktop einfacher) |
| Backup erstellen/list | ja | ja | OK |
| Restore + Format-/Groessenpruefung | ja | ja | OK |
| Pre-Restore-Snapshot | ja | ja | OK |

## Sync (v1)

| Bereich | Desktop | Web | Status |
|---|---|---|---|
| `local_only` | ja | n/a | OK |
| `hybrid_sync` | ja | als Server | OK |
| `remote_only` | ja | als Server | OK |
| `/sync/status` | client | server | OK |
| `/sync/pull` (cursor) | client | server | OK |
| `/sync/push` (batch_id) | client | server | OK |
| Konflikt-Hinweise | ja | ja | OK |

## Setup & Onboarding

| Bereich | Desktop | Web | Status |
|---|---|---|---|
| Setup-Wizard | ja | teilweise | LIMITED (Web im Ausbau) |
| Onboarding-Status (`/onboarding/status`) | n/a | ja | WEB-NEU |
| Institution-Setup | n/a | ja | WEB-NEU |

## Karte / Geo

| Bereich | Desktop | Web | Status |
|---|---|---|---|
| `/map/institutions` | n/a | optional | WEB-NEU (Feature-Flag) |
| Geocoding-Helper | n/a | ja | WEB-NEU |

## Plattform

| Bereich | Desktop | Web | Status |
|---|---|---|---|
| SQLite | ja | ja | OK |
| MariaDB | n/a | ja | WEB-NEU |
| Engine-Switch | n/a | ja | WEB-NEU |
| Docker Stack | n/a | ja | WEB-NEU |
