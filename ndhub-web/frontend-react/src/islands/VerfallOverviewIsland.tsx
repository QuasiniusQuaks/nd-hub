import React, { useEffect, useMemo, useRef, useState } from "react";
import * as core from "../core";
const {
  apiFetch, hasAuthToken, useSessionReload, formatDateTime, formatBytes,
  tabClassName, statusClass, composeAddressParts, classifyStatus,
  readReportFilters, readMultiSelectIds, normalizeDepotRows,
  passwordPolicyHint, copyToClipboard, escapePopupHtml, addBaseTileLayer,
  MAP_TILE_URL, MAP_TILE_ATTR,
} = core;

export function VerfallOverviewIsland() {
  const [rows, setRows] = useState<Array<Record<string, string | number | null>>>([]);
  const [stats, setStats] = useState<{ kritisch: number; warnung: number; achtung: number; gesamt_menge: number }>({
    kritisch: 0,
    warnung: 0,
    achtung: 0,
    gesamt_menge: 0,
  });
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>("");

  const load = async () => {
    const perspective = (document.getElementById("verfall-perspective") as HTMLSelectElement | null)?.value || "depot";
    const category = (document.getElementById("verfall-category") as HTMLSelectElement | null)?.value || "alle";
    const query = (document.getElementById("verfall-search") as HTMLInputElement | null)?.value?.trim() || "";
    const ids = readMultiSelectIds("verfall-ids");
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams({
        perspective,
        ids: ids.join(","),
        q: query,
        category,
      });
      const payload = await apiFetch<VerfallOverviewResponse>(`/verfall/overview?${params.toString()}`);
      setRows(Array.isArray(payload?.rows) ? payload.rows : []);
      setStats({
        kritisch: Number(payload?.stats?.kritisch || 0),
        warnung: Number(payload?.stats?.warnung || 0),
        achtung: Number(payload?.stats?.achtung || 0),
        gesamt_menge: Number(payload?.stats?.gesamt_menge || 0),
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Verfallsdaten konnten nicht geladen werden.");
    } finally {
      setLoading(false);
    }
  };

  useSessionReload(load);

  useEffect(() => {
    const loadButton = document.getElementById("verfall-load");
    const exportButton = document.getElementById("verfall-export-csv");
    const perspective = document.getElementById("verfall-perspective");
    const category = document.getElementById("verfall-category");
    const search = document.getElementById("verfall-search");
    const ids = document.getElementById("verfall-ids");
    const onLoad = () => void load();
    const onAuto = () => void load();
    if (loadButton instanceof HTMLButtonElement) loadButton.addEventListener("click", onLoad);
    if (perspective instanceof HTMLSelectElement) perspective.addEventListener("change", onAuto);
    if (category instanceof HTMLSelectElement) category.addEventListener("change", onAuto);
    if (search instanceof HTMLInputElement) search.addEventListener("input", onAuto);
    if (ids instanceof HTMLSelectElement) ids.addEventListener("change", onAuto);
    // Keep legacy export button visible/usable; this island only renders data.
    if (exportButton instanceof HTMLButtonElement) exportButton.disabled = false;
    return () => {
      if (loadButton instanceof HTMLButtonElement) loadButton.removeEventListener("click", onLoad);
      if (perspective instanceof HTMLSelectElement) perspective.removeEventListener("change", onAuto);
      if (category instanceof HTMLSelectElement) category.removeEventListener("change", onAuto);
      if (search instanceof HTMLInputElement) search.removeEventListener("input", onAuto);
      if (ids instanceof HTMLSelectElement) ids.removeEventListener("change", onAuto);
    };
  }, []);

  return (
    <div className="nd-react-shell">
      <div className="nd-react-heading">
        <p className="nd-react-eyebrow">Verfallsmonitor</p>
        <button type="button" className="btn-primary" onClick={() => void load()} disabled={loading}>
          {loading ? "Laedt..." : "Laden"}
        </button>
      </div>
      {error ? <p className="status error">{error}</p> : null}
      <div className="dashboard-kpis">
        <article className="kpi-card">
          <h3>Kritisch</h3>
          <p className="kpi-value">{stats.kritisch}</p>
        </article>
        <article className="kpi-card">
          <h3>Warnung</h3>
          <p className="kpi-value">{stats.warnung}</p>
        </article>
        <article className="kpi-card">
          <h3>Achtung</h3>
          <p className="kpi-value">{stats.achtung}</p>
        </article>
        <article className="kpi-card">
          <h3>Gesamtmenge</h3>
          <p className="kpi-value">{stats.gesamt_menge}</p>
        </article>
      </div>
      <div className="table-shell table-scroll nd-react-table-compact">
        <table>
          <thead>
            <tr>
              <th>Depot</th>
              <th>Praeparat</th>
              <th>Charge</th>
              <th>Verfall</th>
              <th>Tage bis Verfall</th>
              <th>Status</th>
              <th>Anzahl</th>
            </tr>
          </thead>
          <tbody>
            {rows.length ? (
              rows.map((row, idx) => (
                <tr key={`vf-${idx}`}>
                  <td>{String(row.depot ?? "")}</td>
                  <td>{String(row.praeparat ?? "")}</td>
                  <td>{String(row.charge ?? "")}</td>
                  <td>{String(row.verfall ?? "")}</td>
                  <td>{String(row.tage_bis_verfall ?? "")}</td>
                  <td>{String(row.kategorie ?? "")}</td>
                  <td>{String(row.anzahl ?? "")}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={7} className="empty-cell">
                  Keine Verfallspositionen fuer diese Filter.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

