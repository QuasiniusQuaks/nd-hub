import React, { useEffect, useMemo, useRef, useState } from "react";
import * as core from "../core";
const {
  apiFetch, hasAuthToken, useSessionReload, formatDateTime, formatBytes,
  tabClassName, statusClass, composeAddressParts, classifyStatus,
  readReportFilters, readMultiSelectIds, normalizeDepotRows,
  passwordPolicyHint, copyToClipboard, escapePopupHtml, addBaseTileLayer,
  MAP_TILE_URL, MAP_TILE_ATTR,
} = core;

export function MovementCreateFormIsland() {
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

