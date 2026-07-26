"""Abstract repository interface for web backend DB layer (Issue #70)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class AbstractRepository(ABC):
    """Common contract implemented by SqliteRepository and MariaDbRepository."""

    @abstractmethod
    def list_depots(self, q: str = '', limit: int = 100, offset: int = 0, allowed_ids: list[int] | None = None) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def list_praeparate(self, q: str = '', limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def list_praeparate_for_depot(self, depot_id: int) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def list_depot_assignments(self, depot_id: int) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def set_depot_assignments(self, depot_id: int, assignments: list[dict[str, Any]]) -> None:
        ...

    @abstractmethod
    def create_depot(self, name: str, adresse: str | None = None, strasse: str | None = None, hausnummer: str | None = None, postleitzahl: str | None = None, stadt: str | None = None, telefon: str | None = None, email: str | None = None, institution_id: int | None = None, latitude: float | None = None, longitude: float | None = None) -> int:
        ...

    @abstractmethod
    def get_depot_name(self, depot_id: int) -> str | None:
        ...

    @abstractmethod
    def get_depot(self, depot_id: int) -> dict[str, Any] | None:
        ...

    @abstractmethod
    def update_depot(self, depot_id: int, name: str, adresse: str | None = None, strasse: str | None = None, hausnummer: str | None = None, postleitzahl: str | None = None, stadt: str | None = None, telefon: str | None = None, email: str | None = None, institution_id: int | None = None, latitude: float | None = None, longitude: float | None = None) -> bool:
        ...

    @abstractmethod
    def list_institutions(self) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def get_onboarding_status(self) -> dict[str, Any]:
        ...

    @abstractmethod
    def create_institution(self, name: str, adresse: str | None = None, strasse: str | None = None, hausnummer: str | None = None, postleitzahl: str | None = None, stadt: str | None = None, latitude: float | None = None, longitude: float | None = None) -> int:
        ...

    @abstractmethod
    def create_onboarding_setup(self, institution: dict[str, Any], praeparate: list[dict[str, Any]], depots: list[dict[str, Any]]) -> dict[str, Any]:
        ...

    @abstractmethod
    def update_institution(self, institution_id: int, name: str, adresse: str | None = None, strasse: str | None = None, hausnummer: str | None = None, postleitzahl: str | None = None, stadt: str | None = None, latitude: float | None = None, longitude: float | None = None) -> bool:
        ...

    @abstractmethod
    def delete_institution(self, institution_id: int) -> bool:
        ...

    @abstractmethod
    def set_user_depot_permission(self, username: str, depot_id: int, can_read: bool, can_write: bool) -> None:
        ...

    @abstractmethod
    def list_user_depot_permissions(self, username: str) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def list_map_institutions_with_depots(self) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def delete_depot(self, depot_id: int) -> bool:
        ...

    @abstractmethod
    def create_praeparat(self, name: str, wirkstoff: str | None = None, darreichungsform: str | None = None, staerke: str | None = None, einheit: str | None = None, pzn: str | None = None, hersteller: str | None = None) -> int:
        ...

    @abstractmethod
    def update_praeparat(self, praeparat_id: int, name: str, wirkstoff: str | None = None, darreichungsform: str | None = None, staerke: str | None = None, einheit: str | None = None, pzn: str | None = None, hersteller: str | None = None) -> bool:
        ...

    @abstractmethod
    def delete_praeparat(self, praeparat_id: int) -> bool:
        ...

    @abstractmethod
    def get_praeparat(self, praeparat_id: int) -> dict[str, Any] | None:
        ...

    @abstractmethod
    def list_kontakte(self, depot_id: int) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def create_kontakt(self, depot_id: int, name: str, rolle: str | None = None, telefon: str | None = None, email: str | None = None) -> int:
        ...

    @abstractmethod
    def update_kontakt(self, kontakt_id: int, name: str, rolle: str | None = None, telefon: str | None = None, email: str | None = None) -> bool:
        ...

    @abstractmethod
    def delete_kontakt(self, kontakt_id: int) -> bool:
        ...

    @abstractmethod
    def get_kontakt(self, kontakt_id: int) -> dict[str, Any] | None:
        ...

    @abstractmethod
    def get_kontakte_by_depot_ids(self, depot_ids: list[int]) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def add_email_verlauf(self, betreff: str, nachricht: str, depot_names: str, emails: str, anzahl: int, versand_status: str = 'draft', versand_kanal: str | None = None, versand_fehler: str | None = None) -> int:
        ...

    @abstractmethod
    def get_email_verlauf(self, limit: int = 50) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def get_email_details(self, email_id: int) -> dict[str, Any] | None:
        ...

    @abstractmethod
    def update_email_delivery_status(self, email_id: int, versand_status: str, versand_kanal: str | None = None, versand_fehler: str | None = None) -> bool:
        ...

    @abstractmethod
    def list_bewegungen(self, limit: int = 100, offset: int = 0, q: str = '', typ: str | None = None, depot_id: int | None = None, depot_ids: list[int] | None = None, praeparat_id: int | None = None, has_attachment: bool | None = None, start_date: str | None = None, end_date: str | None = None) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def get_bewegung(self, bewegung_id: int) -> dict[str, Any] | None:
        ...

    @abstractmethod
    def set_bewegung_attachment(self, bewegung_id: int, datei_pfad: str, datei_name: str, datei_groesse: int, uploaded_at: str) -> bool:
        ...

    @abstractmethod
    def insert_bewegung(self, depot_id: int, praeparat_id: int, typ: str, charge: str, verfall: str, datum: str, anzahl: int, empfaenger: str | None = None) -> int:
        ...

    @abstractmethod
    def get_bewegungen_analyse(self, depot_ids: list[int] | None = None, praeparat_ids: list[int] | None = None, start_date: str | None = None, end_date: str | None = None) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def get_bestandsentwicklung(self, depot_ids: list[int] | None = None, praeparat_ids: list[int] | None = None) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def get_praeparat_ranking(self, depot_ids: list[int] | None = None, start_date: str | None = None, end_date: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def get_depot_ranking(self, praeparat_ids: list[int] | None = None, start_date: str | None = None, end_date: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def get_matrix_data(self) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def get_verfall_prognose(self, depot_ids: list[int] | None = None, praeparat_ids: list[int] | None = None, horizon_months: int = 24) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def get_dashboard_overview(self, limit_activity: int = 8, limit_expiry: int = 8, critical_days: int = 30) -> dict[str, Any]:
        ...

    @abstractmethod
    def list_verfall_items(self, depot_ids: list[int] | None = None, praeparat_ids: list[int] | None = None, search_text: str | None = None, category: str | None = None, limit: int = 100, offset: int = 0, critical_days: int = 30, warning_days: int = 90, attention_days: int = 180) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def count_verfall_items(self, depot_ids: list[int] | None = None, praeparat_ids: list[int] | None = None, search_text: str | None = None, category: str | None = None, critical_days: int = 30, warning_days: int = 90, attention_days: int = 180) -> int:
        ...

    @abstractmethod
    def list_new_critical_expiry_events(self, since_iso: str | None = None, limit: int = 25, critical_days: int = 30) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def log_audit(self, username: str, action: str, resource_type: str, resource_id: int | None = None, details: dict[str, Any] | None = None) -> int | None:
        ...

    @abstractmethod
    def list_audit_logs(self, limit: int = 100, offset: int = 0, q: str = '', action: str = '', resource_type: str = '') -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def get_sync_batch_result(self, batch_id: str) -> dict[str, Any] | None:
        ...

    @abstractmethod
    def save_sync_batch_result(self, batch_id: str, username: str, result: dict[str, Any]) -> None:
        ...

    @abstractmethod
    def get_import_batch_result(self, batch_id: str) -> dict[str, Any] | None:
        ...

    @abstractmethod
    def save_import_batch_result(self, batch_id: str, username: str, result: dict[str, Any]) -> None:
        ...

    @abstractmethod
    def list_sync_audit_changes(self, cursor: int = 0, entities: list[str] | None = None, limit: int = 200) -> dict[str, Any]:
        ...

    @abstractmethod
    def get_latest_audit_cursor(self) -> int:
        ...

    @abstractmethod
    def get_sync_ops_stats(self) -> dict[str, Any]:
        ...

