const TOKEN_KEY = "ndhub_token";
const PAGE_SIZE = 20;

const loginForm = document.getElementById("login-form");
const loginStatus = document.getElementById("login-status");
const depotsList = document.getElementById("depots-list");
const praeparateList = document.getElementById("praeparate-list");
const depotSearch = document.getElementById("depot-search");
const depotPrev = document.getElementById("depot-prev");
const depotNext = document.getElementById("depot-next");
const praeparatSearch = document.getElementById("praeparat-search");
const praeparatPrev = document.getElementById("praeparat-prev");
const praeparatNext = document.getElementById("praeparat-next");
const depotForm = document.getElementById("depot-form");
const depotStatus = document.getElementById("depot-status");
const depotDeleteButton = document.getElementById("depot-delete");
const praeparatForm = document.getElementById("praeparat-form");
const praeparatStatus = document.getElementById("praeparat-status");
const praeparatDeleteButton = document.getElementById("praeparat-delete");
const bewegungForm = document.getElementById("bewegung-form");
const bewegungStatus = document.getElementById("bewegung-status");
const bewegungAttachment = document.getElementById("bewegung-attachment");
const bewegungSearch = document.getElementById("bewegung-search");
const bewegungFilterTyp = document.getElementById("bewegung-filter-typ");
const bewegungPrev = document.getElementById("bewegung-prev");
const bewegungNext = document.getElementById("bewegung-next");
const reloadButton = document.getElementById("reload-bewegungen");
const bewegungenBody = document.querySelector("#bewegungen-table tbody");
const auditSection = document.getElementById("audit-section");
const auditSearch = document.getElementById("audit-search");
const auditFilterAction = document.getElementById("audit-filter-action");
const auditFilterResource = document.getElementById("audit-filter-resource");
const auditReload = document.getElementById("audit-reload");
const auditPrev = document.getElementById("audit-prev");
const auditNext = document.getElementById("audit-next");
const auditBody = document.querySelector("#audit-table tbody");
const importFileInput = document.getElementById("import-file");
const importPreviewButton = document.getElementById("import-preview");
const importExecuteButton = document.getElementById("import-execute");
const importTemplateButton = document.getElementById("import-template");
const importStatus = document.getElementById("import-status");
const importPreviewHead = document.querySelector("#import-preview-table thead");
const importPreviewBody = document.querySelector("#import-preview-table tbody");
const importErrors = document.getElementById("import-errors");
const emailDepotsSelect = document.getElementById("email-depots");
const emailSelectAllButton = document.getElementById("email-select-all");
const emailSelectNoneButton = document.getElementById("email-select-none");
const emailPreviewRecipientsButton = document.getElementById("email-preview-recipients");
const emailRecipientStatus = document.getElementById("email-recipient-status");
const emailRecipientPreview = document.getElementById("email-recipient-preview");
const emailDraftForm = document.getElementById("email-draft-form");
const emailDraftStatus = document.getElementById("email-draft-status");
const emailHistoryReloadButton = document.getElementById("email-history-reload");
const emailHistoryBody = document.querySelector("#email-history-table tbody");
const emailHistoryDetail = document.getElementById("email-history-detail");
const reportPerspective = document.getElementById("report-perspective");
const reportIdsSelect = document.getElementById("report-ids");
const reportStartDate = document.getElementById("report-start-date");
const reportEndDate = document.getElementById("report-end-date");
const reportType = document.getElementById("report-type");
const reportLoadButton = document.getElementById("report-load");
const reportExportButton = document.getElementById("report-export-csv");
const reportExportPdfButton = document.getElementById("report-export-pdf");
const reportExportPptButton = document.getElementById("report-export-ppt");
const reportStatus = document.getElementById("report-status");
const reportKpis = document.getElementById("report-kpis");
const reportTableHead = document.querySelector("#report-table thead");
const reportTableBody = document.querySelector("#report-table tbody");
const reportChartLegend = document.getElementById("report-chart-legend");
const reportCharts = document.getElementById("report-charts");
const dashboardKpiDepots = document.getElementById("dashboard-kpi-depots");
const dashboardKpiPraeparate = document.getElementById("dashboard-kpi-praeparate");
const dashboardKpiBewegungen = document.getElementById("dashboard-kpi-bewegungen");
const dashboardKpiKritisch = document.getElementById("dashboard-kpi-kritisch");
const dashboardActivityBody = document.querySelector("#dashboard-activity-table tbody");
const dashboardExpiryBody = document.querySelector("#dashboard-expiry-table tbody");
const dashboardStatus = document.getElementById("dashboard-status");
const dashboardRefreshButton = document.getElementById("dashboard-refresh");
const dashboardOpenBewegungen = document.getElementById("dashboard-open-bewegungen");
const dashboardOpenVerfall = document.getElementById("dashboard-open-verfall");
const dashboardOpenReports = document.getElementById("dashboard-open-reports");
const verfallPerspective = document.getElementById("verfall-perspective");
const verfallIdsSelect = document.getElementById("verfall-ids");
const verfallCategory = document.getElementById("verfall-category");
const verfallSearch = document.getElementById("verfall-search");
const verfallLoadButton = document.getElementById("verfall-load");
const verfallExportCsvButton = document.getElementById("verfall-export-csv");
const verfallTableBody = document.querySelector("#verfall-table tbody");
const verfallStatus = document.getElementById("verfall-status");
const verfallStatKritisch = document.getElementById("verfall-stat-kritisch");
const verfallStatWarnung = document.getElementById("verfall-stat-warnung");
const verfallStatAchtung = document.getElementById("verfall-stat-achtung");
const verfallStatGesamtmenge = document.getElementById("verfall-stat-gesamtmenge");
const themeToggle = document.getElementById("theme-toggle");
const notificationMenu = document.getElementById("notification-menu");
const notificationButton = document.getElementById("notification-button");
const notificationCount = document.getElementById("notification-count");
const notificationMenuPanel = document.getElementById("notification-menu-panel");
const notificationList = document.getElementById("notification-list");
const headerAccountMenu = document.getElementById("header-account-menu");
const headerAccountButton = document.getElementById("header-account-button");
const headerAccountMenuPanel = document.getElementById("header-account-menu-panel");
const headerAccountOpenButton = document.getElementById("header-account-open");
const headerAccountAdminButton = document.getElementById("header-account-admin");
const headerAccountAvatar = document.getElementById("header-account-avatar");
const headerAccountName = document.getElementById("header-account-name");
const loginPill = document.getElementById("login-pill");
const workspaceContext = document.getElementById("workspace-context");
const settingsBackupTabButton = document.querySelector('[data-tab-target="settings-backup-panel"]');
const settingsBackupPanel = document.getElementById("settings-backup-panel");
const navLinks = Array.from(document.querySelectorAll(".nav-link"));
const pageSections = Array.from(document.querySelectorAll(".app-page"));
const subpageLinks = Array.from(document.querySelectorAll(".subpage-link"));
const logoutButton = document.getElementById("logout-button");
const accountSection = document.getElementById("account-section");
const accountPasswordForm = document.getElementById("account-password-form");
const accountStatus = document.getElementById("account-status");
const accountPasswordWarning = document.getElementById("account-password-warning");
const accountActivityBody = document.querySelector("#account-activity-table tbody");
const accountAvatarImage = document.getElementById("account-avatar-image");
const accountAvatarEmpty = document.getElementById("account-avatar-empty");
const accountAvatarForm = document.getElementById("account-avatar-form");
const accountAvatarFile = document.getElementById("account-avatar-file");
const accountAvatarRemoveButton = document.getElementById("account-avatar-remove");
const usersSection = document.getElementById("users-section");
const usersTableBody = document.querySelector("#users-table tbody");
const usersActivityBody = document.querySelector("#users-activity-table tbody");
const usersForm = document.getElementById("users-form");
const usersPermissionsSelect = document.getElementById("users-permissions");
const usersPermissionTemplateSelect = document.getElementById("users-permission-template");
const usersApplyTemplateButton = document.getElementById("users-apply-template");
const usersReloadButton = document.getElementById("users-reload");
const usersResetButton = document.getElementById("users-reset");
const usersUnlockButton = document.getElementById("users-unlock");
const usersDeleteButton = document.getElementById("users-delete");
const usersClearButton = document.getElementById("users-clear");
const usersStatus = document.getElementById("users-status");
const backupDownloadButton = document.getElementById("backup-download");
const backupCreateButton = document.getElementById("backup-create");
const backupReloadButton = document.getElementById("backup-list-reload");
const backupRestoreForm = document.getElementById("backup-restore-form");
const backupRestoreFileInput = document.getElementById("backup-restore-file");
const backupStatus = document.getElementById("backup-status");
const backupTableBody = document.querySelector("#backup-table tbody");
const assignmentDepot = document.getElementById("assignment-depot");
const assignmentList = document.getElementById("assignment-list");
const assignmentSaveButton = document.getElementById("assignment-save");
const assignmentStatus = document.getElementById("assignment-status");
const kontaktDepot = document.getElementById("kontakt-depot");
const kontaktForm = document.getElementById("kontakt-form");
const kontaktDeleteButton = document.getElementById("kontakt-delete");
const kontaktStatus = document.getElementById("kontakt-status");
const kontakteBody = document.querySelector("#kontakte-table tbody");

const depotSelect = document.getElementById("bewegung-depot");
const praeparatSelect = document.getElementById("bewegung-praeparat");
const bewegungAutofillToggle = document.getElementById("bewegung-autofill-toggle");
let depotOffset = 0;
let praeparatOffset = 0;
let bewegungOffset = 0;
let lastDepotCount = 0;
let lastPraeparatCount = 0;
let lastBewegungCount = 0;
let auditOffset = 0;
let lastAuditCount = 0;
let currentRole = null;
let currentUsername = null;
let avatarAvailable = false;
let mustChangePassword = false;
let currentPermissions = new Set();
let permissionCatalog = [];
let permissionTemplates = [];
let currentAssignmentRows = [];
let lastImportPreview = null;
let emailHistoryRows = [];
let reportMasterDepots = [];
let reportMasterPraeparate = [];
let lastReportRows = [];
const depotNameById = new Map();
const praeparatNameById = new Map();
const THEME_KEY = "ndhub_theme";
const LAST_LOGIN_AT_KEY = "ndhub_last_login_at";
let toastContainer = null;
const statusMessageCache = new WeakMap();
const TOAST_LIMITS = {
  maxVisible: 3,
  minIntervalMs: 360,
  dedupeWindowMs: 1600,
  defaultDurationMs: 2800,
};
const toastQueue = [];
const recentToasts = new Map();
let activeToastCount = 0;
let lastToastShownAt = 0;
let toastQueueTimer = null;
let toastSequence = 0;
let activePageId = null;
let movementAutofillAppliedInSession = false;
let headerAccountMenuCloseTimer = null;
let notificationPollTimer = null;
let notificationSince = null;
let notificationMenuCloseTimer = null;
let lastNotificationRows = [];
const inlineTabControllers = new Map();
const inlineTabHintTimers = new Map();
const INLINE_TAB_STORAGE_PREFIX = "ndhub_inline_tab_";
const HEADER_ACCOUNT_MENU_ANIMATION_MS = 140;
const BEWEGUNG_AUTOFILL_ENABLED_KEY = "ndhub_bewegung_autofill_enabled";
const BEWEGUNG_LAST_INPUT_KEY = "ndhub_bewegung_last_input";
const STATUS_CONTEXT_LABELS = {
  "login-status": "Login",
  "depot-status": "Depots",
  "praeparat-status": "Praeparate",
  "bewegung-status": "Bewegungen",
  "assignment-status": "Zuordnungen",
  "kontakt-status": "Kontakte",
  "import-status": "Import",
  "email-recipient-status": "E-Mail Empfaenger",
  "email-draft-status": "E-Mail",
  "report-status": "Auswertungen",
  "dashboard-status": "Dashboard",
  "verfall-status": "Verfall",
  "users-status": "Benutzerverwaltung",
  "account-status": "Konto",
  "backup-status": "Backup",
};
const PAGE_CONTEXT_LABELS = {
  "login-section": "Sicherer Zugang zur Anwendung",
  "dashboard-section": "Uebersicht zu Bestand, Aktivitaeten und Verfall",
  "bewegung-create-section": "Bestandsbewegungen erfassen",
  "bewegung-history-section": "Verlauf durchsuchen und Anhaenge pruefen",
  "verfall-manager-section": "Verfallspositionen filtern, priorisieren und exportieren",
  "settings-section": "Adminbereich: Verwaltung, Sicherheit und Audit",
  "import-section": "Dateien validieren und kontrolliert importieren",
  "email-section": "Empfaenger pruefen und Entwuerfe erstellen",
  "reports-section": "Auswertungen laden und exportieren",
  "account-section": "Profil, Passwort und eigene Aktivitaeten verwalten",
  "users-section": "Benutzer, Rollen und Rechte administrieren",
  "audit-section": "Aenderungen revisionssicher nachvollziehen",
};
const DIRTY_TRACKED_FORMS = [
  depotForm,
  praeparatForm,
  bewegungForm,
  kontaktForm,
  emailDraftForm,
  accountPasswordForm,
  usersForm,
  backupRestoreForm,
];
const IMPORT_ALLOWED_EXTENSIONS = [".csv", ".xlsx", ".xls"];
const BACKUP_ALLOWED_EXTENSIONS = [".db", ".sqlite", ".sqlite3"];
const MAX_IMPORT_FILE_SIZE_BYTES = 10 * 1024 * 1024;
const FORM_STATUS_NODE_BY_ID = {
  "login-form": loginStatus,
  "depot-form": depotStatus,
  "praeparat-form": praeparatStatus,
  "bewegung-form": bewegungStatus,
  "kontakt-form": kontaktStatus,
  "email-draft-form": emailDraftStatus,
  "account-password-form": accountStatus,
  "users-form": usersStatus,
  "backup-restore-form": backupStatus,
};

const CHART_THEME = {
  axis: "#94a3b8",
  grid: "#e2e8f0",
  text: "#0f172a",
  muted: "#64748b",
  positive: "#16a34a",
  neutral: "#2563eb",
  negative: "#dc2626",
  purple: "#7c3aed",
  orange: "#f97316",
};

function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

function removeToken() {
  localStorage.removeItem(TOKEN_KEY);
}

function getBewegungAutofillEnabled() {
  const raw = localStorage.getItem(BEWEGUNG_AUTOFILL_ENABLED_KEY);
  return raw !== "0";
}

function setBewegungAutofillEnabled(enabled) {
  localStorage.setItem(BEWEGUNG_AUTOFILL_ENABLED_KEY, enabled ? "1" : "0");
  if (bewegungAutofillToggle instanceof HTMLInputElement) {
    bewegungAutofillToggle.checked = Boolean(enabled);
  }
}

function readLastBewegungInput() {
  try {
    const raw = localStorage.getItem(BEWEGUNG_LAST_INPUT_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") return null;
    return parsed;
  } catch (_error) {
    return null;
  }
}

function saveLastBewegungInput(payload) {
  if (!payload || typeof payload !== "object") return;
  localStorage.setItem(BEWEGUNG_LAST_INPUT_KEY, JSON.stringify(payload));
}

async function applyBewegungAutofillFromLastInput() {
  if (movementAutofillAppliedInSession) return;
  if (!getBewegungAutofillEnabled()) return;
  if (!(depotSelect instanceof HTMLSelectElement) || !(praeparatSelect instanceof HTMLSelectElement)) return;
  const lastInput = readLastBewegungInput();
  if (!lastInput) return;
  const movementType = document.getElementById("bewegung-typ");
  const amountInput = document.getElementById("bewegung-anzahl");
  const datumInput = document.getElementById("bewegung-datum");

  const hasDepotOption = Array.from(depotSelect.options).some((option) => option.value === String(lastInput.depot_id || ""));
  if (hasDepotOption) {
    depotSelect.value = String(lastInput.depot_id);
    await refreshPraeparateForSelectedDepot();
  }
  const hasPraeparatOption = Array.from(praeparatSelect.options).some(
    (option) => option.value === String(lastInput.praeparat_id || ""),
  );
  if (hasPraeparatOption) {
    praeparatSelect.value = String(lastInput.praeparat_id);
  }
  if (movementType instanceof HTMLSelectElement && lastInput.typ) {
    movementType.value = String(lastInput.typ);
    movementType.dispatchEvent(new Event("change", { bubbles: true }));
  }
  if (amountInput instanceof HTMLInputElement && Number(lastInput.anzahl) > 0) {
    amountInput.value = String(Number(lastInput.anzahl));
  }
  if (datumInput instanceof HTMLInputElement && !datumInput.value.trim()) {
    datumInput.value = new Date().toISOString().slice(0, 10);
  }
  movementAutofillAppliedInSession = true;
}

function hasPermission(permissionKey) {
  if (!permissionKey) return true;
  if (currentRole === "Admin") return true;
  return currentPermissions.has(permissionKey);
}

function isAdminUser() {
  return currentRole === "Admin";
}

function hasPageAccess(requiredKey) {
  if (!requiredKey) return true;
  if (requiredKey === "__admin__") return isAdminUser();
  return hasPermission(requiredKey);
}

function getDefaultLandingPageId() {
  if (hasPermission("movements_read")) return "dashboard-section";
  if (hasPermission("movements_read")) return "bewegung-create-section";
  if (hasPermission("import_use")) return "import-section";
  if (hasPermission("email_use")) return "email-section";
  if (hasPermission("reports_view")) return "reports-section";
  return "account-section";
}

function applyPermissionVisibility() {
  const pagePermissions = {
    "dashboard-section": "movements_read",
    "bewegung-create-section": "movements_read",
    "verfall-manager-section": "movements_read",
    "settings-section": "__admin__",
    "import-section": "import_use",
    "email-section": "email_use",
    "reports-section": "reports_view",
    "account-section": null,
    "login-section": null,
  };
  for (const section of pageSections) {
    const required = pagePermissions[section.id];
    if (required === undefined) continue;
    section.classList.toggle("hidden", !hasPageAccess(required));
  }
  for (const link of navLinks) {
    const targetId = (link.getAttribute("href") || "").replace("#", "");
    const required = pagePermissions[targetId];
    if (required === undefined) continue;
    link.classList.toggle("hidden", !hasPageAccess(required));
  }
  if (settingsBackupTabButton instanceof HTMLElement) {
    settingsBackupTabButton.classList.toggle("hidden", !isAdminUser() || !hasPermission("backup_manage"));
  }
  if (settingsBackupPanel) {
    settingsBackupPanel.classList.toggle("hidden", !isAdminUser() || !hasPermission("backup_manage"));
  }
  if ((!isAdminUser() || !hasPermission("backup_manage")) && settingsBackupPanel?.classList.contains("active")) {
    activateInlineTab("settings", "settings-assignment-panel", { persist: false });
  }
  if (!isAdminUser() && usersActivityBody) {
    usersActivityBody.innerHTML = "";
  }
  if (headerAccountAdminButton) {
    headerAccountAdminButton.classList.toggle("hidden", !isAdminUser());
  }
}

function setAdminUiVisibility(_isAdmin) {
  // Backward-compatible wrapper after permission system introduction.
  applyPermissionVisibility();
}

function setAccountUiVisibility(isVisible) {
  if (headerAccountMenu) headerAccountMenu.classList.toggle("hidden", !isVisible);
  if (notificationMenu) notificationMenu.classList.toggle("hidden", !isVisible);
  if (accountSection) {
    accountSection.classList.toggle("hidden", !isVisible);
  }
  if (!isVisible) {
    closeHeaderAccountMenu();
    closeNotificationMenu();
    updateHeaderAccountPill("", "");
  }
}

function setAuthLocked(locked) {
  document.body.classList.toggle("auth-locked", locked);
  if (locked) {
    setAccountUiVisibility(false);
    currentRole = null;
    currentUsername = null;
    avatarAvailable = false;
    mustChangePassword = false;
    movementAutofillAppliedInSession = false;
    currentPermissions = new Set();
    stopNotificationPolling();
    notificationSince = null;
    renderNotificationList([], { replace: true });
    applyPermissionVisibility();
    if (logoutButton) logoutButton.classList.add("hidden");
    showPage("login-section");
    return;
  }
  if (logoutButton) logoutButton.classList.remove("hidden");
}

function setTheme(mode) {
  const darkModeEnabled = mode === "dark";
  document.body.classList.toggle("dark-mode", darkModeEnabled);
  if (themeToggle) {
    const label = darkModeEnabled ? "Light Mode aktivieren" : "Dark Mode aktivieren";
    themeToggle.setAttribute("title", label);
    themeToggle.setAttribute("aria-label", label);
  }
  localStorage.setItem(THEME_KEY, darkModeEnabled ? "dark" : "light");
}

function updateHeaderAccountPill(username = "", avatarUrl = "") {
  if (headerAccountName) {
    headerAccountName.textContent = username ? username : "Angemeldet";
  }
  if (!headerAccountAvatar) return;
  if (avatarUrl) {
    headerAccountAvatar.innerHTML = `<img src="${avatarUrl}" alt="" />`;
    return;
  }
  const initial = (username || "U").trim().slice(0, 1).toUpperCase();
  headerAccountAvatar.textContent = initial || "U";
}

function closeHeaderAccountMenu() {
  if (!headerAccountMenuPanel) return;
  headerAccountMenuPanel.classList.remove("is-open");
  if (headerAccountButton) headerAccountButton.setAttribute("aria-expanded", "false");
  if (headerAccountMenuCloseTimer) {
    window.clearTimeout(headerAccountMenuCloseTimer);
    headerAccountMenuCloseTimer = null;
  }
  if (headerAccountMenuPanel.classList.contains("hidden")) return;
  headerAccountMenuCloseTimer = window.setTimeout(() => {
    if (!headerAccountMenuPanel.classList.contains("is-open")) {
      headerAccountMenuPanel.classList.add("hidden");
    }
    headerAccountMenuCloseTimer = null;
  }, HEADER_ACCOUNT_MENU_ANIMATION_MS);
}

function toggleHeaderAccountMenu() {
  if (!headerAccountMenuPanel || !headerAccountButton) return;
  const isOpen = headerAccountMenuPanel.classList.contains("is-open");
  if (isOpen) {
    closeHeaderAccountMenu();
    return;
  }
  if (headerAccountMenuCloseTimer) {
    window.clearTimeout(headerAccountMenuCloseTimer);
    headerAccountMenuCloseTimer = null;
  }
  headerAccountMenuPanel.classList.remove("hidden");
  requestAnimationFrame(() => {
    headerAccountMenuPanel.classList.add("is-open");
    headerAccountButton.setAttribute("aria-expanded", "true");
  });
}

function closeNotificationMenu() {
  if (!notificationMenuPanel) return;
  notificationMenuPanel.classList.remove("is-open");
  if (notificationButton) notificationButton.setAttribute("aria-expanded", "false");
  if (notificationMenuCloseTimer) {
    window.clearTimeout(notificationMenuCloseTimer);
    notificationMenuCloseTimer = null;
  }
  if (notificationMenuPanel.classList.contains("hidden")) return;
  notificationMenuCloseTimer = window.setTimeout(() => {
    if (!notificationMenuPanel.classList.contains("is-open")) {
      notificationMenuPanel.classList.add("hidden");
    }
    notificationMenuCloseTimer = null;
  }, HEADER_ACCOUNT_MENU_ANIMATION_MS);
}

function toggleNotificationMenu() {
  if (!notificationMenuPanel || !notificationButton) return;
  const isOpen = notificationMenuPanel.classList.contains("is-open");
  if (isOpen) {
    closeNotificationMenu();
    return;
  }
  if (notificationMenuCloseTimer) {
    window.clearTimeout(notificationMenuCloseTimer);
    notificationMenuCloseTimer = null;
  }
  notificationMenuPanel.classList.remove("hidden");
  requestAnimationFrame(() => {
    notificationMenuPanel.classList.add("is-open");
    notificationButton.setAttribute("aria-expanded", "true");
  });
}

function initializeTheme() {
  setTheme(localStorage.getItem(THEME_KEY) === "dark" ? "dark" : "light");
}

function updateLoginPill(text, isLoggedIn = false) {
  if (!loginPill) return;
  loginPill.textContent = text;
  loginPill.style.borderColor = isLoggedIn ? "#86efac" : "";
  loginPill.style.color = isLoggedIn ? "#166534" : "";
  loginPill.style.backgroundColor = isLoggedIn ? "#ecfdf3" : "";
}

function initializeSectionNavigation() {
  if (!navLinks.length || !pageSections.length) return;
  for (const link of navLinks) {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      const targetId = (link.getAttribute("href") || "").replace("#", "");
      if (!targetId) return;
      showPage(targetId);
    });
  }
  const hashPage = (window.location.hash || "").replace("#", "");
  showPage(hashPage || "login-section", { updateHash: false });
  window.addEventListener("hashchange", () => {
    const nextPage = (window.location.hash || "").replace("#", "");
    if (!nextPage) return;
    showPage(nextPage, { updateHash: false });
  });
}

function initializeInlineTabs() {
  const tabGroups = Array.from(document.querySelectorAll("[data-inline-tabs]"));
  for (const group of tabGroups) {
    const groupName = group.getAttribute("data-inline-tabs");
    const tabs = Array.from(group.querySelectorAll("[data-tab-target]"));
    const panels = groupName
      ? Array.from(document.querySelectorAll(`.inline-tab-panel[data-tab-panel-group="${groupName}"]`))
      : [];
    const activateTab = (targetId, options = {}) => {
      for (const tab of tabs) {
        const isActive = tab.getAttribute("data-tab-target") === targetId;
        tab.classList.toggle("active", isActive);
      }
      for (const panel of panels) {
        const isActive = panel.id === targetId;
        panel.classList.toggle("active", isActive);
      }
      if (groupName && options.persist !== false) {
        localStorage.setItem(`${INLINE_TAB_STORAGE_PREFIX}${groupName}`, targetId);
      }
    };
    if (groupName) {
      inlineTabControllers.set(groupName, activateTab);
    }

    for (const tab of tabs) {
      tab.addEventListener("click", () => {
        const targetId = tab.getAttribute("data-tab-target");
        if (!targetId) return;
        activateTab(targetId);
      });
    }
    if (tabs.length) {
      const firstTarget = tabs[0].getAttribute("data-tab-target");
      const savedTarget = groupName
        ? localStorage.getItem(`${INLINE_TAB_STORAGE_PREFIX}${groupName}`)
        : null;
      const hasSavedTarget = Boolean(
        savedTarget && tabs.some((tab) => tab.getAttribute("data-tab-target") === savedTarget),
      );
      const defaultTarget = hasSavedTarget ? savedTarget : firstTarget;
      if (defaultTarget) activateTab(defaultTarget, { persist: false });
    }
  }
}

function ensureInlineTabHintElement(groupName) {
  const group = document.querySelector(`[data-inline-tabs="${groupName}"]`);
  if (!(group instanceof HTMLElement)) return null;
  let hint = document.querySelector(`.inline-tab-hint[data-tab-hint-group="${groupName}"]`);
  if (!(hint instanceof HTMLElement)) {
    hint = document.createElement("p");
    hint.className = "inline-tab-hint";
    hint.setAttribute("data-tab-hint-group", groupName);
    group.insertAdjacentElement("afterend", hint);
  }
  return hint;
}

function showInlineTabHint(groupName, message, level = "info") {
  const text = String(message || "").trim();
  if (!text) return;
  const hint = ensureInlineTabHintElement(groupName);
  if (!(hint instanceof HTMLElement)) return;

  hint.textContent = text;
  hint.setAttribute("data-level", level);
  hint.classList.add("visible");

  const timer = inlineTabHintTimers.get(groupName);
  if (timer) window.clearTimeout(timer);
  const nextTimer = window.setTimeout(() => {
    hint.classList.remove("visible");
  }, 3800);
  inlineTabHintTimers.set(groupName, nextTimer);
}

function activateInlineTab(groupName, targetId, options = {}) {
  const activate = inlineTabControllers.get(groupName);
  if (!activate || !targetId) return;
  activate(targetId, { persist: options.persist });
  if (options.hint) {
    showInlineTabHint(groupName, options.hint, options.level || "info");
  }
}

function initializeSubpageNavigation() {
  for (const button of subpageLinks) {
    button.addEventListener("click", () => {
      const pageTarget = button.getAttribute("data-page-target");
      if (!pageTarget) return;
      showPage(pageTarget);
    });
  }
}

function initializeBewegungFormUx() {
  const typSelect = document.getElementById("bewegung-typ");
  const empfaengerInput = document.getElementById("bewegung-empfaenger");
  const datumInput = document.getElementById("bewegung-datum");
  const verfallInput = document.getElementById("bewegung-verfall");
  if (bewegungAutofillToggle instanceof HTMLInputElement) {
    bewegungAutofillToggle.checked = getBewegungAutofillEnabled();
    bewegungAutofillToggle.addEventListener("change", () => {
      const enabled = bewegungAutofillToggle.checked;
      setBewegungAutofillEnabled(enabled);
      setStatusWithNextStep(
        bewegungStatus,
        enabled ? "Autofill aktiviert." : "Autofill deaktiviert.",
        enabled ? "Bei neuer Erfassung werden letzte Werte vorgeschlagen" : "Werte manuell erfassen",
      );
    });
  }
  const today = new Date().toISOString().slice(0, 10);
  if (datumInput && !datumInput.value.trim()) datumInput.value = today;
  if (verfallInput && !verfallInput.value.trim()) verfallInput.value = today;

  const updateTypState = () => {
    if (!typSelect || !empfaengerInput) return;
    const isAbgang = typSelect.value === "Abgang";
    empfaengerInput.disabled = !isAbgang;
    if (!isAbgang) empfaengerInput.value = "";
    empfaengerInput.placeholder = isAbgang ? "Empfaenger erforderlich" : "Nur fuer Abgang";
    if (isAbgang && datumInput && !isValidIsoDate(datumInput.value)) {
      datumInput.value = today;
    }
    validateBewegungForm();
  };
  updateTypState();
  typSelect?.addEventListener("change", updateTypState);
  datumInput?.addEventListener("blur", () => validateBewegungForm());
  verfallInput?.addEventListener("blur", () => validateBewegungForm());
  empfaengerInput?.addEventListener("input", () => validateBewegungForm());
}

function ensureToastContainer() {
  if (toastContainer) return toastContainer;
  const container = document.createElement("div");
  container.className = "toast-stack";
  document.body.appendChild(container);
  toastContainer = container;
  return toastContainer;
}

function getToastPriority(level) {
  if (level === "error") return 4;
  if (level === "warning") return 3;
  if (level === "success") return 2;
  return 1;
}

function scheduleToastQueueProcessing(delayMs = 0) {
  if (toastQueueTimer) {
    window.clearTimeout(toastQueueTimer);
    toastQueueTimer = null;
  }
  toastQueueTimer = window.setTimeout(() => {
    toastQueueTimer = null;
    processToastQueue();
  }, Math.max(0, delayMs));
}

function pulseElement(element) {
  if (!(element instanceof HTMLElement)) return;
  element.classList.remove("ux-pulse");
  // Force reflow so the animation can restart on repeated updates.
  // eslint-disable-next-line no-unused-expressions
  element.offsetWidth;
  element.classList.add("ux-pulse");
  window.setTimeout(() => element.classList.remove("ux-pulse"), 460);
}

function spotlightSection(sectionId) {
  const section = document.getElementById(sectionId);
  if (!(section instanceof HTMLElement)) return;
  section.classList.remove("section-spotlight");
  // eslint-disable-next-line no-unused-expressions
  section.offsetWidth;
  section.classList.add("section-spotlight");
  window.setTimeout(() => section.classList.remove("section-spotlight"), 820);
}

function debounce(fn, waitMs = 260) {
  let timer = null;
  return (...args) => {
    if (timer) window.clearTimeout(timer);
    timer = window.setTimeout(() => fn(...args), waitMs);
  };
}

function normalizeLooseDateInput(value) {
  const raw = String(value || "").trim();
  if (!raw) return "";
  const normalized = raw.replaceAll("/", "-").replaceAll(".", "-");
  const parts = normalized.split("-").map((item) => item.trim()).filter(Boolean);
  if (parts.length !== 3) return raw;
  let year = 0;
  let month = 0;
  let day = 0;

  if (/^\d{4}$/.test(parts[0])) {
    year = Number(parts[0]);
    month = Number(parts[1]);
    day = Number(parts[2]);
  } else if (/^\d{4}$/.test(parts[2])) {
    day = Number(parts[0]);
    month = Number(parts[1]);
    year = Number(parts[2]);
  } else {
    return raw;
  }

  if (year < 1900 || year > 2100 || month < 1 || month > 12 || day < 1 || day > 31) {
    return raw;
  }
  const dt = new Date(Date.UTC(year, month - 1, day));
  if (dt.getUTCFullYear() !== year || dt.getUTCMonth() !== month - 1 || dt.getUTCDate() !== day) {
    return raw;
  }
  return `${year.toString().padStart(4, "0")}-${month.toString().padStart(2, "0")}-${day.toString().padStart(2, "0")}`;
}

function initializeInputAssist() {
  document.addEventListener(
    "blur",
    (event) => {
      const target = event.target;
      if (!(target instanceof HTMLInputElement)) return;
      if (target.readOnly || target.disabled) return;
      if (target.type === "password" || target.type === "file" || target.type === "hidden") return;
      if (target.type === "number") return;

      if (target.id === "bewegung-datum" || target.id === "bewegung-verfall") {
        target.value = normalizeLooseDateInput(target.value);
      } else if (target.type === "text" || target.type === "search" || target.type === "email") {
        target.value = target.value.trim();
      }
    },
    true,
  );

  const today = new Date();
  const toIso = (date) => date.toISOString().slice(0, 10);
  if (reportEndDate instanceof HTMLInputElement && !reportEndDate.value) {
    reportEndDate.value = toIso(today);
  }
  if (reportStartDate instanceof HTMLInputElement && !reportStartDate.value) {
    const startDate = new Date(today);
    startDate.setDate(startDate.getDate() - 30);
    reportStartDate.value = toIso(startDate);
  }
}

function markFormDirty(form, dirty = true) {
  if (!(form instanceof HTMLFormElement)) return;
  form.classList.toggle("form-dirty", dirty);
  form.dataset.dirty = dirty ? "1" : "0";
}

function markFormSaved(form) {
  markFormDirty(form, false);
}

function initializeFormDirtyTracking() {
  for (const form of DIRTY_TRACKED_FORMS) {
    if (!(form instanceof HTMLFormElement)) continue;
    const markDirty = (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) return;
      if (target instanceof HTMLButtonElement) return;
      markFormDirty(form, true);
    };
    form.addEventListener("input", markDirty);
    form.addEventListener("change", markDirty);
  }
}

function initializeMoreActionsDismiss() {
  const detailsNodes = Array.from(document.querySelectorAll(".more-actions"));
  if (!detailsNodes.length) return;
  for (const details of detailsNodes) {
    if (!(details instanceof HTMLDetailsElement)) continue;
    details.addEventListener("click", (event) => {
      const target = event.target;
      if (target instanceof HTMLButtonElement) {
        details.open = false;
      }
    });
  }
  document.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof Node)) return;
    for (const details of detailsNodes) {
      if (!(details instanceof HTMLDetailsElement)) continue;
      if (!details.open) continue;
      if (details.contains(target)) continue;
      details.open = false;
    }
  });
}

function renderEmptyTableState(tableBody, colspan, message) {
  if (!tableBody) return;
  tableBody.innerHTML = "";
  const tr = document.createElement("tr");
  tr.innerHTML = `<td class="empty-cell" colspan="${Math.max(1, Number(colspan) || 1)}">${escapeHtml(message)}</td>`;
  tableBody.appendChild(tr);
}

function setStatusWithNextStep(statusNode, message, nextStep = "") {
  if (!(statusNode instanceof HTMLElement)) return;
  const baseMessage = String(message || "").trim();
  const nextStepHint = String(nextStep || "").trim();
  if (!baseMessage) {
    statusNode.textContent = "";
    return;
  }
  statusNode.textContent = nextStepHint
    ? `${baseMessage} Naechster Schritt: ${nextStepHint}`
    : baseMessage;
}

function isValidIsoDate(value) {
  return /^\d{4}-\d{2}-\d{2}$/.test(String(value || "").trim());
}

function validateBewegungForm() {
  const typ = document.getElementById("bewegung-typ");
  const verfall = document.getElementById("bewegung-verfall");
  const datum = document.getElementById("bewegung-datum");
  const empfaenger = document.getElementById("bewegung-empfaenger");
  if (!(typ instanceof HTMLSelectElement)) return true;
  if (!(verfall instanceof HTMLInputElement)) return true;
  if (!(datum instanceof HTMLInputElement)) return true;
  if (!(empfaenger instanceof HTMLInputElement)) return true;

  verfall.value = normalizeLooseDateInput(verfall.value);
  datum.value = normalizeLooseDateInput(datum.value);
  verfall.setCustomValidity(isValidIsoDate(verfall.value) ? "" : "Format: YYYY-MM-DD");
  datum.setCustomValidity(isValidIsoDate(datum.value) ? "" : "Format: YYYY-MM-DD");
  if (typ.value === "Abgang" && !empfaenger.value.trim()) {
    empfaenger.setCustomValidity("Empfaenger ist bei Abgang erforderlich.");
  } else {
    empfaenger.setCustomValidity("");
  }
  return bewegungForm.reportValidity();
}

function validateEmailDraftForm() {
  if (!(emailDraftForm instanceof HTMLFormElement)) return true;
  const selectedDepots = getSelectedEmailDepotIds();
  if (!selectedDepots.length) {
    throw new Error("Bitte mindestens ein Depot auswaehlen.");
  }
  const messageInput = document.getElementById("email-message");
  if (messageInput instanceof HTMLTextAreaElement && !messageInput.value.trim()) {
    messageInput.setCustomValidity("Bitte Nachricht eingeben.");
    emailDraftForm.reportValidity();
    return false;
  }
  if (messageInput instanceof HTMLTextAreaElement) messageInput.setCustomValidity("");
  return true;
}

function hasAllowedExtension(fileName, allowedExtensions) {
  const normalized = String(fileName || "").toLowerCase();
  return allowedExtensions.some((ext) => normalized.endsWith(ext));
}

function validateImportFileSelection() {
  const file = importFileInput?.files?.[0];
  if (!file) {
    throw new Error("Bitte zuerst eine Datei auswaehlen.");
  }
  if (!hasAllowedExtension(file.name, IMPORT_ALLOWED_EXTENSIONS)) {
    throw new Error("Nur CSV- oder Excel-Dateien (.csv, .xlsx, .xls) sind erlaubt.");
  }
  if (file.size > MAX_IMPORT_FILE_SIZE_BYTES) {
    throw new Error("Datei ist zu gross (maximal 10 MB).");
  }
  return file;
}

function validateBackupRestoreFileSelection() {
  const file = backupRestoreFileInput?.files?.[0];
  if (!file) {
    throw new Error("Bitte eine Backup-Datei auswaehlen.");
  }
  if (!hasAllowedExtension(file.name, BACKUP_ALLOWED_EXTENSIONS)) {
    throw new Error("Nur Backup-Dateien mit .db, .sqlite oder .sqlite3 sind erlaubt.");
  }
  return file;
}

function validatePasswordPolicy(password, label = "Passwort") {
  const value = String(password || "");
  if (value.length < 8) {
    throw new Error(`${label} muss mindestens 8 Zeichen lang sein.`);
  }
  if (!/[A-Za-z]/.test(value) || !/\d/.test(value)) {
    throw new Error(`${label} muss mindestens einen Buchstaben und eine Zahl enthalten.`);
  }
}

function passwordPolicyHint(password) {
  const value = String(password || "");
  if (!value) return "";
  if (value.length < 8) return "Mindestens 8 Zeichen erforderlich.";
  if (!/[A-Za-z]/.test(value) || !/\d/.test(value)) return "Mindestens einen Buchstaben und eine Zahl verwenden.";
  return "Passwort entspricht den Mindestregeln.";
}

function validateReportFilters() {
  const ids = getSelectedReportIds();
  if (!ids.length) {
    throw new Error("Bitte mindestens ein Element auswaehlen.");
  }
  const start = reportStartDate?.value || "";
  const end = reportEndDate?.value || "";
  if (start && end && start > end) {
    throw new Error("Der Startzeitraum darf nicht nach dem Endzeitraum liegen.");
  }
  return ids;
}

function validateReportDateRangeSoft() {
  const start = reportStartDate?.value || "";
  const end = reportEndDate?.value || "";
  if (!start || !end) return;
  if (start <= end) return;
  setStatusWithNextStep(reportStatus, "Datumsbereich ungueltig.", "Startdatum auf/frueher als Enddatum setzen");
}

function initializeKeyboardShortcuts() {
  document.addEventListener("keydown", (event) => {
    const key = event.key.toLowerCase();
    const saveIntent = (event.ctrlKey || event.metaKey) && key === "s";
    if (!saveIntent) return;
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;
    const form = target.closest("form");
    if (!(form instanceof HTMLFormElement)) return;
    event.preventDefault();
    form.requestSubmit();
  });

  const emailMessage = document.getElementById("email-message");
  if (emailMessage instanceof HTMLTextAreaElement && emailDraftForm instanceof HTMLFormElement) {
    emailMessage.addEventListener("keydown", (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
        event.preventDefault();
        emailDraftForm.requestSubmit();
      }
    });
  }
}

function focusFirstInvalidField(form) {
  if (!(form instanceof HTMLFormElement)) return;
  const firstInvalid = form.querySelector(":invalid");
  if (!(firstInvalid instanceof HTMLElement)) return;
  firstInvalid.focus({ preventScroll: true });
  firstInvalid.scrollIntoView({ behavior: "smooth", block: "center" });
}

function getStandardValidationMessage(field) {
  if (!(field instanceof HTMLInputElement || field instanceof HTMLSelectElement || field instanceof HTMLTextAreaElement)) {
    return "";
  }
  if (field.validity.valueMissing) return "Bitte dieses Pflichtfeld ausfuellen.";
  if (field.validity.typeMismatch && field instanceof HTMLInputElement && field.type === "email") {
    return "Bitte eine gueltige E-Mail-Adresse eingeben.";
  }
  if (field.validity.patternMismatch) return "Bitte das erwartete Format einhalten.";
  if (field.validity.rangeUnderflow) return `Wert muss mindestens ${field.min} sein.`;
  if (field.validity.rangeOverflow) return `Wert darf hoechstens ${field.max} sein.`;
  if (field.validity.tooShort && field instanceof HTMLInputElement && field.minLength > 0) {
    return `Mindestens ${field.minLength} Zeichen erforderlich.`;
  }
  if (field.validity.tooLong && field instanceof HTMLInputElement && field.maxLength > 0) {
    return `Maximal ${field.maxLength} Zeichen erlaubt.`;
  }
  return "";
}

function initializeRequiredFieldIndicators() {
  const labels = Array.from(document.querySelectorAll("label"));
  for (const label of labels) {
    if (!(label instanceof HTMLLabelElement)) continue;
    const control = label.querySelector("input, select, textarea");
    if (!(control instanceof HTMLInputElement || control instanceof HTMLSelectElement || control instanceof HTMLTextAreaElement)) {
      continue;
    }
    label.classList.toggle("required-field-label", control.required);
  }
}

function initializeFormValidationUx() {
  for (const form of DIRTY_TRACKED_FORMS) {
    if (!(form instanceof HTMLFormElement)) continue;
    form.addEventListener(
      "invalid",
      (event) => {
        const field = event.target;
        if (!(field instanceof HTMLInputElement || field instanceof HTMLSelectElement || field instanceof HTMLTextAreaElement)) {
          return;
        }
        if (!field.validity.customError) {
          field.setCustomValidity(getStandardValidationMessage(field));
        }
        const statusNode = FORM_STATUS_NODE_BY_ID[form.id];
        setStatusWithNextStep(statusNode, field.validationMessage || "Bitte Eingabe korrigieren.", "Fehlerhaftes Feld pruefen");
      },
      true,
    );
    form.addEventListener("input", (event) => {
      const field = event.target;
      if (!(field instanceof HTMLInputElement || field instanceof HTMLSelectElement || field instanceof HTMLTextAreaElement)) {
        return;
      }
      if (field.validity.customError) {
        field.setCustomValidity("");
      }
    });
    form.addEventListener(
      "submit",
      (event) => {
        if (form.checkValidity()) return;
        event.preventDefault();
        form.reportValidity();
        focusFirstInvalidField(form);
      },
      true,
    );
  }
}

function getFirstVisiblePageId() {
  for (const section of pageSections) {
    if (!section.classList.contains("hidden")) {
      return section.id;
    }
  }
  return null;
}

function showPage(pageId, options = {}) {
  closeHeaderAccountMenu();
  const updateHash = options.updateHash !== false;
  const authLocked = document.body.classList.contains("auth-locked");
  if (authLocked && pageId !== "login-section") {
    pageId = "login-section";
  }
  if (mustChangePassword && pageId !== "account-section" && pageId !== "login-section") {
    pageId = "account-section";
  }
  let target = document.getElementById(pageId);
  if (
    !(target instanceof HTMLElement) ||
    !target.classList.contains("app-page") ||
    target.classList.contains("hidden")
  ) {
    const fallbackId = getFirstVisiblePageId();
    if (!fallbackId) return;
    target = document.getElementById(fallbackId);
  }
  if (!(target instanceof HTMLElement)) return;

  for (const section of pageSections) {
    const isActive = section.id === target.id;
    section.classList.toggle("active-page", isActive);
    if (isActive) {
      section.classList.add("is-visible");
    }
  }
  for (const link of navLinks) {
    const linkTarget = (link.getAttribute("href") || "").replace("#", "");
    link.classList.toggle("active", linkTarget === target.id);
  }
  for (const button of subpageLinks) {
    const pageTarget = button.getAttribute("data-page-target") || "";
    button.classList.toggle("active", pageTarget === target.id);
  }
  activePageId = target.id;
  if (workspaceContext) {
    workspaceContext.textContent = PAGE_CONTEXT_LABELS[target.id] || "Desktop-UX mit moderner Web-UI";
  }
  spotlightSection(target.id);

  if (updateHash) {
    window.history.replaceState(null, "", `#${target.id}`);
  }
}

function inferToastLevel(message) {
  const normalized = String(message || "").toLowerCase();
  if (
    normalized.includes("fehl") ||
    normalized.includes("error") ||
    normalized.includes("nicht") ||
    normalized.includes("warnung")
  ) {
    return "error";
  }
  if (normalized.includes("importiert") || normalized.includes("gespeichert") || normalized.includes("aktualisiert")) {
    return "success";
  }
  if (normalized.includes("lade") || normalized.includes("laeuft")) {
    return "info";
  }
  return "info";
}

function buildContextualToastMessage(statusNode, message) {
  const context = STATUS_CONTEXT_LABELS[statusNode.id] || "Status";
  let enriched = String(message || "").trim();
  if (!enriched) return `${context}: -`;

  if (statusNode.id === "depot-status" && /(erstellt|aktualisiert)/i.test(enriched)) {
    const depotName = document.getElementById("depot-name")?.value.trim();
    if (depotName) enriched = `${enriched} (${depotName})`;
  }
  if (statusNode.id === "praeparat-status" && /(erstellt|aktualisiert)/i.test(enriched)) {
    const praeparatName = document.getElementById("praeparat-name")?.value.trim();
    if (praeparatName) enriched = `${enriched} (${praeparatName})`;
  }
  if (statusNode.id === "kontakt-status" && /(gespeichert|geloescht)/i.test(enriched)) {
    const kontaktName = document.getElementById("kontakt-name")?.value.trim();
    if (kontaktName) enriched = `${enriched} (${kontaktName})`;
  }
  if (statusNode.id === "bewegung-status" && /gespeichert/i.test(enriched)) {
    const typ = document.getElementById("bewegung-typ")?.value;
    const charge = document.getElementById("bewegung-charge")?.value.trim();
    const chunks = [typ, charge && `Charge ${charge}`].filter(Boolean);
    if (chunks.length) enriched = `${enriched} [${chunks.join(" | ")}]`;
  }
  if (statusNode.id === "import-status") {
    const fileName = importFileInput?.files?.[0]?.name;
    if (fileName && !/vorlage/i.test(enriched)) enriched = `${enriched} (${fileName})`;
  }
  if (statusNode.id === "report-status" && /(geladen|export)/i.test(enriched)) {
    const reportLabel = reportType?.selectedOptions?.[0]?.textContent?.trim();
    if (reportLabel) enriched = `${enriched} (${reportLabel})`;
  }

  return `${context}: ${enriched}`;
}

function showToast(message, level = "info", duration = 2800) {
  const text = String(message || "").trim();
  if (!text) return;
  const now = Date.now();
  const dedupeKey = `${level}|${text}`;
  const lastSeen = recentToasts.get(dedupeKey);
  if (lastSeen && now - lastSeen < TOAST_LIMITS.dedupeWindowMs) {
    return;
  }
  recentToasts.set(dedupeKey, now);
  for (const [key, seenAt] of recentToasts.entries()) {
    if (now - seenAt > TOAST_LIMITS.dedupeWindowMs * 3) {
      recentToasts.delete(key);
    }
  }

  toastSequence += 1;
  toastQueue.push({
    text,
    level,
    duration: Number(duration) > 0 ? Number(duration) : TOAST_LIMITS.defaultDurationMs,
    priority: getToastPriority(level),
    sequence: toastSequence,
  });
  toastQueue.sort((a, b) => {
    if (b.priority !== a.priority) return b.priority - a.priority;
    return a.sequence - b.sequence;
  });
  processToastQueue();
}

function processToastQueue() {
  if (!toastQueue.length) return;
  if (activeToastCount >= TOAST_LIMITS.maxVisible) return;

  const elapsed = Date.now() - lastToastShownAt;
  if (elapsed < TOAST_LIMITS.minIntervalMs) {
    scheduleToastQueueProcessing(TOAST_LIMITS.minIntervalMs - elapsed);
    return;
  }

  const nextToast = toastQueue.shift();
  if (!nextToast) return;
  const stack = ensureToastContainer();
  const toast = document.createElement("div");
  toast.className = `toast toast-${nextToast.level}`;
  toast.textContent = nextToast.text;
  stack.appendChild(toast);
  activeToastCount += 1;
  lastToastShownAt = Date.now();

  requestAnimationFrame(() => {
    toast.classList.add("show");
  });

  window.setTimeout(() => {
    toast.classList.remove("show");
    window.setTimeout(() => {
      toast.remove();
      activeToastCount = Math.max(0, activeToastCount - 1);
      processToastQueue();
    }, 180);
  }, nextToast.duration);

  if (toastQueue.length) {
    scheduleToastQueueProcessing(TOAST_LIMITS.minIntervalMs);
  }
}

function observeStatusFeedback() {
  const statusNodes = Array.from(document.querySelectorAll(".status"));
  for (const node of statusNodes) {
    statusMessageCache.set(node, node.textContent || "");
    const observer = new MutationObserver(() => {
      const message = (node.textContent || "").trim();
      const previousMessage = (statusMessageCache.get(node) || "").trim();
      statusMessageCache.set(node, message);
      if (!message || message === previousMessage) return;
      if (message.endsWith("...")) return;
      showToast(buildContextualToastMessage(node, message), inferToastLevel(message));
    });
    observer.observe(node, { childList: true, characterData: true, subtree: true });
  }
}

function initializeCardMotion() {
  for (const card of document.querySelectorAll(".card")) {
    card.classList.add("is-visible");
  }
}

function enhanceActionButtons() {
  const buttons = Array.from(document.querySelectorAll("button"));
  for (const button of buttons) {
    const id = (button.id || "").toLowerCase();
    const text = (button.textContent || "").toLowerCase();
    if (id.includes("delete") || text.includes("loesch") || text.includes("abwaehlen")) {
      button.classList.add("btn-danger");
      continue;
    }
    if (
      id.includes("save") ||
      text.includes("speicher") ||
      text.includes("import starten") ||
      text.includes("entwurf erstellen") ||
      text.includes("auswertung laden")
    ) {
      button.classList.add("btn-primary");
      continue;
    }
    if (
      text.includes("aktualisieren") ||
      text.includes("vorlage") ||
      text.includes("download") ||
      text.includes("reload") ||
      id.includes("prev") ||
      id.includes("next")
    ) {
      button.classList.add("btn-secondary");
    }
  }
}

async function apiFetch(path, options = {}) {
  const headers = options.headers || {};
  const token = getToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  const response = await fetch(path, { ...options, headers });
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      if (body && body.detail) {
        detail = body.detail;
      }
    } catch (_error) {
      // Ignore JSON parse issues for plain text errors.
    }
    if (response.status === 401) {
      removeToken();
      setAuthLocked(true);
      updateLoginPill("Bitte anmelden", false);
      loginStatus.textContent = "Sitzung abgelaufen. Bitte erneut anmelden.";
    }
    throw new Error(detail);
  }
  return response;
}

function fillSelect(select, rows, labelKey = "name", options = {}) {
  if (!(select instanceof HTMLSelectElement)) return;
  const previousValue = String(options.preferredValue ?? select.value ?? "");
  select.innerHTML = "";
  const placeholder = options.placeholder || "";
  if (placeholder) {
    const emptyOption = document.createElement("option");
    emptyOption.value = "";
    emptyOption.textContent = placeholder;
    select.appendChild(emptyOption);
  }
  for (const row of rows) {
    const option = document.createElement("option");
    option.value = String(row.id);
    option.textContent = `${row[labelKey]} (#${row.id})`;
    select.appendChild(option);
  }
  const fallbackValue = options.keepSelection !== false ? previousValue : "";
  if (fallbackValue && Array.from(select.options).some((option) => option.value === fallbackValue)) {
    select.value = fallbackValue;
  } else if (placeholder) {
    select.value = "";
  }
}

function renderSimpleList(target, rows) {
  if (!target) return;
  target.innerHTML = "";
  if (!rows.length) {
    const li = document.createElement("li");
    li.textContent = "Keine Eintraege gefunden.";
    li.className = "empty-cell";
    target.appendChild(li);
    pulseElement(target);
    return;
  }
  const activeId =
    target.id === "depots-list"
      ? document.getElementById("depot-id")?.value.trim()
      : document.getElementById("praeparat-id")?.value.trim();
  for (const row of rows) {
    const li = document.createElement("li");
    li.textContent = `${row.name} (#${row.id})`;
    li.dataset.id = String(row.id);
    if (activeId && String(row.id) === activeId) {
      li.classList.add("list-item-active");
    }
    li.style.cursor = "pointer";
    li.addEventListener("click", () => selectMasterRecord(target.id, row));
    target.appendChild(li);
  }
  pulseElement(target);
}

function selectMasterRecord(listId, row) {
  if (listId === "depots-list") {
    document.getElementById("depot-id").value = row.id;
    document.getElementById("depot-name").value = row.name || "";
    document.getElementById("depot-adresse").value = row.adresse || "";
    document.getElementById("depot-telefon").value = row.telefon || "";
    document.getElementById("depot-email").value = row.email || "";
  }
  if (listId === "praeparate-list") {
    document.getElementById("praeparat-id").value = row.id;
    document.getElementById("praeparat-name").value = row.name || "";
  }
}

function renderBewegungen(rows) {
  bewegungenBody.innerHTML = "";
  if (!rows.length) {
    renderEmptyTableState(bewegungenBody, 9, "Keine Bewegungen fuer die aktuelle Filterung.");
    pulseElement(document.getElementById("bewegungen-table"));
    return;
  }
  for (const row of rows) {
    const tr = document.createElement("tr");
    const hasAttachment = row.has_attachment === 1 || row.has_attachment === true;
    const attachmentLabel = hasAttachment ? escapeHtml(row.datei_name || "PDF vorhanden") : "Kein PDF";
    const attachmentActions = hasAttachment
      ? `
          <button type="button" data-action="open-attachment" data-id="${row.id}">Oeffnen</button>
          <span> | </span>
          <button type="button" data-action="download-attachment" data-id="${row.id}">Download</button>
        `
      : "-";
    tr.innerHTML = `
      <td>${row.id}</td>
      <td>${row.typ || ""}</td>
      <td>${row.charge || ""}</td>
      <td>${row.verfall || ""}</td>
      <td>${row.anzahl || ""}</td>
      <td>${row.depot || row.depot_id || ""}</td>
      <td>${row.praeparat || row.praeparat_id || ""}</td>
      <td>${attachmentLabel}</td>
      <td>${attachmentActions}</td>
    `;
    bewegungenBody.appendChild(tr);
  }
  pulseElement(document.getElementById("bewegungen-table"));
}

function renderAssignments(rows) {
  currentAssignmentRows = rows;
  if (!assignmentList) return;
  assignmentList.innerHTML = "";
  for (const row of rows) {
    const wrapper = document.createElement("div");
    wrapper.className = "toolbar";
    wrapper.innerHTML = `
      <label>
        <input type="checkbox" data-assignment-check="${row.praeparat_id}" ${row.assigned ? "checked" : ""} />
        ${escapeHtml(row.praeparat_name)}
      </label>
      <label>
        Sollbestand
        <input
          type="number"
          min="0"
          value="${Number(row.sollbestand || 0)}"
          data-assignment-stock="${row.praeparat_id}"
          ${row.assigned ? "" : "disabled"}
        />
      </label>
    `;
    assignmentList.appendChild(wrapper);
  }
  pulseElement(assignmentList);
}

function renderKontakte(rows) {
  if (!kontakteBody) return;
  kontakteBody.innerHTML = "";
  if (!rows.length) {
    renderEmptyTableState(kontakteBody, 4, "Keine Ansprechpartner fuer das gewaehlte Depot.");
    pulseElement(document.getElementById("kontakte-table"));
    return;
  }
  for (const row of rows) {
    const tr = document.createElement("tr");
    tr.dataset.id = String(row.id);
    tr.dataset.name = row.name || "";
    tr.dataset.rolle = row.rolle || "";
    tr.dataset.telefon = row.telefon || "";
    tr.dataset.email = row.email || "";
    tr.innerHTML = `
      <td>${escapeHtml(row.name || "")}</td>
      <td>${escapeHtml(row.rolle || "")}</td>
      <td>${escapeHtml(row.telefon || "")}</td>
      <td>${escapeHtml(row.email || "")}</td>
    `;
    kontakteBody.appendChild(tr);
  }
  pulseElement(document.getElementById("kontakte-table"));
}

function renderEmailDepots(rows) {
  if (!emailDepotsSelect) return;
  emailDepotsSelect.innerHTML = "";
  for (const row of rows) {
    const option = document.createElement("option");
    option.value = String(row.id);
    option.textContent = `${row.name} (#${row.id})`;
    emailDepotsSelect.appendChild(option);
  }
}

function getSelectedEmailDepotIds() {
  if (!emailDepotsSelect) return [];
  const selected = [];
  for (const option of emailDepotsSelect.options) {
    if (option.selected) {
      selected.push(Number(option.value));
    }
  }
  return selected;
}

function renderEmailHistory(rows) {
  emailHistoryRows = rows;
  if (!emailHistoryBody) return;
  emailHistoryBody.innerHTML = "";
  if (!rows.length) {
    renderEmptyTableState(emailHistoryBody, 4, "Noch keine E-Mail-Eintraege vorhanden.");
    pulseElement(document.getElementById("email-history-table"));
    return;
  }
  for (const row of rows) {
    const tr = document.createElement("tr");
    tr.dataset.id = String(row.id);
    tr.innerHTML = `
      <td>${escapeHtml(row.datum || "")}</td>
      <td>${escapeHtml(row.betreff || "")}</td>
      <td>${escapeHtml(row.empfaenger_depots || "")}</td>
      <td>${escapeHtml(String(row.anzahl_empfaenger || ""))}</td>
    `;
    emailHistoryBody.appendChild(tr);
  }
  pulseElement(document.getElementById("email-history-table"));
}

function formatVerfallKategorieLabel(category) {
  const key = String(category || "").toLowerCase();
  if (key === "kritisch") return "Kritisch";
  if (key === "warnung") return "Warnung";
  if (key === "achtung") return "Achtung";
  if (key === "abgelaufen") return "Abgelaufen";
  return "OK";
}

function getMultiSelectNumberValues(select) {
  if (!(select instanceof HTMLSelectElement)) return [];
  const values = [];
  for (const option of select.options) {
    if (option.selected) values.push(Number(option.value));
  }
  return values.filter((item) => Number.isFinite(item) && item > 0);
}

function renderDashboardOverview(data) {
  const kpis = data?.kpis || {};
  if (dashboardKpiDepots) dashboardKpiDepots.textContent = String(kpis.depots ?? 0);
  if (dashboardKpiPraeparate) dashboardKpiPraeparate.textContent = String(kpis.praeparate ?? 0);
  if (dashboardKpiBewegungen) dashboardKpiBewegungen.textContent = String(kpis.bewegungen ?? 0);
  if (dashboardKpiKritisch) dashboardKpiKritisch.textContent = String(kpis.kritisch_verfallend ?? 0);

  if (dashboardActivityBody) {
    dashboardActivityBody.innerHTML = "";
    const rows = Array.isArray(data?.recent_activity) ? data.recent_activity : [];
    if (!rows.length) {
      renderEmptyTableState(dashboardActivityBody, 5, "Noch keine Aktivitaeten vorhanden.");
    } else {
      for (const row of rows) {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>${escapeHtml(row.datum || "-")}</td>
          <td>${escapeHtml(row.typ || "-")}</td>
          <td>${escapeHtml(row.depot || "-")}</td>
          <td>${escapeHtml(row.praeparat || "-")}</td>
          <td>${escapeHtml(String(row.anzahl ?? "-"))}</td>
        `;
        dashboardActivityBody.appendChild(tr);
      }
    }
  }

  if (dashboardExpiryBody) {
    dashboardExpiryBody.innerHTML = "";
    const rows = Array.isArray(data?.expiry_preview) ? data.expiry_preview : [];
    if (!rows.length) {
      renderEmptyTableState(dashboardExpiryBody, 5, "Keine Verfallspositionen vorhanden.");
    } else {
      for (const row of rows) {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>${escapeHtml(row.depot || "-")}</td>
          <td>${escapeHtml(row.praeparat || "-")}</td>
          <td>${escapeHtml(row.verfall || "-")}</td>
          <td>${escapeHtml(String(row.tage_bis_verfall ?? "-"))}</td>
          <td>${escapeHtml(formatVerfallKategorieLabel(row.kategorie))}</td>
        `;
        dashboardExpiryBody.appendChild(tr);
      }
    }
  }
}

function refreshVerfallSelectionOptions() {
  if (!(verfallPerspective instanceof HTMLSelectElement) || !(verfallIdsSelect instanceof HTMLSelectElement)) return;
  if (verfallPerspective.value === "depot") {
    fillMultiSelect(verfallIdsSelect, reportMasterDepots);
  } else {
    fillMultiSelect(verfallIdsSelect, reportMasterPraeparate);
  }
}

function renderVerfallRows(rows) {
  if (!verfallTableBody) return;
  verfallTableBody.innerHTML = "";
  if (!rows.length) {
    renderEmptyTableState(verfallTableBody, 8, "Keine Verfallspositionen fuer diese Filter.");
    return;
  }
  for (const row of rows) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${escapeHtml(String(row.id ?? ""))}</td>
      <td>${escapeHtml(row.depot || "")}</td>
      <td>${escapeHtml(row.praeparat || "")}</td>
      <td>${escapeHtml(row.charge || "")}</td>
      <td>${escapeHtml(row.verfall || "")}</td>
      <td>${escapeHtml(String(row.tage_bis_verfall ?? ""))}</td>
      <td>${escapeHtml(formatVerfallKategorieLabel(row.kategorie))}</td>
      <td>${escapeHtml(String(row.anzahl ?? ""))}</td>
    `;
    verfallTableBody.appendChild(tr);
  }
}

function renderVerfallStats(stats) {
  if (verfallStatKritisch) verfallStatKritisch.textContent = String(stats?.kritisch ?? 0);
  if (verfallStatWarnung) verfallStatWarnung.textContent = String(stats?.warnung ?? 0);
  if (verfallStatAchtung) verfallStatAchtung.textContent = String(stats?.achtung ?? 0);
  if (verfallStatGesamtmenge) verfallStatGesamtmenge.textContent = String(stats?.gesamt_menge ?? 0);
}

function notificationRowKey(row) {
  if (!row || typeof row !== "object") return "";
  const id = row.id ?? "";
  const verfall = row.verfall ?? "";
  const depot = row.depot ?? "";
  const praeparat = row.praeparat ?? "";
  return `${id}|${depot}|${praeparat}|${verfall}`;
}

function renderNotificationList(rows, options = {}) {
  const replace = Boolean(options.replace);
  const incomingRows = Array.isArray(rows) ? rows : [];
  if (replace) {
    lastNotificationRows = incomingRows;
  } else {
    const merged = [];
    const seen = new Set();
    for (const row of [...incomingRows, ...lastNotificationRows]) {
      const key = notificationRowKey(row);
      if (!key || seen.has(key)) continue;
      seen.add(key);
      merged.push(row);
    }
    lastNotificationRows = merged.slice(0, 50);
  }
  if (notificationList) {
    notificationList.innerHTML = "";
    if (!lastNotificationRows.length) {
      const li = document.createElement("li");
      li.className = "empty-cell";
      li.textContent = "Keine neuen kritischen Hinweise.";
      notificationList.appendChild(li);
    } else {
      for (const row of lastNotificationRows) {
        const li = document.createElement("li");
        li.textContent = `${row.depot} / ${row.praeparat} - ${row.verfall} (${row.tage_bis_verfall} Tage)`;
        notificationList.appendChild(li);
      }
    }
  }
  if (notificationCount) {
    notificationCount.textContent = String(lastNotificationRows.length);
  }
}

function fillMultiSelect(select, rows, labelKey = "name") {
  if (!select) return;
  select.innerHTML = "";
  for (const row of rows) {
    const option = document.createElement("option");
    option.value = String(row.id);
    option.textContent = `${row[labelKey]} (#${row.id})`;
    select.appendChild(option);
  }
}

function getSelectedReportIds() {
  if (!reportIdsSelect) return [];
  const values = [];
  for (const option of reportIdsSelect.options) {
    if (option.selected) values.push(Number(option.value));
  }
  return values;
}

function refreshReportSelectionOptions() {
  if (!reportPerspective || !reportIdsSelect) return;
  if (reportPerspective.value === "depot") {
    fillMultiSelect(reportIdsSelect, reportMasterDepots);
  } else {
    fillMultiSelect(reportIdsSelect, reportMasterPraeparate);
  }
}

function renderReportTable(rows) {
  if (!reportTableHead || !reportTableBody) return;
  reportTableHead.innerHTML = "";
  reportTableBody.innerHTML = "";
  if (!rows || !rows.length) {
    renderEmptyTableState(reportTableBody, 1, "Keine Daten fuer die gewaehlte Auswertung.");
    return;
  }
  const keys = Object.keys(rows[0]);
  const headRow = document.createElement("tr");
  for (const key of keys) {
    const th = document.createElement("th");
    th.textContent = key;
    headRow.appendChild(th);
  }
  reportTableHead.appendChild(headRow);
  for (const row of rows) {
    const tr = document.createElement("tr");
    for (const key of keys) {
      const td = document.createElement("td");
      td.textContent = row[key] ?? "";
      tr.appendChild(td);
    }
    reportTableBody.appendChild(tr);
  }
  pulseElement(document.getElementById("report-table"));
}

function createChartCanvasCard(title, minHeight = 240) {
  if (!reportCharts) return null;
  const card = document.createElement("div");
  card.className = "chart-card";
  const titleEl = document.createElement("div");
  titleEl.className = "chart-title";
  titleEl.textContent = title;
  const canvas = document.createElement("canvas");
  canvas.className = "chart-canvas";
  canvas.height = minHeight;
  card.appendChild(titleEl);
  card.appendChild(canvas);
  reportCharts.appendChild(card);
  return canvas;
}

function drawGroupedBars(canvas, labels, seriesList, options = {}) {
  if (!(canvas instanceof HTMLCanvasElement)) return;
  const cssWidth = Math.max(320, canvas.clientWidth || 320);
  canvas.width = cssWidth;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  const width = canvas.width;
  const height = canvas.height;
  ctx.clearRect(0, 0, width, height);
  if (!labels.length || !seriesList.length) return;

  const allValues = [];
  for (const series of seriesList) {
    allValues.push(...series.values.map((value) => Number(value || 0)));
  }
  const minValue = Math.min(0, ...allValues);
  const maxValue = Math.max(0, ...allValues);
  const range = Math.max(1, maxValue - minValue);
  const left = 52;
  const right = 14;
  const top = 20;
  const bottom = 50;
  const plotWidth = width - left - right;
  const plotHeight = height - top - bottom;
  const zeroY = top + ((maxValue / range) * plotHeight);
  const groupWidth = plotWidth / labels.length;
  const innerWidth = Math.max(8, groupWidth * 0.84);
  const barWidth = Math.max(4, innerWidth / seriesList.length - 2);
  const numberFormatter = options.numberFormatter || ((value) => `${Math.round(value)}`);

  // Grid lines and y-axis labels
  const yTicks = 5;
  ctx.strokeStyle = CHART_THEME.grid;
  ctx.fillStyle = CHART_THEME.muted;
  ctx.font = "10px Inter, Arial, sans-serif";
  for (let tick = 0; tick <= yTicks; tick += 1) {
    const value = maxValue - (tick / yTicks) * range;
    const y = top + (tick / yTicks) * plotHeight;
    ctx.beginPath();
    ctx.moveTo(left, y);
    ctx.lineTo(width - right, y);
    ctx.stroke();
    ctx.fillText(numberFormatter(value), 4, y + 3);
  }

  ctx.strokeStyle = CHART_THEME.axis;
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(left, top);
  ctx.lineTo(left, height - bottom);
  ctx.lineTo(width - right, height - bottom);
  ctx.stroke();

  ctx.strokeStyle = CHART_THEME.grid;
  ctx.beginPath();
  ctx.moveTo(left, zeroY);
  ctx.lineTo(width - right, zeroY);
  ctx.stroke();

  for (let idx = 0; idx < labels.length; idx += 1) {
    const xStart = left + idx * groupWidth + (groupWidth - innerWidth) / 2;
    for (let sIdx = 0; sIdx < seriesList.length; sIdx += 1) {
      const series = seriesList[sIdx];
      const value = Number(series.values[idx] || 0);
      const barHeight = (Math.abs(value) / range) * plotHeight;
      const x = xStart + sIdx * (barWidth + 2);
      const y = value >= 0 ? zeroY - barHeight : zeroY;
      ctx.fillStyle = series.color;
      ctx.fillRect(x, y, barWidth, Math.max(1, barHeight));

      if (barHeight > 14) {
        ctx.fillStyle = CHART_THEME.text;
        ctx.font = "10px Inter, Arial, sans-serif";
        const valueText = numberFormatter(value);
        const tx = x + Math.max(0, barWidth / 2 - Math.min(14, valueText.length * 2));
        const ty = value >= 0 ? y - 3 : y + barHeight + 11;
        ctx.fillText(valueText, tx, ty);
      }
    }
  }

  ctx.fillStyle = CHART_THEME.text;
  ctx.font = "10px Inter, Arial, sans-serif";
  const labelStep = labels.length > 16 ? 2 : 1;
  for (let idx = 0; idx < labels.length; idx += labelStep) {
    const xCenter = left + idx * groupWidth + groupWidth / 2;
    const shortLabel = String(labels[idx]).slice(0, 12);
    ctx.fillText(shortLabel, xCenter - 18, height - bottom + 14);
  }

  if (options.showLegend !== false && seriesList.length > 1) {
    let legendX = left;
    const legendY = 10;
    for (const series of seriesList) {
      ctx.fillStyle = series.color;
      ctx.fillRect(legendX, legendY, 10, 10);
      ctx.fillStyle = CHART_THEME.text;
      ctx.font = "11px Inter, Arial, sans-serif";
      ctx.fillText(series.label, legendX + 14, legendY + 9);
      legendX += 14 + Math.min(90, series.label.length * 7);
    }
  }
}

function drawHorizontalBars(canvas, labels, values, options = {}) {
  if (!(canvas instanceof HTMLCanvasElement)) return;
  const cssWidth = Math.max(320, canvas.clientWidth || 320);
  canvas.width = cssWidth;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  const width = canvas.width;
  const height = canvas.height;
  ctx.clearRect(0, 0, width, height);
  if (!labels.length || !values.length) return;

  const left = 146;
  const right = 18;
  const top = 18;
  const bottom = 22;
  const plotWidth = width - left - right;
  const plotHeight = height - top - bottom;
  const rowHeight = plotHeight / labels.length;
  const maxValue = Math.max(1, ...values.map((value) => Number(value || 0)));
  const barHeight = Math.max(10, rowHeight * 0.62);

  ctx.strokeStyle = CHART_THEME.axis;
  ctx.beginPath();
  ctx.moveTo(left, top);
  ctx.lineTo(left, height - bottom);
  ctx.stroke();

  ctx.fillStyle = CHART_THEME.text;
  ctx.font = "11px Inter, Arial, sans-serif";

  for (let idx = 0; idx < labels.length; idx += 1) {
    const yCenter = top + idx * rowHeight + rowHeight / 2;
    const y = yCenter - barHeight / 2;
    const value = Number(values[idx] || 0);
    const widthFactor = value / maxValue;
    const w = Math.max(1, widthFactor * plotWidth);

    ctx.fillStyle = options.color || CHART_THEME.purple;
    ctx.fillRect(left, y, w, barHeight);

    ctx.fillStyle = CHART_THEME.text;
    const label = String(labels[idx]).slice(0, 24);
    ctx.fillText(label, 6, yCenter + 4);
    ctx.fillText(`${Math.round(value)}`, left + w + 6, yCenter + 4);
  }
}

function drawLineAreaChart(canvas, labels, values, options = {}) {
  if (!(canvas instanceof HTMLCanvasElement)) return;
  const cssWidth = Math.max(320, canvas.clientWidth || 320);
  canvas.width = cssWidth;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  const width = canvas.width;
  const height = canvas.height;
  ctx.clearRect(0, 0, width, height);
  if (!labels.length || !values.length) return;

  const left = 50;
  const right = 12;
  const top = 18;
  const bottom = 40;
  const plotWidth = width - left - right;
  const plotHeight = height - top - bottom;
  const maxValue = Math.max(1, ...values.map((value) => Number(value || 0)));
  const minValue = 0;
  const range = Math.max(1, maxValue - minValue);

  const points = values.map((value, idx) => {
    const x = left + (idx / Math.max(1, values.length - 1)) * plotWidth;
    const normalized = (Number(value || 0) - minValue) / range;
    const y = top + (1 - normalized) * plotHeight;
    return { x, y, value: Number(value || 0) };
  });

  ctx.strokeStyle = CHART_THEME.grid;
  for (let i = 0; i <= 4; i += 1) {
    const y = top + (i / 4) * plotHeight;
    ctx.beginPath();
    ctx.moveTo(left, y);
    ctx.lineTo(width - right, y);
    ctx.stroke();
  }

  ctx.strokeStyle = options.lineColor || CHART_THEME.neutral;
  ctx.lineWidth = 2;
  ctx.beginPath();
  points.forEach((point, idx) => {
    if (idx === 0) ctx.moveTo(point.x, point.y);
    else ctx.lineTo(point.x, point.y);
  });
  ctx.stroke();

  ctx.fillStyle = options.fillColor || "rgba(37, 99, 235, 0.2)";
  ctx.beginPath();
  points.forEach((point, idx) => {
    if (idx === 0) ctx.moveTo(point.x, point.y);
    else ctx.lineTo(point.x, point.y);
  });
  ctx.lineTo(points[points.length - 1].x, top + plotHeight);
  ctx.lineTo(points[0].x, top + plotHeight);
  ctx.closePath();
  ctx.fill();

  ctx.fillStyle = options.lineColor || CHART_THEME.neutral;
  for (const point of points) {
    ctx.beginPath();
    ctx.arc(point.x, point.y, 3, 0, Math.PI * 2);
    ctx.fill();
  }

  ctx.fillStyle = CHART_THEME.text;
  ctx.font = "10px Inter, Arial, sans-serif";
  const labelStep = labels.length > 16 ? 2 : 1;
  for (let idx = 0; idx < labels.length; idx += labelStep) {
    const x = left + (idx / Math.max(1, labels.length - 1)) * plotWidth;
    const label = String(labels[idx]).slice(0, 10);
    ctx.fillText(label, x - 14, height - 20);
  }
}

function renderReportCharts(rows) {
  if (!reportCharts) return;
  reportCharts.innerHTML = "";
  if (reportChartLegend) {
    reportChartLegend.textContent = "";
  }
  if (!rows || !rows.length) return;

  const typ = reportType?.value || "bewegungen";
  if (typ === "bewegungen") {
    const monthMap = new Map();
    const actorMap = new Map();
    for (const row of rows) {
      const monat = row.monat || "Unbekannt";
      if (!monthMap.has(monat)) {
        monthMap.set(monat, { Zugang: 0, Abgang: 0, Vernichtung: 0 });
      }
      monthMap.get(monat)[row.typ] = (monthMap.get(monat)[row.typ] || 0) + Number(row.anzahl || 0);
      const actor = reportPerspective?.value === "depot" ? row.praeparat : row.depot;
      actorMap.set(actor, (actorMap.get(actor) || 0) + Number(row.anzahl || 0));
    }
    const months = Array.from(monthMap.keys()).sort().slice(-12);
    const series = [
      { label: "Zugang", color: CHART_THEME.positive, values: months.map((m) => monthMap.get(m).Zugang || 0) },
      { label: "Abgang", color: CHART_THEME.neutral, values: months.map((m) => monthMap.get(m).Abgang || 0) },
      { label: "Vernichtung", color: CHART_THEME.negative, values: months.map((m) => monthMap.get(m).Vernichtung || 0) },
    ];
    const monthlyCanvas = createChartCanvasCard("Monatlicher Bewegungsverlauf");
    drawGroupedBars(monthlyCanvas, months, series, {
      numberFormatter: (value) => `${Math.round(value)}`,
      showLegend: true,
    });

    const topActors = Array.from(actorMap.entries()).sort((a, b) => b[1] - a[1]).slice(0, 10);
    const actorCanvas = createChartCanvasCard(`Top ${reportPerspective?.value === "depot" ? "Praeparate" : "Depots"}`);
    drawGroupedBars(
      actorCanvas,
      topActors.map((entry) => entry[0]),
      [{ label: "Anzahl", color: CHART_THEME.purple, values: topActors.map((entry) => entry[1]) }],
      { showLegend: false },
    );
    if (reportChartLegend) {
      reportChartLegend.textContent = "Farben: Zugang (gruen), Abgang (blau), Vernichtung (rot).";
    }
    return;
  }

  if (typ === "bestand") {
    const subset = rows
      .slice()
      .sort((a, b) => Math.abs(Number(b.differenz || 0)) - Math.abs(Number(a.differenz || 0)))
      .slice(0, 14);
    const labels = subset.map((row) => `${row.depot}/${row.praeparat}`.slice(0, 18));
    const balanceCanvas = createChartCanvasCard("Soll vs. Ist");
    drawGroupedBars(balanceCanvas, labels, [
      { label: "Soll", color: "#3b82f6", values: subset.map((row) => Number(row.sollbestand || 0)) },
      { label: "Ist", color: CHART_THEME.positive, values: subset.map((row) => Number(row.ist_bestand || 0)) },
    ], { showLegend: true });
    const diffCanvas = createChartCanvasCard("Differenz je Position");
    drawGroupedBars(diffCanvas, labels, [
      {
        label: "Differenz",
        color: CHART_THEME.negative,
        values: subset.map((row) => Number(row.differenz || 0)),
      },
    ], { showLegend: false });
    if (reportChartLegend) {
      reportChartLegend.textContent = "Soll/Ist-Vergleich und Abweichung je Depot-Praeparat-Kombination.";
    }
    return;
  }

  if (typ === "ranking") {
    const labels = rows.map((row) => row.name).slice(0, 12);
    const values = rows.map((row) => Number(row.anzahl || 0)).slice(0, 12);
    const rankingCanvas = createChartCanvasCard("Top Ranking (Horizontal)", 300);
    drawHorizontalBars(rankingCanvas, labels, values, { color: CHART_THEME.purple });
    if (reportChartLegend) {
      reportChartLegend.textContent = "Ranking nach Abgaengen/Vernichtungen.";
    }
    return;
  }

  if (typ === "matrix") {
    const byDepot = new Map();
    for (const row of rows) {
      byDepot.set(row.depot, (byDepot.get(row.depot) || 0) + Number(row.differenz || 0));
    }
    const depotEntries = Array.from(byDepot.entries()).slice(0, 12);
    const matrixCanvas = createChartCanvasCard("Matrix-Abweichung je Depot");
    drawGroupedBars(
      matrixCanvas,
      depotEntries.map((entry) => entry[0]),
      [{ label: "Differenz", color: "#ef4444", values: depotEntries.map((entry) => entry[1]) }],
      { showLegend: false },
    );
    if (reportChartLegend) {
      reportChartLegend.textContent = "Positive Werte = Ueberschuss, negative Werte = Fehlbestand.";
    }
    return;
  }

  if (typ === "verfall") {
    const labels = rows.slice(0, 18).map((row) => row.verfall_monat);
    const values = rows.slice(0, 18).map((row) => Number(row.anzahl || 0));
    const cumulative = [];
    let running = 0;
    for (const value of values) {
      running += value;
      cumulative.push(running);
    }
    const monthCanvas = createChartCanvasCard("Verfall pro Monat");
    drawGroupedBars(monthCanvas, labels, [{ label: "Anzahl", color: CHART_THEME.orange, values }]);
    const cumulativeCanvas = createChartCanvasCard("Kumulierte Verfallsmenge (Linie/Flaeche)");
    drawLineAreaChart(cumulativeCanvas, labels, cumulative, {
      lineColor: "#2563eb",
      fillColor: "rgba(37, 99, 235, 0.2)",
    });
    if (reportChartLegend) {
      reportChartLegend.textContent = "Verfallsvorschau monatlich und kumuliert.";
    }
  }
}

function createBlobUrlFromResponse(response, blob) {
  const contentType = response.headers.get("content-type") || "application/pdf";
  return URL.createObjectURL(new Blob([blob], { type: contentType }));
}

async function openAttachment(bewegungId) {
  const response = await apiFetch(`/bewegungen/${bewegungId}/attachment`);
  const blob = await response.blob();
  const blobUrl = createBlobUrlFromResponse(response, blob);
  window.open(blobUrl, "_blank", "noopener,noreferrer");
  setTimeout(() => URL.revokeObjectURL(blobUrl), 10000);
}

async function downloadAttachment(bewegungId, filename) {
  const response = await apiFetch(`/bewegungen/${bewegungId}/attachment?download=true`);
  const blob = await response.blob();
  const blobUrl = createBlobUrlFromResponse(response, blob);
  const link = document.createElement("a");
  link.href = blobUrl;
  link.download = filename || `bewegung_${bewegungId}.pdf`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(blobUrl), 10000);
}

function renderAuditLogs(rows) {
  if (!auditBody) return;
  auditBody.innerHTML = "";
  if (!rows.length) {
    renderEmptyTableState(auditBody, 6, "Keine Audit-Eintraege fuer die aktuelle Filterung.");
    pulseElement(document.getElementById("audit-table"));
    return;
  }
  for (const row of rows) {
    const tr = document.createElement("tr");
    const action = row.action || "";
    const actionClass = getAuditActionClass(action);
    const detailsText = formatAuditDetails(row.details);
    tr.innerHTML = `
      <td>${row.timestamp || ""}</td>
      <td>${row.username || ""}</td>
      <td><span class="audit-badge ${actionClass}">${action}</span></td>
      <td>${row.resource_type || ""}</td>
      <td>${row.resource_id || ""}</td>
      <td><pre class="audit-details">${escapeHtml(detailsText)}</pre></td>
    `;
    auditBody.appendChild(tr);
  }
  pulseElement(document.getElementById("audit-table"));
}

function renderImportPreview(rows) {
  if (!importPreviewHead || !importPreviewBody) return;
  importPreviewHead.innerHTML = "";
  importPreviewBody.innerHTML = "";
  if (!rows.length) {
    renderEmptyTableState(importPreviewBody, 1, "Keine Vorschauzeilen vorhanden.");
    return;
  }
  const columns = Object.keys(rows[0]);
  const headRow = document.createElement("tr");
  for (const col of columns) {
    const th = document.createElement("th");
    th.textContent = col;
    headRow.appendChild(th);
  }
  importPreviewHead.appendChild(headRow);
  for (const row of rows) {
    const tr = document.createElement("tr");
    for (const col of columns) {
      const td = document.createElement("td");
      td.textContent = row[col] ?? "";
      tr.appendChild(td);
    }
    importPreviewBody.appendChild(tr);
  }
  pulseElement(document.getElementById("import-preview-table"));
}

function clearUsersForm() {
  document.getElementById("users-id").value = "";
  document.getElementById("users-username").value = "";
  document.getElementById("users-role").value = "User";
  document.getElementById("users-email").value = "";
  document.getElementById("users-active").checked = true;
  document.getElementById("users-password").value = "";
  document.getElementById("users-reset-password").value = "";
  if (usersPermissionsSelect) {
    for (const option of usersPermissionsSelect.options) {
      option.selected = false;
    }
  }
  if (usersPermissionTemplateSelect) {
    usersPermissionTemplateSelect.value = "";
  }
  syncUsersPermissionsUiState();
  markFormSaved(usersForm);
}

function renderUsers(rows) {
  if (!usersTableBody) return;
  usersTableBody.innerHTML = "";
  if (!rows.length) {
    renderEmptyTableState(usersTableBody, 10, "Keine Benutzer vorhanden.");
    pulseElement(document.getElementById("users-table"));
    return;
  }
  for (const row of rows) {
    const tr = document.createElement("tr");
    const permissionList = Array.isArray(row.permissions) ? row.permissions : [];
    tr.dataset.id = String(row.id);
    tr.dataset.username = row.username || "";
    tr.dataset.role = row.role || "User";
    tr.dataset.email = row.email || "";
    tr.dataset.active = row.is_active ? "1" : "0";
    tr.dataset.permissions = JSON.stringify(permissionList);
    tr.innerHTML = `
      <td>${row.id}</td>
      <td>${escapeHtml(row.username || "")}</td>
      <td>${escapeHtml(row.role || "")}</td>
      <td>${escapeHtml(row.email || "")}</td>
      <td>${row.is_active ? "Ja" : "Nein"}</td>
      <td>${escapeHtml(permissionList.join(", ") || "-")}</td>
      <td>${row.failed_attempts || 0}</td>
      <td>${escapeHtml(row.locked_until || "-")}</td>
      <td>${row.is_default_password ? "Ja" : "Nein"}</td>
      <td>${escapeHtml(row.last_login || "-")}</td>
    `;
    usersTableBody.appendChild(tr);
  }
  pulseElement(document.getElementById("users-table"));
}

function renderActivityRows(targetBody, rows) {
  if (!targetBody) return;
  targetBody.innerHTML = "";
  if (!rows.length) {
    renderEmptyTableState(targetBody, 3, "Keine Aktivitaeten vorhanden.");
    return;
  }
  for (const row of rows) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${escapeHtml(row.timestamp || "")}</td>
      <td>${escapeHtml(row.action || "")}</td>
      <td>${escapeHtml(row.details || "")}</td>
    `;
    targetBody.appendChild(tr);
  }
}

function formatBytes(sizeBytes) {
  const value = Number(sizeBytes || 0);
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(2)} MB`;
}

function renderBackupRows(rows) {
  if (!backupTableBody) return;
  backupTableBody.innerHTML = "";
  if (!rows.length) {
    renderEmptyTableState(backupTableBody, 4, "Noch keine Backups vorhanden.");
    return;
  }
  for (const row of rows) {
    const tr = document.createElement("tr");
    tr.dataset.filename = row.filename || "";
    tr.innerHTML = `
      <td>${escapeHtml(row.filename || "")}</td>
      <td>${escapeHtml(row.created_at || "")}</td>
      <td>${formatBytes(row.size_bytes)}</td>
      <td><button type="button" data-action="download-backup">Download</button></td>
    `;
    backupTableBody.appendChild(tr);
  }
}

function renderPermissionCatalog() {
  if (!usersPermissionsSelect) return;
  usersPermissionsSelect.innerHTML = "";
  for (const item of permissionCatalog) {
    const option = document.createElement("option");
    option.value = item.key;
    option.textContent = item.label || item.key;
    usersPermissionsSelect.appendChild(option);
  }
}

function renderPermissionTemplates() {
  if (!usersPermissionTemplateSelect) return;
  usersPermissionTemplateSelect.innerHTML = '<option value="">Vorlage waehlen</option>';
  for (const item of permissionTemplates) {
    const option = document.createElement("option");
    option.value = item.key;
    option.textContent = item.label || item.key;
    usersPermissionTemplateSelect.appendChild(option);
  }
}

function setSelectedPermissions(permissionKeys) {
  if (!usersPermissionsSelect) return;
  const selected = new Set(Array.isArray(permissionKeys) ? permissionKeys : []);
  for (const option of usersPermissionsSelect.options) {
    option.selected = selected.has(option.value);
  }
}

function syncUsersPermissionsUiState() {
  const role = document.getElementById("users-role")?.value || "User";
  const isAdmin = role === "Admin";
  if (usersPermissionsSelect) usersPermissionsSelect.disabled = isAdmin;
  if (usersPermissionTemplateSelect) usersPermissionTemplateSelect.disabled = isAdmin;
  if (usersApplyTemplateButton) usersApplyTemplateButton.disabled = isAdmin;
  if (isAdmin && usersPermissionsSelect) {
    for (const option of usersPermissionsSelect.options) option.selected = true;
  }
}

async function loadPermissionCatalog() {
  if (!hasPermission("users_manage")) {
    permissionCatalog = [];
    permissionTemplates = [];
    renderPermissionCatalog();
    renderPermissionTemplates();
    return;
  }
  const data = await (await apiFetch("/permissions/catalog")).json();
  permissionCatalog = Array.isArray(data.rows) ? data.rows : [];
  permissionTemplates = Array.isArray(data.templates) ? data.templates : [];
  renderPermissionCatalog();
  renderPermissionTemplates();
  syncUsersPermissionsUiState();
}

async function loadBackupList() {
  if (!isAdminUser() || !hasPermission("backup_manage")) return;
  const data = await (await apiFetch("/admin/backup/list?limit=200")).json();
  renderBackupRows(data.rows || []);
}

async function downloadBackupByFilename(filename) {
  const safeName = String(filename || "").trim();
  if (!safeName) throw new Error("Dateiname fehlt.");
  const response = await apiFetch(`/admin/backup/download/${encodeURIComponent(safeName)}`);
  const blob = await response.blob();
  const blobUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = blobUrl;
  link.download = safeName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(blobUrl), 10000);
}

async function loadUsers() {
  if (!isAdminUser() || !hasPermission("users_manage")) return;
  const rows = await (await apiFetch("/users")).json();
  renderUsers(rows);
}

async function loadCurrentUserActivity() {
  const rows = await (await apiFetch("/auth/activity?limit=50")).json();
  renderActivityRows(accountActivityBody, rows);
}

async function loadCurrentAvatar() {
  if (!accountAvatarImage || !accountAvatarEmpty) return;
  if (!avatarAvailable) {
    accountAvatarImage.classList.add("hidden");
    accountAvatarEmpty.classList.remove("hidden");
    accountAvatarImage.removeAttribute("src");
    updateHeaderAccountPill(currentUsername || "", "");
    return;
  }
  const token = getToken();
  if (!token) {
    accountAvatarImage.classList.add("hidden");
    accountAvatarEmpty.classList.remove("hidden");
    updateHeaderAccountPill(currentUsername || "", "");
    return;
  }
  const response = await fetch("/auth/avatar", {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (response.status === 404) {
    avatarAvailable = false;
    accountAvatarImage.classList.add("hidden");
    accountAvatarEmpty.classList.remove("hidden");
    accountAvatarImage.removeAttribute("src");
    updateHeaderAccountPill(currentUsername || "", "");
    return;
  }
  if (!response.ok) {
    throw new Error("Profilbild konnte nicht geladen werden.");
  }
  const blob = await response.blob();
  const blobUrl = URL.createObjectURL(blob);
  accountAvatarImage.src = blobUrl;
  accountAvatarImage.classList.remove("hidden");
  accountAvatarEmpty.classList.add("hidden");
  updateHeaderAccountPill(currentUsername || "", blobUrl);
  window.setTimeout(() => URL.revokeObjectURL(blobUrl), 15000);
}

async function loadSelectedUserActivity(userId) {
  if (!userId || !isAdminUser() || !hasPermission("users_manage")) return;
  const rows = await (await apiFetch(`/users/${Number(userId)}/activity?limit=100`)).json();
  renderActivityRows(usersActivityBody, rows);
}

async function saveUserFromForm() {
  const userId = document.getElementById("users-id").value.trim();
  const username = document.getElementById("users-username").value.trim();
  const role = document.getElementById("users-role").value;
  const email = document.getElementById("users-email").value.trim();
  const isActive = document.getElementById("users-active").checked;
  const password = document.getElementById("users-password").value;
  const permissions = usersPermissionsSelect
    ? Array.from(usersPermissionsSelect.selectedOptions).map((option) => option.value)
    : [];
  if (!username) {
    throw new Error("Bitte Benutzername angeben.");
  }
  if (!userId && !password) {
    throw new Error("Bitte Passwort fuer den neuen Benutzer angeben.");
  }
  if (!userId && password) {
    validatePasswordPolicy(password, "Passwort fuer neuen Benutzer");
  }
  if (email && !email.includes("@")) {
    throw new Error("Bitte eine gueltige E-Mail-Adresse eingeben.");
  }
  if (userId) {
    await apiFetch(`/users/${Number(userId)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username,
        role,
        email: email || null,
        is_active: isActive,
        permissions,
      }),
    });
    return "Benutzer aktualisiert.";
  }
  await apiFetch("/users", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      username,
      password,
      role,
      email: email || null,
      is_active: isActive,
      permissions,
    }),
  });
  return "Benutzer erstellt.";
}

async function resetSelectedUserPassword() {
  const userId = document.getElementById("users-id").value.trim();
  const newPassword = document.getElementById("users-reset-password").value;
  if (!userId) {
    throw new Error("Bitte zuerst einen Benutzer auswaehlen.");
  }
  validatePasswordPolicy(newPassword, "Neues Passwort");
  await apiFetch(`/users/${Number(userId)}/reset-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ new_password: newPassword }),
  });
}

function getAuditActionClass(action) {
  if (action === "create") return "audit-badge-create";
  if (action === "update") return "audit-badge-update";
  if (action === "delete") return "audit-badge-delete";
  return "";
}

function formatAuditDetails(details) {
  if (!details) return "{}";
  try {
    const parsed = typeof details === "string" ? JSON.parse(details) : details;
    return JSON.stringify(parsed, null, 2);
  } catch (_error) {
    return String(details);
  }
}

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

async function loadMasterData() {
  const depots = await (await apiFetch(
    `/depots?limit=${PAGE_SIZE}&offset=${depotOffset}&q=${encodeURIComponent(depotSearch.value.trim())}`,
  )).json();
  const praeparate = await (await apiFetch(
    `/praeparate?limit=${PAGE_SIZE}&offset=${praeparatOffset}&q=${encodeURIComponent(praeparatSearch.value.trim())}`,
  )).json();
  const depotsForReports = await (await apiFetch("/depots?limit=500&offset=0&q=")).json();
  const praeparateForReports = await (await apiFetch("/praeparate?limit=500&offset=0&q=")).json();
  lastDepotCount = depots.length;
  lastPraeparatCount = praeparate.length;
  reportMasterDepots = depotsForReports;
  reportMasterPraeparate = praeparateForReports;
  depotNameById.clear();
  for (const row of depotsForReports) depotNameById.set(Number(row.id), row.name || String(row.id));
  praeparatNameById.clear();
  for (const row of praeparateForReports) praeparatNameById.set(Number(row.id), row.name || String(row.id));
  renderSimpleList(depotsList, depots);
  renderSimpleList(praeparateList, praeparate);
  fillSelect(depotSelect, depots, "name", { placeholder: "Depot waehlen" });
  if (assignmentDepot) fillSelect(assignmentDepot, depots, "name", { placeholder: "Depot waehlen" });
  if (kontaktDepot) fillSelect(kontaktDepot, depots, "name", { placeholder: "Depot waehlen" });
  renderEmailDepots(depots);
  refreshReportSelectionOptions();
  refreshVerfallSelectionOptions();
  if (depotSelect.value) {
    await refreshPraeparateForSelectedDepot();
  } else {
    fillSelect(praeparatSelect, praeparate, "name", { placeholder: "Praeparat waehlen" });
  }
  if (assignmentDepot?.value) {
    await loadAssignments();
  } else if (assignmentList) {
    assignmentList.innerHTML = "";
  }
  if (kontaktDepot?.value) {
    await loadKontakte();
  } else if (kontakteBody) {
    renderEmptyTableState(kontakteBody, 4, "Bitte zuerst ein Depot waehlen.");
  }
  await loadEmailHistory();
  if (depotPrev) depotPrev.disabled = depotOffset === 0;
  if (depotNext) depotNext.disabled = lastDepotCount < PAGE_SIZE;
  if (praeparatPrev) praeparatPrev.disabled = praeparatOffset === 0;
  if (praeparatNext) praeparatNext.disabled = lastPraeparatCount < PAGE_SIZE;
}

async function loadBewegungen() {
  const bewegungenRaw = await (await apiFetch(
    `/bewegungen?limit=${PAGE_SIZE}&offset=${bewegungOffset}&q=${encodeURIComponent(bewegungSearch.value.trim())}&typ=${encodeURIComponent(bewegungFilterTyp.value)}`,
  )).json();
  const bewegungen = bewegungenRaw.map((row) => ({
    ...row,
    depot: depotNameById.get(Number(row.depot_id)) || row.depot_id,
    praeparat: praeparatNameById.get(Number(row.praeparat_id)) || row.praeparat_id,
  }));
  lastBewegungCount = bewegungen.length;
  renderBewegungen(bewegungen);
  if (bewegungPrev) bewegungPrev.disabled = bewegungOffset === 0;
  if (bewegungNext) bewegungNext.disabled = lastBewegungCount < PAGE_SIZE;
}

async function refreshPraeparateForSelectedDepot() {
  const depotId = Number(depotSelect.value);
  if (!depotId) {
    praeparatSelect.innerHTML = "";
    return;
  }
  const assignedPraeparate = await (await apiFetch(`/depots/${depotId}/praeparate`)).json();
  fillSelect(praeparatSelect, assignedPraeparate, "name", { placeholder: "Praeparat waehlen" });
}

async function loadAuditLogs() {
  if (!isAdminUser() || !hasPermission("audit_view") || !auditSection) {
    return;
  }
  const logs = await (await apiFetch(
    `/audit-logs?limit=${PAGE_SIZE}&offset=${auditOffset}&q=${encodeURIComponent(auditSearch.value.trim())}&action=${encodeURIComponent(auditFilterAction.value)}&resource_type=${encodeURIComponent(auditFilterResource.value)}`,
  )).json();
  lastAuditCount = logs.length;
  renderAuditLogs(logs);
  if (auditPrev) auditPrev.disabled = auditOffset === 0;
  if (auditNext) auditNext.disabled = lastAuditCount < PAGE_SIZE;
}

async function loadAssignments() {
  if (!assignmentDepot?.value) {
    if (assignmentList) assignmentList.innerHTML = "";
    return;
  }
  const depotId = Number(assignmentDepot.value);
  const rows = await (await apiFetch(`/depots/${depotId}/zuordnungen`)).json();
  renderAssignments(rows);
}

async function saveAssignments() {
  if (!assignmentDepot?.value) return;
  const depotId = Number(assignmentDepot.value);
  const assignments = [];
  for (const row of currentAssignmentRows) {
    const check = assignmentList.querySelector(`[data-assignment-check="${row.praeparat_id}"]`);
    const stock = assignmentList.querySelector(`[data-assignment-stock="${row.praeparat_id}"]`);
    if (!check?.checked) continue;
    assignments.push({
      praeparat_id: Number(row.praeparat_id),
      sollbestand: Number(stock?.value || 0),
    });
  }
  await apiFetch(`/depots/${depotId}/zuordnungen`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ assignments }),
  });
}

async function loadKontakte() {
  if (!kontaktDepot?.value) {
    if (kontakteBody) kontakteBody.innerHTML = "";
    return;
  }
  const depotId = Number(kontaktDepot.value);
  const rows = await (await apiFetch(`/depots/${depotId}/kontakte`)).json();
  renderKontakte(rows);
}

async function previewEmailRecipients() {
  const depotIds = getSelectedEmailDepotIds();
  const response = await apiFetch("/emails/recipients-preview", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ depot_ids: depotIds }),
  });
  return response.json();
}

async function createEmailDraft() {
  const depotIds = getSelectedEmailDepotIds();
  const payload = {
    depot_ids: depotIds,
    betreff: document.getElementById("email-subject").value.trim(),
    nachricht: document.getElementById("email-message").value,
  };
  const response = await apiFetch("/emails/drafts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return response.json();
}

async function loadEmailHistory() {
  const rows = await (await apiFetch("/emails/history?limit=50")).json();
  renderEmailHistory(rows);
}

async function loadEmailHistoryDetail(emailId) {
  const detail = await (await apiFetch(`/emails/history/${emailId}`)).json();
  return detail;
}

async function loadDashboardOverview() {
  const data = await (await apiFetch("/dashboard/overview")).json();
  renderDashboardOverview(data);
  return data;
}

async function loadVerfallOverview() {
  const perspective = verfallPerspective?.value || "depot";
  const ids = getMultiSelectNumberValues(verfallIdsSelect);
  const params = new URLSearchParams({
    perspective,
    ids: ids.join(","),
    q: verfallSearch?.value?.trim() || "",
    category: verfallCategory?.value || "alle",
    limit: "200",
    offset: "0",
  });
  const data = await (await apiFetch(`/verfall/overview?${params.toString()}`)).json();
  renderVerfallRows(Array.isArray(data.rows) ? data.rows : []);
  renderVerfallStats(data.stats_page || {});
  return data;
}

async function exportVerfallOverviewCsv() {
  const perspective = verfallPerspective?.value || "depot";
  const ids = getMultiSelectNumberValues(verfallIdsSelect);
  const params = new URLSearchParams({
    perspective,
    ids: ids.join(","),
    q: verfallSearch?.value?.trim() || "",
    category: verfallCategory?.value || "alle",
  });
  const response = await apiFetch(`/verfall/overview/export.csv?${params.toString()}`);
  const blob = await response.blob();
  const blobUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = blobUrl;
  link.download = "verfall_manager.csv";
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(blobUrl), 10000);
}

async function pollVerfallNotifications() {
  if (!hasPermission("movements_read")) return;
  const params = new URLSearchParams({ limit: "20" });
  if (notificationSince) params.set("since", notificationSince);
  const data = await (await apiFetch(`/notifications/verfall?${params.toString()}`)).json();
  notificationSince = data.next_since || notificationSince;
  const rows = Array.isArray(data.rows) ? data.rows : [];
  renderNotificationList(rows);
  if (rows.length > 0) {
    showToast(`${rows.length} neue kritische Verfallshinweise`, "warning", 3600);
  }
}

function stopNotificationPolling() {
  if (notificationPollTimer) {
    window.clearInterval(notificationPollTimer);
    notificationPollTimer = null;
  }
}

function readIsoTimestampFromStorage(key) {
  const raw = localStorage.getItem(key);
  if (!raw) return null;
  const text = String(raw).trim();
  if (!text) return null;
  const parsed = Date.parse(text);
  if (Number.isNaN(parsed)) return null;
  return new Date(parsed).toISOString();
}

function startNotificationPolling(sinceIso = null) {
  stopNotificationPolling();
  notificationSince = sinceIso ? String(sinceIso).trim() : null;
  pollVerfallNotifications().catch((_error) => {
    // Notification polling must not block app usage.
  });
  notificationPollTimer = window.setInterval(() => {
    pollVerfallNotifications().catch((_error) => {
      // Ignore transient polling errors.
    });
  }, 5 * 60 * 1000);
}

async function loadReportData() {
  const ids = validateReportFilters();
  const perspective = reportPerspective?.value || "depot";
  const typ = reportType?.value || "bewegungen";
  const params = new URLSearchParams({
    perspective,
    ids: ids.join(","),
  });
  if (reportStartDate?.value) params.set("start_date", reportStartDate.value);
  if (reportEndDate?.value) params.set("end_date", reportEndDate.value);
  const response = await apiFetch(`/reports/${typ}?${params.toString()}`);
  return response.json();
}

async function exportReportCsv() {
  const ids = validateReportFilters();
  const perspective = reportPerspective?.value || "depot";
  const typ = reportType?.value || "bewegungen";
  const params = new URLSearchParams({
    perspective,
    ids: ids.join(","),
  });
  if (reportStartDate?.value) params.set("start_date", reportStartDate.value);
  if (reportEndDate?.value) params.set("end_date", reportEndDate.value);
  const response = await apiFetch(`/reports/${typ}/export.csv?${params.toString()}`);
  const blob = await response.blob();
  const blobUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = blobUrl;
  link.download = `${typ}.csv`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(blobUrl), 10000);
}

async function exportReportFile(extension) {
  const ids = validateReportFilters();
  const perspective = reportPerspective?.value || "depot";
  const typ = reportType?.value || "bewegungen";
  const params = new URLSearchParams({
    perspective,
    ids: ids.join(","),
  });
  if (reportStartDate?.value) params.set("start_date", reportStartDate.value);
  if (reportEndDate?.value) params.set("end_date", reportEndDate.value);
  const response = await apiFetch(`/reports/${typ}/export.${extension}?${params.toString()}`);
  const blob = await response.blob();
  const blobUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = blobUrl;
  link.download = `${typ}.${extension}`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(blobUrl), 10000);
}

async function previewImport() {
  const file = validateImportFileSelection();
  const formData = new FormData();
  formData.append("file", file, file.name);
  const response = await apiFetch("/imports/bewegungen/preview", {
    method: "POST",
    body: formData,
  });
  const data = await response.json();
  lastImportPreview = data;
  renderImportPreview(data.preview_rows || []);
  const hasErrors = (data.error_count || 0) > 0;
  if (importErrors) {
    if (hasErrors) {
      importErrors.classList.remove("hidden");
      importErrors.textContent = (data.errors || []).join("\n");
      activateInlineTab("import", "import-errors-panel", {
        hint: "Fehler gefunden - automatisch zum Fehler-Tab gewechselt.",
        level: "warning",
      });
    } else {
      importErrors.classList.add("hidden");
      importErrors.textContent = "";
      activateInlineTab("import", "import-upload-panel", {
        hint: "Vorschau ohne Fehler - Sie koennen den Import starten.",
        level: "success",
      });
    }
  }
  if (importExecuteButton) {
    importExecuteButton.disabled = (data.valid_rows || 0) === 0;
  }
  return data;
}

async function executeImport() {
  const file = validateImportFileSelection();
  const formData = new FormData();
  formData.append("file", file, file.name);
  const response = await apiFetch("/imports/bewegungen/execute", {
    method: "POST",
    body: formData,
  });
  return response.json();
}

async function afterLogin(options = {}) {
  const isFreshLogin = Boolean(options.isFreshLogin);
  const me = await (await apiFetch("/auth/me")).json();
  currentRole = me.role || null;
  currentUsername = me.username || null;
  avatarAvailable = Boolean(me.avatar_available);
  mustChangePassword = Boolean(me.requires_password_change);
  currentPermissions = new Set(Array.isArray(me.permissions) ? me.permissions : []);
  setAuthLocked(false);
  setAccountUiVisibility(true);
  applyPermissionVisibility();
  updateLoginPill(`Angemeldet: ${me.username} (${me.role || "-"})`, true);
  updateHeaderAccountPill(me.username || "", "");
  if (accountPasswordWarning) {
    accountPasswordWarning.classList.toggle("hidden", !mustChangePassword);
  }
  await loadPermissionCatalog();
  if (hasPermission("masterdata_read")) {
    await loadMasterData();
    if (hasPermission("movements_write")) {
      await applyBewegungAutofillFromLastInput();
    }
  }
  if (hasPermission("movements_read")) {
    let sinceForNotifications = null;
    if (isFreshLogin) {
      sinceForNotifications = readIsoTimestampFromStorage(LAST_LOGIN_AT_KEY);
      localStorage.setItem(LAST_LOGIN_AT_KEY, new Date().toISOString());
    }
    await loadDashboardOverview();
    await loadVerfallOverview();
    await loadBewegungen();
    startNotificationPolling(sinceForNotifications);
  } else {
    stopNotificationPolling();
  }
  if (isAdminUser() && hasPermission("audit_view")) {
    await loadAuditLogs();
  }
  await loadCurrentUserActivity();
  await loadCurrentAvatar();
  if (isAdminUser()) {
    await loadUsers();
    await loadBackupList();
  }
  if (mustChangePassword) {
    accountStatus.textContent = "Bitte zuerst Ihr Standard-Passwort aendern.";
    showPage("account-section");
  } else {
    showPage(getDefaultLandingPageId());
  }
}

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  loginStatus.textContent = "Anmeldung laeuft...";
  try {
    const username = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value;
    const response = await fetch("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    if (!response.ok) {
      let detail = "Login fehlgeschlagen.";
      try {
        const body = await response.json();
        if (body?.detail) detail = body.detail;
      } catch (_error) {
        // ignore parse errors
      }
      throw new Error(detail);
    }
    const data = await response.json();
    setToken(data.token);
    loginStatus.textContent = `Angemeldet als ${data.username} (${data.role || "-"})`;
    updateLoginPill(`Angemeldet: ${data.username} (${data.role || "-"})`, true);
    await afterLogin({ isFreshLogin: true });
  } catch (error) {
    removeToken();
    loginStatus.textContent = error.message;
    updateLoginPill("Login fehlgeschlagen", false);
    setAuthLocked(true);
    showPage("login-section");
  }
});

depotForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  depotStatus.textContent = "Speichere Depot...";
  try {
    const id = document.getElementById("depot-id").value.trim();
    const payload = {
      name: document.getElementById("depot-name").value.trim(),
      adresse: document.getElementById("depot-adresse").value.trim() || null,
      telefon: document.getElementById("depot-telefon").value.trim() || null,
      email: document.getElementById("depot-email").value.trim() || null,
    };
    const path = id ? `/depots/${id}` : "/depots";
    const method = id ? "PUT" : "POST";
    await apiFetch(path, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    setStatusWithNextStep(
      depotStatus,
      id ? "Depot aktualisiert." : "Depot erstellt.",
      "Zuordnungen oder Ansprechpartner pruefen",
    );
    markFormSaved(depotForm);
    await loadMasterData();
  } catch (error) {
    depotStatus.textContent = error.message;
  }
});

depotDeleteButton.addEventListener("click", async () => {
  const id = document.getElementById("depot-id").value.trim();
  if (!id) {
    depotStatus.textContent = "Bitte Depot-ID zum Loeschen auswaehlen.";
    return;
  }
  if (!window.confirm(`Depot #${id} wirklich loeschen?`)) {
    return;
  }
  depotStatus.textContent = "Loesche Depot...";
  try {
    await apiFetch(`/depots/${id}`, { method: "DELETE" });
    setStatusWithNextStep(depotStatus, "Depot geloescht.", "Depotliste pruefen oder neues Depot anlegen");
    depotForm.reset();
    markFormSaved(depotForm);
    await loadMasterData();
  } catch (error) {
    depotStatus.textContent = error.message;
  }
});

praeparatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  praeparatStatus.textContent = "Speichere Praeparat...";
  try {
    const id = document.getElementById("praeparat-id").value.trim();
    const payload = {
      name: document.getElementById("praeparat-name").value.trim(),
    };
    const path = id ? `/praeparate/${id}` : "/praeparate";
    const method = id ? "PUT" : "POST";
    await apiFetch(path, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    setStatusWithNextStep(
      praeparatStatus,
      id ? "Praeparat aktualisiert." : "Praeparat erstellt.",
      "Zuordnungen pruefen oder naechstes Praeparat bearbeiten",
    );
    markFormSaved(praeparatForm);
    await loadMasterData();
  } catch (error) {
    praeparatStatus.textContent = error.message;
  }
});

praeparatDeleteButton.addEventListener("click", async () => {
  const id = document.getElementById("praeparat-id").value.trim();
  if (!id) {
    praeparatStatus.textContent = "Bitte Praeparat-ID zum Loeschen auswaehlen.";
    return;
  }
  if (!window.confirm(`Praeparat #${id} wirklich loeschen?`)) {
    return;
  }
  praeparatStatus.textContent = "Loesche Praeparat...";
  try {
    await apiFetch(`/praeparate/${id}`, { method: "DELETE" });
    setStatusWithNextStep(
      praeparatStatus,
      "Praeparat geloescht.",
      "Praeparateliste pruefen oder neues Praeparat anlegen",
    );
    praeparatForm.reset();
    markFormSaved(praeparatForm);
    await loadMasterData();
  } catch (error) {
    praeparatStatus.textContent = error.message;
  }
});

bewegungForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!validateBewegungForm()) {
    setStatusWithNextStep(bewegungStatus, "Bitte Eingaben pruefen.", "Pflichtfelder korrigieren und erneut speichern");
    return;
  }
  bewegungStatus.textContent = "Speichere Bewegung...";
  try {
    const payload = {
      depot_id: Number(depotSelect.value),
      praeparat_id: Number(praeparatSelect.value),
      typ: document.getElementById("bewegung-typ").value,
      charge: document.getElementById("bewegung-charge").value.trim(),
      verfall: document.getElementById("bewegung-verfall").value.trim(),
      datum: document.getElementById("bewegung-datum").value.trim(),
      anzahl: Number(document.getElementById("bewegung-anzahl").value),
      empfaenger: document.getElementById("bewegung-empfaenger").value.trim() || null,
    };
    const response = await apiFetch("/bewegungen", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    const file = bewegungAttachment?.files?.[0];
    if (file) {
      if (!file.name.toLowerCase().endsWith(".pdf")) {
        throw new Error("Nur PDF-Dateien sind als Anhang erlaubt.");
      }
      const formData = new FormData();
      formData.append("file", file, file.name);
      await apiFetch(`/bewegungen/${data.id}/attachment`, {
        method: "POST",
        body: formData,
      });
      bewegungAttachment.value = "";
      setStatusWithNextStep(
        bewegungStatus,
        `Bewegung gespeichert (ID ${data.id}) inkl. PDF-Anhang.`,
        "Im Verlauf pruefen oder naechste Bewegung erfassen",
      );
    } else {
      setStatusWithNextStep(
        bewegungStatus,
        `Bewegung gespeichert (ID ${data.id}).`,
        "Im Verlauf pruefen oder naechste Bewegung erfassen",
      );
    }
    if (getBewegungAutofillEnabled()) {
      saveLastBewegungInput({
        depot_id: payload.depot_id,
        praeparat_id: payload.praeparat_id,
        typ: payload.typ,
        anzahl: payload.anzahl,
      });
    }
    markFormSaved(bewegungForm);
    await loadBewegungen();
  } catch (error) {
    bewegungStatus.textContent = error.message;
  }
});

depotSelect.addEventListener("change", async () => {
  try {
    await refreshPraeparateForSelectedDepot();
  } catch (error) {
    bewegungStatus.textContent = error.message;
  }
});

reloadButton.addEventListener("click", async () => {
  bewegungStatus.textContent = "Lade Bewegungen...";
  try {
    await loadBewegungen();
    bewegungStatus.textContent = "Bewegungen aktualisiert.";
  } catch (error) {
    bewegungStatus.textContent = error.message;
  }
});

if (auditSearch) {
  auditSearch.addEventListener("input", debounce(async () => {
    auditOffset = 0;
    await loadAuditLogs();
  }, 280));
}
if (auditFilterAction) {
  auditFilterAction.addEventListener("change", async () => {
    auditOffset = 0;
    await loadAuditLogs();
  });
}
if (auditFilterResource) {
  auditFilterResource.addEventListener("change", async () => {
    auditOffset = 0;
    await loadAuditLogs();
  });
}
if (auditReload) {
  auditReload.addEventListener("click", async () => {
    await loadAuditLogs();
  });
}
if (auditPrev) {
  auditPrev.addEventListener("click", async () => {
    auditOffset = Math.max(0, auditOffset - PAGE_SIZE);
    await loadAuditLogs();
  });
}
if (auditNext) {
  auditNext.addEventListener("click", async () => {
    if (lastAuditCount === PAGE_SIZE) {
      auditOffset += PAGE_SIZE;
      await loadAuditLogs();
    }
  });
}

depotSearch.addEventListener("input", debounce(async () => {
  depotOffset = 0;
  await loadMasterData();
}, 280));

praeparatSearch.addEventListener("input", debounce(async () => {
  praeparatOffset = 0;
  await loadMasterData();
}, 280));

bewegungSearch.addEventListener("input", debounce(async () => {
  bewegungOffset = 0;
  await loadBewegungen();
}, 280));

bewegungFilterTyp.addEventListener("change", async () => {
  bewegungOffset = 0;
  await loadBewegungen();
});

depotPrev.addEventListener("click", async () => {
  depotOffset = Math.max(0, depotOffset - PAGE_SIZE);
  await loadMasterData();
});

depotNext.addEventListener("click", async () => {
  if (lastDepotCount === PAGE_SIZE) {
    depotOffset += PAGE_SIZE;
    await loadMasterData();
  }
});

praeparatPrev.addEventListener("click", async () => {
  praeparatOffset = Math.max(0, praeparatOffset - PAGE_SIZE);
  await loadMasterData();
});

praeparatNext.addEventListener("click", async () => {
  if (lastPraeparatCount === PAGE_SIZE) {
    praeparatOffset += PAGE_SIZE;
    await loadMasterData();
  }
});

bewegungPrev.addEventListener("click", async () => {
  bewegungOffset = Math.max(0, bewegungOffset - PAGE_SIZE);
  await loadBewegungen();
});

bewegungNext.addEventListener("click", async () => {
  if (lastBewegungCount === PAGE_SIZE) {
    bewegungOffset += PAGE_SIZE;
    await loadBewegungen();
  }
});

bewegungenBody.addEventListener("click", async (event) => {
  const target = event.target;
  if (!(target instanceof HTMLElement)) {
    return;
  }
  const action = target.dataset.action;
  const id = Number(target.dataset.id);
  if (!action || !id) {
    return;
  }
  bewegungStatus.textContent = "Lade PDF-Anhang...";
  try {
    if (action === "open-attachment") {
      await openAttachment(id);
      bewegungStatus.textContent = "PDF-Anhang geoeffnet.";
      return;
    }
    if (action === "download-attachment") {
      await downloadAttachment(id);
      bewegungStatus.textContent = "PDF-Anhang heruntergeladen.";
    }
  } catch (error) {
    bewegungStatus.textContent = error.message;
  }
});

initializeTheme();
initializeSectionNavigation();
initializeInlineTabs();
initializeSubpageNavigation();
initializeBewegungFormUx();
initializeInputAssist();
initializeCardMotion();
enhanceActionButtons();
initializeRequiredFieldIndicators();
initializeFormDirtyTracking();
initializeFormValidationUx();
initializeMoreActionsDismiss();
initializeKeyboardShortcuts();
observeStatusFeedback();
updateLoginPill("Nicht angemeldet", false);
setAuthLocked(true);

if (themeToggle) {
  themeToggle.addEventListener("click", () => {
    const isDark = document.body.classList.contains("dark-mode");
    setTheme(isDark ? "light" : "dark");
  });
}

if (headerAccountButton) {
  headerAccountButton.addEventListener("click", (event) => {
    event.stopPropagation();
    toggleHeaderAccountMenu();
  });
}

if (notificationButton) {
  notificationButton.addEventListener("click", (event) => {
    event.stopPropagation();
    toggleNotificationMenu();
  });
}

if (headerAccountOpenButton) {
  headerAccountOpenButton.addEventListener("click", () => {
    closeHeaderAccountMenu();
    showPage("account-section");
  });
}

if (headerAccountAdminButton) {
  headerAccountAdminButton.addEventListener("click", () => {
    closeHeaderAccountMenu();
    showPage("settings-section");
  });
}

document.addEventListener("click", (event) => {
  const target = event.target;
  if (!(target instanceof Node)) return;
  if (headerAccountMenu && !headerAccountMenu.contains(target)) {
    closeHeaderAccountMenu();
  }
  if (notificationMenu && !notificationMenu.contains(target)) {
    closeNotificationMenu();
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeHeaderAccountMenu();
    closeNotificationMenu();
  }
});

if (getToken()) {
  loginStatus.textContent = "Token gefunden, lade Daten...";
  afterLogin({ isFreshLogin: false }).then(() => {
    loginStatus.textContent = "Bereit (Token aktiv).";
  }).catch((error) => {
    removeToken();
    setAuthLocked(true);
    loginStatus.textContent = `Bitte neu anmelden: ${error.message}`;
    updateLoginPill("Bitte neu anmelden", false);
    showPage("login-section");
  });
} else {
  showPage("login-section");
}

if (assignmentList) {
  assignmentList.addEventListener("change", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;
    const checkId = target.getAttribute("data-assignment-check");
    if (!checkId) return;
    const stockInput = assignmentList.querySelector(`[data-assignment-stock="${checkId}"]`);
    if (stockInput instanceof HTMLInputElement) {
      stockInput.disabled = !(target instanceof HTMLInputElement ? target.checked : false);
    }
  });
}

if (assignmentDepot) {
  assignmentDepot.addEventListener("change", async () => {
    try {
      await loadAssignments();
    } catch (error) {
      assignmentStatus.textContent = error.message;
    }
  });
}

if (assignmentSaveButton) {
  assignmentSaveButton.addEventListener("click", async () => {
    assignmentStatus.textContent = "Speichere Zuordnungen...";
    try {
      await saveAssignments();
      assignmentStatus.textContent = "Zuordnungen gespeichert.";
      await refreshPraeparateForSelectedDepot();
    } catch (error) {
      assignmentStatus.textContent = error.message;
    }
  });
}

if (kontaktDepot) {
  kontaktDepot.addEventListener("change", async () => {
    kontaktForm?.reset();
    document.getElementById("kontakt-id").value = "";
    if (kontakteBody) kontakteBody.querySelectorAll("tr").forEach((item) => item.classList.remove("active-row"));
    try {
      await loadKontakte();
    } catch (error) {
      kontaktStatus.textContent = error.message;
    }
  });
}

if (kontakteBody) {
  kontakteBody.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;
    const tr = target.closest("tr");
    if (!tr) return;
    kontakteBody.querySelectorAll("tr").forEach((item) => item.classList.remove("active-row"));
    tr.classList.add("active-row");
    document.getElementById("kontakt-id").value = tr.dataset.id || "";
    document.getElementById("kontakt-name").value = tr.dataset.name || "";
    document.getElementById("kontakt-rolle").value = tr.dataset.rolle || "";
    document.getElementById("kontakt-telefon").value = tr.dataset.telefon || "";
    document.getElementById("kontakt-email").value = tr.dataset.email || "";
  });
}

if (kontaktForm) {
  kontaktForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!kontaktDepot?.value) return;
    kontaktStatus.textContent = "Speichere Kontakt...";
    const kontaktId = document.getElementById("kontakt-id").value.trim();
    const payload = {
      name: document.getElementById("kontakt-name").value.trim(),
      rolle: document.getElementById("kontakt-rolle").value.trim() || null,
      telefon: document.getElementById("kontakt-telefon").value.trim() || null,
      email: document.getElementById("kontakt-email").value.trim() || null,
    };
    try {
      if (kontaktId) {
        await apiFetch(`/kontakte/${kontaktId}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
      } else {
        await apiFetch(`/depots/${Number(kontaktDepot.value)}/kontakte`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
      }
      setStatusWithNextStep(kontaktStatus, "Kontakt gespeichert.", "Weitere Kontakte pflegen oder Depot wechseln");
      kontaktForm.reset();
      document.getElementById("kontakt-id").value = "";
      markFormSaved(kontaktForm);
      await loadKontakte();
    } catch (error) {
      kontaktStatus.textContent = error.message;
    }
  });
}

if (kontaktDeleteButton) {
  kontaktDeleteButton.addEventListener("click", async () => {
    const kontaktId = document.getElementById("kontakt-id").value.trim();
    if (!kontaktId) {
      kontaktStatus.textContent = "Bitte Kontakt auswaehlen.";
      return;
    }
    if (!window.confirm(`Kontakt #${kontaktId} wirklich loeschen?`)) {
      return;
    }
    kontaktStatus.textContent = "Loesche Kontakt...";
    try {
      await apiFetch(`/kontakte/${kontaktId}`, { method: "DELETE" });
      setStatusWithNextStep(kontaktStatus, "Kontakt geloescht.", "Kontaktliste pruefen oder neuen Kontakt anlegen");
      kontaktForm?.reset();
      document.getElementById("kontakt-id").value = "";
      markFormSaved(kontaktForm);
      await loadKontakte();
    } catch (error) {
      kontaktStatus.textContent = error.message;
    }
  });
}

if (importPreviewButton) {
  importPreviewButton.addEventListener("click", async () => {
    importStatus.textContent = "Lade Import-Vorschau...";
    try {
      const data = await previewImport();
      setStatusWithNextStep(
        importStatus,
        `${data.valid_rows} gueltige Zeilen, ${data.error_count} Fehler.`,
        data.error_count ? "Fehler-Tab korrigieren" : "Import starten",
      );
    } catch (error) {
      importStatus.textContent = error.message;
    }
  });
}

if (importExecuteButton) {
  importExecuteButton.addEventListener("click", async () => {
    importStatus.textContent = "Import laeuft...";
    try {
      if (!lastImportPreview) {
        await previewImport();
      }
      const result = await executeImport();
      setStatusWithNextStep(
        importStatus,
        `${result.imported} Bewegungen importiert, ${result.error_count} Fehler.`,
        result.error_count ? "Fehler pruefen" : "Verlauf aktualisieren und weiterarbeiten",
      );
      if (importErrors) {
        if ((result.error_count || 0) > 0) {
          importErrors.classList.remove("hidden");
          importErrors.textContent = (result.errors || []).join("\n");
          activateInlineTab("import", "import-errors-panel", {
            hint: "Import mit Fehlern beendet - Details im Fehler-Tab.",
            level: "warning",
          });
        } else {
          importErrors.classList.add("hidden");
          importErrors.textContent = "";
          activateInlineTab("import", "import-upload-panel", {
            hint: "Import erfolgreich abgeschlossen.",
            level: "success",
          });
        }
      }
      await loadBewegungen();
    } catch (error) {
      importStatus.textContent = error.message;
    }
  });
}

if (importTemplateButton) {
  importTemplateButton.addEventListener("click", async () => {
    importStatus.textContent = "Lade Excel-Vorlage...";
    try {
      const response = await apiFetch("/imports/bewegungen/template");
      const blob = await response.blob();
      const blobUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = blobUrl;
      link.download = "bewegungen_vorlage.xlsx";
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(blobUrl), 10000);
      importStatus.textContent = "Vorlage heruntergeladen.";
    } catch (error) {
      importStatus.textContent = error.message;
    }
  });
}

if (importFileInput) {
  importFileInput.addEventListener("change", () => {
    try {
      validateImportFileSelection();
      setStatusWithNextStep(importStatus, "Datei geprueft.", "Vorschau laden");
    } catch (error) {
      setStatusWithNextStep(importStatus, error.message, "Andere Datei auswaehlen");
      if (importExecuteButton) importExecuteButton.disabled = true;
      return;
    }
    lastImportPreview = null;
    activateInlineTab("import", "import-upload-panel", {
      hint: "Neue Datei gewaehlt - bitte Vorschau laden.",
      level: "info",
    });
    if (importExecuteButton) {
      importExecuteButton.disabled = true;
    }
    if (importPreviewHead) importPreviewHead.innerHTML = "";
    if (importPreviewBody) importPreviewBody.innerHTML = "";
    if (importErrors) {
      importErrors.classList.add("hidden");
      importErrors.textContent = "";
    }
  });
}

if (emailSelectAllButton) {
  emailSelectAllButton.addEventListener("click", () => {
    if (!emailDepotsSelect) return;
    for (const option of emailDepotsSelect.options) option.selected = true;
  });
}

if (emailSelectNoneButton) {
  emailSelectNoneButton.addEventListener("click", () => {
    if (!emailDepotsSelect) return;
    for (const option of emailDepotsSelect.options) option.selected = false;
  });
}

if (emailPreviewRecipientsButton) {
  emailPreviewRecipientsButton.addEventListener("click", async () => {
    emailRecipientStatus.textContent = "Lade Empfaenger...";
    try {
      const data = await previewEmailRecipients();
      emailRecipientStatus.textContent = `${data.count} Empfaenger gefunden.`;
      if (emailRecipientPreview) {
        if (!data.recipients.length) {
          emailRecipientPreview.textContent = "Keine Ansprechpartner mit E-Mail gefunden.";
        } else {
          const lines = data.recipients.map(
            (row) => `${row.depot_name}: ${row.name} (${row.rolle || "-"}) <${row.email}>`,
          );
          emailRecipientPreview.textContent = lines.join("\n");
        }
      }
    } catch (error) {
      emailRecipientStatus.textContent = error.message;
    }
  });
}

if (emailDraftForm) {
  emailDraftForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!validateEmailDraftForm()) {
      setStatusWithNextStep(emailDraftStatus, "Bitte Entwurf vervollstaendigen.", "Depot und Nachricht ausfuellen");
      return;
    }
    emailDraftStatus.textContent = "Erstelle E-Mail-Entwurf...";
    try {
      const result = await createEmailDraft();
      setStatusWithNextStep(
        emailDraftStatus,
        `Entwurf gespeichert (ID ${result.id}, ${result.recipient_count} Empfaenger).`,
        "Im Verlauf oeffnen und Details pruefen",
      );
      emailDraftForm.reset();
      markFormSaved(emailDraftForm);
      await loadEmailHistory();
      activateInlineTab("email", "email-history-panel", {
        hint: "Entwurf erstellt - Verlauf wurde geoeffnet.",
        level: "success",
      });
    } catch (error) {
      emailDraftStatus.textContent = error.message;
    }
  });
}

if (emailHistoryReloadButton) {
  emailHistoryReloadButton.addEventListener("click", async () => {
    try {
      await loadEmailHistory();
      activateInlineTab("email", "email-history-panel", {
        hint: "Verlauf aktualisiert.",
        level: "info",
      });
    } catch (error) {
      emailDraftStatus.textContent = error.message;
    }
  });
}

if (emailHistoryBody) {
  emailHistoryBody.addEventListener("click", async (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;
    const tr = target.closest("tr");
    if (!tr?.dataset.id) return;
    try {
      const detail = await loadEmailHistoryDetail(Number(tr.dataset.id));
      if (emailHistoryDetail) {
        emailHistoryDetail.textContent =
          `Datum: ${detail.datum || ""}\n` +
          `Betreff: ${detail.betreff || ""}\n` +
          `Depots: ${detail.empfaenger_depots || ""}\n` +
          `Empfaenger (${detail.anzahl_empfaenger || 0}):\n${(detail.empfaenger_emails || "").split("; ").join("\n")}\n\n` +
          `Nachricht:\n${detail.nachricht || ""}`;
      }
    } catch (error) {
      if (emailHistoryDetail) emailHistoryDetail.textContent = error.message;
    }
  });
}

if (reportPerspective) {
  reportPerspective.addEventListener("change", () => {
    refreshReportSelectionOptions();
    lastReportRows = [];
    if (reportCharts) reportCharts.innerHTML = "";
    if (reportChartLegend) reportChartLegend.textContent = "";
  });
}

if (verfallPerspective) {
  verfallPerspective.addEventListener("change", () => {
    refreshVerfallSelectionOptions();
  });
}

if (verfallLoadButton) {
  verfallLoadButton.addEventListener("click", async () => {
    if (!verfallStatus) return;
    verfallStatus.textContent = "Lade Verfallsdaten...";
    try {
      const data = await loadVerfallOverview();
      setStatusWithNextStep(
        verfallStatus,
        `${Array.isArray(data.rows) ? data.rows.length : 0} Verfallspositionen geladen.`,
        "Filter anpassen oder CSV exportieren",
      );
    } catch (error) {
      verfallStatus.textContent = error.message;
    }
  });
}

if (verfallExportCsvButton) {
  verfallExportCsvButton.addEventListener("click", async () => {
    if (!verfallStatus) return;
    verfallStatus.textContent = "Erstelle Verfall-CSV...";
    try {
      await exportVerfallOverviewCsv();
      verfallStatus.textContent = "Verfall-CSV heruntergeladen.";
    } catch (error) {
      verfallStatus.textContent = error.message;
    }
  });
}

if (verfallSearch) {
  verfallSearch.addEventListener("input", debounce(async () => {
    if (!hasPermission("movements_read")) return;
    try {
      await loadVerfallOverview();
    } catch (_error) {
      // keep UI responsive on quick typing
    }
  }, 300));
}

if (verfallCategory) {
  verfallCategory.addEventListener("change", async () => {
    if (!hasPermission("movements_read")) return;
    try {
      await loadVerfallOverview();
    } catch (_error) {
      // ignore transient errors
    }
  });
}

if (dashboardRefreshButton) {
  dashboardRefreshButton.addEventListener("click", async () => {
    if (!dashboardStatus) return;
    dashboardStatus.textContent = "Aktualisiere Dashboard...";
    try {
      await loadDashboardOverview();
      dashboardStatus.textContent = "Dashboard aktualisiert.";
    } catch (error) {
      dashboardStatus.textContent = error.message;
    }
  });
}

if (dashboardOpenBewegungen) {
  dashboardOpenBewegungen.addEventListener("click", () => {
    showPage("bewegung-create-section");
  });
}
if (dashboardOpenVerfall) {
  dashboardOpenVerfall.addEventListener("click", () => {
    showPage("verfall-manager-section");
  });
}
if (dashboardOpenReports) {
  dashboardOpenReports.addEventListener("click", () => {
    showPage("reports-section");
  });
}

if (reportType) {
  reportType.addEventListener("change", () => {
    lastReportRows = [];
    if (reportCharts) reportCharts.innerHTML = "";
    if (reportChartLegend) reportChartLegend.textContent = "";
    if (reportKpis) reportKpis.textContent = "";
    if (reportTableHead) reportTableHead.innerHTML = "";
    if (reportTableBody) reportTableBody.innerHTML = "";
  });
}
if (reportStartDate) {
  reportStartDate.addEventListener("change", validateReportDateRangeSoft);
}
if (reportEndDate) {
  reportEndDate.addEventListener("change", validateReportDateRangeSoft);
}

if (reportLoadButton) {
  reportLoadButton.addEventListener("click", async () => {
    reportStatus.textContent = "Lade Auswertung...";
    try {
      const data = await loadReportData();
      lastReportRows = data.rows || [];
      renderReportTable(lastReportRows);
      renderReportCharts(lastReportRows);
      if (reportKpis) {
        reportKpis.textContent = JSON.stringify(data.kpis || {}, null, 2);
      }
      setStatusWithNextStep(
        reportStatus,
        `${lastReportRows.length} Zeilen geladen.`,
        "Charts pruefen oder Export ausfuehren",
      );
      if (lastReportRows.length > 0) {
        activateInlineTab("reports", "reports-visual-panel", {
          hint: "Auswertung geladen - Visualisierung geoeffnet.",
          level: "success",
        });
      } else {
        activateInlineTab("reports", "reports-table-panel", {
          hint: "Keine Chartdaten - pruefen Sie KPIs und Tabellen.",
          level: "info",
        });
      }
    } catch (error) {
      reportStatus.textContent = error.message;
      activateInlineTab("reports", "reports-builder-panel", {
        hint: "Laden fehlgeschlagen - bitte Filter im Builder anpassen.",
        level: "warning",
      });
    }
  });
}

if (reportExportButton) {
  reportExportButton.addEventListener("click", async () => {
    reportStatus.textContent = "Erstelle CSV Export...";
    try {
      await exportReportCsv();
      reportStatus.textContent = "CSV Export heruntergeladen.";
    } catch (error) {
      reportStatus.textContent = error.message;
    }
  });
}

if (reportExportPdfButton) {
  reportExportPdfButton.addEventListener("click", async () => {
    reportStatus.textContent = "Erstelle PDF Export...";
    try {
      await exportReportFile("pdf");
      reportStatus.textContent = "PDF Export heruntergeladen.";
    } catch (error) {
      reportStatus.textContent = error.message;
    }
  });
}

if (reportExportPptButton) {
  reportExportPptButton.addEventListener("click", async () => {
    reportStatus.textContent = "Erstelle PPT Export...";
    try {
      await exportReportFile("pptx");
      reportStatus.textContent = "PPT Export heruntergeladen.";
    } catch (error) {
      reportStatus.textContent = error.message;
    }
  });
}

if (logoutButton) {
  logoutButton.addEventListener("click", async () => {
    try {
      await apiFetch("/auth/logout", { method: "POST" });
    } catch (_error) {
      // local logout still proceeds even if backend token revoke fails.
    }
    removeToken();
    setAuthLocked(true);
    updateLoginPill("Nicht angemeldet", false);
    loginStatus.textContent = "Abgemeldet.";
    showPage("login-section");
  });
}

if (usersTableBody) {
  usersTableBody.addEventListener("click", async (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;
    const row = target.closest("tr");
    if (!row) return;
    usersTableBody.querySelectorAll("tr").forEach((item) => item.classList.remove("active-row"));
    row.classList.add("active-row");
    document.getElementById("users-id").value = row.dataset.id || "";
    document.getElementById("users-username").value = row.dataset.username || "";
    document.getElementById("users-role").value = row.dataset.role || "User";
    document.getElementById("users-email").value = row.dataset.email || "";
    document.getElementById("users-active").checked = row.dataset.active === "1";
    document.getElementById("users-password").value = "";
    if (usersPermissionsSelect) {
      let selectedPermissions = [];
      try {
        selectedPermissions = JSON.parse(row.dataset.permissions || "[]");
      } catch (_error) {
        selectedPermissions = [];
      }
      setSelectedPermissions(selectedPermissions);
    }
    syncUsersPermissionsUiState();
    try {
      await loadSelectedUserActivity(row.dataset.id || "");
    } catch (error) {
      usersStatus.textContent = error.message;
    }
  });
}

if (accountPasswordForm) {
  accountPasswordForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!accountStatus) return;
    accountStatus.textContent = "Aendere Passwort...";
    const oldPassword = document.getElementById("account-old-password").value;
    const newPassword = document.getElementById("account-new-password").value;
    try {
      await apiFetch("/auth/change-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
      });
      accountStatus.textContent = "Passwort erfolgreich geaendert.";
      accountPasswordForm.reset();
      markFormSaved(accountPasswordForm);
      mustChangePassword = false;
      if (accountPasswordWarning) {
        accountPasswordWarning.classList.add("hidden");
      }
      showToast("Passwort erfolgreich geaendert.", "success");
      await loadCurrentUserActivity();
      showPage(getDefaultLandingPageId());
    } catch (error) {
      accountStatus.textContent = error.message;
      showToast(error.message, "error");
    }
  });
}

if (accountAvatarForm) {
  accountAvatarForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!accountAvatarFile?.files?.length) {
      if (accountStatus) accountStatus.textContent = "Bitte zuerst eine Bilddatei waehlen.";
      return;
    }
    if (accountStatus) accountStatus.textContent = "Speichere Profilbild...";
    const formData = new FormData();
    formData.append("file", accountAvatarFile.files[0], accountAvatarFile.files[0].name);
    try {
      await apiFetch("/auth/avatar", { method: "POST", body: formData });
      avatarAvailable = true;
      if (accountStatus) accountStatus.textContent = "Profilbild gespeichert.";
      showToast("Profilbild gespeichert.", "success");
      accountAvatarForm.reset();
      await loadCurrentAvatar();
      await loadCurrentUserActivity();
    } catch (error) {
      if (accountStatus) accountStatus.textContent = error.message;
      showToast(error.message, "error");
    }
  });
}

if (accountAvatarRemoveButton) {
  accountAvatarRemoveButton.addEventListener("click", async () => {
    if (accountStatus) accountStatus.textContent = "Entferne Profilbild...";
    try {
      await apiFetch("/auth/avatar", { method: "DELETE" });
      avatarAvailable = false;
      if (accountStatus) accountStatus.textContent = "Profilbild entfernt.";
      showToast("Profilbild entfernt.", "success");
      await loadCurrentAvatar();
      await loadCurrentUserActivity();
    } catch (error) {
      if (accountStatus) accountStatus.textContent = error.message;
      showToast(error.message, "error");
    }
  });
}

if (backupDownloadButton) {
  backupDownloadButton.addEventListener("click", async () => {
    if (backupStatus) backupStatus.textContent = "Erstelle Backup...";
    try {
      const response = await apiFetch("/admin/backup/download");
      const blob = await response.blob();
      const blobUrl = URL.createObjectURL(blob);
      const contentDisposition = response.headers.get("content-disposition") || "";
      const match = /filename=\"?([^\";]+)\"?/i.exec(contentDisposition);
      const filename = match ? match[1] : "ndhub_backup.db";
      const link = document.createElement("a");
      link.href = blobUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(blobUrl), 10000);
      setStatusWithNextStep(backupStatus, "Backup heruntergeladen.", "Datei sicher ablegen oder Liste aktualisieren");
      showToast("Backup heruntergeladen.", "success");
      await loadBackupList();
    } catch (error) {
      if (backupStatus) backupStatus.textContent = error.message;
      showToast(error.message, "error");
    }
  });
}

if (backupCreateButton) {
  backupCreateButton.addEventListener("click", async () => {
    if (backupStatus) backupStatus.textContent = "Erstelle Backup...";
    try {
      const result = await (await apiFetch("/admin/backup/create", { method: "POST" })).json();
      setStatusWithNextStep(backupStatus, `Backup erstellt: ${result.filename}`, "Bei Bedarf direkt herunterladen");
      showToast("Backup erstellt.", "success");
      await loadBackupList();
    } catch (error) {
      if (backupStatus) backupStatus.textContent = error.message;
      showToast(error.message, "error");
    }
  });
}

if (backupReloadButton) {
  backupReloadButton.addEventListener("click", async () => {
    if (backupStatus) backupStatus.textContent = "Lade Backup-Liste...";
    try {
      await loadBackupList();
      setStatusWithNextStep(backupStatus, "Backup-Liste aktualisiert.", "Restore-Datei waehlen oder Backup erstellen");
    } catch (error) {
      if (backupStatus) backupStatus.textContent = error.message;
      showToast(error.message, "error");
    }
  });
}

if (backupTableBody) {
  backupTableBody.addEventListener("click", async (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;
    const button = target.closest("button[data-action='download-backup']");
    if (!button) return;
    const row = button.closest("tr");
    const filename = row?.dataset.filename || "";
    if (!filename) return;
    if (backupStatus) backupStatus.textContent = `Lade ${filename}...`;
    try {
      await downloadBackupByFilename(filename);
      setStatusWithNextStep(backupStatus, `Backup heruntergeladen: ${filename}`, "Datei archivieren oder weitere Backups pruefen");
      showToast("Backup-Datei heruntergeladen.", "success");
    } catch (error) {
      if (backupStatus) backupStatus.textContent = error.message;
      showToast(error.message, "error");
    }
  });
}

if (backupRestoreForm) {
  backupRestoreForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    let restoreFile;
    try {
      restoreFile = validateBackupRestoreFileSelection();
    } catch (error) {
      setStatusWithNextStep(backupStatus, error.message, "Gueltige Backup-Datei waehlen");
      return;
    }
    if (!window.confirm("Backup wirklich wiederherstellen? Danach bitte neu anmelden.")) return;
    if (backupStatus) backupStatus.textContent = "Stelle Backup wieder her...";
    const formData = new FormData();
    formData.append("file", restoreFile, restoreFile.name);
    try {
      const result = await (
        await apiFetch("/admin/backup/restore", {
          method: "POST",
          body: formData,
        })
      ).json();
      if (backupStatus) backupStatus.textContent = result.message || "Backup wiederhergestellt.";
      showToast("Backup wiederhergestellt. Bitte neu anmelden.", "warning", 4200);
      removeToken();
      setAuthLocked(true);
      updateLoginPill("Bitte anmelden", false);
      showPage("login-section");
    } catch (error) {
      if (backupStatus) backupStatus.textContent = error.message;
      showToast(error.message, "error");
    }
  });
}

if (usersForm) {
  const usersRoleSelect = document.getElementById("users-role");
  const usersPasswordInput = document.getElementById("users-password");
  const usersResetPasswordInput = document.getElementById("users-reset-password");
  usersRoleSelect?.addEventListener("change", () => {
    syncUsersPermissionsUiState();
  });
  usersPasswordInput?.addEventListener("input", () => {
    const hint = passwordPolicyHint(usersPasswordInput.value);
    if (hint) setStatusWithNextStep(usersStatus, hint, "Danach Benutzer speichern");
  });
  usersResetPasswordInput?.addEventListener("input", () => {
    const hint = passwordPolicyHint(usersResetPasswordInput.value);
    if (hint) setStatusWithNextStep(usersStatus, hint, "Danach Passwort zuruecksetzen");
  });
  usersForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    usersStatus.textContent = "Speichere Benutzer...";
    try {
      const message = await saveUserFromForm();
      setStatusWithNextStep(usersStatus, message, "Benutzerliste pruefen oder Aktivitaeten oeffnen");
      showToast(message, "success");
      markFormSaved(usersForm);
      await loadUsers();
      if (!document.getElementById("users-id").value.trim()) {
        clearUsersForm();
      }
    } catch (error) {
      usersStatus.textContent = error.message;
      showToast(error.message, "error");
    }
  });
}

if (usersApplyTemplateButton) {
  usersApplyTemplateButton.addEventListener("click", () => {
    const role = document.getElementById("users-role")?.value || "User";
    if (role === "Admin") {
      usersStatus.textContent = "Admin besitzt automatisch alle Berechtigungen.";
      syncUsersPermissionsUiState();
      return;
    }
    const key = usersPermissionTemplateSelect?.value || "";
    if (!key) {
      usersStatus.textContent = "Bitte zuerst eine Rechtevorlage waehlen.";
      return;
    }
    const template = permissionTemplates.find((item) => item.key === key);
    if (!template) {
      usersStatus.textContent = "Vorlage nicht gefunden.";
      return;
    }
    setSelectedPermissions(template.permissions || []);
    usersStatus.textContent = `Vorlage uebernommen: ${template.label || template.key}`;
  });
}

if (usersReloadButton) {
  usersReloadButton.addEventListener("click", async () => {
    usersStatus.textContent = "Lade Benutzerliste...";
    try {
      await loadUsers();
      usersStatus.textContent = "Benutzerliste aktualisiert.";
    } catch (error) {
      usersStatus.textContent = error.message;
    }
  });
}

if (usersResetButton) {
  usersResetButton.addEventListener("click", async () => {
    usersStatus.textContent = "Setze Passwort zurueck...";
    try {
      await resetSelectedUserPassword();
      setStatusWithNextStep(usersStatus, "Passwort erfolgreich zurueckgesetzt.", "Benutzer informieren und Login testen");
      document.getElementById("users-reset-password").value = "";
      markFormSaved(usersForm);
      showToast("Passwort wurde zurueckgesetzt.", "success");
    } catch (error) {
      usersStatus.textContent = error.message;
      showToast(error.message, "error");
    }
  });
}

if (usersUnlockButton) {
  usersUnlockButton.addEventListener("click", async () => {
    const userId = document.getElementById("users-id").value.trim();
    if (!userId) {
      usersStatus.textContent = "Bitte zuerst einen Benutzer auswaehlen.";
      return;
    }
    usersStatus.textContent = "Entsperre Benutzer...";
    try {
      await apiFetch(`/users/${Number(userId)}/unlock`, { method: "POST" });
      setStatusWithNextStep(usersStatus, "Benutzer entsperrt.", "Benutzerliste aktualisieren oder Aktivitaeten pruefen");
      markFormSaved(usersForm);
      showToast("Benutzer entsperrt.", "success");
      await loadUsers();
      await loadSelectedUserActivity(userId);
    } catch (error) {
      usersStatus.textContent = error.message;
      showToast(error.message, "error");
    }
  });
}

if (usersDeleteButton) {
  usersDeleteButton.addEventListener("click", async () => {
    const userId = document.getElementById("users-id").value.trim();
    if (!userId) {
      usersStatus.textContent = "Bitte zuerst einen Benutzer auswaehlen.";
      return;
    }
    usersStatus.textContent = "Loesche Benutzer...";
    try {
      await apiFetch(`/users/${Number(userId)}`, { method: "DELETE" });
      setStatusWithNextStep(usersStatus, "Benutzer geloescht.", "Liste pruefen oder neuen Benutzer anlegen");
      showToast("Benutzer geloescht.", "success");
      clearUsersForm();
      markFormSaved(usersForm);
      await loadUsers();
    } catch (error) {
      usersStatus.textContent = error.message;
      showToast(error.message, "error");
    }
  });
}

if (usersClearButton) {
  usersClearButton.addEventListener("click", () => {
    clearUsersForm();
    if (usersTableBody) {
      usersTableBody.querySelectorAll("tr").forEach((item) => item.classList.remove("active-row"));
    }
    if (usersActivityBody) usersActivityBody.innerHTML = "";
    usersStatus.textContent = "";
    markFormSaved(usersForm);
  });
}

window.addEventListener("resize", () => {
  if (lastReportRows.length) {
    renderReportCharts(lastReportRows);
  }
});

