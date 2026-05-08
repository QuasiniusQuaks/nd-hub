# Zielgruppen

ND-Hub adressiert mehrere klar abgrenzbare Anwendergruppen. Auf dieser Seite
wird beschrieben, welchen Nutzen die jeweilige Gruppe konkret erhaelt und in
welchen Szenarien ND-Hub typischerweise eingesetzt wird.

## Primaere Zielgruppen

### Apotheken und krankenhausnahe Versorgungsbereiche

- Verantwortlich fuer Bereitstellung, Bestueckung und Verfallskontrolle von
  **Notfalldepots**.
- Profitieren von:
    - strukturierten Stammdaten (Depots, Praeparate, Zuordnungen),
    - automatisierten Verfallsuebersichten,
    - klar dokumentierten Bewegungen mit PDF-Anhaengen.

### Leitung und Fachadministration

- Steuern Bestaende und Bewegungen ueber mehrere Depots hinweg.
- Profitieren von:
    - Reportings (Bestand, Bewegungen, Ranking, Matrix, Verfall) mit
      Exporten in CSV/PDF/PPTX,
    - rollenbasierter Rechtevergabe,
    - Auswertungen fuer interne Steuerung und externe Pruefungen.

### Qualitaetsmanagement, Revision und Compliance

- Benoetigen nachvollziehbare Aktivitaetshistorien.
- Profitieren von:
    - Audit-Logs (CRUD, Login, Sync),
    - Backup-/Restore-Pfaden mit Format- und Groessenpruefung,
    - dokumentierten Cutover-/Go-Live-Pfaden fuer Datenmigrationen.

### IT- und Digitalisierungsverantwortliche

- Entscheiden ueber Bereitstellungsmodell, Datenbankstrategie und Skalierung.
- Profitieren von:
    - Wahlfreiheit zwischen Desktop, Web oder Hybrid,
    - umschaltbarer DB-Engine (SQLite oder MariaDB),
    - Docker-basiertem, reproduzierbarem Deployment.

## Typische Einsatzszenarien

| Szenario | Kurzbeschreibung |
|---|---|
| Standortbetrieb | Eine Apotheke betreibt den Desktop Client lokal mit SQLite. |
| Zentralbetrieb | Eine Klinikgruppe betreibt die Webanwendung zentral mit MariaDB im Docker-Stack. |
| Hybridbetrieb | Mehrere Standorte arbeiten lokal mit Desktop, synchronisieren aber ueber das Web-Backend. |
| Pilotbetrieb | Einfuehrung in einem Pilotstandort, schrittweise Ausweitung. |
| Datenmigration | Bestehende SQLite-Datenbasis wird kontrolliert auf MariaDB ueberfuehrt. |

## Rollen in der Anwendung

| Rolle | Typische Verantwortung in ND-Hub |
|---|---|
| Admin | Stammdaten, Benutzer, Backups, Konfiguration, Audit. |
| Fachanwender | Bewegungen, Verfallskontrolle, Berichte, E-Mail-Workflows. |
| Auditor / QM | Lesen von Audit-Logs, Reports und Verfallsdaten (read-orientierte Sicht). |

Detaillierte Beschreibungen der Rollen und ihrer Rechte siehe
[Security / AuthN & AuthZ](../security/01-authn-authz.md).
