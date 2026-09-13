import React, { useEffect, useMemo, useRef, useState } from "react";
import * as core from "../core";
const {
  apiFetch, hasAuthToken, useSessionReload, formatDateTime, formatBytes,
  tabClassName, statusClass, composeAddressParts, classifyStatus,
  readReportFilters, readMultiSelectIds, normalizeDepotRows,
  passwordPolicyHint, copyToClipboard, escapePopupHtml, addBaseTileLayer,
  MAP_TILE_URL, MAP_TILE_ATTR,
} = core;

export function DesktopSyncFormIsland() {
  const [backendUrl] = useState<string>(window.location.origin || `${window.location.protocol}//${window.location.host}`);
  const [clientLabel, setClientLabel] = useState<string>("");
  const [token, setToken] = useState<string>("");
  const [expiresAt, setExpiresAt] = useState<string>("");
  const [status, setStatus] = useState<string>("Backend-URL geladen. Token bei Bedarf erzeugen.");
  const [busy, setBusy] = useState<boolean>(false);

  const generate = async () => {
    setBusy(true);
    setStatus("Token wird erzeugt...");
    try {
      const payload = await apiFetch<{ token?: string; backend_url?: string; expires_at?: string }>("/auth/desktop-sync-token", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ client_label: clientLabel.trim() || null }),
      });
      setToken(String(payload.token || ""));
      setExpiresAt(payload.expires_at ? formatDateTime(payload.expires_at) : "");
      setStatus("Desktop-Token erzeugt. Bitte sicher speichern.");
      window.dispatchEvent(new CustomEvent("ndhub-desktop-token-created"));
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Desktop-Token konnte nicht erzeugt werden.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="nd-react-shell">
      <div className="nd-react-data-header">
        <h3 className="nd-react-data-title">Desktop-Sync Zugang</h3>
      </div>
      <form className="grid" onSubmit={(event) => event.preventDefault()}>
        <label>
          Backend-URL
          <input type="text" readOnly value={backendUrl} />
        </label>
        <label>
          Client-Bezeichnung
          <input type="text" maxLength={120} value={clientLabel} onChange={(event) => setClientLabel(event.target.value)} />
        </label>
        <label>
          Desktop-Token
          <input type="text" readOnly value={token} />
        </label>
        <label>
          Gueltig bis
          <input type="text" readOnly value={expiresAt} />
        </label>
        <div className="actions">
          <button type="button" onClick={() => void generate()} disabled={busy}>{busy ? "Erzeuge..." : "Token erzeugen"}</button>
          <button type="button" onClick={() => void copyToClipboard(backendUrl)}>URL kopieren</button>
          <button type="button" onClick={() => void copyToClipboard(token)}>Token kopieren</button>
        </div>
      </form>
      <p className={statusClass(classifyStatus(status))}>{status}</p>
    </div>
  );
}

