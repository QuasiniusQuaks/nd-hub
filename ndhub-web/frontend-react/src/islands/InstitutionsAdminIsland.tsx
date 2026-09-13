import React, { useEffect, useMemo, useRef, useState } from "react";
import * as core from "../core";
const {
  apiFetch, hasAuthToken, useSessionReload, formatDateTime, formatBytes,
  tabClassName, statusClass, composeAddressParts, classifyStatus,
  readReportFilters, readMultiSelectIds, normalizeDepotRows,
  passwordPolicyHint, copyToClipboard, escapePopupHtml, addBaseTileLayer,
  MAP_TILE_URL, MAP_TILE_ATTR,
} = core;

export function InstitutionsAdminIsland() {
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

