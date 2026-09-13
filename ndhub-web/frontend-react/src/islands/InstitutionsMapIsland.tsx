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

export function InstitutionsMapIsland() {
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

