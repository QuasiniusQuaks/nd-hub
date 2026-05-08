# Datenschutz

Diese Seite gibt einen technischen und organisatorischen Ueberblick zum
Datenschutz in ND-Hub. Sie ersetzt keine rechtliche Pruefung und keine
projektspezifische Datenschutzfolgenabschaetzung.

## Datenarten in ND-Hub

| Kategorie | Beispiele |
|---|---|
| Stammdaten | Depots, Praeparate, Institutionen, Kontakte (Name, Rolle, Telefon, E-Mail). |
| Bewegungsdaten | Datum, Charge, Verfall, Anzahl, optional Empfaenger und PDF-Anhang. |
| Benutzerdaten | Benutzername, Passwort-Hash, Avatar, Aktivitaeten. |
| Audit | Wer hat wann welche Aktion auf welcher Resource ausgefuehrt. |
| Sync-Metadaten | Cursor, Batch-IDs, Konfliktinformationen. |

## Speicherung

- Datenbank: SQLite-Datei oder MariaDB-Server (im Container).
- Anhaenge: PDF-Dateien unter `/data/uploads`.
- Backups: logische Dumps unter `/data/backups`.
- Logs: standardmaessig ueber Container-Logging; produktiv extern
  zentralisieren.

## Transport

- Browserzugriff: TLS via vorgeschalteten Reverse Proxy empfohlen.
- Backend zu Datenbank: containerinternes Netzwerk im Compose-Stack
  (`ndhub-web` <-> `mariadb`).
- Sync zwischen Desktop und Web-Backend: ueber dieselben REST-Endpunkte
  (HTTPS empfohlen).

## Personenbezogene Daten

- Kontakt- und Benutzerdaten enthalten **personenbezogene Daten**
  (Name, E-Mail).
- Empfaenger-Felder in Bewegungen koennen personenbezogen sein.
- E-Mail-Verlauf enthaelt Inhalte versendeter Mails.

Datenschutzrelevante Massnahmen:

- Zugriffsrechte konsequent ueber Rollen und `user_depot_permissions`
  steuern.
- Loeschen oder Schwaerzen alter Daten gemaess organisatorischer
  Aufbewahrungsregeln.
- Backups verschluesselt aufbewahren (organisatorisch sicherzustellen).

## Pruefungs- und Compliance-Empfehlungen

- DSGVO-Verzeichnis von Verarbeitungstaetigkeiten pflegen.
- Auftragsverarbeitungsvertraege bei Cloud-Hosting beachten.
- Datenschutzfolgenabschaetzung bei groesseren Datenmengen oder
  besonders schutzbeduerftigen Personenkreisen.
- Loesch- und Aufbewahrungskonzepte fuer Backups dokumentieren.

## Datenexport und Auskunft

- Daten lassen sich ueber Reports und CSV-Exporte gezielt extrahieren.
- Audit-Logs ermoeglichen Auskunft zu Aktionen pro Benutzer.
- Backups erlauben technische Wiederherstellung historischer Staende.

## Datenloeschung

- Loeschen von Stammdaten erfolgt ueber die regulaeren CRUD-Operationen.
- Bewegungen werden in der Regel nicht physisch geloescht (Audit- und
  Nachvollziehbarkeitsanforderungen). Eine projektspezifische
  Loeschstrategie ist organisatorisch festzulegen.
