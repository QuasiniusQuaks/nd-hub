# Konzept: Analytics Control Center (ND-Hub Desktop)

**Status:** Entwurf v0.1 — wartet auf Rücksprache mit Imperator
**Datum:** 2026-06-17
**Ziel:** Analyse-Bereich von "klassisch mit Sidebar-Filter" auf "State-of-the-Art Kontrollzentrum mit Wow-Effekt"

---

## 1. Status-Quo (was nicht funktioniert)

| Schwäche | Auswirkung |
|---|---|
| Sidebar-Filter links, Listen-Selection (Multi-Select-Listbox) | Altbacken, 2010er-Look |
| 5 separate Buttons "Bewegungsanalyse / Bestandsentwicklung / Ranking / Matrix / Verfall" | User muss **wissen** welche Analyse er will — keine Inspiration |
| 1367 Zeilen in einer Datei (`page_auswertungen.py`) | Nicht wartbar, alles copy-paste |
| Matplotlib-Charts inline gerendert, kein Hover-Tooltip | User muss raten was die Kurve bedeutet |
| Keine Insights / "Heute auffällig" | Keine Aha-Momente |
| Kein Cross-Filtering | Klick auf "Top-Akteur XY" führt nirgends hin |
| KPIs sind simple Label+Value, keine Sparklines, keine Vergleiche | Wirken statisch |
| Kein Dashboard-Persistenz (Layout wird nicht gespeichert) | Jeder Start = Standard-Layout |
| Keine Vorlagen/Saved-Views ("Mein Depot-Morgenreport") | Power-User können nichts wiederverwenden |
| DB-Layer hat nur 3 spezifische Analytics-Methoden, Rest in der UI | Schicht-Trennung kaputt |

---

## 2. Vision: Analytics Control Center

Statt "5 Buttons + Sidebar" wird der Analyse-Bereich zu einem **dreistufigen Erlebnis**:

### 2.1 Hero-Layer: Insight-Banner (above the fold)
- Große, animierte **"Heute"-Karten** (3-4 Stück):
  - 🚨 *"3 Präparate verfallen in den nächsten 30 Tagen"*
  - ✅ *"Depot Berlin-Mitte ist 8% über Soll — Trend stabil"*
  - ⚠️ *"2 Depots ohne Bewegung >180 Tage"*
  - 📈 *"Diese Woche 12% mehr Zugang als letzte"*
- Jede Karte **klickbar** → drillt direkt in die passende Detail-View
- Auto-Refresh jede 5 Minuten + Pull-to-Refresh

### 2.2 Tab-Layer: 4 Analyse-Cluster (statt 5 verstreute Buttons)
- **📦 Bestand** — Heatmap, Soll/Ist-Vergleich, Top-Abweichungen
- **🔄 Bewegungen** — Flow, Ranking, Zeitreihen
- **⏳ Verfall** — Prognose, Risiko-Score, Charge-Trace
- **🛡️ Compliance** — Audit-Trail, User-Aktivität, Auffälligkeiten

Jeder Tab ist ein eigenes Widget mit eigener Sidebar, aber einheitlichem Design-System.

### 2.3 Detail-Layer: Interaktive Charts
- **Plotly-artige Interaktivität** (mit Matplotlib + custom Mouse-Events): Hover-Tooltips, Zoom, Click-to-Drill
- **Cross-Filter**: Klick auf "Depot A" in einem Chart filtert alle anderen Charts
- **Time-Range-Picker** global (7d / 30d / 90d / 1y / Custom) — wirkt auf alle Charts
- **Vergleichs-Modus**: "vs. Vorjahr" oder "vs. Durchschnitt" toggle

---

## 3. Design-System (Modern, State-of-the-Art)

Inspiration: Linear, Vercel, Hynex Healthcare, MediFlex.

| Element | Spec |
|---|---|
| **Theme** | AppleTheme beibehalten, aber **Glassmorphismus-Touch** (semi-transparente Cards mit `backdrop-filter: blur(20px)`) |
| **Spacing** | 8px-Grid, 24px Section-Padding |
| **Cards** | 16px Border-Radius, Subtile Shadow, 1px Hairline-Border in Light-Mode |
| **Typo** | Inter / SF Pro, 4 Größen (12/14/16/20), Gewichte 400/500/600/700 |
| **Farben** | Apple-Theme erweitern um `accent.primary`, `accent.success`, `accent.warning`, `accent.danger` (semantisch) |
| **Animation** | 200ms ease-out für Hover, 300ms spring für State-Change (z.B. KPI-Update mit Zähler-Animation) |
| **Empty States** | Illustration + 1-Satz-Hilfetext + "Insights generieren" CTA |
| **Loading** | Skeleton-Loader (kein Spinner) — Apple-Health-Style |

### Wow-Details
- **Number-Counter-Animation** wenn KPIs sich ändern (Zähler rollt von 0 auf neuen Wert)
- **Sparkline in jeder KPI-Card** (Mini-Chart 7-Tage-Verlauf)
- **Color-coded Status-Dot** auf Cards (grün/gelb/rot je nach Schwellwert)
- **"Auto-Insights" Panel**: Generiert 3 Bullet-Points "Was ist diese Woche passiert?"

---

## 4. Feature-Inventar (was reinkommt)

### Phase 1: Foundation (2-3 Tage, vorzeigbar)
1. ✨ **Insight-Banner** (4 Smart-Cards oben)
2. ✨ **4-Tab-Cluster** (Bestand / Bewegungen / Verfall / Compliance)
3. ✨ **Globale Filter-Leiste** (Zeitraum + Depots/Präparate, oben sticky)
4. ✨ **Sparkline-KPIs** (jede KPI-Card hat 7-Tage-Trend)
5. ✨ **Number-Counter-Animation**
6. ✨ **Neue AnalyticsPage** (aufteilen der 1367-Zeilen-Datei in 5 Module)

### Phase 2: Interaktivität (2-3 Tage)
7. **Hover-Tooltips** auf allen Charts
8. **Click-to-Drill** (Klick auf Bar → Detail-Liste)
9. **Cross-Filter** (Klick auf Series filtert andere Charts)
10. **Vergleichs-Modus** (vs. Vorjahr)
11. **Saved Views / Templates** (User speichert Filter-Set als "Mein Morgen-Report")
12. **Dashboard-Layout persistent** (Position der Cards wird gespeichert)

### Phase 3: Wow-Features (2-3 Tage, das Salz in der Suppe)
13. **"Was ist passiert?" Auto-Insights** (3 Bullet-Points, NL-generiert)
14. **Anomalie-Detection** (statistische Ausreißer mit Highlight)
15. **Forecast-Band** (Verfall-Prognose mit Konfidenzintervall)
16. **Export als interaktives HTML** (Self-contained, offline teilbar)
17. **PDF-Reports neu** (Apple-Health-Style Annual-Report)

### Phase 4: Power-User (1-2 Tage)
18. **Custom-SQL-Query-Tab** (für Power-User, mit Save)
19. **Saved-Reports-Bibliothek** (Reports browsen + re-run)
20. **Email-Schedule** (wöchentlicher Report als PDF)

---

## 5. Architektur-Refactor (parallel zu Phase 1)

**Problem:** `page_auswertungen.py` ist 1367 Zeilen Monolith.

**Lösung — Modul-Architektur:**

```
ui/pages/analytics/
├── __init__.py
├── analytics_page.py           # Container mit Tabs
├── _widgets/                   # Wiederverwendbare Custom-Widgets
│   ├── insight_banner.py
│   ├── sparkline_kpi_card.py
│   ├── glass_card.py
│   ├── animated_counter.py
│   ├── date_range_picker.py
│   └── chart_tooltip_event.py  # Matplotlib-Hover-Handler
├── _charts/                    # Chart-Wrapper
│   ├── base_chart.py           # AbstractCanvas mit Tooltip-Filter-Animation
│   ├── flow_chart.py           # Sankey-ähnlich
│   ├── heatmap.py
│   ├── forecast_band.py
│   └── ranking_bar.py
├── _filters/
│   ├── global_filter_bar.py
│   └── cross_filter_state.py   # Singleton für Cross-Chart-Filtering
├── tabs/
│   ├── tab_bestand.py
│   ├── tab_bewegungen.py
│   ├── tab_verfall.py
│   └── tab_compliance.py
├── _insights/
│   └── auto_insights.py        # Generiert "Was ist passiert?"-Bullets
└── _db/
    └── analytics_queries.py    # Alle Analytics-SQL-Queries zentralisiert
```

**DB-Layer-Erweiterung:** 12+ neue Methoden in `db_manager.py` für die neuen Analysen:
- `get_anomalies(threshold_std=2)` — statistische Ausreißer
- `get_forecast(months=12)` — Verfall-Forecast mit Trend
- `get_period_comparison(period_a, period_b)` — für Vergleichsansicht
- `get_top_movers(direction='in'|'out', limit=10)`
- `get_inventory_turnover()` — Lagerumschlagshäufigkeit
- `get_dead_stock(days=180)` — Präparate ohne Bewegung
- `get_user_activity_heatmap()` — Compliance-Tab
- etc.

---

## 6. Konkrete UI-Mockups (ASCII-Skizze)

### 6.1 Hauptansicht
```
┌─────────────────────────────────────────────────────────────────────┐
│ ☰  📊 Analytics Control Center           🔍 [Filter: Alle Depots]  │
│                                              [Zeit: 7T ▼] [⚙️]      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────┐│
│  │ 🚨 3         │  │ ✅ Berlin    │  │ ⚠️ 2 Depots  │  │ 📈 +12% ││
│  │ Verfälle     │  │ +8% über     │  │ ohne Aktiv.  │  │ Zugang  ││
│  │ <30 Tage     │  │ Soll         │  │ >180 Tage    │  │ vs.     ││
│  │ [Sparkline↗] │  │ [Sparkline→] │  │ [Sparkline↘] │  │ letzte W││
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────┘│
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  [📦 Bestand] [🔄 Bewegungen] [⏳ Verfall] [🛡️ Compliance]  │  │
│  ├──────────────────────────────────────────────────────────────┤  │
│  │                                                              │  │
│  │   📊 Soll/Ist-Heatmap (Depot × Präparat)                     │  │
│  │   ┌──────┬──────┬──────┬──────┐                              │  │
│  │   │ 🟢 0 │ 🟢 +1│ 🔴 -3│ 🟢 +2│  ← Hover: tooltip          │  │
│  │   │ 🟢 +1│ 🟡 -1│ 🟢 +4│ 🟢 0 │  ← Click: filtert andere   │  │
│  │   └──────┴──────┴──────┴──────┘                              │  │
│  │                                                              │  │
│  │   📈 Verlauf 30 Tage        🏆 Top 5 Abweichungen            │  │
│  │   [Line-Chart, animated]   [Ranking, sparkline je Reihe]    │  │
│  │                                                              │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 6.2 Drill-Down (Klick auf Insight-Card)
```
┌─────────────────────────────────────────────────────────────────────┐
│ ← Zurück   🚨 Verfälle in den nächsten 30 Tagen                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Präparat       Depot        Charge    Verfall     Menge    │   │
│  │────────────────────────────────────────────────────────────│   │
│  │ Morphin 10mg   Berlin-Mitte  M2401    12.07.2026  24 EH   │   │
│  │ Adrenalin      Hamburg       A8811    15.07.2026  12 EH   │   │
│  │ Noradrenalin   München       N4402    22.07.2026  8 EH    │   │
│  │ [Bulk-Action:  ☑ Export als CSV  ☑ Mail an Depotleitung] │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  📈 Forecast: bei aktuellem Verbrauch weitere 12 Verfälle in 60T   │
│  💡 Empfehlung: 3 Depots sollten umverteilen                        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 7. Tech-Entscheidungen

| Frage | Vorschlag | Begründung |
|---|---|---|
| Matplotlib beibehalten? | ✅ Ja + Custom-Interaktivität | Schon da, gut für PDF-Export |
| Plotly/QtCharts? | ❌ Nein | Zu groß, Dependencies |
| Animations-Framework? | QPropertyAnimation + QTimer | Native Qt, keine Extra-Deps |
| Persistenz von Layout? | JSON in `data_dir/analytics_layout.json` | Konsistent mit Config-Pattern |
| Saved-Views? | SQLite-Tabelle `analytics_saved_views` | Native zur DB |
| PDF-Export? | ReportLab wie bisher | Stabil |
| HTML-Export? | Jinja2 + eingebettete Daten | Optional, Phase 3 |

---

## 8. Aufwandsschätzung

| Phase | Dauer | Senior-Risiko |
|---|---:|---|
| Phase 1: Foundation | 2-3 Tage | Mittel — Architektur-Refactor |
| Phase 2: Interaktivität | 2-3 Tage | Mittel — Matplotlib-Events |
| Phase 3: Wow-Features | 2-3 Tage | Hoch — Auto-Insights ist Forschung |
| Phase 4: Power-User | 1-2 Tage | Niedrig |
| **Gesamt** | **8-11 Tage** | |

Plus **DB-Query-Methoden**: 5-8 neue in `db_manager.py`, +1 Tag.

**Realistisch:** 10-12 Tage Vollgas, oder 4-5 Sessions mit Issue-by-Issue-Sprints.

---

## 9. Erste Schritte (wenn freigegeben)

1. **Issue #42 erstellen**: "Analytics Control Center Phase 1: Foundation + Architektur"
2. **Branch `feat/analytics-control-center`**
3. **DB-Methoden zuerst** (testbar, schnell, schafft Grundlage)
4. **Modul-Struktur** in `ui/pages/analytics/` anlegen
5. **Insight-Banner + 4 Tabs** (das größte Wow-Element zuerst)
6. **Bestehende 5 Auswertungen in die Tabs migrieren**
7. **Alte `page_auswertungen.py` als Shim behalten** bis Phase 1 grün ist

---

## 10. Was ich VOR dem Code-Start brauche

Bitte um Entscheidung zu folgenden Punkten:

1. **Tab-Cluster-Naming**: "Bestand / Bewegungen / Verfall / Compliance" — passt das? Alternative: "Lager / Aktivität / Risiko / Audit"?
2. **Insight-Banner ja oder nein?** (oben 4 Smart-Cards)
3. **Saved Views gewünscht?** (Phase 2 vs. Phase 4)
4. **Auto-Insights NL-generiert** oder Template-basiert?
5. **Reihenfolge**: Phase 1+2+3 zusammen oder iterativ freigeben?
6. **Side-Constraint**: Eigene Sub-Route im Menü? ("Analytics" als eigene Page statt in Sidebar-Tab)?
