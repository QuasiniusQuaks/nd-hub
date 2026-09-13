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

export function BackupManagerIsland() {
  const [rows, setRows] = useState<BackupRow[]>([]);
  const [status, setStatus] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(true);
  const [dbEngine, setDbEngine] = useState<string>("sqlite");
  const [maxRestoreSizeMb, setMaxRestoreSizeMb] = useState<number>(20);
  const [restoreFile, setRestoreFile] = useState<File | null>(null);
  const [workingAction, setWorkingAction] = useState<"" | "download" | "create" | "reload" | "restore">("");

  const loadList = async () => {
    setWorkingAction("reload");
    setStatus("Lade Backup-Liste...");
    try {
      const data = await apiFetch<BackupListResponse>("/admin/backup/list?limit=200");
      setRows(Array.isArray(data.rows) ? data.rows : []);
      setDbEngine(String(data.db_engine || "sqlite").toLowerCase());
      setMaxRestoreSizeMb(Math.max(1, Number(data.max_restore_size_mb || 20)));
      setStatus("Backup-Liste aktualisiert.");
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Backup-Liste konnte nicht geladen werden.");
    } finally {
      setWorkingAction("");
      setLoading(false);
    }
  };

  useSessionReload(loadList);

  const tokenHeaders = (): HeadersInit => {
    const token = window.localStorage.getItem("ndhub_token") || "";
    return token ? { Authorization: `Bearer ${token}` } : {};
  };

  const startDownload = async (path: string, fallbackName: string) => {
    const response = await fetch(path, { headers: tokenHeaders() });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const blob = await response.blob();
    const contentDisposition = response.headers.get("content-disposition") || "";
    const match = /filename=\"?([^\";]+)\"?/i.exec(contentDisposition);
    const filename = match ? match[1] : fallbackName;
    const blobUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = blobUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(blobUrl), 10000);
    return filename;
  };

  const downloadLatest = async () => {
    setWorkingAction("download");
    setStatus("Erstelle Backup...");
    try {
      await startDownload("/admin/backup/download", "ndhub_backup.db");
      setStatus("Backup heruntergeladen.");
      await loadList();
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Backup-Download fehlgeschlagen.");
    } finally {
      setWorkingAction("");
    }
  };

  const createBackup = async () => {
    setWorkingAction("create");
    setStatus("Erstelle Backup...");
    try {
      const result = await apiFetch<{ filename?: string }>("/admin/backup/create", { method: "POST" });
      setStatus(`Backup erstellt: ${result.filename || "-"}`);
      await loadList();
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Backup konnte nicht erstellt werden.");
    } finally {
      setWorkingAction("");
    }
  };

  const downloadByFilename = async (filename: string) => {
    if (!filename) return;
    setStatus(`Lade ${filename}...`);
    try {
      await startDownload(`/admin/backup/download/${encodeURIComponent(filename)}`, filename);
      setStatus(`Backup heruntergeladen: ${filename}`);
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Backup-Datei konnte nicht heruntergeladen werden.");
    }
  };

  const validateRestoreFile = (file: File) => {
    const allowed = dbEngine === "mariadb" ? [".mariadb.json", ".json"] : [".db", ".sqlite", ".sqlite3"];
    const lower = file.name.toLowerCase();
    if (!allowed.some((suffix) => lower.endsWith(suffix))) {
      throw new Error(
        dbEngine === "mariadb"
          ? "Nur Backup-Dateien mit .mariadb.json/.json sind erlaubt."
          : "Nur Backup-Dateien mit .db/.sqlite/.sqlite3 sind erlaubt.",
      );
    }
    const maxBytes = Math.max(1, Number(maxRestoreSizeMb || 20)) * 1024 * 1024;
    if (Number(file.size || 0) > maxBytes) {
      throw new Error(`Backup-Datei ist zu gross (max. ${maxRestoreSizeMb} MB).`);
    }
  };

  const restoreBackup = async () => {
    if (!restoreFile) {
      setStatus("Bitte eine Backup-Datei auswaehlen.");
      return;
    }
    try {
      validateRestoreFile(restoreFile);
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Datei ungueltig.");
      return;
    }
    if (!window.confirm("Backup wirklich wiederherstellen? Danach bitte neu anmelden.")) return;
    setWorkingAction("restore");
    setStatus("Stelle Backup wieder her...");
    try {
      const formData = new FormData();
      formData.append("file", restoreFile, restoreFile.name);
      const token = window.localStorage.getItem("ndhub_token") || "";
      const response = await fetch("/admin/backup/restore", {
        method: "POST",
        body: formData,
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const result = (await response.json()) as { message?: string };
      setStatus(result.message || "Backup wiederhergestellt. Bitte neu anmelden.");
      window.localStorage.removeItem("ndhub_token");
      window.location.hash = "#login-section";
      window.location.reload();
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Backup konnte nicht wiederhergestellt werden.");
    } finally {
      setWorkingAction("");
    }
  };

  return (
    <div className="nd-react-shell">
      <div className="nd-react-heading">
        <p className="nd-react-eyebrow">Backup und Restore</p>
        <p className="muted">Engine: {dbEngine.toUpperCase()} | Restore-Limit: {maxRestoreSizeMb} MB</p>
      </div>
      <div className="toolbar">
        <div className="actions">
          <button type="button" onClick={() => void downloadLatest()} disabled={workingAction !== ""}>
            {workingAction === "download" ? "Laedt..." : "Backup herunterladen"}
          </button>
          <button type="button" onClick={() => void createBackup()} disabled={workingAction !== ""}>
            {workingAction === "create" ? "Erstellt..." : "Backup erstellen"}
          </button>
          <button type="button" onClick={() => void loadList()} disabled={workingAction !== ""}>
            {workingAction === "reload" ? "Laedt..." : "Backup-Liste aktualisieren"}
          </button>
        </div>
      </div>
      <div className="table-shell table-scroll">
        <table>
          <thead>
            <tr>
              <th>Datei</th>
              <th>Erstellt</th>
              <th>Groesse</th>
              <th>Aktion</th>
            </tr>
          </thead>
          <tbody>
            {!loading && rows.length ? (
              rows.map((row, idx) => (
                <tr key={`backup-${idx}-${row.filename || ""}`}>
                  <td>{row.filename || ""}</td>
                  <td>{row.created_at || ""}</td>
                  <td>{formatBytes(Number(row.size_bytes || 0))}</td>
                  <td>
                    <button type="button" onClick={() => void downloadByFilename(String(row.filename || ""))}>
                      Download
                    </button>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={4} className="empty-cell">
                  {loading ? "Lade Backups..." : "Noch keine Backups vorhanden."}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <form
        className="grid"
        onSubmit={(event) => {
          event.preventDefault();
          void restoreBackup();
        }}
      >
        <label>
          Backup-Datei
          <input
            type="file"
            accept=".db,.sqlite,.sqlite3,.mariadb.json,.json"
            onChange={(event) => setRestoreFile(event.target.files?.[0] || null)}
          />
        </label>
        <div className="actions">
          <button type="submit" disabled={workingAction !== "" || !restoreFile}>
            {workingAction === "restore" ? "Stellt wieder her..." : "Backup wiederherstellen"}
          </button>
        </div>
      </form>
      <p className={statusClass(classifyStatus(status))}>{status}</p>
    </div>
  );
}

