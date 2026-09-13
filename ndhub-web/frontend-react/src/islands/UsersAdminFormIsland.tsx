import React, { useEffect, useMemo, useRef, useState } from "react";
import * as core from "../core";
const {
  apiFetch, hasAuthToken, useSessionReload, formatDateTime, formatBytes,
  tabClassName, statusClass, composeAddressParts, classifyStatus,
  readReportFilters, readMultiSelectIds, normalizeDepotRows,
  passwordPolicyHint, copyToClipboard, escapePopupHtml, addBaseTileLayer,
  MAP_TILE_URL, MAP_TILE_ATTR,
} = core;

export function UsersAdminFormIsland() {
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

