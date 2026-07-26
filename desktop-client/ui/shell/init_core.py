"""MainWindow shell helpers (Issue #93)."""
from __future__ import annotations

import logging
import os
import time

from apple_theme import AppleTheme
from core.config_manager import ConfigManager
from core.data_access_layer import (
    BackendApiClient,
    BackendSyncConfig,
    DataAccessRouter,
    OperatingMode,
)
from core.sync_service import DesktopSyncService
from core.sync_worker import SyncWorkerRunner
from db_manager import Database
from PySide6 import QtCore, QtGui, QtWidgets
from security_manager import SecurityManager
from verfallmanager import VerfallManager

from ui.resources import LOGO_BASE64
from ui.shell.constants import UI, Cache

logger = logging.getLogger("ND-Hub")

def __init__(self, config: ConfigManager, parent: QtWidgets.QWidget | None = None):

    super().__init__(parent)
    self.config = config
    self._setup_wizard_prompted_session = False
    self._startup_profiling = os.environ.get("ND_HUB_PROFILE_STARTUP", "0") == "1"
    self._startup_t0 = time.perf_counter()
    self._startup_last = self._startup_t0

    # Pfade aus Konfiguration beziehen
    db_path = self.config.get_db_path()
    attachment_folder = os.path.join(self.config.data_dir, "Attachments")

    # Ordner sicherstellen
    os.makedirs(attachment_folder, exist_ok=True)

    logger.info("ND-Hub initialisiert mit:")
    logger.info(f"  - Datenverzeichnis: {self.config.data_dir}")
    logger.info(f"  - Datenbank: {db_path}")
    logger.info(f"  - Anhänge: {attachment_folder}")

    # Initialisierung in logischen Blöcken
    self.db_path = db_path
    self.attachment_folder = attachment_folder

    # Database zuerst — Security/Verfall teilen die Connection (Issue #18)
    self._init_database(db_path)
    self._init_security(db_path)
    self._profile_startup("Database + Security abgeschlossen")

    # Core-Komponenten
    self._init_data_access_layer()
    self._init_sync_service()
    self._init_managers(db_path)
    self._init_multi_user_mode()
    self._profile_startup("Core-Komponenten initialisiert")

    # Cache für Performance-Optimierung
    self.cache = Cache()

    # UI aufbauen
    self._init_window()
    self._init_ui()
    self._init_pages()
    self._setup_integrated_login()
    self._profile_startup("UI und erste Seite bereit")

    # Timer starten
    self._init_timers()
    self._profile_startup("Timer gestartet")
    self._profile_startup("MainWindow vollständig initialisiert", final=True)


def _profile_startup(self, label: str, final: bool = False) -> None:
    """Optionales Startup-Profiling über ND_HUB_PROFILE_STARTUP=1."""
    if not self._startup_profiling:
        return
    now = time.perf_counter()
    delta_ms = (now - self._startup_last) * 1000
    total_ms = (now - self._startup_t0) * 1000
    logger.info(f"[startup] {label}: +{delta_ms:.1f}ms (gesamt {total_ms:.1f}ms)")
    self._startup_last = now
    if final:
        logger.info("[startup] Profiling abgeschlossen")

# ============================================================
# SECURITY
# ============================================================

def _init_security(self, db_path: str) -> None:
    """Initialisiert Security.

    Issue #18: Geteilte Connection mit der Database-Instanz, um
    Lock-Contention zu vermeiden (3 parallele Connections auf
    dieselbe Datei).
    """
    self.security = SecurityManager(database=self.db)


def _handle_successful_login(self, username: str) -> None:
    """Zeigt Post-Login-Dialogs (Willkommen, Passwort-Warnung)"""
    self._init_multi_user_mode()
    self._refresh_user_sidebar_state()
    QtCore.QTimer.singleShot(1200, self._run_sync_cycle)

    # Begrüßung standardmäßig nicht-blockierend loggen, um die Startzeit
    # nicht mit einem zusätzlichen Klick zu verlängern.
    if os.environ.get("ND_HUB_SHOW_WELCOME_DIALOG", "0") == "1":
        QtWidgets.QMessageBox.information(
            None,
            "Anmeldung erfolgreich",
            f"Willkommen, {username}!\n\nRolle: {self.security.get_current_role()}"
        )
    else:
        logger.info("Anmeldung erfolgreich: %s (%s)", username, self.security.get_current_role())

    # Warnung bei unsicherem Passwort (delegiert an SecurityManager)
    if hasattr(self, 'security') and getattr(self.security, 'is_using_default_password', lambda: False)():
        QtWidgets.QMessageBox.warning(
            None,
            "Zwingende Passwort-Änderung",
            "Aus Sicherheitsgründen MÜSSEN Sie Ihr Standard-Passwort jetzt ändern, bevor Sie das System weiter verwenden."
        )
        self.change_user_password()

        # Re-evaluierung nach dem Dialog
        if getattr(self.security, 'is_using_default_password', lambda: False)():
            QtWidgets.QMessageBox.critical(
                None,
                "Zugriff verweigert",
                "Das Standard-Passwort wurde nicht erfolgreich geändert. Die Anwendung wird beendet."
            )
            self.force_logout()
            return

    # Länger verzögern + eigener Tick: Login-Overlay/Toast dürfen erst fertig sein.
    QtCore.QTimer.singleShot(800, self._maybe_open_setup_wizard)


def _maybe_open_setup_wizard(self) -> None:
    """Öffnet den Einrichtungswizard einmal pro Sitzung, wenn Stammdaten noch fehlen."""
    if getattr(self, "_setup_wizard_prompted_session", False):
        return
    if not hasattr(self, "db") or not hasattr(self, "security"):
        return
    if not self.security.is_admin():
        return
    if not self.security.has_permission("masterdata_write"):
        return
    if self.db.is_read_only_mode():
        return
    if not self.db.needs_setup_wizard():
        return
    self._setup_wizard_prompted_session = True
    logger.info("Starte Einrichtungswizard (Post-Login, native Dialog)")
    try:
        from ui.dialogs.setup_wizard_dialog import SetupWizardDialog

        # Native modal window statt embedded overlay:
        # nested QEventLoop + Fullscreen/Maximized + großer Wizard
        # hat unter Windows Exit-139 (Segfault) ausgelöst.
        # parent=None: kein Backdrop auf dem MainWindow (Fix "Später"-Overlay)
        dlg = SetupWizardDialog(None, self.db)
        dlg.setWindowFlag(QtCore.Qt.Window, True)
        dlg.setWindowModality(QtCore.Qt.ApplicationModal)
        dlg.exec()
        # Falls ältere Backdrops vom Parent hängen: aufräumen
        for child in self.findChildren(QtWidgets.QWidget, "setup_wizard_backdrop"):
            child.hide()
            child.setParent(None)
            child.deleteLater()
        logger.info("Einrichtungswizard beendet (result=%s)", dlg.result())
    except Exception:
        logger.exception("Einrichtungswizard konnte nicht geöffnet werden")


def open_setup_wizard_dialog(self) -> None:
    """Manueller Start des Einrichtungswizards (z. B. aus den Grundeinstellungen)."""
    if not hasattr(self, "db") or not hasattr(self, "security"):
        return
    if not self.security.is_admin():
        QtWidgets.QMessageBox.information(
            self,
            "Einrichtungswizard",
            "Nur Administratoren können den Einrichtungswizard öffnen.",
        )
        return
    if not self.security.has_permission("masterdata_write"):
        QtWidgets.QMessageBox.information(
            self,
            "Einrichtungswizard",
            "Keine Berechtigung zum Bearbeiten von Stammdaten (masterdata_write).",
        )
        return
    if self.db.is_read_only_mode():
        QtWidgets.QMessageBox.warning(
            self,
            "Nur-Lesen Modus",
            "Der Einrichtungswizard ist im Nur-Lesen Modus nicht verfügbar.",
        )
        return
    try:
        from ui.dialogs.setup_wizard_dialog import SetupWizardDialog

        # parent=None: kein Backdrop auf dem MainWindow (Fix "Später"-Overlay)
        dlg = SetupWizardDialog(None, self.db)
        dlg.setWindowFlag(QtCore.Qt.Window, True)
        dlg.setWindowModality(QtCore.Qt.ApplicationModal)
        dlg.exec()
        # Falls ältere Backdrops vom Parent hängen: aufräumen
        for child in self.findChildren(QtWidgets.QWidget, "setup_wizard_backdrop"):
            child.hide()
            child.setParent(None)
            child.deleteLater()
    except Exception:
        logger.exception("Einrichtungswizard konnte nicht geöffnet werden")

# ============================================================
# INITIALISIERUNG
# ============================================================

def _init_database(self, db_path: str) -> None:
    """Initialisiert Datenbankverbindung"""
    self.db = Database(db_path)


def _init_data_access_layer(self) -> None:
    """Initialisiert den Translational Layer fuer lokale/offline/hybride Betriebsmodi."""
    configured_mode = self.config.get_operating_mode()
    operating_mode = OperatingMode.from_raw(configured_mode)
    backend_url = self.config.get_backend_url()
    backend_token = self.config.get_backend_token()

    api_client = BackendApiClient(
        BackendSyncConfig(
            base_url=backend_url,
            access_token=backend_token,
        )
    )
    self.data_access_router = DataAccessRouter(
        local_db=self.db,
        operating_mode=operating_mode,
        api_client=api_client,
    )
    effective_mode, reason = self.data_access_router.resolve_effective_mode()
    logger.info(
        "DataAccess-Modus: configured=%s effective=%s reason=%s backend=%s",
        operating_mode.value,
        effective_mode.value,
        reason,
        backend_url or "<leer>",
    )


def _init_sync_service(self) -> None:
    """Initialisiert zyklischen Sync-Service fuer Hybrid-Betrieb."""
    self.sync_service = DesktopSyncService(
        db=self.db,
        config=self.config,
        router=self.data_access_router,
    )
    # Worker-Runner entkoppelt den Push/Pull-Zyklus vom UI-Thread.
    # Signal-Handler werden hier gebunden, damit UI-Updates
    # automatisch im Haupt-Thread eintreffen.
    self.sync_worker_runner = SyncWorkerRunner(self.sync_service, max_threads=1)
    self.sync_worker_runner.signals.cycle_finished.connect(self._on_sync_cycle_finished)
    self.sync_worker_runner.signals.cycle_failed.connect(self._on_sync_cycle_failed)
    self.sync_worker_runner.signals.cycle_skipped.connect(self._on_sync_cycle_skipped)
    self._refresh_sync_scheduler()


def _init_multi_user_mode(self) -> None:
    """Initialisiert Schreib-/Lese-Modus über exklusiven Write-Lease."""
    username = self.security.get_current_user()
    if not username or not hasattr(self, "db"):
        return
    is_writer = self.db.acquire_write_lease(username)
    if hasattr(self, "security"):
        self.security.set_query_only(not is_writer)
    if not is_writer:
        QtWidgets.QMessageBox.warning(
            self,
            "Nur-Lesen Modus aktiv",
            "Ein anderer Client schreibt aktuell auf diese Datenbank.\n"
            "Diese Sitzung läuft im Nur-Lesen Modus.",
        )
    if hasattr(self, "stack"):
        current = self.stack.currentWidget()
        if current is not None:
            self._apply_write_mode_to_page(current)


def _init_managers(self, db_path: str) -> None:
    """Initialisiert Business-Logic-Manager.

    Issue #18: Geteilte Connection mit der Database-Instanz für
    VerfallManager — keine separate sqlite3-Connection mehr.
    """
    self.verfallmanager = VerfallManager(database=self.db)
    logger.info("VerfallManager initialisiert (geteilt mit Database)")


def _init_window(self) -> None:
    """Konfiguriert Hauptfenster"""
    self.setStyleSheet(AppleTheme.get_stylesheet())
    self.setWindowTitle("ND-Hub")
    self.resize(1400, 800)
    self.setMinimumSize(UI.MIN_WINDOW_WIDTH, UI.MIN_WINDOW_HEIGHT)

    # Window-Icon setzen
    self._set_window_icon()


def _set_window_icon(self) -> None:
    """Lädt Window-Icon (Base64 oder Datei)"""
    try:
        import base64
        icon_data = base64.b64decode(LOGO_BASE64)
        pixmap = QtGui.QPixmap()
        if pixmap.loadFromData(icon_data) and not pixmap.isNull():
            self.setWindowIcon(QtGui.QIcon(pixmap))
            return
    except Exception as e:
        logger.debug(f"Base64-Icon fehlgeschlagen: {e}")

    # Fallback: Datei
    if os.path.exists("logo.png"):
        self.setWindowIcon(QtGui.QIcon("logo.png"))
        logger.debug("Window-Icon aus logo.png geladen")


def _init_ui(self) -> None:
    """Baut Haupt-UI auf (Sidebar + Stack)"""
    central = QtWidgets.QWidget()
    self.setCentralWidget(central)

    main_layout = QtWidgets.QHBoxLayout(central)
    main_layout.setContentsMargins(0, 0, 0, 0)
    main_layout.setSpacing(0)
    self.main_layout = main_layout

    # Sidebar
    sidebar = self._create_sidebar()
    main_layout.addWidget(sidebar)

    self.right_container = QtWidgets.QWidget()
    right_layout = QtWidgets.QVBoxLayout(self.right_container)
    right_layout.setContentsMargins(0, 0, 0, 0)
    right_layout.setSpacing(0)

    self.read_only_banner = QtWidgets.QFrame()
    self.read_only_banner.setVisible(False)
    banner_layout = QtWidgets.QHBoxLayout(self.read_only_banner)
    banner_layout.setContentsMargins(14, 8, 14, 8)
    banner_layout.setSpacing(8)
    self.read_only_banner_label = QtWidgets.QLabel(
        "Nur-Lesen Modus aktiv - ein anderer Client hat den Schreibzugriff."
    )
    self.read_only_banner_label.setWordWrap(True)
    self.read_only_banner_label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
    banner_layout.addWidget(self.read_only_banner_label)
    banner_layout.addStretch()
    right_layout.addWidget(self.read_only_banner)

    # Content-Stack
    self.stack = QtWidgets.QStackedWidget()
    self.stack.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
    right_layout.addWidget(self.stack, 1)
    main_layout.addWidget(self.right_container, 1)
    self._update_sidebar_width(self.width())
    self._setup_feedback_layers()
    self._apply_chrome_overlay_styles()

