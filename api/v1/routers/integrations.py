"""Integration endpoints for Jira and Google Calendar."""

import base64
import hashlib
import json
from datetime import UTC, datetime, timedelta
from functools import lru_cache

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
    metadata: dict,
) -> int:
    expires_at = datetime.now(UTC) + timedelta(days=30)

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


@router.get("/jira/connect")
async def jira_connect_payload() -> dict:
    service = JiraService()
    return service.build_oauth_connect_payload()


@router.post("/jira/connect")
async def jira_connect(workspace_id: int = 1) -> dict:
    service = JiraService()
    payload = service.build_oauth_connect_payload()
    payload["workspace_id"] = workspace_id
    return payload


@router.get("/jira/callback")
async def jira_callback(
    code: str = "",
    state: str = "",
    workspace_id: int = 1,
) -> dict:
    if not code.strip():
        raise HTTPException(status_code=400, detail="missing authorization code")

    integration_id = _upsert_integration_account(
        workspace_id=workspace_id,
        provider="jira",
        account_label="Jira OAuth",
        access_token=f"jira_access_{code.strip()}",
        refresh_token=f"jira_refresh_{code.strip()}",
        metadata={"state": state, "mode": "dev_callback_capture"},
    )

    return {
        "provider": "jira",
        "status": "connected",
        "message": "Jira callback processed and integration account stored.",
        "workspace_id": workspace_id,
        "integration_id": integration_id,
        "state": state,
    }


@router.get("/google/connect")
async def google_connect_payload() -> dict:
    service = GoogleCalendarService()
    return service.build_oauth_connect_payload()


@router.post("/google/connect")
async def google_connect(workspace_id: int = 1) -> dict:
    service = GoogleCalendarService()
    payload = service.build_oauth_connect_payload()
    payload["workspace_id"] = workspace_id
    return payload


@router.get("/google/callback")
async def google_callback(
    code: str = "",
    state: str = "",
    workspace_id: int = 1,
) -> dict:
    if not code.strip():
        raise HTTPException(status_code=400, detail="missing authorization code")

    integration_id = _upsert_integration_account(
        workspace_id=workspace_id,
        provider="google_calendar",
        account_label="Google Calendar OAuth",
        access_token=f"google_access_{code.strip()}",
        refresh_token=f"google_refresh_{code.strip()}",
        metadata={"state": state, "mode": "dev_callback_capture"},
    )

    return {
        "provider": "google_calendar",
        "status": "connected",
        "message": "Google callback processed and integration account stored.",
        "workspace_id": workspace_id,
        "integration_id": integration_id,
        "state": state,
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
