import React, { useEffect, useMemo, useRef, useState } from "react";
import * as core from "../core";
const {
  apiFetch, hasAuthToken, useSessionReload, formatDateTime, formatBytes,
  tabClassName, statusClass, composeAddressParts, classifyStatus,
  readReportFilters, readMultiSelectIds, normalizeDepotRows,
  passwordPolicyHint, copyToClipboard, escapePopupHtml, addBaseTileLayer,
  MAP_TILE_URL, MAP_TILE_ATTR,
} = core;

export function AssignmentManagerIsland() {
  const [depots, setDepots] = useState<DepotRow[]>([]);
  const [selectedDepotId, setSelectedDepotId] = useState<number>(0);
  const [rows, setRows] = useState<AssignmentRow[]>([]);
  const [status, setStatus] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(true);

  const loadDepots = async () => {
    const depotsPayload = await apiFetch<DepotRow[] | { rows?: DepotRow[] }>("/depots?limit=500&offset=0&q=");
    const nextDepots = normalizeDepotRows(depotsPayload);
    setDepots(nextDepots);
    if (!selectedDepotId && nextDepots.length) {
      setSelectedDepotId(Number(nextDepots[0].id));
    }
    return nextDepots;
  };

  const loadAssignments = async (depotId: number) => {
    if (!depotId) {
      setRows([]);
      return;
    }
    const data = await apiFetch<AssignmentRow[]>(`/depots/${depotId}/zuordnungen`);
    setRows(Array.isArray(data) ? data : []);
  };

  useEffect(() => {
    void (async () => {
      setLoading(true);
      try {
        const nextDepots = await loadDepots();
        const initialDepotId = selectedDepotId || Number(nextDepots[0]?.id || 0);
        if (initialDepotId) await loadAssignments(initialDepotId);
      } catch (err) {
        setStatus(err instanceof Error ? err.message : "Zuordnungen konnten nicht geladen werden.");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  useEffect(() => {
    if (!selectedDepotId) return;
    void loadAssignments(selectedDepotId);
  }, [selectedDepotId]);

  const updateRow = (praeparatId: number, patch: Partial<AssignmentRow>) => {
    setRows((prev) =>
      prev.map((row) => (row.praeparat_id === praeparatId ? { ...row, ...patch } : row)),
    );
  };

  const save = async () => {
    if (!selectedDepotId) return;
    setStatus("Speichere Zuordnungen...");
    try {
      const assignments = rows
        .filter((row) => Boolean(row.assigned))
        .map((row) => ({
          praeparat_id: Number(row.praeparat_id),
          sollbestand: Math.max(0, Number(row.sollbestand || 0)),
        }));
      await apiFetch(`/depots/${selectedDepotId}/zuordnungen`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ assignments }),
      });
      setStatus("Zuordnungen gespeichert.");
      await loadAssignments(selectedDepotId);
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Zuordnungen konnten nicht gespeichert werden.");
    }
  };

  return (
    <div className="nd-react-shell">
      <h3>Depot-Praeparate-Zuordnung</h3>
      <label>
        Depot
        <select
          value={selectedDepotId ? String(selectedDepotId) : ""}
          onChange={(event) => setSelectedDepotId(Number(event.target.value || 0))}
        >
          <option value="">Depot waehlen</option>
          {depots.map((row) => (
            <option key={row.id} value={row.id}>
              {row.name || "-"} (#{row.id})
            </option>
          ))}
        </select>
      </label>
      <div className="grid">
        {rows.length ? (
          rows.map((row) => (
            <div key={row.praeparat_id} className="toolbar">
              <label>
                <input
                  type="checkbox"
                  checked={Boolean(row.assigned)}
                  onChange={(event) => updateRow(row.praeparat_id, { assigned: event.target.checked })}
                />
                {row.praeparat_name || `Praeparat #${row.praeparat_id}`}
              </label>
              <label>
                Sollbestand
                <input
                  type="number"
                  min={0}
                  value={Number(row.sollbestand || 0)}
                  disabled={!row.assigned}
                  onChange={(event) =>
                    updateRow(row.praeparat_id, { sollbestand: Number(event.target.value || 0) })
                  }
                />
              </label>
            </div>
          ))
        ) : (
          <p className="muted">{loading ? "Lade Zuordnungen..." : "Keine Zuordnungen vorhanden."}</p>
        )}
      </div>
      <div className="actions">
        <button type="button" onClick={() => void save()} disabled={!selectedDepotId}>
          Zuordnungen speichern
        </button>
      </div>
      <p className={statusClass(classifyStatus(status))}>{status}</p>
    </div>
  );
}

