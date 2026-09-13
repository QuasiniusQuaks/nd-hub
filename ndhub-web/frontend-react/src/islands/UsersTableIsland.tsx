import React, { useEffect, useMemo, useRef, useState } from "react";
import * as core from "../core";
const {
  apiFetch, hasAuthToken, useSessionReload, formatDateTime, formatBytes,
  tabClassName, statusClass, composeAddressParts, classifyStatus,
  readReportFilters, readMultiSelectIds, normalizeDepotRows,
  passwordPolicyHint, copyToClipboard, escapePopupHtml, addBaseTileLayer,
  MAP_TILE_URL, MAP_TILE_ATTR,
} = core;

export function UsersTableIsland() {
  const [rows, setRows] = useState<UserRow[]>([]);
  const [error, setError] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(true);

  const loadUsers = async () => {
    setLoading(true);
    try {
      const data = await apiFetch<UserRow[]>("/users");
      setRows(Array.isArray(data) ? data : []);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Benutzer konnten nicht geladen werden.");
    } finally {
      setLoading(false);
    }
  };

  useSessionReload(loadUsers);

  useEffect(() => {
    const reloadButton = document.getElementById("users-reload");
    if (!(reloadButton instanceof HTMLButtonElement)) return;
    const listener = () => void loadUsers();
    reloadButton.addEventListener("click", listener);
    return () => reloadButton.removeEventListener("click", listener);
  }, []);

  useEffect(() => {
    const onRefresh = () => void loadUsers();
    window.addEventListener("ndhub-users-changed", onRefresh);
    return () => window.removeEventListener("ndhub-users-changed", onRefresh);
  }, []);

  return (
    <div className="nd-react-shell">
      <div className="nd-react-data-header">
        <h3 className="nd-react-data-title">Benutzerliste</h3>
        <span className="nd-react-badge">
          Eintraege <strong>{rows.length}</strong>
        </span>
      </div>
      {error ? <p className="status error">{error}</p> : null}
      {loading ? (
        <p className={statusClass("info")}>Lade Benutzer...</p>
      ) : (
        <div className="table-shell table-scroll nd-react-table-compact">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Benutzer</th>
                <th>Rolle</th>
                <th>E-Mail</th>
                <th>Aktiv</th>
                <th>Rechte</th>
                <th>Fehlversuche</th>
                <th>Gesperrt bis</th>
                <th>Default-PW</th>
                <th>Letzter Login</th>
              </tr>
            </thead>
            <tbody>
              {rows.length ? (
                rows.map((row) => (
                  <tr key={row.id}>
                    <td>{row.id}</td>
                    <td>{row.username}</td>
                    <td>{row.role}</td>
                    <td>{row.email || "-"}</td>
                    <td>{row.is_active ? "Ja" : "Nein"}</td>
                    <td>{(row.permissions || []).join(", ") || "Standard"}</td>
                    <td>{row.failed_attempts || 0}</td>
                    <td>{row.locked_until || "-"}</td>
                    <td>{row.is_default_password ? "Ja" : "Nein"}</td>
                    <td>{row.last_login || "-"}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={10} className="empty-cell">
                    Keine Benutzer vorhanden.
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

