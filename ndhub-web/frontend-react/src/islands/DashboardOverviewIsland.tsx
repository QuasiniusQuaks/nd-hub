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

export function DashboardOverviewIsland() {
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

