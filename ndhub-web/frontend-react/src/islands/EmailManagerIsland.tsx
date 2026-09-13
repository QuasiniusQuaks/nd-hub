import React, { useEffect, useMemo, useRef, useState } from "react";
import * as core from "../core";
const {
  apiFetch, hasAuthToken, useSessionReload, formatDateTime, formatBytes,
  tabClassName, statusClass, composeAddressParts, classifyStatus,
  readReportFilters, readMultiSelectIds, normalizeDepotRows,
  passwordPolicyHint, copyToClipboard, escapePopupHtml, addBaseTileLayer,
  MAP_TILE_URL, MAP_TILE_ATTR,
} = core;

export function EmailManagerIsland() {
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

