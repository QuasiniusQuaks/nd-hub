import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import L from "leaflet";
import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";
import "./styles.css";
import "leaflet/dist/leaflet.css";

// Fix default Leaflet marker assets in Vite bundles.
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});

/**
 * OSM's public tile endpoint often returns "Access blocked" / 403 for app
 * traffic. Use CARTO basemaps (OSM data) which allow normal web app usage.
 */
const MAP_TILE_URL = "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png";
const MAP_TILE_ATTR =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>';

function addBaseTileLayer(map: L.Map): L.TileLayer {
  return L.tileLayer(MAP_TILE_URL, {
    maxZoom: 18,
    subdomains: "abcd",
    attribution: MAP_TILE_ATTR,
  }).addTo(map);
}

type DesktopToken = {
  token_fingerprint: string;
  token_masked: string;
  client_label?: string | null;
  username: string;
  role?: string | null;
  created_at: string;
  expires_at: string;
  status: string;
};

type UserRow = {
  id: number;
  username: string;
  role: string;
  email?: string | null;
  is_active: boolean;
  permissions: string[];
  failed_attempts: number;
  locked_until?: string | null;
  is_default_password?: boolean;
  last_login?: string | null;
};

type ReportRow = Record<string, string | number | null>;

type ReportResponse = {
  rows?: ReportRow[];
  kpis?: Record<string, unknown>;
};

type DashboardOverview = {
  kpis?: {
    depots?: number;
    praeparate?: number;
    bewegungen?: number;
    kritisch_verfallend?: number;
  };
  recent_activity?: Array<Record<string, string | number | null>>;
  expiry_preview?: Array<Record<string, string | number | null>>;
};

type VerfallOverviewResponse = {
  rows?: Array<Record<string, string | number | null>>;
  stats?: {
    kritisch?: number;
    warnung?: number;
    achtung?: number;
    gesamt_menge?: number;
  };
};

type AuditRow = {
  timestamp?: string;
  username?: string;
  action?: string;
  resource_type?: string;
  resource_id?: string | number;
  details?: string;
};

type ImportPreviewResponse = {
  preview_rows?: Array<Record<string, string | number | null>>;
  errors?: string[];
  error_count?: number;
  valid_rows?: number;
  total_rows?: number;
};

type ImportExecuteResponse = {
  dry_run?: boolean;
  already_applied?: boolean;
  would_imported?: number;
  imported?: number;
  error_count?: number;
  errors?: string[];
};

type BackupRow = {
  filename?: string;
  created_at?: string;
  size_bytes?: number;
};

type BackupListResponse = {
  rows?: BackupRow[];
  max_restore_size_mb?: number;
  db_engine?: string;
};

type DepotRow = {
  id: number;
  name: string;
};

type EmailRecipientPreviewRow = {
  id?: number;
  depot_id?: number;
  depot_name?: string;
  name?: string;
  rolle?: string;
  email?: string;
};

type EmailRecipientPreviewResponse = {
  count?: number;
  rows?: EmailRecipientPreviewRow[];
  recipients?: EmailRecipientPreviewRow[];
  depot_names?: string[];
  selected_contact_count?: number;
};

type EmailDeliveryStatus = {
  mode?: string;
  can_send_now?: boolean;
  from_address?: string;
};

type EmailDraftResult = {
  id?: number;
  recipient_count?: number;
  delivery_status?: string;
  sent_count?: number;
  delivery_error?: string;
};

type EmailHistoryRow = {
  id: number;
  datum?: string;
  betreff?: string;
  empfaenger_depots?: string;
  anzahl_empfaenger?: number;
  versand_status?: string;
  versand_kanal?: string;
};

type EmailHistoryDetail = {
  id?: number;
  datum?: string;
  betreff?: string;
  versand_status?: string;
  versand_kanal?: string;
  empfaenger_depots?: string;
  anzahl_empfaenger?: number;
  empfaenger_emails?: string;
  versand_fehler?: string;
  nachricht?: string;
};

function normalizeDepotRows(payload: unknown): DepotRow[] {
  if (Array.isArray(payload)) return payload as DepotRow[];
  if (payload && typeof payload === "object" && Array.isArray((payload as { rows?: unknown[] }).rows)) {
    return (payload as { rows: DepotRow[] }).rows;
  }
  return [];
}

type MasterDepot = {
  id: number;
  name?: string;
  adresse?: string | null;
  strasse?: string | null;
  hausnummer?: string | null;
  postleitzahl?: string | null;
  stadt?: string | null;
  telefon?: string | null;
  email?: string | null;
  institution_id?: number | null;
  institution_name?: string | null;
  latitude?: number | null;
  longitude?: number | null;
};

type MasterPraeparat = {
  id: number;
  name?: string;
  wirkstoff?: string | null;
  darreichungsform?: string | null;
  staerke?: string | null;
  einheit?: string | null;
  pzn?: string | null;
  hersteller?: string | null;
};

type AssignmentRow = {
  praeparat_id: number;
  praeparat_name?: string;
  assigned?: boolean;
  sollbestand?: number;
};

type ContactRow = {
  id: number;
  name?: string;
  rolle?: string | null;
  telefon?: string | null;
  email?: string | null;
};

type PermissionCatalogItem = {
  key: string;
  label?: string;
};

type PermissionTemplate = {
  key: string;
  label?: string;
  permissions?: string[];
};

type ActivityRow = {
  timestamp?: string;
  action?: string;
  details?: string;
};

type MeResponse = {
  username?: string;
  role?: string;
  avatar_available?: boolean;
  requires_password_change?: boolean;
};

type InstitutionMapRow = {
  institution_id: number;
  institution_name?: string;
  institution_adresse?: string;
  latitude?: number | null;
  longitude?: number | null;
  depots?: Array<{ id: number; name?: string; adresse?: string; latitude?: number | null; longitude?: number | null }>;
};

function escapePopupHtml(value: string): string {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

type InstitutionRow = {
  id: number;
  name: string;
  adresse?: string | null;
  strasse?: string | null;
  hausnummer?: string | null;
  postleitzahl?: string | null;
  stadt?: string | null;
  latitude?: number | null;
  longitude?: number | null;
};

type DepotPermissionRow = {
  depot_id: number;
  depot_name?: string;
  can_read?: boolean | number;
  can_write?: boolean | number;
};

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const token = window.localStorage.getItem("ndhub_token") || "";
  const headers = new Headers(options?.headers || {});
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(path, { ...options, headers });
  if (!response.ok) {
    let message = `HTTP ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body?.detail) message = body.detail;
    } catch {
      // ignore
    }
    throw new Error(message);
  }
  return (await response.json()) as T;
}

function hasAuthToken(): boolean {
  return Boolean(window.localStorage.getItem("ndhub_token"));
}

/**
 * Islands mount at page load (often before login). Re-run `load` on shell
 * `ndhub-session-ready` so menus/data work after login or password-gate unlock.
 */
function useSessionReload(load: () => void | Promise<void>, options?: { requireToken?: boolean }): void {
  const requireToken = options?.requireToken !== false;
  useEffect(() => {
    const run = () => {
      if (requireToken && !hasAuthToken()) return;
      void load();
    };
    run();
    window.addEventListener("ndhub-session-ready", run);
    return () => window.removeEventListener("ndhub-session-ready", run);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- intentional mount + session bridge
  }, []);
}

function formatDateTime(value: string): string {
  if (!value) return "-";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}

function formatBytes(sizeBytes: number): string {
  const value = Number(sizeBytes || 0);
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(2)} MB`;
}

function tabClassName(active: boolean): string {
  return active ? "inline-tab active" : "inline-tab";
}

type StatusTone = "default" | "success" | "warning" | "error" | "info";

function statusClass(tone: StatusTone): string {
  if (tone === "default") return "status";
  return `status ${tone}`;
}

function composeAddressParts(
  strasse?: string | null,
  hausnummer?: string | null,
  postleitzahl?: string | null,
  stadt?: string | null,
): string {
  const streetBlock = [String(strasse || "").trim(), String(hausnummer || "").trim()].filter(Boolean).join(" ");
  const cityBlock = [String(postleitzahl || "").trim(), String(stadt || "").trim()].filter(Boolean).join(" ");
  return [streetBlock, cityBlock].filter(Boolean).join(", ");
}

function classifyStatus(message: string): StatusTone {
  const normalized = String(message || "").toLowerCase();
  if (!normalized.trim()) return "default";
  if (
    normalized.includes("fehl") ||
    normalized.includes("error") ||
    normalized.includes("ungueltig") ||
    normalized.includes("konnte nicht")
  ) {
    return "error";
  }
  if (normalized.includes("warn") || normalized.includes("achtung")) return "warning";
  if (normalized.includes("geladen") || normalized.includes("aktualisiert") || normalized.includes("hinweis")) return "info";
  if (
    normalized.includes("gespeichert") ||
    normalized.includes("erstellt") ||
    normalized.includes("abgeschlossen") ||
    normalized.includes("importiert")
  ) {
    return "success";
  }
  return "default";
}

function readReportFilters(): { perspective: string; typ: string; ids: number[]; startDate: string; endDate: string } {
  const perspective = (document.getElementById("report-perspective") as HTMLSelectElement | null)?.value || "depot";
  const typ = (document.getElementById("report-type") as HTMLSelectElement | null)?.value || "bewegungen";
  const idsSelect = document.getElementById("report-ids") as HTMLSelectElement | null;
  const startDate = (document.getElementById("report-start-date") as HTMLInputElement | null)?.value || "";
  const endDate = (document.getElementById("report-end-date") as HTMLInputElement | null)?.value || "";
  const ids: number[] = [];
  if (idsSelect) {
    for (const option of idsSelect.options) {
      if (!option.selected) continue;
      const parsed = Number(option.value);
      if (Number.isFinite(parsed) && parsed > 0) ids.push(parsed);
    }
  }
  return { perspective, typ, ids, startDate, endDate };
}

function readMultiSelectIds(selectId: string): number[] {
  const select = document.getElementById(selectId) as HTMLSelectElement | null;
  if (!select) return [];
  const ids: number[] = [];
  for (const option of select.options) {
    if (!option.selected) continue;
    const parsed = Number(option.value);
    if (Number.isFinite(parsed) && parsed > 0) ids.push(parsed);
  }
  return ids;
}

const BEWEGUNG_AUTOFILL_ENABLED_KEY = "ndhub_bewegung_autofill_enabled";
const BEWEGUNG_LAST_INPUT_KEY = "ndhub_bewegung_last_input";

function passwordPolicyHint(value: string): string {
  const password = String(value || "");
  if (!password) return "Passwort ist erforderlich.";
  if (password.length < 8) return "Passwort muss mindestens 8 Zeichen lang sein.";
  if (!/[A-Z]/.test(password)) return "Passwort muss mindestens einen Grossbuchstaben enthalten.";
  if (!/[a-z]/.test(password)) return "Passwort muss mindestens einen Kleinbuchstaben enthalten.";
  if (!/[0-9]/.test(password)) return "Passwort muss mindestens eine Zahl enthalten.";
  return "";
}

async function copyToClipboard(text: string): Promise<void> {
  const value = String(text || "").trim();
  if (!value) throw new Error("Nichts zum Kopieren vorhanden.");
  if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
    await navigator.clipboard.writeText(value);
    return;
  }
  const fallback = document.createElement("textarea");
  fallback.value = value;
  fallback.setAttribute("readonly", "readonly");
  fallback.style.position = "absolute";
  fallback.style.left = "-9999px";
  document.body.appendChild(fallback);
  fallback.select();
  const ok = document.execCommand("copy");
  fallback.remove();
  if (!ok) throw new Error("Kopieren nicht verfuegbar.");
}

function DesktopSyncArchiveIsland() {
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

function UsersTableIsland() {
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

function ReportTableIsland() {
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

function DashboardOverviewIsland() {
  const [data, setData] = useState<DashboardOverview>({});
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>("");
  const [mapRows, setMapRows] = useState<InstitutionMapRow[]>([]);
  const [mapError, setMapError] = useState<string>("");
  const dashboardMapRef = useRef<L.Map | null>(null);
  const dashboardMarkerLayerRef = useRef<L.LayerGroup | null>(null);

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const payload = await apiFetch<DashboardOverview>("/dashboard/overview");
      setData(payload || {});
    } catch (err) {
      setError(err instanceof Error ? err.message : "Dashboard konnte nicht geladen werden.");
    } finally {
      setLoading(false);
    }
  };

  useSessionReload(load);

  useEffect(() => {
    const refreshButton = document.getElementById("dashboard-refresh");
    if (!(refreshButton instanceof HTMLButtonElement)) return;
    const listener = () => {
      void load();
    };
    refreshButton.addEventListener("click", listener);
    return () => refreshButton.removeEventListener("click", listener);
  }, []);

  useEffect(() => {
    let disposed = false;
    let resizeObserver: ResizeObserver | null = null;
    const mapNode = document.getElementById("institutions-map-dashboard");
    if (!mapNode) return;
    const scheduleInvalidate = () => {
      if (!dashboardMapRef.current) return;
      window.setTimeout(() => dashboardMapRef.current?.invalidateSize(), 0);
      window.setTimeout(() => dashboardMapRef.current?.invalidateSize(), 120);
      window.setTimeout(() => dashboardMapRef.current?.invalidateSize(), 320);
    };

    const loadMapData = async () => {
      if (!hasAuthToken()) return;
      try {
        const payload = await apiFetch<InstitutionMapRow[]>("/map/institutions");
        if (disposed) return;
        setMapRows(Array.isArray(payload) ? payload : []);
        setMapError("");
        if (!dashboardMapRef.current) {
          const germanyBounds = L.latLngBounds(
            [47.2, 5.5],
            [55.2, 15.6],
          );
          dashboardMapRef.current = L.map(mapNode, {
            minZoom: 5,
            maxZoom: 12,
            maxBounds: germanyBounds,
            maxBoundsViscosity: 1.0,
          }).setView([51.1657, 10.4515], 6);
          addBaseTileLayer(dashboardMapRef.current);
          dashboardMarkerLayerRef.current = L.layerGroup().addTo(dashboardMapRef.current);
        }
        dashboardMapRef.current.setView([51.1657, 10.4515], 6);
        scheduleInvalidate();
        if (typeof ResizeObserver !== "undefined") {
          resizeObserver = new ResizeObserver(() => {
            scheduleInvalidate();
          });
          resizeObserver.observe(mapNode);
        }
      } catch (err) {
        if (disposed) return;
        setMapError(err instanceof Error ? err.message : "Deutschlandkarte konnte nicht geladen werden.");
      }
    };

    void loadMapData();
    const onSessionReady = () => {
      void loadMapData();
    };
    window.addEventListener("ndhub-session-ready", onSessionReady);
    window.addEventListener("resize", scheduleInvalidate);
    window.addEventListener("ndhub-page-change", scheduleInvalidate as EventListener);
    return () => {
      disposed = true;
      window.removeEventListener("ndhub-session-ready", onSessionReady);
      window.removeEventListener("resize", scheduleInvalidate);
      window.removeEventListener("ndhub-page-change", scheduleInvalidate as EventListener);
      resizeObserver?.disconnect();
      dashboardMapRef.current?.remove();
      dashboardMapRef.current = null;
      dashboardMarkerLayerRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = dashboardMapRef.current;
    const layer = dashboardMarkerLayerRef.current;
    if (!map || !layer) return;
    layer.clearLayers();

    mapRows.forEach((institution) => {
      (institution.depots || []).forEach((depot) => {
        const latitude = Number(depot.latitude ?? institution.latitude);
        const longitude = Number(depot.longitude ?? institution.longitude);
        if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return;
        const depotName = depot.name || `Depot ${depot.id}`;
        const institutionName = institution.institution_name || `Institution ${institution.institution_id}`;
        const marker = L.marker([latitude, longitude], { title: `${depotName} (${institutionName})` }).addTo(layer);
        marker.bindTooltip(`Depot: ${depotName}<br/>Institution: ${institutionName}`);
      });
    });
    map.setView([51.1657, 10.4515], 6);
    window.setTimeout(() => map.invalidateSize(), 0);
  }, [mapRows]);

  const kpis = data.kpis || {};
  const recentRows = Array.isArray(data.recent_activity) ? data.recent_activity : [];
  const expiryRows = Array.isArray(data.expiry_preview) ? data.expiry_preview : [];
  const criticalCount = Number(kpis.kritisch_verfallend ?? 0);

  return (
    <div className="nd-react-shell">
      <div className="nd-react-heading">
        <p className="nd-react-eyebrow">Live Dashboard</p>
        <div className="nd-react-toolbar">
          <button type="button" className="btn-secondary" onClick={() => (window.location.hash = "#bewegung-create-section")}>
            Bewegung erfassen
          </button>
          <button type="button" className="btn-secondary" onClick={() => (window.location.hash = "#verfall-manager-section")}>
            Verfall pruefen
          </button>
          <button type="button" className="btn-primary" onClick={() => void load()} disabled={loading}>
            {loading ? "Laedt..." : "Aktualisieren"}
          </button>
        </div>
      </div>
      {error ? <p className="status error">{error}</p> : null}
      <section className="nd-react-hero">
        <div>
          <h3>Betriebsstatus auf einen Blick</h3>
          <p className="muted">
            Kritische Positionen, Bestandsbewegungen und letzte Aktivitaeten werden in Echtzeit zusammengefasst.
          </p>
          <p className={statusClass(criticalCount > 0 ? "warning" : "success")}>
            {criticalCount > 0
              ? `${criticalCount} Positionen sind kritisch verfallend.`
              : "Keine kritischen Verfallspositionen aktuell."}
          </p>
        </div>
        <div className="nd-react-hero-metrics">
          <article className="nd-react-metric">
            <span className="nd-react-metric-label">Depots</span>
            <span className="nd-react-metric-value">{String(kpis.depots ?? 0)}</span>
          </article>
          <article className="nd-react-metric">
            <span className="nd-react-metric-label">Praeparate</span>
            <span className="nd-react-metric-value">{String(kpis.praeparate ?? 0)}</span>
          </article>
          <article className="nd-react-metric">
            <span className="nd-react-metric-label">Bewegungen</span>
            <span className="nd-react-metric-value">{String(kpis.bewegungen ?? 0)}</span>
          </article>
          <article className="nd-react-metric">
            <span className="nd-react-metric-label">Kritisch</span>
            <span className="nd-react-metric-value">{String(criticalCount)}</span>
          </article>
        </div>
      </section>
      <section className="nd-react-panel">
        <div className="nd-react-heading" style={{ marginBottom: 14 }}>
          <h3>Deutschlandkarte</h3>
          <div className="nd-react-toolbar">
            <button
              type="button"
              className="btn-secondary"
              onClick={() => (window.location.hash = "#institutions-map-section")}
            >
              Zur detaillierten Deutschlandkarte
            </button>
          </div>
        </div>
        {mapError ? <p className={statusClass("error")}>{mapError}</p> : null}
        <div
          id="institutions-map-dashboard"
          style={{ height: 420, width: "100%", borderRadius: 12, cursor: "pointer" }}
          onClick={() => (window.location.hash = "#institutions-map-section")}
          title="Zur detaillierten Deutschlandkarte wechseln"
        />
        <p className="muted">Alle Notfalldepots mit Institutionszuordnung auf der Karte. Klicken oeffnet die Detailkarte.</p>
      </section>
      <div className="nd-react-grid-two">
        <section className="nd-react-panel">
          <h3>Naechste Verfaelle</h3>
          <div className="table-shell table-scroll nd-react-table-compact">
            <table>
              <thead>
                <tr>
                  <th>Depot</th>
                  <th>Praeparat</th>
                  <th>Verfall</th>
                  <th>Tage bis Verfall</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {expiryRows.length ? (
                  expiryRows.map((row, idx) => (
                    <tr key={`exp-${idx}`}>
                      <td>{String(row.depot ?? "-")}</td>
                      <td>{String(row.praeparat ?? "-")}</td>
                      <td>{String(row.verfall ?? "-")}</td>
                      <td>{String(row.tage_bis_verfall ?? "-")}</td>
                      <td>{String(row.kategorie ?? "-")}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={5} className="empty-cell">
                      Keine Verfallspositionen vorhanden.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
        <section className="nd-react-panel">
          <h3>Letzte Aktivitaeten</h3>
          <div className="table-shell table-scroll nd-react-table-compact">
            <table>
              <thead>
                <tr>
                  <th>Datum</th>
                  <th>Typ</th>
                  <th>Depot</th>
                  <th>Praeparat</th>
                  <th>Anzahl</th>
                </tr>
              </thead>
              <tbody>
                {recentRows.length ? (
                  recentRows.map((row, idx) => (
                    <tr key={`act-${idx}`}>
                      <td>{String(row.datum ?? "-")}</td>
                      <td>{String(row.typ ?? "-")}</td>
                      <td>{String(row.depot ?? "-")}</td>
                      <td>{String(row.praeparat ?? "-")}</td>
                      <td>{String(row.anzahl ?? "-")}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={5} className="empty-cell">
                      Noch keine Aktivitaeten vorhanden.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  );
}

function AdminWorkspaceIsland() {
  const sections = [
    { id: "admin-masterdata", label: "Depots & Praeparate" },
    { id: "admin-assignments", label: "Zuordnungen" },
    { id: "admin-institutions-rights", label: "Institutionen & Rechte" },
    { id: "admin-contacts", label: "Kontakte" },
  ];
  const [activeSection, setActiveSection] = useState<string>(sections[0].id);

  return (
    <div className="nd-react-shell nd-admin-workspace">
      <div className="nd-react-heading">
        <div>
          <p className="nd-react-eyebrow">Verwaltung</p>
          <h3>Stammdaten-Workspace</h3>
          <p className="muted">Alle Stammdaten-, Zuordnungs-, Institutions-/Rechte- und Kontaktfunktionen auf einer Seite.</p>
        </div>
      </div>
      <div className="inline-tabs">
          {sections.map((section) => (
            <button
              key={section.id}
              type="button"
              className={tabClassName(activeSection === section.id)}
              onClick={() => setActiveSection(section.id)}
            >
              {section.label}
            </button>
          ))}
      </div>
      {activeSection === "admin-masterdata" ? (
        <div className="inline-tab-panel active">
            <MasterdataManagerIsland />
        </div>
      ) : null}
      {activeSection === "admin-assignments" ? (
        <div className="inline-tab-panel active">
            <AssignmentManagerIsland />
        </div>
      ) : null}
      {activeSection === "admin-institutions-rights" ? (
        <div className="inline-tab-panel active">
            <InstitutionsAdminIsland />
        </div>
      ) : null}
      {activeSection === "admin-contacts" ? (
        <div className="inline-tab-panel active">
            <ContactsManagerIsland />
        </div>
      ) : null}
    </div>
  );
}

function InstitutionsMapIsland() {
  const [rows, setRows] = useState<InstitutionMapRow[]>([]);
  const [error, setError] = useState<string>("");
  const [query, setQuery] = useState<string>("");
  const [institutionId, setInstitutionId] = useState<string>("");
  const mapRef = useRef<L.Map | null>(null);
  const markerLayerRef = useRef<L.LayerGroup | null>(null);
  const germanyBounds = useMemo(
    () =>
      L.latLngBounds(
        [47.2, 5.5],
        [55.2, 15.6],
      ),
    [],
  );

  useEffect(() => {
    let disposed = false;
    let resizeObserver: ResizeObserver | null = null;
    const mapNode = document.getElementById("institutions-map");
    const hostNode = document.getElementById("institutions-map-section");
    const scheduleInvalidate = () => {
      if (!mapRef.current) return;
      window.setTimeout(() => mapRef.current?.invalidateSize(), 0);
      window.setTimeout(() => mapRef.current?.invalidateSize(), 120);
      window.setTimeout(() => mapRef.current?.invalidateSize(), 320);
    };
    const ensureMapLayout = () => {
      if (!mapRef.current) return;
      if (hostNode?.classList.contains("active-page")) {
        scheduleInvalidate();
      }
    };
    const load = async () => {
      try {
        const payload = await apiFetch<InstitutionMapRow[]>("/map/institutions");
        if (disposed) return;
        const nextRows = Array.isArray(payload) ? payload : [];
        setRows(nextRows);
        setError("");
        const node = document.getElementById("institutions-map");
        if (!node) return;
        if (!mapRef.current) {
          mapRef.current = L.map(node, {
            minZoom: 5,
            maxZoom: 12,
            maxBounds: germanyBounds,
            maxBoundsViscosity: 1.0,
          }).setView([51.1657, 10.4515], 6);
          addBaseTileLayer(mapRef.current);
          markerLayerRef.current = L.layerGroup().addTo(mapRef.current);
          mapRef.current.fitBounds(germanyBounds, { maxZoom: 6 });
        }
        ensureMapLayout();
        if (typeof ResizeObserver !== "undefined" && mapNode) {
          resizeObserver = new ResizeObserver(() => {
            ensureMapLayout();
          });
          resizeObserver.observe(mapNode);
          if (hostNode) {
            resizeObserver.observe(hostNode);
          }
        }
      } catch (err) {
        if (disposed) return;
        setError(err instanceof Error ? err.message : "Karte konnte nicht geladen werden.");
      }
    };
    void load();
    window.addEventListener("hashchange", ensureMapLayout);
    window.addEventListener("ndhub-page-change", ensureMapLayout as EventListener);
    return () => {
      disposed = true;
      window.removeEventListener("hashchange", ensureMapLayout);
      window.removeEventListener("ndhub-page-change", ensureMapLayout as EventListener);
      resizeObserver?.disconnect();
      mapRef.current?.remove();
      mapRef.current = null;
      markerLayerRef.current = null;
    };
  }, [germanyBounds]);

  const filteredRows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return rows.filter((item) => {
      if (institutionId && String(item.institution_id) !== institutionId) return false;
      if (!q) return true;
      const inInstitution = String(item.institution_name || "").toLowerCase().includes(q);
      const inDepot = (item.depots || []).some((depot) => String(depot.name || "").toLowerCase().includes(q));
      return inInstitution || inDepot;
    });
  }, [rows, query, institutionId]);

  const filteredDepots = useMemo(() => {
    return filteredRows.flatMap((item) =>
      (item.depots || []).map((depot) => ({
        institutionId: item.institution_id,
        institutionName: item.institution_name || `Institution ${item.institution_id}`,
        institutionAddress: item.institution_adresse || "",
        latitude: Number(depot.latitude ?? item.latitude),
        longitude: Number(depot.longitude ?? item.longitude),
        depotId: depot.id,
        depotName: depot.name || `Depot ${depot.id}`,
        depotAddress: depot.adresse || "Keine Adresse hinterlegt",
      })),
    );
  }, [filteredRows]);

  useEffect(() => {
    const map = mapRef.current;
    const layer = markerLayerRef.current;
    if (!map || !layer) return;
    layer.clearLayers();
    const bounds = L.latLngBounds([]);
    const markerIndexByInstitution = new Map<number, number>();
    filteredDepots.forEach((entry) => {
      if (!Number.isFinite(entry.latitude) || !Number.isFinite(entry.longitude)) return;
      const index = markerIndexByInstitution.get(entry.institutionId) || 0;
      markerIndexByInstitution.set(entry.institutionId, index + 1);
      const radius = index === 0 ? 0 : 0.015 * (1 + Math.floor(index / 8));
      const angle = (index * 45 * Math.PI) / 180;
      const lat = entry.latitude + Math.sin(angle) * radius;
      const lng = entry.longitude + Math.cos(angle) * radius;
      const marker = L.marker([lat, lng], {
        title: `${entry.depotName} (${entry.institutionName})`,
      }).addTo(layer);
      marker.bindTooltip(`Depot: ${entry.depotName}<br/>Institution: ${entry.institutionName}`);
      marker.bindPopup(
        `<strong>${escapePopupHtml(entry.depotName)}</strong><br/>
        <span>${escapePopupHtml(entry.depotAddress)}</span><br/><br/>
        <span><strong>Institution:</strong> ${escapePopupHtml(entry.institutionName)}</span><br/>
        <span>${escapePopupHtml(entry.institutionAddress)}</span><br/><br/>
        <button type="button" class="nd-map-open-stock" data-depot-id="${entry.depotId}" style="margin-top:6px;">
          Aktuelle Bestaende anzeigen
        </button>
        <div class="nd-map-stock-preview" data-depot-id="${entry.depotId}" style="margin-top:8px; font-size:12px; color:#4b5563;">
          Lade aktuellen Bestand...
        </div>`,
      );
      marker.on("popupopen", (event: L.PopupEvent) => {
        const popupElement = event.popup.getElement();
        const stockPreview = popupElement?.querySelector(".nd-map-stock-preview");
        if (stockPreview instanceof HTMLElement) {
          void (async () => {
            try {
              const payload = await apiFetch<ReportResponse>(
                `/reports/bestand?perspective=depot&ids=${encodeURIComponent(String(entry.depotId))}`,
              );
              const rows = Array.isArray(payload?.rows) ? payload.rows : [];
              const kpis = payload?.kpis && typeof payload.kpis === "object" ? payload.kpis : {};
              const gesamtbestand = Number(kpis.gesamtbestand ?? 0);
              const kritischeLuecken = Number(kpis.kritische_luecken ?? 0);
              const bestandsquote = Number(kpis.bestandsquote ?? 0);
              const deviationRows = rows
                .map((row) => ({
                  praeparat: String(row.praeparat ?? "-"),
                  ist: Number(row.ist_bestand ?? 0),
                  soll: Number(row.sollbestand ?? 0),
                  diff: Number(row.differenz ?? 0),
                }))
                .filter((row) => row.diff !== 0)
                .sort((a, b) => Math.abs(b.diff) - Math.abs(a.diff))
                .slice(0, 8);
              const sample = deviationRows
                .map((row) => {
                  const signedDiff = row.diff > 0 ? `+${row.diff}` : `${row.diff}`;
                  return `${escapePopupHtml(row.praeparat)}: Ist ${row.ist} / Soll ${row.soll} (Delta ${signedDiff})`;
                })
                .join("<br/>");
              stockPreview.innerHTML = `
                <strong>Aktueller Bestand</strong><br/>
                Gesamt: ${gesamtbestand} | Quote: ${bestandsquote.toFixed(2)}% | Luecken: ${kritischeLuecken}
                ${
                  sample
                    ? `<br/><strong>Abweichungen vom Soll:</strong><br/><span>${sample}</span>`
                    : "<br/><span>Keine Soll-Ist-Abweichungen bei den Praeparaten.</span>"
                }
              `;
            } catch (err) {
              const message = err instanceof Error ? err.message : "Bestand konnte nicht geladen werden.";
              stockPreview.textContent = message;
            }
          })();
        }
        const link = popupElement?.querySelector(".nd-map-open-stock");
        if (!(link instanceof HTMLButtonElement)) return;
        const handleClick = (clickEvent: Event) => {
          clickEvent.preventDefault();
          clickEvent.stopPropagation();
          const depotId = Number(link.dataset.depotId || "0");
          if (!Number.isFinite(depotId) || depotId <= 0) return;
          window.location.hash = "#reports-section";
          window.dispatchEvent(new CustomEvent("ndhub-open-depot-stock-report", { detail: { depotId } }));
        };
        link.addEventListener("click", handleClick, { once: true });
      });
      bounds.extend([lat, lng]);
    });
    if (query.trim() || institutionId) {
      if (bounds.isValid()) {
        map.fitBounds(bounds.pad(0.2), { maxZoom: 11 });
      }
    } else {
      map.fitBounds(germanyBounds, { maxZoom: 6 });
    }
    window.setTimeout(() => map.invalidateSize(), 0);
  }, [filteredDepots, germanyBounds, institutionId, query]);

  return (
    <div className="nd-react-shell">
      <div className="nd-react-heading">
        <p className="nd-react-eyebrow">Deutschlandkarte</p>
      </div>
      {error ? <p className={statusClass("error")}>{error}</p> : null}
      <div className="nd-react-toolbar">
        <input
          type="text"
          placeholder="Institution oder Depot suchen"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <select value={institutionId} onChange={(event) => setInstitutionId(event.target.value)}>
          <option value="">Alle Institutionen</option>
          {rows.map((item) => (
            <option key={item.institution_id} value={String(item.institution_id)}>
              {item.institution_name || `Institution ${item.institution_id}`}
            </option>
          ))}
        </select>
      </div>
      <div id="institutions-map" style={{ height: 420, width: "100%", borderRadius: 12 }} />
      <p className="muted">Angezeigt werden Notfalldepots; die zugeordnete Institution steht direkt am Marker.</p>
      <div className="table-shell">
        <table>
          <thead>
            <tr>
              <th>Notfalldepot</th>
              <th>Adresse</th>
              <th>Institution</th>
            </tr>
          </thead>
          <tbody>
            {filteredDepots.map((row) => (
              <tr key={row.depotId}>
                <td>{row.depotName}</td>
                <td>{row.depotAddress}</td>
                <td>{row.institutionName}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function InstitutionsAdminIsland() {
  const [institutions, setInstitutions] = useState<InstitutionRow[]>([]);
  const [depots, setDepots] = useState<MasterDepot[]>([]);
  const [users, setUsers] = useState<UserRow[]>([]);
  const [selectedUsername, setSelectedUsername] = useState<string>("");
  const [selectedDepotId, setSelectedDepotId] = useState<number>(0);
  const [selectedInstitutionId, setSelectedInstitutionId] = useState<number>(0);
  const [editingInstitutionId, setEditingInstitutionId] = useState<number>(0);
  const [institutionName, setInstitutionName] = useState<string>("");
  const [institutionStreet, setInstitutionStreet] = useState<string>("");
  const [institutionHouseNumber, setInstitutionHouseNumber] = useState<string>("");
  const [institutionPostcode, setInstitutionPostcode] = useState<string>("");
  const [institutionCity, setInstitutionCity] = useState<string>("");
  const [institutionLatitude, setInstitutionLatitude] = useState<string>("");
  const [institutionLongitude, setInstitutionLongitude] = useState<string>("");
  const [permissions, setPermissions] = useState<Record<number, { can_read: boolean; can_write: boolean }>>({});
  const [status, setStatus] = useState<string>("");

  const load = async () => {
    try {
      const [inst, depotsPayload, usersPayload] = await Promise.all([
        apiFetch<InstitutionRow[]>("/institutions"),
        apiFetch<{ rows?: MasterDepot[] }>("/depots?limit=1000&offset=0&q="),
        apiFetch<{ rows?: UserRow[] }>("/users?limit=500&offset=0"),
      ]);
      setInstitutions(Array.isArray(inst) ? inst : []);
      const depotRows = Array.isArray((depotsPayload as { rows?: MasterDepot[] }).rows)
        ? ((depotsPayload as { rows?: MasterDepot[] }).rows as MasterDepot[])
        : (Array.isArray(depotsPayload as unknown) ? (depotsPayload as unknown as MasterDepot[]) : []);
      setDepots(depotRows);
      const nextUsers = Array.isArray(usersPayload.rows) ? usersPayload.rows : [];
      setUsers(nextUsers);
      if (!selectedUsername && nextUsers.length > 0) setSelectedUsername(nextUsers[0].username);
      if (!selectedDepotId && depotRows.length > 0) {
        setSelectedDepotId(Number(depotRows[0].id));
      }
      if (!selectedInstitutionId && Array.isArray(inst) && inst.length > 0) {
        setSelectedInstitutionId(Number(inst[0].id));
      }
      if (!editingInstitutionId && Array.isArray(inst) && inst.length > 0) {
        const first = inst[0];
        setEditingInstitutionId(Number(first.id));
        setInstitutionName(first.name || "");
        setInstitutionStreet(first.strasse || "");
        setInstitutionHouseNumber(first.hausnummer || "");
        setInstitutionPostcode(first.postleitzahl || "");
        setInstitutionCity(first.stadt || "");
        setInstitutionLatitude(first.latitude != null ? String(first.latitude) : "");
        setInstitutionLongitude(first.longitude != null ? String(first.longitude) : "");
      }
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Laden fehlgeschlagen.");
    }
  };

  useSessionReload(load);

  useEffect(() => {
    if (!selectedUsername) return;
    const run = async () => {
      try {
        const rows = await apiFetch<DepotPermissionRow[]>(`/users/${encodeURIComponent(selectedUsername)}/depot-permissions`);
        const next: Record<number, { can_read: boolean; can_write: boolean }> = {};
        rows.forEach((row) => {
          next[Number(row.depot_id)] = {
            can_read: Boolean(Number(row.can_read || 0)),
            can_write: Boolean(Number(row.can_write || 0)),
          };
        });
        setPermissions(next);
      } catch {
        setPermissions({});
      }
    };
    void run();
  }, [selectedUsername]);

  const savePermissions = async () => {
    try {
      await apiFetch("/users/depot-permissions", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: selectedUsername,
          permissions: depots.map((depot) => ({
            depot_id: Number(depot.id),
            can_read: Boolean(permissions[Number(depot.id)]?.can_read),
            can_write: Boolean(permissions[Number(depot.id)]?.can_write),
          })),
        }),
      });
      setStatus("Depotrechte gespeichert.");
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Speichern fehlgeschlagen.");
    }
  };

  const createInstitution = async () => {
    const name = institutionName.trim();
    if (!name) {
      setStatus("Bitte Institutionsnamen eingeben.");
      return;
    }
    try {
      await apiFetch("/institutions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          adresse: composeAddressParts(institutionStreet, institutionHouseNumber, institutionPostcode, institutionCity) || null,
          strasse: institutionStreet.trim() || null,
          hausnummer: institutionHouseNumber.trim() || null,
          postleitzahl: institutionPostcode.trim() || null,
          stadt: institutionCity.trim() || null,
          latitude: institutionLatitude.trim() ? Number(institutionLatitude) : null,
          longitude: institutionLongitude.trim() ? Number(institutionLongitude) : null,
        }),
      });
      setInstitutionName("");
      setInstitutionStreet("");
      setInstitutionHouseNumber("");
      setInstitutionPostcode("");
      setInstitutionCity("");
      setInstitutionLatitude("");
      setInstitutionLongitude("");
      setStatus("Institution angelegt.");
      await load();
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Institution konnte nicht angelegt werden.");
    }
  };

  const geocodeInstitutionAddress = async () => {
    const q = composeAddressParts(institutionStreet, institutionHouseNumber, institutionPostcode, institutionCity);
    if (!q) {
      setStatus("Bitte zuerst eine Adresse eingeben.");
      return;
    }
    try {
      const result = await apiFetch<{ latitude: number; longitude: number; display_name?: string }>(
        `/geo/geocode?q=${encodeURIComponent(q)}`,
      );
      setInstitutionLatitude(String(result.latitude));
      setInstitutionLongitude(String(result.longitude));
      setStatus(`Koordinate gefunden: ${result.display_name || "OSM Treffer"}`);
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Geokodierung fehlgeschlagen.");
    }
  };

  const loadInstitutionIntoForm = (institutionId: number) => {
    const selected = institutions.find((item) => Number(item.id) === Number(institutionId));
    if (!selected) return;
    setEditingInstitutionId(Number(selected.id));
    setInstitutionName(selected.name || "");
    setInstitutionStreet(selected.strasse || "");
    setInstitutionHouseNumber(selected.hausnummer || "");
    setInstitutionPostcode(selected.postleitzahl || "");
    setInstitutionCity(selected.stadt || "");
    setInstitutionLatitude(selected.latitude != null ? String(selected.latitude) : "");
    setInstitutionLongitude(selected.longitude != null ? String(selected.longitude) : "");
  };

  const updateInstitution = async () => {
    if (!editingInstitutionId) {
      setStatus("Bitte Institution zum Bearbeiten auswaehlen.");
      return;
    }
    const name = institutionName.trim();
    if (!name) {
      setStatus("Bitte Institutionsnamen eingeben.");
      return;
    }
    try {
      await apiFetch(`/institutions/${editingInstitutionId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          adresse: composeAddressParts(institutionStreet, institutionHouseNumber, institutionPostcode, institutionCity) || null,
          strasse: institutionStreet.trim() || null,
          hausnummer: institutionHouseNumber.trim() || null,
          postleitzahl: institutionPostcode.trim() || null,
          stadt: institutionCity.trim() || null,
          latitude: institutionLatitude.trim() ? Number(institutionLatitude) : null,
          longitude: institutionLongitude.trim() ? Number(institutionLongitude) : null,
        }),
      });
      setStatus("Institution aktualisiert.");
      await load();
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Aktualisierung fehlgeschlagen.");
    }
  };

  const deleteInstitution = async () => {
    if (!editingInstitutionId) {
      setStatus("Bitte Institution auswaehlen.");
      return;
    }
    if (!window.confirm("Institution wirklich loeschen?")) return;
    try {
      await apiFetch(`/institutions/${editingInstitutionId}`, { method: "DELETE" });
      setStatus("Institution geloescht.");
      setEditingInstitutionId(0);
      setInstitutionName("");
      setInstitutionStreet("");
      setInstitutionHouseNumber("");
      setInstitutionPostcode("");
      setInstitutionCity("");
      setInstitutionLatitude("");
      setInstitutionLongitude("");
      await load();
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Loeschen fehlgeschlagen.");
    }
  };

  const assignDepotInstitution = async () => {
    if (!selectedDepotId || !selectedInstitutionId) {
      setStatus("Bitte Depot und Institution auswaehlen.");
      return;
    }
    const depot = depots.find((item) => Number(item.id) === Number(selectedDepotId));
    if (!depot) {
      setStatus("Depot nicht gefunden.");
      return;
    }
    try {
      await apiFetch(`/depots/${selectedDepotId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: depot.name || "",
          adresse: composeAddressParts(depot.strasse, depot.hausnummer, depot.postleitzahl, depot.stadt) || depot.adresse || "",
          strasse: depot.strasse || "",
          hausnummer: depot.hausnummer || "",
          postleitzahl: depot.postleitzahl || "",
          stadt: depot.stadt || "",
          telefon: depot.telefon || "",
          email: depot.email || "",
          institution_id: selectedInstitutionId,
          latitude: depot.latitude ?? null,
          longitude: depot.longitude ?? null,
        }),
      });
      setStatus("Depot-Institution-Zuordnung gespeichert.");
      await load();
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Depot-Zuordnung fehlgeschlagen.");
    }
  };

  return (
    <div className="nd-react-shell">
      <div className="nd-react-heading">
        <p className="nd-react-eyebrow">Institutionen und Depotrechte</p>
      </div>
      <div className="nd-react-grid-two">
        <div className="nd-react-panel">
          <h3>Institutionen</h3>
          <form
            className="nd-react-form nd-react-form-grid"
            onSubmit={(event) => {
              event.preventDefault();
              void createInstitution();
            }}
          >
            <label>
              Institution (Bearbeiten)
              <select value={String(editingInstitutionId)} onChange={(event) => loadInstitutionIntoForm(Number(event.target.value))}>
                {institutions.map((item) => (
                  <option key={item.id} value={String(item.id)}>
                    {item.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Name
              <input value={institutionName} onChange={(event) => setInstitutionName(event.target.value)} required />
            </label>
            <label>
              Strasse
              <input value={institutionStreet} onChange={(event) => setInstitutionStreet(event.target.value)} />
            </label>
            <label>
              Hausnummer
              <input value={institutionHouseNumber} onChange={(event) => setInstitutionHouseNumber(event.target.value)} />
            </label>
            <label>
              Postleitzahl
              <input value={institutionPostcode} onChange={(event) => setInstitutionPostcode(event.target.value.replace(/\D+/g, "").slice(0, 5))} />
            </label>
            <label>
              Stadt
              <input value={institutionCity} onChange={(event) => setInstitutionCity(event.target.value)} />
            </label>
            <label>
              Breitengrad
              <input value={institutionLatitude} onChange={(event) => setInstitutionLatitude(event.target.value)} placeholder="z. B. 52.52" />
            </label>
            <label>
              Laengengrad
              <input value={institutionLongitude} onChange={(event) => setInstitutionLongitude(event.target.value)} placeholder="z. B. 13.405" />
            </label>
            <div className="actions">
              <button type="submit">Institution anlegen</button>
              <button type="button" onClick={() => void geocodeInstitutionAddress()}>
                Adresse geokodieren
              </button>
              <button type="button" onClick={() => void updateInstitution()}>
                Institution speichern
              </button>
              <button type="button" className="btn-danger" onClick={() => void deleteInstitution()}>
                Institution loeschen
              </button>
            </div>
          </form>
          <div className="table-shell table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Adresse</th>
                  <th>Lat</th>
                  <th>Lon</th>
                </tr>
              </thead>
              <tbody>
                {institutions.map((item) => (
                  <tr key={item.id}>
                    <td>{item.name}</td>
                    <td>{item.adresse || "-"}</td>
                    <td>{item.latitude ?? "-"}</td>
                    <td>{item.longitude ?? "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <h3>Depot einer Institution zuordnen</h3>
          <form
            className="nd-react-form nd-react-form-grid"
            onSubmit={(event) => {
              event.preventDefault();
              void assignDepotInstitution();
            }}
          >
            <label>
              Depot
              <select value={String(selectedDepotId)} onChange={(event) => setSelectedDepotId(Number(event.target.value))}>
                {depots.map((item) => (
                  <option key={item.id} value={String(item.id)}>
                    {item.name || `Depot ${item.id}`}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Institution
              <select
                value={String(selectedInstitutionId)}
                onChange={(event) => setSelectedInstitutionId(Number(event.target.value))}
              >
                {institutions.map((item) => (
                  <option key={item.id} value={String(item.id)}>
                    {item.name}
                  </option>
                ))}
              </select>
            </label>
            <div className="actions">
              <button type="submit">Zuordnung speichern</button>
            </div>
          </form>
        </div>
        <div className="nd-react-panel">
          <h3>Depotrechte pro Benutzer</h3>
          <label>
            Benutzer
            <select value={selectedUsername} onChange={(event) => setSelectedUsername(event.target.value)}>
              {users.map((user) => (
                <option key={user.id} value={user.username}>
                  {user.username}
                </option>
              ))}
            </select>
          </label>
          <div className="table-shell table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Depot</th>
                  <th>Institution</th>
                  <th>Read</th>
                  <th>Write</th>
                </tr>
              </thead>
              <tbody>
                {depots.map((depot) => {
                  const key = Number(depot.id);
                  const rights = permissions[key] || { can_read: false, can_write: false };
                  return (
                    <tr key={key}>
                      <td>{depot.name || `Depot ${key}`}</td>
                      <td>{depot.institution_name || "-"}</td>
                      <td>
                        <input
                          type="checkbox"
                          checked={rights.can_read}
                          onChange={(event) =>
                            setPermissions((prev) => ({ ...prev, [key]: { ...rights, can_read: event.target.checked } }))
                          }
                        />
                      </td>
                      <td>
                        <input
                          type="checkbox"
                          checked={rights.can_write}
                          onChange={(event) =>
                            setPermissions((prev) => ({ ...prev, [key]: { ...rights, can_write: event.target.checked } }))
                          }
                        />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div className="actions">
            <button type="button" onClick={savePermissions}>
              Rechte speichern
            </button>
            <button type="button" onClick={() => void load()}>
              Neu laden
            </button>
          </div>
          {status ? <p className={statusClass(classifyStatus(status))}>{status}</p> : null}
        </div>
      </div>
    </div>
  );
}

type MovementRow = {
  id: number;
  typ?: string;
  charge?: string;
  verfall?: string;
  anzahl?: number;
  depot?: string;
  depot_id?: number;
  praeparat?: string;
  praeparat_id?: number;
  has_attachment?: boolean | number;
  datei_name?: string;
};

function MovementHistoryIsland() {
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

function VerfallOverviewIsland() {
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

function AuditLogsIsland() {
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

function ImportManagerIsland() {
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

function BackupManagerIsland() {
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

function EmailManagerIsland() {
  const [activeTab, setActiveTab] = useState<"compose" | "history">("compose");
  const [depots, setDepots] = useState<DepotRow[]>([]);
  const [selectedDepotIds, setSelectedDepotIds] = useState<number[]>([]);
  const [availableRecipients, setAvailableRecipients] = useState<EmailRecipientPreviewRow[]>([]);
  const [selectedContactIds, setSelectedContactIds] = useState<number[]>([]);
  const [subject, setSubject] = useState<string>("");
  const [message, setMessage] = useState<string>("");
  const [sendNow, setSendNow] = useState<boolean>(false);
  const [deliveryStatusText, setDeliveryStatusText] = useState<string>("Versandmodus wird geladen...");
  const [canSendNow, setCanSendNow] = useState<boolean>(false);
  const [recipientStatus, setRecipientStatus] = useState<string>("");
  const [recipientPreviewText, setRecipientPreviewText] = useState<string>("");
  const [draftStatus, setDraftStatus] = useState<string>("");
  const [historyRows, setHistoryRows] = useState<EmailHistoryRow[]>([]);
  const [historyDetailText, setHistoryDetailText] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(true);

  const loadBaseData = async () => {
    setLoading(true);
    try {
      const depotsPayload = await apiFetch<DepotRow[] | { rows?: DepotRow[] }>("/depots?limit=500&offset=0&q=");
      setDepots(normalizeDepotRows(depotsPayload));

      const status = await apiFetch<EmailDeliveryStatus>("/emails/delivery/status");
      if (status.mode === "smtp") {
        setDeliveryStatusText(
          status.can_send_now
            ? `Versandmodus: SMTP aktiv (${status.from_address || "Absender konfiguriert"}).`
            : "Versandmodus: SMTP konfiguriert, aber unvollstaendig.",
        );
      } else {
        setDeliveryStatusText("Versandmodus: Entwurf-only (kein Live-Versand).");
      }
      const allowedNow = Boolean(status.can_send_now);
      setCanSendNow(allowedNow);
      if (!allowedNow) setSendNow(false);

      const history = await apiFetch<EmailHistoryRow[]>("/emails/history?limit=50");
      setHistoryRows(Array.isArray(history) ? history : []);
    } catch (err) {
      const text = err instanceof Error ? err.message : "E-Mail-Daten konnten nicht geladen werden.";
      setDeliveryStatusText(`Versandmodus konnte nicht geladen werden: ${text}`);
      setDraftStatus(text);
    } finally {
      setLoading(false);
    }
  };

  useSessionReload(loadBaseData);

  const refreshRecipientsForSelectedDepots = async (depotIds: number[]) => {
    if (!depotIds.length) {
      setAvailableRecipients([]);
      setSelectedContactIds([]);
      return;
    }
    try {
      const response = await apiFetch<EmailRecipientPreviewResponse>("/emails/recipients-preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ depot_ids: depotIds }),
      });
      const rows = Array.isArray(response.recipients)
        ? response.recipients
        : (Array.isArray(response.rows) ? response.rows : []);
      setAvailableRecipients(rows);
      const availableIds = new Set(rows.map((row) => Number(row.id || 0)).filter((id) => Number.isFinite(id) && id > 0));
      setSelectedContactIds((prev) => prev.filter((id) => availableIds.has(id)));
    } catch (_err) {
      setAvailableRecipients([]);
      setSelectedContactIds([]);
    }
  };

  useEffect(() => {
    void refreshRecipientsForSelectedDepots(selectedDepotIds);
  }, [selectedDepotIds]);

  const previewRecipients = async () => {
    setRecipientStatus("Lade Empfaenger...");
    try {
      const response = await apiFetch<EmailRecipientPreviewResponse>("/emails/recipients-preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ depot_ids: selectedDepotIds, kontakt_ids: selectedContactIds }),
      });
      const rows = Array.isArray(response.recipients)
        ? response.recipients
        : (Array.isArray(response.rows) ? response.rows : []);
      setRecipientStatus(
        `${Number(response.count || 0)} Empfaenger gefunden${
          selectedContactIds.length ? ` (aus ${selectedContactIds.length} ausgewaehlten Kontakten)` : ""
        }.`,
      );
      if (!rows.length) {
        setRecipientPreviewText("Keine Ansprechpartner mit E-Mail gefunden.");
      } else {
        setRecipientPreviewText(
          rows.map((row) => `${row.depot_name || "-"}: ${row.name || "-"} (${row.rolle || "-"}) <${row.email || "-"}>`).join("\n"),
        );
      }
    } catch (err) {
      setRecipientStatus(err instanceof Error ? err.message : "Empfaenger-Vorschau fehlgeschlagen.");
    }
  };

  const submitDraft = async () => {
    if (!selectedDepotIds.length || !subject.trim() || !message.trim()) {
      setDraftStatus("Bitte Entwurf vervollstaendigen.");
      return;
    }
    setDraftStatus("Erstelle E-Mail-Entwurf...");
    try {
      const result = await apiFetch<EmailDraftResult>("/emails/drafts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          depot_ids: selectedDepotIds,
          kontakt_ids: selectedContactIds,
          betreff: subject.trim(),
          nachricht: message,
          send_now: sendNow,
        }),
      });
      const deliveryMessage =
        result.delivery_status === "sent"
          ? `Entwurf gespeichert und gesendet (${Number(result.sent_count || 0)} zugestellt)`
          : result.delivery_status === "send_failed"
            ? `Entwurf gespeichert, Versand fehlgeschlagen (${result.delivery_error || "unbekannter Fehler"})`
            : "Entwurf gespeichert";
      setDraftStatus(`${deliveryMessage} (ID ${Number(result.id || 0)}, ${Number(result.recipient_count || 0)} Empfaenger).`);
      if (result.delivery_status === "draft" && Number(result.id || 0) > 0) {
        const markedSent = window.confirm("Wurde der Entwurf versendet?");
        if (markedSent) {
          await apiFetch(`/emails/history/${Number(result.id)}/delivery-status`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ versand_status: "sent", versand_kanal: "manual", versand_fehler: null }),
          });
          setDraftStatus(
            `Entwurf gespeichert und manuell als gesendet markiert (ID ${Number(result.id || 0)}, ${Number(result.recipient_count || 0)} Empfaenger).`,
          );
        }
      }
      setSubject("");
      setMessage("");
      setSendNow(false);
      const history = await apiFetch<EmailHistoryRow[]>("/emails/history?limit=50");
      setHistoryRows(Array.isArray(history) ? history : []);
      setActiveTab("history");
    } catch (err) {
      setDraftStatus(err instanceof Error ? err.message : "E-Mail-Entwurf konnte nicht erstellt werden.");
    }
  };

  const reloadHistory = async () => {
    try {
      const history = await apiFetch<EmailHistoryRow[]>("/emails/history?limit=50");
      setHistoryRows(Array.isArray(history) ? history : []);
      setDraftStatus("Verlauf aktualisiert.");
    } catch (err) {
      setDraftStatus(err instanceof Error ? err.message : "Verlauf konnte nicht geladen werden.");
    }
  };

  const openHistoryDetail = async (id: number) => {
    try {
      const detail = await apiFetch<EmailHistoryDetail>(`/emails/history/${id}`);
      const recipientLines = String(detail.empfaenger_emails || "").split("; ").join("\n");
      const text =
        `Datum: ${detail.datum || ""}\n` +
        `Betreff: ${detail.betreff || ""}\n` +
        `Status: ${detail.versand_status || "draft"} (${detail.versand_kanal || "draft"})\n` +
        `Depots: ${detail.empfaenger_depots || ""}\n` +
        `Empfaenger (${Number(detail.anzahl_empfaenger || 0)}):\n${recipientLines}\n\n` +
        `${detail.versand_fehler ? `Versandfehler: ${detail.versand_fehler}\n\n` : ""}` +
        `Nachricht:\n${detail.nachricht || ""}`;
      setHistoryDetailText(text);
    } catch (err) {
      setHistoryDetailText(err instanceof Error ? err.message : "Detail konnte nicht geladen werden.");
    }
  };

  const updateHistoryDeliveryStatus = async (id: number, nextStatus: "draft" | "sent") => {
    try {
      await apiFetch(`/emails/history/${id}/delivery-status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          versand_status: nextStatus,
          versand_kanal: nextStatus === "sent" ? "manual" : "draft",
          versand_fehler: null,
        }),
      });
      const history = await apiFetch<EmailHistoryRow[]>("/emails/history?limit=50");
      setHistoryRows(Array.isArray(history) ? history : []);
      if (historyDetailText.trim()) {
        await openHistoryDetail(id);
      }
      setDraftStatus(`E-Mail #${id} als ${nextStatus === "sent" ? "gesendet" : "Entwurf"} markiert.`);
    } catch (err) {
      setDraftStatus(err instanceof Error ? err.message : "Status konnte nicht aktualisiert werden.");
    }
  };

  return (
    <div className="nd-react-shell">
      <div className="nd-react-data-header">
        <h3 className="nd-react-data-title">E-Mail-Kommunikation</h3>
        <span className="nd-react-badge">
          Historie <strong>{historyRows.length}</strong>
        </span>
      </div>
      <div className="inline-tabs">
        <button type="button" className={tabClassName(activeTab === "compose")} onClick={() => setActiveTab("compose")}>
          Neue E-Mail
        </button>
        <button type="button" className={tabClassName(activeTab === "history")} onClick={() => setActiveTab("history")}>
          Verlauf
        </button>
      </div>
      {activeTab === "compose" ? (
        <div className="inline-tab-panel active">
          <h3>Neue E-Mail (Entwurf)</h3>
          <p className={statusClass(classifyStatus(deliveryStatusText))}>{deliveryStatusText}</p>
          <div>
            <div className="nd-react-email-recipient-grid">
              <label>
                Depots (Mehrfachauswahl)
                <select
                  multiple
                  size={7}
                  value={selectedDepotIds.map(String)}
                  onChange={(event) => {
                    const nextIds = Array.from(event.currentTarget.selectedOptions).map((option) => Number(option.value));
                    setSelectedDepotIds(nextIds.filter((value) => Number.isFinite(value) && value > 0));
                  }}
                >
                  {depots.map((row) => (
                    <option key={row.id} value={row.id}>
                      {row.name} (#{row.id})
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Ansprechpartner (optional, Mehrfachauswahl)
                <select
                  multiple
                  size={8}
                  value={selectedContactIds.map(String)}
                  onChange={(event) => {
                    const nextIds = Array.from(event.currentTarget.selectedOptions).map((option) => Number(option.value));
                    setSelectedContactIds(nextIds.filter((value) => Number.isFinite(value) && value > 0));
                  }}
                >
                  {availableRecipients.map((row) => (
                    <option key={String(row.id)} value={String(row.id || "")}>
                      {`${row.depot_name || "-"}: ${row.name || "-"} (${row.rolle || "-"}) <${row.email || "-"}>`}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <div className="actions">
              <button type="button" onClick={() => setSelectedDepotIds(depots.map((item) => Number(item.id)).filter((id) => id > 0))}>
                Alle auswaehlen
              </button>
              <button type="button" onClick={() => setSelectedDepotIds([])}>
                Alle abwaehlen
              </button>
              <button
                type="button"
                onClick={() =>
                  setSelectedContactIds(
                    availableRecipients
                      .map((row) => Number(row.id || 0))
                      .filter((id) => Number.isFinite(id) && id > 0),
                  )
                }
                disabled={!availableRecipients.length}
              >
                Alle Ansprechpartner auswaehlen
              </button>
              <button type="button" onClick={() => setSelectedContactIds([])} disabled={!selectedContactIds.length}>
                Ansprechpartner abwaehlen
              </button>
              <button type="button" onClick={() => void previewRecipients()}>
                Empfaenger-Vorschau
              </button>
            </div>
            <p className={statusClass(classifyStatus(recipientStatus))}>{recipientStatus}</p>
            <pre className="audit-details">{recipientPreviewText}</pre>
            <form
              className="grid"
              onSubmit={(event) => {
                event.preventDefault();
                void submitDraft();
              }}
            >
              <label>
                Betreff
                <input type="text" required value={subject} onChange={(event) => setSubject(event.target.value)} />
              </label>
              <label>
                Nachricht
                <textarea rows={6} value={message} onChange={(event) => setMessage(event.target.value)} />
              </label>
              <label className="checkbox-row nd-react-inline-checkbox">
                <input
                  type="checkbox"
                  checked={sendNow}
                  disabled={!canSendNow}
                  onChange={(event) => setSendNow(event.target.checked)}
                />
                Sofort versenden (wenn SMTP aktiv)
              </label>
              <button type="submit" disabled={loading}>
                E-Mail-Entwurf erstellen
              </button>
            </form>
            <p className={statusClass(classifyStatus(draftStatus))}>{draftStatus}</p>
          </div>
        </div>
      ) : (
        <div className="inline-tab-panel active">
          <h3>E-Mail-Verlauf</h3>
          <div className="actions">
            <button type="button" className="btn-secondary" onClick={() => void reloadHistory()}>
              Aktualisieren
            </button>
          </div>
          <div className="table-shell table-scroll nd-react-clickable-row nd-react-table-compact">
            <table>
              <thead>
                <tr>
                  <th>Datum</th>
                  <th>Betreff</th>
                  <th>Depots</th>
                  <th>Empfaenger</th>
                  <th>Status</th>
                  <th>Aktion</th>
                </tr>
              </thead>
              <tbody>
                {historyRows.length ? (
                  historyRows.map((row) => (
                    <tr key={row.id} onClick={() => void openHistoryDetail(row.id)}>
                      <td>{row.datum || ""}</td>
                      <td>{row.betreff || ""}</td>
                      <td>{row.empfaenger_depots || ""}</td>
                      <td>{String(row.anzahl_empfaenger ?? "")}</td>
                      <td>{String(row.versand_status || "draft")}</td>
                      <td>
                        {String(row.versand_status || "draft") === "sent" ? (
                          <button
                            type="button"
                            className="btn-secondary"
                            onClick={(event) => {
                              event.stopPropagation();
                              void updateHistoryDeliveryStatus(row.id, "draft");
                            }}
                          >
                            Als Entwurf markieren
                          </button>
                        ) : (
                          <button
                            type="button"
                            className="btn-secondary"
                            onClick={(event) => {
                              event.stopPropagation();
                              void updateHistoryDeliveryStatus(row.id, "sent");
                            }}
                          >
                            Als gesendet markieren
                          </button>
                        )}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={6} className="empty-cell">
                      Noch keine E-Mail-Eintraege vorhanden.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <p className="muted">Klick auf eine Zeile zeigt die Details unten.</p>
          <pre className="audit-details">{historyDetailText}</pre>
        </div>
      )}
    </div>
  );
}

function MasterdataManagerIsland() {
  const pageSize = 20;
  const [depots, setDepots] = useState<MasterDepot[]>([]);
  const [praeparate, setPraeparate] = useState<MasterPraeparat[]>([]);
  const [depotSearch, setDepotSearch] = useState<string>("");
  const [praeparatSearch, setPraeparatSearch] = useState<string>("");
  const [depotOffset, setDepotOffset] = useState<number>(0);
  const [praeparatOffset, setPraeparatOffset] = useState<number>(0);
  const [lastDepotCount, setLastDepotCount] = useState<number>(0);
  const [lastPraeparatCount, setLastPraeparatCount] = useState<number>(0);
  const [depotStatus, setDepotStatus] = useState<string>("");
  const [praeparatStatus, setPraeparatStatus] = useState<string>("");
  const [depotForm, setDepotForm] = useState<{
    id: string;
    name: string;
    adresse: string;
    strasse: string;
    hausnummer: string;
    postleitzahl: string;
    stadt: string;
    telefon: string;
    email: string;
    latitude: string;
    longitude: string;
  }>({
    id: "",
    name: "",
    adresse: "",
    strasse: "",
    hausnummer: "",
    postleitzahl: "",
    stadt: "",
    telefon: "",
    email: "",
    latitude: "",
    longitude: "",
  });
  const [praeparatForm, setPraeparatForm] = useState<{
    id: string;
    name: string;
    wirkstoff: string;
    darreichungsform: string;
    staerke: string;
    einheit: string;
    pzn: string;
    hersteller: string;
  }>({
    id: "",
    name: "",
    wirkstoff: "",
    darreichungsform: "",
    staerke: "",
    einheit: "",
    pzn: "",
    hersteller: "",
  });

  const loadDepots = async (offset = depotOffset, search = depotSearch) => {
    try {
      const rows = await apiFetch<MasterDepot[]>(
        `/depots?limit=${pageSize}&offset=${offset}&q=${encodeURIComponent(search.trim())}`,
      );
      const safeRows = Array.isArray(rows) ? rows : [];
      setDepots(safeRows);
      setLastDepotCount(safeRows.length);
      setDepotOffset(offset);
    } catch (err) {
      setDepotStatus(err instanceof Error ? err.message : "Depots konnten nicht geladen werden.");
    }
  };

  const loadPraeparate = async (offset = praeparatOffset, search = praeparatSearch) => {
    try {
      const rows = await apiFetch<MasterPraeparat[]>(
        `/praeparate?limit=${pageSize}&offset=${offset}&q=${encodeURIComponent(search.trim())}`,
      );
      const safeRows = Array.isArray(rows) ? rows : [];
      setPraeparate(safeRows);
      setLastPraeparatCount(safeRows.length);
      setPraeparatOffset(offset);
    } catch (err) {
      setPraeparatStatus(err instanceof Error ? err.message : "Praeparate konnten nicht geladen werden.");
    }
  };

  useEffect(() => {
    void loadDepots(0, "");
    void loadPraeparate(0, "");
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadDepots(0, depotSearch);
    }, 250);
    return () => window.clearTimeout(timer);
  }, [depotSearch]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadPraeparate(0, praeparatSearch);
    }, 250);
    return () => window.clearTimeout(timer);
  }, [praeparatSearch]);

  const geocodeDepotAddress = async () => {
    const address = composeAddressParts(depotForm.strasse, depotForm.hausnummer, depotForm.postleitzahl, depotForm.stadt);
    if (!address) {
      setDepotStatus("Bitte zuerst Strasse, Hausnummer, Postleitzahl und Stadt eingeben.");
      return;
    }
    try {
      const result = await apiFetch<{ latitude: number; longitude: number; display_name?: string }>(
        `/geo/geocode?q=${encodeURIComponent(address)}`,
      );
      setDepotForm((prev) => ({
        ...prev,
        latitude: String(result.latitude),
        longitude: String(result.longitude),
      }));
      setDepotStatus(`Depot-Koordinaten gefunden: ${result.display_name || "OSM Treffer"}`);
    } catch (err) {
      setDepotStatus(err instanceof Error ? err.message : "Depot-Geokodierung fehlgeschlagen.");
    }
  };

  const saveDepot = async () => {
    if (!depotForm.name.trim()) {
      setDepotStatus("Name ist erforderlich.");
      return;
    }
    setDepotStatus("Speichere Depot...");
    try {
      const id = depotForm.id.trim();
      const path = id ? `/depots/${id}` : "/depots";
      const method = id ? "PUT" : "POST";
      await apiFetch(path, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: depotForm.name.trim(),
          adresse: composeAddressParts(depotForm.strasse, depotForm.hausnummer, depotForm.postleitzahl, depotForm.stadt) || null,
          strasse: depotForm.strasse.trim() || null,
          hausnummer: depotForm.hausnummer.trim() || null,
          postleitzahl: depotForm.postleitzahl.trim() || null,
          stadt: depotForm.stadt.trim() || null,
          telefon: depotForm.telefon.trim() || null,
          email: depotForm.email.trim() || null,
          latitude: depotForm.latitude.trim() ? Number(depotForm.latitude) : null,
          longitude: depotForm.longitude.trim() ? Number(depotForm.longitude) : null,
        }),
      });
      setDepotStatus(id ? "Depot aktualisiert." : "Depot erstellt.");
      await loadDepots(depotOffset, depotSearch);
    } catch (err) {
      setDepotStatus(err instanceof Error ? err.message : "Depot konnte nicht gespeichert werden.");
    }
  };

  const deleteDepot = async () => {
    const id = depotForm.id.trim();
    if (!id) {
      setDepotStatus("Bitte Depot-ID zum Loeschen auswaehlen.");
      return;
    }
    if (!window.confirm(`Depot #${id} wirklich loeschen?`)) return;
    setDepotStatus("Loesche Depot...");
    try {
      await apiFetch(`/depots/${id}`, { method: "DELETE" });
      setDepotStatus("Depot geloescht.");
      setDepotForm({ id: "", name: "", adresse: "", strasse: "", hausnummer: "", postleitzahl: "", stadt: "", telefon: "", email: "", latitude: "", longitude: "" });
      await loadDepots(Math.max(0, depotOffset), depotSearch);
    } catch (err) {
      setDepotStatus(err instanceof Error ? err.message : "Depot konnte nicht geloescht werden.");
    }
  };

  const savePraeparat = async () => {
    if (!praeparatForm.name.trim()) {
      setPraeparatStatus("Name ist erforderlich.");
      return;
    }
    setPraeparatStatus("Speichere Praeparat...");
    try {
      const id = praeparatForm.id.trim();
      const path = id ? `/praeparate/${id}` : "/praeparate";
      const method = id ? "PUT" : "POST";
      await apiFetch(path, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: praeparatForm.name.trim(),
          wirkstoff: praeparatForm.wirkstoff.trim() || null,
          darreichungsform: praeparatForm.darreichungsform.trim() || null,
          staerke: praeparatForm.staerke.trim() || null,
          einheit: praeparatForm.einheit.trim() || null,
          pzn: praeparatForm.pzn.trim() || null,
          hersteller: praeparatForm.hersteller.trim() || null,
        }),
      });
      setPraeparatStatus(id ? "Praeparat aktualisiert." : "Praeparat erstellt.");
      await loadPraeparate(praeparatOffset, praeparatSearch);
    } catch (err) {
      setPraeparatStatus(err instanceof Error ? err.message : "Praeparat konnte nicht gespeichert werden.");
    }
  };

  const deletePraeparat = async () => {
    const id = praeparatForm.id.trim();
    if (!id) {
      setPraeparatStatus("Bitte Praeparat-ID zum Loeschen auswaehlen.");
      return;
    }
    if (!window.confirm(`Praeparat #${id} wirklich loeschen?`)) return;
    setPraeparatStatus("Loesche Praeparat...");
    try {
      await apiFetch(`/praeparate/${id}`, { method: "DELETE" });
      setPraeparatStatus("Praeparat geloescht.");
      setPraeparatForm({
        id: "",
        name: "",
        wirkstoff: "",
        darreichungsform: "",
        staerke: "",
        einheit: "",
        pzn: "",
        hersteller: "",
      });
      await loadPraeparate(Math.max(0, praeparatOffset), praeparatSearch);
    } catch (err) {
      setPraeparatStatus(err instanceof Error ? err.message : "Praeparat konnte nicht geloescht werden.");
    }
  };

  return (
    <div className="nd-react-shell">
      <h3>Stammdaten</h3>
      <div className="nd-react-panel">
        <h4>Depots</h4>
          <div className="toolbar">
            <label>
              Depot-Suche
              <input
                type="text"
                placeholder="Name, Adresse, Telefon, E-Mail"
                value={depotSearch}
                onChange={(event) => setDepotSearch(event.target.value)}
              />
            </label>
            <div className="actions">
              <button
                type="button"
                disabled={depotOffset === 0}
                onClick={() => {
                  void loadDepots(Math.max(0, depotOffset - pageSize), depotSearch);
                }}
              >
                Depot &lt;
              </button>
              <button
                type="button"
                disabled={lastDepotCount < pageSize}
                onClick={() => {
                  void loadDepots(depotOffset + pageSize, depotSearch);
                }}
              >
                Depot &gt;
              </button>
            </div>
          </div>
          <form
            className="grid two-col"
            onSubmit={(event) => {
              event.preventDefault();
              void saveDepot();
            }}
          >
            <label>
              Depot-ID (leer = neu)
              <input
                type="number"
                min={1}
                value={depotForm.id}
                onChange={(event) => setDepotForm((prev) => ({ ...prev, id: event.target.value }))}
              />
            </label>
            <label>
              Name
              <input
                type="text"
                required
                value={depotForm.name}
                onChange={(event) => setDepotForm((prev) => ({ ...prev, name: event.target.value }))}
              />
            </label>
            <label>
              Strasse
              <input
                type="text"
                value={depotForm.strasse}
                onChange={(event) => setDepotForm((prev) => ({ ...prev, strasse: event.target.value }))}
              />
            </label>
            <label>
              Hausnummer
              <input
                type="text"
                value={depotForm.hausnummer}
                onChange={(event) => setDepotForm((prev) => ({ ...prev, hausnummer: event.target.value }))}
              />
            </label>
            <label>
              Postleitzahl
              <input
                type="text"
                value={depotForm.postleitzahl}
                onChange={(event) =>
                  setDepotForm((prev) => ({ ...prev, postleitzahl: event.target.value.replace(/\D+/g, "").slice(0, 5) }))
                }
              />
            </label>
            <label>
              Stadt
              <input
                type="text"
                value={depotForm.stadt}
                onChange={(event) => setDepotForm((prev) => ({ ...prev, stadt: event.target.value }))}
              />
            </label>
            <label>
              Telefon
              <input
                type="text"
                value={depotForm.telefon}
                onChange={(event) => setDepotForm((prev) => ({ ...prev, telefon: event.target.value }))}
              />
            </label>
            <label>
              E-Mail
              <input
                type="text"
                value={depotForm.email}
                onChange={(event) => setDepotForm((prev) => ({ ...prev, email: event.target.value }))}
              />
            </label>
            <label>
              Breitengrad
              <input
                type="text"
                value={depotForm.latitude}
                onChange={(event) => setDepotForm((prev) => ({ ...prev, latitude: event.target.value }))}
              />
            </label>
            <label>
              Laengengrad
              <input
                type="text"
                value={depotForm.longitude}
                onChange={(event) => setDepotForm((prev) => ({ ...prev, longitude: event.target.value }))}
              />
            </label>
            <div className="actions">
              <button className="primary-action" type="submit">
                Depot speichern
              </button>
              <button type="button" onClick={() => void geocodeDepotAddress()}>
                Adresse geokodieren
              </button>
              <button type="button" onClick={() => void deleteDepot()}>
                Depot loeschen
              </button>
            </div>
          </form>
          <p className={statusClass(classifyStatus(depotStatus))}>{depotStatus}</p>
          <div>
            <h3>Depots</h3>
            <ul id="react-depots-list">
              {depots.length ? (
                depots.map((row) => (
                  <li
                    key={row.id}
                    className={String(row.id) === depotForm.id ? "list-item-active" : ""}
                    onClick={() =>
                      setDepotForm({
                        id: String(row.id),
                        name: row.name || "",
                        adresse: row.adresse || "",
                        strasse: row.strasse || "",
                        hausnummer: row.hausnummer || "",
                        postleitzahl: row.postleitzahl || "",
                        stadt: row.stadt || "",
                        telefon: row.telefon || "",
                        email: row.email || "",
                        latitude: row.latitude != null ? String(row.latitude) : "",
                        longitude: row.longitude != null ? String(row.longitude) : "",
                      })
                    }
                  >
                    {row.name || "-"}{row.wirkstoff ? ` - ${row.wirkstoff}` : ""} (#{row.id})
                  </li>
                ))
              ) : (
                <li className="empty-cell">Keine Eintraege gefunden.</li>
              )}
            </ul>
          </div>
      </div>
      <div className="nd-react-panel">
        <h4>Praeparate</h4>
          <div className="toolbar">
            <label>
              Praeparat-Suche
              <input
                type="text"
                placeholder="Name"
                value={praeparatSearch}
                onChange={(event) => setPraeparatSearch(event.target.value)}
              />
            </label>
            <div className="actions">
              <button
                type="button"
                disabled={praeparatOffset === 0}
                onClick={() => {
                  void loadPraeparate(Math.max(0, praeparatOffset - pageSize), praeparatSearch);
                }}
              >
                Praeparat &lt;
              </button>
              <button
                type="button"
                disabled={lastPraeparatCount < pageSize}
                onClick={() => {
                  void loadPraeparate(praeparatOffset + pageSize, praeparatSearch);
                }}
              >
                Praeparat &gt;
              </button>
            </div>
          </div>
          <form
            className="grid two-col"
            onSubmit={(event) => {
              event.preventDefault();
              void savePraeparat();
            }}
          >
            <label>
              Praeparat-ID (leer = neu)
              <input
                type="number"
                min={1}
                value={praeparatForm.id}
                onChange={(event) => setPraeparatForm((prev) => ({ ...prev, id: event.target.value }))}
              />
            </label>
            <label>
              Name
              <input
                type="text"
                required
                value={praeparatForm.name}
                onChange={(event) => setPraeparatForm((prev) => ({ ...prev, name: event.target.value }))}
              />
            </label>
            <label>
              Wirkstoff
              <input
                type="text"
                value={praeparatForm.wirkstoff}
                onChange={(event) => setPraeparatForm((prev) => ({ ...prev, wirkstoff: event.target.value }))}
              />
            </label>
            <label>
              Darreichungsform
              <input
                type="text"
                value={praeparatForm.darreichungsform}
                onChange={(event) => setPraeparatForm((prev) => ({ ...prev, darreichungsform: event.target.value }))}
              />
            </label>
            <label>
              Staerke
              <input
                type="text"
                value={praeparatForm.staerke}
                onChange={(event) => setPraeparatForm((prev) => ({ ...prev, staerke: event.target.value }))}
              />
            </label>
            <label>
              Einheit
              <input
                type="text"
                value={praeparatForm.einheit}
                onChange={(event) => setPraeparatForm((prev) => ({ ...prev, einheit: event.target.value }))}
              />
            </label>
            <label>
              PZN
              <input
                type="text"
                value={praeparatForm.pzn}
                onChange={(event) => setPraeparatForm((prev) => ({ ...prev, pzn: event.target.value }))}
              />
            </label>
            <label>
              Hersteller
              <input
                type="text"
                value={praeparatForm.hersteller}
                onChange={(event) => setPraeparatForm((prev) => ({ ...prev, hersteller: event.target.value }))}
              />
            </label>
            <div className="actions">
              <button className="primary-action" type="submit">
                Praeparat speichern
              </button>
              <button type="button" onClick={() => void deletePraeparat()}>
                Praeparat loeschen
              </button>
            </div>
          </form>
          <p className={statusClass(classifyStatus(praeparatStatus))}>{praeparatStatus}</p>
          <div>
            <h3>Praeparate</h3>
            <ul id="react-praeparate-list">
              {praeparate.length ? (
                praeparate.map((row) => (
                  <li
                    key={row.id}
                    className={String(row.id) === praeparatForm.id ? "list-item-active" : ""}
                    onClick={() =>
                      setPraeparatForm({
                        id: String(row.id),
                        name: row.name || "",
                        wirkstoff: row.wirkstoff || "",
                        darreichungsform: row.darreichungsform || "",
                        staerke: row.staerke || "",
                        einheit: row.einheit || "",
                        pzn: row.pzn || "",
                        hersteller: row.hersteller || "",
                      })
                    }
                  >
                    {row.name || "-"} (#{row.id})
                  </li>
                ))
              ) : (
                <li className="empty-cell">Keine Eintraege gefunden.</li>
              )}
            </ul>
          </div>
      </div>
    </div>
  );
}

function AssignmentManagerIsland() {
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

function ContactsManagerIsland() {
  const [depots, setDepots] = useState<DepotRow[]>([]);
  const [selectedDepotId, setSelectedDepotId] = useState<number>(0);
  const [rows, setRows] = useState<ContactRow[]>([]);
  const [status, setStatus] = useState<string>("");
  const [selectedContactId, setSelectedContactId] = useState<number>(0);
  const [form, setForm] = useState<{ name: string; rolle: string; telefon: string; email: string }>({
    name: "",
    rolle: "",
    telefon: "",
    email: "",
  });

  const loadDepots = async () => {
    const depotsPayload = await apiFetch<DepotRow[] | { rows?: DepotRow[] }>("/depots?limit=500&offset=0&q=");
    const nextDepots = normalizeDepotRows(depotsPayload);
    setDepots(nextDepots);
    if (!selectedDepotId && nextDepots.length) setSelectedDepotId(Number(nextDepots[0].id));
    return nextDepots;
  };

  const loadContacts = async (depotId: number) => {
    if (!depotId) {
      setRows([]);
      return;
    }
    const data = await apiFetch<ContactRow[]>(`/depots/${depotId}/kontakte`);
    setRows(Array.isArray(data) ? data : []);
  };

  useEffect(() => {
    void (async () => {
      try {
        const nextDepots = await loadDepots();
        const initialDepotId = selectedDepotId || Number(nextDepots[0]?.id || 0);
        if (initialDepotId) await loadContacts(initialDepotId);
      } catch (err) {
        setStatus(err instanceof Error ? err.message : "Kontakte konnten nicht geladen werden.");
      }
    })();
  }, []);

  useEffect(() => {
    if (!selectedDepotId) return;
    setSelectedContactId(0);
    setForm({ name: "", rolle: "", telefon: "", email: "" });
    void loadContacts(selectedDepotId);
  }, [selectedDepotId]);

  const submit = async () => {
    if (!selectedDepotId) return;
    if (!form.name.trim()) {
      setStatus("Name ist erforderlich.");
      return;
    }
    setStatus("Speichere Kontakt...");
    try {
      const payload = {
        name: form.name.trim(),
        rolle: form.rolle.trim() || null,
        telefon: form.telefon.trim() || null,
        email: form.email.trim() || null,
      };
      if (selectedContactId) {
        await apiFetch(`/kontakte/${selectedContactId}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
      } else {
        await apiFetch(`/depots/${selectedDepotId}/kontakte`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
      }
      setStatus("Kontakt gespeichert.");
      setSelectedContactId(0);
      setForm({ name: "", rolle: "", telefon: "", email: "" });
      await loadContacts(selectedDepotId);
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Kontakt konnte nicht gespeichert werden.");
    }
  };

  const remove = async () => {
    if (!selectedContactId) {
      setStatus("Bitte Kontakt auswaehlen.");
      return;
    }
    if (!window.confirm(`Kontakt #${selectedContactId} wirklich loeschen?`)) return;
    setStatus("Loesche Kontakt...");
    try {
      await apiFetch(`/kontakte/${selectedContactId}`, { method: "DELETE" });
      setStatus("Kontakt geloescht.");
      setSelectedContactId(0);
      setForm({ name: "", rolle: "", telefon: "", email: "" });
      await loadContacts(selectedDepotId);
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Kontakt konnte nicht geloescht werden.");
    }
  };

  return (
    <div className="nd-react-shell">
      <h3>Ansprechpartner</h3>
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
      <div className="table-shell table-scroll">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Rolle</th>
              <th>Telefon</th>
              <th>E-Mail</th>
            </tr>
          </thead>
          <tbody>
            {rows.length ? (
              rows.map((row) => (
                <tr
                  key={row.id}
                  className={row.id === selectedContactId ? "active-row" : ""}
                  onClick={() => {
                    setSelectedContactId(row.id);
                    setForm({
                      name: row.name || "",
                      rolle: row.rolle || "",
                      telefon: row.telefon || "",
                      email: row.email || "",
                    });
                  }}
                >
                  <td>{row.name || ""}</td>
                  <td>{row.rolle || ""}</td>
                  <td>{row.telefon || ""}</td>
                  <td>{row.email || ""}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={4} className="empty-cell">
                  Keine Ansprechpartner fuer das gewaehlte Depot.
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
          void submit();
        }}
      >
        <label>
          Name
          <input type="text" required value={form.name} onChange={(event) => setForm((p) => ({ ...p, name: event.target.value }))} />
        </label>
        <label>
          Rolle
          <input type="text" value={form.rolle} onChange={(event) => setForm((p) => ({ ...p, rolle: event.target.value }))} />
        </label>
        <label>
          Telefon
          <input type="text" value={form.telefon} onChange={(event) => setForm((p) => ({ ...p, telefon: event.target.value }))} />
        </label>
        <label>
          E-Mail
          <input type="text" value={form.email} onChange={(event) => setForm((p) => ({ ...p, email: event.target.value }))} />
        </label>
        <div className="actions">
          <button type="submit">Kontakt speichern</button>
          <button type="button" onClick={() => void remove()}>
            Kontakt loeschen
          </button>
        </div>
      </form>
      <p className={statusClass(classifyStatus(status))}>{status}</p>
    </div>
  );
}

function MovementCreateFormIsland() {
  const [depots, setDepots] = useState<DepotRow[]>([]);
  const [praeparate, setPraeparate] = useState<MasterPraeparat[]>([]);
  const [depotId, setDepotId] = useState<string>("");
  const [praeparatId, setPraeparatId] = useState<string>("");
  const [typ, setTyp] = useState<string>("Zugang");
  const [charge, setCharge] = useState<string>("");
  const [verfall, setVerfall] = useState<string>("");
  const [datum, setDatum] = useState<string>(new Date().toISOString().slice(0, 10));
  const [anzahl, setAnzahl] = useState<string>("1");
  const [empfaenger, setEmpfaenger] = useState<string>("");
  const [attachment, setAttachment] = useState<File | null>(null);
  const [autofillEnabled, setAutofillEnabled] = useState<boolean>(true);
  const [status, setStatus] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);

  const loadPraeparate = async (nextDepotId: string) => {
    if (!nextDepotId) {
      setPraeparate([]);
      setPraeparatId("");
      return;
    }
    const rows = await apiFetch<MasterPraeparat[]>(`/depots/${Number(nextDepotId)}/praeparate`);
    const safeRows = Array.isArray(rows) ? rows : [];
    setPraeparate(safeRows);
    setPraeparatId((prev) => (safeRows.some((row) => String(row.id) === prev) ? prev : String(safeRows[0]?.id || "")));
  };

  const initForm = async () => {
    if (!hasAuthToken()) return;
    try {
      const depotsResponse = await apiFetch<{ rows?: DepotRow[] }>("/depots?limit=500&offset=0&q=");
      const rows = normalizeDepotRows(depotsResponse);
      setDepots(rows);
      const savedEnabled = window.localStorage.getItem(BEWEGUNG_AUTOFILL_ENABLED_KEY);
      const enabled = savedEnabled === null ? true : savedEnabled === "1";
      setAutofillEnabled(enabled);

      const savedRaw = window.localStorage.getItem(BEWEGUNG_LAST_INPUT_KEY);
      const saved = savedRaw ? (JSON.parse(savedRaw) as { depot_id?: number; praeparat_id?: number; typ?: string; anzahl?: number }) : null;
      const initialDepotId = saved?.depot_id ? String(saved.depot_id) : String(rows[0]?.id || "");
      setDepotId(initialDepotId);
      if (saved?.typ) setTyp(String(saved.typ));
      if (Number(saved?.anzahl || 0) > 0) setAnzahl(String(saved?.anzahl));
      await loadPraeparate(initialDepotId);
      if (saved?.praeparat_id) setPraeparatId(String(saved.praeparat_id));
      setStatus("");
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Bewegungsformular konnte nicht initialisiert werden.");
    }
  };

  useSessionReload(initForm);

  const onDepotChange = async (value: string) => {
    setDepotId(value);
    try {
      await loadPraeparate(value);
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Praeparate konnten nicht geladen werden.");
    }
  };

  const validateAttachment = (file: File | null) => {
    if (!file) return;
    const safeName = String(file.name || "").toLowerCase();
    if (!safeName.endsWith(".pdf")) throw new Error("Nur PDF-Dateien sind als Anhang erlaubt.");
    if (Number(file.size || 0) > 10 * 1024 * 1024) throw new Error("PDF-Datei ist zu gross (max. 10 MB).");
    const type = String(file.type || "").toLowerCase();
    if (type && type !== "application/pdf" && type !== "application/x-pdf") {
      throw new Error("Nur PDF-Dateien sind als Anhang erlaubt.");
    }
  };

  const submit = async () => {
    if (!depotId || !praeparatId || !charge.trim() || !verfall.trim() || !datum.trim()) {
      setStatus("Bitte Pflichtfelder ausfuellen.");
      return;
    }
    if (Number(anzahl || 0) <= 0) {
      setStatus("Anzahl muss groesser als 0 sein.");
      return;
    }
    if (typ === "Abgang" && !empfaenger.trim()) {
      setStatus("Empfaenger ist bei Abgang erforderlich.");
      return;
    }
    setLoading(true);
    setStatus("Speichere Bewegung...");
    try {
      validateAttachment(attachment);
      const movement = await apiFetch<{ id: number }>("/bewegungen", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          depot_id: Number(depotId),
          praeparat_id: Number(praeparatId),
          typ,
          charge: charge.trim(),
          verfall: verfall.trim(),
          datum: datum.trim(),
          anzahl: Number(anzahl),
          empfaenger: empfaenger.trim() || null,
        }),
      });
      if (attachment) {
        const formData = new FormData();
        formData.append("file", attachment, attachment.name);
        await apiFetch(`/bewegungen/${movement.id}/attachment`, { method: "POST", body: formData });
      }
      if (autofillEnabled) {
        window.localStorage.setItem(
          BEWEGUNG_LAST_INPUT_KEY,
          JSON.stringify({
            depot_id: Number(depotId),
            praeparat_id: Number(praeparatId),
            typ,
            anzahl: Number(anzahl),
          }),
        );
      }
      setStatus(attachment ? `Bewegung ${movement.id} inkl. PDF gespeichert.` : `Bewegung ${movement.id} gespeichert.`);
      setCharge("");
      setEmpfaenger("");
      setAttachment(null);
      const attachmentInput = document.getElementById("react-bewegung-attachment") as HTMLInputElement | null;
      if (attachmentInput) attachmentInput.value = "";
      window.dispatchEvent(new CustomEvent("ndhub-movement-created"));
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Bewegung konnte nicht gespeichert werden.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="nd-react-shell">
      <div className="nd-react-data-header">
        <h3 className="nd-react-data-title">Neue Bewegung erfassen</h3>
        <span className="nd-react-badge">
          Autofill <strong>{autofillEnabled ? "an" : "aus"}</strong>
        </span>
      </div>
      <form className="grid two-col nd-react-movement-form" onSubmit={(event) => { event.preventDefault(); void submit(); }}>
        <label>
          Depot
          <select required value={depotId} onChange={(event) => void onDepotChange(event.target.value)}>
            <option value="">Depot waehlen</option>
            {depots.map((row) => (
              <option key={row.id} value={row.id}>{row.name || `Depot #${row.id}`}</option>
            ))}
          </select>
        </label>
        <label>
          Praeparat
          <select required value={praeparatId} onChange={(event) => setPraeparatId(event.target.value)}>
            <option value="">Praeparat waehlen</option>
            {praeparate.map((row) => (
              <option key={row.id} value={row.id}>{row.name || `Praeparat #${row.id}`}</option>
            ))}
          </select>
        </label>
        <label>
          Typ
          <select value={typ} onChange={(event) => setTyp(event.target.value)}>
            <option value="Zugang">Zugang</option>
            <option value="Abgang">Abgang</option>
            <option value="Vernichtung">Vernichtung</option>
          </select>
        </label>
        <label>
          Charge
          <input type="text" required value={charge} onChange={(event) => setCharge(event.target.value)} />
        </label>
        <label>
          Verfall (YYYY-MM-DD)
          <input type="text" required value={verfall} onChange={(event) => setVerfall(event.target.value)} />
        </label>
        <label>
          Datum (YYYY-MM-DD)
          <input type="text" required value={datum} onChange={(event) => setDatum(event.target.value)} />
        </label>
        <label>
          Anzahl
          <input type="number" min={1} required value={anzahl} onChange={(event) => setAnzahl(event.target.value)} />
        </label>
        <label>
          Empfaenger (nur bei Abgang)
          <input type="text" value={empfaenger} onChange={(event) => setEmpfaenger(event.target.value)} />
        </label>
        <label>
          PDF-Anhang (optional)
          <input id="react-bewegung-attachment" type="file" accept="application/pdf,.pdf" onChange={(event) => setAttachment(event.target.files?.[0] || null)} />
        </label>
        <label className="checkbox-row">
          <input
            type="checkbox"
            checked={autofillEnabled}
            onChange={(event) => {
              setAutofillEnabled(event.target.checked);
              window.localStorage.setItem(BEWEGUNG_AUTOFILL_ENABLED_KEY, event.target.checked ? "1" : "0");
            }}
          />
          Letzte Auswahl merken (Depot/Praeparat/Typ)
        </label>
        <button type="submit" disabled={loading}>{loading ? "Speichert..." : "Speichern"}</button>
      </form>
      <p className={statusClass(classifyStatus(status))}>{status}</p>
    </div>
  );
}

function DesktopSyncFormIsland() {
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

function UsersAdminFormIsland() {
  const [users, setUsers] = useState<UserRow[]>([]);
  const [catalog, setCatalog] = useState<PermissionCatalogItem[]>([]);
  const [templates, setTemplates] = useState<PermissionTemplate[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<string>("");
  const [username, setUsername] = useState<string>("");
  const [role, setRole] = useState<string>("User");
  const [email, setEmail] = useState<string>("");
  const [isActive, setIsActive] = useState<boolean>(true);
  const [password, setPassword] = useState<string>("");
  const [resetPassword, setResetPassword] = useState<string>("");
  const [permissions, setPermissions] = useState<string[]>([]);
  const [templateKey, setTemplateKey] = useState<string>("");
  const [activityRows, setActivityRows] = useState<ActivityRow[]>([]);
  const [status, setStatus] = useState<string>("");

  const loadUsers = async () => {
    const rows = await apiFetch<UserRow[]>("/users");
    setUsers(Array.isArray(rows) ? rows : []);
  };

  const loadCatalog = async () => {
    const payload = await apiFetch<{ rows?: PermissionCatalogItem[]; templates?: PermissionTemplate[] }>("/permissions/catalog");
    setCatalog(Array.isArray(payload.rows) ? payload.rows : []);
    setTemplates(Array.isArray(payload.templates) ? payload.templates : []);
  };

  const clearForm = () => {
    setSelectedUserId("");
    setUsername("");
    setRole("User");
    setEmail("");
    setIsActive(true);
    setPassword("");
    setResetPassword("");
    setPermissions([]);
    setTemplateKey("");
    setActivityRows([]);
    setStatus("");
  };

  useEffect(() => {
    void (async () => {
      try {
        await Promise.all([loadUsers(), loadCatalog()]);
      } catch (err) {
        setStatus(err instanceof Error ? err.message : "Benutzerdaten konnten nicht geladen werden.");
      }
    })();
  }, []);

  useEffect(() => {
    if (!selectedUserId) return;
    const selected = users.find((row) => String(row.id) === selectedUserId);
    if (!selected) return;
    setUsername(selected.username || "");
    setRole(selected.role || "User");
    setEmail(selected.email || "");
    setIsActive(Boolean(selected.is_active));
    setPassword("");
    setResetPassword("");
    setPermissions(Array.isArray(selected.permissions) ? selected.permissions : []);
    void (async () => {
      try {
        const rows = await apiFetch<ActivityRow[]>(`/users/${Number(selected.id)}/activity?limit=100`);
        setActivityRows(Array.isArray(rows) ? rows : []);
      } catch (err) {
        setStatus(err instanceof Error ? err.message : "Aktivitaeten konnten nicht geladen werden.");
      }
    })();
  }, [selectedUserId, users]);

  useEffect(() => {
    if (role !== "Admin") return;
    setPermissions(catalog.map((item) => item.key));
  }, [role, catalog]);

  const save = async () => {
    if (!username.trim()) {
      setStatus("Bitte Benutzername angeben.");
      return;
    }
    if (!selectedUserId) {
      const hint = passwordPolicyHint(password);
      if (hint) {
        setStatus(hint);
        return;
      }
    }
    if (email.trim() && !email.includes("@")) {
      setStatus("Bitte eine gueltige E-Mail-Adresse eingeben.");
      return;
    }
    setStatus("Speichere Benutzer...");
    try {
      if (selectedUserId) {
        await apiFetch(`/users/${Number(selectedUserId)}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username: username.trim(), role, email: email.trim() || null, is_active: isActive, permissions }),
        });
        setStatus("Benutzer aktualisiert.");
      } else {
        await apiFetch("/users", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username: username.trim(), password, role, email: email.trim() || null, is_active: isActive, permissions }),
        });
        setStatus("Benutzer erstellt.");
      }
      await loadUsers();
      window.dispatchEvent(new CustomEvent("ndhub-users-changed"));
      if (!selectedUserId) clearForm();
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Benutzer konnte nicht gespeichert werden.");
    }
  };

  return (
    <div className="nd-react-shell">
      <div className="nd-react-data-header">
        <h3 className="nd-react-data-title">Benutzer verwalten</h3>
        <span className="nd-react-badge">
          Nutzer <strong>{users.length}</strong>
        </span>
      </div>
      <div className="grid two-col">
        <label>
          Benutzer aus Liste
          <select value={selectedUserId} onChange={(event) => setSelectedUserId(event.target.value)}>
            <option value="">Neuer Benutzer</option>
            {users.map((row) => <option key={row.id} value={row.id}>{row.username} (#{row.id})</option>)}
          </select>
        </label>
        <label>
          Rolle
          <select value={role} onChange={(event) => setRole(event.target.value)}>
            <option value="User">User</option>
            <option value="Admin">Admin</option>
          </select>
        </label>
        <label>
          Benutzername
          <input type="text" value={username} onChange={(event) => setUsername(event.target.value)} />
        </label>
        <label>
          E-Mail
          <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} />
        </label>
        <label className="checkbox-row">
          <input type="checkbox" checked={isActive} onChange={(event) => setIsActive(event.target.checked)} />
          Aktiv
        </label>
        <label>
          Rechtevorlage
          <select value={templateKey} disabled={role === "Admin"} onChange={(event) => setTemplateKey(event.target.value)}>
            <option value="">Vorlage waehlen</option>
            {templates.map((item) => <option key={item.key} value={item.key}>{item.label || item.key}</option>)}
          </select>
        </label>
        <label>
          Berechtigungen
          <select
            multiple
            size={8}
            disabled={role === "Admin"}
            value={permissions}
            onChange={(event) => {
              const next = Array.from(event.currentTarget.selectedOptions).map((option) => option.value);
              setPermissions(next);
            }}
          >
            {catalog.map((item) => <option key={item.key} value={item.key}>{item.label || item.key}</option>)}
          </select>
        </label>
        <div className="actions">
          <button
            type="button"
            disabled={!templateKey || role === "Admin"}
            onClick={() => {
              const tpl = templates.find((item) => item.key === templateKey);
              if (tpl?.permissions) setPermissions(tpl.permissions);
            }}
          >
            Vorlage uebernehmen
          </button>
        </div>
        <label>
          Passwort (Neuanlage)
          <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
        </label>
        <label>
          Neues Passwort (Reset)
          <input type="password" value={resetPassword} onChange={(event) => setResetPassword(event.target.value)} />
        </label>
      </div>
      <div className="actions">
        <button type="button" onClick={() => void save()}>Benutzer speichern</button>
        <button
          type="button"
          onClick={() => {
            void (async () => {
              if (!selectedUserId) {
                setStatus("Bitte zuerst einen Benutzer auswaehlen.");
                return;
              }
              const hint = passwordPolicyHint(resetPassword);
              if (hint) {
                setStatus(hint);
                return;
              }
              await apiFetch(`/users/${Number(selectedUserId)}/reset-password`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ new_password: resetPassword }),
              });
              setStatus("Passwort erfolgreich zurueckgesetzt.");
              setResetPassword("");
            })();
          }}
        >
          Passwort zuruecksetzen
        </button>
        <button type="button" onClick={() => void (async () => {
          if (!selectedUserId) return setStatus("Bitte zuerst einen Benutzer auswaehlen.");
          await apiFetch(`/users/${Number(selectedUserId)}/unlock`, { method: "POST" });
          setStatus("Benutzer entsperrt.");
          await loadUsers();
          window.dispatchEvent(new CustomEvent("ndhub-users-changed"));
        })()}>Benutzer entsperren</button>
        <button type="button" onClick={() => void (async () => {
          if (!selectedUserId) return setStatus("Bitte zuerst einen Benutzer auswaehlen.");
          if (!window.confirm(`Benutzer #${selectedUserId} wirklich loeschen?`)) return;
          await apiFetch(`/users/${Number(selectedUserId)}`, { method: "DELETE" });
          setStatus("Benutzer geloescht.");
          clearForm();
          await loadUsers();
          window.dispatchEvent(new CustomEvent("ndhub-users-changed"));
        })()}>Benutzer loeschen</button>
        <button type="button" onClick={() => clearForm()}>Eingabe leeren</button>
      </div>
      <p className={statusClass(classifyStatus(status))}>{status}</p>
      <h3>Benutzer-Aktivitaet</h3>
      <div className="table-shell table-scroll">
        <table>
          <thead>
            <tr><th>Zeit</th><th>Aktion</th><th>Details</th></tr>
          </thead>
          <tbody>
            {activityRows.length ? activityRows.map((row, idx) => (
              <tr key={`ua-${idx}`}>
                <td>{String(row.timestamp || "")}</td>
                <td>{String(row.action || "")}</td>
                <td>{String(row.details || "")}</td>
              </tr>
            )) : <tr><td colSpan={3} className="empty-cell">Keine Aktivitaeten vorhanden.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function AccountManagerIsland() {
  const [status, setStatus] = useState<string>("");
  const [oldPassword, setOldPassword] = useState<string>("");
  const [newPassword, setNewPassword] = useState<string>("");
  const [avatarUrl, setAvatarUrl] = useState<string>("");
  const [avatarFile, setAvatarFile] = useState<File | null>(null);
  const [activityRows, setActivityRows] = useState<ActivityRow[]>([]);
  const [mustChangePassword, setMustChangePassword] = useState<boolean>(false);

  const loadActivity = async () => {
    const rows = await apiFetch<ActivityRow[]>("/auth/activity?limit=10");
    setActivityRows(Array.isArray(rows) ? rows : []);
  };

  const loadAvatar = async () => {
    const token = window.localStorage.getItem("ndhub_token") || "";
    if (!token) return;
    const response = await fetch("/auth/avatar", { headers: { Authorization: `Bearer ${token}` } });
    if (response.status === 404) {
      setAvatarUrl("");
      return;
    }
    if (!response.ok) throw new Error("Profilbild konnte nicht geladen werden.");
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    setAvatarUrl(url);
  };

  const refreshAccount = async () => {
    if (!hasAuthToken()) return;
    try {
      const me = await apiFetch<MeResponse>("/auth/me");
      setMustChangePassword(Boolean(me.requires_password_change));
      await Promise.all([loadActivity(), loadAvatar()]);
      setStatus("");
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Konto konnte nicht geladen werden.");
    }
  };

  useSessionReload(refreshAccount);

  useEffect(() => {
    return () => {
      if (avatarUrl) URL.revokeObjectURL(avatarUrl);
    };
  }, [avatarUrl]);

  return (
    <div className="nd-react-shell">
      <div className="nd-react-data-header">
        <h3 className="nd-react-data-title">Mein Konto</h3>
        <span className="nd-react-badge">
          Aktivitaeten <strong>{activityRows.length}</strong>
        </span>
      </div>
      {mustChangePassword ? <p className={statusClass("warning")}>Sicherheitsregel: Bitte Standard-Passwort sofort aendern.</p> : null}
      <div className="toolbar">
        <div>
          <h3>Profilbild</h3>
          {avatarUrl ? <img className="account-avatar" src={avatarUrl} alt="Profilbild" /> : <p className="muted">Noch kein Profilbild hinterlegt.</p>}
        </div>
        <div className="actions">
          <input type="file" accept=".png,.jpg,.jpeg,.webp,.bmp" onChange={(event) => setAvatarFile(event.target.files?.[0] || null)} />
          <button type="button" className="btn-primary" onClick={() => void (async () => {
            if (!avatarFile) return setStatus("Bitte zuerst eine Bilddatei waehlen.");
            const formData = new FormData();
            formData.append("file", avatarFile, avatarFile.name);
            await apiFetch("/auth/avatar", { method: "POST", body: formData });
            setStatus("Profilbild gespeichert.");
            await loadAvatar();
            await loadActivity();
          })()}>Profilbild speichern</button>
          <button type="button" className="btn-danger" onClick={() => void (async () => {
            await apiFetch("/auth/avatar", { method: "DELETE" });
            setStatus("Profilbild entfernt.");
            setAvatarUrl("");
            await loadActivity();
          })()}>Profilbild entfernen</button>
        </div>
      </div>
      <form className="grid two-col" onSubmit={(event) => {
        event.preventDefault();
        void (async () => {
          try {
            await apiFetch("/auth/change-password", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
            });
            setStatus("Passwort erfolgreich geaendert.");
            setOldPassword("");
            setNewPassword("");
            setMustChangePassword(false);
            // Notify shell (app.js) so navigation is no longer forced to account-section.
            window.dispatchEvent(new CustomEvent("ndhub-password-changed"));
            await loadActivity();
          } catch (err) {
            setStatus(err instanceof Error ? err.message : "Passwort konnte nicht geaendert werden.");
          }
        })();
      }}>
        <label>
          Altes Passwort
          <input type="password" required value={oldPassword} onChange={(event) => setOldPassword(event.target.value)} />
        </label>
        <label>
          Neues Passwort
          <input type="password" minLength={8} required value={newPassword} onChange={(event) => setNewPassword(event.target.value)} />
        </label>
        <div className="actions">
          <button type="submit" className="btn-primary">Passwort aendern</button>
        </div>
      </form>
      <p className={statusClass(classifyStatus(status))}>{status}</p>
      <h3>Letzte Aktivitaeten</h3>
      <div className="table-shell table-scroll nd-react-table-compact">
        <table>
          <thead>
            <tr><th>Zeit</th><th>Aktion</th><th>Details</th></tr>
          </thead>
          <tbody>
            {activityRows.length ? activityRows.map((row, idx) => (
              <tr key={`ca-${idx}`}>
                <td>{String(row.timestamp || "")}</td>
                <td>{String(row.action || "")}</td>
                <td>{String(row.details || "")}</td>
              </tr>
            )) : <tr><td colSpan={3} className="empty-cell">Keine Aktivitaeten vorhanden.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function mountIsland(id: string, element: React.ReactNode, islandName: string, mounted: Set<string>) {
  const node = document.getElementById(id);
  if (!node) {
    return;
  }
  const root = createRoot(node);
  root.render(element);
  mounted.add(islandName);
}

const ISLAND_REGISTRY: Array<{ id: string; element: React.ReactNode; islandName: string }> = [
  { id: "react-dashboard-overview", element: <DashboardOverviewIsland />, islandName: "dashboard-overview" },
  { id: "react-admin-workspace", element: <AdminWorkspaceIsland />, islandName: "admin-workspace" },
  { id: "react-institutions-map", element: <InstitutionsMapIsland />, islandName: "institutions-map" },
  { id: "react-bewegungen-history", element: <MovementHistoryIsland />, islandName: "bewegungen-history" },
  { id: "react-verfall-overview", element: <VerfallOverviewIsland />, islandName: "verfall-overview" },
  { id: "react-audit-table", element: <AuditLogsIsland />, islandName: "audit-table" },
  { id: "react-import-manager", element: <ImportManagerIsland />, islandName: "import-manager" },
  { id: "react-backup-manager", element: <BackupManagerIsland />, islandName: "backup-manager" },
  { id: "react-email-manager", element: <EmailManagerIsland />, islandName: "email-manager" },
  { id: "react-desktop-sync-archive", element: <DesktopSyncArchiveIsland />, islandName: "desktop-sync-archive" },
  { id: "react-desktop-sync-form", element: <DesktopSyncFormIsland />, islandName: "desktop-sync-form" },
  { id: "react-users-table", element: <UsersTableIsland />, islandName: "users-table" },
  { id: "react-users-admin-form", element: <UsersAdminFormIsland />, islandName: "users-admin-form" },
  { id: "react-report-table", element: <ReportTableIsland />, islandName: "report-table" },
  { id: "react-bewegung-create-form", element: <MovementCreateFormIsland />, islandName: "bewegung-create-form" },
  { id: "react-account-manager", element: <AccountManagerIsland />, islandName: "account-manager" },
];

function bootstrapIslands() {
  const mounted = new Set<string>();
  for (const island of ISLAND_REGISTRY) {
    mountIsland(island.id, island.element, island.islandName, mounted);
  }
  window.NDHubReactIslands = mounted;
  window.dispatchEvent(new CustomEvent("ndhub-react-ready"));
}

bootstrapIslands();

declare global {
  interface Window {
    NDHubReactIslands?: Set<string>;
  }
}

