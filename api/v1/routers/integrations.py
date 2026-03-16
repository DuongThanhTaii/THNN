"""Integration endpoints for Jira and Google Calendar."""

import base64
import hashlib
import hmac
import json
import secrets
import time
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Any

from cryptography.fernet import Fernet
from fastapi import APIRouter, HTTPException

from config.settings import get_settings
from integrations.google_calendar import GoogleCalendarService
from integrations.jira import JiraService
from storage.db import get_db_cursor

router = APIRouter(prefix="/integrations", tags=["integrations"])


@lru_cache
def _build_fernet() -> Fernet:
    settings = get_settings()
    master_key = settings.encryption_master_key.strip()
    if not master_key:
        raise HTTPException(
            status_code=500,
            detail="ENCRYPTION_MASTER_KEY is required for integration token encryption",
        )

    # Fernet requires a 32-byte url-safe base64 key.
    derived = hashlib.sha256(master_key.encode("utf-8")).digest()
    fernet_key = base64.urlsafe_b64encode(derived)
    return Fernet(fernet_key)


def _encrypt_token(value: str) -> str:
    return _build_fernet().encrypt(value.encode("utf-8")).decode("ascii")


def _upsert_integration_account(
    *,
    workspace_id: int,
    provider: str,
    account_label: str,
    access_token: str,
    refresh_token: str | None,
    metadata: dict[str, Any],
    token_expires_at: datetime | None = None,
) -> int:
    expires_at = token_expires_at or (datetime.now(UTC) + timedelta(days=30))

    with get_db_cursor() as cur:
        cur.execute(
            """
            SELECT id
            FROM integration_accounts
            WHERE workspace_id = %s AND provider = %s
            ORDER BY id DESC
            LIMIT 1
            """,
            (workspace_id, provider),
        )
        existing = cur.fetchone()

        if existing is None:
            cur.execute(
                """
                INSERT INTO integration_accounts(
                    workspace_id,
                    provider,
                    account_label,
                    encrypted_access_token,
                    encrypted_refresh_token,
                    token_expires_at,
                    metadata
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
                RETURNING id
                """,
                (
                    workspace_id,
                    provider,
                    account_label,
                    _encrypt_token(access_token),
                    _encrypt_token(refresh_token) if refresh_token else None,
                    expires_at,
                    json.dumps(metadata),
                ),
            )
            return int(cur.fetchone()[0])

        integration_id = int(existing[0])
        cur.execute(
            """
            UPDATE integration_accounts
            SET
                account_label = %s,
                encrypted_access_token = %s,
                encrypted_refresh_token = %s,
                token_expires_at = %s,
                metadata = %s::jsonb,
                updated_at = NOW()
            WHERE id = %s
            """,
            (
                account_label,
                _encrypt_token(access_token),
                _encrypt_token(refresh_token) if refresh_token else None,
                expires_at,
                json.dumps(metadata),
                integration_id,
            ),
        )
        return integration_id


def _oauth_state_secret() -> bytes:
    settings = get_settings()
    secret = settings.jwt_secret.strip() or settings.encryption_master_key.strip()
    if not secret:
        raise HTTPException(
            status_code=500,
            detail="JWT_SECRET or ENCRYPTION_MASTER_KEY is required for OAuth state signing",
        )
    return secret.encode("utf-8")


def _encode_state_payload(payload: dict[str, Any]) -> str:
    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode(
        "utf-8"
    )
    signature = hmac.new(_oauth_state_secret(), payload_bytes, hashlib.sha256).digest()
    payload_token = base64.urlsafe_b64encode(payload_bytes).decode("ascii").rstrip("=")
    signature_token = base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")
    return f"{payload_token}.{signature_token}"


def _decode_state_payload(state: str) -> dict[str, Any]:
    try:
        payload_token, signature_token = state.split(".", 1)
        payload_padded = payload_token + "=" * ((4 - (len(payload_token) % 4)) % 4)
        signature_padded = signature_token + "=" * (
            (4 - (len(signature_token) % 4)) % 4
        )
        payload_bytes = base64.urlsafe_b64decode(payload_padded.encode("ascii"))
        signature = base64.urlsafe_b64decode(signature_padded.encode("ascii"))
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"invalid oauth state format: {e}",
        ) from e

    expected = hmac.new(_oauth_state_secret(), payload_bytes, hashlib.sha256).digest()
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=400, detail="invalid oauth state signature")

    try:
        data = json.loads(payload_bytes.decode("utf-8"))
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"invalid oauth state payload: {e}",
        ) from e
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="invalid oauth state payload type")
    return data


def _build_oauth_state(provider: str, workspace_id: int, ttl_seconds: int = 600) -> str:
    now = int(time.time())
    payload = {
        "provider": provider,
        "workspace_id": workspace_id,
        "nonce": secrets.token_urlsafe(12),
        "iat": now,
        "exp": now + ttl_seconds,
    }
    return _encode_state_payload(payload)


def _validate_oauth_state(state: str, provider: str) -> dict[str, Any]:
    payload = _decode_state_payload(state)
    if str(payload.get("provider") or "") != provider:
        raise HTTPException(status_code=400, detail="invalid oauth state provider")

    exp = payload.get("exp")
    if not isinstance(exp, int):
        raise HTTPException(status_code=400, detail="invalid oauth state expiration")
    if int(time.time()) > exp:
        raise HTTPException(status_code=400, detail="oauth state has expired")

    workspace_id = payload.get("workspace_id")
    if not isinstance(workspace_id, int):
        raise HTTPException(status_code=400, detail="invalid oauth state workspace")
    return payload


@router.get("/jira/connect")
async def jira_connect_payload(workspace_id: int = 1) -> dict:
    service = JiraService()
    state = _build_oauth_state("jira", workspace_id)
    payload = service.build_oauth_connect_payload(state)
    payload["workspace_id"] = workspace_id
    return payload


@router.post("/jira/connect")
async def jira_connect(workspace_id: int = 1) -> dict:
    service = JiraService()
    state = _build_oauth_state("jira", workspace_id)
    payload = service.build_oauth_connect_payload(state)
    payload["workspace_id"] = workspace_id
    return payload


@router.get("/jira/callback")
async def jira_callback(
    code: str = "",
    state: str = "",
    workspace_id: int | None = None,
) -> dict:
    if not code.strip():
        raise HTTPException(status_code=400, detail="missing authorization code")
    if not state.strip():
        raise HTTPException(status_code=400, detail="missing oauth state")

    state_payload = _validate_oauth_state(state.strip(), "jira")
    state_workspace_id = int(state_payload["workspace_id"])
    if workspace_id is not None and workspace_id != state_workspace_id:
        raise HTTPException(
            status_code=400, detail="workspace_id does not match oauth state"
        )

    service = JiraService()
    token_data = await service.exchange_code_for_tokens(code.strip())

    expires_in_raw = token_data.get("expires_in")
    token_expires_at: datetime | None = None
    if isinstance(expires_in_raw, int) and expires_in_raw > 0:
        token_expires_at = datetime.now(UTC) + timedelta(seconds=expires_in_raw)

    integration_id = _upsert_integration_account(
        workspace_id=state_workspace_id,
        provider="jira",
        account_label="Jira OAuth",
        access_token=str(token_data["access_token"]),
        refresh_token=(
            str(token_data["refresh_token"])
            if token_data.get("refresh_token") is not None
            else None
        ),
        metadata={
            "scope": str(token_data.get("scope") or ""),
            "token_type": str(token_data.get("token_type") or ""),
            "expires_in": token_data.get("expires_in"),
            "state_nonce": state_payload.get("nonce"),
            "mode": "oauth_code_exchange",
        },
        token_expires_at=token_expires_at,
    )

    return {
        "provider": "jira",
        "status": "connected",
        "message": "Jira callback processed and integration account stored.",
        "workspace_id": state_workspace_id,
        "integration_id": integration_id,
        "state": state_payload,
    }


@router.get("/google/connect")
async def google_connect_payload(workspace_id: int = 1) -> dict:
    service = GoogleCalendarService()
    state = _build_oauth_state("google_calendar", workspace_id)
    payload = service.build_oauth_connect_payload(state)
    payload["workspace_id"] = workspace_id
    return payload


@router.post("/google/connect")
async def google_connect(workspace_id: int = 1) -> dict:
    service = GoogleCalendarService()
    state = _build_oauth_state("google_calendar", workspace_id)
    payload = service.build_oauth_connect_payload(state)
    payload["workspace_id"] = workspace_id
    return payload


@router.get("/google/callback")
async def google_callback(
    code: str = "",
    state: str = "",
    workspace_id: int | None = None,
) -> dict:
    if not code.strip():
        raise HTTPException(status_code=400, detail="missing authorization code")
    if not state.strip():
        raise HTTPException(status_code=400, detail="missing oauth state")

    state_payload = _validate_oauth_state(state.strip(), "google_calendar")
    state_workspace_id = int(state_payload["workspace_id"])
    if workspace_id is not None and workspace_id != state_workspace_id:
        raise HTTPException(
            status_code=400, detail="workspace_id does not match oauth state"
        )

    service = GoogleCalendarService()
    token_data = await service.exchange_code_for_tokens(code.strip())

    expires_in_raw = token_data.get("expires_in")
    token_expires_at: datetime | None = None
    if isinstance(expires_in_raw, int) and expires_in_raw > 0:
        token_expires_at = datetime.now(UTC) + timedelta(seconds=expires_in_raw)

    integration_id = _upsert_integration_account(
        workspace_id=state_workspace_id,
        provider="google_calendar",
        account_label="Google Calendar OAuth",
        access_token=str(token_data["access_token"]),
        refresh_token=(
            str(token_data["refresh_token"])
            if token_data.get("refresh_token") is not None
            else None
        ),
        metadata={
            "scope": str(token_data.get("scope") or ""),
            "token_type": str(token_data.get("token_type") or ""),
            "expires_in": token_data.get("expires_in"),
            "state_nonce": state_payload.get("nonce"),
            "mode": "oauth_code_exchange",
        },
        token_expires_at=token_expires_at,
    )

    return {
        "provider": "google_calendar",
        "status": "connected",
        "message": "Google callback processed and integration account stored.",
        "workspace_id": state_workspace_id,
        "integration_id": integration_id,
        "state": state_payload,
    }


@router.get("/accounts")
async def list_integration_accounts(workspace_id: int = 1) -> dict:
    with get_db_cursor() as cur:
        cur.execute(
            """
            SELECT id, provider, account_label, token_expires_at, created_at, updated_at
            FROM integration_accounts
            WHERE workspace_id = %s
            ORDER BY updated_at DESC, id DESC
            """,
            (workspace_id,),
        )
        rows = cur.fetchall()

    accounts = [
        {
            "id": int(row[0]),
            "provider": str(row[1]),
            "account_label": str(row[2]) if row[2] is not None else "",
            "token_expires_at": row[3].isoformat() if row[3] is not None else None,
            "created_at": row[4].isoformat() if row[4] is not None else None,
            "updated_at": row[5].isoformat() if row[5] is not None else None,
        }
        for row in rows
    ]

    return {
        "workspace_id": workspace_id,
        "count": len(accounts),
        "items": accounts,
    }
