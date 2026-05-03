# Phase 1: Supply Chain, Malware-Resilienz und SAST

## 1.1 Dependency Integrity (npm)

- [`package.json`](../frontend-react/package.json) nutzt Semver-Ranges (`^`). Für Releases **Lockfile** ([`package-lock.json`](../frontend-react/package-lock.json)) versionieren und `npm ci` in CI verwenden.
- Keine zusätzlichen Runtime-Pakete außer `react`, `react-dom`, `leaflet` – kleine Angriffsfläche.

## 1.2 Dependency Integrity (Python)

- [`requirements.txt`](../requirements.txt) entspricht weitgehend dem Desktop-Client-Stack plus **PyMySQL** für MariaDB-Pfad.
- Gleiche Empfehlung: Pins/Lock für reproduzierbare Builds.

## 1.3 SAST / Heuristiken (Frontend)

Manuelle Stichprobe in [`frontend-react/src/main.tsx`](../frontend-react/src/main.tsx):

- **Kein** `dangerouslySetInnerHTML`, **kein** `eval` / `new Function` in der Quelle.
- **Hilfsfunktion** `escapePopupHtml` für Leaflet-Popup-Inhalte (XSS-Minderung bei Karten-Popups).
- API-Fehler: JSON `detail` wird als Nutzertext genutzt – bei kontrolliertem Backend unkritisch; bei kompromittiertem Backend theoretisch **reflektierter XSS** in UI-Strings (niedriges Risiko, trotzdem Content-Security-Policy erwägen).

## 1.4 JavaScript-Bundle / Build

- Vite bündelt React; keine eingebetteten Drittanbieter-Skripte aus CDN im Quell-Einstieg (lokale Assets).
- **Dev-Server:** siehe CVE-Matrix (esbuild/vite) – betrifft primär `npm run dev`, nicht das statische Produkt aus `vite build`.

## 1.5 Docker / Image

- Multi-Stage-Build prüfen (siehe [`Dockerfile`](../Dockerfile)): minimale Runtime-Images bevorzugen, keine Build-Secrets in Layern.

## 1.6 Malware (Prozess)

- Wie beim Desktop-Review: regelmäßige `npm audit` / OSV, Review neuer Dependencies, keine dynamischen `import()` aus Nutzer-URLs.
