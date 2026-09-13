from pathlib import Path

from security_manager import SecurityManager


def test_hash_and_verify_roundtrip():
    password = "UltraSafe!123"
    password_hash = SecurityManager.hash_password(password)
    assert SecurityManager.verify_password(password, password_hash) is True
    assert SecurityManager.verify_password("wrong-password", password_hash) is False


def test_default_admin_password_from_env(monkeypatch, tmp_path: Path):
    db_path = tmp_path / "security_test.db"
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")

    manager = SecurityManager(str(db_path), allow_own_connection=True)
    try:
        success, _ = manager.authenticate("admin", "InitPass!12345")
        assert success is True

        fail, _ = manager.authenticate("admin", "admin")
        assert fail is False
    finally:
        manager.close()
        monkeypatch.delenv("ND_HUB_INITIAL_ADMIN_PASSWORD", raising=False)
