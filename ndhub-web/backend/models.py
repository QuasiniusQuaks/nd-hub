"""Pydantic models + related constants for ND-Hub web backend (Issue #60)."""

from datetime import date
from typing import Any, Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)

class LoginResponse(BaseModel):
    token: str
    username: str
    role: Optional[str]
    requires_password_change: bool = False
    permissions: list[str] = Field(default_factory=list)

class DesktopSyncTokenResponse(BaseModel):
    backend_url: str
    token: str
    username: str
    role: Optional[str]
    expires_at: str
    client_label: Optional[str] = None

class DesktopSyncTokenCreateRequest(BaseModel):
    client_label: Optional[str] = Field(default=None, max_length=120)

class DesktopSyncTokenArchiveItem(BaseModel):
    token_fingerprint: str
    token_masked: str
    client_label: Optional[str]
    username: str
    role: Optional[str]
    created_at: str
    expires_at: str
    status: str

class DesktopSyncTokenRevokeRequest(BaseModel):
    token_fingerprint: str = Field(min_length=8)

class PasswordChangeRequest(BaseModel):
    old_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8)

class UserCreateRequest(BaseModel):
    username: str = Field(min_length=3)
    password: str = Field(min_length=8)
    role: str = Field(min_length=1)
    email: Optional[str] = None
    is_active: bool = True
    permissions: Optional[list[str]] = None

class UserUpdateRequest(BaseModel):
    username: Optional[str] = Field(default=None, min_length=3)
    role: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None
    permissions: Optional[list[str]] = None

class UserPasswordResetRequest(BaseModel):
    new_password: str = Field(min_length=8)

class BewegungCreateRequest(BaseModel):
    depot_id: int
    praeparat_id: int
    typ: str
    charge: str
    verfall: date
    datum: date
    anzahl: int = Field(gt=0)
    empfaenger: Optional[str] = None

class DepotUpsertRequest(BaseModel):
    name: str = Field(min_length=1)
    adresse: Optional[str] = None
    strasse: Optional[str] = None
    hausnummer: Optional[str] = None
    postleitzahl: Optional[str] = None
    stadt: Optional[str] = None
    telefon: Optional[str] = None
    email: Optional[str] = None
    institution_id: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class InstitutionUpsertRequest(BaseModel):
    name: str = Field(min_length=1)
    adresse: Optional[str] = None
    strasse: Optional[str] = None
    hausnummer: Optional[str] = None
    postleitzahl: Optional[str] = None
    stadt: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class OnboardingPraeparatItem(BaseModel):
    name: str = Field(min_length=1)
    wirkstoff: Optional[str] = None
    darreichungsform: Optional[str] = None
    staerke: Optional[str] = None
    einheit: Optional[str] = None
    pzn: Optional[str] = None
    hersteller: Optional[str] = None

class OnboardingDepotAssignmentItem(BaseModel):
    praeparat_name: str = Field(min_length=1)
    sollbestand: int = Field(ge=0, default=0)

class OnboardingDepotItem(BaseModel):
    name: str = Field(min_length=1)
    adresse: Optional[str] = None
    strasse: Optional[str] = None
    hausnummer: Optional[str] = None
    postleitzahl: Optional[str] = None
    stadt: Optional[str] = None
    telefon: Optional[str] = None
    email: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    assignments: list[OnboardingDepotAssignmentItem] = Field(default_factory=list)

class OnboardingInstitutionSetupRequest(BaseModel):
    institution: InstitutionUpsertRequest
    praeparate: list[OnboardingPraeparatItem] = Field(default_factory=list)
    depots: list[OnboardingDepotItem] = Field(default_factory=list)

class UserDepotPermissionItem(BaseModel):
    depot_id: int
    can_read: bool = False
    can_write: bool = False

class UserDepotPermissionUpdateRequest(BaseModel):
    username: str = Field(min_length=1)
    permissions: list[UserDepotPermissionItem] = Field(default_factory=list)

class PraeparatUpsertRequest(BaseModel):
    name: str = Field(min_length=1)
    wirkstoff: Optional[str] = None
    darreichungsform: Optional[str] = None
    staerke: Optional[str] = None
    einheit: Optional[str] = None
    pzn: Optional[str] = None
    hersteller: Optional[str] = None

class DepotAssignmentItem(BaseModel):
    praeparat_id: int
    sollbestand: int = Field(ge=0, default=0)

class DepotAssignmentsUpdateRequest(BaseModel):
    assignments: list[DepotAssignmentItem]

class KontaktUpsertRequest(BaseModel):
    name: str = Field(min_length=1)
    rolle: Optional[str] = None
    telefon: Optional[str] = None
    email: Optional[str] = None

class EmailRecipientPreviewRequest(BaseModel):
    depot_ids: list[int] = Field(default_factory=list)
    kontakt_ids: list[int] = Field(default_factory=list)

class EmailDraftCreateRequest(BaseModel):
    depot_ids: list[int] = Field(default_factory=list)
    kontakt_ids: list[int] = Field(default_factory=list)
    betreff: str = Field(min_length=1)
    nachricht: str = ""
    send_now: bool = False

class EmailDeliveryStatusUpdateRequest(BaseModel):
    versand_status: str = Field(min_length=1)
    versand_kanal: Optional[str] = None
    versand_fehler: Optional[str] = None

class SyncPullRequest(BaseModel):
    cursor: Optional[str] = None
    entities: list[str] = Field(default_factory=list)
    limit: int = Field(default=200, ge=1, le=1000)

class SyncPushChangeItem(BaseModel):
    entity: str = Field(min_length=1)
    operation: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)
    client_change_id: Optional[str] = None

class SyncPushRequest(BaseModel):
    batch_id: str = Field(min_length=1, max_length=128)
    changes: list[SyncPushChangeItem] = Field(default_factory=list)


MAX_ATTACHMENT_SIZE_BYTES = 10 * 1024 * 1024

PDF_MIME_TYPES = {"application/pdf", "application/x-pdf"}

ALLOWED_IMPORT_TYPES = {"Zugang", "Abgang", "Vernichtung"}

IMPORT_REQUIRED_COLUMNS = ["depot", "praeparat", "typ", "charge", "verfall", "datum", "anzahl"]

IMPORT_COLUMN_ALIASES = {
    "depot": {"depot"},
    "praeparat": {"praeparat", "präparat"},
    "typ": {"typ", "type"},
    "charge": {"charge"},
    "verfall": {"verfall", "verfallsdatum"},
    "datum": {"datum", "date"},
    "anzahl": {"anzahl", "menge", "quantity"},
    "empfaenger": {"empfaenger", "empfänger"},
}

ALLOWED_USER_ROLES = {"Admin", "User"}

PERMISSION_DEFINITIONS = [
    {"key": "masterdata_read", "label": "Stammdaten lesen"},
    {"key": "masterdata_write", "label": "Stammdaten bearbeiten"},
    {"key": "movements_read", "label": "Bewegungen lesen"},
    {"key": "movements_write", "label": "Bewegungen erfassen"},
    {"key": "settings_read", "label": "Grundeinstellungen lesen"},
    {"key": "settings_write", "label": "Grundeinstellungen bearbeiten"},
    {"key": "import_use", "label": "Import nutzen"},
    {"key": "email_use", "label": "E-Mail nutzen"},
    {"key": "reports_view", "label": "Auswertungen sehen"},
    {"key": "audit_view", "label": "Audit sehen"},
    {"key": "users_manage", "label": "Benutzer verwalten"},
    {"key": "backup_manage", "label": "Backup verwalten"},
]

ALL_PERMISSION_KEYS = {item["key"] for item in PERMISSION_DEFINITIONS}

DEFAULT_USER_PERMISSIONS = {
    "masterdata_read",
    "movements_read",
    "movements_write",
    "settings_read",
    "import_use",
    "email_use",
    "reports_view",
}

PERMISSION_TEMPLATES = [
    {"key": "readonly", "label": "ReadOnly", "permissions": ["masterdata_read", "movements_read", "settings_read", "reports_view"]},
    {"key": "disponent", "label": "Disponent", "permissions": ["masterdata_read", "movements_read", "movements_write", "settings_read", "import_use", "email_use", "reports_view"]},
    {"key": "reporting", "label": "Reporting", "permissions": ["masterdata_read", "movements_read", "reports_view"]},
    {"key": "ops_admin", "label": "Ops Admin", "permissions": ["masterdata_read", "masterdata_write", "movements_read", "movements_write", "settings_read", "settings_write", "import_use", "email_use", "reports_view", "audit_view", "backup_manage"]},
]


