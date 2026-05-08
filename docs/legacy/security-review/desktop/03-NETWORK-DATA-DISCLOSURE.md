!!! warning "Archiviert"
    Diese Originaldatei ist archiviert. Der aktuelle, konsolidierte Stand befindet sich in der Enterprise-Dokumentation (siehe Hauptnavigation links).

# Phase 3: Netzwerk, „Telemetrie“ und Datenabflüsse

## Begriff Telemetrie (Review-Definition)

Jeder **absichtliche oder unbeabsichtigte** Abfluss von Daten aus dem Prozess: Netzwerk, Logdateien, Crash-Dumps, Drittanbieter-Bibliotheken mit Netzwerkzugriff.

## Ergebnis: Produkt-Telemetrie

Im überprüften Quelltext **keine** dedizierten Drittanbieter-Telemetrie-SDKs (Sentry, Segment, Google Analytics o. ä.). UI-Begriffe wie „Analytics“ beziehen sich auf **lokale Auswertungen** (Berichte/Diagramme), nicht auf Cloud-Tracking.

## Netzwerk-Inventory (Python, Anwendung)

| Modul / Datei | Mechanismus | Ziel / Zweck | Daten |
|---------------|-------------|--------------|--------|
| [core/data_access_layer.py](../core/data_access_layer.py) | `urllib.request.urlopen` | Konfigurierte `backend_url` + Pfade (`/health`, `/sync/pull`, `/sync/push`, `/auth/…`, `/audit-logs`, …) | JSON-Payloads inkl. Sync-Daten; Header `Authorization: Bearer <token>` |
| [ui/pages/page_grundeinstellungen/_hauptseite.py](../ui/pages/page_grundeinstellungen/_hauptseite.py) | `urlopen` | Verbindungstest: `{backend_url}/auth/me` | Bearer-Token aus UI-Feld |
| [ui/dialogs/setup_wizard_dialog.py](../ui/dialogs/setup_wizard_dialog.py) | `urlopen` (falls vorhanden) | Setup-/Backend-Prüfungen analog Grundeinstellungen | Konfigurationsabhängig |
| [db_manager.py](../db_manager.py) | `smtplib.SMTP` / `SMTP_SSL` | Benutzerkonfigurierter SMTP-Host | E-Mail-Inhalt, Empfänger, ggf. SMTP-Credentials |

## Netzwerk-Inventory (Browser, eingebettetes Web)

| Datei | Mechanismus | Ziel |
|--------|--------------|------|
| [backend/web/app.js](../backend/web/app.js) | `fetch(path)` | Same-Origin-API unter `/auth/login`, `/auth/avatar`, weitere relative API-Pfade |

Keine fest codierten externen Telemetrie-Endpunkte in der Stichprobe.

## URL-Policy und Risiken

- **`BackendSyncConfig.normalized_base_url`**: Es wird aktuell **kein Zwang auf `https://`** erkannt; ein Angreifer mit Schreibzugriff auf `settings.ini` oder die UI könnte **http://** oder interne URLs setzen (MITM, SSRF-Randbedingungen je nach Umgebung).
- **Empfehlung:** Vor Verwendung Schema auf `https` beschränken oder explizit konfigurierbar machen mit Warnung bei HTTP; `file://` und ähnliche Schemata ablehnen.

## Bibliotheken (Matplotlib, Pandas, …)

- Standardnutzung lädt keine Chart-Daten aus dem Internet; wenn Nutzer **URLs** als Dateinamen in Bibliotheks-APIs verwendet, können transitive `urlopen`-Pfade theoretisch greifen – für ND-Hub-typische Pfade (lokale Dateiauswahl) geringes Restrisiko; in Schulungsmaterial vermerken.

## Logging als Datenabfluss

- Logger `ND-Hub`, `ND-Hub.DataAccess`, etc.: Prüfen, dass bei Fehlern **keine vollen Bearer-Token, SMTP-Passwörter oder Klartext-Passwörter** in Tracebacks landen (insbesondere `str(exc)` aus HTTP-Fehlern).
- In `BackendApiClient._post_json` / `_get_json` werden HTTP-Fehlerdetails aus dem Body gelesen – Inhalt kann servergesteuert sein; **nicht ungefiltert in UI/Logs** für Endnutzer mit maximalem Detailgrad ausgeben.

## Transparenz (Endkunden / IT)

Kurzes Datenblatt sollte kommunizieren:

1. **Hybrid-Sync:** welche Basis-URL, welche Entitäten, Intervall, TLS.
2. **SMTP:** welcher Server, dass Zugangsdaten lokal gespeichert werden.
3. **Kein** Hersteller-Cloud-Telemetrie, falls zutreffend und vertraglich abgesichert.
