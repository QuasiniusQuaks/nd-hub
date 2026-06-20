"""Analytics Control Center — Modul-Package.

Issue #42: Komplettumbau des Analyse-Bereichs von klassischer Sidebar-Filter-
Ansicht auf ein State-of-the-Art Kontrollzentrum mit Insight-Banner,
4-Tab-Cluster und interaktiven Charts.

Struktur:
    analytics_page.py       — Container mit Tabs + globaler Filter-Leiste
    _widgets/               — Wiederverwendbare Custom-Widgets
    _charts/                — Chart-Wrapper
    _filters/               — Filter-Komponenten + Cross-Filter-State
    tabs/                   — 4 Analyse-Tabs (Bestand, Bewegungen, Verfall, Compliance)
    _insights/              — Auto-Insights-Generator
    _db/                    — Zentralisierte Analytics-Queries (Delegation an Database)
"""
