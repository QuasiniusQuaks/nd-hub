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

export function ImportManagerIsland() {
  const [activeTab, setActiveTab] = useState<"upload" | "errors">("upload");
  const [file, setFile] = useState<File | null>(null);
  const [dryRun, setDryRun] = useState<boolean>(false);
  const [status, setStatus] = useState<string>("");
  const [loadingPreview, setLoadingPreview] = useState<boolean>(false);
  const [loadingExecute, setLoadingExecute] = useState<boolean>(false);
  const [loadingTemplate, setLoadingTemplate] = useState<boolean>(false);
  const [previewRows, setPreviewRows] = useState<Array<Record<string, string | number | null>>>([]);
  const [errors, setErrors] = useState<string[]>([]);
  const [validRows, setValidRows] = useState<number>(0);
  const [totalRows, setTotalRows] = useState<number>(0);

  const canExecute = !loadingExecute && !loadingPreview && validRows > 0 && file !== null;
  const previewColumns = previewRows.length ? Object.keys(previewRows[0]) : [];

  const runPreview = async (): Promise<ImportPreviewResponse | null> => {
    if (!file) {
      setStatus("Bitte zuerst eine Datei auswaehlen.");
      return null;
    }
    setLoadingPreview(true);
    setStatus("Lade Import-Vorschau...");
    try {
      const formData = new FormData();
      formData.append("file", file, file.name);
      const data = await apiFetch<ImportPreviewResponse>("/imports/bewegungen/preview", {
        method: "POST",
        body: formData,
      });
      const nextRows = Array.isArray(data.preview_rows) ? data.preview_rows : [];
      const nextErrors = Array.isArray(data.errors) ? data.errors : [];
      setPreviewRows(nextRows);
      setErrors(nextErrors);
      setValidRows(Number(data.valid_rows || 0));
      setTotalRows(Number(data.total_rows || 0));
      if (nextErrors.length > 0) {
        setActiveTab("errors");
        setStatus(`Vorschau geladen: ${nextRows.length} Zeilen, ${nextErrors.length} Fehler.`);
      } else {
        setActiveTab("upload");
        setStatus(`Vorschau ohne Fehler geladen: ${nextRows.length} Zeilen.`);
      }
      return data;
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Import-Vorschau fehlgeschlagen.");
      return null;
    } finally {
      setLoadingPreview(false);
    }
  };

  const runExecute = async () => {
    if (!file) {
      setStatus("Bitte zuerst eine Datei auswaehlen.");
      return;
    }
    setLoadingExecute(true);
    setStatus("Import laeuft...");
    try {
      if (previewRows.length === 0 && errors.length === 0) {
        await runPreview();
      }
      const formData = new FormData();
      formData.append("file", file, file.name);
      formData.append("dry_run", dryRun ? "true" : "false");
      const result = await apiFetch<ImportExecuteResponse>("/imports/bewegungen/execute", {
        method: "POST",
        body: formData,
      });
      const resultErrors = Array.isArray(result.errors) ? result.errors : [];
      setErrors(resultErrors);
      if (resultErrors.length > 0) setActiveTab("errors");
      const message = result.dry_run
        ? `Dry-Run abgeschlossen: ${Number(result.would_imported || 0)} Bewegungen wuerden importiert, ${Number(result.error_count || 0)} Fehler.`
        : result.already_applied
          ? `Import bereits ausgefuehrt: ${Number(result.imported || 0)} Bewegungen, ${Number(result.error_count || 0)} Fehler.`
          : `${Number(result.imported || 0)} Bewegungen importiert, ${Number(result.error_count || 0)} Fehler.`;
      setStatus(message);
      if (!result.dry_run && Number(result.error_count || 0) === 0) {
        setFile(null);
        setPreviewRows([]);
        setValidRows(0);
        setTotalRows(0);
      }
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Import fehlgeschlagen.");
    } finally {
      setLoadingExecute(false);
    }
  };

  const downloadTemplate = async () => {
    setLoadingTemplate(true);
    setStatus("Lade Excel-Vorlage...");
    try {
      const token = window.localStorage.getItem("ndhub_token") || "";
      const response = await fetch("/imports/bewegungen/template", {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const blob = await response.blob();
      const disposition = response.headers.get("Content-Disposition") || "";
      const filenameMatch = disposition.match(/filename="?([^"]+)"?/i);
      const filename = filenameMatch?.[1] || "bewegungen_template.xlsx";
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 10000);
      setStatus("Vorlage heruntergeladen.");
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Vorlage konnte nicht geladen werden.");
    } finally {
      setLoadingTemplate(false);
    }
  };

  return (
    <div className="nd-react-shell">
      <div className="nd-react-heading">
        <p className="nd-react-eyebrow">Importmanager</p>
        <div className="nd-react-quick-actions">
          <button type="button" className="btn-secondary" onClick={() => setActiveTab("upload")}>
            Upload
          </button>
          <button type="button" className="btn-secondary" onClick={() => setActiveTab("errors")}>
            Fehler
          </button>
        </div>
      </div>
      <div className="inline-tabs">
        <button type="button" className={tabClassName(activeTab === "upload")} onClick={() => setActiveTab("upload")}>
          Datei & Vorschau
        </button>
        <button type="button" className={tabClassName(activeTab === "errors")} onClick={() => setActiveTab("errors")}>
          Fehler
        </button>
      </div>
      {activeTab === "upload" ? (
        <div className="inline-tab-panel active">
          <p className="muted">Pflichtspalten: Depot, Praeparat, Typ, Charge, Verfall, Datum, Anzahl</p>
          <div className="nd-react-summary-grid">
            <article className="nd-react-summary-card">
              <span className="label">Datei</span>
              <span className="value">{file ? "1" : "0"}</span>
            </article>
            <article className="nd-react-summary-card">
              <span className="label">Gueltige Zeilen</span>
              <span className="value">{validRows}</span>
            </article>
            <article className="nd-react-summary-card">
              <span className="label">Fehler</span>
              <span className="value">{errors.length}</span>
            </article>
          </div>
          <div className="toolbar">
            <label>
              Datei
              <input
                type="file"
                accept=".csv,.xlsx,.xls"
                onChange={(event) => {
                  const selected = event.target.files?.[0] || null;
                  setFile(selected);
                  setPreviewRows([]);
                  setErrors([]);
                  setValidRows(0);
                  setTotalRows(0);
                  setStatus(selected ? `Datei gewaehlt: ${selected.name}` : "");
                }}
              />
            </label>
            <div className="actions">
              <button type="button" onClick={() => void runPreview()} disabled={loadingPreview || !file}>
                {loadingPreview ? "Laedt..." : "Vorschau laden"}
              </button>
              <button type="button" onClick={() => void runExecute()} disabled={!canExecute}>
                {loadingExecute ? "Laeuft..." : "Import starten"}
              </button>
              <button type="button" onClick={() => void downloadTemplate()} disabled={loadingTemplate}>
                {loadingTemplate ? "Laedt..." : "Excel-Vorlage"}
              </button>
            </div>
          </div>
          <label className="checkbox-row">
            <input type="checkbox" checked={dryRun} onChange={(event) => setDryRun(event.target.checked)} />
            Dry-Run (nur pruefen, nicht schreiben)
          </label>
          <p className={statusClass(classifyStatus(status))}>{status}</p>
          <p className="muted">Zeilen gesamt: {totalRows} | Gueltige Zeilen: {validRows}</p>
          <div className="table-shell table-scroll nd-react-table-compact">
            <table>
              <thead>
                <tr>
                  {previewColumns.length ? (
                    previewColumns.map((column) => <th key={column}>{column}</th>)
                  ) : (
                    <th>Vorschau</th>
                  )}
                </tr>
              </thead>
              <tbody>
                {previewRows.length ? (
                  previewRows.map((row, idx) => (
                    <tr key={`import-${idx}`}>
                      {previewColumns.map((column) => (
                        <td key={`${idx}-${column}`}>{String(row[column] ?? "")}</td>
                      ))}
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={Math.max(1, previewColumns.length)} className="empty-cell">
                      Keine Vorschauzeilen vorhanden.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="inline-tab-panel active">
          <h3>Importfehler</h3>
          <p className="muted">Hier sehen Sie Validierungsfehler aus Vorschau und Import.</p>
          {errors.length ? (
            <pre className="audit-details">{errors.join("\n")}</pre>
          ) : (
            <p className="muted">Keine Fehler vorhanden.</p>
          )}
        </div>
      )}
    </div>
  );
}

