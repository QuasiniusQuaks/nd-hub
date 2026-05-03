# Phase 3: Netzwerk, „Telemetrie“ und Datenabflüsse

## Produkt-Telemetrie

Im Frontend-Quelltext **keine** Analytics-/Crash-SDKs (kein Sentry, Segment, GA).

## Netzwerk-Inventory (Browser)

| Ziel | Mechanismus | Daten / Hinweis |
|------|-------------|-----------------|
| **Same-Origin API** | `fetch(path)` mit relativen Pfaden in [`main.tsx`](../frontend-react/src/main.tsx) (`apiFetch`, Uploads, Backup, …) | Bearer-Token im Header; JSON-Bodies je Route |
| **OpenStreetMap-Kacheln** | `L.tileLayer("https://{s}.tile.openstreetmap.org/...")` (mind. zwei Stellen in `main.tsx`) | **Drittanbieter:** Client-IP, User-Agent, Kartenausschnitt (Zoom/BBOX) gehen an OSM-Server; **Datenschutz-Hinweis** für Betreiber/Nutzer |
| **Keine** weiteren fest codierten HTTPS-URLs im grep-Stichproben-Set | — | — |

## Token-Speicherung

- Sitzungs-Token: **`localStorage`** unter Schlüssel `ndhub_token` (mehrfach gelesen/gesetzt).
- **Risiko:** Bei **XSS** im selben Origin kann Skript-Code das Token lesen. Mitigation: CSP, strikte Output-Escaping, kurze Token-TTL serverseitig, HttpOnly-Cookies als Alternative (größerer Umbau).
- Zusätzlich: Formular-/UI-State in `localStorage` (Autofill-Keys) – geringeres Risiko, aber lokale Datenhaltung dokumentieren.

## Logging / Fehlertexte

- API-Fehlerdetails aus `response.json().detail` werden dem Nutzer angezeigt – kein absichtliches Logging von Secrets im Frontend; Backend-Logs separat prüfen (nicht Gegenstand dieses reinen Web-Frontend-Reviews).

## Transparenz (IT / Datenschutz)

Datenblatt sollte nennen:

1. Welche **API**-Endpunkte die SPA nutzt (Same-Origin).
2. **OSM-Kartenkacheln** (externe Anfragen).
3. Speicherort **Token** (`localStorage`).
