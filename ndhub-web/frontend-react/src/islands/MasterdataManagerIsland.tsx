import React, { useEffect, useMemo, useRef, useState } from "react";
import * as core from "../core";
const {
  apiFetch, hasAuthToken, useSessionReload, formatDateTime, formatBytes,
  tabClassName, statusClass, composeAddressParts, classifyStatus,
  readReportFilters, readMultiSelectIds, normalizeDepotRows,
  passwordPolicyHint, copyToClipboard, escapePopupHtml, addBaseTileLayer,
  MAP_TILE_URL, MAP_TILE_ATTR,
} = core;

export function MasterdataManagerIsland() {
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

