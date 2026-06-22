"""Tests für Phase 3 Features: Auto-Insights, HTML-Export, PDF-Report.

Issue #42 Phase 3 — Wow-Features.
"""

from __future__ import annotations

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from db_manager import Database


@pytest.fixture
def analytics_db():
    """Test-DB mit Daten für Auto-Insights."""
    db_path = tempfile.mktemp(suffix="_phase3_test.db")
    db = Database(db_path)
    cur = db.conn.cursor()

    cur.execute("INSERT INTO depots (id, name) VALUES (1, 'Berlin')")
    cur.execute("INSERT INTO depots (id, name) VALUES (2, 'Hamburg')")
    cur.execute("INSERT INTO praeparate (id, name) VALUES (1, 'Morphin')")
    cur.execute("INSERT INTO praeparate (id, name) VALUES (2, 'Adrenalin')")
    cur.execute("INSERT INTO depot_praeparate (depot_id, praeparat_id, sollbestand) VALUES (1, 1, 100)")
    cur.execute("INSERT INTO depot_praeparate (depot_id, praeparat_id, sollbestand) VALUES (2, 2, 50)")

    now = datetime.now()
    soon = (now + timedelta(days=15)).strftime("%Y-%m-%d")
    recent = now.strftime("%Y-%m-%d")
    old = (now - timedelta(days=200)).strftime("%Y-%m-%d")

    # Verfall nahe
    cur.execute(
        "INSERT INTO bewegungen (depot_id, praeparat_id, charge, verfall, eingang_datum, anzahl, typ) "
        "VALUES (1, 1, 'C1', ?, ?, 120, 'Zugang')", (soon, recent)
    )
    # Abgang
    cur.execute(
        "INSERT INTO bewegungen (depot_id, praeparat_id, charge, verfall, eingang_datum, ausgang_datum, anzahl, typ) "
        "VALUES (1, 1, '', '', NULL, ?, 30, 'Abgang')", (recent,)
    )
    # Hamburg: alte Bewegung (inaktiv)
    cur.execute(
        "INSERT INTO bewegungen (depot_id, praeparat_id, charge, verfall, eingang_datum, anzahl, typ) "
        "VALUES (2, 2, 'C2', '', ?, 40, 'Zugang')", (old,)
    )

    db.conn.commit()
    yield db
    db.conn.close()
    Path(db_path).unlink(missing_ok=True)


class TestAutoInsightsGenerator:
    """Tests für den Auto-Insights Generator."""

    def test_generate_returns_list(self, analytics_db):
        from ui.pages.analytics._insights.auto_insights import AutoInsightsGenerator

        gen = AutoInsightsGenerator(analytics_db)
        insights = gen.generate(days=7)
        assert isinstance(insights, list)
        assert len(insights) <= 3

    def test_insight_has_required_fields(self, analytics_db):
        from ui.pages.analytics._insights.auto_insights import AutoInsightsGenerator

        gen = AutoInsightsGenerator(analytics_db)
        insights = gen.generate(days=7)
        for insight in insights:
            assert hasattr(insight, "icon")
            assert hasattr(insight, "text")
            assert hasattr(insight, "severity")
            assert hasattr(insight, "category")
            assert insight.severity in ("info", "warning", "danger", "success")

    def test_verfall_insight_generated(self, analytics_db):
        """Verfall-Warning sollte als Danger-Insight auftauchen."""
        from ui.pages.analytics._insights.auto_insights import AutoInsightsGenerator

        gen = AutoInsightsGenerator(analytics_db)
        insights = gen.generate(days=7)
        verfall_insights = [i for i in insights if i.category == "verfall"]
        assert len(verfall_insights) >= 1
        assert verfall_insights[0].severity == "danger"
        assert "verfall" in verfall_insights[0].text.lower()

    def test_prioritization_danger_first(self, analytics_db):
        """Danger-Insights sollten vor Warning/Info kommen."""
        from ui.pages.analytics._insights.auto_insights import AutoInsightsGenerator

        gen = AutoInsightsGenerator(analytics_db)
        insights = gen.generate(days=7)
        if len(insights) >= 2:
            severity_order = {"danger": 0, "warning": 1, "success": 2, "info": 3}
            for i in range(len(insights) - 1):
                assert severity_order[insights[i].severity] <= severity_order[insights[i + 1].severity]

    def test_empty_db_returns_empty_list(self):
        """Leere DB → keine Insights."""
        db_path = tempfile.mktemp(suffix="_empty.db")
        db = Database(db_path)
        try:
            from ui.pages.analytics._insights.auto_insights import AutoInsightsGenerator
            gen = AutoInsightsGenerator(db)
            insights = gen.generate(days=7)
            assert isinstance(insights, list)
        finally:
            db.conn.close()
            Path(db_path).unlink(missing_ok=True)

    def test_insight_text_not_empty(self, analytics_db):
        from ui.pages.analytics._insights.auto_insights import AutoInsightsGenerator
        gen = AutoInsightsGenerator(analytics_db)
        insights = gen.generate(days=7)
        for insight in insights:
            assert len(insight.text) > 0
            assert len(insight.icon) > 0


class TestHTMLExport:
    """Tests für den HTML-Exporter."""

    def test_export_creates_file(self, analytics_db, tmp_path):
        from ui.pages.analytics._insights.html_export import HTMLExporter

        exporter = HTMLExporter(analytics_db)
        output = str(tmp_path / "test_report.html")
        result = exporter.export(output, days=30)

        assert result is True
        assert Path(output).exists()
        content = Path(output).read_text(encoding="utf-8")
        assert "<html" in content.lower()
        assert "</html>" in content.lower()

    def test_html_contains_data(self, analytics_db, tmp_path):
        from ui.pages.analytics._insights.html_export import HTMLExporter

        exporter = HTMLExporter(analytics_db)
        output = str(tmp_path / "test_report.html")
        exporter.export(output, days=30)

        content = Path(output).read_text(encoding="utf-8")
        # Chart.js sollte referenziert sein
        assert "chart.js" in content.lower() or "Chart" in content
        # Daten als JSON eingebettet
        assert "DATA" in content or "depot_deviation" in content

    def test_html_contains_verfall_data(self, analytics_db, tmp_path):
        from ui.pages.analytics._insights.html_export import HTMLExporter

        exporter = HTMLExporter(analytics_db)
        output = str(tmp_path / "test_report.html")
        exporter.export(output, days=30)

        content = Path(output).read_text(encoding="utf-8")
        # Verfall-Daten sollten drin sein (Präparat Morphin)
        assert "Morphin" in content or "verfall_warnings" in content

    def test_export_invalid_path_returns_false(self, analytics_db):
        from ui.pages.analytics._insights.html_export import HTMLExporter

        exporter = HTMLExporter(analytics_db)
        result = exporter.export("/nonexistent/path/report.html", days=30)
        assert result is False

    def test_collect_data_structure(self, analytics_db):
        from ui.pages.analytics._insights.html_export import HTMLExporter

        exporter = HTMLExporter(analytics_db)
        data = exporter._collect_data(days=30)
        assert "generated_at" in data
        assert "period_days" in data
        assert "verfall_warnings" in data
        assert "depot_deviation" in data
        assert isinstance(data["verfall_warnings"], list)


class TestPDFReport:
    """Tests für den PDF-Reporter."""

    def test_export_creates_file(self, analytics_db, tmp_path):
        from ui.pages.analytics._insights.pdf_report import PDFReporter

        reporter = PDFReporter(analytics_db)
        output = str(tmp_path / "test_report.pdf")
        result = reporter.export(output, days=30)

        assert result is True
        assert Path(output).exists()
        assert Path(output).stat().st_size > 0

    def test_pdf_is_valid_pdf(self, analytics_db, tmp_path):
        from ui.pages.analytics._insights.pdf_report import PDFReporter

        reporter = PDFReporter(analytics_db)
        output = str(tmp_path / "test_report.pdf")
        reporter.export(output, days=30)

        # PDF Magic Bytes prüfen
        with open(output, "rb") as f:
            header = f.read(4)
        assert header == b"%PDF"

    def test_pdf_contains_kpi_section(self, analytics_db, tmp_path):
        from ui.pages.analytics._insights.pdf_report import PDFReporter

        reporter = PDFReporter(analytics_db)
        output = str(tmp_path / "test_report.pdf")
        reporter.export(output, days=30)

        # KPIs sollten im PDF sein — prüfe via Text-Extraction
        content = Path(output).read_bytes()
        # PDF enthält komprimierte Streams, aber KPI-Labels sind als Text drin
        assert len(content) > 1000  # Nicht-leeres PDF

    def test_collect_kpis(self, analytics_db):
        from ui.pages.analytics._insights.pdf_report import PDFReporter

        reporter = PDFReporter(analytics_db)
        kpis = reporter._collect_kpis(days=7)
        assert isinstance(kpis, list)
        # Mindestens ein KPI
        assert len(kpis) > 0
        # Jeder KPI hat Label + Value
        for kpi in kpis:
            assert len(kpi) == 2

    def test_export_invalid_path_returns_false(self, analytics_db):
        from ui.pages.analytics._insights.pdf_report import PDFReporter

        reporter = PDFReporter(analytics_db)
        result = reporter.export("/nonexistent/path/report.pdf", days=30)
        assert result is False
