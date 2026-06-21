"""Auto-Insights Generator — "Was ist passiert?" Bullet-Points.

Analysiert DB-Daten und generiert 3 natürlichsprachige Bullet-Points,
die die wichtigsten Events der letzten Periode zusammenfassen.

Template-basiert (nicht LLM-generiert), wie im Konzept empfohlen.

Issue #42 Phase 3 — Wow-Features.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from db_manager import Database

logger = logging.getLogger(__name__)


@dataclass
class Insight:
    """Ein generierter Insight-Bullet-Point."""

    icon: str        # Emoji
    text: str        # NL-Text
    severity: str    # "info" | "warning" | "danger" | "success"
    category: str    # "verfall" | "bestand" | "bewegung" | "compliance"


class AutoInsightsGenerator:
    """Generiert 3 Insight-Bullet-Points aus DB-Daten.

    Priorität:
      1. Danger (Verfälle, kritische Abweichungen)
      2. Warning (Inaktive Depots, Anomalien)
      3. Info/Success (Trends, Umschlag)
    """

    def __init__(self, db: Database) -> None:
        self.db = db

    def generate(self, days: int = 7) -> list[Insight]:
        """Generiert bis zu 3 Insights für die letzten `days` Tage.

        Returns:
            Liste von Insight-Objekten (max. 3), priorisiert nach Severity.
        """
        insights: list[Insight] = []

        # 1. Verfall-Warnings (Danger)
        insights.extend(self._check_verfall())

        # 2. Depot-Abweichungen (Danger/Warning)
        insights.extend(self._check_depot_deviation())

        # 3. Inaktive Depots (Warning)
        insights.extend(self._check_inactive_depots())

        # 4. Trend (Info/Success)
        insights.extend(self._check_trend(days))

        # 5. Anomalien (Warning)
        insights.extend(self._check_anomalies())

        # 6. Dead Stock (Warning)
        insights.extend(self._check_dead_stock())

        # Priorisieren: danger > warning > success > info
        severity_order = {"danger": 0, "warning": 1, "success": 2, "info": 3}
        insights.sort(key=lambda i: severity_order.get(i.severity, 99))

        return insights[:3]

    def _check_verfall(self) -> list[Insight]:
        """Prüft auf bevorstehende Verfälle."""
        try:
            rows = self.db.get_verfall_warnings(days=30)
            if not rows:
                return []

            count = len(rows)
            total_einheiten = sum(r["anzahl"] for r in rows)
            naechster = rows[0]
            return [Insight(
                icon="🚨",
                text=(f"{count} Präparate ({total_einheiten} EH) verfallen "
                      f"in den nächsten 30 Tagen — nächster: "
                      f"{naechster['praeparat_name']} am {naechster['verfall']}"),
                severity="danger",
                category="verfall",
            )]
        except Exception:
            logger.debug("Verfall-Insight fehlgeschlagen")
            return []

    def _check_depot_deviation(self) -> list[Insight]:
        """Prüft auf kritische Soll/Ist-Abweichungen."""
        try:
            rows = self.db.get_depot_deviation()
            kritisch = [r for r in rows if abs(r["differenz"] or 0) > 20]
            if not kritisch:
                return []

            if len(kritisch) == 1:
                r = kritisch[0]
                diff = r["differenz"]
                richtung = "über" if diff > 0 else "unter"
                return [Insight(
                    icon="⚠️",
                    text=f"Depot {r['depot_name']} weicht {abs(diff)} EH {richtung} dem Soll ab",
                    severity="danger" if abs(diff) > 50 else "warning",
                    category="bestand",
                )]
            return [Insight(
                icon="⚠️",
                text=f"{len(kritisch)} Depots mit kritischer Soll/Ist-Abweichung (>20 EH)",
                severity="warning",
                category="bestand",
            )]
        except Exception:
            logger.debug("Deviation-Insight fehlgeschlagen")
            return []

    def _check_inactive_depots(self) -> list[Insight]:
        """Prüft auf inaktive Depots."""
        try:
            rows = self.db.get_inactive_depots(days=180)
            if not rows:
                return []
            return [Insight(
                icon="💤",
                text=f"{len(rows)} Depot(s) ohne Bewegung in den letzten 180 Tagen",
                severity="warning",
                category="bestand",
            )]
        except Exception:
            logger.debug("Inactive-Depot-Insight fehlgeschlagen")
            return []

    def _check_trend(self, days: int) -> list[Insight]:
        """Prüft den Zugang-Trend vs. Vorperiode."""
        try:
            trend = self.db.get_period_trend(days=days)
            pct = trend["veraenderung_pct"]
            aktuell = trend["zugang_aktuell"]

            if aktuell == 0:
                return [Insight(
                    icon="📊",
                    text=f"Keine Zugänge in den letzten {days} Tagen",
                    severity="info",
                    category="bewegung",
                )]

            if pct > 0:
                return [Insight(
                    icon="📈",
                    text=f"Zugänge +{pct}% vs. Vorperiode ({aktuell} EH in {days} Tagen)",
                    severity="success",
                    category="bewegung",
                )]
            elif pct < 0:
                return [Insight(
                    icon="📉",
                    text=f"Zugänge {pct}% vs. Vorperiode ({aktuell} EH in {days} Tagen)",
                    severity="info",
                    category="bewegung",
                )]
            return []
        except Exception:
            logger.debug("Trend-Insight fehlgeschlagen")
            return []

    def _check_anomalies(self) -> list[Insight]:
        """Prüft auf statistische Anomalien."""
        try:
            rows = self.db.get_anomalies(threshold_std=2.5)
            if not rows:
                return []
            top = rows[0]
            return [Insight(
                icon="🔮",
                text=(f"Anomalie erkannt: {top['praeparat_name']} — "
                      f"{top['total']} EH am {top['tag']} "
                      f"(Z-Score: {top['z_score']}, Normal: {top['mean']})"),
                severity="warning",
                category="bewegung",
            )]
        except Exception:
            logger.debug("Anomalie-Insight fehlgeschlagen")
            return []

    def _check_dead_stock(self) -> list[Insight]:
        """Prüft auf toten Bestand."""
        try:
            rows = self.db.get_dead_stock(days=180)
            if not rows:
                return []
            total = sum(r["ist_bestand"] for r in rows)
            return [Insight(
                icon="📦",
                text=f"{len(rows)} Präparate mit totem Bestand ({total} EH ohne Bewegung >180 Tage)",
                severity="warning",
                category="bestand",
            )]
        except Exception:
            logger.debug("Dead-Stock-Insight fehlgeschlagen")
            return []
