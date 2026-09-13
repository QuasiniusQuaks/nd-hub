import React, { useEffect, useMemo, useRef, useState } from "react";
import L from "leaflet";
import * as core from "../core";
const {
  apiFetch, hasAuthToken, useSessionReload, formatDateTime, formatBytes,
  tabClassName, statusClass, composeAddressParts, classifyStatus,
  readReportFilters, readMultiSelectIds, normalizeDepotRows,
  passwordPolicyHint, copyToClipboard, escapePopupHtml, addBaseTileLayer,
  MAP_TILE_URL, MAP_TILE_ATTR,
} = core;

export function ReportTableIsland() {
  const [rows, setRows] = useState<ReportRow[]>([]);
  const [kpis, setKpis] = useState<Record<string, unknown>>({});
  const [error, setError] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const [hasLoaded, setHasLoaded] = useState<boolean>(false);
  const reportOptionsRef = useRef<{ depots: Array<{ id: number; name?: string }>; praeparate: Array<{ id: number; name?: string }> }>({
    depots: [],
    praeparate: [],
  });

  const load = async () => {
    const filters = readReportFilters();
    if (!filters.ids.length) {
      setError("Bitte mindestens eine ID fuer die Auswertung waehlen.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams({
        perspective: filters.perspective,
        ids: filters.ids.join(","),
      });
      if (filters.startDate) params.set("start_date", filters.startDate);
      if (filters.endDate) params.set("end_date", filters.endDate);
      const payload = await apiFetch<ReportResponse>(`/reports/${filters.typ}?${params.toString()}`);
      setRows(Array.isArray(payload?.rows) ? payload.rows : []);
      setKpis(payload?.kpis && typeof payload.kpis === "object" ? payload.kpis : {});
      setHasLoaded(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Auswertung konnte nicht geladen werden.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const loadButton = document.getElementById("report-load");
    if (!(loadButton instanceof HTMLButtonElement)) return;
    const listener = () => {
      void load();
    };
    loadButton.addEventListener("click", listener);
    return () => loadButton.removeEventListener("click", listener);
  }, []);

  useEffect(() => {
    const perspectiveSelect = document.getElementById("report-perspective");
    const idsSelect = document.getElementById("report-ids");
    if (!(perspectiveSelect instanceof HTMLSelectElement)) return;
    if (!(idsSelect instanceof HTMLSelectElement)) return;

    const applyOptions = () => {
      const useDepots = perspectiveSelect.value === "depot";
      const source = useDepots ? reportOptionsRef.current.depots : reportOptionsRef.current.praeparate;
      const previous = new Set(Array.from(idsSelect.selectedOptions).map((option) => option.value));
      idsSelect.innerHTML = "";
      for (const row of source) {
        const option = document.createElement("option");
        option.value = String(row.id);
        option.textContent = `${row.name || (useDepots ? `Depot #${row.id}` : `Praeparat #${row.id}`)} (#${row.id})`;
        option.selected = previous.has(option.value);
        idsSelect.appendChild(option);
      }
    };

    const loadOptions = async () => {
      try {
        const [depots, praeparate] = await Promise.all([
          apiFetch<Array<{ id: number; name?: string }>>("/depots?limit=500&offset=0&q="),
          apiFetch<Array<{ id: number; name?: string }>>("/praeparate?limit=500&offset=0&q="),
        ]);
        reportOptionsRef.current.depots = Array.isArray(depots) ? depots : [];
        reportOptionsRef.current.praeparate = Array.isArray(praeparate) ? praeparate : [];
        applyOptions();
      } catch {
        // Legacy-Loader bleibt weiterhin aktiv; Fehler hier nicht hart anzeigen.
      }
    };

    const onPerspectiveChange = () => applyOptions();
    perspectiveSelect.addEventListener("change", onPerspectiveChange);
    void loadOptions();
    return () => perspectiveSelect.removeEventListener("change", onPerspectiveChange);
  }, []);

  useEffect(() => {
    const sleep = (ms: number) => new Promise((resolve) => window.setTimeout(resolve, ms));
    const selectDepotId = (idsSelect: HTMLSelectElement, depotId: number): boolean => {
      let found = false;
      for (const option of idsSelect.options) {
        const selected = option.value === String(depotId);
        option.selected = selected;
        if (selected) found = true;
      }
      return found;
    };
    const onOpenDepotStockReport = async (event: Event) => {
      const customEvent = event as CustomEvent<{ depotId?: number }>;
      const depotId = Number(customEvent.detail?.depotId || 0);
      if (!Number.isFinite(depotId) || depotId <= 0) return;

      const perspectiveSelect = document.getElementById("report-perspective");
      const typeSelect = document.getElementById("report-type");
      const idsSelect = document.getElementById("report-ids");
      if (!(perspectiveSelect instanceof HTMLSelectElement)) return;
      if (!(typeSelect instanceof HTMLSelectElement)) return;
      if (!(idsSelect instanceof HTMLSelectElement)) return;

      perspectiveSelect.value = "depot";
      perspectiveSelect.dispatchEvent(new Event("change"));
      typeSelect.value = "bestand";

      let optionFound = false;
      for (let attempt = 0; attempt < 20; attempt += 1) {
        optionFound = selectDepotId(idsSelect, depotId);
        if (optionFound) break;
        await sleep(100);
      }
      if (!optionFound) {
        try {
          const depots = await apiFetch<Array<{ id: number; name?: string }>>("/depots?limit=500");
          const matchingDepot = (depots || []).find((item) => Number(item.id) === depotId);
          if (matchingDepot) {
            const injected = document.createElement("option");
            injected.value = String(depotId);
            injected.textContent = `${matchingDepot.name || `Depot #${depotId}`} (#${depotId})`;
            idsSelect.appendChild(injected);
            optionFound = selectDepotId(idsSelect, depotId);
          }
        } catch {
          // Fehler wird unten ueber die Standardmeldung behandelt.
        }
        if (!optionFound) {
          setError(`Depot #${depotId} ist in den Auswertungsfiltern nicht verfuegbar.`);
          return;
        }
      }
      void load();
    };

    window.addEventListener("ndhub-open-depot-stock-report", onOpenDepotStockReport as EventListener);
    return () => {
      window.removeEventListener("ndhub-open-depot-stock-report", onOpenDepotStockReport as EventListener);
    };
  }, []);

  const columns = useMemo(() => {
    if (!rows.length) return [];
    return Object.keys(rows[0]);
  }, [rows]);
  const quoteValue = Number(kpis.bestandsquote ?? 0);
  const quotePercent = Number.isFinite(quoteValue) ? Math.max(0, Math.min(100, quoteValue)) : 0;
  const visualKpis = [
    {
      key: "bestandsquote",
      label: "Bestandsquote",
      value: `${quotePercent.toFixed(2)}%`,
      tone: quotePercent < 90 ? "warning" : "success",
    },
    {
      key: "kritische_luecken",
      label: "Kritische Luecken",
      value: String(Number(kpis.kritische_luecken ?? 0)),
      tone: Number(kpis.kritische_luecken ?? 0) > 0 ? "warning" : "success",
    },
    {
      key: "gesamtbestand",
      label: "Gesamtbestand",
      value: String(Number(kpis.gesamtbestand ?? 0)),
      tone: "default",
    },
  ];

  return (
    <div className="nd-react-shell">
      <div className="nd-react-heading">
        <p className="nd-react-eyebrow">Daten und KPIs</p>
        <button type="button" className="btn-primary" onClick={() => void load()} disabled={loading}>
          {loading ? "Laedt..." : "Auswertung laden"}
        </button>
      </div>
      {error ? <p className="status error">{error}</p> : null}
      <div className="nd-react-summary-grid">
        <article className="nd-react-summary-card">
          <span className="label">Datensaetze</span>
          <span className="value">{rows.length}</span>
        </article>
        <article className="nd-react-summary-card">
          <span className="label">KPI-Felder</span>
          <span className="value">{Object.keys(kpis).length}</span>
        </article>
      </div>
      {Object.keys(kpis).length ? (
        <div className="nd-react-kpi-visual-grid">
          {visualKpis.map((item) => (
            <article key={item.key} className={`nd-react-kpi-visual-card ${item.tone}`}>
              <span className="label">{item.label}</span>
              <span className="value">{item.value}</span>
              {item.key === "bestandsquote" ? (
                <div className="nd-react-kpi-meter" aria-label="Bestandsquote">
                  <div className="nd-react-kpi-meter-fill" style={{ width: `${quotePercent}%` }} />
                </div>
              ) : null}
            </article>
          ))}
        </div>
      ) : null}
      <div className="table-shell table-scroll nd-react-table-compact">
        <table>
          <thead>
            <tr>
              {columns.length ? (
                columns.map((column) => <th key={column}>{column}</th>)
              ) : (
                <th>Daten</th>
              )}
            </tr>
          </thead>
          <tbody>
            {rows.length ? (
              rows.map((row, idx) => (
                <tr key={`row-${idx}`}>
                  {columns.map((column) => (
                    <td key={`${idx}-${column}`}>{String(row[column] ?? "")}</td>
                  ))}
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={Math.max(1, columns.length)} className="empty-cell">
                  {hasLoaded ? "Keine Daten fuer die aktuellen Filter." : "Noch keine Auswertung geladen."}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

