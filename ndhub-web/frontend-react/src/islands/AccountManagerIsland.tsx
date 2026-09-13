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

export function AccountManagerIsland() {
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
