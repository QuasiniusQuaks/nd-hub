import React, { useEffect, useMemo, useRef, useState } from "react";
import * as core from "../core";
const {
  apiFetch, hasAuthToken, useSessionReload, formatDateTime, formatBytes,
  tabClassName, statusClass, composeAddressParts, classifyStatus,
  readReportFilters, readMultiSelectIds, normalizeDepotRows,
  passwordPolicyHint, copyToClipboard, escapePopupHtml, addBaseTileLayer,
  MAP_TILE_URL, MAP_TILE_ATTR,
} = core;

export function AuditLogsIsland() {
  const [rows, setRows] = useState<AuditRow[]>([]);
  const [error, setError] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(true);
  const [offset, setOffset] = useState<number>(0);
  const [lastCount, setLastCount] = useState<number>(0);

  const load = async (nextOffset = offset) => {
    const search = (document.getElementById("audit-search") as HTMLInputElement | null)?.value?.trim() || "";
    const action = (document.getElementById("audit-filter-action") as HTMLSelectElement | null)?.value || "";
    const resource = (document.getElementById("audit-filter-resource") as HTMLSelectElement | null)?.value || "";
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams({
        limit: "20",
        offset: String(nextOffset),
        q: search,
        action,
        resource_type: resource,
      });
      const data = await apiFetch<AuditRow[]>(`/audit-logs?${params.toString()}`);
      setRows(Array.isArray(data) ? data : []);
      setLastCount(Array.isArray(data) ? data.length : 0);
      setOffset(nextOffset);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Audit-Logs konnten nicht geladen werden.");
    } finally {
      setLoading(false);
    }
  };

  useSessionReload(() => load(0));

  useEffect(() => {
    const reload = document.getElementById("audit-reload");
    const prev = document.getElementById("audit-prev");
    const next = document.getElementById("audit-next");
    const search = document.getElementById("audit-search");
    const action = document.getElementById("audit-filter-action");
    const resource = document.getElementById("audit-filter-resource");
    const onReload = () => void load(offset);
    const onPrev = () => void load(Math.max(0, offset - 20));
    const onNext = () => {
      if (lastCount < 20) return;
      void load(offset + 20);
    };
    const onFilter = () => void load(0);
    if (reload instanceof HTMLButtonElement) reload.addEventListener("click", onReload);
    if (prev instanceof HTMLButtonElement) prev.addEventListener("click", onPrev);
    if (next instanceof HTMLButtonElement) next.addEventListener("click", onNext);
    if (search instanceof HTMLInputElement) search.addEventListener("input", onFilter);
    if (action instanceof HTMLSelectElement) action.addEventListener("change", onFilter);
    if (resource instanceof HTMLSelectElement) resource.addEventListener("change", onFilter);
    return () => {
      if (reload instanceof HTMLButtonElement) reload.removeEventListener("click", onReload);
      if (prev instanceof HTMLButtonElement) prev.removeEventListener("click", onPrev);
      if (next instanceof HTMLButtonElement) next.removeEventListener("click", onNext);
      if (search instanceof HTMLInputElement) search.removeEventListener("input", onFilter);
      if (action instanceof HTMLSelectElement) action.removeEventListener("change", onFilter);
      if (resource instanceof HTMLSelectElement) resource.removeEventListener("change", onFilter);
    };
  }, [offset, lastCount]);

  return (
    <div className="nd-react-shell">
      <div className="nd-react-data-header">
        <h3 className="nd-react-data-title">Audit-Logs</h3>
        <span className="nd-react-badge">
          Offset <strong>{offset}</strong>
        </span>
      </div>
      {error ? <p className="status error">{error}</p> : null}
      {loading ? (
        <p className={statusClass("info")}>Lade Audit-Logs...</p>
      ) : (
        <div className="table-shell table-scroll nd-react-table-compact">
          <table>
            <thead>
              <tr>
                <th>Zeit</th>
                <th>Benutzer</th>
                <th>Aktion</th>
                <th>Ressource</th>
                <th>ID</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              {rows.length ? (
                rows.map((row, idx) => (
                  <tr key={`audit-${idx}`}>
                    <td>{row.timestamp || ""}</td>
                    <td>{row.username || ""}</td>
                    <td>{row.action || ""}</td>
                    <td>{row.resource_type || ""}</td>
                    <td>{String(row.resource_id ?? "")}</td>
                    <td>
                      <pre className="audit-details">{String(row.details || "")}</pre>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="empty-cell">
                    Keine Audit-Eintraege fuer die aktuelle Filterung.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

