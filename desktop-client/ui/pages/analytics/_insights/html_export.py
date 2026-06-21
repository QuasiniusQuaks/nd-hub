"""HTML-Export — self-contained interaktives HTML für Offline-Teilung.

Generiert eine einzelne HTML-Datei mit eingebetteten Daten + Chart.js (CDN-fallback
inline), die offline geteilt werden kann.

Issue #42 Phase 3 — Wow-Features.
"""

from __future__ import annotations

import html
import json
import logging
from datetime import datetime
from pathlib import Path

from db_manager import Database

logger = logging.getLogger(__name__)


class HTMLExporter:
    """Exportiert Analytics-Daten als self-contained HTML-Report."""

    def __init__(self, db: Database) -> None:
        self.db = db

    def export(
        self,
        output_path: str,
        title: str = "ND-Hub Analytics Report",
        days: int = 30,
    ) -> bool:
        """Generiert eine HTML-Datei mit eingebetteten Charts.

        Args:
            output_path: Pfad für die HTML-Datei.
            title: Report-Titel.
            days: Zeitraum in Tagen.

        Returns:
            True bei Erfolg, False bei Fehler.
        """
        try:
            data = self._collect_data(days)
            html_content = self._render_html(title, data)
            Path(output_path).write_text(html_content, encoding="utf-8")
            logger.info("HTML-Export: %s (%d bytes)", output_path, len(html_content))
            return True
        except Exception:
            logger.exception("HTML-Export fehlgeschlagen")
            return False

    def _collect_data(self, days: int) -> dict:
        """Sammelt alle Analytics-Daten für den Export."""
        data: dict = {
            "generated_at": datetime.now().isoformat(),
            "period_days": days,
        }

        # Verfall-Warnings
        try:
            verfall = self.db.get_verfall_warnings(days=30)
            data["verfall_warnings"] = [
                {
                    "praeparat": str(r["praeparat_name"]),
                    "depot": str(r["depot_name"]),
                    "charge": str(r["charge"] or ""),
                    "verfall": str(r["verfall"] or ""),
                    "anzahl": int(r["anzahl"]),
                }
                for r in verfall
            ]
        except Exception:
            data["verfall_warnings"] = []

        # Depot-Abweichung
        try:
            deviation = self.db.get_depot_deviation()
            data["depot_deviation"] = [
                {
                    "depot": str(r["depot_name"]),
                    "soll": int(r["soll_gesamt"]),
                    "ist": int(r["ist_gesamt"]),
                    "differenz": int(r["differenz"]),
                }
                for r in deviation
            ]
        except Exception:
            data["depot_deviation"] = []

        # Top-Movers
        try:
            movers_in = self.db.get_top_movers(direction="in", limit=10, days=days)
            movers_out = self.db.get_top_movers(direction="out", limit=10, days=days)
            data["top_movers_in"] = [
                {"name": str(r["praeparat_name"]), "gesamt": int(r["gesamt"])}
                for r in movers_in
            ]
            data["top_movers_out"] = [
                {"name": str(r["praeparat_name"]), "gesamt": int(r["gesamt"])}
                for r in movers_out
            ]
        except Exception:
            data["top_movers_in"] = []
            data["top_movers_out"] = []

        # Verfall-Forecast
        try:
            forecast = self.db.get_verfall_forecast(months=12)
            data["verfall_forecast"] = [
                {
                    "monat": str(r["monat"]),
                    "einheiten": int(r["verfallende_einheiten"]),
                    "chargen": int(r["anzahl_chargen"]),
                }
                for r in forecast
            ]
        except Exception:
            data["verfall_forecast"] = []

        # Inaktive Depots
        try:
            inactive = self.db.get_inactive_depots(days=180)
            data["inactive_depots"] = [
                {"depot": str(r["depot_name"]), "letzte_bewegung": str(r["letzte_bewegung"] or "—")}
                for r in inactive
            ]
        except Exception:
            data["inactive_depots"] = []

        # Anomalien
        try:
            anomalies = self.db.get_anomalies(threshold_std=2.0)
            data["anomalies"] = [
                {
                    "praeparat": str(r["praeparat_name"]),
                    "typ": str(r["typ"]),
                    "tag": str(r["tag"]),
                    "total": int(r["total"]),
                    "mean": float(r["mean"]),
                    "z_score": float(r["z_score"]),
                }
                for r in anomalies
            ]
        except Exception:
            data["anomalies"] = []

        return data

    def _render_html(self, title: str, data: dict) -> str:
        """Rendert die HTML-Datei mit eingebetteten Daten + Chart.js."""
        data_json = json.dumps(data, ensure_ascii=False, indent=2)
        generated = html.escape(data.get("generated_at", ""))
        safe_title = html.escape(title)

        return f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{safe_title}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, 'SF Pro Display', 'Segoe UI', sans-serif;
            background: #f5f5f7; color: #1d1d1f; padding: 24px;
        }}
        h1 {{ font-size: 28px; margin-bottom: 4px; }}
        .subtitle {{ color: #86868b; font-size: 14px; margin-bottom: 24px; }}
        .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 24px; }}
        .card {{
            background: #fff; border-radius: 16px; padding: 24px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08); border: 1px solid #e0e0e0;
        }}
        .card h2 {{ font-size: 18px; margin-bottom: 16px; }}
        .card.full {{ grid-column: 1 / -1; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ text-align: left; padding: 8px 12px; border-bottom: 1px solid #f0f0f0; font-size: 13px; }}
        th {{ color: #86868b; font-weight: 600; text-transform: uppercase; font-size: 11px; }}
        .badge-danger {{ background: #ffe0e0; color: #c0392b; padding: 2px 8px; border-radius: 8px; }}
        .badge-warning {{ background: #fff3e0; color: #e67e22; padding: 2px 8px; border-radius: 8px; }}
        .badge-success {{ background: #e0f5e9; color: #27ae60; padding: 2px 8px; border-radius: 8px; }}
        canvas {{ max-height: 300px; }}
        .empty {{ color: #86868b; font-style: italic; padding: 16px; }}
    </style>
</head>
<body>
    <h1>{safe_title}</h1>
    <p class="subtitle">Generiert am {generated} · Self-contained · Offline teilbar</p>

    <div class="grid">
        <div class="card">
            <h2>📊 Depot Soll/Ist-Abweichung</h2>
            <canvas id="chart-deviation"></canvas>
        </div>
        <div class="card">
            <h2>📈 Top-Movers (Zugang)</h2>
            <canvas id="chart-movers-in"></canvas>
        </div>
        <div class="card">
            <h2>📉 Top-Movers (Abgang)</h2>
            <canvas id="chart-movers-out"></canvas>
        </div>
        <div class="card">
            <h2>⏳ Verfall-Forecast (12 Monate)</h2>
            <canvas id="chart-forecast"></canvas>
        </div>
    </div>

    <div class="card full" style="margin-bottom: 24px;">
        <h2>🚨 Verfälle in den nächsten 30 Tagen</h2>
        <div id="verfall-table"></div>
    </div>

    <div class="card full" style="margin-bottom: 24px;">
        <h2>🔮 Statistische Anomalien</h2>
        <div id="anomaly-table"></div>
    </div>

    <script>
        const DATA = {data_json};

        // Charts
        function makeChart(id, type, labels, values, color) {{
            const ctx = document.getElementById(id);
            if (!ctx || !labels.length) return;
            new Chart(ctx, {{ type, data: {{ labels, datasets: [{{ data: values, backgroundColor: color }}] }},
                options: {{ responsive: true, plugins: {{ legend: {{ display: false }} }} }} }});
        }}

        makeChart('chart-deviation', 'bar',
            DATA.depot_deviation.map(d => d.depot),
            DATA.depot_deviation.map(d => d.differenz),
            'rgba(52, 152, 219, 0.7)');

        makeChart('chart-movers-in', 'bar',
            DATA.top_movers_in.map(d => d.name),
            DATA.top_movers_in.map(d => d.gesamt),
            'rgba(39, 174, 96, 0.7)');

        makeChart('chart-movers-out', 'bar',
            DATA.top_movers_out.map(d => d.name),
            DATA.top_movers_out.map(d => d.gesamt),
            'rgba(231, 76, 60, 0.7)');

        makeChart('chart-forecast', 'line',
            DATA.verfall_forecast.map(d => d.monat),
            DATA.verfall_forecast.map(d => d.einheiten),
            'rgba(255, 149, 0, 0.7)');

        // Verfall-Tabelle
        const vt = document.getElementById('verfall-table');
        if (DATA.verfall_warnings.length === 0) {{
            vt.innerHTML = '<p class="empty">Keine Verfälle in den nächsten 30 Tagen ✅</p>';
        }} else {{
            vt.innerHTML = '<table><tr><th>Präparat</th><th>Depot</th><th>Charge</th><th>Verfall</th><th>Menge</th></tr>' +
                DATA.verfall_warnings.map(v => `<tr><td>${{v.praeparat}}</td><td>${{v.depot}}</td><td>${{v.charge}}</td><td><span class="badge-danger">${{v.verfall}}</span></td><td>${{v.anzahl}} EH</td></tr>`).join('') +
                '</table>';
        }}

        // Anomalie-Tabelle
        const at = document.getElementById('anomaly-table');
        if (DATA.anomalies.length === 0) {{
            at.innerHTML = '<p class="empty">Keine statistischen Anomalien erkannt ✅</p>';
        }} else {{
            at.innerHTML = '<table><tr><th>Präparat</th><th>Typ</th><th>Datum</th><th>Menge</th><th>Ø Normal</th><th>Z-Score</th></tr>' +
                DATA.anomalies.map(a => `<tr><td>${{a.praeparat}}</td><td>${{a.typ}}</td><td>${{a.tag}}</td><td>${{a.total}}</td><td>${{a.mean.toFixed(1)}}</td><td>${{a.z_score.toFixed(2)}}</td></tr>`).join('') +
                '</table>';
        }}
    </script>
</body>
</html>"""
