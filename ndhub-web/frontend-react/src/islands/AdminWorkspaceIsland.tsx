import React, { useEffect, useMemo, useRef, useState } from "react";
import * as core from "../core";
const {
  apiFetch, hasAuthToken, useSessionReload, formatDateTime, formatBytes,
  tabClassName, statusClass, composeAddressParts, classifyStatus,
  readReportFilters, readMultiSelectIds, normalizeDepotRows,
  passwordPolicyHint, copyToClipboard, escapePopupHtml, addBaseTileLayer,
  MAP_TILE_URL, MAP_TILE_ATTR,
} = core;

export function AdminWorkspaceIsland() {
  const sections = [
    { id: "admin-masterdata", label: "Depots & Praeparate" },
    { id: "admin-assignments", label: "Zuordnungen" },
    { id: "admin-institutions-rights", label: "Institutionen & Rechte" },
    { id: "admin-contacts", label: "Kontakte" },
  ];
  const [activeSection, setActiveSection] = useState<string>(sections[0].id);

  return (
    <div className="nd-react-shell nd-admin-workspace">
      <div className="nd-react-heading">
        <div>
          <p className="nd-react-eyebrow">Verwaltung</p>
          <h3>Stammdaten-Workspace</h3>
          <p className="muted">Alle Stammdaten-, Zuordnungs-, Institutions-/Rechte- und Kontaktfunktionen auf einer Seite.</p>
        </div>
      </div>
      <div className="inline-tabs">
          {sections.map((section) => (
            <button
              key={section.id}
              type="button"
              className={tabClassName(activeSection === section.id)}
              onClick={() => setActiveSection(section.id)}
            >
              {section.label}
            </button>
          ))}
      </div>
      {activeSection === "admin-masterdata" ? (
        <div className="inline-tab-panel active">
            <MasterdataManagerIsland />
        </div>
      ) : null}
      {activeSection === "admin-assignments" ? (
        <div className="inline-tab-panel active">
            <AssignmentManagerIsland />
        </div>
      ) : null}
      {activeSection === "admin-institutions-rights" ? (
        <div className="inline-tab-panel active">
            <InstitutionsAdminIsland />
        </div>
      ) : null}
      {activeSection === "admin-contacts" ? (
        <div className="inline-tab-panel active">
            <ContactsManagerIsland />
        </div>
      ) : null}
    </div>
  );
}

