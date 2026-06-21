"""PDF-Report — Apple-Health-Style Annual-Report via ReportLab.

Generiert einen strukturierten PDF-Report mit KPIs, Tabellen und
Zusammenfassung. Apple-Health-inspiriertes Design (große Zahlen,
klare Typo,pastellige Akzente).

Issue #42 Phase 3 — Wow-Features.
"""

from __future__ import annotations

import logging
from datetime import datetime

from db_manager import Database

logger = logging.getLogger(__name__)


class PDFReporter:
    """Generiert Apple-Health-Style PDF-Reports via ReportLab."""

    def __init__(self, db: Database) -> None:
        self.db = db

    def export(
        self,
        output_path: str,
        title: str = "ND-Hub Analytics Report",
        days: int = 30,
    ) -> bool:
        """Generiert eine PDF-Datei mit Analytics-Zusammenfassung.

        Args:
            output_path: Pfad für die PDF-Datei.
            title: Report-Titel.
            days: Zeitraum in Tagen.

        Returns:
            True bei Erfolg, False bei Fehler.
        """
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
            from reportlab.lib.units import mm
            from reportlab.platypus import (
                Paragraph,
                SimpleDocTemplate,
                Spacer,
                Table,
                TableStyle,
            )

            doc = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                leftMargin=20 * mm,
                rightMargin=20 * mm,
                topMargin=20 * mm,
                bottomMargin=20 * mm,
            )

            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                "CustomTitle",
                parent=styles["Title"],
                fontSize=28,
                spaceAfter=6,
                textColor=colors.HexColor("#1d1d1f"),
            )
            subtitle_style = ParagraphStyle(
                "Subtitle",
                parent=styles["Normal"],
                fontSize=12,
                textColor=colors.HexColor("#86868b"),
                spaceAfter=20,
            )
            section_style = ParagraphStyle(
                "Section",
                parent=styles["Heading2"],
                fontSize=16,
                spaceBefore=20,
                spaceAfter=10,
                textColor=colors.HexColor("#1d1d1f"),
            )
            body_style = ParagraphStyle(
                "Body",
                parent=styles["Normal"],
                fontSize=11,
                spaceAfter=6,
                textColor=colors.HexColor("#1d1d1f"),
            )

            story: list = []

            # Header
            story.append(Paragraph(title, title_style))
            story.append(Paragraph(
                f"Generiert am {datetime.now().strftime('%d.%m.%Y um %H:%M')} · Zeitraum: {days} Tage",
                subtitle_style,
            ))

            # KPI-Sektion
            story.append(Paragraph("📊 Kennzahlen", section_style))
            kpi_data = self._collect_kpis(days)
            if kpi_data:
                kpi_table = Table(kpi_data, colWidths=[80 * mm, 90 * mm])
                kpi_table.setStyle(TableStyle([
                    ("FONTSIZE", (0, 0), (-1, -1), 11),
                    ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#86868b")),
                    ("TEXTCOLOR", (1, 0), (1, -1), colors.HexColor("#1d1d1f")),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("LINEBELOW", (0, 0), (-1, -2), 0.5, colors.HexColor("#e0e0e0")),
                ]))
                story.append(kpi_table)
            else:
                story.append(Paragraph("Keine Daten verfügbar.", body_style))

            # Verfall-Sektion
            story.append(Paragraph("🚨 Verfälle in den nächsten 30 Tagen", section_style))
            verfall_data = self._collect_verfall_table()
            if verfall_data and len(verfall_data) > 1:
                v_table = Table(verfall_data, colWidths=[45 * mm, 35 * mm, 30 * mm, 30 * mm, 30 * mm])
                v_table.setStyle(TableStyle([
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f5f5f7")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#86868b")),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e0e0e0")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fafafa")]),
                ]))
                story.append(v_table)
            else:
                story.append(Paragraph("Keine Verfälle in den nächsten 30 Tagen ✅", body_style))

            # Depot-Abweichung
            story.append(Paragraph("📊 Depot Soll/Ist-Abweichung", section_style))
            deviation_data = self._collect_deviation_table()
            if deviation_data and len(deviation_data) > 1:
                d_table = Table(deviation_data, colWidths=[50 * mm, 35 * mm, 35 * mm, 35 * mm, 25 * mm])
                d_table.setStyle(TableStyle([
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f5f5f7")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#86868b")),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e0e0e0")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fafafa")]),
                ]))
                story.append(d_table)
            else:
                story.append(Paragraph("Keine Abweichungsdaten verfügbar.", body_style))

            # Anomalien
            story.append(Paragraph("🔮 Statistische Anomalien", section_style))
            anomaly_data = self._collect_anomaly_table()
            if anomaly_data and len(anomaly_data) > 1:
                a_table = Table(anomaly_data, colWidths=[40 * mm, 25 * mm, 30 * mm, 25 * mm, 25 * mm, 25 * mm])
                a_table.setStyle(TableStyle([
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f5f5f7")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#86868b")),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e0e0e0")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fafafa")]),
                ]))
                story.append(a_table)
            else:
                story.append(Paragraph("Keine statistischen Anomalien erkannt ✅", body_style))

            # Footer
            story.append(Spacer(1, 30 * mm))
            story.append(Paragraph(
                f"<para alignment='center'><font color='#86868b' size='9'>"
                f"ND-Hub Analytics · Self-generated · {datetime.now().year}</font></para>",
                body_style,
            ))

            doc.build(story)
            logger.info("PDF-Export: %s", output_path)
            return True

        except Exception:
            logger.exception("PDF-Export fehlgeschlagen")
            return False

    def _collect_kpis(self, days: int) -> list[list[str]]:
        """Sammelt KPI-Werte für die PDF-Tabelle."""
        kpis: list[list[str]] = []

        try:
            trend = self.db.get_period_trend(days=days)
            kpis.append(["Zugänge (aktuelle Periode)", f"{trend['zugang_aktuell']} EH"])
            kpis.append(["Zugänge (Vorperiode)", f"{trend['zugang_vorperiode']} EH"])
            kpis.append(["Veränderung", f"{trend['veraenderung_pct']:+.1f}%"])
        except Exception:
            pass

        try:
            verfall = self.db.get_verfall_warnings(days=30)
            kpis.append(["Verfälle <30 Tage", f"{len(verfall)} Präparate"])
        except Exception:
            pass

        try:
            inactive = self.db.get_inactive_depots(days=180)
            kpis.append(["Inaktive Depots (>180T)", f"{len(inactive)}"])
        except Exception:
            pass

        try:
            dead = self.db.get_dead_stock(days=180)
            total_dead = sum(r["ist_bestand"] for r in dead) if dead else 0
            kpis.append(["Toter Bestand", f"{len(dead)} Präparate ({total_dead} EH)"])
        except Exception:
            pass

        try:
            anomalies = self.db.get_anomalies(threshold_std=2.0)
            kpis.append(["Anomalien (Z≥2.0)", f"{len(anomalies)}"])
        except Exception:
            pass

        return kpis

    def _collect_verfall_table(self) -> list[list[str]]:
        """Sammelt Verfall-Daten für die PDF-Tabelle."""
        try:
            rows = self.db.get_verfall_warnings(days=30)
            data = [["Präparat", "Depot", "Charge", "Verfall", "Menge"]]
            for r in rows[:20]:  # Max 20 Zeilen
                data.append([
                    str(r["praeparat_name"]),
                    str(r["depot_name"]),
                    str(r["charge"] or "—"),
                    str(r["verfall"] or "—"),
                    f"{r['anzahl']} EH",
                ])
            return data
        except Exception:
            return []

    def _collect_deviation_table(self) -> list[list[str]]:
        """Sammelt Abweichungs-Daten für die PDF-Tabelle."""
        try:
            rows = self.db.get_depot_deviation()
            data = [["Depot", "Soll", "Ist", "Differenz", "Status"]]
            for r in rows:
                diff = r["differenz"] or 0
                status = "🟢 OK" if abs(diff) <= 5 else ("🟡 Leicht" if abs(diff) <= 20 else "🔴 Kritisch")
                data.append([
                    str(r["depot_name"]),
                    str(r["soll_gesamt"]),
                    str(r["ist_gesamt"]),
                    f"{diff:+d}",
                    status,
                ])
            return data
        except Exception:
            return []

    def _collect_anomaly_table(self) -> list[list[str]]:
        """Sammelt Anomalie-Daten für die PDF-Tabelle."""
        try:
            rows = self.db.get_anomalies(threshold_std=2.0)
            data = [["Präparat", "Typ", "Datum", "Menge", "Ø Normal", "Z-Score"]]
            for r in rows[:15]:
                data.append([
                    str(r["praeparat_name"]),
                    str(r["typ"]),
                    str(r["tag"]),
                    str(r["total"]),
                    f"{r['mean']:.1f}",
                    f"{r['z_score']:.2f}",
                ])
            return data
        except Exception:
            return []
