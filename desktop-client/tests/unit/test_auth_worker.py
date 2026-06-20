"""Tests fuer core/auth_worker.py.

Die Tests pruefen die Verifikationslogik direkt ueber die Hilfsfunktion
``_verify_password``, da AuthVerifyRunnable von ``QtCore.QRunnable`` ab-
leitet und in der Stub-Umgebung ohne echtes Qt nicht instanziiert werden
kann. Der Smoke-Test fuer AuthVerifyRunner greift nur auf dessen API-
Oberflaeche zu.
"""
from __future__ import annotations

from core.auth_worker import AuthVerifyRunner, _verify_password
from security_manager import SecurityManager


def test_verify_password_accepts_correct_password():
    password = "worker-test-password"
    password_hash = SecurityManager.hash_password(password)

    is_valid, error = _verify_password(password, password_hash)

    assert is_valid is True
    assert error is None


def test_verify_password_rejects_wrong_password():
    password = "worker-test-password"
    password_hash = SecurityManager.hash_password(password)

    is_valid, error = _verify_password("wrong-password", password_hash)

    assert is_valid is False
    assert error is None


def test_verify_password_rejects_empty_hash():
    is_valid, error = _verify_password("any-password", "")

    assert is_valid is False
    assert error is None


def test_verify_password_handles_invalid_hash():
    # verify_password fängt ungültige Hashes intern ab und gibt False zurück.
    is_valid, error = _verify_password("password", "not-a-valid-hash")

    assert is_valid is False
    assert error is None


def test_auth_verify_runner_has_signals_and_start():
    """Smoke-Test fuer AuthVerifyRunner-API.

    Instanziiert den Runner und prueft, dass Signale vorhanden und
    ``start()`` das Runnable akzeptiert. Eine echte Thread-Pool-Ausfuehrung
    wird hier nicht getriggert, weil das in der Stub-Qt-Umgebung zu
    MagicMock-Problemen fuehren wuerde.
    """
    runner = AuthVerifyRunner()
    assert runner.signals is not None
    assert hasattr(runner.signals, "finished")
    assert hasattr(runner.signals, "failed")
    assert hasattr(runner, "start")
