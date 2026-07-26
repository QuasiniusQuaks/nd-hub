"""Unit tests for shared.security + shared.backend_helpers (Issue #94)."""

from __future__ import annotations

from datetime import date

from security_manager import SecurityManager

from shared.backend_helpers.common import (
    add_months,
    enrich_verfall_rows,
    normalize_import_column_name,
    normalize_verfall_thresholds,
    parse_id_list_csv,
    parse_permission_list,
    permissions_for_role,
    sanitize_filename_part,
    verfall_category,
)
from shared.security.password import hash_password, verify_password


def test_password_roundtrip():
    hashed = hash_password("SharedPass!12345")
    assert verify_password("SharedPass!12345", hashed)
    assert not verify_password("wrong", hashed)
    assert not verify_password("SharedPass!12345", "")


def test_security_manager_delegates_to_shared():
    hashed = SecurityManager.hash_password("Delegate!12345")
    assert SecurityManager.verify_password("Delegate!12345", hashed)
    assert not SecurityManager.verify_password("nope", hashed)


def test_sanitize_and_ids():
    assert sanitize_filename_part("a/b c") == "a_b_c"
    assert parse_id_list_csv("1, 2,3") == [1, 2, 3]
    assert parse_id_list_csv("") == []


def test_add_months_and_import_name():
    assert add_months(date(2024, 1, 15), 1) == date(2024, 2, 1)
    assert normalize_import_column_name("Depot-Name") == "depotname"


def test_verfall_shared():
    c, w, a = normalize_verfall_thresholds(30, 90, 180)
    assert (c, w, a) == (30, 90, 180)
    assert verfall_category(10, 30, 90, 180) == "kritisch"
    rows = enrich_verfall_rows([{"tage_bis_verfall": 10}], 30, 90, 180)
    assert rows[0]["kategorie"] == "kritisch"


def test_permissions_shared():
    allowed = {"a", "b", "c"}
    defaults = {"a"}
    assert parse_permission_list('["a","x"]', allowed) == {"a"}
    assert permissions_for_role("Admin", None, allowed_keys=allowed, default_permissions=defaults) == allowed
    assert permissions_for_role("User", None, allowed_keys=allowed, default_permissions=defaults) == defaults
