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

export function MovementHistoryIsland() {
  const [rows, setRows] = useState<MovementRow[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>("");
  const [offset, setOffset] = useState<number>(0);
  const [lastCount, setLastCount] = useState<number>(0);

  const load = async (nextOffset = offset) => {
    const selectedDepot = Number((document.getElementById("bewegung-filter-depot") as HTMLSelectElement | null)?.value || 0);
    const selectedPraeparat = Number((document.getElementById("bewegung-filter-praeparat") as HTMLSelectElement | null)?.value || 0);
    const onlyWithPdf = (document.getElementById("bewegung-filter-has-attachment") as HTMLInputElement | null)?.checked ? 1 : 0;
    const startDate = (document.getElementById("bewegung-filter-start-date") as HTMLInputElement | null)?.value?.trim() || "";
    const endDate = (document.getElementById("bewegung-filter-end-date") as HTMLInputElement | null)?.value?.trim() || "";
    const searchQuery = (document.getElementById("bewegung-search") as HTMLInputElement | null)?.value?.trim() || "";
    const typ = (document.getElementById("bewegung-filter-typ") as HTMLSelectElement | null)?.value || "";

    setLoading(true);
    setError("");
    try {
      const query = `/bewegungen?limit=20&offset=${nextOffset}&q=${encodeURIComponent(searchQuery)}&typ=${encodeURIComponent(
        typ,
      )}&depot_id=${selectedDepot > 0 ? selectedDepot : 0}&praeparat_id=${selectedPraeparat > 0 ? selectedPraeparat : 0}&has_attachment=${onlyWithPdf}&start_date=${encodeURIComponent(
        startDate,
      )}&end_date=${encodeURIComponent(endDate)}`;
      const data = await apiFetch<MovementRow[]>(query);
      setRows(Array.isArray(data) ? data : []);
      setLastCount(Array.isArray(data) ? data.length : 0);
      setOffset(nextOffset);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Bewegungen konnten nicht geladen werden.");
    } finally {
      setLoading(false);
    }
  };

  useSessionReload(() => load(0));

  useEffect(() => {
    const onCreated = () => {
      void load(0);
    };
    window.addEventListener("ndhub-movement-created", onCreated);
    return () => window.removeEventListener("ndhub-movement-created", onCreated);
  }, [offset]);

  useEffect(() => {
    const reload = document.getElementById("reload-bewegungen");
    const prev = document.getElementById("bewegung-prev");
    const next = document.getElementById("bewegung-next");
    const filters = [
      "bewegung-search",
      "bewegung-filter-depot",
      "bewegung-filter-typ",
      "bewegung-filter-praeparat",
      "bewegung-filter-has-attachment",
      "bewegung-filter-start-date",
      "bewegung-filter-end-date",
    ]
      .map((id) => document.getElementById(id))
      .filter(Boolean) as HTMLElement[];

    const onReload = () => {
      void load(offset);
    };
    const onPrev = () => {
      void load(Math.max(0, offset - 20));
    };
    const onNext = () => {
      if (lastCount < 20) return;
      void load(offset + 20);
    };
    const onFilter = () => {
      void load(0);
    };

    if (reload instanceof HTMLButtonElement) reload.addEventListener("click", onReload);
    if (prev instanceof HTMLButtonElement) prev.addEventListener("click", onPrev);
    if (next instanceof HTMLButtonElement) next.addEventListener("click", onNext);
    for (const element of filters) {
      const eventName = element instanceof HTMLInputElement ? "input" : "change";
      element.addEventListener(eventName, onFilter);
    }

    return () => {
      if (reload instanceof HTMLButtonElement) reload.removeEventListener("click", onReload);
      if (prev instanceof HTMLButtonElement) prev.removeEventListener("click", onPrev);
      if (next instanceof HTMLButtonElement) next.removeEventListener("click", onNext);
      for (const element of filters) {
        const eventName = element instanceof HTMLInputElement ? "input" : "change";
        element.removeEventListener(eventName, onFilter);
      }
    };
  }, [offset, lastCount]);

  const openAttachment = async (id: number) => {
    try {
      const response = await fetch(`/bewegungen/${id}/attachment`, {
        headers: { Authorization: `Bearer ${window.localStorage.getItem("ndhub_token") || ""}` },
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const blob = await response.blob();
      const blobUrl = URL.createObjectURL(blob);
      window.open(blobUrl, "_blank", "noopener,noreferrer");
      window.setTimeout(() => URL.revokeObjectURL(blobUrl), 10000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Anhang konnte nicht geoeffnet werden.");
    }
  };

  const downloadAttachment = async (id: number, filename: string) => {
    try {
      const response = await fetch(`/bewegungen/${id}/attachment?download=true`, {
        headers: { Authorization: `Bearer ${window.localStorage.getItem("ndhub_token") || ""}` },
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const blob = await response.blob();
      const blobUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = blobUrl;
      link.download = filename || `bewegung_${id}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(blobUrl), 10000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Anhang konnte nicht heruntergeladen werden.");
    }
  };

  return (
    <div className="nd-react-shell">
      <div className="nd-react-data-header">
        <h3 className="nd-react-data-title">Bewegungsverlauf</h3>
        <span className="nd-react-badge">
          Seite ab <strong>{offset + 1}</strong>
        </span>
      </div>
      {error ? <p className="status error">{error}</p> : null}
      {loading ? (
        <p className={statusClass("info")}>Lade Bewegungen...</p>
      ) : (
        <div className="table-shell table-scroll nd-react-table-compact">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Typ</th>
                <th>Charge</th>
                <th>Verfall</th>
                <th>Anzahl</th>
                <th>Depot</th>
                <th>Praeparat</th>
                <th>PDF</th>
                <th>Aktionen</th>
              </tr>
            </thead>
            <tbody>
              {rows.length ? (
                rows.map((row) => {
                  const hasAttachment = row.has_attachment === true || row.has_attachment === 1;
                  return (
                    <tr key={row.id}>
                      <td>{row.id}</td>
                      <td>{row.typ || ""}</td>
                      <td>{row.charge || ""}</td>
                      <td>{row.verfall || ""}</td>
                      <td>{row.anzahl ?? ""}</td>
                      <td>{row.depot || row.depot_id || ""}</td>
                      <td>{row.praeparat || row.praeparat_id || ""}</td>
                      <td>{hasAttachment ? row.datei_name || "PDF vorhanden" : "Kein PDF"}</td>
                      <td>
                        {hasAttachment ? (
                          <div className="actions">
                            <button type="button" className="btn-secondary" onClick={() => void openAttachment(row.id)}>
                              Oeffnen
                            </button>
                            <button
                              type="button"
                              className="btn-secondary"
                              onClick={() => void downloadAttachment(row.id, row.datei_name || "")}
                            >
                              Download
                            </button>
                          </div>
                        ) : (
                          "-"
                        )}
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={9} className="empty-cell">
                    Keine Bewegungen fuer die aktuelle Filterung.
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

