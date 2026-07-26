"""Pydantic models + constants for ND-Hub desktop backend (Issue #61)."""

from datetime import date

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)

class LoginResponse(BaseModel):
    token: str
    username: str
    role: str | None
    requires_password_change: bool = False
    permissions: list[str] = Field(default_factory=list)

class PasswordChangeRequest(BaseModel):
    old_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8)

class UserCreateRequest(BaseModel):
    username: str = Field(min_length=3)
    password: str = Field(min_length=8)
    role: str = Field(min_length=1)
    email: str | None = None
    is_active: bool = True
    permissions: list[str] | None = None

class UserUpdateRequest(BaseModel):
    username: str | None = Field(default=None, min_length=3)
    role: str | None = None
    email: str | None = None
    is_active: bool | None = None
    permissions: list[str] | None = None

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
    empfaenger: str | None = None

class DepotUpsertRequest(BaseModel):
    name: str = Field(min_length=1)
    adresse: str | None = None
    telefon: str | None = None
    email: str | None = None

class PraeparatUpsertRequest(BaseModel):
    name: str = Field(min_length=1)

class DepotAssignmentItem(BaseModel):
    praeparat_id: int
    sollbestand: int = Field(ge=0, default=0)

class DepotAssignmentsUpdateRequest(BaseModel):
    assignments: list[DepotAssignmentItem]

class KontaktUpsertRequest(BaseModel):
    name: str = Field(min_length=1)
    rolle: str | None = None
    telefon: str | None = None
    email: str | None = None

class EmailRecipientPreviewRequest(BaseModel):
    depot_ids: list[int] = Field(default_factory=list)

class EmailDraftCreateRequest(BaseModel):
    depot_ids: list[int] = Field(default_factory=list)
    betreff: str = Field(min_length=1)
    nachricht: str = ""


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


