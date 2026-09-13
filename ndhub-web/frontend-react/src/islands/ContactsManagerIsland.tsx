import React, { useEffect, useMemo, useRef, useState } from "react";
import * as core from "../core";
const {
  apiFetch, hasAuthToken, useSessionReload, formatDateTime, formatBytes,
  tabClassName, statusClass, composeAddressParts, classifyStatus,
  readReportFilters, readMultiSelectIds, normalizeDepotRows,
  passwordPolicyHint, copyToClipboard, escapePopupHtml, addBaseTileLayer,
  MAP_TILE_URL, MAP_TILE_ATTR,
} = core;

export function ContactsManagerIsland() {
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

