
"""
ND-Hub – Die ND-Hub-Verwaltung – Modern UI Edition 2025

Features:
- Modernes Flat Design mit Material Design Elementen
- Depots, Präparate mit Sollbestand-Verwaltung
- Bewegungen mit PDF-Attachments
- CSV/Excel-Import für Bestandsmeldungen & Bewegungen
- E-Mail-Integration mit Outlook
- Statistik-Diagramme mit Jahresvergleich
- Bewegungsverlauf mit Filter
- PDF-Export für Berichte

Abhängigkeiten:
pip install PySide6 reportlab matplotlib pywin32 pandas openpyxl
"""
import os
import sys
import time
from enum import IntEnum

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt

# ===== NEUE IMPORTS FÜR APPLE-STYLE =====
from apple_theme import AppleTheme

# Core Modules
from core.config_manager import ConfigManager
from core.data_access_layer import (
    BackendApiClient,
    BackendSyncConfig,
    DataAccessRouter,
    OperatingMode,
)
from core.error_handler import setup_global_error_handler
from core.sync_service import DesktopSyncService
from core.sync_worker import SyncWorkerRunner
from icon_manager import IconManager

# import win32com.client  # Windows-only Outlook integration
from security_manager import SecurityManager
from ui.dialogs.embedded_dialog_host import exec_embedded_dialog, install_embedded_dialog_patches
from ui.resources import LOGO_BASE64
from verfallmanager import VerfallManager

# Versionsnummer
VERSION = "0.42"

# ============================================================================= 
# NEUE KOMPONENTEN in v1.0
# -Benutzerverwaltung & Verschlüsselung
#   -Verfallsdatenüberwachung
# =============================================================================

import logging

# Initialisiere Konfiguration (vor dem Logging)
config = ConfigManager()
DATA_DIR = config.data_dir

# NumExpr-Hinweis unterdrücken und Thread-Anzahl explizit setzen
os.environ.setdefault("NUMEXPR_MAX_THREADS", "8")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "8")

from logging.handlers import RotatingFileHandler


def _build_logging_handlers():
    """Erzeugt Logging-Handler mit robuster Fallback-Strategie."""
    handlers = [logging.StreamHandler()]
    try:
        log_dir = config.get_log_dir()
        os.makedirs(log_dir, exist_ok=True)
        handlers.insert(
            0,
            RotatingFileHandler(
                os.path.join(log_dir, "nd_hub.log"),
                maxBytes=5 * 1024 * 1024,
                backupCount=3,
                encoding="utf-8",
            ),
        )
    except Exception as exc:
        # Während des Logging-Setups ist der Root-Logger noch nicht konfiguriert
        # → stderr als Fallback, damit die Warnung nicht stillschweigend verschluckt wird.
        sys.stderr.write(f"Warnung: Dateilogging deaktiviert ({exc})\n")
    return handlers


# Logging - Optimized for performance
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=_build_logging_handlers()
)
logger = logging.getLogger("ND-Hub")

# Performance-optimized logger for frequent operations
perf_logger = logging.getLogger('perf')
perf_log_path = os.path.join(config.get_log_dir(), "nd_hub_perf.log")
try:
    os.makedirs(config.get_log_dir(), exist_ok=True)
    perf_handler = RotatingFileHandler(perf_log_path, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8')
    perf_handler.setLevel(logging.DEBUG)
    perf_logger.addHandler(perf_handler)
except Exception as exc:
    logger.debug(f"Perf-File-Logger deaktiviert: {exc}")
perf_logger.setLevel(logging.DEBUG)

# Konstanten
class UI:
    MIN_WINDOW_WIDTH = 1100
    MIN_WINDOW_HEIGHT = 700
    SIDEBAR_WIDTH = 240
    MAX_BACKUPS_DEFAULT = 10

class Cache:
    """Schneller UI-Hash-Speicher für Diff-Berechnungen.

    Wird in ``nd_hub.py`` als ``self.cache`` gehalten und vergleicht den
    aktuellen Inhalt des Verfall-Widgets mit dem zuletzt gerenderten Stand.
    Felder ohne aktive Verwendung werden hier bewusst weggelassen — eine
    Cache-Klasse ist kein Sammelbecken für „vielleicht später mal".
    """

    def __init__(self):
        self._last_verfall_hash: str | None = None

class PageIndex(IntEnum):
    """Stack-Indizes für Navigation"""
    DASHBOARD = 0
    MOVEMENTS = 1
    HISTORIE = 2
    AUSWERTUNGEN = 3
    IMPORT = 4
    EMAIL = 5
    GRUNDEINSTELLUNGEN = 6

from db_manager import Database

# =============================================================================
# Main Window
# =============================================================================


class MainWindow(QtWidgets.QMainWindow):
    """Hauptfenster der ND-Hub-Verwaltung"""
    
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
        
        # Security zuerst (blockierend)
        self._init_security(db_path)
        self._profile_startup("Security abgeschlossen")
        
        # Core-Komponenten
        self._init_database(db_path)
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

        QtCore.QTimer.singleShot(500, self._maybe_open_setup_wizard)

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
        try:
            from ui.dialogs.setup_wizard_dialog import SetupWizardDialog

            dlg = SetupWizardDialog(self, self.db)
            exec_embedded_dialog(self, dlg)
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

            dlg = SetupWizardDialog(self, self.db)
            exec_embedded_dialog(self, dlg)
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
    
    def _create_sidebar(self) -> QtWidgets.QFrame:
        """Erstellt Sidebar mit Navigation"""
        sidebar = QtWidgets.QFrame()
        sidebar.setObjectName("sidebar")
        self.sidebar = sidebar
        sidebar.setMinimumWidth(230)
        sidebar.setMaximumWidth(260)
        sidebar.setSizePolicy(
            QtWidgets.QSizePolicy.Fixed,
            QtWidgets.QSizePolicy.Expanding
        )
        
        layout = QtWidgets.QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        content_layout = QtWidgets.QVBoxLayout()
        content_layout.setContentsMargins(0, 16, 0, 16)
        content_layout.setSpacing(0)

        # Logo-Bereich
        content_layout.addWidget(self._create_logo_container())
        content_layout.addSpacing(20)

        # Navigation
        self.sidebar_buttons = []
        self._add_navigation_buttons(content_layout)

        # User-Bereich
        content_layout.addStretch()
        self._add_user_section(content_layout)
        layout.addLayout(content_layout)
        
        return sidebar

    def _update_sidebar_width(self, window_width: int) -> None:
        """Hält Sidebar stabil, aber auf kleinen Fenstern kompakt."""
        if not hasattr(self, "sidebar"):
            return
        target = 230 if window_width < 1300 else 250
        self.sidebar.setMinimumWidth(target)
        self.sidebar.setMaximumWidth(target)

    def _setup_feedback_layers(self) -> None:
        """Initialisiert Busy-Overlay und Toast-Container."""
        self._active_toasts = []
        self._busy_operation_seq = 0
        self._busy_delay_timer = QtCore.QTimer(self)
        self._busy_delay_timer.setSingleShot(True)

        self.busy_overlay = QtWidgets.QWidget(self.right_container)
        self.busy_overlay.setObjectName("page_busy_overlay")
        busy_layout = QtWidgets.QVBoxLayout(self.busy_overlay)
        busy_layout.setContentsMargins(24, 24, 24, 24)
        busy_layout.addStretch()

        self._busy_card_frame = QtWidgets.QFrame()
        self._busy_card_frame.setObjectName("busy_card")
        self._busy_card_frame.setMaximumWidth(360)
        card_layout = QtWidgets.QVBoxLayout(self._busy_card_frame)
        card_layout.setSpacing(10)
        self.busy_label = QtWidgets.QLabel("Seite wird geladen ...")
        card_layout.addWidget(self.busy_label)

        self.busy_hint_label = QtWidgets.QLabel("Bitte einen Moment Geduld.")
        card_layout.addWidget(self.busy_hint_label)

        self.busy_progress = QtWidgets.QProgressBar()
        self.busy_progress.setRange(0, 0)
        self.busy_progress.setTextVisible(False)
        card_layout.addWidget(self.busy_progress)

        busy_layout.addWidget(self._busy_card_frame, alignment=Qt.AlignHCenter)
        busy_layout.addStretch()
        self.busy_overlay.hide()

        self.toast_container = QtWidgets.QWidget(self.right_container)
        self.toast_container.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        self.toast_container.setStyleSheet("background: transparent;")
        self.toast_container.hide()
        self._update_feedback_layer_geometry()

    def _update_feedback_layer_geometry(self) -> None:
        if hasattr(self, "right_container"):
            rect = self.right_container.rect()
            if hasattr(self, "busy_overlay"):
                self.busy_overlay.setGeometry(rect)
            if hasattr(self, "toast_container"):
                self.toast_container.setGeometry(rect)
                self._reflow_toasts()

    def _show_page_busy(self, message: str) -> None:
        if hasattr(self, "busy_label"):
            self.busy_label.setText(message)
        if hasattr(self, "busy_overlay"):
            self._update_feedback_layer_geometry()
            self.busy_overlay.raise_()
            self.busy_overlay.show()
            self.busy_overlay.repaint()
            QtWidgets.QApplication.processEvents(QtCore.QEventLoop.AllEvents)

    def _hide_page_busy(self) -> None:
        if hasattr(self, "busy_overlay"):
            self.busy_overlay.hide()

    def _begin_busy_operation(self, message: str, delay_ms: int = 120) -> int:
        """
        Startet einen verzögerten Busy-Indicator.
        Der Overlay wird nur angezeigt, wenn die Aktion länger als delay_ms dauert.
        """
        self._busy_operation_seq += 1
        op_id = self._busy_operation_seq
        if delay_ms <= 0:
            self._show_page_busy(message)
            return op_id
        if hasattr(self, "_busy_delay_timer"):
            self._busy_delay_timer.stop()
            try:
                self._busy_delay_timer.timeout.disconnect()
            except (RuntimeError, TypeError):
                logger.debug("Busy-Timer-Signal war bereits getrennt — kein Disconnect nötig.")

            def _show_if_still_running():
                if op_id == self._busy_operation_seq:
                    self._show_page_busy(message)

            self._busy_delay_timer.timeout.connect(_show_if_still_running)
            self._busy_delay_timer.start(delay_ms)
        return op_id

    def _end_busy_operation(self, op_id: int) -> None:
        """Beendet eine Busy-Operation sicher ohne visuelles Blinken."""
        if op_id != getattr(self, "_busy_operation_seq", -1):
            return
        if hasattr(self, "_busy_delay_timer"):
            self._busy_delay_timer.stop()
            try:
                self._busy_delay_timer.timeout.disconnect()
            except (RuntimeError, TypeError):
                logger.debug("Busy-Timer-Signal war bereits getrennt — kein Disconnect nötig.")
        self._hide_page_busy()

    def show_toast(self, message: str, level: str = "info", duration_ms: int = 2600) -> None:
        """Zeigt unaufdringliches Toast-Feedback oben rechts."""
        if not hasattr(self, "toast_container"):
            return
        palette = {
            "success": ("#ecfdf3", "#166534", "#86efac"),
            "warning": ("#fffbeb", "#92400e", "#fcd34d"),
            "error": ("#fef2f2", "#991b1b", "#fca5a5"),
            "info": ("#eff6ff", "#1d4ed8", "#93c5fd"),
        }
        bg, fg, border = palette.get(level, palette["info"])

        # QWidget statt QFrame: globales QFrame-Theme + Stylesheet-Border wirkten wie doppelter Rahmen.
        toast = QtWidgets.QWidget(self.toast_container)
        toast.setObjectName("toast_bubble")
        toast.setStyleSheet(
            f"QWidget#toast_bubble {{"
            f"background-color: {bg};"
            f"color: {fg};"
            f"border: 1px solid {border};"
            "border-radius: 8px;"
            "}}"
        )
        toast_layout = QtWidgets.QHBoxLayout(toast)
        toast_layout.setContentsMargins(12, 8, 12, 8)
        toast_layout.setSpacing(8)
        label = QtWidgets.QLabel(message)
        label.setWordWrap(True)
        label.setStyleSheet(
            f"color: {fg}; font-size: 12px; font-weight: 600; background: transparent; border: none;"
        )
        toast_layout.addWidget(label)
        toast.setMaximumWidth(440)
        toast.adjustSize()

        self._active_toasts.append(toast)
        self.toast_container.show()
        toast.show()
        self._reflow_toasts()

        QtCore.QTimer.singleShot(duration_ms, lambda t=toast: self._remove_toast(t))

    def _remove_toast(self, toast: QtWidgets.QWidget) -> None:
        if toast in getattr(self, "_active_toasts", []):
            self._active_toasts.remove(toast)
        toast.hide()
        toast.deleteLater()
        self._reflow_toasts()
        if hasattr(self, "toast_container") and not self._active_toasts:
            self.toast_container.hide()

    def _reflow_toasts(self) -> None:
        if not hasattr(self, "toast_container"):
            return
        x_margin = 16
        y = 16
        max_width = min(440, max(260, self.toast_container.width() - 32))
        for toast in reversed(self._active_toasts):
            toast.setFixedWidth(max_width)
            toast.adjustSize()
            height = toast.sizeHint().height()
            x = max(8, self.toast_container.width() - toast.width() - x_margin)
            toast.setGeometry(x, y, toast.width(), height)
            y += height + 10
    
    def _create_logo_container(self) -> QtWidgets.QWidget:
        """Erstellt Logo-Container (wiederverwendbar)"""
        container = QtWidgets.QWidget()
        container.setObjectName("logo_container")
        container.setStyleSheet("""
            QWidget#logo_container {
                background: transparent;
                border: none;
                margin: 0 12px 16px 12px;
            }
        """)
        
        layout = QtWidgets.QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Logo laden
        logo_label = self._create_logo_label()
        layout.addWidget(logo_label)
        
        # # Titel
        # title = QtWidgets.QLabel("Verwaltung ND-Hubs")
        # title.setFont(AppleTheme.get_font('title_3'))
        # title.setStyleSheet(f"color: {AppleTheme.COLORS['label']}; font-weight: 700; background: transparent;")
        # title.setAlignment(Qt.AlignCenter)
        # layout.addWidget(title)      
               
        return container
    
    def _create_logo_label(self) -> QtWidgets.QWidget:
        """
        Erstellt Logo-Label mit abgerundeten Ecken und Beschriftung
        Base64 oder Emoji-Fallback
        """
        # Container für Logo + Text
        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)  # Abstand zwischen Logo und Text
        
        try:
            import base64

            from PySide6.QtCore import QRectF
            from PySide6.QtGui import QPainter, QPainterPath
            
            logo_data = base64.b64decode(LOGO_BASE64)
            pixmap = QtGui.QPixmap()
            
            if pixmap.loadFromData(logo_data) and not pixmap.isNull():
                # Logo skalieren
                scaled_pixmap = pixmap.scaled(
                    84, 84,
                    Qt.KeepAspectRatio, 
                    Qt.SmoothTransformation
                )
                
                # Erstelle ein neues Pixmap mit transparentem Hintergrund
                size = scaled_pixmap.size()
                rounded_pixmap = QtGui.QPixmap(size)
                rounded_pixmap.fill(Qt.transparent)
                
                # Male das Logo mit abgerundeten Ecken
                painter = QPainter(rounded_pixmap)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                
                # Erstelle Pfad mit abgerundeten Ecken
                path = QPainterPath()
                rect = QRectF(0, 0, size.width(), size.height())
                radius = 16  # Radius anpassbar (8-20 empfohlen)
                path.addRoundedRect(rect, radius, radius)
                
                # Clipping anwenden und Logo zeichnen
                painter.setClipPath(path)
                painter.drawPixmap(0, 0, scaled_pixmap)
                painter.end()
                
                # Logo-Label
                logo_label = QtWidgets.QLabel()
                logo_label.setPixmap(rounded_pixmap)
                logo_label.setAlignment(Qt.AlignCenter)
                logo_label.setStyleSheet("QLabel { background: transparent; }")
                layout.addWidget(logo_label)
                
        except Exception as e:
            logger.debug(f"Logo-Fehler: {e}. Fallback auf Emoji.")
            
            # Fallback: Emoji
            logo_label = QtWidgets.QLabel("")
            logo_label.setFont(AppleTheme.get_font('largetitle'))
            logo_label.setAlignment(Qt.AlignCenter)
            logo_label.setStyleSheet("QLabel { background: transparent; }")
            layout.addWidget(logo_label)
        
        # ===== BRANDING UNTER DEM LOGO =====
        brand_label = QtWidgets.QLabel("ND-Hub")
        brand_label.setFont(AppleTheme.get_font('headline'))
        brand_label.setAlignment(Qt.AlignCenter)
        brand_label.setStyleSheet("""
            QLabel {
                color: #ecf0f1;
                background: transparent;
                font-weight: 800;
                padding-top: 4px;
            }
        """)
        layout.addWidget(brand_label)

        claim_label = QtWidgets.QLabel("Die Notfalldepot-Verwaltung")
        claim_label.setFont(AppleTheme.get_font('caption1'))
        claim_label.setWordWrap(True)
        claim_label.setAlignment(Qt.AlignCenter)
        claim_label.setMaximumWidth(170)
        claim_label.setStyleSheet("""
            QLabel {
                color: #bdc3c7;
                background: transparent;
                font-weight: 500;
                padding-bottom: 4px;
            }
        """)
        layout.addWidget(claim_label)
        # ===== ENDE BRANDING =====
        
        return container
    
    def _add_navigation_buttons(self, layout: QtWidgets.QVBoxLayout) -> None:
        """Fügt Navigations-Buttons zur Sidebar hinzu"""
        buttons = [
            ("Dashboard", PageIndex.DASHBOARD, "home"),
            ("Bewegungen", PageIndex.MOVEMENTS, "activity"),
            ("Verlauf", PageIndex.HISTORIE, "clock"),
            ("Auswertungen", PageIndex.AUSWERTUNGEN, "pie_chart"),
            ("Import", PageIndex.IMPORT, "download"),
            ("E-Mail", PageIndex.EMAIL, "mail"),
            ("Grundeinstellungen", PageIndex.GRUNDEINSTELLUNGEN, "settings"),
        ]
        
        for text, page_idx, icon_name in buttons:
            btn = self.create_sidebar_button(text, icon_name)
            layout.addWidget(btn)
    
    def _add_user_section(self, layout: QtWidgets.QVBoxLayout) -> None:
        """Fügt User-Info und -Buttons zur Sidebar hinzu"""
        # Trennlinie
        separator = QtWidgets.QFrame()
        separator.setFrameShape(QtWidgets.QFrame.HLine)
        separator.setStyleSheet("background-color: rgba(255, 255, 255, 0.2); margin: 10px 16px;")
        layout.addWidget(separator)
        
        # User-Info-Widget
        user_widget = self._create_user_info_widget()
        layout.addWidget(user_widget)
        
        # Profilbild für den aktuellen Benutzer
        self.btn_change_avatar = self._create_styled_button("Profilbild ändern", self.change_user_avatar)
        self.btn_change_avatar.setIcon(IconManager.get_icon("folder", color="#ecf0f1"))
        layout.addWidget(self.btn_change_avatar)

        self.btn_remove_avatar = self._create_styled_button("Profilbild entfernen", self.remove_user_avatar)
        self.btn_remove_avatar.setIcon(IconManager.get_icon("x", color="#ecf0f1"))
        layout.addWidget(self.btn_remove_avatar)

        # Passwort-Button
        self.btn_change_password = self._create_styled_button("Passwort ändern", self.change_user_password)
        self.btn_change_password.setIcon(IconManager.get_icon("key", color="#ecf0f1"))
        layout.addWidget(self.btn_change_password)
        
        # Theme-Toggle
        text = " Dark Mode" if not AppleTheme.is_dark_mode else " Light Mode"
        icon_name = "moon" if not AppleTheme.is_dark_mode else "sun"
        self.btn_theme_toggle = self._create_styled_button(text, self.toggle_theme)
        self.btn_theme_toggle.setIcon(IconManager.get_icon(icon_name, color="#ecf0f1"))
        layout.addWidget(self.btn_theme_toggle)

        # Logout
        self.btn_logout = self._create_logout_button()
        layout.addWidget(self.btn_logout)

    def _apply_chrome_overlay_styles(self) -> None:
        """Banner, Busy- und Login-Overlays an AppleTheme anpassen (Dark/Light)."""
        c = AppleTheme.current_colors()
        dim = "rgba(15, 23, 42, 200)" if AppleTheme.is_dark_mode else "rgba(15, 23, 42, 170)"
        dim_busy = "rgba(15, 23, 42, 200)" if AppleTheme.is_dark_mode else "rgba(15, 23, 42, 110)"

        if hasattr(self, "read_only_banner"):
            self.read_only_banner.setStyleSheet(
                f"background-color: {c['status_orange_bg']}; border-bottom: 1px solid {c['status_orange']};"
            )
        if hasattr(self, "read_only_banner_label"):
            self.read_only_banner_label.setStyleSheet(
                f"color: {c['status_orange']}; font-size: 12px; font-weight: 600;"
            )

        if hasattr(self, "busy_overlay"):
            self.busy_overlay.setStyleSheet(
                f"QWidget#page_busy_overlay {{ background-color: {dim_busy}; }}"
            )
        if hasattr(self, "_busy_card_frame"):
            self._busy_card_frame.setStyleSheet(
                f"QFrame#busy_card {{"
                f"background-color: {c['bg_secondary']};"
                f"border: 1px solid {c['separator']};"
                f"border-radius: 12px;"
                f"padding: 18px;"
                f"}}"
            )
        if hasattr(self, "busy_label"):
            self.busy_label.setStyleSheet(
                f"font-size: 14px; font-weight: 600; color: {c['label']}; background: transparent;"
            )
        if hasattr(self, "busy_hint_label"):
            self.busy_hint_label.setStyleSheet(
                f"font-size: 12px; color: {c['secondary_label']}; background: transparent;"
            )

        if hasattr(self, "login_overlay"):
            self.login_overlay.setStyleSheet(
                f"QWidget#login_overlay {{ background-color: {dim}; }}"
            )
        if hasattr(self, "_login_card_frame"):
            self._login_card_frame.setStyleSheet(
                f"QFrame#login_card {{"
                f"background-color: {c['bg_secondary']};"
                f"border: 1px solid {c['separator']};"
                f"border-radius: 12px;"
                f"padding: 28px;"
                f"}}"
            )
        if hasattr(self, "_login_title_label"):
            self._login_title_label.setStyleSheet(
                f"font-size: 24px; font-weight: 700; color: {c['label']}; background: transparent;"
            )
        if hasattr(self, "_login_subtitle_label"):
            self._login_subtitle_label.setStyleSheet(
                f"font-size: 14px; color: {c['secondary_label']}; line-height: 1.4; background: transparent;"
            )
        if hasattr(self, "_login_hint_label"):
            self._login_hint_label.setStyleSheet(
                f"font-size: 12px; color: {c['tertiary_label']}; background: transparent;"
            )
        le_style = (
            f"QLineEdit {{"
            f"background-color: {c['bg_tertiary']};"
            f"color: {c['label']};"
            f"border: 1px solid {c['separator']};"
            f"border-radius: 8px;"
            f"padding: 8px 10px;"
            f"selection-background-color: {c['blue']};"
            f"selection-color: #ffffff;"
            f"}}"
        )
        if hasattr(self, "login_user_input"):
            self.login_user_input.setStyleSheet(le_style)
        if hasattr(self, "login_password_input"):
            self.login_password_input.setStyleSheet(le_style)
        if hasattr(self, "login_error_label"):
            self.login_error_label.setStyleSheet(
                f"color: {c['red']}; font-size: 12px; background: transparent;"
            )

    def toggle_theme(self) -> None:
        """Schaltet zwischen Light- und Dark-Mode um"""
        AppleTheme.is_dark_mode = not AppleTheme.is_dark_mode
        
        # UI aktualisieren
        self.setStyleSheet(AppleTheme.get_stylesheet())
        self._apply_chrome_overlay_styles()
        
        # Toggle-Button Text aktualisieren
        text = " Dark Mode" if not AppleTheme.is_dark_mode else " Light Mode"
        icon_name = "moon" if not AppleTheme.is_dark_mode else "sun"
        self.btn_theme_toggle.setText(text)
        self.btn_theme_toggle.setIcon(IconManager.get_icon(icon_name, color="#ecf0f1"))
        
        # Sidebar-Buttons aktualisieren (Farben neu laden)
        for btn in self.sidebar_buttons:
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        
        # Aktiven Button neu markieren
        self.set_active_button(self.stack.currentIndex())
        
        # Aktuelle Seite benachrichtigen (speziell für Matplotlib/Charts)
        current_page = self.stack.currentWidget()
        if hasattr(current_page, "refresh_theme"):
            current_page.refresh_theme()
        
        logging.info(f"Theme gewechselt: {'Dark' if AppleTheme.is_dark_mode else 'Light'} Mode")
    
    def _create_user_info_widget(self) -> QtWidgets.QWidget:
        """Erstellt User-Info-Widget (Icon, Name, Rolle)"""
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(4)
        
        # Icon
        self.user_avatar_label = QtWidgets.QLabel()
        self.user_avatar_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.user_avatar_label)
        
        # Name
        self.user_name_label = QtWidgets.QLabel(self.security.get_current_user() or "Nicht angemeldet")
        c = AppleTheme.current_colors()
        self.user_name_label.setStyleSheet(f"color: {c['sidebar_text_active']}; font-size: 13px; font-weight: 600;")
        self.user_name_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.user_name_label)
        
        # Rolle
        self.user_role_label = QtWidgets.QLabel(f"({self.security.get_current_role() or '-'})")
        self.user_role_label.setStyleSheet(f"color: {c['sidebar_text']}; font-size: 11px;")
        self.user_role_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.user_role_label)

        self.user_mode_label = QtWidgets.QLabel("")
        self.user_mode_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.user_mode_label)
        self._refresh_user_sidebar_state()
        
        return widget

    def _refresh_user_sidebar_state(self) -> None:
        """Synchronisiert Benutzerinfos und Admin-Buttons nach Login."""
        if hasattr(self, "user_name_label"):
            self.user_name_label.setText(self.security.get_current_user() or "Nicht angemeldet")
        if hasattr(self, "user_role_label"):
            self.user_role_label.setText(f"({self.security.get_current_role() or '-'})")
        current_user = self.security.get_current_user() if hasattr(self, "security") else None
        if hasattr(self, "user_mode_label"):
            if not current_user:
                self.user_mode_label.setText("")
                if hasattr(self, "read_only_banner"):
                    self.read_only_banner.setVisible(False)
            elif hasattr(self, "db") and self.db.is_read_only_mode():
                self.user_mode_label.setText("Modus: Nur Lesen")
                oc = AppleTheme.current_colors()
                self.user_mode_label.setStyleSheet(
                    f"color: {oc['status_orange']}; font-size: 11px; font-weight: 600;"
                )
                if hasattr(self, "read_only_banner"):
                    self.read_only_banner.setVisible(True)
            else:
                self.user_mode_label.setText("Modus: Schreiben")
                oc = AppleTheme.current_colors()
                self.user_mode_label.setStyleSheet(
                    f"color: {oc['status_green']}; font-size: 11px; font-weight: 600;"
                )
                if hasattr(self, "read_only_banner"):
                    self.read_only_banner.setVisible(False)
        self._update_user_avatar_display()

    def _apply_write_mode_to_page(self, page: QtWidgets.QWidget) -> None:
        """Deaktiviert Schreib-Buttons bei read-only Sessions."""
        if page is None or not hasattr(self, "db"):
            return
        read_only = self.db.is_read_only_mode()
        for widget in page.findChildren(QtWidgets.QAbstractButton):
            object_name = widget.objectName() or ""
            requires_write = bool(widget.property("requires_write"))
            btn_class = str(widget.property("class") or "")
            if object_name in {"btn_add", "btn_save", "btn_delete"} or btn_class in {"btn_add", "btn_save", "btn_delete"} or requires_write:
                widget.setEnabled(not read_only)

    def _update_user_avatar_display(self) -> None:
        """Aktualisiert Profilbild in der Sidebar."""
        if not hasattr(self, "user_avatar_label"):
            return
        avatar_path = self.security.get_current_user_avatar_path()
        if avatar_path and os.path.exists(avatar_path):
            pixmap = QtGui.QPixmap(avatar_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(44, 44, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                rounded = QtGui.QPixmap(44, 44)
                rounded.fill(Qt.transparent)
                painter = QtGui.QPainter(rounded)
                painter.setRenderHint(QtGui.QPainter.Antialiasing)
                path = QtGui.QPainterPath()
                path.addEllipse(0, 0, 44, 44)
                painter.setClipPath(path)
                painter.drawPixmap(0, 0, scaled)
                painter.end()
                self.user_avatar_label.setPixmap(rounded)
                return
        self.user_avatar_label.setPixmap(IconManager.get_pixmap("user", color="#ecf0f1", size=36))
    
    def _create_styled_button(self, text: str, callback) -> QtWidgets.QPushButton:
        """Factory für Sidebar-Buttons (DRY)"""
        btn = QtWidgets.QPushButton(text)
        btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #bdc3c7;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 6px;
                padding: 8px 12px;
                text-align: center;
                margin: 4px 16px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: rgba(52, 152, 219, 0.2);
                color: #ecf0f1;
            }
        """)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(callback)
        return btn
    
    def _create_logout_button(self) -> QtWidgets.QPushButton:
        """Erstellt Logout-Button (spezielles Styling)"""
        btn = QtWidgets.QPushButton(" Abmelden")
        btn.setIcon(IconManager.get_icon("log_out", color="white"))
        btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(231, 76, 60, 0.8);
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 12px;
                text-align: center;
                margin: 8px 16px 16px 16px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: rgba(192, 57, 43, 1);
            }
        """)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(self.logout)
        return btn
    
    def _init_pages(self) -> None:
        """Erstellt Stack-Platzhalter und lädt Seiten bei Bedarf."""
        self._page_instances = {}
        self._settings_backup_checked = False
        self.page_dashboard = None
        self.page_grundeinstellungen = None

        for _ in range(len(PageIndex)):
            self.stack.addWidget(QtWidgets.QWidget())

        self._ensure_page_loaded(PageIndex.DASHBOARD)
        self.stack.setCurrentIndex(PageIndex.DASHBOARD)
        self.set_active_button(PageIndex.DASHBOARD)

    def _create_page_instance(self, idx: int):
        """Erzeugt eine Seite lazily beim ersten Aufruf."""
        if idx == PageIndex.DASHBOARD:
            from apple_dashboard import AppleDashboard
            page = AppleDashboard(self.db, self.verfallmanager)
            page.requestedPage.connect(self.switch_to_page)
            self.page_dashboard = page
            return page
        if idx == PageIndex.MOVEMENTS:
            from ui.pages.page_bewegungen import BewegungenPage
            return BewegungenPage(self.db, self.attachment_folder, security=self.security)
        if idx == PageIndex.HISTORIE:
            from ui.pages.page_historie import BewegungshistoriePage
            return BewegungshistoriePage(self.db)
        if idx == PageIndex.AUSWERTUNGEN:
            from ui.pages.page_auswertungen import AuswertungenPage
            return AuswertungenPage(self.db)
        if idx == PageIndex.IMPORT:
            from ui.pages.page_import import ImportPage
            return ImportPage(self.db)
        if idx == PageIndex.EMAIL:
            from ui.pages.page_email import EmailPage
            return EmailPage(self.db)
        if idx == PageIndex.GRUNDEINSTELLUNGEN:
            from ui.pages.page_grundeinstellungen import GrundeinstellungenPage
            page = GrundeinstellungenPage(self.db, security=self.security)
            self.page_grundeinstellungen = page
            return page
        raise ValueError(f"Unbekannter PageIndex: {idx}")

    def _ensure_page_loaded(self, idx: int):
        """Stellt sicher, dass die gewünschte Seite im Stack geladen ist."""
        if idx in self._page_instances:
            return self._page_instances[idx]
        page = self._create_page_instance(idx)
        placeholder = self.stack.widget(idx)
        self.stack.insertWidget(idx, page)
        if placeholder is not None:
            self.stack.removeWidget(placeholder)
            placeholder.deleteLater()
        self._page_instances[idx] = page
        self._install_page_enhancements(page)
        return page
    
    def _init_timers(self) -> None:
        """Startet Auto-Refresh-Timer"""
        self.verfall_refresh_timer = QtCore.QTimer(self)
        self.verfall_refresh_timer.timeout.connect(self.refresh_verfall_widgets)
        self.verfall_refresh_timer.start(300000)  # 5 Minuten

        self.write_lease_timer = QtCore.QTimer(self)
        self.write_lease_timer.timeout.connect(self._heartbeat_write_lease)
        self.write_lease_timer.start(10000)  # 10 Sekunden

        self.sync_timer = QtCore.QTimer(self)
        self.sync_timer.timeout.connect(self._run_sync_cycle)
        self._refresh_sync_scheduler()

    def _refresh_sync_scheduler(self) -> None:
        """Aktualisiert den periodischen Sync-Timer anhand der aktuellen Konfiguration."""
        if not hasattr(self, "sync_timer"):
            return
        mode = OperatingMode.from_raw(self.config.get_operating_mode())
        interval_ms = max(10, self.config.get_sync_interval_seconds()) * 1000
        self.sync_timer.setInterval(interval_ms)
        if mode == OperatingMode.HYBRID_SYNC:
            if not self.sync_timer.isActive():
                self.sync_timer.start()
                QtCore.QTimer.singleShot(1000, self._run_sync_cycle)
            logger.info("Sync-Timer aktiv: mode=%s interval=%ss", mode.value, interval_ms // 1000)
        else:
            if self.sync_timer.isActive():
                self.sync_timer.stop()
            logger.info("Sync-Timer pausiert: mode=%s", mode.value)

    def _heartbeat_write_lease(self) -> None:
        """Aktualisiert den Write-Lease periodisch."""
        if not hasattr(self, "db") or not hasattr(self, "security"):
            return
        username = self.security.get_current_user()
        if not username:
            return
        if self.db.write_lease_owner:
            still_writer = self.db.refresh_write_lease(username)
            if not still_writer:
                self.security.set_query_only(True)
                QtWidgets.QMessageBox.warning(
                    self,
                    "Schreibzugriff verloren",
                    "Diese Sitzung wurde in den Nur-Lesen Modus versetzt.",
                )
                self.show_toast("Schreibzugriff verloren - Nur-Lesen Modus aktiv.", "warning", 3200)
                self._refresh_user_sidebar_state()
                current = self.stack.currentWidget() if hasattr(self, "stack") else None
                if current is not None:
                    self._apply_write_mode_to_page(current)

    def _run_sync_cycle(self) -> None:
        """Plant einen Push/Pull-Cycle im QThreadPool (non-blocking).

        Vorher lief ``self.sync_service.run_cycle`` synchron im UI-Thread
        und konnte bei langsamen Backend-Antworten die UI einfrieren.
        Mit dem Worker-Runner läuft der Cycle in einem Worker-Thread und
        die UI bleibt reaktiv. Ergebnis-Updates kommen via Signal zurück.
        """
        if not hasattr(self, "sync_worker_runner") or not hasattr(self, "security"):
            return
        username = self.security.get_current_user()
        if not username:
            return
        started = self.sync_worker_runner.submit(username)
        if not started:
            # Bereits ein Cycle aktiv oder Username leer — kein Log-Spam
            # (Timer feuert u. U. häufiger als Intervalle abgeschlossen sind).
            return

    def _on_sync_cycle_finished(self, payload: dict) -> None:
        """Slot: erfolgreicher Sync-Cycle, ggf. UI aktualisieren."""
        pushed = payload.get("pushed", 0) or 0
        pulled = payload.get("pulled", 0) or 0
        rejected = payload.get("rejected", 0) or 0
        conflicts = payload.get("conflicts", 0) or 0
        if pushed or pulled or rejected or conflicts:
            logger.info(
                "Sync-Zyklus: mode=%s pushed=%s pulled=%s rejected=%s conflicts=%s reason=%s",
                payload.get("effective_mode"),
                pushed,
                pulled,
                rejected,
                conflicts,
                payload.get("reason"),
            )
        # Pull kann Stammdaten/Depots verändert haben → Cache invalidieren
        # und ggf. sichtbare Seiten neu laden.
        if pulled:
            try:
                if hasattr(self.db, "_clear_lookup_caches"):
                    self.db._clear_lookup_caches()
            except Exception as exc:  # noqa: BLE001
                logger.debug("Cache-Invalidierung nach Sync fehlgeschlagen: %s", exc)
            if hasattr(self, "_refresh_user_sidebar_state"):
                self._refresh_user_sidebar_state()

    def _on_sync_cycle_failed(self, message: str) -> None:
        """Slot: Sync-Cycle fehlgeschlagen."""
        logger.warning("Sync-Zyklus fehlgeschlagen: %s", message)

    def _on_sync_cycle_skipped(self, reason: str) -> None:
        """Slot: Sync-Cycle wurde übersprungen (z. B. kein Hybrid-Mode)."""
        logger.debug("Sync-Cycle übersprungen: %s", reason)

    def _setup_integrated_login(self) -> None:
        """Login als Overlay im Hauptfenster statt separatem Fenster."""
        self._login_attempts = 0
        self.login_overlay = QtWidgets.QWidget(self)
        self.login_overlay.setObjectName("login_overlay")

        overlay_layout = QtWidgets.QVBoxLayout(self.login_overlay)
        overlay_layout.setContentsMargins(24, 24, 24, 24)
        overlay_layout.addStretch()

        self._login_card_frame = QtWidgets.QFrame()
        self._login_card_frame.setObjectName("login_card")
        self._login_card_frame.setMaximumWidth(560)
        self._login_card_frame.setMinimumWidth(500)
        card_layout = QtWidgets.QVBoxLayout(self._login_card_frame)
        card_layout.setSpacing(14)

        self._login_title_label = QtWidgets.QLabel("Willkommen bei ND-Hub")
        card_layout.addWidget(self._login_title_label)

        self._login_subtitle_label = QtWidgets.QLabel(
            "Melden Sie sich mit Ihrem Benutzerkonto an, um "
            "Bestände, Bewegungen und Auswertungen sicher zu verwalten."
        )
        self._login_subtitle_label.setWordWrap(True)
        card_layout.addWidget(self._login_subtitle_label)

        self._login_hint_label = QtWidgets.QLabel(
            "Hinweis: Bei Problemen wenden Sie sich an einen Administrator."
        )
        self._login_hint_label.setWordWrap(True)
        card_layout.addWidget(self._login_hint_label)

        self.login_user_input = QtWidgets.QLineEdit()
        self.login_user_input.setPlaceholderText("Benutzername")
        self.login_user_input.setMinimumHeight(42)
        card_layout.addWidget(self.login_user_input)

        self.login_password_input = QtWidgets.QLineEdit()
        self.login_password_input.setPlaceholderText("Passwort")
        self.login_password_input.setEchoMode(QtWidgets.QLineEdit.Password)
        self.login_password_input.setMinimumHeight(42)
        card_layout.addWidget(self.login_password_input)

        self.login_error_label = QtWidgets.QLabel("")
        self.login_error_label.setWordWrap(True)
        card_layout.addWidget(self.login_error_label)

        self.login_submit_btn = QtWidgets.QPushButton("Anmelden")
        self.login_submit_btn.setObjectName("btn_save")
        self.login_submit_btn.setMinimumHeight(46)
        self.login_submit_btn.setDefault(True)
        self.login_submit_btn.setAutoDefault(True)
        card_layout.addWidget(self.login_submit_btn)

        overlay_layout.addWidget(self._login_card_frame, alignment=Qt.AlignHCenter)
        overlay_layout.addStretch()

        self.login_submit_btn.clicked.connect(self._perform_integrated_login)
        self.login_user_input.returnPressed.connect(self._perform_integrated_login)
        self.login_password_input.returnPressed.connect(self._perform_integrated_login)

        self._apply_chrome_overlay_styles()

        self.login_overlay.setGeometry(self.rect())
        self.login_overlay.raise_()
        self.login_overlay.show()
        self.login_user_input.setFocus()

    def _perform_integrated_login(self) -> None:
        """Authentifiziert den Benutzer aus dem eingebetteten Login-Overlay."""
        username = self.login_user_input.text().strip()
        password = self.login_password_input.text()
        success, message = self.security.authenticate(username, password)

        if success:
            logger.info(
                "Benutzer '%s' angemeldet (Rolle: %s)",
                username,
                self.security.get_current_role(),
            )
            self.login_overlay.hide()
            self._handle_successful_login(username)
            self.show_toast(f"Willkommen, {username}.", "success")
            return

        self._login_attempts += 1
        remaining = 3 - self._login_attempts
        if remaining <= 0:
            QtWidgets.QMessageBox.critical(
                self,
                "Zugriff verweigert",
                "Maximale Anzahl an Anmeldeversuchen überschritten.",
            )
            QtWidgets.QApplication.quit()
            return

        self.login_error_label.setText(f"{message} Noch {remaining} Versuch(e) übrig.")
        self.login_password_input.clear()
        self.login_password_input.setFocus()

    def _show_confirmation_overlay(
        self,
        title: str,
        message: str,
        confirm_text: str,
        on_confirm,
        cancel_text: str = "Abbrechen",
        confirm_object_name: str = "btn_save",
    ) -> None:
        """Zeigt eine integrierte Bestätigungsabfrage im Hauptfenster."""
        self._hide_confirmation_overlay()

        c = AppleTheme.current_colors()
        dim = "rgba(15, 23, 42, 200)" if AppleTheme.is_dark_mode else "rgba(15, 23, 42, 170)"

        self.confirm_overlay = QtWidgets.QWidget(self)
        self.confirm_overlay.setObjectName("confirm_overlay")
        self.confirm_overlay.setStyleSheet(
            f"QWidget#confirm_overlay {{ background-color: {dim}; }}"
        )
        self.confirm_overlay.setGeometry(self.rect())

        overlay_layout = QtWidgets.QVBoxLayout(self.confirm_overlay)
        overlay_layout.setContentsMargins(24, 24, 24, 24)
        overlay_layout.addStretch()

        card = QtWidgets.QFrame()
        card.setObjectName("confirm_card")
        card.setMaximumWidth(480)
        card.setStyleSheet(
            f"QFrame#confirm_card {{"
            f"background-color: {c['bg_secondary']};"
            f"border: 1px solid {c['separator']};"
            f"border-radius: 12px;"
            f"padding: 20px;"
            f"}}"
        )
        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setSpacing(12)

        title_label = QtWidgets.QLabel(title)
        title_label.setStyleSheet(
            f"font-size: 20px; font-weight: 700; color: {c['label']}; background: transparent;"
        )
        card_layout.addWidget(title_label)

        message_label = QtWidgets.QLabel(message)
        message_label.setWordWrap(True)
        message_label.setStyleSheet(
            f"font-size: 13px; color: {c['secondary_label']}; background: transparent;"
        )
        card_layout.addWidget(message_label)

        button_row = QtWidgets.QHBoxLayout()
        button_row.addStretch()

        cancel_btn = QtWidgets.QPushButton(cancel_text)
        cancel_btn.setObjectName("btn_secondary")
        cancel_btn.setMinimumHeight(40)
        cancel_btn.clicked.connect(self._hide_confirmation_overlay)
        button_row.addWidget(cancel_btn)

        confirm_btn = QtWidgets.QPushButton(confirm_text)
        confirm_btn.setObjectName(confirm_object_name)
        confirm_btn.setMinimumHeight(40)

        def _confirm_and_close():
            self._hide_confirmation_overlay()
            on_confirm()

        confirm_btn.clicked.connect(_confirm_and_close)
        button_row.addWidget(confirm_btn)
        card_layout.addLayout(button_row)

        overlay_layout.addWidget(card, alignment=Qt.AlignHCenter)
        overlay_layout.addStretch()

        self.confirm_overlay.raise_()
        self.confirm_overlay.show()

    def _hide_confirmation_overlay(self) -> None:
        if hasattr(self, "confirm_overlay") and self.confirm_overlay is not None:
            self.confirm_overlay.hide()
            self.confirm_overlay.deleteLater()
            self.confirm_overlay = None

    def _show_logout_choice_overlay(self) -> None:
        """Zeigt die Auswahl zwischen Benutzerwechsel und Beenden."""
        self._hide_confirmation_overlay()

        c = AppleTheme.current_colors()
        dim = "rgba(15, 23, 42, 200)" if AppleTheme.is_dark_mode else "rgba(15, 23, 42, 170)"

        self.confirm_overlay = QtWidgets.QWidget(self)
        self.confirm_overlay.setObjectName("confirm_overlay")
        self.confirm_overlay.setStyleSheet(
            f"QWidget#confirm_overlay {{ background-color: {dim}; }}"
        )
        self.confirm_overlay.setGeometry(self.rect())

        overlay_layout = QtWidgets.QVBoxLayout(self.confirm_overlay)
        overlay_layout.setContentsMargins(24, 24, 24, 24)
        overlay_layout.addStretch()

        card = QtWidgets.QFrame()
        card.setObjectName("confirm_card")
        card.setMaximumWidth(520)
        card.setStyleSheet(
            f"QFrame#confirm_card {{"
            f"background-color: {c['bg_secondary']};"
            f"border: 1px solid {c['separator']};"
            f"border-radius: 12px;"
            f"padding: 20px;"
            f"}}"
        )
        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setSpacing(12)

        title_label = QtWidgets.QLabel("Abmelden")
        title_label.setStyleSheet(
            f"font-size: 20px; font-weight: 700; color: {c['label']}; background: transparent;"
        )
        card_layout.addWidget(title_label)

        message_label = QtWidgets.QLabel(
            "Möchten Sie den Benutzer wechseln oder das Programm beenden?"
        )
        message_label.setWordWrap(True)
        message_label.setStyleSheet(
            f"font-size: 13px; color: {c['secondary_label']}; background: transparent;"
        )
        card_layout.addWidget(message_label)

        button_row = QtWidgets.QHBoxLayout()
        button_row.addStretch()

        cancel_btn = QtWidgets.QPushButton("Abbrechen")
        cancel_btn.setObjectName("btn_secondary")
        cancel_btn.setMinimumHeight(40)
        cancel_btn.clicked.connect(self._hide_confirmation_overlay)
        button_row.addWidget(cancel_btn)

        switch_btn = QtWidgets.QPushButton("Benutzer wechseln")
        switch_btn.setObjectName("btn_save")
        switch_btn.setMinimumHeight(40)
        switch_btn.clicked.connect(self._execute_user_switch)
        button_row.addWidget(switch_btn)

        quit_btn = QtWidgets.QPushButton("Programm beenden")
        quit_btn.setObjectName("btn_delete")
        quit_btn.setMinimumHeight(40)
        quit_btn.clicked.connect(self._confirm_close)
        button_row.addWidget(quit_btn)

        card_layout.addLayout(button_row)
        overlay_layout.addWidget(card, alignment=Qt.AlignHCenter)
        overlay_layout.addStretch()

        self.confirm_overlay.raise_()
        self.confirm_overlay.show()
    
    # ============================================================
    # EVENT HANDLERS
    # ============================================================
    def create_sidebar_button(self, text: str, icon_name: str = None) -> QtWidgets.QPushButton:
        """Erstellt Sidebar-Button mit Auto-Registrierung und Icon"""
        btn = QtWidgets.QPushButton(f" {text}")
        if icon_name:
            btn.setIcon(IconManager.get_icon(icon_name, color="#ecf0f1"))
            btn.setIconSize(QtCore.QSize(18, 18))
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda: self.on_sidebar_click(btn))
        self.sidebar_buttons.append(btn)
        return btn
    
    def on_sidebar_click(self, clicked_btn: QtWidgets.QPushButton) -> None:
        """Handler für Sidebar-Navigation"""
        idx = self.sidebar_buttons.index(clicked_btn)
        self.switch_to_page(idx)

    def switch_to_page(self, idx: int) -> None:
        """Zentrale Methode zum Seitenwechsel mit Zugriffskontrolle"""
        current_page = self.stack.currentWidget() if hasattr(self, "stack") else None
        if current_page is not None and self.stack.currentIndex() != idx:
            if not self._confirm_discard_unsaved_changes(current_page):
                return

        # Zugriffskontrolle für geschützte Seiten
        if idx == PageIndex.GRUNDEINSTELLUNGEN:
            if not self.security.is_admin():
                QtWidgets.QMessageBox.warning(
                    self,
                    "Keine Berechtigung",
                    f"Nur Administratoren haben Zugriff auf die Grundeinstellungen.\n\n"
                    f"Ihre Rolle: {self.security.get_current_role()}"
                )
                return
        
        busy_op_id = -1
        try:
            page_name = PageIndex(idx).name.replace("_", " ").title() if idx in PageIndex._value2member_map_ else "Seite"
            heavy_pages = {PageIndex.AUSWERTUNGEN, PageIndex.HISTORIE, PageIndex.EMAIL}
            busy_delay_ms = 0 if idx in heavy_pages else 120
            busy_op_id = self._begin_busy_operation(f"Lade {page_name} ...", delay_ms=busy_delay_ms)
            # Navigation durchführen
            page = self._ensure_page_loaded(idx)
            self.stack.setCurrentWidget(page)
            self.set_active_button(idx)
            self._apply_write_mode_to_page(page)

            if idx == PageIndex.GRUNDEINSTELLUNGEN and not self._settings_backup_checked:
                try:
                    if not self.db.is_read_only_mode():
                        self.page_grundeinstellungen.check_auto_backup()
                finally:
                    self._settings_backup_checked = True
        except Exception as e:
            logger.error("Seitenwechsel fehlgeschlagen (idx=%s): %s", idx, e, exc_info=True)
            QtWidgets.QMessageBox.critical(
                self,
                "Seite konnte nicht geladen werden",
                "Die gewünschte Seite konnte nicht geöffnet werden.\n\n"
                f"Fehler: {e}\n\n"
                "Bitte prüfen Sie die Logdatei für Details."
            )
            self._ensure_page_loaded(PageIndex.DASHBOARD)
            self.stack.setCurrentIndex(PageIndex.DASHBOARD)
            self.set_active_button(PageIndex.DASHBOARD)
        finally:
            self._end_busy_operation(busy_op_id)
        
        # Log bei Navigation (optional)
        # logger.debug(f"Seite gewechselt: Index {idx}")
    
    def set_active_button(self, active_idx: int) -> None:
        """Markiert aktiven Sidebar-Button"""
        for i, btn in enumerate(self.sidebar_buttons):
            btn.setProperty("active", "true" if i == active_idx else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _install_page_enhancements(self, page: QtWidgets.QWidget) -> None:
        """Registriert Dirty-Tracking/Hooks einmalig pro Seite."""
        if page is None or getattr(page, "_ndh_page_enhanced", False):
            return
        page._ndh_page_enhanced = True
        page._has_unsaved_changes = False

        def _mark_dirty(*_args, p=page):
            self._mark_page_dirty(p)

        for widget in page.findChildren(QtWidgets.QWidget):
            if isinstance(widget, QtWidgets.QLineEdit):
                widget.textChanged.connect(_mark_dirty)
            elif isinstance(widget, (QtWidgets.QTextEdit, QtWidgets.QPlainTextEdit)):
                widget.textChanged.connect(_mark_dirty)
            elif isinstance(widget, QtWidgets.QComboBox):
                widget.currentIndexChanged.connect(_mark_dirty)
            elif isinstance(widget, (QtWidgets.QSpinBox, QtWidgets.QDoubleSpinBox)):
                widget.valueChanged.connect(_mark_dirty)
            elif isinstance(widget, (QtWidgets.QDateEdit, QtWidgets.QDateTimeEdit, QtWidgets.QTimeEdit)):
                widget.dateTimeChanged.connect(_mark_dirty)
            elif isinstance(widget, (QtWidgets.QCheckBox, QtWidgets.QRadioButton)):
                widget.toggled.connect(_mark_dirty)

        for btn in page.findChildren(QtWidgets.QPushButton):
            obj = (btn.objectName() or "").lower()
            text = (btn.text() or "").strip().lower()
            if obj in {"btn_save", "btn_add", "btn_delete"} or any(
                token in text for token in ("speichern", "anlegen", "hinzufügen", "erstellen", "übernehmen")
            ):
                btn.clicked.connect(lambda _=False, p=page: QtCore.QTimer.singleShot(250, lambda: self._clear_page_dirty(p)))

    def _mark_page_dirty(self, page: QtWidgets.QWidget) -> None:
        if page is not None:
            page._has_unsaved_changes = True

    def _clear_page_dirty(self, page: QtWidgets.QWidget) -> None:
        if page is not None:
            page._has_unsaved_changes = False

    def _page_has_unsaved_changes(self, page: QtWidgets.QWidget) -> bool:
        return bool(getattr(page, "_has_unsaved_changes", False))

    def _confirm_discard_unsaved_changes(self, page: QtWidgets.QWidget) -> bool:
        """Fragt vor Seitenwechsel/Beenden bei ungespeicherten Änderungen."""
        if page is None or not self._page_has_unsaved_changes(page):
            return True
        reply = QtWidgets.QMessageBox.question(
            self,
            "Ungespeicherte Änderungen",
            "Es gibt ungespeicherte Änderungen auf der aktuellen Seite.\n"
            "Möchten Sie diese verwerfen und fortfahren?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        if reply == QtWidgets.QMessageBox.Yes:
            self._clear_page_dirty(page)
            self.show_toast("Ungespeicherte Änderungen verworfen.", "warning", 2200)
            return True
        return False
    
    def _get_verfall_data_hash(self):
        """Berechnet Hash der aktuellen Verfalldaten für Change-Detection"""
        try:
            # Einfache Heuristik: Anzahl der kritischen Verfallsdaten
            kritische = self.verfallmanager.getverfallendepraeparate(kategorie='kritisch')
            achtung = self.verfallmanager.getverfallendepraeparate(kategorie='achtung')
            kritisch_count = len(kritische)
            achtung_count = len(achtung)
            return f"{kritisch_count}_{achtung_count}"
        except Exception as e:
            logger.error(f"Fehler beim Berechnen des Verfall-Hash: {e}")
            return "error"
    
    def refresh_verfall_widgets(self) -> None:
        """Aktualisiert Verfall-Widgets nur bei tatsächlichen Änderungen (Timer-Callback)"""
        try:
            current_hash = self._get_verfall_data_hash()
            
            # Nur aktualisieren, wenn sich Daten geändert haben
            if current_hash != self.cache._last_verfall_hash:
                if hasattr(self.page_dashboard, 'verfall_widget'):
                    self.page_dashboard.verfall_widget.refresh()
                
                if hasattr(self, 'verfall_indicator'):
                    self.verfall_indicator.refresh()
                
                self.cache._last_verfall_hash = current_hash
                perf_logger.info("Verfall-Widgets aktualisiert (Daten geändert)")
            else:
                perf_logger.debug("Verfall-Widgets: Keine Änderungen, Skip Refresh")
                
        except Exception as e:
            logger.error(f"Fehler beim Refresh: {e}", exc_info=True)
    
    # ============================================================
    # USER ACTIONS
    # ============================================================
    def change_user_password(self) -> None:
        """Öffnet Dialog zum Passwort-Ändern"""
        if hasattr(self, "db") and self.db.is_read_only_mode():
            QtWidgets.QMessageBox.warning(self, "Nur-Lesen Modus", "Passwortänderung ist im Nur-Lesen Modus nicht möglich.")
            return
        from ui.dialogs.login_dialog import ChangePasswordDialog

        user_id = self.security.get_current_user_id()
        username = self.security.get_current_user()
        
        dialog = ChangePasswordDialog(username, self)
        if exec_embedded_dialog(self, dialog) == QtWidgets.QDialog.Accepted:
            old_pw, new_pw = dialog.get_passwords()
            success, message = self.security.change_password(user_id, old_pw, new_pw)
            
            if success:
                QtWidgets.QMessageBox.information(self, "Erfolg", f"{message}\n\nIhr neues Passwort wurde gespeichert.")
                self.show_toast("Passwort erfolgreich geändert.", "success")
            else:
                QtWidgets.QMessageBox.warning(self, "Fehler", message)

    def change_user_avatar(self) -> None:
        """Erlaubt dem Benutzer, ein Profilbild zu setzen."""
        if hasattr(self, "db") and self.db.is_read_only_mode():
            QtWidgets.QMessageBox.warning(self, "Nur-Lesen Modus", "Profilbild kann im Nur-Lesen Modus nicht geändert werden.")
            return
        user_id = self.security.get_current_user_id()
        if not user_id:
            return
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Profilbild auswählen",
            "",
            "Bilder (*.png *.jpg *.jpeg *.webp *.bmp)",
        )
        if not file_path:
            return
        success, message = self.security.set_user_avatar(user_id, file_path)
        if success:
            self._update_user_avatar_display()
            QtWidgets.QMessageBox.information(self, "Profilbild", message)
            self.show_toast("Profilbild aktualisiert.", "success")
        else:
            QtWidgets.QMessageBox.warning(self, "Profilbild", message)

    def remove_user_avatar(self) -> None:
        """Entfernt das Profilbild des aktuellen Benutzers."""
        if hasattr(self, "db") and self.db.is_read_only_mode():
            QtWidgets.QMessageBox.warning(self, "Nur-Lesen Modus", "Profilbild kann im Nur-Lesen Modus nicht entfernt werden.")
            return
        user_id = self.security.get_current_user_id()
        if not user_id:
            return
        success, message = self.security.clear_user_avatar(user_id)
        if success:
            self._update_user_avatar_display()
            QtWidgets.QMessageBox.information(self, "Profilbild", message)
            self.show_toast("Profilbild entfernt.", "success")
        else:
            QtWidgets.QMessageBox.warning(self, "Profilbild", message)
    
    def open_user_management(self) -> None:
        """Öffnet integrierte Benutzerverwaltung in den Grundeinstellungen."""

        if not self.security.is_admin():
            QtWidgets.QMessageBox.warning(
                self,
                "Keine Berechtigung",
                "Nur Administratoren können auf die Benutzerverwaltung zugreifen."
            )
            return

        self.switch_to_page(PageIndex.GRUNDEINSTELLUNGEN)
        if not getattr(self, "page_grundeinstellungen", None):
            return

        tabs = getattr(self.page_grundeinstellungen, "tabs", None)
        if not tabs:
            return

        for idx in range(tabs.count()):
            if tabs.tabText(idx) == "Benutzer":
                tabs.setCurrentIndex(idx)
                return
    
    def force_logout(self) -> None:
        """Meldet den Benutzer sofort ab und beendet die App (Zwang)"""
        username = self.security.get_current_user()
        if hasattr(self, "db"):
            self.db.release_write_lease()
        self.security.logout()
        logger.warning(f"Benutzer '{username}' zwangsabgemeldet (Zwingende Passwort-Richtlinie)")
        QtWidgets.QApplication.quit()

    def _execute_logout(self) -> None:
        username = self.security.get_current_user()
        if hasattr(self, "db"):
            self.db.release_write_lease()
        self.security.logout()
        logger.info(f"Benutzer '{username}' abgemeldet")
        QtWidgets.QApplication.quit()

    def _execute_user_switch(self) -> None:
        """Meldet aktuellen Benutzer ab und zeigt den Login-Screen."""
        username = self.security.get_current_user()
        if hasattr(self, "db"):
            self.db.release_write_lease()
        self.security.logout()
        logger.info(f"Benutzer '{username}' abgemeldet (Benutzerwechsel)")

        self._hide_confirmation_overlay()
        self._refresh_user_sidebar_state()
        self.switch_to_page(PageIndex.DASHBOARD)

        self._login_attempts = 0
        if hasattr(self, "login_user_input"):
            self.login_user_input.clear()
        if hasattr(self, "login_password_input"):
            self.login_password_input.clear()
        if hasattr(self, "login_error_label"):
            self.login_error_label.clear()

        if hasattr(self, "login_overlay"):
            self.login_overlay.setGeometry(self.rect())
            self.login_overlay.raise_()
            self.login_overlay.show()
        if hasattr(self, "login_user_input"):
            self.login_user_input.setFocus()

    def logout(self) -> None:
        """Zeigt Auswahl für Benutzerwechsel oder Programmende."""
        current_page = self.stack.currentWidget() if hasattr(self, "stack") else None
        if current_page is not None and not self._confirm_discard_unsaved_changes(current_page):
            return
        self._show_logout_choice_overlay()
    
    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """Cleanup beim Schließen"""
        if getattr(self, "_allow_close", False):
            if hasattr(self, 'verfallmanager'):
                self.verfallmanager.close()
            if hasattr(self, "db"):
                self.db.release_write_lease()
            if hasattr(self, 'security'):
                self.security.logout()
                self.security.close()
            event.accept()
            return

        current_page = self.stack.currentWidget() if hasattr(self, "stack") else None
        if current_page is not None and not self._confirm_discard_unsaved_changes(current_page):
            event.ignore()
            return

        event.ignore()
        self._show_confirmation_overlay(
            title="Beenden",
            message="Möchten Sie die Anwendung wirklich beenden?",
            confirm_text="Beenden",
            on_confirm=self._confirm_close,
            confirm_object_name="btn_delete",
        )

    def _confirm_close(self) -> None:
        self._hide_confirmation_overlay()
        self._allow_close = True
        self.close()

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        self._update_sidebar_width(event.size().width())
        self._update_feedback_layer_geometry()
        if hasattr(self, "login_overlay"):
            self.login_overlay.setGeometry(self.rect())
        if hasattr(self, "confirm_overlay") and self.confirm_overlay is not None:
            self.confirm_overlay.setGeometry(self.rect())

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        """ESC schließt nur den eingebetteten Bestätigungs-Overlay."""
        if event.key() == Qt.Key_Escape and hasattr(self, "confirm_overlay") and self.confirm_overlay:
            self._hide_confirmation_overlay()
            event.ignore()
            return
        super().keyPressEvent(event)
    

# =============================================================================
# Pages





# =============================================================================
# Import-Seite (verbessert mit Excel-Dropdowns)
# =============================================================================


# =============================================================================
# E-Mail-Seite
# =============================================================================


# =============================================================================

if __name__ == "__main__":
    # QApplication wird für GUI und Error Handler benötigt
    app = QtWidgets.QApplication(sys.argv)
    install_embedded_dialog_patches()
    app.setApplicationName("ND-Hub")
    app.setOrganizationName("ND-Hub Enterprise")
    
    # Globaler Error Handler initialisieren
    error_handler = setup_global_error_handler(app)
    
    # Logik für Datenbank-Pfad Erreichbarkeit
    db_path = config.get_db_path()
    db_dir = os.path.dirname(db_path)
    if not db_dir:
        db_dir = "."
        
    if not os.path.exists(db_dir):
        QtWidgets.QMessageBox.critical(None, "Fehler", 
            f"Der Speicherort der Datenbank ist nicht erreichbar!\n\nPfad: {db_path}\n\n"
            "Bitte stellen Sie sicher, dass:\n"
            "1. Das Laufwerk oder das Netzwerk verbunden ist\n"
            "2. Sie Zugriff auf den Ordner haben")
        sys.exit(1)
    
    # Theme anwenden
    app.setStyleSheet(AppleTheme.get_stylesheet())
    
    # MainWindow mit zentralem ConfigManager starten
    win = MainWindow(config)
    win.showFullScreen()
    
    sys.exit(app.exec())
