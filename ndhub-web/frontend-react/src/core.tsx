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
export const MAP_TILE_URL = "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png";
export const MAP_TILE_ATTR =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>';

export function addBaseTileLayer(map: L.Map): L.TileLayer {
  return L.tileLayer(MAP_TILE_URL, {
    maxZoom: 18,
    subdomains: "abcd",
    attribution: MAP_TILE_ATTR,
  }).addTo(map);
}

export type DesktopToken = {
  token_fingerprint: string;
  token_masked: string;
  client_label?: string | null;
  username: string;
  role?: string | null;
  created_at: string;
  expires_at: string;
  status: string;
};

export type UserRow = {
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

export type ReportRow = Record<string, string | number | null>;

export type ReportResponse = {
  rows?: ReportRow[];
  kpis?: Record<string, unknown>;
};

export type DashboardOverview = {
  kpis?: {
    depots?: number;
    praeparate?: number;
    bewegungen?: number;
    kritisch_verfallend?: number;
  };
  recent_activity?: Array<Record<string, string | number | null>>;
  expiry_preview?: Array<Record<string, string | number | null>>;
};

export type VerfallOverviewResponse = {
  rows?: Array<Record<string, string | number | null>>;
  stats?: {
    kritisch?: number;
    warnung?: number;
    achtung?: number;
    gesamt_menge?: number;
  };
};

export type AuditRow = {
  timestamp?: string;
  username?: string;
  action?: string;
  resource_type?: string;
  resource_id?: string | number;
  details?: string;
};

export type ImportPreviewResponse = {
  preview_rows?: Array<Record<string, string | number | null>>;
  errors?: string[];
  error_count?: number;
  valid_rows?: number;
  total_rows?: number;
};

export type ImportExecuteResponse = {
  dry_run?: boolean;
  already_applied?: boolean;
  would_imported?: number;
  imported?: number;
  error_count?: number;
  errors?: string[];
};

export type BackupRow = {
  filename?: string;
  created_at?: string;
  size_bytes?: number;
};

export type BackupListResponse = {
  rows?: BackupRow[];
  max_restore_size_mb?: number;
  db_engine?: string;
};

export type DepotRow = {
  id: number;
  name: string;
};

export type EmailRecipientPreviewRow = {
  id?: number;
  depot_id?: number;
  depot_name?: string;
  name?: string;
  rolle?: string;
  email?: string;
};

export type EmailRecipientPreviewResponse = {
  count?: number;
  rows?: EmailRecipientPreviewRow[];
  recipients?: EmailRecipientPreviewRow[];
  depot_names?: string[];
  selected_contact_count?: number;
};

export type EmailDeliveryStatus = {
  mode?: string;
  can_send_now?: boolean;
  from_address?: string;
};

export type EmailDraftResult = {
  id?: number;
  recipient_count?: number;
  delivery_status?: string;
  sent_count?: number;
  delivery_error?: string;
};

export type EmailHistoryRow = {
  id: number;
  datum?: string;
  betreff?: string;
  empfaenger_depots?: string;
  anzahl_empfaenger?: number;
  versand_status?: string;
  versand_kanal?: string;
};

export type EmailHistoryDetail = {
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

export function normalizeDepotRows(payload: unknown): DepotRow[] {
  if (Array.isArray(payload)) return payload as DepotRow[];
  if (payload && typeof payload === "object" && Array.isArray((payload as { rows?: unknown[] }).rows)) {
    return (payload as { rows: DepotRow[] }).rows;
  }
  return [];
}

export type MasterDepot = {
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

export type MasterPraeparat = {
  id: number;
  name?: string;
  wirkstoff?: string | null;
  darreichungsform?: string | null;
  staerke?: string | null;
  einheit?: string | null;
  pzn?: string | null;
  hersteller?: string | null;
};

export type AssignmentRow = {
  praeparat_id: number;
  praeparat_name?: string;
  assigned?: boolean;
  sollbestand?: number;
};

export type ContactRow = {
  id: number;
  name?: string;
  rolle?: string | null;
  telefon?: string | null;
  email?: string | null;
};

export type PermissionCatalogItem = {
  key: string;
  label?: string;
};

export type PermissionTemplate = {
  key: string;
  label?: string;
  permissions?: string[];
};

export type ActivityRow = {
  timestamp?: string;
  action?: string;
  details?: string;
};

export type MeResponse = {
  username?: string;
  role?: string;
  avatar_available?: boolean;
  requires_password_change?: boolean;
};

export type InstitutionMapRow = {
  institution_id: number;
  institution_name?: string;
  institution_adresse?: string;
  latitude?: number | null;
  longitude?: number | null;
  depots?: Array<{ id: number; name?: string; adresse?: string; latitude?: number | null; longitude?: number | null }>;
};

export function escapePopupHtml(value: string): string {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

export type InstitutionRow = {
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

export type DepotPermissionRow = {
  depot_id: number;
  depot_name?: string;
  can_read?: boolean | number;
  can_write?: boolean | number;
};

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
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

export function hasAuthToken(): boolean {
  return Boolean(window.localStorage.getItem("ndhub_token"));
}

/**
 * Islands mount at page load (often before login). Re-run `load` on shell
 * `ndhub-session-ready` so menus/data work after login or password-gate unlock.
 */
export function useSessionReload(load: () => void | Promise<void>, options?: { requireToken?: boolean }): void {
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

export function formatDateTime(value: string): string {
  if (!value) return "-";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}

export function formatBytes(sizeBytes: number): string {
  const value = Number(sizeBytes || 0);
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(2)} MB`;
}

export function tabClassName(active: boolean): string {
  return active ? "inline-tab active" : "inline-tab";
}

export type StatusTone = "default" | "success" | "warning" | "error" | "info";

export function statusClass(tone: StatusTone): string {
  if (tone === "default") return "status";
  return `status ${tone}`;
}

export function composeAddressParts(
  strasse?: string | null,
  hausnummer?: string | null,
  postleitzahl?: string | null,
  stadt?: string | null,
): string {
  const streetBlock = [String(strasse || "").trim(), String(hausnummer || "").trim()].filter(Boolean).join(" ");
  const cityBlock = [String(postleitzahl || "").trim(), String(stadt || "").trim()].filter(Boolean).join(" ");
  return [streetBlock, cityBlock].filter(Boolean).join(", ");
}

export function classifyStatus(message: string): StatusTone {
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

export function readReportFilters(): { perspective: string; typ: string; ids: number[]; startDate: string; endDate: string } {
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

export function readMultiSelectIds(selectId: string): number[] {
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

export const BEWEGUNG_AUTOFILL_ENABLED_KEY = "ndhub_bewegung_autofill_enabled";
export const BEWEGUNG_LAST_INPUT_KEY = "ndhub_bewegung_last_input";

export function passwordPolicyHint(value: string): string {
  const password = String(value || "");
  if (!password) return "Passwort ist erforderlich.";
  if (password.length < 8) return "Passwort muss mindestens 8 Zeichen lang sein.";
  if (!/[A-Z]/.test(password)) return "Passwort muss mindestens einen Grossbuchstaben enthalten.";
  if (!/[a-z]/.test(password)) return "Passwort muss mindestens einen Kleinbuchstaben enthalten.";
  if (!/[0-9]/.test(password)) return "Passwort muss mindestens eine Zahl enthalten.";
  return "";
}

export async function copyToClipboard(text: string): Promise<void> {
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

