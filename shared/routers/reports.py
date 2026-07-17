"""Shared Reports router (Issues #60/#61).

enable_depot_scope: web multi-institution depot filtering + validated date ranges.
enable_rich_filenames: web export filenames with perspective/date metadata.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status


def create_reports_router(
    repository,
    require_permission,
    *,
    parse_id_list_csv,
    csv_response,
    pdf_response,
    pptx_response,
    enable_depot_scope: bool = False,
    enable_rich_filenames: bool = False,
    scoped_requested_ids=None,
    allowed_depot_ids=None,
    validated_report_date_range=None,
    build_report_export_filename=None,
    add_months=None,
) -> APIRouter:
    router = APIRouter(prefix="/reports", tags=["reports"])

    def _filename(base: str, ext: str, **meta):
        if enable_rich_filenames and build_report_export_filename is not None:
            return build_report_export_filename(base, ext, **meta)
        return f"{base}.{ext}"

    def _parse_perspective(perspective: str) -> str:
        safe = (perspective or "").strip().lower()
        if safe not in {"depot", "praeparat"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ungueltige Perspektive.")
        return safe

    def _selected_ids(ids: str) -> list[int]:
        try:
            selected = parse_id_list_csv(ids)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Ungueltige IDs: {exc}") from exc
        if not selected:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mindestens eine ID ist erforderlich.")
        return selected

    def _date_range(start_date: str, end_date: str):
        if enable_depot_scope and validated_report_date_range is not None:
            return validated_report_date_range(start_date, end_date)
        return ((start_date or "").strip() or None, (end_date or "").strip() or None)

    def _depot_scope(session, safe_perspective: str, selected_ids: list[int]):
        if not enable_depot_scope:
            return selected_ids if safe_perspective == "depot" else None
        if safe_perspective == "depot":
            return scoped_requested_ids(session, selected_ids, require_write=False)
        return allowed_depot_ids(session, require_write=False)

    @router.get("/bewegungen")
    def report_bewegungen(
        perspective: str = "depot",
        ids: str = "",
        start_date: str = "",
        end_date: str = "",
        session=Depends(require_permission("reports_view")),
    ) -> dict:
        _ = session
        safe_perspective = _parse_perspective(perspective)
        selected_ids = _selected_ids(ids)
        scoped_depot_ids = _depot_scope(session, safe_perspective, selected_ids)
        if enable_depot_scope and session.role != "Admin" and not scoped_depot_ids:
            return {"rows": [], "kpis": {"gesamt": 0, "zugang": 0, "abgang": 0}}
        safe_start_date, safe_end_date = _date_range(start_date, end_date)
        rows = repository.get_bewegungen_analyse(
            depot_ids=scoped_depot_ids if safe_perspective == "depot" else (scoped_depot_ids if enable_depot_scope else None),
            praeparat_ids=selected_ids if safe_perspective == "praeparat" else None,
            start_date=safe_start_date,
            end_date=safe_end_date,
        )
        total = int(sum(int(row["anzahl"]) for row in rows))
        zugang = int(sum(int(row["anzahl"]) for row in rows if row["typ"] == "Zugang"))
        abgang = int(sum(int(row["anzahl"]) for row in rows if row["typ"] in {"Abgang", "Vernichtung"}))
        return {"rows": rows, "kpis": {"gesamt": total, "zugang": zugang, "abgang": abgang}}

    @router.get("/bewegungen/export.csv")
    def export_report_bewegungen_csv(
        perspective: str = "depot",
        ids: str = "",
        start_date: str = "",
        end_date: str = "",
        session=Depends(require_permission("reports_view")),
    ):
        report = report_bewegungen(perspective, ids, start_date, end_date, session)
        rows = [
            [row["monat"], row["depot"], row["praeparat"], row["typ"], row["anzahl"]]
            for row in report["rows"]
        ]
        return csv_response(
            filename=_filename(
                "bewegungsanalyse",
                "csv",
                perspective=perspective,
                start_date=start_date,
                end_date=end_date,
            ),
            headers=["Monat", "Depot", "Praeparat", "Typ", "Anzahl"],
            rows=rows,
        )

    @router.get("/bestand")
    def report_bestand(
        perspective: str = "depot",
        ids: str = "",
        session=Depends(require_permission("reports_view")),
    ) -> dict:
        _ = session
        safe_perspective = _parse_perspective(perspective)
        selected_ids = _selected_ids(ids)
        scoped_depot_ids = _depot_scope(session, safe_perspective, selected_ids)
        if enable_depot_scope and session.role != "Admin" and not scoped_depot_ids:
            return {"rows": [], "kpis": {"bestandsquote": 0.0, "kritische_luecken": 0, "gesamtbestand": 0}}
        rows = repository.get_bestandsentwicklung(
            depot_ids=scoped_depot_ids if safe_perspective == "depot" else (scoped_depot_ids if enable_depot_scope else None),
            praeparat_ids=selected_ids if safe_perspective == "praeparat" else None,
        )
        sum_soll = int(sum(int(row["sollbestand"]) for row in rows))
        sum_ist = int(sum(int(row["ist_bestand"]) for row in rows))
        luecken = int(sum(1 for row in rows if int(row["differenz"]) < 0))
        quote = (sum_ist / sum_soll * 100) if sum_soll > 0 else 0.0
        return {
            "rows": rows,
            "kpis": {
                "bestandsquote": round(quote, 2),
                "kritische_luecken": luecken,
                "gesamtbestand": sum_ist,
            },
        }

    @router.get("/bestand/export.csv")
    def export_report_bestand_csv(
        perspective: str = "depot",
        ids: str = "",
        session=Depends(require_permission("reports_view")),
    ):
        report = report_bestand(perspective, ids, session)
        rows = [
            [row["depot"], row["praeparat"], row["sollbestand"], row["ist_bestand"], row["differenz"]]
            for row in report["rows"]
        ]
        return csv_response(
            filename=_filename("bestandsentwicklung", "csv", perspective=perspective),
            headers=["Depot", "Praeparat", "Soll", "Ist", "Differenz"],
            rows=rows,
        )

    @router.get("/ranking")
    def report_ranking(
        perspective: str = "depot",
        ids: str = "",
        start_date: str = "",
        end_date: str = "",
        limit: int = 10,
        session=Depends(require_permission("reports_view")),
    ) -> dict:
        _ = session
        safe_perspective = _parse_perspective(perspective)
        selected_ids = _selected_ids(ids)
        scoped_depot_ids = _depot_scope(session, safe_perspective, selected_ids)
        if enable_depot_scope and session.role != "Admin" and not scoped_depot_ids:
            return {
                "rows": [],
                "label": "praeparat" if safe_perspective == "depot" else "depot",
                "kpis": {"gesamtvolumen": 0},
            }
        safe_start_date, safe_end_date = _date_range(start_date, end_date)
        if safe_perspective == "depot":
            raw_rows = repository.get_praeparat_ranking(
                depot_ids=scoped_depot_ids,
                start_date=safe_start_date,
                end_date=safe_end_date,
                limit=limit,
            )
            label = "praeparat"
        else:
            raw_rows = repository.get_depot_ranking(
                praeparat_ids=selected_ids,
                start_date=safe_start_date,
                end_date=safe_end_date,
                limit=limit,
            )
            label = "depot"
        rows: list[dict] = []
        for row in raw_rows:
            item = row if isinstance(row, dict) else {}
            name = str(item.get("name") or item.get("depot") or item.get("praeparat") or "")
            try:
                anzahl = int(item.get("anzahl") or 0)
            except (TypeError, ValueError):
                anzahl = 0
            rows.append({"name": name, "anzahl": anzahl})
        ranking_basis = "abgang_vernichtung"
        if not rows:
            fallback_rows = repository.get_bewegungen_analyse(
                depot_ids=scoped_depot_ids if safe_perspective == "depot" else None,
                praeparat_ids=selected_ids if safe_perspective == "praeparat" else None,
                start_date=safe_start_date,
                end_date=safe_end_date,
            )
            aggregate: dict[str, int] = {}
            for item in fallback_rows:
                key = str(item.get("praeparat") if safe_perspective == "depot" else item.get("depot") or "")
                if not key:
                    continue
                try:
                    amount = int(item.get("anzahl") or 0)
                except (TypeError, ValueError):
                    amount = 0
                aggregate[key] = aggregate.get(key, 0) + amount
            rows = [
                {"name": key, "anzahl": value}
                for key, value in sorted(aggregate.items(), key=lambda kv: kv[1], reverse=True)[
                    : max(1, min(int(limit), 50))
                ]
            ]
            ranking_basis = "alle_bewegungen"
        total = int(sum(int(row.get("anzahl") or 0) for row in rows))
        return {"rows": rows, "label": label, "kpis": {"gesamtvolumen": total, "ranking_basis": ranking_basis}}

    @router.get("/ranking/export.csv")
    def export_report_ranking_csv(
        perspective: str = "depot",
        ids: str = "",
        start_date: str = "",
        end_date: str = "",
        limit: int = 10,
        session=Depends(require_permission("reports_view")),
    ):
        report = report_ranking(perspective, ids, start_date, end_date, limit, session)
        rows = [
            [str(row.get("name") or ""), int(row.get("anzahl") or 0)]
            for row in report["rows"]
            if isinstance(row, dict)
        ]
        label_header = "Praeparat" if report["label"] == "praeparat" else "Depot"
        return csv_response(
            filename=_filename(
                "ranking",
                "csv",
                perspective=perspective,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
            ),
            headers=[label_header, "Anzahl"],
            rows=rows,
        )

    @router.get("/matrix")
    def report_matrix(session=Depends(require_permission("reports_view"))) -> dict:
        if enable_depot_scope:
            scoped_depot_ids = set(allowed_depot_ids(session, require_write=False))
            if session.role != "Admin" and not scoped_depot_ids:
                return {"rows": []}
            allowed_depot_names = set()
            if session.role != "Admin":
                allowed_rows = repository.list_depots(limit=5000, offset=0, allowed_ids=list(scoped_depot_ids))
                allowed_depot_names = {str(row.get("name") or "") for row in allowed_rows}
        else:
            allowed_depot_names = None
            _ = session
        rows = repository.get_matrix_data()
        enriched = []
        for row in rows:
            if enable_depot_scope and session.role != "Admin" and str(row.get("depot") or "") not in allowed_depot_names:
                continue
            diff = int(row["ist_bestand"]) - int(row["sollbestand"])
            item = dict(row)
            item["differenz"] = diff
            enriched.append(item)
        return {"rows": enriched}

    @router.get("/matrix/export.csv")
    def export_report_matrix_csv(session=Depends(require_permission("reports_view"))):
        report = report_matrix(session)
        rows = [
            [row["depot"], row["praeparat"], row["sollbestand"], row["ist_bestand"], row["differenz"]]
            for row in report["rows"]
        ]
        return csv_response(
            filename=_filename("matrix_bestand", "csv"),
            headers=["Depot", "Praeparat", "Soll", "Ist", "Differenz"],
            rows=rows,
        )

    @router.get("/verfall")
    def report_verfall(
        perspective: str = "depot",
        ids: str = "",
        horizon_months: int = 24,
        session=Depends(require_permission("reports_view")),
    ) -> dict:
        _ = session
        safe_perspective = _parse_perspective(perspective)
        selected_ids = _selected_ids(ids)
        rows = repository.get_verfall_prognose(
            depot_ids=selected_ids if safe_perspective == "depot" else None,
            praeparat_ids=selected_ids if safe_perspective == "praeparat" else None,
            horizon_months=horizon_months,
        )
        current_month = date.today().strftime("%Y-%m")
        if add_months is None:
            raise RuntimeError("add_months helper required for verfall reports")
        horizon_end = add_months(date.today().replace(day=1), max(1, min(int(horizon_months), 60))).strftime("%Y-%m")
        filtered_rows = [
            row
            for row in rows
            if row["verfall_monat"] and row["verfall_monat"] <= horizon_end
        ]
        bereits_verfallen = int(
            sum(int(row["anzahl"]) for row in filtered_rows if row["verfall_monat"] < current_month)
        )
        return {
            "rows": filtered_rows,
            "kpis": {
                "bereits_verfallen": bereits_verfallen,
                "gesamt_vorschau": int(sum(int(row["anzahl"]) for row in filtered_rows)),
            },
        }

    @router.get("/verfall/export.csv")
    def export_report_verfall_csv(
        perspective: str = "depot",
        ids: str = "",
        horizon_months: int = 24,
        session=Depends(require_permission("reports_view")),
    ):
        report = report_verfall(perspective, ids, horizon_months, session)
        rows = [[row["verfall_monat"], row["anzahl"]] for row in report["rows"]]
        return csv_response(
            filename=_filename(
                "verfall_prognose",
                "csv",
                perspective=perspective,
                horizon_months=horizon_months,
            ),
            headers=["Verfall_Monat", "Anzahl"],
            rows=rows,
        )

    @router.get("/{report_type}/export.pdf")
    def export_report_pdf(
        report_type: str,
        perspective: str = "depot",
        ids: str = "",
        start_date: str = "",
        end_date: str = "",
        limit: int = 10,
        horizon_months: int = 24,
        session=Depends(require_permission("reports_view")),
    ):
        safe_type = (report_type or "").strip().lower()
        if safe_type == "bewegungen":
            report = report_bewegungen(perspective, ids, start_date, end_date, session)
            headers = ["Monat", "Depot", "Praeparat", "Typ", "Anzahl"]
            rows = [[row["monat"], row["depot"], row["praeparat"], row["typ"], row["anzahl"]] for row in report["rows"]]
            return pdf_response(
                _filename("bewegungsanalyse", "pdf", perspective=perspective, start_date=start_date, end_date=end_date),
                "Bewegungsanalyse",
                headers,
                rows,
                report["kpis"],
            )
        if safe_type == "bestand":
            report = report_bestand(perspective, ids, session)
            headers = ["Depot", "Praeparat", "Soll", "Ist", "Differenz"]
            rows = [[row["depot"], row["praeparat"], row["sollbestand"], row["ist_bestand"], row["differenz"]] for row in report["rows"]]
            return pdf_response(
                _filename("bestandsentwicklung", "pdf", perspective=perspective),
                "Bestandsentwicklung",
                headers,
                rows,
                report["kpis"],
            )
        if safe_type == "ranking":
            report = report_ranking(perspective, ids, start_date, end_date, limit, session)
            label_header = "Praeparat" if report["label"] == "praeparat" else "Depot"
            headers = [label_header, "Anzahl"]
            rows = [[row["name"], row["anzahl"]] for row in report["rows"]]
            return pdf_response(
                _filename("ranking", "pdf", perspective=perspective, start_date=start_date, end_date=end_date, limit=limit),
                "Ranking",
                headers,
                rows,
                report["kpis"],
            )
        if safe_type == "matrix":
            report = report_matrix(session)
            headers = ["Depot", "Praeparat", "Soll", "Ist", "Differenz"]
            rows = [[row["depot"], row["praeparat"], row["sollbestand"], row["ist_bestand"], row["differenz"]] for row in report["rows"]]
            return pdf_response(_filename("matrix_bestand", "pdf"), "Matrix Bestand", headers, rows, {})
        if safe_type == "verfall":
            report = report_verfall(perspective, ids, horizon_months, session)
            headers = ["Verfall_Monat", "Anzahl"]
            rows = [[row["verfall_monat"], row["anzahl"]] for row in report["rows"]]
            return pdf_response(
                _filename("verfall_prognose", "pdf", perspective=perspective, horizon_months=horizon_months),
                "Verfall Prognose",
                headers,
                rows,
                report["kpis"],
            )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unbekannter Report-Typ.")

    @router.get("/{report_type}/export.pptx")
    def export_report_pptx(
        report_type: str,
        perspective: str = "depot",
        ids: str = "",
        start_date: str = "",
        end_date: str = "",
        limit: int = 10,
        horizon_months: int = 24,
        session=Depends(require_permission("reports_view")),
    ):
        safe_type = (report_type or "").strip().lower()
        if safe_type == "bewegungen":
            report = report_bewegungen(perspective, ids, start_date, end_date, session)
            headers = ["Monat", "Depot", "Praeparat", "Typ", "Anzahl"]
            rows = [[row["monat"], row["depot"], row["praeparat"], row["typ"], row["anzahl"]] for row in report["rows"]]
            return pptx_response(
                _filename("bewegungsanalyse", "pptx", perspective=perspective, start_date=start_date, end_date=end_date),
                "Bewegungsanalyse",
                headers,
                rows,
                report["kpis"],
            )
        if safe_type == "bestand":
            report = report_bestand(perspective, ids, session)
            headers = ["Depot", "Praeparat", "Soll", "Ist", "Differenz"]
            rows = [[row["depot"], row["praeparat"], row["sollbestand"], row["ist_bestand"], row["differenz"]] for row in report["rows"]]
            return pptx_response(
                _filename("bestandsentwicklung", "pptx", perspective=perspective),
                "Bestandsentwicklung",
                headers,
                rows,
                report["kpis"],
            )
        if safe_type == "ranking":
            report = report_ranking(perspective, ids, start_date, end_date, limit, session)
            label_header = "Praeparat" if report["label"] == "praeparat" else "Depot"
            headers = [label_header, "Anzahl"]
            rows = [[row["name"], row["anzahl"]] for row in report["rows"]]
            return pptx_response(
                _filename("ranking", "pptx", perspective=perspective, start_date=start_date, end_date=end_date, limit=limit),
                "Ranking",
                headers,
                rows,
                report["kpis"],
            )
        if safe_type == "matrix":
            report = report_matrix(session)
            headers = ["Depot", "Praeparat", "Soll", "Ist", "Differenz"]
            rows = [[row["depot"], row["praeparat"], row["sollbestand"], row["ist_bestand"], row["differenz"]] for row in report["rows"]]
            return pptx_response(_filename("matrix_bestand", "pptx"), "Matrix Bestand", headers, rows, {})
        if safe_type == "verfall":
            report = report_verfall(perspective, ids, horizon_months, session)
            headers = ["Verfall_Monat", "Anzahl"]
            rows = [[row["verfall_monat"], row["anzahl"]] for row in report["rows"]]
            return pptx_response(
                _filename("verfall_prognose", "pptx", perspective=perspective, horizon_months=horizon_months),
                "Verfall Prognose",
                headers,
                rows,
                report["kpis"],
            )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unbekannter Report-Typ.")

    return router
