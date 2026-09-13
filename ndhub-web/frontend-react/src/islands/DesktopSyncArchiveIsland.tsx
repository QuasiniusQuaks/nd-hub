import React, { useEffect, useMemo, useRef, useState } from "react";
import * as core from "../core";
const {
  apiFetch, hasAuthToken, useSessionReload, formatDateTime, formatBytes,
  tabClassName, statusClass, composeAddressParts, classifyStatus,
  readReportFilters, readMultiSelectIds, normalizeDepotRows,
  passwordPolicyHint, copyToClipboard, escapePopupHtml, addBaseTileLayer,
  MAP_TILE_URL, MAP_TILE_ATTR,
} = core;

export function DesktopSyncArchiveIsland() {
  const [rows, setRows] = useState<DesktopToken[]>([]);
  const [error, setError] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(true);

  const load = async () => {
    setLoading(true);
    try {
      const data = await apiFetch<DesktopToken[]>("/auth/desktop-sync-tokens");
      setRows(Array.isArray(data) ? data : []);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Desktop-Sync-Archiv konnte nicht geladen werden.");
    } finally {
      setLoading(false);
    }
  };

  useSessionReload(load);

  useEffect(() => {
    const onRefresh = () => {
      void load();
    };
    window.addEventListener("ndhub-desktop-token-created", onRefresh);
    return () => window.removeEventListener("ndhub-desktop-token-created", onRefresh);
  }, []);

  const activeRows = useMemo(() => rows.filter((item) => String(item.status || "").toLowerCase() === "aktiv"), [rows]);

  const revoke = async (fingerprint: string) => {
    try {
      await apiFetch("/auth/desktop-sync-token/revoke", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token_fingerprint: fingerprint }),
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Token-Widerruf fehlgeschlagen.");
    }
  };

  return (
    <div className="nd-react-shell">
      <div className="nd-react-data-header">
        <h3 className="nd-react-data-title">Desktop-Token-Archiv</h3>
        <span className="nd-react-badge">
          Aktiv <strong>{activeRows.length}</strong>
        </span>
      </div>
      {error ? <p className="status error">{error}</p> : null}
      {loading ? (
        <p className={statusClass("info")}>Lade Token-Archiv...</p>
      ) : (
        <>
          <div className="table-shell table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Erstellt</th>
                  <th>Client</th>
                  <th>Benutzer</th>
                  <th>Rolle</th>
                  <th>Gueltig bis</th>
                  <th>Status</th>
                  <th>Token</th>
                  <th>Aktion</th>
                </tr>
              </thead>
              <tbody>
                {rows.length ? (
                  rows.map((row) => (
                    <tr key={row.token_fingerprint}>
                      <td>{formatDateTime(row.created_at)}</td>
                      <td>{row.client_label || "-"}</td>
                      <td>{row.username}</td>
                      <td>{row.role || "-"}</td>
                      <td>{formatDateTime(row.expires_at)}</td>
                      <td>{row.status}</td>
                      <td>
                        <code>{row.token_masked}</code>
                      </td>
                      <td>
                        {String(row.status || "").toLowerCase() === "aktiv" ? (
                          <button type="button" onClick={() => void revoke(row.token_fingerprint)}>
                            Widerrufen
                          </button>
                        ) : (
                          "-"
                        )}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={8} className="empty-cell">
                      Noch keine Tokens erzeugt.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <p className={statusClass("info")}>Aktive Tokens: {activeRows.length}</p>
        </>
      )}
    </div>
  );
}

