import pytest
from cryptography.fernet import Fernet
from fastapi import HTTPException

from config import secrets


def test_get_secret_prefers_direct_env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "abc")
    monkeypatch.setenv("JWT_SECRET_FILE", "")

    assert secrets.get_secret("JWT_SECRET") == "abc"


def test_get_secret_reads_file_when_env_empty(monkeypatch, tmp_path):
    secret_file = tmp_path / "jwt_secret.txt"
    secret_file.write_text("file-value\n", encoding="utf-8")
    monkeypatch.setenv("JWT_SECRET", "")
    monkeypatch.setenv("JWT_SECRET_FILE", str(secret_file))

    assert secrets.get_secret("JWT_SECRET") == "file-value"


def test_get_encryption_key_ring_deduplicates(monkeypatch):
    monkeypatch.setenv("ENCRYPTION_MASTER_KEY", "k1")
    monkeypatch.setenv("ENCRYPTION_FALLBACK_KEYS", "k1,k2,k3,k2")

    assert secrets.get_encryption_key_ring() == ["k1", "k2", "k3"]


def test_build_fernet_bundle_requires_primary_or_fallback(monkeypatch):
    monkeypatch.setenv("ENCRYPTION_MASTER_KEY", "")
    monkeypatch.setenv("ENCRYPTION_FALLBACK_KEYS", "")

    with pytest.raises(HTTPException):
        secrets.build_fernet_bundle()


def test_get_oauth_state_secret_prefers_jwt(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "jwt")
    monkeypatch.setenv("ENCRYPTION_MASTER_KEY", "enc")

    assert secrets.get_oauth_state_secret() == b"jwt"


def test_get_oauth_state_secret_falls_back_to_encryption(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "")
    monkeypatch.setenv("ENCRYPTION_MASTER_KEY", "enc-primary")

    assert secrets.get_oauth_state_secret() == b"enc-primary"


def test_build_fernet_bundle_from_values_supports_key_rotation_decrypt():
    old_key = "old-secret-key"
    new_key = "new-secret-key"

    old_fernet = Fernet(secrets._derive_fernet_key(old_key))
    ciphertext = old_fernet.encrypt(b"token-123")

    bundle = secrets.build_fernet_bundle_from_values(
        master_key=new_key,
        fallback_keys=old_key,
    )

    assert bundle.decrypt(ciphertext) == b"token-123"
