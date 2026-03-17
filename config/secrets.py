"""Centralized secret access and encryption key management."""

from __future__ import annotations

import base64
import hashlib
import os
from pathlib import Path

from cryptography.fernet import Fernet, MultiFernet
from fastapi import HTTPException


def get_secret(name: str, *, required: bool = False) -> str:
    """Resolve secret from ENV or optional *_FILE indirection."""
    value = os.environ.get(name, "")
    if value:
        return value.strip()

    file_var = f"{name}_FILE"
    file_path = os.environ.get(file_var, "").strip()
    if file_path:
        try:
            return Path(file_path).read_text(encoding="utf-8").strip()
        except Exception as exc:
            if required:
                raise HTTPException(
                    status_code=500,
                    detail=f"failed to read required secret file {file_var}: {exc}",
                ) from exc
            return ""

    if required:
        raise HTTPException(status_code=500, detail=f"missing required secret: {name}")
    return ""


def _derive_fernet_key(raw: str) -> bytes:
    """Derive Fernet-compatible key bytes from arbitrary input string."""
    digest = hashlib.sha256(raw.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def get_encryption_key_ring() -> list[str]:
    """Return primary+fallback encryption keys for rotation-safe decrypt/encrypt."""
    primary = get_secret("ENCRYPTION_MASTER_KEY")
    fallbacks = [
        item.strip()
        for item in get_secret("ENCRYPTION_FALLBACK_KEYS").split(",")
        if item.strip()
    ]

    ring: list[str] = []
    if primary:
        ring.append(primary)
    for key in fallbacks:
        if key not in ring:
            ring.append(key)
    return ring


def get_encryption_key_ring_from_values(
    *,
    master_key: str,
    fallback_keys: str,
) -> list[str]:
    ring: list[str] = []
    if master_key.strip():
        ring.append(master_key.strip())

    for item in fallback_keys.split(","):
        key = item.strip()
        if key and key not in ring:
            ring.append(key)
    return ring


def build_fernet_bundle() -> MultiFernet:
    """Create MultiFernet where first key encrypts and all keys can decrypt."""
    key_ring = get_encryption_key_ring()
    if not key_ring:
        raise HTTPException(
            status_code=500,
            detail=(
                "ENCRYPTION_MASTER_KEY is required for integration token encryption"
            ),
        )

    fernets = [Fernet(_derive_fernet_key(key)) for key in key_ring]
    return MultiFernet(fernets)


def build_fernet_bundle_from_values(
    *,
    master_key: str,
    fallback_keys: str,
) -> MultiFernet:
    key_ring = get_encryption_key_ring_from_values(
        master_key=master_key,
        fallback_keys=fallback_keys,
    )
    if not key_ring:
        raise HTTPException(
            status_code=500,
            detail=(
                "ENCRYPTION_MASTER_KEY is required for integration token encryption"
            ),
        )

    fernets = [Fernet(_derive_fernet_key(key)) for key in key_ring]
    return MultiFernet(fernets)


def get_oauth_state_secret() -> bytes:
    """Return signing secret for OAuth state HMAC with rotation fallback."""
    jwt_secret = get_secret("JWT_SECRET")
    if jwt_secret:
        return jwt_secret.encode("utf-8")

    key_ring = get_encryption_key_ring()
    if key_ring:
        return key_ring[0].encode("utf-8")

    raise HTTPException(
        status_code=500,
        detail="JWT_SECRET or ENCRYPTION_MASTER_KEY is required for OAuth state signing",
    )


def get_oauth_state_secret_from_values(
    *,
    jwt_secret: str,
    master_key: str,
    fallback_keys: str,
) -> bytes:
    if jwt_secret.strip():
        return jwt_secret.strip().encode("utf-8")

    key_ring = get_encryption_key_ring_from_values(
        master_key=master_key,
        fallback_keys=fallback_keys,
    )
    if key_ring:
        return key_ring[0].encode("utf-8")

    raise HTTPException(
        status_code=500,
        detail="JWT_SECRET or ENCRYPTION_MASTER_KEY is required for OAuth state signing",
    )
