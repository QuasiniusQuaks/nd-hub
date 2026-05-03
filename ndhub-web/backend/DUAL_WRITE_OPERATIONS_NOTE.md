# Dual-Write Operations Note

Diese Notiz beschreibt den operativen Umgang mit `ND_HUB_DUAL_WRITE_SQLITE`.

## Grundregel

- Im Normalbetrieb nach Cutover gilt:
  - `ND_HUB_DB_ENGINE=mariadb`
  - `ND_HUB_DUAL_WRITE_SQLITE=0`

`ND_HUB_DUAL_WRITE_SQLITE=1` ist nur ein temporarer Uebergangs- oder
Diagnosemodus und **kein** Dauerzustand fuer den produktiven Betrieb.

## Wann temporar auf `1` setzen?

Nur in klaren Ausnahmefaellen:

1. **Kurzfristige Stabilisierungsphase nach Major-Change**
   - z. B. direkt nach grossem Repository-Refactor.
2. **Gezielter Diagnosezeitraum**
   - wenn MariaDB-Ergebnisse mit SQLite-Spiegel verglichen werden muessen.
3. **Geplanter Canary-Betrieb mit enger Beobachtung**
   - fuer wenige Stunden/Tage und mit klarer Rueckstellung auf `0`.

## Wann **nicht** auf `1` setzen?

- Nicht als Workaround fuer nicht analysierte Produktionsfehler.
- Nicht dauerhaft zur "Sicherheit".
- Nicht waehrend laufender Datenmigrationen ohne klare Datenhoheit.

## Risiken bei `1`

- Hoehere Latenz bei Schreiboperationen.
- Erhoehte Komplexitaet bei Fehlersuche (zwei Write-Ziele).
- Potenzielle Drift-Risiken, falls Mirror-Write temporar fehlschlaegt.

## Operativer Ablauf fuer temporare Aktivierung

1. Change begruenden und Zeitfenster festlegen.
2. `ND_HUB_DUAL_WRITE_SQLITE=1` setzen und Service neu starten.
3. Kern-Smoke ausfuehren (CRUD, Reports, Backup-List).
4. MariaDB und SQLite Counts stichprobenartig vergleichen.
5. Nach Abschluss zwingend auf `ND_HUB_DUAL_WRITE_SQLITE=0` zurueckstellen.
6. Erneuter Kurz-Smoke und Abschlussdokumentation.

## Monitoring-Empfehlung

- API-Fehlerquote fuer Write-Endpunkte beobachten.
- Warnungen zu fehlgeschlagenen Mirror-Writes aktiv auswerten.
- Bei wiederholten Mirror-Warnungen Ursache beheben, nicht dauerhaft auf `1` bleiben.
