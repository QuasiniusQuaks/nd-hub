# ND-Hub – Projektplan, PSP und Tabellenstruktur

**Projektname:** ND-Hub – Die Notfalldepot-Verwaltung
**Planungsstand:** Projektplan 2.0  
**Vorgehensmodell:** server-first, inkrementell, 2‑Wochen-Sprints  
**Zielbild:** Zentrales Backend mit Webanwendung, Desktop-Client und optionaler lokaler SQLite-/Sync-Fähigkeit.

***

## 1. Projektkontext

ND-Hub wird als **neue Plattform** geplant und nicht mehr als reiner Desktop-Umbau verstanden. Ausgangspunkt ist ein bestehender Python-/PySide6-Client mit SQLite, der künftig durch eine Serveranwendung mit Web- und Desktop-Clients ergänzt beziehungsweise architektonisch neu geschnitten werden soll.

Für die Projektplanung wird ein **Projektstrukturplan mit klar abgegrenzten Arbeitspaketen** verwendet, weil Arbeitspakete als kleinste steuerbare Einheit mit Verantwortlichkeit, Ergebnis und Aufwand gelten und daraus Termin- und Ablaufplanung abgeleitet werden.[1][2][3][4]

### 1.1 Projektziele

| Ziel | Beschreibung | Priorität |
|---|---|---|
| Z1 | Aufbau einer zentralen Serverplattform für ND-Hub | Muss |
| Z2 | Bereitstellung einer Webanwendung für Standardzugriff | Muss |
| Z3 | Bereitstellung eines Desktop-Clients für Power-User und lokale Nutzung | Muss |
| Z4 | Unterstützung von lokalem, onlinebasiertem und hybridem Betrieb | Soll |
| Z5 | Nachvollziehbarkeit durch Rollen, Audit und Historie | Muss |
| Z6 | Docker-basiertes Deployment für Serverbetrieb | Muss |

### 1.2 MVP-Scope

| Bereich | Im MVP enthalten | Nicht im ersten MVP |
|---|---|---|
| Benutzer | Login, Rollen, Basisrechte | SSO, Mandantenfähigkeit |
| Depots | Anlegen, Bearbeiten, Suchen, Zuordnen | Komplexe Freigabeworkflows |
| Präparate | Stammdaten, Kategorisierung, Zuordnung | Erweiterte Stammdatenimporte |
| Bestände | Bestandsführung, Bewegungen, Historie | Vollständige mobile Lagerprozesse |
| Reporting | Basisexporte, einfache Berichte | Umfangreiche BI-/Dashboard-Suite |
| Sync | Grundlegender Hybridmodus | Vollautomatische Konfliktassistenz V2 |

### 1.3 Projektannahmen

| Annahme | Wert |
|---|---|
| Sprintlänge | 2 Wochen |
| Teamgröße | 3–4 Rollen, teils in Personalunion |
| Schätzmethode | Personentage (PT) |
| Planungsziel | Pilotfähiges System, kein Full Enterprise Release |
| Architekturprinzip | server-first, modulare Clients |
| Kritischer Risikobereich | Sync-/Hybridbetrieb |

### 1.4 Rollenmodell im Projekt

| Rolle | Hauptverantwortung |
|---|---|
| PM / Product Owner | Scope, Prioritäten, Stakeholder, Abnahme |
| Tech Lead / Architect | Zielarchitektur, Modulkonzept, technische Entscheidungen |
| Backend Engineer | API, Auth, PostgreSQL, Jobs, Audit |
| Desktop Engineer | PySide6-Client, lokale SQLite, Betriebsmodi |
| Web Engineer | Web-Frontend, API-Integration |
| QA / Testkoordination | Teststrategie, Testfälle, Abnahmequalität |
| DevOps | Deployment, Staging, Backups, Secrets |

***

## 2. Lieferstrategie und konkreter Projektplan

Für Softwareprojekte ist eine Gliederung in Analyse, Design, Entwicklung, Test und Einführung üblich; für ND-Hub wird diese Logik auf die Phasen **Initialisierung, Architektur, Daten/API, Backend, Clients, Sync, Qualität und Pilot** abgebildet.[5][6]

Die Delivery-Strategie ist bewusst **vertikal**: zentrale Fachfunktion zuerst einmal durch Backend, Desktop und Web liefern, statt isoliert nur einzelne Technikschichten fertigzustellen.

### 2.1 Phasenplan

| Phase | Dauer | Ziel | Hauptergebnis |
|---|---:|---|---|
| Phase 0 | 1 Woche | Projekt initialisieren | Scope, Rollen, Backlog V1 |
| Phase 1 | 2 Wochen | Zielarchitektur und Modulgrenzen festziehen | Architekturfreigabe |
| Phase 2 | 2 Wochen | Datenmodell und API-Design definieren | OpenAPI V1, Schemas V1 |
| Phase 3 | 3 Wochen | Backend-MVP aufbauen | Laufendes Backend in Staging |
| Phase 4 | 3 Wochen | Desktop-Client neu schneiden | Nutzbarer Desktop-MVP |
| Phase 5 | 2 Wochen | Web-MVP bereitstellen | Nutzbare Web-Basis |
| Phase 6 | 4 Wochen | Hybrid-/Sync-MVP umsetzen | Push/Pull/Retry/Konfliktlogik V1 |
| Phase 7 | 3 Wochen | Qualität, Betrieb, Pilot | Pilotbericht, Go-Live-Empfehlung |

### 2.2 Meilensteine

| Meilenstein | Sprint | Kriterium |
|---|---|---|
| M1 – Projektstart freigegeben | S1 | Scope, Rollen, MVP beschlossen |
| M2 – Architektur beschlossen | S2 | Architektur, Module, ADRs freigegeben |
| M3 – Daten & API freigegeben | S3 | PostgreSQL-/SQLite-Modell und API-Vertrag stehen |
| M4 – Backend-MVP in Staging | S5 | Auth und Kernmodule laufen |
| M5 – Desktop-MVP nutzbar | S7 | Desktop-Client lokal/online nutzbar |
| M6 – Web-MVP nutzbar | S8 | Kernprozesse im Browser verfügbar |
| M7 – Sync-MVP stabil | S10 | Hybridmodus mit Konfliktregeln vorhanden |
| M8 – Pilot abgeschlossen | S11 | Pilotfeedback bewertet, Go-Live-Entscheidung vorbereitet |

### 2.3 Sprintplan

| Sprint | Ziel | Hauptarbeit | Ergebnis |
|---|---|---|---|
| S1 | Projektstart | Scope, Rollen, Zielbild, MVP | Projektauftrag + Backlog V1 |
| S2 | Architekturschnitt | Modulkonzept, ADRs, Domain Start | Architekturpaket V1 |
| S3 | Daten/API | Datenmodelle, API, Sicherheit | OpenAPI + Schema V1 |
| S4 | Plattformbasis | Backend-Skeleton, Auth, Desktop-Skeleton | Technische Basis |
| S5 | Fachkern | Depot, Präparate, Bestände, Repositories | Backend-Kern + Client-Datalayer |
| S6 | Betriebsmodi | Audit, Jobs, Moduslogik, Web-Basis | System nutzbar in Basisform |
| S7 | Nutzbare Clients | Desktop-Kernscreens, Web-Views, Tests | Erste Ende-zu-Ende-Nutzung |
| S8 | Reporting + Sync-Vorbereitung | Reporting, Web-Details, Sync-Schema | Pilotnahe Funktionsbreite |
| S9 | Sync-Kern | Push, Pull, Retry, Staging | Hybridmodus technisch lauffähig |
| S10 | Hardening | Konflikte, Sync-UI, Backup/Restore, Pilotvorbereitung | Stabilisierung |
| S11 | Pilot | Pilotbetrieb, Bugfixing, Freigabeentscheidung | Pilotbericht |

***

## 3. Detaillierter PSP mit Aufwand und Sprints

### 3.1 PSP-Struktur – Projekt und Architektur

| PSP | Ebene | Arbeitspaket | Beschreibung | Aufwand (PT) | Sprint | Owner | Abhängigkeiten | Ergebnis | Priorität |
|---|---|---|---|---:|---|---|---|---|---|
| 1.1 | Projekt | Projektauftrag und Scope | Zielbild, Nutzen, Stakeholder, Nicht-Ziele, MVP festlegen | 3 | S1 | PM / Tech Lead | — | Freigegebener Projektauftrag | Muss |
| 1.2 | Projekt | Fachlicher MVP-Scope | Depots, Präparate, Bestände, Buchungen, Berichte, Benutzer priorisieren | 4 | S1 | Product | 1.1 | MVP-Katalog | Muss |
| 1.3 | Projekt | Rollen- und Rechtebild | Fachliche Rollen und grobe Rechte definieren | 3 | S1 | Product + Backend | 1.2 | Rollenmatrix V1 | Muss |
| 1.4 | Architektur | Zielarchitektur | Server, Web, Desktop, lokal/online/hybrid, Betriebsgrenzen schneiden | 4 | S1 | Architect | 1.1 | Architekturübersicht | Muss |
| 1.5 | Architektur | Modulkonzept | Backend-, Desktop-, Web- und Sync-Module finalisieren | 4 | S2 | Architect | 1.4 | Modulkonzept V1 | Muss |
| 1.6 | Architektur | ADRs | Technische Kernentscheidungen dokumentieren | 3 | S2 | Architect | 1.4 | ADR-Sammlung | Soll |
| 1.7 | Projekt | Projektsetup | Repos, Branching, CI-Grundlagen, Ticketstruktur | 4 | S2 | Tech Lead | 1.1 | Dev-Setup | Muss |

**Teilaufwand Bereich 1:** **25 PT**

### 3.2 PSP-Struktur – Fachmodell, Daten und API

| PSP | Ebene | Arbeitspaket | Beschreibung | Aufwand (PT) | Sprint | Owner | Abhängigkeiten | Ergebnis | Priorität |
|---|---|---|---|---:|---|---|---|---|---|
| 2.1 | Fach | Domänenmodell | Entitäten, Aggregate, IDs, Zustände, Versionen definieren | 5 | S2 | Backend Lead | 1.2, 1.4 | Domain Model V1 | Muss |
| 2.2 | Daten | Server-Datenmodell | PostgreSQL-Schema, Beziehungen, Audit-Felder, Soft Delete | 6 | S3 | Backend | 2.1 | DB-Schema V1 | Muss |
| 2.3 | Daten | Lokales Datenmodell | SQLite-Schema für Desktop-Local/Hybrid definieren | 4 | S3 | Desktop | 2.1 | SQLite-Schema V1 | Muss |
| 2.4 | API | API-Vertrag | Endpunkte, DTOs, Fehlercodes, Filter, Pagination definieren | 6 | S3 | Backend | 2.1 | OpenAPI V1 | Muss |
| 2.5 | Sicherheit | Sicherheitskonzept | Auth, Tokens/Sessions, Passwortregeln, Rechteprüfung | 4 | S3 | Backend | 2.4 | Security-Konzept | Muss |
| 2.6 | Daten | Migrationsstrategie | DB-Versionierung, Seeds, Upgradepfade | 3 | S3 | Backend | 2.2 | Migrationskonzept | Soll |

**Teilaufwand Bereich 2:** **28 PT**

### 3.3 PSP-Struktur – Backend

| PSP | Ebene | Arbeitspaket | Beschreibung | Aufwand (PT) | Sprint | Owner | Abhängigkeiten | Ergebnis | Priorität |
|---|---|---|---|---:|---|---|---|---|---|
| 3.1 | Backend | Backend-Grundgerüst | FastAPI-Struktur, Config, Logging, Error Handling, Healthchecks | 6 | S4 | Backend | 2.4, 2.5 | Startfähiges Backend | Muss |
| 3.2 | Backend | Auth und Benutzer | Login, Benutzerverwaltung, Rollenprüfung | 7 | S4 | Backend | 3.1 | Auth-Modul | Muss |
| 3.3 | Backend | Depotmodul | CRUD + Fachlogik für Depots | 6 | S4 | Backend | 3.1 | Depot-API | Muss |
| 3.4 | Backend | Präparatemodul | Stammdaten, Kategorien, Zuordnungen | 6 | S5 | Backend | 3.1 | Präparate-API | Muss |
| 3.5 | Backend | Bestandsmodul | Bewegungen, Bestände, Historie, Plausibilitäten | 8 | S5 | Backend | 3.3, 3.4 | Bestands-API | Muss |
| 3.6 | Backend | Reporting-Basis | Basisberichte, Export, PDF-/Druck-Trigger | 5 | S5 | Backend | 3.3–3.5 | Reporting V1 | Soll |
| 3.7 | Backend | Audit und Historie | Änderungsprotokoll und Nachvollziehbarkeit | 5 | S6 | Backend | 3.2–3.5 | Audit-Modul | Soll |
| 3.8 | Backend | Hintergrundjobs | Worker für Berichte, Importe, Wartungsjobs | 5 | S6 | Backend | 3.6 | Job-System | Soll |

**Teilaufwand Bereich 3:** **48 PT**

### 3.4 PSP-Struktur – Desktop-Client

| PSP | Ebene | Arbeitspaket | Beschreibung | Aufwand (PT) | Sprint | Owner | Abhängigkeiten | Ergebnis | Priorität |
|---|---|---|---|---:|---|---|---|---|---|
| 4.1 | Desktop | Desktop-Neuschnitt | Neues App-Skelett, UI-/Service-/Repository-Trennung | 6 | S4 | Desktop Lead | 1.5, 2.3 | Client-Grundgerüst | Muss |
| 4.2 | Desktop | Konfiguration | Serverprofil, Moduswahl, Benutzerkontext, Flags | 3 | S4 | Desktop | 4.1 | Config-Modul | Muss |
| 4.3 | Desktop | Local Repository | SQLite als austauschbarer Datenzugriff | 6 | S5 | Desktop | 2.3, 4.1 | Local Data Layer | Muss |
| 4.4 | Desktop | API Repository | Remote-Zugriff über Backend-API | 6 | S5 | Desktop | 2.4, 4.1 | Remote Data Layer | Muss |
| 4.5 | Desktop | Modussteuerung | Lokal, Online, Hybrid umschaltbar machen | 4 | S6 | Desktop | 4.3, 4.4 | Betriebsmodus-Manager | Muss |
| 4.6 | Desktop | Kernscreens Depots | Listen, Detail, Formular, Suche | 6 | S6 | Desktop | 4.3, 4.4 | Depot-UI | Muss |
| 4.7 | Desktop | Kernscreens Präparate | Listen, Detail, Formular, Suche | 6 | S7 | Desktop | 4.3, 4.4 | Präparate-UI | Muss |
| 4.8 | Desktop | Kernscreens Bestände | Bewegungen, Historie, Bestandssichten | 8 | S7 | Desktop | 4.3, 4.4 | Bestands-UI | Muss |
| 4.9 | Desktop | Reporting-Oberfläche | Exportauswahl, Berichtsanstoß, Statusanzeige | 4 | S8 | Desktop | 3.6 | Reporting-UI | Soll |

**Teilaufwand Bereich 4:** **49 PT**

### 3.5 PSP-Struktur – Web-Anwendung

| PSP | Ebene | Arbeitspaket | Beschreibung | Aufwand (PT) | Sprint | Owner | Abhängigkeiten | Ergebnis | Priorität |
|---|---|---|---|---:|---|---|---|---|---|
| 5.1 | Web | Web-Grundgerüst | Login, Navigation, Layout, API-Anbindung | 6 | S6 | Web Lead | 2.4, 3.2 | Web-App-Basis | Muss |
| 5.2 | Web | Depot-Views | Listen, Detail, Formulare | 5 | S7 | Web | 5.1, 3.3 | Depot-Webmodul | Muss |
| 5.3 | Web | Präparate-Views | Listen, Detail, Formulare | 5 | S7 | Web | 5.1, 3.4 | Präparate-Webmodul | Muss |
| 5.4 | Web | Bestands-Views | Bewegungen, Filter, Historie | 7 | S8 | Web | 5.1, 3.5 | Bestands-Webmodul | Muss |
| 5.5 | Web | Reporting-Basis | Berichtsliste, Trigger, Download | 4 | S8 | Web | 5.1, 3.6 | Reporting-Webmodul | Soll |

**Teilaufwand Bereich 5:** **27 PT**

### 3.6 PSP-Struktur – Sync-Schicht

Offline-/Hybrid-Architekturen erfordern einen eigenen technischen Strang für lokale Speicherung, Synchronisation, Wiederholungen und Konfliktbehandlung; genau dieser Bereich ist erfahrungsgemäß der größte Projektrisikotreiber.[2][1]

| PSP | Ebene | Arbeitspaket | Beschreibung | Aufwand (PT) | Sprint | Owner | Abhängigkeiten | Ergebnis | Priorität |
|---|---|---|---|---:|---|---|---|---|---|
| 6.1 | Sync | Sync-Datenmodell | Outbox, Status, Version, Zeitstempel, Konfliktmarker | 5 | S8 | Sync Lead | 2.3, 2.4 | Sync-Schema | Soll |
| 6.2 | Sync | Push-Engine | Lokale Änderungen an Server senden | 7 | S9 | Sync | 6.1, 4.4 | Push V1 | Soll |
| 6.3 | Sync | Pull-Engine | Serveränderungen lokal einspielen | 7 | S9 | Sync | 6.1, 4.3 | Pull V1 | Soll |
| 6.4 | Sync | Retry- und Fehlerlogik | Retry, Backoff, Fehlerstatus, Wiederaufnahme | 4 | S9 | Sync | 6.2, 6.3 | Retry-System | Soll |
| 6.5 | Sync | Konfliktregeln | Update/Delete-Konflikte, Dubletten, Priorisierungsregeln | 6 | S10 | Sync + Product | 6.2, 6.3 | Konfliktmatrix V1 | Soll |
| 6.6 | Sync | Sync-UI | Status, letzte Sync-Zeit, Fehler, manuelle Aktionen | 5 | S10 | Desktop + Sync | 6.2–6.5 | Sync-Oberfläche | Soll |
| 6.7 | Sync | Offline-Testszenarien | Netzverlust, Reconnect, konkurrierende Änderungen | 5 | S10 | QA + Sync | 6.2–6.6 | Testkatalog Sync | Soll |

**Teilaufwand Bereich 6:** **39 PT**

### 3.7 PSP-Struktur – Qualität, Betrieb und Pilot

| PSP | Ebene | Arbeitspaket | Beschreibung | Aufwand (PT) | Sprint | Owner | Abhängigkeiten | Ergebnis | Priorität |
|---|---|---|---|---:|---|---|---|---|---|
| 7.1 | QA | Teststrategie | Unit-, API-, UI-, Integrations- und Sync-Tests definieren | 4 | S6 | QA / Tech Lead | 2.x, 3.x | Testkonzept | Muss |
| 7.2 | QA | Testautomatisierung | Basistests und Testpipeline für Backend, Desktop, Web | 8 | S7–S9 | QA + Devs | 7.1 | Automatisierte Testbasis | Soll |
| 7.3 | Betrieb | Observability | Logs, Audit, Sync-Logs, Healthchecks, Metriken | 5 | S9 | Backend | 3.1, 3.7, 6.x | Betriebs-Transparenz | Soll |
| 7.4 | Betrieb | Deployment Staging | Reverse Proxy, Compose, Secrets, Staging-Setup, Backups | 6 | S9 | DevOps | 3.x, 5.x | Staging-Umgebung | Muss |
| 7.5 | Betrieb | Restore- und Backup-Test | Backup/Restore praktisch nachweisen | 3 | S10 | DevOps | 7.4 | Restore-Nachweis | Soll |
| 7.6 | Pilot | Pilotvorbereitung | Pilotanwender, Daten, Supportkanal, Schulungsunterlagen | 4 | S10 | PM / Product | 4.x, 5.x, 7.4 | Pilotpaket | Muss |
| 7.7 | Pilot | Pilotbetrieb | Pilotphase, Feedback, Bugfixing, Nachpriorisierung | 10 | S11 | Alle | 7.6 | Pilotbericht | Muss |
| 7.8 | Projekt | Go-Live-Entscheidung | Bewertung, Restmängel, Freigabe oder Verlängerung | 2 | S11 | PM / Stakeholder | 7.7 | Freigabeentscheidung | Muss |

**Teilaufwand Bereich 7:** **42 PT**

### 3.8 Gesamtaufwand

| Bereich | Aufwand |
|---|---:|
| 1. Projekt und Architektur | 25 PT |
| 2. Fachmodell, Daten, API | 28 PT |
| 3. Backend | 48 PT |
| 4. Desktop | 49 PT |
| 5. Web | 27 PT |
| 6. Sync | 39 PT |
| 7. Qualität, Betrieb, Pilot | 42 PT |
| **Gesamt** | **258 PT** |

***

## 4. Detaillierte Tabellenstruktur für Backlog, Import und Steuerung

Die folgende Struktur ist so geschnitten, dass sie direkt in **Jira, Notion, OpenProject, Excel oder eine SQL-Tabelle** überführt werden kann. Der Aufbau mit PSP-Code, Arbeitspaket, Owner, Aufwand, Abhängigkeiten und Ergebnis entspricht dem Zweck eines Projektstrukturplans als steuerbares Planungsgerüst.[3][4][2]

### 4.1 Empfohlene Spaltenstruktur

| Spalte | Typ | Beschreibung | Beispiel |
|---|---|---|---|
| `PSP_Code` | Text | Eindeutiger Code aus dem Projektstrukturplan | `4.6` |
| `Bereich` | Text | Oberbereich wie Backend, Desktop, Web, Sync | `Desktop` |
| `Ebene` | Text | Projekt, Architektur, Modul, Arbeitspaket | `Arbeitspaket` |
| `Titel` | Text | Kurzer Name des Pakets | `Kernscreens Depots` |
| `Beschreibung` | Text | Konkrete inhaltliche Beschreibung | `Listen, Detail, Formular, Suche` |
| `Ziel` | Text | Welches Ergebnis erreicht werden soll | `Nutzbare Depot-UI` |
| `Owner` | Text | Hauptverantwortliche Rolle | `Desktop Lead` |
| `Mitwirkende` | Text | Weitere Rollen | `Backend, QA` |
| `Priorität` | Text | Muss / Soll / Kann | `Muss` |
| `Aufwand_PT` | Zahl | Schätzung in Personentagen | `6` |
| `Sprint_Start` | Text | Start-Sprint | `S6` |
| `Sprint_Ende` | Text | End-Sprint | `S6` |
| `Abhängigkeiten` | Text | PSP-Codes vorgelagerter Pakete | `4.3, 4.4` |
| `Risiko` | Text | Hauptrisiko | `API-Änderungen` |
| `Akzeptanzkriterien` | Text | Definition für fachliche Abnahme | `Depotliste, Suche und Detailansicht funktionsfähig` |
| `Lieferobjekt` | Text | Dokument, Modul, Release, UI, Service | `Desktop-Modul` |
| `Status` | Text | Offen / In Arbeit / Blockiert / Done | `Offen` |
| `Meilenstein` | Text | Zugehöriger Meilenstein | `M5` |
| `Kommentar` | Text | Freitext für PM/Review | `Abhängig von finalem API-Vertrag` |

### 4.2 Importfähige Master-Tabelle

> Diese Tabelle ist die eigentliche Masterstruktur für dein Projektcontrolling.

| PSP_Code | Bereich | Titel | Owner | Priorität | Aufwand_PT | Sprint_Start | Sprint_Ende | Abhängigkeiten | Meilenstein | Lieferobjekt |
|---|---|---|---|---|---:|---|---|---|---|---|
| 1.1 | Projekt | Projektauftrag und Scope | PM / Tech Lead | Muss | 3 | S1 | S1 | — | M1 | Projektauftrag |
| 1.2 | Projekt | Fachlicher MVP-Scope | Product | Muss | 4 | S1 | S1 | 1.1 | M1 | MVP-Katalog |
| 1.3 | Projekt | Rollen- und Rechtebild | Product + Backend | Muss | 3 | S1 | S1 | 1.2 | M1 | Rollenmatrix |
| 1.4 | Architektur | Zielarchitektur | Architect | Muss | 4 | S1 | S1 | 1.1 | M1 | Architekturübersicht |
| 1.5 | Architektur | Modulkonzept | Architect | Muss | 4 | S2 | S2 | 1.4 | M2 | Modulkonzept |
| 1.6 | Architektur | ADRs | Architect | Soll | 3 | S2 | S2 | 1.4 | M2 | ADR-Sammlung |
| 1.7 | Projekt | Projektsetup | Tech Lead | Muss | 4 | S2 | S2 | 1.1 | M2 | Dev-Setup |
| 2.1 | Fach | Domänenmodell | Backend Lead | Muss | 5 | S2 | S2 | 1.2, 1.4 | M2 | Domain Model |
| 2.2 | Daten | Server-Datenmodell | Backend | Muss | 6 | S3 | S3 | 2.1 | M3 | PostgreSQL-Schema |
| 2.3 | Daten | Lokales Datenmodell | Desktop | Muss | 4 | S3 | S3 | 2.1 | M3 | SQLite-Schema |
| 2.4 | API | API-Vertrag | Backend | Muss | 6 | S3 | S3 | 2.1 | M3 | OpenAPI |
| 2.5 | Sicherheit | Sicherheitskonzept | Backend | Muss | 4 | S3 | S3 | 2.4 | M3 | Security-Konzept |
| 2.6 | Daten | Migrationsstrategie | Backend | Soll | 3 | S3 | S3 | 2.2 | M3 | Migrationskonzept |
| 3.1 | Backend | Backend-Grundgerüst | Backend | Muss | 6 | S4 | S4 | 2.4, 2.5 | M4 | API-Basis |
| 3.2 | Backend | Auth und Benutzer | Backend | Muss | 7 | S4 | S4 | 3.1 | M4 | Auth-Modul |
| 3.3 | Backend | Depotmodul | Backend | Muss | 6 | S4 | S4 | 3.1 | M4 | Depot-API |
| 3.4 | Backend | Präparatemodul | Backend | Muss | 6 | S5 | S5 | 3.1 | M4 | Präparate-API |
| 3.5 | Backend | Bestandsmodul | Backend | Muss | 8 | S5 | S5 | 3.3, 3.4 | M4 | Bestands-API |
| 3.6 | Backend | Reporting-Basis | Backend | Soll | 5 | S5 | S5 | 3.3, 3.4, 3.5 | M4 | Reporting V1 |
| 3.7 | Backend | Audit und Historie | Backend | Soll | 5 | S6 | S6 | 3.2, 3.5 | M5 | Audit-Modul |
| 3.8 | Backend | Hintergrundjobs | Backend | Soll | 5 | S6 | S6 | 3.6 | M5 | Job-System |
| 4.1 | Desktop | Desktop-Neuschnitt | Desktop Lead | Muss | 6 | S4 | S4 | 1.5, 2.3 | M4 | Client-Grundgerüst |
| 4.2 | Desktop | Konfiguration | Desktop | Muss | 3 | S4 | S4 | 4.1 | M4 | Config-Modul |
| 4.3 | Desktop | Local Repository | Desktop | Muss | 6 | S5 | S5 | 2.3, 4.1 | M5 | Local Data Layer |
| 4.4 | Desktop | API Repository | Desktop | Muss | 6 | S5 | S5 | 2.4, 4.1 | M5 | Remote Data Layer |
| 4.5 | Desktop | Modussteuerung | Desktop | Muss | 4 | S6 | S6 | 4.3, 4.4 | M5 | Betriebsmodus |
| 4.6 | Desktop | Kernscreens Depots | Desktop | Muss | 6 | S6 | S6 | 4.3, 4.4 | M5 | Depot-UI |
| 4.7 | Desktop | Kernscreens Präparate | Desktop | Muss | 6 | S7 | S7 | 4.3, 4.4 | M5 | Präparate-UI |
| 4.8 | Desktop | Kernscreens Bestände | Desktop | Muss | 8 | S7 | S7 | 4.3, 4.4 | M5 | Bestands-UI |
| 4.9 | Desktop | Reporting-Oberfläche | Desktop | Soll | 4 | S8 | S8 | 3.6 | M6 | Reporting-UI |
| 5.1 | Web | Web-Grundgerüst | Web Lead | Muss | 6 | S6 | S6 | 2.4, 3.2 | M5 | Web-Basis |
| 5.2 | Web | Depot-Views | Web | Muss | 5 | S7 | S7 | 5.1, 3.3 | M6 | Depot-Webmodul |
| 5.3 | Web | Präparate-Views | Web | Muss | 5 | S7 | S7 | 5.1, 3.4 | M6 | Präparate-Webmodul |
| 5.4 | Web | Bestands-Views | Web | Muss | 7 | S8 | S8 | 5.1, 3.5 | M6 | Bestands-Webmodul |
| 5.5 | Web | Reporting-Basis | Web | Soll | 4 | S8 | S8 | 5.1, 3.6 | M6 | Reporting-Webmodul |
| 6.1 | Sync | Sync-Datenmodell | Sync Lead | Soll | 5 | S8 | S8 | 2.3, 2.4 | M6 | Sync-Schema |
| 6.2 | Sync | Push-Engine | Sync | Soll | 7 | S9 | S9 | 6.1, 4.4 | M7 | Push V1 |
| 6.3 | Sync | Pull-Engine | Sync | Soll | 7 | S9 | S9 | 6.1, 4.3 | M7 | Pull V1 |
| 6.4 | Sync | Retry- und Fehlerlogik | Sync | Soll | 4 | S9 | S9 | 6.2, 6.3 | M7 | Retry-System |
| 6.5 | Sync | Konfliktregeln | Sync + Product | Soll | 6 | S10 | S10 | 6.2, 6.3 | M7 | Konfliktmatrix |
| 6.6 | Sync | Sync-UI | Desktop + Sync | Soll | 5 | S10 | S10 | 6.2, 6.3, 6.5 | M7 | Sync-Oberfläche |
| 6.7 | Sync | Offline-Testszenarien | QA + Sync | Soll | 5 | S10 | S10 | 6.2–6.6 | M7 | Sync-Testkatalog |
| 7.1 | QA | Teststrategie | QA / Tech Lead | Muss | 4 | S6 | S6 | 2.x, 3.x | M5 | Testkonzept |
| 7.2 | QA | Testautomatisierung | QA + Devs | Soll | 8 | S7 | S9 | 7.1 | M7 | Testpipeline |
| 7.3 | Betrieb | Observability | Backend | Soll | 5 | S9 | S9 | 3.1, 3.7, 6.x | M7 | Monitoring/Logs |
| 7.4 | Betrieb | Deployment Staging | DevOps | Muss | 6 | S9 | S9 | 3.x, 5.x | M7 | Staging |
| 7.5 | Betrieb | Restore- und Backup-Test | DevOps | Soll | 3 | S10 | S10 | 7.4 | M7 | Restore-Nachweis |
| 7.6 | Pilot | Pilotvorbereitung | PM / Product | Muss | 4 | S10 | S10 | 4.x, 5.x, 7.4 | M7 | Pilotpaket |
| 7.7 | Pilot | Pilotbetrieb | Alle | Muss | 10 | S11 | S11 | 7.6 | M8 | Pilotbericht |
| 7.8 | Projekt | Go-Live-Entscheidung | PM / Stakeholder | Muss | 2 | S11 | S11 | 7.7 | M8 | Freigabe |

### 4.3 Empfohlene Epic-Struktur für Jira/Notion/OpenProject

| Epic-Code | Epic | Enthält PSP |
|---|---|---|
| E-01 | Projekt und Architektur | 1.1–1.7 |
| E-02 | Fachmodell, Daten und API | 2.1–2.6 |
| E-03 | Backend | 3.1–3.8 |
| E-04 | Desktop | 4.1–4.9 |
| E-05 | Web | 5.1–5.5 |
| E-06 | Sync | 6.1–6.7 |
| E-07 | Qualität und Betrieb | 7.1–7.5 |
| E-08 | Pilot und Freigabe | 7.6–7.8 |

### 4.4 Beispiel für Ticket-Hierarchie

| Ebene | Beispiel |
|---|---|
| Initiative | ND-Hub Plattform-Neustart |
| Epic | E-03 Backend |
| Feature | Bestandsverwaltung |
| Arbeitspaket / Story | 3.5 Bestandsmodul |
| Subtasks | API-Routen, Validierung, Tests, Historie, Review |

***

## 5. Steuerung, Risiken und konkrete Arbeitsweise

Für ND-Hub würde ich die Projektsteuerung bewusst schlank halten: Sprint Planning, Weekly Status, Sprint Review und Retrospektive reichen für ein kleines Kernteam in der Regel aus. Die Kombination aus Projektstrukturplan, Arbeitspaketen und Sprintplanung bildet dann die operative Steuerung.[1][2][5]

### 5.1 Steuerungsrhythmus

| Termin | Frequenz | Inhalt |
|---|---|---|
| Sprint Planning | alle 2 Wochen | Auswahl und Zuschnitt der Sprint-Pakete |
| Weekly Status | wöchentlich | Risiken, Blocker, Entscheidungen |
| Sprint Review | alle 2 Wochen | Ergebnisdemo gegen Akzeptanzkriterien |
| Retro | alle 2 Wochen | Prozessverbesserung |
| Architektur-Review | monatlich | ADRs, Schnittstellen, technische Leitplanken |
| Pilot-Review | ab S10/S11 | Rückmeldungen, Go-Live-Reife |

### 5.2 Definition of Ready

| Kriterium | Beschreibung |
|---|---|
| Fachlich beschrieben | Klarer Nutzen und Scope |
| Verantwortlich | Owner benannt |
| Akzeptanzkriterien | Prüffähige Ergebnisse definiert |
| Abhängigkeiten klar | Vorläuferpakete benannt |
| Aufwand grob geschätzt | PT vorhanden |
| Sprintfähig | Innerhalb eines Sprints realistisch startbar |

### 5.3 Definition of Done

| Kriterium | Beschreibung |
|---|---|
| Implementiert | Code fertig |
| Getestet | Relevante Tests vorhanden |
| Reviewed | Fachlich/technisch geprüft |
| Dokumentiert | Relevante Doku oder ADR ergänzt |
| Betriebsfähig | Logging/Config berücksichtigt |
| Abnahmefähig | Akzeptanzkriterien erfüllt |

### 5.4 Risikoregister

| Risiko | Auswirkung | Eintritt | Gegenmaßnahme |
|---|---|---|---|
| Sync-Logik komplexer als geplant | Hoch | Hoch | Früher Prototyp ab S8, Testkatalog, Konfliktmatrix |
| API ändert sich zu spät | Hoch | Mittel | OpenAPI früh festziehen, Versionsregeln |
| Scope-Wachstum | Hoch | Hoch | MVP hart schützen, Change-Board light |
| Desktop und Web driften fachlich auseinander | Mittel | Mittel | Fachlogik serverzentriert halten |
| Reporting frisst zu viel Zeit | Mittel | Mittel | Nur Basisberichte im MVP |
| Testabdeckung zu spät | Mittel | Mittel | Teststrategie ab S6, Pipeline ab S7 |
| Betrieb/Restore nicht real geübt | Hoch | Mittel | Restore-Test S10 verpflichtend |

### 5.5 Operativer Start

Der konkrete Startpunkt ist **Sprint 1** mit Projektauftrag, MVP-Scope, Rollenbild und Zielarchitektur. Direkt danach folgt in **Sprint 2** der Architekturschnitt mit Modulkonzept und Domain Model, damit ab Sprint 3 Datenmodell und API nicht auf unscharfen Annahmen aufbauen.[6][2]

Ab **Sprint 4** sollte nur noch gegen die freigegebene Architektur entwickelt werden. Neue Anforderungen gehen dann regulär ins Backlog und verdrängen nicht ungeplant bereits laufende Arbeitspakete.

***

**Arbeitsdokument Ende.**

Quellen
[1] Beispiel für ein Arbeitspaket https://projekte-leicht-gemacht.de/blog/projektmanagement/klassisch/projektplanung/arbeitspakete/
[2] Projektstrukturplan erstellen - Projektron GmbH https://www.projektron.de/blog/detailseite/projektstrukturplan-3799/
[3] Arbeitspaket - Projektmanagement nach ISO21500 https://www.iso21500.de/de/projektmanagement-glossar/arbeitspaket/
[4] Arbeitspaket: Definition | Inhalte | Erläuterung https://www.projektmagazin.de/glossarterm/arbeitspaket
[5] Die 5 Projektmanagement-Phasen im Überblick! [2026] - Asana https://asana.com/de/resources/project-management-phases
[6] Planungsphase – DMS/eAkte-Wiki https://wiki.uni-bielefeld.de/eakte/index.php/Planungsphase
