# Produktbeschreibung

## Vision

ND-Hub ist eine **digitale Plattform zur strukturierten Verwaltung von
Notfalldepots**. Sie ersetzt manuelle Listen, Excel-basierte Bestandsfuehrung
und insellastige Einzelloesungen durch einen klaren, auditierbaren Prozess fuer
Depots, Praeparate, Bewegungen und Verfallsdaten.

## Zwei Produktlinien, ein fachlicher Kern

| Produkt | Beschreibung | Primaerer Einsatz |
|---|---|---|
| **ND-Hub Desktop Client** | PySide6-Desktopanwendung mit moderner UI und integriertem FastAPI-Modul fuer lokale Web-Hilfen. | Lokaler Arbeitsplatzbetrieb, performantes Werkzeug am Standort. |
| **ND-Hub Webanwendung** | FastAPI-Backend + React/Vite-Frontend, Docker-Deployment, MariaDB-Faehigkeit. | Zentrale, browserbasierte Bereitstellung, standortuebergreifend. |

Beide Loesungen verfolgen dasselbe Ziel:

- **betriebliche Sicherheit erhoehen**,
- **manuelle Aufwaende reduzieren**,
- **revisionsfaehige Daten** liefern.

## Wertversprechen

### Fuer Fachanwender

- Klare, gefuehrte Bedienoberflaeche fuer Depotpflege, Bewegungserfassung
  und Verfallskontrolle.
- Schnelles Auffinden von Bewegungen und Bestaenden ueber leistungsfaehige
  Filter und Suchen.
- Strukturierte E-Mail-Workflows mit Empfaengervorschau und Versandhistorie.

### Fuer Administration und IT

- Rollenbasierter Zugriff mit Selbstschutzregeln fuer Admin-Konten.
- Audit-Logs ueber alle relevanten Aktionen.
- Backup/Restore mit Format- und Groessenpruefung.
- Saubere Engine-Umschaltung zwischen SQLite und MariaDB ueber
  `ND_HUB_DB_ENGINE`.

### Fuer Entscheider und Compliance

- Auditierbare Prozesse statt verstreuter Excel-Dateien.
- Exportfaehige Berichte (CSV, PDF, PPTX) fuer Steuerung und Pruefung.
- Skalierbarer Pfad: Start lokal (Desktop) oder zentral (Web), Ausbau
  schrittweise moeglich.

## Produktstatus (aktuell)

- **Aktuelle Version:** `v0.5`
- **Bereitstellungsmodelle:** Desktop (lokal) und Web (zentral, containerfaehig)
- **Datenbankstrategie:** SQLite und MariaDB unterstuetzt; MariaDB-Cutover
  und Smoke-Checks dokumentiert.
- **Sync:** Hybrid-Sync v1 zwischen Desktop und Web (Push/Pull, idempotent).
- **Quality-Gate:** Stability/Acceptance-Suite mit `28 passed` (Stand
  Sprint-Abschluss).

## Abgrenzung

ND-Hub konzentriert sich auf **Notfalldepot-Prozesse**. Die Plattform
ersetzt nicht:

- Warenwirtschaft oder vollstaendige ERP-Systeme,
- Buchhaltungs- oder Rechnungsstellungssysteme,
- mobile Lagerprozesse mit Industrie-Scannern (kein eigener Stack hierfuer).

Sie integriert sich aber durch Exportformate und (perspektivisch) APIs in
bestehende Systemlandschaften.
