const TOKEN_KEY = "ndhub_token";
const PAGE_SIZE = 20;
const uiUtils = window.NDHubUIUtils || {};
const safeAppendCell = uiUtils.appendCell || ((tr, text) => {
  const td = document.createElement("td");
  td.textContent = String(text ?? "");
  tr.appendChild(td);
  return td;
});
const safeAppendHtmlCell = uiUtils.appendHtmlCell || ((tr, html) => {
  const td = document.createElement("td");
  td.innerHTML = String(html || "");
  tr.appendChild(td);
  return td;
});

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
const praeparatForm = document.getElementById("praeparat-form");
const praeparatStatus = document.getElementById("praeparat-status");
const bewegungForm = document.getElementById("bewegung-form");
const bewegungStatus = document.getElementById("bewegung-status");
const bewegungAttachment = document.getElementById("bewegung-attachment");
const bewegungSearch = document.getElementById("bewegung-search");
const bewegungFilterDepot = document.getElementById("bewegung-filter-depot");
const bewegungFilterTyp = document.getElementById("bewegung-filter-typ");
const bewegungFilterPraeparat = document.getElementById("bewegung-filter-praeparat");
const bewegungFilterHasAttachment = document.getElementById("bewegung-filter-has-attachment");
const bewegungFilterStartDate = document.getElementById("bewegung-filter-start-date");
const bewegungFilterEndDate = document.getElementById("bewegung-filter-end-date");
const bewegungPrev = document.getElementById("bewegung-prev");
const bewegungNext = document.getElementById("bewegung-next");
const bewegungenBody = document.querySelector("#bewegungen-table tbody");
const auditSection = document.getElementById("audit-section");
const auditSearch = document.getElementById("audit-search");
const auditFilterAction = document.getElementById("audit-filter-action");
const auditFilterResource = document.getElementById("audit-filter-resource");
const auditPrev = document.getElementById("audit-prev");
const auditNext = document.getElementById("audit-next");
const auditBody = document.querySelector("#audit-table tbody");
const importFileInput = document.getElementById("import-file");
const emailDeliveryMode = document.getElementById("email-delivery-mode");
const emailSendNow = document.getElementById("email-send-now");
const reportPerspective = document.getElementById("report-perspective");
const reportIdsSelect = document.getElementById("report-ids");
const reportStartDate = document.getElementById("report-start-date");
const reportEndDate = document.getElementById("report-end-date");
const reportType = document.getElementById("report-type");
const reportStatus = document.getElementById("report-status");
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
const dashboardOpenBewegungen = document.getElementById("dashboard-open-bewegungen");
const dashboardOpenVerfall = document.getElementById("dashboard-open-verfall");
const dashboardOpenReports = document.getElementById("dashboard-open-reports");
const verfallPerspective = document.getElementById("verfall-perspective");
const verfallIdsSelect = document.getElementById("verfall-ids");
const verfallCategory = document.getElementById("verfall-category");
const verfallSearch = document.getElementById("verfall-search");
const verfallTableBody = document.querySelector("#verfall-table tbody");
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
const workspaceArea = document.getElementById("workspace-area");
const settingsBackupTabButton = document.querySelector('[data-tab-target="settings-backup-panel"]');
const settingsBackupPanel = document.getElementById("settings-backup-panel");
const onboardingStartAdminButton = document.getElementById("onboarding-start-admin");
const onboardingStepLabel = document.getElementById("onboarding-step-label");
const onboardingStatus = document.getElementById("onboarding-status");
const onboardingStep1 = document.getElementById("onboarding-form-step-1");
const onboardingStep2 = document.getElementById("onboarding-form-step-2");
const onboardingStep3 = document.getElementById("onboarding-form-step-3");
const onboardingStep4 = document.getElementById("onboarding-form-step-4");
const onboardingInstitutionName = document.getElementById("onboarding-institution-name");
const onboardingInstitutionStreet = document.getElementById("onboarding-institution-street");
const onboardingInstitutionHouseNumber = document.getElementById("onboarding-institution-house-number");
const onboardingInstitutionPostcode = document.getElementById("onboarding-institution-postcode");
const onboardingInstitutionCity = document.getElementById("onboarding-institution-city");
const onboardingInstitutionLatitude = document.getElementById("onboarding-institution-latitude");
const onboardingInstitutionLongitude = document.getElementById("onboarding-institution-longitude");
const onboardingGeocodeButton = document.getElementById("onboarding-geocode");
const onboardingPraeparateList = document.getElementById("onboarding-praeparate-list");
const onboardingAddPraeparatButton = document.getElementById("onboarding-add-praeparat");
const onboardingDepotsList = document.getElementById("onboarding-depots-list");
const onboardingReview = document.getElementById("onboarding-review");
const onboardingAddDepotButton = document.getElementById("onboarding-add-depot");
const onboardingPrevButton = document.getElementById("onboarding-prev");
const onboardingNextButton = document.getElementById("onboarding-next");
const onboardingSubmitButton = document.getElementById("onboarding-submit");
const desktopSyncForm = document.getElementById("desktop-sync-form");
const desktopSyncBackendUrlInput = document.getElementById("desktop-sync-backend-url");
const desktopSyncClientLabelInput = document.getElementById("desktop-sync-client-label");
const desktopSyncTokenInput = document.getElementById("desktop-sync-token");
const desktopSyncExpiresAtInput = document.getElementById("desktop-sync-expires-at");
const desktopSyncGenerateButton = document.getElementById("desktop-sync-generate");
const desktopSyncCopyUrlButton = document.getElementById("desktop-sync-copy-url");
const desktopSyncCopyTokenButton = document.getElementById("desktop-sync-copy-token");
const desktopSyncStatus = document.getElementById("desktop-sync-status");
const desktopSyncArchiveTableBody = document.querySelector("#desktop-sync-archive-table tbody");
const navLinks = Array.from(document.querySelectorAll(".nav-link"));
const sidebarShortcuts = Array.from(document.querySelectorAll(".sidebar-shortcut"));
const mobileQuickLinks = Array.from(document.querySelectorAll(".mobile-quick-link"));
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
const usersTableBody = document.querySelector("#users-table tbody");
const usersActivityBody = document.querySelector("#users-activity-table tbody");
const usersForm = document.getElementById("users-form");
const usersPermissionsSelect = document.getElementById("users-permissions");
const usersPermissionTemplateSelect = document.getElementById("users-permission-template");
const usersApplyTemplateButton = document.getElementById("users-apply-template");
const usersResetButton = document.getElementById("users-reset");
const usersUnlockButton = document.getElementById("users-unlock");
const usersDeleteButton = document.getElementById("users-delete");
const usersClearButton = document.getElementById("users-clear");
const usersStatus = document.getElementById("users-status");
const backupRestoreForm = document.getElementById("backup-restore-form");
const backupRestoreFileInput = document.getElementById("backup-restore-file");
const backupStatus = document.getElementById("backup-status");
const backupTableBody = document.querySelector("#backup-table tbody");
const assignmentDepot = document.getElementById("assignment-depot");
const kontaktDepot = document.getElementById("kontakt-depot");
const kontaktForm = document.getElementById("kontakt-form");
const kontaktStatus = document.getElementById("kontakt-status");

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
let reportMasterDepots = [];
let reportMasterPraeparate = [];
let lastReportRows = [];
let reportBestandShowAll = false;
let maxBackupRestoreSizeMb = 200;
let backupDbEngine = "sqlite";
let onboardingStepIndex = 0;
let onboardingAutoOpened = false;
let onboardingPraeparate = [];
let onboardingDepots = [];
const depotNameById = new Map();
const praeparatNameById = new Map();
const THEME_KEY = "ndhub_theme";
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
let historyFiltersAppliedInSession = false;
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
const BEWEGUNG_HISTORY_FILTERS_KEY_PREFIX = "ndhub_bewegung_history_filters_";
const MAX_BEWEGUNG_ATTACHMENT_SIZE_BYTES = 10 * 1024 * 1024;
const ALLOWED_BEWEGUNG_ATTACHMENT_MIME_TYPES = new Set(["application/pdf", "application/x-pdf"]);
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
  "onboarding-status": "Einrichtungswizard",
};
const PAGE_CONTEXT_LABELS = {
  "login-section": "Sicherer Zugang zur Anwendung",
  "dashboard-section": "Uebersicht zu Bestand, Aktivitaeten und Verfall",
  "stammdaten-section": "Stammdatenverwaltung und Zuordnungen",
  "bewegung-create-section": "Bestandsbewegungen erfassen",
  "bewegung-import-section": "Bewegungen aus Dateien importieren",
  "bewegung-history-section": "Verlauf durchsuchen und Anhaenge pruefen",
  "verfall-manager-section": "Verfallspositionen filtern, priorisieren und exportieren",
  "settings-section": "Adminbereich: Verwaltung, Sicherheit und Audit",
  "onboarding-section": "Neue Institution mit Stammdaten und Zuordnungen einrichten",
  "email-section": "Empfaenger pruefen und Entwuerfe erstellen",
  "reports-section": "Auswertungen laden und exportieren",
  "account-section": "Profil, Passwort und eigene Aktivitaeten verwalten",
  "users-section": "Benutzer, Rollen und Rechte administrieren",
  "audit-section": "Aenderungen revisionssicher nachvollziehen",
};
const PAGE_AREA_LABELS = {
  "login-section": "Zugang",
  "dashboard-section": "Uebersicht",
  "stammdaten-section": "Verwaltung",
  "bewegung-create-section": "Operativ",
  "bewegung-import-section": "Operativ",
  "bewegung-history-section": "Operativ",
  "verfall-manager-section": "Operativ",
  "email-section": "Kommunikation",
  "reports-section": "Analyse",
  "settings-section": "Administration",
  "onboarding-section": "Administration",
  "users-section": "Administration",
  "audit-section": "Administration",
  "account-section": "Konto",
};
const DIRTY_TRACKED_FORMS = [
  depotForm,
  praeparatForm,
  bewegungForm,
  kontaktForm,
  accountPasswordForm,
  usersForm,
  backupRestoreForm,
];
const DEFAULT_MAX_BACKUP_RESTORE_SIZE_MB = 200;
const FORM_STATUS_NODE_BY_ID = {
  "login-form": loginStatus,
  "depot-form": depotStatus,
  "praeparat-form": praeparatStatus,
  "bewegung-form": bewegungStatus,
  "kontakt-form": kontaktStatus,
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
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch (_error) {
    return "";
  }
}

function setToken(token) {
  try {
    localStorage.setItem(TOKEN_KEY, token);
  } catch (_error) {
    // Ignore storage failures (e.g., strict privacy mode).
  }
}

function removeToken() {
  try {
    localStorage.removeItem(TOKEN_KEY);
  } catch (_error) {
    // Ignore storage failures (e.g., strict privacy mode).
  }
}

function getBewegungAutofillEnabled() {
  let raw = null;
  try {
    raw = localStorage.getItem(BEWEGUNG_AUTOFILL_ENABLED_KEY);
  } catch (_error) {
    raw = null;
  }
  return raw !== "0";
}

function setBewegungAutofillEnabled(enabled) {
  try {
    localStorage.setItem(BEWEGUNG_AUTOFILL_ENABLED_KEY, enabled ? "1" : "0");
  } catch (_error) {
    // Ignore storage failures.
  }
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
  try {
    localStorage.setItem(BEWEGUNG_LAST_INPUT_KEY, JSON.stringify(payload));
  } catch (_error) {
    // Ignore storage failures.
  }
}

function getBewegungHistoryFiltersStorageKey() {
  const safeUser = (currentUsername || "anonymous").trim().toLowerCase() || "anonymous";
  return `${BEWEGUNG_HISTORY_FILTERS_KEY_PREFIX}${safeUser}`;
}

function readBewegungHistoryFilters() {
  try {
    const raw = localStorage.getItem(getBewegungHistoryFiltersStorageKey());
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") return null;
    return parsed;
  } catch (_error) {
    return null;
  }
}

function collectCurrentBewegungHistoryFilters() {
  return {
    q: bewegungSearch?.value?.trim() || "",
    typ: bewegungFilterTyp?.value || "",
    depot_id: bewegungFilterDepot?.value || "",
    praeparat_id: bewegungFilterPraeparat?.value || "",
    has_attachment: bewegungFilterHasAttachment?.checked ? 1 : 0,
    start_date: bewegungFilterStartDate?.value?.trim() || "",
    end_date: bewegungFilterEndDate?.value?.trim() || "",
  };
}

function saveBewegungHistoryFilters() {
  try {
    localStorage.setItem(getBewegungHistoryFiltersStorageKey(), JSON.stringify(collectCurrentBewegungHistoryFilters()));
  } catch (_error) {
    // Ignore storage failures.
  }
}

function applyBewegungHistoryFiltersFromStorage() {
  if (historyFiltersAppliedInSession) return;
  const saved = readBewegungHistoryFilters();
  if (!saved) return;
  if (bewegungSearch instanceof HTMLInputElement) bewegungSearch.value = String(saved.q || "");
  if (bewegungFilterTyp instanceof HTMLSelectElement) bewegungFilterTyp.value = String(saved.typ || "");
  if (bewegungFilterDepot instanceof HTMLSelectElement) bewegungFilterDepot.value = String(saved.depot_id || "");
  if (bewegungFilterPraeparat instanceof HTMLSelectElement) bewegungFilterPraeparat.value = String(saved.praeparat_id || "");
  if (bewegungFilterHasAttachment instanceof HTMLInputElement) bewegungFilterHasAttachment.checked = Number(saved.has_attachment || 0) === 1;
  if (bewegungFilterStartDate instanceof HTMLInputElement) bewegungFilterStartDate.value = String(saved.start_date || "");
  if (bewegungFilterEndDate instanceof HTMLInputElement) bewegungFilterEndDate.value = String(saved.end_date || "");
  historyFiltersAppliedInSession = true;
}

function resetBewegungHistoryFiltersToDefault() {
  if (bewegungSearch instanceof HTMLInputElement) bewegungSearch.value = "";
  if (bewegungFilterTyp instanceof HTMLSelectElement) bewegungFilterTyp.value = "";
  if (bewegungFilterDepot instanceof HTMLSelectElement) bewegungFilterDepot.value = "";
  if (bewegungFilterPraeparat instanceof HTMLSelectElement) bewegungFilterPraeparat.value = "";
  if (bewegungFilterHasAttachment instanceof HTMLInputElement) bewegungFilterHasAttachment.checked = false;
  if (bewegungFilterStartDate instanceof HTMLInputElement) bewegungFilterStartDate.value = "";
  if (bewegungFilterEndDate instanceof HTMLInputElement) bewegungFilterEndDate.value = "";
  saveBewegungHistoryFilters();
}

function validateBewegungAttachmentFile(file) {
  if (!(file instanceof File)) return;
  const safeName = String(file.name || "").trim();
  if (!safeName.toLowerCase().endsWith(".pdf")) {
    throw new Error("Nur PDF-Dateien sind als Anhang erlaubt.");
  }
  if (Number(file.size || 0) > MAX_BEWEGUNG_ATTACHMENT_SIZE_BYTES) {
    throw new Error("PDF-Datei ist zu gross (max. 10 MB).");
  }
  const type = String(file.type || "").trim().toLowerCase();
  if (type && !ALLOWED_BEWEGUNG_ATTACHMENT_MIME_TYPES.has(type)) {
    throw new Error("Nur PDF-Dateien sind als Anhang erlaubt.");
  }
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
  if (hasPermission("movements_write")) return "bewegung-create-section";
  if (hasPermission("import_use")) return "bewegung-import-section";
  if (hasPermission("email_use")) return "email-section";
  if (hasPermission("reports_view")) return "reports-section";
  return "account-section";
}

function applyPermissionVisibility() {
  const pagePermissions = {
    "dashboard-section": "movements_read",
    "stammdaten-section": "__admin__",
    "bewegung-create-section": "movements_read",
    "bewegung-import-section": "import_use",
    "bewegung-history-section": "movements_read",
    "verfall-manager-section": "movements_read",
    "settings-section": "__admin__",
    "onboarding-section": "__admin__",
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
  for (const shortcut of sidebarShortcuts) {
    const required = shortcut.getAttribute("data-required-permission");
    if (!required) continue;
    shortcut.classList.toggle("hidden", !hasPageAccess(required));
  }
  for (const quickLink of mobileQuickLinks) {
    const targetId = quickLink.getAttribute("data-page-target") || "";
    const required = pagePermissions[targetId];
    if (required === undefined) continue;
    quickLink.classList.toggle("hidden", !hasPageAccess(required));
  }
  if (settingsBackupTabButton instanceof HTMLElement) {
    settingsBackupTabButton.classList.toggle("hidden", !isAdminUser() || !hasPermission("backup_manage"));
  }
  if (settingsBackupPanel) {
    settingsBackupPanel.classList.toggle("hidden", !isAdminUser() || !hasPermission("backup_manage"));
  }
  if ((!isAdminUser() || !hasPermission("backup_manage")) && settingsBackupPanel?.classList.contains("active")) {
    activateInlineTab("settings", "settings-desktop-sync-panel", { persist: false });
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
    historyFiltersAppliedInSession = false;
    onboardingAutoOpened = false;
    currentPermissions = new Set();
    stopNotificationPolling();
    notificationSince = null;
    renderNotificationList([]);
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
  try {
    localStorage.setItem(THEME_KEY, darkModeEnabled ? "dark" : "light");
  } catch (_error) {
    // Ignore storage failures.
  }
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
  let savedTheme = "light";
  try {
    savedTheme = localStorage.getItem(THEME_KEY) === "dark" ? "dark" : "light";
  } catch (_error) {
    savedTheme = "light";
  }
  setTheme(savedTheme);
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
  for (const quickLink of mobileQuickLinks) {
    quickLink.addEventListener("click", (event) => {
      event.preventDefault();
      const targetId = quickLink.getAttribute("data-page-target") || "";
      if (!targetId) return;
      showPage(targetId);
    });
  }
}

function initializeSidebarShortcuts() {
  for (const shortcut of sidebarShortcuts) {
    shortcut.addEventListener("click", () => {
      const pageTarget = shortcut.getAttribute("data-sidebar-page") || "";
      if (!pageTarget) return;
      showPage(pageTarget);
      const tabTarget = shortcut.getAttribute("data-sidebar-tab") || "";
      if (tabTarget) {
        activateInlineTab("settings", tabTarget, { hint: "Bereich geoeffnet", level: "info" });
      }
    });
  }
}

function syncSidebarShortcutState(targetPageId) {
  for (const shortcut of sidebarShortcuts) {
    const pageTarget = shortcut.getAttribute("data-sidebar-page") || "";
    const tabTarget = shortcut.getAttribute("data-sidebar-tab") || "";
    const settingsOpen = pageTarget === targetPageId && targetPageId === "settings-section";
    if (!settingsOpen) {
      shortcut.classList.toggle("active", pageTarget === targetPageId);
      continue;
    }
    const tabPanel = tabTarget ? document.getElementById(tabTarget) : null;
    const tabIsActive = tabPanel instanceof HTMLElement ? tabPanel.classList.contains("active") : false;
    shortcut.classList.toggle("active", tabIsActive);
  }
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
        try {
          localStorage.setItem(`${INLINE_TAB_STORAGE_PREFIX}${groupName}`, targetId);
        } catch (_error) {
          // Ignore storage failures.
        }
      }
      if (activePageId === "settings-section") {
        syncSidebarShortcutState("settings-section");
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
        ? (() => {
            try {
              return localStorage.getItem(`${INLINE_TAB_STORAGE_PREFIX}${groupName}`);
            } catch (_error) {
              return null;
            }
          })()
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
  statusNode.classList.remove("success", "warning", "error", "info");
  if (!baseMessage) {
    statusNode.textContent = "";
    return;
  }
  const lowered = baseMessage.toLowerCase();
  if (/(fehler|error|konnte nicht|ungueltig|abgelaufen)/i.test(lowered)) {
    statusNode.classList.add("error");
  } else if (/(warn|achtung|kritisch)/i.test(lowered)) {
    statusNode.classList.add("warning");
  } else if (/(geladen|aktualisiert|hinweis)/i.test(lowered)) {
    statusNode.classList.add("info");
  } else if (/(gespeichert|erstellt|abgeschlossen|importiert|erfolgreich)/i.test(lowered)) {
    statusNode.classList.add("success");
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

function hasAllowedExtension(fileName, allowedExtensions) {
  const normalized = String(fileName || "").toLowerCase();
  return allowedExtensions.some((ext) => normalized.endsWith(ext));
}

function filenameFromResponseHeader(response, fallbackName) {
  const fallback = String(fallbackName || "download.bin");
  const header = String(response?.headers?.get("content-disposition") || "");
  if (!header) return fallback;

  const utfMatch = header.match(/filename\*\s*=\s*UTF-8''([^;]+)/i);
  if (utfMatch && utfMatch[1]) {
    try {
      return decodeURIComponent(utfMatch[1].trim().replace(/^"|"$/g, "")) || fallback;
    } catch (_error) {
      // Continue with plain filename parsing below.
    }
  }
  const plainMatch = header.match(/filename\s*=\s*("?)([^";]+)\1/i);
  if (plainMatch && plainMatch[2]) return plainMatch[2].trim();
  return fallback;
}

function validateBackupRestoreFileSelection() {
  const file = backupRestoreFileInput?.files?.[0];
  if (!file) {
    throw new Error("Bitte eine Backup-Datei auswaehlen.");
  }
  const allowedForEngine = backupDbEngine === "mariadb"
    ? [".mariadb.json", ".json"]
    : [".db", ".sqlite", ".sqlite3"];
  if (!hasAllowedExtension(file.name, allowedForEngine)) {
    const expected = backupDbEngine === "mariadb"
      ? ".mariadb.json/.json"
      : ".db/.sqlite/.sqlite3";
    throw new Error(`Nur Backup-Dateien mit ${expected} sind erlaubt.`);
  }
  const maxBytes = Math.max(1, Number(maxBackupRestoreSizeMb || DEFAULT_MAX_BACKUP_RESTORE_SIZE_MB)) * 1024 * 1024;
  if (Number(file.size || 0) > maxBytes) {
    throw new Error(`Backup-Datei ist zu gross (max. ${maxBackupRestoreSizeMb} MB).`);
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

function parseOnboardingPraeparate() {
  const unique = [];
  const seen = new Set();
  for (const item of onboardingPraeparate) {
    const name = String(item?.name || "").trim();
    if (!name) continue;
    const key = name.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    unique.push({
      name,
      wirkstoff: String(item?.wirkstoff || "").trim() || null,
      darreichungsform: String(item?.darreichungsform || "").trim() || null,
      staerke: String(item?.staerke || "").trim() || null,
      einheit: String(item?.einheit || "").trim() || null,
      pzn: String(item?.pzn || "").trim() || null,
      hersteller: String(item?.hersteller || "").trim() || null,
    });
  }
  return unique;
}

function createOnboardingPraeparatCard(item, index) {
  const card = document.createElement("div");
  card.className = "onboarding-praeparat-card";
  card.innerHTML = `
    <h4>Praeparat ${index + 1}</h4>
    <div class="grid two-col">
      <label>Name<input type="text" data-onboarding-praeparat-field="name" value="${escapeHtml(item.name || "")}" /></label>
      <label>Wirkstoff<input type="text" data-onboarding-praeparat-field="wirkstoff" value="${escapeHtml(item.wirkstoff || "")}" /></label>
      <label>Darreichungsform<input type="text" data-onboarding-praeparat-field="darreichungsform" value="${escapeHtml(item.darreichungsform || "")}" /></label>
      <label>Staerke<input type="text" data-onboarding-praeparat-field="staerke" value="${escapeHtml(item.staerke || "")}" /></label>
      <label>Einheit<input type="text" data-onboarding-praeparat-field="einheit" value="${escapeHtml(item.einheit || "")}" /></label>
      <label>PZN<input type="text" data-onboarding-praeparat-field="pzn" value="${escapeHtml(item.pzn || "")}" /></label>
      <label>Hersteller<input type="text" data-onboarding-praeparat-field="hersteller" value="${escapeHtml(item.hersteller || "")}" /></label>
    </div>
    <div class="actions">
      <button type="button" data-onboarding-remove-praeparat="${index}">Praeparat entfernen</button>
    </div>
  `;
  card.addEventListener("input", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLInputElement)) return;
    const field = target.getAttribute("data-onboarding-praeparat-field");
    if (!field) return;
    onboardingPraeparate[index][field] = target.value;
    updateOnboardingReview();
  });
  const removeButton = card.querySelector(`[data-onboarding-remove-praeparat="${index}"]`);
  removeButton?.addEventListener("click", () => {
    onboardingPraeparate.splice(index, 1);
    renderOnboardingPraeparate();
    renderOnboardingDepots();
  });
  return card;
}

function renderOnboardingPraeparate() {
  if (!onboardingPraeparateList) return;
  onboardingPraeparateList.innerHTML = "";
  onboardingPraeparate.forEach((item, index) => {
    onboardingPraeparateList.appendChild(createOnboardingPraeparatCard(item, index));
  });
  updateOnboardingReview();
}

function buildOnboardingInstitutionAddress() {
  const street = String(onboardingInstitutionStreet?.value || "").trim();
  const houseNumber = String(onboardingInstitutionHouseNumber?.value || "").trim();
  const postcode = String(onboardingInstitutionPostcode?.value || "").trim();
  const city = String(onboardingInstitutionCity?.value || "").trim();
  const streetBlock = [street, houseNumber].filter(Boolean).join(" ");
  const cityBlock = [postcode, city].filter(Boolean).join(" ");
  return [streetBlock, cityBlock].filter(Boolean).join(", ");
}

function buildOnboardingDepotAddress(depot) {
  const street = String(depot?.strasse || "").trim();
  const houseNumber = String(depot?.hausnummer || "").trim();
  const postcode = String(depot?.postleitzahl || "").trim();
  const city = String(depot?.stadt || "").trim();
  const streetBlock = [street, houseNumber].filter(Boolean).join(" ");
  const cityBlock = [postcode, city].filter(Boolean).join(" ");
  return [streetBlock, cityBlock].filter(Boolean).join(", ");
}

function validateOnboardingInstitutionAddressFields() {
  const street = String(onboardingInstitutionStreet?.value || "").trim();
  const houseNumber = String(onboardingInstitutionHouseNumber?.value || "").trim();
  const postcode = String(onboardingInstitutionPostcode?.value || "").trim();
  const city = String(onboardingInstitutionCity?.value || "").trim();
  if (!street || !houseNumber || !postcode || !city) {
    throw new Error("Bitte Strasse, Hausnummer, Postleitzahl und Stadt fuer die Institution erfassen.");
  }
  if (!/^\d{5}$/.test(postcode)) {
    throw new Error("Postleitzahl muss genau 5 Ziffern enthalten.");
  }
}

async function geocodeOnboardingInstitutionAddress() {
  validateOnboardingInstitutionAddressFields();
  const address = buildOnboardingInstitutionAddress();
  if (!address) {
    throw new Error("Bitte zuerst Strasse, Hausnummer, Postleitzahl und Stadt erfassen.");
  }
  const params = new URLSearchParams({ q: address });
  const payload = await (await apiFetch(`/geo/geocode?${params.toString()}`)).json();
  if (onboardingInstitutionLatitude instanceof HTMLInputElement) {
    onboardingInstitutionLatitude.value = String(payload.latitude ?? "");
  }
  if (onboardingInstitutionLongitude instanceof HTMLInputElement) {
    onboardingInstitutionLongitude.value = String(payload.longitude ?? "");
  }
}

function buildOnboardingPayload() {
  const institutionName = String(onboardingInstitutionName?.value || "").trim();
  const praeparate = parseOnboardingPraeparate();
  if (!institutionName) throw new Error("Bitte Institutionsname eintragen.");
  if (!praeparate.length) throw new Error("Bitte mindestens ein Praeparat erfassen.");
  if (!onboardingDepots.length) throw new Error("Bitte mindestens ein Notfalldepot anlegen.");

  const normalizedDepots = onboardingDepots.map((depot) => {
    const name = String(depot.name || "").trim();
    if (!name) throw new Error("Jedes Depot benoetigt einen Namen.");
    const assignments = Array.from(new Set((depot.praeparate || []).map((nameItem) => String(nameItem || "").trim())))
      .filter(Boolean)
      .map((nameItem) => ({ praeparat_name: nameItem, sollbestand: 0 }));
    if (!assignments.length) {
      throw new Error(`Depot '${name}' muss mindestens ein Praeparat zugeordnet haben.`);
    }
    return {
      name,
      adresse: buildOnboardingDepotAddress(depot) || null,
      strasse: String(depot.strasse || "").trim() || null,
      hausnummer: String(depot.hausnummer || "").trim() || null,
      postleitzahl: String(depot.postleitzahl || "").trim() || null,
      stadt: String(depot.stadt || "").trim() || null,
      telefon: String(depot.telefon || "").trim() || null,
      email: String(depot.email || "").trim() || null,
      latitude: String(depot.latitude || "").trim() ? Number(depot.latitude) : null,
      longitude: String(depot.longitude || "").trim() ? Number(depot.longitude) : null,
      assignments,
    };
  });

  return {
    institution: {
      name: institutionName,
      adresse: buildOnboardingInstitutionAddress() || null,
      strasse: String(onboardingInstitutionStreet?.value || "").trim() || null,
      hausnummer: String(onboardingInstitutionHouseNumber?.value || "").trim() || null,
      postleitzahl: String(onboardingInstitutionPostcode?.value || "").trim() || null,
      stadt: String(onboardingInstitutionCity?.value || "").trim() || null,
      latitude: onboardingInstitutionLatitude?.value ? Number(onboardingInstitutionLatitude.value) : null,
      longitude: onboardingInstitutionLongitude?.value ? Number(onboardingInstitutionLongitude.value) : null,
    },
    praeparate,
    depots: normalizedDepots,
  };
}

function updateOnboardingReview() {
  if (!onboardingReview) return;
  try {
    const payload = buildOnboardingPayload();
    onboardingReview.textContent = JSON.stringify(payload, null, 2);
  } catch (error) {
    onboardingReview.textContent = error instanceof Error ? error.message : "Pruefung fehlgeschlagen.";
  }
}

function createOnboardingDepotCard(depot, index) {
  const card = document.createElement("div");
  card.className = "onboarding-depot-card";
  const options = parseOnboardingPraeparate()
    .map(
      (item) =>
        `<option value="${escapeHtml(item.name)}" ${depot.praeparate.includes(item.name) ? "selected" : ""}>${escapeHtml(item.name)}</option>`,
    )
    .join("");
  card.innerHTML = `
    <h4>Depot ${index + 1}</h4>
    <div class="grid two-col">
      <label>Name<input type="text" data-onboarding-depot-field="name" value="${escapeHtml(depot.name || "")}" /></label>
      <label>Strasse<input type="text" data-onboarding-depot-field="strasse" value="${escapeHtml(depot.strasse || "")}" /></label>
      <label>Hausnummer<input type="text" data-onboarding-depot-field="hausnummer" value="${escapeHtml(depot.hausnummer || "")}" /></label>
      <label>Postleitzahl<input type="text" data-onboarding-depot-field="postleitzahl" value="${escapeHtml(depot.postleitzahl || "")}" /></label>
      <label>Stadt<input type="text" data-onboarding-depot-field="stadt" value="${escapeHtml(depot.stadt || "")}" /></label>
      <label>Telefon<input type="text" data-onboarding-depot-field="telefon" value="${escapeHtml(depot.telefon || "")}" /></label>
      <label>E-Mail<input type="email" data-onboarding-depot-field="email" value="${escapeHtml(depot.email || "")}" /></label>
      <label>Latitude<input type="number" step="any" readonly data-onboarding-depot-field="latitude" value="${escapeHtml(depot.latitude || "")}" /></label>
      <label>Longitude<input type="number" step="any" readonly data-onboarding-depot-field="longitude" value="${escapeHtml(depot.longitude || "")}" /></label>
      <label>Praeparate (Mehrfachauswahl)
        <select data-onboarding-depot-field="praeparate" multiple size="6">${options}</select>
      </label>
    </div>
    <div class="actions">
      <button type="button" data-onboarding-geocode-depot="${index}">Depot-Koordinaten berechnen</button>
      <button type="button" data-onboarding-remove-depot="${index}">Depot entfernen</button>
    </div>
  `;
  card.addEventListener("input", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;
    const field = target.getAttribute("data-onboarding-depot-field");
    if (!field) return;
    if (field === "praeparate" && target instanceof HTMLSelectElement) {
      onboardingDepots[index].praeparate = Array.from(target.selectedOptions).map((opt) => opt.value);
    } else if (target instanceof HTMLInputElement) {
      onboardingDepots[index][field] = target.value;
    }
    updateOnboardingReview();
  });
  const removeButton = card.querySelector(`[data-onboarding-remove-depot="${index}"]`);
  removeButton?.addEventListener("click", () => {
    onboardingDepots.splice(index, 1);
    renderOnboardingDepots();
  });
  const geocodeButton = card.querySelector(`[data-onboarding-geocode-depot="${index}"]`);
  geocodeButton?.addEventListener("click", async () => {
    try {
      const q = buildOnboardingDepotAddress(onboardingDepots[index]);
      if (!q) throw new Error("Bitte Strasse, Hausnummer, Postleitzahl und Stadt fuer das Depot erfassen.");
      const payload = await (await apiFetch(`/geo/geocode?q=${encodeURIComponent(q)}`)).json();
      onboardingDepots[index].latitude = String(payload.latitude ?? "");
      onboardingDepots[index].longitude = String(payload.longitude ?? "");
      renderOnboardingDepots();
      if (onboardingStatus) onboardingStatus.textContent = `Depot ${index + 1}: Koordinaten gesetzt.`;
    } catch (error) {
      if (onboardingStatus) onboardingStatus.textContent = error instanceof Error ? error.message : "Geokodierung fehlgeschlagen.";
    }
  });
  return card;
}

function renderOnboardingDepots() {
  if (!onboardingDepotsList) return;
  onboardingDepotsList.innerHTML = "";
  onboardingDepots.forEach((depot, index) => {
    onboardingDepotsList.appendChild(createOnboardingDepotCard(depot, index));
  });
  updateOnboardingReview();
}

function setOnboardingStep(nextIndex) {
  onboardingStepIndex = Math.max(0, Math.min(3, Number(nextIndex) || 0));
  const steps = [onboardingStep1, onboardingStep2, onboardingStep3, onboardingStep4];
  steps.forEach((step, index) => {
    if (!(step instanceof HTMLElement)) return;
    step.classList.toggle("hidden", index !== onboardingStepIndex);
  });
  if (onboardingStepLabel) onboardingStepLabel.textContent = `Schritt ${onboardingStepIndex + 1} von 4`;
  if (onboardingPrevButton) onboardingPrevButton.disabled = onboardingStepIndex === 0;
  if (onboardingNextButton) onboardingNextButton.classList.toggle("hidden", onboardingStepIndex === 3);
  if (onboardingSubmitButton) onboardingSubmitButton.classList.toggle("hidden", onboardingStepIndex !== 3);
  if (onboardingStepIndex === 3) updateOnboardingReview();
}

function validateOnboardingStep(index) {
  if (index === 0) {
    if (!String(onboardingInstitutionName?.value || "").trim()) {
      throw new Error("Bitte Institutionsname eintragen.");
    }
    validateOnboardingInstitutionAddressFields();
    if (!String(onboardingInstitutionLatitude?.value || "").trim() || !String(onboardingInstitutionLongitude?.value || "").trim()) {
      throw new Error("Bitte Koordinaten ueber 'Koordinaten aus Adresse berechnen' setzen.");
    }
  }
  if (index === 1) {
    if (!parseOnboardingPraeparate().length) {
      throw new Error("Bitte mindestens ein Praeparat erfassen.");
    }
  }
  if (index === 2) {
    if (!onboardingDepots.length) throw new Error("Bitte mindestens ein Notfalldepot anlegen.");
    for (const depot of onboardingDepots) {
      if (!String(depot.name || "").trim()) throw new Error("Jedes Depot benoetigt einen Namen.");
      if (!Array.isArray(depot.praeparate) || !depot.praeparate.length) {
        throw new Error(`Depot '${depot.name || "ohne Namen"}' braucht mindestens ein Praeparat.`);
      }
    }
  }
}

async function checkAndOpenOnboardingIfRequired() {
  if (onboardingAutoOpened || !isAdminUser() || !hasPermission("masterdata_read")) return;
  try {
    const statusPayload = await (await apiFetch("/onboarding/status")).json();
    if (statusPayload && statusPayload.requires_onboarding) {
      onboardingAutoOpened = true;
      showPage("onboarding-section");
      if (onboardingStatus) {
        onboardingStatus.textContent = "Neue Datenbank erkannt: Bitte Einrichtung abschliessen.";
      }
    }
  } catch (_error) {
    // Non-blocking for normal app operation.
  }
}

async function submitOnboardingSetup() {
  const payload = buildOnboardingPayload();
  if (onboardingStatus) onboardingStatus.textContent = "Einrichtung wird gespeichert...";
  const result = await (
    await apiFetch("/onboarding/institution-setup", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    })
  ).json();
  if (onboardingStatus) {
    onboardingStatus.textContent = `Einrichtung abgeschlossen. Institution-ID: ${result.institution_id}`;
  }
  await loadMasterData();
  showPage("dashboard-section");
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
  syncSidebarShortcutState(target.id);
  for (const quickLink of mobileQuickLinks) {
    const targetId = quickLink.getAttribute("data-page-target") || "";
    quickLink.classList.toggle("active", targetId === target.id);
  }
  for (const button of subpageLinks) {
    const pageTarget = button.getAttribute("data-page-target") || "";
    button.classList.toggle("active", pageTarget === target.id);
  }
  activePageId = target.id;
  if (workspaceContext) {
    workspaceContext.textContent = PAGE_CONTEXT_LABELS[target.id] || "Desktop-UX mit moderner Web-UI";
  }
  if (workspaceArea) {
    workspaceArea.textContent = PAGE_AREA_LABELS[target.id] || "Arbeitsbereich";
  }
  spotlightSection(target.id);

  if (updateHash) {
    window.history.replaceState(null, "", `#${target.id}`);
  }
  window.dispatchEvent(
    new CustomEvent("ndhub-page-change", {
      detail: { pageId: target.id },
    }),
  );
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

function initializeResponsiveTables() {
  if (typeof uiUtils.wrapResponsiveTables === "function") {
    uiUtils.wrapResponsiveTables();
  }
}

function isReactIslandMounted(islandName) {
  const mounted = window.NDHubReactIslands;
  return mounted instanceof Set && mounted.has(islandName);
}

function applyReactIslandVisibility() {
  const mappings = [
    { island: "institutions-map", reactId: "react-institutions-map", legacyIds: [] },
    { island: "admin-workspace", reactId: "react-admin-workspace", legacyIds: [] },
    { island: "institutions-admin", reactId: "react-institutions-admin", legacyIds: [] },
    { island: "bewegung-create-form", reactId: "react-bewegung-create-form", legacyIds: ["bewegung-create-legacy-content"] },
    { island: "desktop-sync-form", reactId: "react-desktop-sync-form", legacyIds: ["desktop-sync-form-legacy-content"] },
    { island: "desktop-sync-archive", reactId: "react-desktop-sync-archive", legacyIds: ["desktop-sync-archive-table"] },
    { island: "users-table", reactId: "react-users-table", legacyIds: ["users-table"] },
    { island: "users-admin-form", reactId: "react-users-admin-form", legacyIds: ["users-form-legacy-content"] },
    { island: "report-table", reactId: "react-report-table", legacyIds: ["report-table"] },
    { island: "account-manager", reactId: "react-account-manager", legacyIds: ["account-legacy-content"] },
    { island: "dashboard-overview", reactId: "react-dashboard-overview", legacyIds: ["dashboard-legacy-content"] },
    { island: "bewegungen-history", reactId: "react-bewegungen-history", legacyIds: ["bewegungen-table"] },
    { island: "audit-table", reactId: "react-audit-table", legacyIds: ["audit-table"] },
    { island: "verfall-overview", reactId: "react-verfall-overview", legacyIds: ["verfall-legacy-content"] },
    { island: "import-manager", reactId: "react-import-manager", legacyIds: ["import-legacy-content"] },
    { island: "backup-manager", reactId: "react-backup-manager", legacyIds: ["backup-legacy-content"] },
    { island: "email-manager", reactId: "react-email-manager", legacyIds: ["email-legacy-content"] },
    { island: "masterdata-manager", reactId: "react-masterdata-manager", legacyIds: ["masterdata-legacy-content"] },
    { island: "assignment-manager", reactId: "react-assignment-manager", legacyIds: ["assignment-legacy-content"] },
    { island: "contacts-manager", reactId: "react-contacts-manager", legacyIds: ["contacts-legacy-content"] },
  ];
  for (const mapping of mappings) {
    const reactNode = document.getElementById(mapping.reactId);
    const mounted = isReactIslandMounted(mapping.island);
    if (reactNode) reactNode.classList.toggle("hidden", !mounted);
    for (const legacyId of mapping.legacyIds) {
      const legacyNode = document.getElementById(legacyId);
      if (legacyNode) legacyNode.classList.toggle("hidden", mounted);
    }
  }
}

function enhanceActionButtons() {
  const buttons = Array.from(document.querySelectorAll("button"));
  const explicitPrimaryIds = new Set([
    "login-button",
    "dashboard-refresh",
    "bewegung-save",
    "report-load",
    "save-depot",
    "save-praeparat",
    "save-contact",
    "save-assignment",
  ]);
  const explicitDangerIds = new Set([
    "logout-button",
    "delete-depot",
    "delete-praeparat",
    "delete-contact",
    "backup-restore",
  ]);

  for (const button of buttons) {
    if (button.classList.contains("btn-primary") || button.classList.contains("btn-secondary") || button.classList.contains("btn-danger")) {
      continue;
    }
    const intent = (button.getAttribute("data-ui-intent") || "").toLowerCase();
    if (intent === "danger") {
      button.classList.add("btn-danger");
      continue;
    }
    if (intent === "primary") {
      button.classList.add("btn-primary");
      continue;
    }
    if (intent === "secondary") {
      button.classList.add("btn-secondary");
      continue;
    }

    const id = (button.id || "").toLowerCase();
    if (explicitDangerIds.has(id)) {
      button.classList.add("btn-danger");
      continue;
    }
    if (explicitPrimaryIds.has(id) || id.includes("save")) {
      button.classList.add("btn-primary");
      continue;
    }
    if (id.includes("prev") || id.includes("next") || id.includes("reload") || id.includes("download")) {
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
  if (target?.id === "depots-list" && isReactIslandMounted("masterdata-manager")) return;
  if (target?.id === "praeparate-list" && isReactIslandMounted("masterdata-manager")) return;
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

function renderBewegungen(rows, options = {}) {
  if (isReactIslandMounted("bewegungen-history")) return;
  bewegungenBody.innerHTML = "";
  const emptyMessage = String(options.emptyMessage || "Keine Bewegungen fuer die aktuelle Filterung.");
  if (!rows.length) {
    renderEmptyTableState(bewegungenBody, 9, emptyMessage);
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
          <button type="button" data-action="download-attachment" data-id="${row.id}" data-filename="${encodeURIComponent(row.datei_name || "")}">Download</button>
        `
      : "-";
    safeAppendCell(tr, row.id);
    safeAppendCell(tr, row.typ || "");
    safeAppendCell(tr, row.charge || "");
    safeAppendCell(tr, row.verfall || "");
    safeAppendCell(tr, row.anzahl || "");
    safeAppendCell(tr, row.depot || row.depot_id || "");
    safeAppendCell(tr, row.praeparat || row.praeparat_id || "");
    safeAppendHtmlCell(tr, attachmentLabel);
    safeAppendHtmlCell(tr, attachmentActions);
    bewegungenBody.appendChild(tr);
  }
  pulseElement(document.getElementById("bewegungen-table"));
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
  if (isReactIslandMounted("dashboard-overview")) return;
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
  if (isReactIslandMounted("verfall-overview")) return;
  if (!verfallTableBody) return;
  verfallTableBody.innerHTML = "";
  if (!rows.length) {
    renderEmptyTableState(verfallTableBody, 7, "Keine Verfallspositionen fuer diese Filter.");
    return;
  }
  for (const row of rows) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
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

function renderNotificationList(rows) {
  lastNotificationRows = Array.isArray(rows) ? rows : [];
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

function enableClickToggleMultiSelect(select) {
  if (!(select instanceof HTMLSelectElement)) return;
  if (!select.multiple) return;
  if (select.dataset.clickToggleReady === "1") return;
  select.dataset.clickToggleReady = "1";
  select.addEventListener("mousedown", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLOptionElement)) return;
    event.preventDefault();
    target.selected = !target.selected;
    select.focus();
    select.dispatchEvent(new Event("change", { bubbles: true }));
  });
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
  if (isReactIslandMounted("report-table")) return;
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
  canvas.dataset.chartHeight = String(minHeight);
  canvas.style.height = `${minHeight}px`;
  card.appendChild(titleEl);
  card.appendChild(canvas);
  reportCharts.appendChild(card);
  return canvas;
}

function getChartContext(canvas, minWidth = 320) {
  if (!(canvas instanceof HTMLCanvasElement)) return null;
  const cssWidth = Math.max(minWidth, Math.round(canvas.clientWidth || minWidth));
  const configuredHeight = Number(canvas.dataset.chartHeight || 0);
  const cssHeight = Math.max(120, Math.round(configuredHeight || canvas.clientHeight || canvas.height || 240));
  const dpr = Math.max(1, Math.min(3, Number(window.devicePixelRatio) || 1));

  canvas.style.width = `${cssWidth}px`;
  canvas.style.height = `${cssHeight}px`;

  const backingWidth = Math.max(1, Math.round(cssWidth * dpr));
  const backingHeight = Math.max(1, Math.round(cssHeight * dpr));
  if (canvas.width !== backingWidth) canvas.width = backingWidth;
  if (canvas.height !== backingHeight) canvas.height = backingHeight;

  const ctx = canvas.getContext("2d");
  if (!ctx) return null;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, cssWidth, cssHeight);
  return { ctx, width: cssWidth, height: cssHeight };
}

function appendChartLegendBelow(canvas, items) {
  if (!(canvas instanceof HTMLCanvasElement)) return;
  const card = canvas.parentElement;
  if (!(card instanceof HTMLElement)) return;
  const existing = card.querySelector(".chart-inline-legend");
  if (existing) existing.remove();
  if (!Array.isArray(items) || !items.length) return;
  const legend = document.createElement("div");
  legend.className = "chart-inline-legend";
  legend.style.display = "flex";
  legend.style.flexWrap = "wrap";
  legend.style.gap = "10px";
  legend.style.marginTop = "8px";
  legend.style.fontSize = "12px";
  legend.style.color = CHART_THEME.text;
  for (const item of items) {
    const entry = document.createElement("span");
    entry.style.display = "inline-flex";
    entry.style.alignItems = "center";
    entry.style.gap = "6px";
    const swatch = document.createElement("span");
    swatch.style.display = "inline-block";
    swatch.style.width = "10px";
    swatch.style.height = "10px";
    swatch.style.borderRadius = "2px";
    swatch.style.background = item.color || CHART_THEME.neutral;
    const label = document.createElement("span");
    label.textContent = item.label || "";
    entry.appendChild(swatch);
    entry.appendChild(label);
    legend.appendChild(entry);
  }
  card.appendChild(legend);
}

function splitLabelLines(ctx, text, maxWidth) {
  const raw = String(text || "").trim();
  if (!raw) return [""];
  const tokens = raw
    .replaceAll("/", "/ ")
    .replaceAll(",", ", ")
    .replaceAll("(", " (")
    .replaceAll(")", ") ")
    .split(/\s+/)
    .filter(Boolean);
  if (!tokens.length) return [raw];
  const lines = [];
  let current = "";
  for (const token of tokens) {
    const next = current ? `${current} ${token}` : token;
    if (ctx.measureText(next).width <= maxWidth) {
      current = next;
      continue;
    }
    if (current) lines.push(current);
    if (ctx.measureText(token).width <= maxWidth) {
      current = token;
      continue;
    }
    let chunk = "";
    for (const ch of token) {
      const candidate = `${chunk}${ch}`;
      if (ctx.measureText(candidate).width <= maxWidth) {
        chunk = candidate;
      } else {
        if (chunk) lines.push(chunk);
        chunk = ch;
      }
    }
    current = chunk;
  }
  if (current) lines.push(current);
  return lines.length ? lines : [raw];
}

function drawGroupedBars(canvas, labels, seriesList, options = {}) {
  if (!(canvas instanceof HTMLCanvasElement)) return;
  const prepared = getChartContext(canvas, 320);
  if (!prepared) return;
  const { ctx, width, height } = prepared;
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
  const splitLabelLines = (text, maxWidth) => {
    const raw = String(text || "").trim();
    if (!raw) return [""];
    const tokens = raw
      .replaceAll("/", "/ ")
      .replaceAll(",", ", ")
      .split(/\s+/)
      .filter(Boolean);
    if (!tokens.length) return [raw];
    const lines = [];
    let current = "";
    for (const token of tokens) {
      const next = current ? `${current} ${token}` : token;
      if (ctx.measureText(next).width <= maxWidth) {
        current = next;
        continue;
      }
      if (current) lines.push(current);
      if (ctx.measureText(token).width <= maxWidth) {
        current = token;
        continue;
      }
      let chunk = "";
      for (const ch of token) {
        const candidate = `${chunk}${ch}`;
        if (ctx.measureText(candidate).width <= maxWidth) {
          chunk = candidate;
        } else {
          if (chunk) lines.push(chunk);
          chunk = ch;
        }
      }
      current = chunk;
    }
    if (current) lines.push(current);
    return lines.length ? lines : [raw];
  };

  const baseFont = "10px Inter, Arial, sans-serif";
  ctx.font = baseFont;
  const useVerticalLabels = options.labelOrientation === "vertical" || (options.labelOrientation !== "horizontal" && labels.length >= 8);
  const provisionalPlotWidth = Math.max(40, width - left - right);
  const provisionalGroupWidth = provisionalPlotWidth / Math.max(1, labels.length);
  const labelWrapWidth = Math.max(34, provisionalGroupWidth * 0.92);
  const labelLinesByIndex = labels.map((label) => splitLabelLines(label, labelWrapWidth));
  const maxVerticalLabelWidth = Math.max(
    1,
    ...labels.map((label) => ctx.measureText(String(label || "")).width),
  );
  const maxLabelLines = Math.max(1, ...labelLinesByIndex.map((lines) => lines.length));
  const labelLineHeight = 12;
  const bottom = useVerticalLabels ? 24 + Math.ceil(maxVerticalLabelWidth) : 28 + maxLabelLines * labelLineHeight;
  const minPlotHeight = 150;
  const minHeightNeeded = top + bottom + minPlotHeight;
  if (!options._resized && height < minHeightNeeded) {
    canvas.dataset.chartHeight = String(minHeightNeeded);
    canvas.style.height = `${minHeightNeeded}px`;
    drawGroupedBars(canvas, labels, seriesList, { ...options, _resized: true });
    return;
  }
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
  ctx.font = baseFont;
  if (useVerticalLabels) {
    for (let idx = 0; idx < labels.length; idx += 1) {
      const xCenter = left + idx * groupWidth + groupWidth / 2;
      const label = String(labels[idx] || "");
      const yBase = height - 8;
      ctx.save();
      ctx.translate(xCenter, yBase);
      // Von unten nach oben lesbar.
      ctx.rotate(-Math.PI / 2);
      ctx.fillText(label, 0, 0);
      ctx.restore();
    }
  } else {
    for (let idx = 0; idx < labels.length; idx += 1) {
      const xCenter = left + idx * groupWidth + groupWidth / 2;
      const lines = labelLinesByIndex[idx] || [String(labels[idx] || "")];
      for (let lineIdx = 0; lineIdx < lines.length; lineIdx += 1) {
        const line = lines[lineIdx];
        const textWidth = ctx.measureText(line).width;
        const y = height - bottom + 14 + lineIdx * labelLineHeight;
        ctx.fillText(line, xCenter - textWidth / 2, y);
      }
    }
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
  const prepared = getChartContext(canvas, 320);
  if (!prepared) return;
  const { ctx, width, height } = prepared;
  if (!labels.length || !values.length) return;

  ctx.font = "11px Inter, Arial, sans-serif";
  const right = 18;
  const top = 18;
  const bottom = 22;
  const maxLabelArea = Math.max(160, Math.min(320, width * 0.42));
  const labelWrapWidth = maxLabelArea - 14;
  const wrappedLabels = labels.map((label) => splitLabelLines(ctx, label, labelWrapWidth));
  const maxLabelWidth = Math.max(80, ...wrappedLabels.flat().map((line) => ctx.measureText(line).width));
  const left = Math.min(maxLabelArea, maxLabelWidth + 16);
  const lineHeight = 12;
  const rowHeight = Math.max(26, wrappedLabels.reduce((max, lines) => Math.max(max, lines.length * lineHeight + 8), 26));
  const minHeightNeeded = top + bottom + rowHeight * labels.length;
  if (!options._resized && height < minHeightNeeded) {
    canvas.dataset.chartHeight = String(minHeightNeeded);
    canvas.style.height = `${minHeightNeeded}px`;
    drawHorizontalBars(canvas, labels, values, { ...options, _resized: true });
    return;
  }
  const plotWidth = width - left - right;
  const plotHeight = height - top - bottom;
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
    const lines = wrappedLabels[idx] || [String(labels[idx] || "")];
    const linesHeight = lines.length * lineHeight;
    let yText = yCenter - linesHeight / 2 + lineHeight - 2;
    for (const line of lines) {
      ctx.fillText(line, 6, yText);
      yText += lineHeight;
    }
    ctx.fillText(`${Math.round(value)}`, left + w + 6, yCenter + 4);
  }
}

function drawHorizontalPairBars(canvas, labels, firstValues, secondValues, options = {}) {
  if (!(canvas instanceof HTMLCanvasElement)) return;
  const prepared = getChartContext(canvas, 320);
  if (!prepared) return;
  const { ctx, width, height } = prepared;
  if (!labels.length || !firstValues.length || !secondValues.length) return;

  ctx.font = "11px Inter, Arial, sans-serif";
  const right = 18;
  const top = 18;
  const bottom = 22;
  const maxLabelArea = Math.max(170, Math.min(340, width * 0.45));
  const labelWrapWidth = maxLabelArea - 14;
  const wrappedLabels = labels.map((label) => splitLabelLines(ctx, label, labelWrapWidth));
  const maxLabelWidth = Math.max(90, ...wrappedLabels.flat().map((line) => ctx.measureText(line).width));
  const left = Math.min(maxLabelArea, maxLabelWidth + 16);
  const lineHeight = 12;
  const rowHeight = Math.max(34, wrappedLabels.reduce((max, lines) => Math.max(max, lines.length * lineHeight + 12), 34));
  const minHeightNeeded = top + bottom + rowHeight * labels.length;
  if (!options._resized && height < minHeightNeeded) {
    canvas.dataset.chartHeight = String(minHeightNeeded);
    canvas.style.height = `${minHeightNeeded}px`;
    drawHorizontalPairBars(canvas, labels, firstValues, secondValues, { ...options, _resized: true });
    return;
  }

  const plotWidth = width - left - right;
  const maxValue = Math.max(
    1,
    ...firstValues.map((value) => Number(value || 0)),
    ...secondValues.map((value) => Number(value || 0)),
  );
  const barHeight = Math.max(8, rowHeight * 0.28);

  ctx.strokeStyle = CHART_THEME.axis;
  ctx.beginPath();
  ctx.moveTo(left, top);
  ctx.lineTo(left, height - bottom);
  ctx.stroke();

  for (let idx = 0; idx < labels.length; idx += 1) {
    const yCenter = top + idx * rowHeight + rowHeight / 2;
    const first = Number(firstValues[idx] || 0);
    const second = Number(secondValues[idx] || 0);
    const w1 = Math.max(1, (first / maxValue) * plotWidth);
    const w2 = Math.max(1, (second / maxValue) * plotWidth);

    const y1 = yCenter - barHeight - 2;
    const y2 = yCenter + 2;
    ctx.fillStyle = options.firstColor || "#3b82f6";
    ctx.fillRect(left, y1, w1, barHeight);
    ctx.fillStyle = options.secondColor || CHART_THEME.positive;
    ctx.fillRect(left, y2, w2, barHeight);

    ctx.fillStyle = CHART_THEME.text;
    const lines = wrappedLabels[idx] || [String(labels[idx] || "")];
    const linesHeight = lines.length * lineHeight;
    let yText = yCenter - linesHeight / 2 + lineHeight - 2;
    for (const line of lines) {
      ctx.fillText(line, 6, yText);
      yText += lineHeight;
    }

    ctx.fillText(`${Math.round(first)}`, left + w1 + 6, y1 + barHeight - 1);
    ctx.fillText(`${Math.round(second)}`, left + w2 + 6, y2 + barHeight - 1);
  }
}

function drawHorizontalDeltaBars(canvas, labels, values, options = {}) {
  if (!(canvas instanceof HTMLCanvasElement)) return;
  const prepared = getChartContext(canvas, 320);
  if (!prepared) return;
  const { ctx, width, height } = prepared;
  if (!labels.length || !values.length) return;

  ctx.font = "11px Inter, Arial, sans-serif";
  const right = 18;
  const top = 18;
  const bottom = 22;
  const maxLabelArea = Math.max(170, Math.min(340, width * 0.45));
  const labelWrapWidth = maxLabelArea - 14;
  const wrappedLabels = labels.map((label) => splitLabelLines(ctx, label, labelWrapWidth));
  const maxLabelWidth = Math.max(90, ...wrappedLabels.flat().map((line) => ctx.measureText(line).width));
  const left = Math.min(maxLabelArea, maxLabelWidth + 16);
  const lineHeight = 12;
  const rowHeight = Math.max(32, wrappedLabels.reduce((max, lines) => Math.max(max, lines.length * lineHeight + 10), 32));
  const minHeightNeeded = top + bottom + rowHeight * labels.length;
  if (!options._resized && height < minHeightNeeded) {
    canvas.dataset.chartHeight = String(minHeightNeeded);
    canvas.style.height = `${minHeightNeeded}px`;
    drawHorizontalDeltaBars(canvas, labels, values, { ...options, _resized: true });
    return;
  }

  const plotWidth = width - left - right;
  const maxAbs = Math.max(1, ...values.map((value) => Math.abs(Number(value || 0))));
  const zeroX = left + plotWidth / 2;
  const halfWidth = plotWidth / 2;
  const barHeight = Math.max(10, rowHeight * 0.6);

  ctx.strokeStyle = CHART_THEME.axis;
  ctx.beginPath();
  ctx.moveTo(zeroX, top);
  ctx.lineTo(zeroX, height - bottom);
  ctx.stroke();

  for (let idx = 0; idx < labels.length; idx += 1) {
    const yCenter = top + idx * rowHeight + rowHeight / 2;
    const y = yCenter - barHeight / 2;
    const value = Number(values[idx] || 0);
    const w = Math.max(1, (Math.abs(value) / maxAbs) * halfWidth);
    const x = value >= 0 ? zeroX : zeroX - w;
    ctx.fillStyle = value >= 0 ? (options.positiveColor || CHART_THEME.positive) : (options.negativeColor || CHART_THEME.negative);
    ctx.fillRect(x, y, w, barHeight);

    ctx.fillStyle = CHART_THEME.text;
    const lines = wrappedLabels[idx] || [String(labels[idx] || "")];
    const linesHeight = lines.length * lineHeight;
    let yText = yCenter - linesHeight / 2 + lineHeight - 2;
    for (const line of lines) {
      ctx.fillText(line, 6, yText);
      yText += lineHeight;
    }

    const valueX = value >= 0 ? x + w + 6 : x - 18;
    ctx.fillText(`${Math.round(value)}`, valueX, yCenter + 4);
  }
}

function drawMatrixHeatmap(canvas, rows, options = {}) {
  if (!(canvas instanceof HTMLCanvasElement)) return;
  const prepared = getChartContext(canvas, 520);
  if (!prepared) return;
  const { ctx, width, height } = prepared;
  if (!Array.isArray(rows) || !rows.length) return;

  const depots = Array.from(new Set(rows.map((row) => String(row.depot || "").trim()).filter(Boolean)));
  const praeparate = Array.from(new Set(rows.map((row) => String(row.praeparat || "").trim()).filter(Boolean)));
  if (!depots.length || !praeparate.length) return;

  ctx.font = "11px Inter, Arial, sans-serif";
  const maxDepotLabelWidth = Math.max(80, ...depots.map((label) => ctx.measureText(label).width));
  const left = Math.min(220, maxDepotLabelWidth + 14);
  const praeparatLabelMax = Math.max(40, ...praeparate.map((label) => ctx.measureText(String(label || "")).width));
  const top = Math.min(180, Math.max(72, Math.ceil(praeparatLabelMax) + 12));
  const right = 20;
  const bottom = 24;
  const plotWidth = Math.max(120, width - left - right);
  const plotHeight = Math.max(100, height - top - bottom);
  const cellWidth = plotWidth / Math.max(1, praeparate.length);
  const cellHeight = plotHeight / Math.max(1, depots.length);

  const matrix = new Map();
  let maxAbs = 0;
  for (const row of rows) {
    const depot = String(row.depot || "").trim();
    const praeparat = String(row.praeparat || "").trim();
    if (!depot || !praeparat) continue;
    const value = Number(row.differenz || 0);
    matrix.set(`${depot}|||${praeparat}`, value);
    maxAbs = Math.max(maxAbs, Math.abs(value));
  }
  maxAbs = Math.max(1, maxAbs);

  const colorFor = (value) => {
    if (!Number.isFinite(value) || value === 0) return "rgba(148, 163, 184, 0.15)";
    const ratio = Math.min(1, Math.abs(value) / maxAbs);
    const alpha = 0.2 + ratio * 0.7;
    if (value > 0) return `rgba(34, 197, 94, ${alpha})`;
    return `rgba(239, 68, 68, ${alpha})`;
  };

  // Grid cells
  for (let yIdx = 0; yIdx < depots.length; yIdx += 1) {
    const depot = depots[yIdx];
    const y = top + yIdx * cellHeight;
    for (let xIdx = 0; xIdx < praeparate.length; xIdx += 1) {
      const praeparat = praeparate[xIdx];
      const x = left + xIdx * cellWidth;
      const value = Number(matrix.get(`${depot}|||${praeparat}`) || 0);
      ctx.fillStyle = colorFor(value);
      ctx.fillRect(x + 1, y + 1, Math.max(1, cellWidth - 2), Math.max(1, cellHeight - 2));
    }
  }

  // Grid lines
  ctx.strokeStyle = "rgba(148, 163, 184, 0.25)";
  ctx.lineWidth = 1;
  for (let yIdx = 0; yIdx <= depots.length; yIdx += 1) {
    const y = top + yIdx * cellHeight;
    ctx.beginPath();
    ctx.moveTo(left, y);
    ctx.lineTo(left + plotWidth, y);
    ctx.stroke();
  }
  for (let xIdx = 0; xIdx <= praeparate.length; xIdx += 1) {
    const x = left + xIdx * cellWidth;
    ctx.beginPath();
    ctx.moveTo(x, top);
    ctx.lineTo(x, top + plotHeight);
    ctx.stroke();
  }

  // Row labels (depots)
  ctx.fillStyle = CHART_THEME.text;
  ctx.textBaseline = "middle";
  for (let yIdx = 0; yIdx < depots.length; yIdx += 1) {
    const yCenter = top + yIdx * cellHeight + cellHeight / 2;
    const label = depots[yIdx];
    const trimmed = label.length > 28 ? `${label.slice(0, 27)}…` : label;
    ctx.fillText(trimmed, 6, yCenter);
  }

  // Column labels (praeparate)
  ctx.fillStyle = CHART_THEME.text;
  ctx.textBaseline = "middle";
  ctx.font = "10px Inter, Arial, sans-serif";
  for (let xIdx = 0; xIdx < praeparate.length; xIdx += 1) {
    const xCenter = left + xIdx * cellWidth + cellWidth / 2;
    const labelRaw = String(praeparate[xIdx] || "");
    const label = labelRaw.length > 28 ? `${labelRaw.slice(0, 27)}…` : labelRaw;
    ctx.save();
    ctx.translate(xCenter, top - 6);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText(label, 0, 0);
    ctx.restore();
  }

  if (options.showSummary !== false) {
    ctx.textBaseline = "alphabetic";
    ctx.font = "10px Inter, Arial, sans-serif";
    ctx.fillText(`Praeparate: ${praeparate.length}`, left, height - 8);
    ctx.fillText(`Depots: ${depots.length}`, left + 110, height - 8);
    ctx.fillText(`Max |Differenz|: ${Math.round(maxAbs)}`, left + 190, height - 8);
  }
}

function drawLineAreaChart(canvas, labels, values, options = {}) {
  if (!(canvas instanceof HTMLCanvasElement)) return;
  const prepared = getChartContext(canvas, 320);
  if (!prepared) return;
  const { ctx, width, height } = prepared;
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
      showLegend: false,
    });
    appendChartLegendBelow(monthlyCanvas, [
      { label: "Zugang", color: CHART_THEME.positive },
      { label: "Abgang", color: CHART_THEME.neutral },
      { label: "Vernichtung", color: CHART_THEME.negative },
    ]);

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
    const sortedRows = rows
      .slice()
      .sort((a, b) => Math.abs(Number(b.differenz || 0)) - Math.abs(Number(a.differenz || 0)));
    const subset = reportBestandShowAll ? sortedRows : sortedRows.slice(0, 10);
    const labels = subset.map((row) => `${row.praeparat} (${row.depot})`);
    const balanceCanvas = createChartCanvasCard(
      reportBestandShowAll ? "Soll vs. Ist (Alle Positionen)" : "Soll vs. Ist (Top Abweichungen)",
      320,
    );
    drawHorizontalPairBars(
      balanceCanvas,
      labels,
      subset.map((row) => Number(row.sollbestand || 0)),
      subset.map((row) => Number(row.ist_bestand || 0)),
      { firstColor: "#3b82f6", secondColor: CHART_THEME.positive },
    );
    const diffCanvas = createChartCanvasCard(
      reportBestandShowAll ? "Differenz je Position (Alle Positionen)" : "Differenz je Position (Top Abweichungen)",
      320,
    );
    drawHorizontalDeltaBars(
      diffCanvas,
      labels,
      subset.map((row) => Number(row.differenz || 0)),
      { positiveColor: CHART_THEME.positive, negativeColor: CHART_THEME.negative },
    );
    if (reportChartLegend) {
      reportChartLegend.innerHTML = "";
      const info = document.createElement("span");
      info.textContent = reportBestandShowAll
        ? "Vollansicht: Alle Positionen mit vollstaendigen Labels."
        : "Fokusansicht: Top-10 Abweichungen mit vollstaendigen Labels.";
      reportChartLegend.appendChild(info);
      if (sortedRows.length > 10) {
        const toggleBtn = document.createElement("button");
        toggleBtn.type = "button";
        toggleBtn.className = "btn-secondary";
        toggleBtn.style.marginLeft = "8px";
        toggleBtn.textContent = reportBestandShowAll ? "Top 10 anzeigen" : "Alle anzeigen";
        toggleBtn.addEventListener("click", () => {
          reportBestandShowAll = !reportBestandShowAll;
          renderReportCharts(lastReportRows);
        });
        reportChartLegend.appendChild(toggleBtn);
      }
    }
    return;
  }

  if (typ === "ranking") {
    const labels = rows.map((row) => row.name || row.depot || row.praeparat || "Unbekannt").slice(0, 12);
    const values = rows.map((row) => Number(row.anzahl || 0)).slice(0, 12);
    const rankingCanvas = createChartCanvasCard("Top Ranking (Horizontal)", 300);
    drawHorizontalBars(rankingCanvas, labels, values, { color: CHART_THEME.purple });
    if (reportChartLegend) {
      reportChartLegend.textContent = "Ranking: primaer Abgaenge/Vernichtungen, bei fehlenden Daten Fallback auf alle Bewegungen.";
    }
    return;
  }

  if (typ === "matrix") {
    const maxRows = rows.slice(0, 220);
    const matrixCanvas = createChartCanvasCard("Matrix-Heatmap Soll/Ist-Abweichung", 360);
    drawMatrixHeatmap(matrixCanvas, maxRows);
    if (reportChartLegend) {
      reportChartLegend.textContent = "Heatmap: Gruen = Ueberschuss, Rot = Fehlbestand, Intensitaet = Abweichungsstaerke.";
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
  const openedWindow = window.open(blobUrl, "_blank", "noopener,noreferrer");
  if (!openedWindow) {
    URL.revokeObjectURL(blobUrl);
    throw new Error("Popup blockiert. Bitte Download verwenden oder Popups erlauben.");
  }
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
  if (isReactIslandMounted("audit-table")) return;
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
    safeAppendCell(tr, row.timestamp || "");
    safeAppendCell(tr, row.username || "");
    safeAppendHtmlCell(tr, `<span class="audit-badge ${escapeHtml(actionClass)}">${escapeHtml(action)}</span>`);
    safeAppendCell(tr, row.resource_type || "");
    safeAppendCell(tr, row.resource_id || "");
    safeAppendHtmlCell(tr, `<pre class="audit-details">${escapeHtml(detailsText)}</pre>`);
    auditBody.appendChild(tr);
  }
  pulseElement(document.getElementById("audit-table"));
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
  if (isReactIslandMounted("users-table")) return;
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
    safeAppendCell(tr, row.id);
    safeAppendCell(tr, row.username || "");
    safeAppendCell(tr, row.role || "");
    safeAppendCell(tr, row.email || "");
    safeAppendCell(tr, row.is_active ? "Ja" : "Nein");
    safeAppendCell(tr, permissionList.join(", ") || "-");
    safeAppendCell(tr, row.failed_attempts || 0);
    safeAppendCell(tr, row.locked_until || "-");
    safeAppendCell(tr, row.is_default_password ? "Ja" : "Nein");
    safeAppendCell(tr, row.last_login || "-");
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
    safeAppendCell(tr, row.timestamp || "");
    safeAppendCell(tr, row.action || "");
    safeAppendCell(tr, row.details || "");
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
  if (isReactIslandMounted("backup-manager")) return;
  if (!backupTableBody) return;
  backupTableBody.innerHTML = "";
  if (!rows.length) {
    renderEmptyTableState(backupTableBody, 4, "Noch keine Backups vorhanden.");
    return;
  }
  for (const row of rows) {
    const tr = document.createElement("tr");
    tr.dataset.filename = row.filename || "";
    safeAppendCell(tr, row.filename || "");
    safeAppendCell(tr, row.created_at || "");
    safeAppendCell(tr, formatBytes(row.size_bytes));
    safeAppendHtmlCell(tr, '<button type="button" data-action="download-backup">Download</button>');
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
  if (isReactIslandMounted("backup-manager")) return;
  if (!isAdminUser() || !hasPermission("backup_manage")) return;
  const data = await (await apiFetch("/admin/backup/list?limit=200")).json();
  maxBackupRestoreSizeMb = Math.max(1, Number(data.max_restore_size_mb || DEFAULT_MAX_BACKUP_RESTORE_SIZE_MB));
  backupDbEngine = String(data.db_engine || "sqlite").toLowerCase();
  renderBackupRows(data.rows || []);
}

function setDesktopSyncStatus(message, level = "info") {
  if (!desktopSyncStatus) return;
  desktopSyncStatus.textContent = message || "";
  desktopSyncStatus.classList.remove("success", "error");
  if (level === "success") desktopSyncStatus.classList.add("success");
  if (level === "error") desktopSyncStatus.classList.add("error");
}

function resolveDesktopSyncBackendUrl() {
  return window.location.origin || `${window.location.protocol}//${window.location.host}`;
}

async function copyTextToClipboard(value) {
  if (!value) throw new Error("Nichts zum Kopieren vorhanden.");
  if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
    await navigator.clipboard.writeText(value);
    return;
  }
  const fallback = document.createElement("textarea");
  fallback.value = value;
  fallback.setAttribute("readonly", "readonly");
  fallback.style.position = "absolute";
  fallback.style.left = "-9999px";
  document.body.appendChild(fallback);
  fallback.select();
  const ok = document.execCommand("copy");
  fallback.remove();
  if (!ok) throw new Error("Kopieren nicht verfuegbar.");
}

function renderDesktopSyncArchiveRows(rows) {
  if (isReactIslandMounted("desktop-sync-archive")) return;
  if (!desktopSyncArchiveTableBody) return;
  desktopSyncArchiveTableBody.innerHTML = "";
  if (!Array.isArray(rows) || rows.length === 0) {
    const tr = document.createElement("tr");
    tr.innerHTML = '<td colspan="8" class="muted">Noch keine Tokens erzeugt.</td>';
    desktopSyncArchiveTableBody.appendChild(tr);
    return;
  }
  rows.forEach((row) => {
    const tr = document.createElement("tr");
    const createdAt = row?.created_at ? new Date(row.created_at).toLocaleString() : "-";
    const expiresAt = row?.expires_at ? new Date(row.expires_at).toLocaleString() : "-";
    tr.innerHTML = `
      <td>${escapeHtml(createdAt)}</td>
      <td>${escapeHtml(row?.client_label || "-")}</td>
      <td>${escapeHtml(row?.username || "-")}</td>
      <td>${escapeHtml(row?.role || "-")}</td>
      <td>${escapeHtml(expiresAt)}</td>
      <td>${escapeHtml(row?.status || "-")}</td>
      <td><code>${escapeHtml(row?.token_masked || "-")}</code></td>
      <td></td>
    `;
    const actionCell = tr.lastElementChild;
    const isRevokable = String(row?.status || "").toLowerCase() === "aktiv";
    if (actionCell && isRevokable && row?.token_fingerprint) {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = "Widerrufen";
      button.className = "btn-secondary";
      button.addEventListener("click", async () => {
        if (!window.confirm("Token wirklich widerrufen?")) return;
        setDesktopSyncStatus("Token wird widerrufen...");
        try {
          await revokeDesktopSyncToken(String(row.token_fingerprint));
          await loadDesktopSyncArchive();
          setDesktopSyncStatus("Desktop-Token widerrufen.", "success");
          showToast("Desktop-Token widerrufen.", "success");
        } catch (error) {
          setDesktopSyncStatus(error.message, "error");
          showToast(error.message, "error");
        }
      });
      actionCell.appendChild(button);
    } else if (actionCell) {
      actionCell.textContent = "-";
    }
    desktopSyncArchiveTableBody.appendChild(tr);
  });
}

async function loadDesktopSyncArchive() {
  if (!desktopSyncArchiveTableBody) return;
  const rows = await (await apiFetch("/auth/desktop-sync-tokens")).json();
  renderDesktopSyncArchiveRows(Array.isArray(rows) ? rows : []);
}

async function revokeDesktopSyncToken(tokenFingerprint) {
  await apiFetch("/auth/desktop-sync-token/revoke", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token_fingerprint: tokenFingerprint }),
  });
}

async function loadDesktopSyncPanel() {
  if (!desktopSyncForm) return;
  if (desktopSyncBackendUrlInput) desktopSyncBackendUrlInput.value = resolveDesktopSyncBackendUrl();
  if (desktopSyncClientLabelInput && !desktopSyncClientLabelInput.value) {
    desktopSyncClientLabelInput.value = "";
  }
  if (desktopSyncTokenInput) desktopSyncTokenInput.value = "";
  if (desktopSyncExpiresAtInput) desktopSyncExpiresAtInput.value = "";
  await loadDesktopSyncArchive();
  setDesktopSyncStatus("Backend-URL geladen. Token bei Bedarf erzeugen.");
}

async function generateDesktopSyncToken() {
  const clientLabel = String(desktopSyncClientLabelInput?.value || "").trim();
  const payload = await (
    await apiFetch("/auth/desktop-sync-token", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ client_label: clientLabel || null }),
    })
  ).json();
  if (desktopSyncBackendUrlInput) {
    desktopSyncBackendUrlInput.value = payload.backend_url || resolveDesktopSyncBackendUrl();
  }
  if (desktopSyncTokenInput) desktopSyncTokenInput.value = payload.token || "";
  if (desktopSyncExpiresAtInput) {
    desktopSyncExpiresAtInput.value = payload.expires_at ? new Date(payload.expires_at).toLocaleString() : "";
  }
  await loadDesktopSyncArchive();
  setDesktopSyncStatus("Desktop-Token erzeugt. Bitte sicher speichern.", "success");
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
  const rows = await (await apiFetch("/auth/activity?limit=10")).json();
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
  if (uiUtils.escapeHtml) return uiUtils.escapeHtml(text);
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
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
  if (bewegungFilterDepot) {
    fillSelect(bewegungFilterDepot, depotsForReports, "name", { placeholder: "Alle Depots" });
  }
  if (bewegungFilterPraeparat) {
    fillSelect(bewegungFilterPraeparat, praeparateForReports, "name", { placeholder: "Alle Praeparate" });
  }
  if (assignmentDepot) fillSelect(assignmentDepot, depots, "name", { placeholder: "Depot waehlen" });
  if (kontaktDepot) fillSelect(kontaktDepot, depots, "name", { placeholder: "Depot waehlen" });
  refreshReportSelectionOptions();
  refreshVerfallSelectionOptions();
  if (depotSelect.value) {
    await refreshPraeparateForSelectedDepot();
  } else {
    fillSelect(praeparatSelect, praeparate, "name", { placeholder: "Praeparat waehlen" });
  }
  if (depotPrev) depotPrev.disabled = depotOffset === 0;
  if (depotNext) depotNext.disabled = lastDepotCount < PAGE_SIZE;
  if (praeparatPrev) praeparatPrev.disabled = praeparatOffset === 0;
  if (praeparatNext) praeparatNext.disabled = lastPraeparatCount < PAGE_SIZE;
}

async function loadBewegungen() {
  const selectedDepot = Number(bewegungFilterDepot?.value || 0);
  const selectedPraeparat = Number(bewegungFilterPraeparat?.value || 0);
  const onlyWithPdf = bewegungFilterHasAttachment?.checked ? 1 : 0;
  const startDate = bewegungFilterStartDate?.value?.trim() || "";
  const endDate = bewegungFilterEndDate?.value?.trim() || "";
  const searchQuery = bewegungSearch?.value?.trim() || "";
  const hasActiveFilters = Boolean(
    searchQuery ||
    bewegungFilterTyp?.value ||
    selectedDepot > 0 ||
    selectedPraeparat > 0 ||
    onlyWithPdf === 1 ||
    startDate ||
    endDate,
  );
  const bewegungenRaw = await (await apiFetch(
    `/bewegungen?limit=${PAGE_SIZE}&offset=${bewegungOffset}&q=${encodeURIComponent(searchQuery)}&typ=${encodeURIComponent(bewegungFilterTyp.value)}&depot_id=${selectedDepot > 0 ? selectedDepot : 0}&praeparat_id=${selectedPraeparat > 0 ? selectedPraeparat : 0}&has_attachment=${onlyWithPdf}&start_date=${encodeURIComponent(startDate)}&end_date=${encodeURIComponent(endDate)}`,
  )).json();
  if (!bewegungenRaw.length && bewegungOffset > 0) {
    bewegungOffset = Math.max(0, bewegungOffset - PAGE_SIZE);
    if (bewegungStatus instanceof HTMLElement) {
      setStatusWithNextStep(
        bewegungStatus,
        "Keine Eintraege mehr auf dieser Seite, springe zur vorherigen Seite.",
        "Filter anpassen oder weitere Bewegungen erfassen",
      );
    }
    return loadBewegungen();
  }
  const bewegungen = bewegungenRaw.map((row) => ({
    ...row,
    depot: depotNameById.get(Number(row.depot_id)) || row.depot_id,
    praeparat: praeparatNameById.get(Number(row.praeparat_id)) || row.praeparat_id,
  }));
  lastBewegungCount = bewegungen.length;
  const emptyMessage = hasActiveFilters
    ? "Keine Bewegungen fuer die aktuelle Filterung. Filter pruefen oder zuruecksetzen."
    : "Noch keine Bewegungen vorhanden.";
  renderBewegungen(bewegungen, { emptyMessage });
  saveBewegungHistoryFilters();
  if (bewegungPrev) bewegungPrev.disabled = bewegungOffset === 0;
  if (bewegungNext) bewegungNext.disabled = lastBewegungCount < PAGE_SIZE;
}

async function exportBewegungenCsv() {
  const selectedDepot = Number(bewegungFilterDepot?.value || 0);
  const selectedPraeparat = Number(bewegungFilterPraeparat?.value || 0);
  const onlyWithPdf = bewegungFilterHasAttachment?.checked ? 1 : 0;
  const startDate = bewegungFilterStartDate?.value?.trim() || "";
  const endDate = bewegungFilterEndDate?.value?.trim() || "";
  const params = new URLSearchParams({
    q: bewegungSearch.value.trim(),
    typ: bewegungFilterTyp.value,
    depot_id: String(selectedDepot > 0 ? selectedDepot : 0),
    praeparat_id: String(selectedPraeparat > 0 ? selectedPraeparat : 0),
    has_attachment: String(onlyWithPdf),
    start_date: startDate,
    end_date: endDate,
  });
  const response = await apiFetch(`/bewegungen/export.csv?${params.toString()}`);
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "bewegungen_verlauf.csv";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
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
  if (isReactIslandMounted("audit-table")) return;
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

async function loadEmailDeliveryStatus() {
  if (isReactIslandMounted("email-manager")) return {};
  const status = await (await apiFetch("/emails/delivery/status")).json();
  if (emailDeliveryMode) {
    if (status.mode === "smtp") {
      emailDeliveryMode.textContent = status.can_send_now
        ? `Versandmodus: SMTP aktiv (${status.from_address || "Absender konfiguriert"}).`
        : "Versandmodus: SMTP konfiguriert, aber unvollstaendig.";
    } else {
      emailDeliveryMode.textContent = "Versandmodus: Entwurf-only (kein Live-Versand).";
    }
  }
  if (emailSendNow instanceof HTMLInputElement) {
    emailSendNow.disabled = !status.can_send_now;
    if (!status.can_send_now) emailSendNow.checked = false;
  }
  return status;
}

async function loadDashboardOverview() {
  if (isReactIslandMounted("dashboard-overview")) return {};
  const data = await (await apiFetch("/dashboard/overview")).json();
  renderDashboardOverview(data);
  return data;
}

async function loadVerfallOverview() {
  if (isReactIslandMounted("verfall-overview")) return { rows: [], stats_page: {} };
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

function startNotificationPolling() {
  stopNotificationPolling();
  notificationSince = new Date(Date.now() - 60 * 1000).toISOString();
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
  link.download = filenameFromResponseHeader(response, `${typ}.csv`);
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
  link.download = filenameFromResponseHeader(response, `${typ}.${extension}`);
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(blobUrl), 10000);
}

async function afterLogin() {
  const me = await (await apiFetch("/auth/me")).json();
  currentRole = me.role || null;
  currentUsername = me.username || null;
  avatarAvailable = Boolean(me.avatar_available);
  mustChangePassword = Boolean(me.requires_password_change);
  currentPermissions = new Set(Array.isArray(me.permissions) ? me.permissions : []);
  setAuthLocked(false);
  setAccountUiVisibility(true);
  applyPermissionVisibility();
  applyReactIslandVisibility();
  updateLoginPill(`Angemeldet: ${me.username} (${me.role || "-"})`, true);
  updateHeaderAccountPill(me.username || "", "");
  if (accountPasswordWarning) {
    accountPasswordWarning.classList.toggle("hidden", !mustChangePassword);
  }
  const guardedLoad = async (label, fn) => {
    try {
      await fn();
    } catch (error) {
      console.warn(`Teilbereich konnte nicht geladen werden (${label}):`, error);
    }
  };

  await guardedLoad("permissions", loadPermissionCatalog);
  if (hasPermission("masterdata_read")) {
    await guardedLoad("masterdata", loadMasterData);
    applyBewegungHistoryFiltersFromStorage();
    if (hasPermission("movements_write") && !isReactIslandMounted("bewegung-create-form")) {
      await guardedLoad("bewegung-autofill", applyBewegungAutofillFromLastInput);
    }
  }
  if (hasPermission("movements_read")) {
    await Promise.allSettled([
      guardedLoad("dashboard", loadDashboardOverview),
      guardedLoad("verfall-overview", loadVerfallOverview),
      guardedLoad("bewegungen", loadBewegungen),
    ]);
    startNotificationPolling();
  } else {
    stopNotificationPolling();
  }
  if (isAdminUser() && hasPermission("audit_view")) {
    await guardedLoad("audit", loadAuditLogs);
  }
  if (hasPermission("email_use")) {
    await guardedLoad("email-status", loadEmailDeliveryStatus);
  }
  if (!isReactIslandMounted("account-manager")) {
    await Promise.allSettled([
      guardedLoad("account-activity", loadCurrentUserActivity),
      guardedLoad("account-avatar", loadCurrentAvatar),
    ]);
  }
  if (isAdminUser()) {
    await Promise.allSettled([
      guardedLoad("users", loadUsers),
      guardedLoad("backups", loadBackupList),
      !isReactIslandMounted("desktop-sync-form") ? guardedLoad("desktop-sync", loadDesktopSyncPanel) : Promise.resolve(),
    ]);
  }
  if (mustChangePassword) {
    accountStatus.textContent = "Bitte zuerst Ihr Standard-Passwort aendern.";
    showPage("account-section");
  } else {
    showPage(getDefaultLandingPageId());
    await checkAndOpenOnboardingIfRequired();
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
    await afterLogin();
  } catch (error) {
    removeToken();
    loginStatus.textContent = error.message;
    updateLoginPill("Login fehlgeschlagen", false);
    setAuthLocked(true);
    showPage("login-section");
  }
});

if (onboardingAddDepotButton) {
  onboardingAddDepotButton.addEventListener("click", () => {
    onboardingDepots.push({
      name: "",
      strasse: "",
      hausnummer: "",
      postleitzahl: "",
      stadt: "",
      telefon: "",
      email: "",
      latitude: "",
      longitude: "",
      praeparate: [],
    });
    renderOnboardingDepots();
  });
}

if (onboardingPrevButton) {
  onboardingPrevButton.addEventListener("click", () => {
    setOnboardingStep(onboardingStepIndex - 1);
  });
}

if (onboardingNextButton) {
  onboardingNextButton.addEventListener("click", () => {
    try {
      validateOnboardingStep(onboardingStepIndex);
      setOnboardingStep(onboardingStepIndex + 1);
    } catch (error) {
      if (onboardingStatus) onboardingStatus.textContent = error instanceof Error ? error.message : "Eingabe ungueltig.";
    }
  });
}

if (onboardingSubmitButton) {
  onboardingSubmitButton.addEventListener("click", async () => {
    try {
      validateOnboardingStep(2);
      await submitOnboardingSetup();
    } catch (error) {
      if (onboardingStatus) onboardingStatus.textContent = error instanceof Error ? error.message : "Einrichtung fehlgeschlagen.";
    }
  });
}

if (onboardingAddPraeparatButton) {
  onboardingAddPraeparatButton.addEventListener("click", () => {
    onboardingPraeparate.push({
      name: "",
      wirkstoff: "",
      darreichungsform: "",
      staerke: "",
      einheit: "",
      pzn: "",
      hersteller: "",
    });
    renderOnboardingPraeparate();
    renderOnboardingDepots();
  });
}

if (onboardingInstitutionPostcode instanceof HTMLInputElement) {
  onboardingInstitutionPostcode.addEventListener("input", () => {
    const digitsOnly = onboardingInstitutionPostcode.value.replace(/\D+/g, "").slice(0, 5);
    if (onboardingInstitutionPostcode.value !== digitsOnly) {
      onboardingInstitutionPostcode.value = digitsOnly;
    }
  });
}

for (const addressField of [
  onboardingInstitutionStreet,
  onboardingInstitutionHouseNumber,
  onboardingInstitutionPostcode,
  onboardingInstitutionCity,
]) {
  if (!(addressField instanceof HTMLInputElement)) continue;
  addressField.addEventListener("input", () => {
    if (onboardingInstitutionLatitude instanceof HTMLInputElement) onboardingInstitutionLatitude.value = "";
    if (onboardingInstitutionLongitude instanceof HTMLInputElement) onboardingInstitutionLongitude.value = "";
    updateOnboardingReview();
  });
}

if (onboardingGeocodeButton) {
  onboardingGeocodeButton.addEventListener("click", async () => {
    try {
      if (onboardingStatus) onboardingStatus.textContent = "Adresse wird geokodiert...";
      await geocodeOnboardingInstitutionAddress();
      if (onboardingStatus) onboardingStatus.textContent = "Koordinaten wurden automatisch gesetzt.";
      updateOnboardingReview();
    } catch (error) {
      if (onboardingStatus) onboardingStatus.textContent = error instanceof Error ? error.message : "Geokodierung fehlgeschlagen.";
    }
  });
}

if (onboardingStartAdminButton) {
  onboardingStartAdminButton.addEventListener("click", () => {
    setOnboardingStep(0);
    showPage("onboarding-section");
  });
}

if (bewegungForm && !isReactIslandMounted("bewegung-create-form")) {
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
      let attachmentUploadError = "";
      if (file) {
        validateBewegungAttachmentFile(file);
        try {
          const formData = new FormData();
          formData.append("file", file, file.name);
          await apiFetch(`/bewegungen/${data.id}/attachment`, {
            method: "POST",
            body: formData,
          });
          bewegungAttachment.value = "";
        } catch (error) {
          attachmentUploadError = error instanceof Error ? error.message : "Upload fehlgeschlagen.";
        }
      }
      if (file && attachmentUploadError) {
        setStatusWithNextStep(
          bewegungStatus,
          `Bewegung gespeichert (ID ${data.id}), aber PDF-Anhang fehlgeschlagen: ${attachmentUploadError}`,
          "Anhang ueber Verlauf erneut pruefen oder Bewegung ohne Anhang fortsetzen",
        );
      } else if (file) {
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
}

if (depotSelect && !isReactIslandMounted("bewegung-create-form")) {
  depotSelect.addEventListener("change", async () => {
    try {
      await refreshPraeparateForSelectedDepot();
    } catch (error) {
      bewegungStatus.textContent = error.message;
    }
  });
}

initializeTheme();
initializeSectionNavigation();
initializeInlineTabs();
initializeSidebarShortcuts();
initializeSubpageNavigation();
initializeBewegungFormUx();
initializeInputAssist();
initializeCardMotion();
initializeResponsiveTables();
applyReactIslandVisibility();
enhanceActionButtons();
initializeRequiredFieldIndicators();
initializeFormDirtyTracking();
initializeFormValidationUx();
initializeMoreActionsDismiss();
initializeKeyboardShortcuts();
observeStatusFeedback();
updateLoginPill("Nicht angemeldet", false);
setOnboardingStep(0);
if (!onboardingPraeparate.length) {
  onboardingPraeparate.push({
    name: "",
    wirkstoff: "",
    darreichungsform: "",
    staerke: "",
    einheit: "",
    pzn: "",
    hersteller: "",
  });
}
renderOnboardingPraeparate();
renderOnboardingDepots();
setAuthLocked(true);

window.addEventListener("ndhub-react-ready", () => {
  applyReactIslandVisibility();
  initializeResponsiveTables();
});

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
  afterLogin().then(() => {
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



if (reportPerspective) {
  reportPerspective.addEventListener("change", () => {
    refreshReportSelectionOptions();
    reportBestandShowAll = false;
    lastReportRows = [];
    if (reportCharts) reportCharts.innerHTML = "";
    if (reportChartLegend) reportChartLegend.textContent = "";
  });
}

enableClickToggleMultiSelect(reportIdsSelect);
enableClickToggleMultiSelect(verfallIdsSelect);

if (reportType) {
  reportType.addEventListener("change", () => {
    reportBestandShowAll = false;
  });
}

const reportLoadButton = document.getElementById("report-load");
if (reportLoadButton) {
  reportLoadButton.addEventListener("click", async () => {
    if (reportStatus) reportStatus.textContent = "Auswertung wird geladen...";
    try {
      const payload = await loadReportData();
      const rows = Array.isArray(payload?.rows) ? payload.rows : [];
      lastReportRows = rows;
      renderReportTable(rows);
      renderReportCharts(rows);
      if (reportStatus) {
        reportStatus.textContent = `Auswertung geladen (${rows.length} Zeilen).`;
      }
    } catch (error) {
      if (reportStatus) reportStatus.textContent = `Auswertung fehlgeschlagen: ${error.message}`;
    }
  });
}

const reportExportCsvButton = document.getElementById("report-export-csv");
if (reportExportCsvButton) {
  reportExportCsvButton.addEventListener("click", async () => {
    if (reportStatus) reportStatus.textContent = "CSV-Export wird erstellt...";
    try {
      await exportReportCsv();
      if (reportStatus) reportStatus.textContent = "CSV-Export bereitgestellt.";
    } catch (error) {
      if (reportStatus) reportStatus.textContent = `CSV-Export fehlgeschlagen: ${error.message}`;
    }
  });
}

const reportExportPdfButton = document.getElementById("report-export-pdf");
if (reportExportPdfButton) {
  reportExportPdfButton.addEventListener("click", async () => {
    if (reportStatus) reportStatus.textContent = "PDF-Export wird erstellt...";
    try {
      await exportReportFile("pdf");
      if (reportStatus) reportStatus.textContent = "PDF-Export bereitgestellt.";
    } catch (error) {
      if (reportStatus) reportStatus.textContent = `PDF-Export fehlgeschlagen: ${error.message}`;
    }
  });
}

const reportExportPptButton = document.getElementById("report-export-ppt");
if (reportExportPptButton) {
  reportExportPptButton.addEventListener("click", async () => {
    if (reportStatus) reportStatus.textContent = "PPT-Export wird erstellt...";
    try {
      await exportReportFile("pptx");
      if (reportStatus) reportStatus.textContent = "PPT-Export bereitgestellt.";
    } catch (error) {
      if (reportStatus) reportStatus.textContent = `PPT-Export fehlgeschlagen: ${error.message}`;
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

if (accountPasswordForm && !isReactIslandMounted("account-manager")) {
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

if (accountAvatarForm && !isReactIslandMounted("account-manager")) {
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

if (accountAvatarRemoveButton && !isReactIslandMounted("account-manager")) {
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


if (desktopSyncGenerateButton && !isReactIslandMounted("desktop-sync-form")) {
  desktopSyncGenerateButton.addEventListener("click", async () => {
    setDesktopSyncStatus("Token wird erzeugt...");
    try {
      await generateDesktopSyncToken();
      showToast("Desktop-Token erzeugt.", "success");
    } catch (error) {
      setDesktopSyncStatus(error.message, "error");
      showToast(error.message, "error");
    }
  });
}

if (desktopSyncCopyUrlButton && !isReactIslandMounted("desktop-sync-form")) {
  desktopSyncCopyUrlButton.addEventListener("click", async () => {
    try {
      await copyTextToClipboard(desktopSyncBackendUrlInput?.value || "");
      setDesktopSyncStatus("Backend-URL kopiert.", "success");
    } catch (error) {
      setDesktopSyncStatus(error.message, "error");
      showToast(error.message, "error");
    }
  });
}

if (desktopSyncCopyTokenButton && !isReactIslandMounted("desktop-sync-form")) {
  desktopSyncCopyTokenButton.addEventListener("click", async () => {
    try {
      await copyTextToClipboard(desktopSyncTokenInput?.value || "");
      setDesktopSyncStatus("Desktop-Token kopiert.", "success");
    } catch (error) {
      setDesktopSyncStatus(error.message, "error");
      showToast(error.message, "error");
    }
  });
}

if (usersForm && !isReactIslandMounted("users-admin-form")) {
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

if (usersApplyTemplateButton && !isReactIslandMounted("users-admin-form")) {
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

if (usersResetButton && !isReactIslandMounted("users-admin-form")) {
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

if (usersUnlockButton && !isReactIslandMounted("users-admin-form")) {
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

if (usersDeleteButton && !isReactIslandMounted("users-admin-form")) {
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

if (usersClearButton && !isReactIslandMounted("users-admin-form")) {
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

