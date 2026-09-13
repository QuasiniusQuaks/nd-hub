import React from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";
import "leaflet/dist/leaflet.css";
import { DesktopSyncArchiveIsland } from "./islands/DesktopSyncArchiveIsland";
import { UsersTableIsland } from "./islands/UsersTableIsland";
import { ReportTableIsland } from "./islands/ReportTableIsland";
import { DashboardOverviewIsland } from "./islands/DashboardOverviewIsland";
import { AdminWorkspaceIsland } from "./islands/AdminWorkspaceIsland";
import { InstitutionsMapIsland } from "./islands/InstitutionsMapIsland";
import { InstitutionsAdminIsland } from "./islands/InstitutionsAdminIsland";
import { MovementHistoryIsland } from "./islands/MovementHistoryIsland";
import { VerfallOverviewIsland } from "./islands/VerfallOverviewIsland";
import { AuditLogsIsland } from "./islands/AuditLogsIsland";
import { ImportManagerIsland } from "./islands/ImportManagerIsland";
import { BackupManagerIsland } from "./islands/BackupManagerIsland";
import { EmailManagerIsland } from "./islands/EmailManagerIsland";
import { MasterdataManagerIsland } from "./islands/MasterdataManagerIsland";
import { AssignmentManagerIsland } from "./islands/AssignmentManagerIsland";
import { ContactsManagerIsland } from "./islands/ContactsManagerIsland";
import { MovementCreateFormIsland } from "./islands/MovementCreateFormIsland";
import { DesktopSyncFormIsland } from "./islands/DesktopSyncFormIsland";
import { UsersAdminFormIsland } from "./islands/UsersAdminFormIsland";
import { AccountManagerIsland } from "./islands/AccountManagerIsland";

function mountIsland(id: string, element: React.ReactNode, islandName: string, mounted: Set<string>) {
  const node = document.getElementById(id);
  if (!node) {
    return;
  }
  const root = createRoot(node);
  root.render(element);
  mounted.add(islandName);
}

const ISLAND_REGISTRY: Array<{ id: string; element: React.ReactNode; islandName: string }> = [
  { id: "react-dashboard-overview", element: <DashboardOverviewIsland />, islandName: "dashboard-overview" },
  { id: "react-admin-workspace", element: <AdminWorkspaceIsland />, islandName: "admin-workspace" },
  { id: "react-institutions-map", element: <InstitutionsMapIsland />, islandName: "institutions-map" },
  { id: "react-bewegungen-history", element: <MovementHistoryIsland />, islandName: "bewegungen-history" },
  { id: "react-verfall-overview", element: <VerfallOverviewIsland />, islandName: "verfall-overview" },
  { id: "react-audit-table", element: <AuditLogsIsland />, islandName: "audit-table" },
  { id: "react-import-manager", element: <ImportManagerIsland />, islandName: "import-manager" },
  { id: "react-backup-manager", element: <BackupManagerIsland />, islandName: "backup-manager" },
  { id: "react-email-manager", element: <EmailManagerIsland />, islandName: "email-manager" },
  { id: "react-desktop-sync-archive", element: <DesktopSyncArchiveIsland />, islandName: "desktop-sync-archive" },
  { id: "react-desktop-sync-form", element: <DesktopSyncFormIsland />, islandName: "desktop-sync-form" },
  { id: "react-users-table", element: <UsersTableIsland />, islandName: "users-table" },
  { id: "react-users-admin-form", element: <UsersAdminFormIsland />, islandName: "users-admin-form" },
  { id: "react-report-table", element: <ReportTableIsland />, islandName: "report-table" },
  { id: "react-bewegung-create-form", element: <MovementCreateFormIsland />, islandName: "bewegung-create-form" },
  { id: "react-account-manager", element: <AccountManagerIsland />, islandName: "account-manager" },
];

function bootstrapIslands() {
  const mounted = new Set<string>();
  for (const island of ISLAND_REGISTRY) {
    mountIsland(island.id, island.element, island.islandName, mounted);
  }
  window.NDHubReactIslands = mounted;
  window.dispatchEvent(new CustomEvent("ndhub-react-ready"));
}

bootstrapIslands();

declare global {
  interface Window {
    NDHubReactIslands?: Set<string>;
  }
}
