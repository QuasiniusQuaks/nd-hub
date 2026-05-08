# ND-Hub

<p align="center">
  <img src="new_logo.png" alt="ND-Hub Logo" width="220" />
</p>

<p align="center">
  <img alt="Version" src="https://img.shields.io/badge/Version-v0.42-1f6feb" />
  <img alt="Produkte" src="https://img.shields.io/badge/Produkte-Desktop%20%2B%20Web-0a7f5a" />
  <img alt="Technologie" src="https://img.shields.io/badge/Stack-PySide6%20%7C%20FastAPI%20%7C%20React-6f42c1" />
</p>

<p align="center">
  <strong>Digitale Plattform zur strukturierten Verwaltung von Notfalldepots</strong><br/>
  Desktop-Client und Webanwendung fuer sichere Prozesse, hohe Transparenz und belastbare Auswertungen.
</p>

---

## Inhaltsverzeichnis

- [Was ist ND-Hub?](#was-ist-nd-hub)
- [Produktstatus (aktuell)](#produktstatus-aktuell)
- [Die zwei Software-Produkte im Ueberblick](#die-zwei-software-produkte-im-ueberblick)
- [Feature-Highlights auf einen Blick](#feature-highlights-auf-einen-blick)
- [Zielgruppen und Einsatzszenarien](#zielgruppen-und-einsatzszenarien)
- [Warum ND-Hub fuer potenzielle Kunden relevant ist](#warum-nd-hub-fuer-potenzielle-kunden-relevant-ist)
- [Kurzvergleich Desktop vs. Web](#kurzvergleich-desktop-vs-web)
- [Architektur auf einen Blick](#architektur-auf-einen-blick)
- [Schnellstart](#schnellstart)
- [Wichtige Projektpfade](#wichtige-projektpfade)
- [FAQ fuer Interessenten](#faq-fuer-interessenten)
- [Warum jetzt starten?](#warum-jetzt-starten)
- [Kontakt & Demo](#kontakt--demo)
- [Historie](#historie)

---

## Was ist ND-Hub?

ND-Hub ist eine spezialisierte Softwareloesung fuer Organisationen, die Notfalldepots, Praeparate, Bewegungen und Verfallsdaten professionell steuern wollen.  
Das Repository umfasst zwei Produktlinien mit demselben fachlichen Kern:

- `desktop-client/`: lokale, performante Desktopanwendung mit moderner UI und integriertem Backend.
- `ndhub-web/`: webbasierte Variante mit FastAPI-Backend, React-Frontend, Docker-Betrieb und unterstuetztem SQLite-/MariaDB-Betrieb.

Beide Loesungen verfolgen dasselbe Ziel: **betriebliche Sicherheit erhoehen, manuelle Aufwaende reduzieren und revisionsfaehige Daten schaffen**.

### Produktstatus (aktuell)

- **Aktuelle Version:** `v0.42`
- **Bereitstellungsmodelle:** Desktop (lokal) und Web (zentral/containerfaehig)
- **Schwerpunkt:** Stabiler operativer Betrieb, Sicherheit und fachliche Nachvollziehbarkeit

---

## Die zwei Software-Produkte im Ueberblick

### 1) ND-Hub Desktop Client

Die Desktopanwendung (PySide6) richtet sich an Teams, die ein robustes, lokales Arbeitswerkzeug mit hoher Reaktionsgeschwindigkeit und geringer Betriebsabhaengigkeit benoetigen.

**Ideal fuer Kunden, die ...**

- sensible Prozesse bevorzugt lokal betreiben moechten.
- eine performante App fuer den taeglichen Arbeitsplatz brauchen.
- klare, gefuehrte Oberflaechen fuer operative Teams erwarten.

**Kernnutzen**

- Schnelles, direktes Arbeiten am Arbeitsplatz ohne Browser-Abhaengigkeit.
- Durchgaengige Bedienfuehrung fuer operative Prozesse rund um Notfalldepots.
- Lokaler Betrieb mit klarer Trennung von Programm- und Datenpfaden.

**Wichtige Funktionsbereiche**

- Dashboard fuer Bestands- und Uebersichtskennzahlen.
- Depotverwaltung (Anlegen, Bearbeiten, Strukturieren).
- Praeparateverwaltung inkl. Zuordnungen und Sollbestaenden.
- Bewegungsmanagement (Ein- und Ausgaenge) inklusive Dokumentenbezug.
- Verfallmanagement mit Fristenfokus und Fruehwarnlogik.
- E-Mail-Funktionen mit Empfaenger-Vorschau und Verlauf.
- Berichte und Exporte (CSV/PDF/PPTX) fuer Fachbereich und Management.
- Audit-Logs fuer Nachvollziehbarkeit relevanter Aktionen.
- Backup/Restore-Funktionen fuer Datensicherung und Wiederherstellung.
- Setup-Wizard fuer strukturierte Erstkonfiguration.
- Benutzer- und Rechteverwaltung mit Admin-Schutzmechanismen.

**Technische und betriebliche Staerken**

- Sicherheitsarchitektur mit Passwort-Hashing, Account-Schutz und Rollenlogik.
- Globales Error-Handling fuer stabilen Betrieb im Alltag.
- Datenbankoptimierung (SQLite/WAL) fuer performante Zugriffe.
- Geeignet fuer Umgebungen mit restriktiven Berechtigungen.

Mehr Details: [`desktop-client/README.md`](desktop-client/README.md)

---

### 2) ND-Hub Webanwendung

Die Webanwendung ist fuer Organisationen gedacht, die zentrale Bereitstellung, browserbasierten Zugriff und eine skalierbare Datenstrategie (SQLite oder MariaDB) priorisieren.

**Ideal fuer Kunden, die ...**

- standortuebergreifend ueber den Browser arbeiten moechten.
- eine zentrale Betriebsplattform mit API-Fokus suchen.
- ihre Infrastruktur schrittweise modernisieren wollen.

**Kernnutzen**

- Zentraler Zugriff ueber Browser statt lokaler Installation pro Arbeitsplatz.
- API-zentrierter Aufbau fuer Integrationen und saubere Systemgrenzen.
- Containerfaehiger Betrieb via Docker Compose.

**Wichtige Funktionsbereiche**

- Authentifizierung und rollenbasierte Zugriffssteuerung.
- Vollstaendige CRUD-Prozesse fuer Depots, Praeparate und Kontakte.
- Bewegungsverwaltung mit Filterung, Pagination und PDF-Anhangsfunktion.
- Importstrecke fuer CSV/Excel inkl. Vorschau, Validierung und idempotenter Ausfuehrung.
- E-Mail-Workflows als Entwurf oder SMTP-Versand mit Statusverfolgung.
- Umfassende Reportings (Bestand, Bewegungen, Ranking, Matrix, Verfall) inkl. Export.
- Verfallsuebersichten und Benachrichtigungsendpunkte.
- Audit-Log-Endpunkte fuer Compliance- und Pruefkontexte.
- Admin-Backup/Restore mit Schutz gegen unkontrollierte Upload-Groessen.

**Technische und betriebliche Staerken**

- FastAPI-Backend mit klar dokumentierten Endpunkten.
- React/Vite-Frontend als moderne UI-Basis (inkrementeller Ausbau).
- Docker- und Migrationsartefakte fuer standardisierten Betrieb.
- Betriebsfaehig mit `ND_HUB_DB_ENGINE=sqlite` oder `ND_HUB_DB_ENGINE=mariadb`.
- Docker-Profile fuer beide Varianten; in produktionsnahen Profilen ist MariaDB als Zielbild vorgesehen.
- Kontrollierter Cutover-/Rollback-Pfad inkl. Smoke- und Go-Live-Checklisten.
- Hybrid-Sync- und Stabilitaetstests fuer belastbare Releases.

Mehr Details: [`ndhub-web/backend/README.md`](ndhub-web/backend/README.md)

---

## Feature-Highlights auf einen Blick

### Operative Prozesse

- Strukturierte Verwaltung von Depots, Praeparaten, Kontakten und Bewegungen.
- Verfallmanagement mit Fruehwarnfokus fuer kritische Bestandspositionen.
- Rollenbasierte Arbeitsablaeufe fuer Admins und Fachanwender.

### Analyse, Reporting und Kommunikation

- Fach- und Managementauswertungen fuer Bestand, Bewegungen, Rankings, Matrix und Verfall.
- Exporte in `CSV`, `PDF` und `PPTX` fuer Meetings, Revision und Weiterverarbeitung.
- E-Mail-Workflows inkl. Entwurfsmodus, SMTP-Option und Versandstatushistorie.

### Sicherheit und Compliance

- Auditierbare Prozesse durch rollenbasierte Rechte und Audit-Logs.
- Gehaertete Admin-Funktionen (z. B. Schutz des letzten aktiven Admins).
- Datensicherung durch Backup/Restore-Pfade mit Validierungsmechanismen.

---

## Zielgruppen und Einsatzszenarien

ND-Hub ist besonders interessant fuer:

- Apotheken und krankenhausnahe Versorgungsbereiche mit Notfalldepotverantwortung.
- Leitung und Fachadministration, die Bestands-, Verfalls- und Bewegungsdaten zentral steuern wollen.
- Qualitaetsmanagement, Revision oder Compliance-Funktionen mit Bedarf an auditierbaren Prozessen.
- IT- und Digitalisierungsverantwortliche, die zwischen lokalem und webzentralem Betriebsmodell waehlen moechten.

**Typische Szenarien**

- Standardisierte Pflege von Depotstammdaten und Zuordnungen.
- Regelmaessige Verfallskontrolle mit vorbereiteten Auswertungen.
- Monats-/Quartalsreporting fuer interne Steuerung oder externe Nachweise.
- Datenmigration bzw. schrittweise Modernisierung von lokal zu zentral.

### Entscheider-Mehrwert (fuer potenzielle Kunden)

- **Kostenkontrolle:** weniger manuelle Listenprozesse, weniger Medienbrueche, klare Standards.
- **Risikoreduktion:** transparente Verfalls- und Bewegungsdaten statt verstreuter Einzeldateien.
- **Skalierbarkeit:** Einstieg lokal (Desktop) und Ausbau auf zentrale Webprozesse moeglich.
- **Revisionssicherheit:** dokumentierte Aktionen und exportierbare Nachweise fuer Pruefungen.

---

## Warum ND-Hub fuer potenzielle Kunden relevant ist

- **Transparenz:** alle Kernprozesse sind auswertbar, exportierbar und nachvollziehbar.
- **Sicherheit:** rollenbasierter Zugriff, gehaertete Admin-Funktionen und Auditierbarkeit.
- **Betriebssicherheit:** Backup/Restore, stabile Fehlerbehandlung, pruefbare Releases.
- **Flexibilitaet:** Desktop fuer lokale Teams, Web fuer zentrale Bereitstellung.
- **Zukunftsfaehigkeit:** klarer Entwicklungspfad mit API- und Datenbankstrategie.

---

## Kurzvergleich Desktop vs. Web

| Kriterium | Desktop Client | Webanwendung |
|---|---|---|
| Primarer Einsatz | Lokaler Arbeitsplatzbetrieb | Zentraler Browserzugriff |
| Betriebsmodell | Lokal installiert | Server-/Containerbasiert |
| Staerken | Direktes UI-Feeling, geringe Abhaengigkeit | Zentrale Bereitstellung, API-zentriert |
| Zielbild | Fokus auf operative Einzelstandorte | Fokus auf uebergreifende Verfuegbarkeit |
| Datenstrategie | SQLite (optimiert) | SQLite oder MariaDB (umschaltbar ueber `ND_HUB_DB_ENGINE`) |

---

## Architektur auf einen Blick

```text
ND-Hub Plattform
├── Desktop Client (PySide6 + integriertes FastAPI-Modul)
│   ├── Operative Fachprozesse (Depots, Praeparate, Bewegungen, Verfall)
│   ├── Reporting & Exporte
│   ├── Security / Audit / Backup
│   └── Lokale Datenhaltung (SQLite, optimiert)
└── Webanwendung (FastAPI + React/Vite)
    ├── API-zentrierte Fachlogik
    ├── Browser-UI (inkrementelle Islands-Strategie)
    ├── Containerbetrieb (Docker)
    └── Datenpfad SQLite <-> MariaDB (Cutover/Go-Live dokumentiert)
```

---

## Schnellstart

### Desktop Client starten

```bash
cd desktop-client
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python run_notfalldepots.py
```

### Webanwendung lokal starten

```bash
cd ndhub-web/frontend-react && npm install && npm run build
cd ../.. && cd ndhub-web && python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python run_backend.py
```

---

## Wichtige Projektpfade

- `desktop-client/` - Desktopprodukt inkl. UI, Kernlogik und lokaler Betriebswerkzeuge
- `ndhub-web/` - Webprodukt inkl. Backend, Frontend und Docker-/Migrationspfaden
- `desktop-client/tests/` - Unit-, Integrations- und Performancetests
- `ndhub-web/backend/tests/` - API-, Security-, Stabilitaets- und Sync-Tests

---

## FAQ fuer Interessenten

### Ist ND-Hub eher fuer kleine Teams oder fuer groeßere Organisationen geeignet?

Beides ist moeglich: Der Desktop-Client ist stark fuer lokal arbeitende Teams, die Webanwendung fuer zentral organisierte, standortuebergreifende Strukturen.

### Kann man mit dem Desktop starten und spaeter auf Web erweitern?

Ja. Das Produkt ist so aufgebaut, dass ein schrittweiser Ausbau vom lokalen Betrieb hin zu zentralen Webprozessen moeglich ist.

### Welche Datenbankstrategie verfolgt ND-Hub?

Die Webanwendung unterstuetzt SQLite und MariaDB. Fuer den produktiven MariaDB-Betrieb sind Cutover-, Smoke- und Rollback-Prozesse dokumentiert; optional steht ein kurzer Dual-Write-Uebergangsmodus zur Verfuegung.

### Wie unterstuetzt ND-Hub Compliance und Pruefbarkeit?

Durch rollenbasierte Zugriffe, Audit-Logs, nachvollziehbare Fachprozesse und exportierbare Auswertungen fuer interne wie externe Pruefkontexte.

### Welche Export- und Berichtsoptionen sind verfuegbar?

Berichte koennen je nach Bereich als `CSV`, `PDF` und `PPTX` exportiert werden, z. B. fuer Management-Updates, Audits und operative Auswertungen.

---

## Warum jetzt starten?

- **Schnelle Wirkung im Alltag:** Standardisierte Prozesse reduzieren Suchaufwand, Rueckfragen und Medienbrueche bereits in der Einfuehrungsphase.
- **Bessere Steuerbarkeit:** Verfalls-, Bestands- und Bewegungsdaten werden zentral sichtbar und sind fuer Entscheidungen sofort nutzbar.
- **Geringeres Betriebsrisiko:** Rollen, Audit-Logs und Backup/Restore schaffen Verlaesslichkeit in kritischen Versorgungsprozessen.
- **Schrittweise Modernisierung statt Big Bang:** Start mit Desktop oder Web moeglich, anschliessend planbarer Ausbau entlang Ihrer Infrastrukturstrategie.

---

## Kontakt & Demo

Sie moechten ND-Hub fuer Ihre Organisation bewerten?  
Gern unterstuetzen wir mit einem strukturierten Demo- und Einfuehrungsprozess.

### Empfohlener Ablauf fuer Interessenten

1. **Kurz-Assessment (30 Min.)**  
   Gemeinsame Sicht auf aktuelle Prozesse, Anforderungen und Zielbild.
2. **Produktdemo (45-60 Min.)**  
   Live-Einblick in Desktop-Client und Webanwendung entlang realer Anwendungsfaelle.
3. **Pilotplanung**  
   Definition von Pilotumfang, Rollen, Datenbasis und Erfolgskriterien.
4. **Onboarding & Go-Live**  
   Technische Einrichtung, Schulung der Kernanwender und operative Inbetriebnahme.

### Was fuer eine Demo hilfreich ist

- Anzahl der Standorte / beteiligten Teams
- heutiger Prozess fuer Bestands- und Verfallskontrolle
- benoetigte Berichte / Exportformate
- gewuenschtes Betriebsmodell (Desktop, Web oder Hybrid)

> Hinweis: Diese README dient als Produktueberblick.  
> Fuer technische Details und Betriebsdokumentation siehe die projektspezifischen READMEs in `desktop-client/` und `ndhub-web/`.

---

## Historie

Dieses Repository wurde mit einer orphan-Wurzel neu aufgesetzt und auf die beiden aktuellen Hauptlinien fokussiert (`desktop-client` und `ndhub-web`).  
Aeltere Versionsordner (z. B. V1-V39) liegen nur noch in Archiv-Branches bzw. externen Backups.
