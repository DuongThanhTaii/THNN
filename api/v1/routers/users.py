"""User management endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from storage.db import get_db_cursor

router = APIRouter(prefix="/users", tags=["users"])


class UserResponse(BaseModel):
    id: int
    external_id: str | None
    email: str | None
    display_name: str | None


class UserCreateRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    display_name: str = Field(min_length=1, max_length=200)
    external_id: str | None = Field(default=None, max_length=255)


class UserUpdateRequest(BaseModel):
    email: str | None = Field(default=None, min_length=3, max_length=255)
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    external_id: str | None = Field(default=None, max_length=255)


def _user_from_row(row) -> UserResponse:
    return UserResponse(
        id=int(row[0]),
        external_id=str(row[1]) if row[1] is not None else None,
        email=str(row[2]) if row[2] is not None else None,
        display_name=str(row[3]) if row[3] is not None else None,
    )


@router.get("", response_model=list[UserResponse])
async def list_users(
    limit: int = 100,
    offset: int = 0,
    q: str | None = None,
) -> list[UserResponse]:
    limit = max(1, min(limit, 200))
    offset = max(0, offset)

    where_parts: list[str] = []
    params: list[object] = []

    if q and q.strip():
        where_parts.append(
            "(COALESCE(display_name, '') ILIKE %s OR COALESCE(email, '') ILIKE %s)"
        )
        query = f"%{q.strip()}%"
        params.extend([query, query])

    where_sql = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

    with get_db_cursor() as cur:
        cur.execute(
            f"""
            SELECT id, external_id, email, display_name
            FROM users
            {where_sql}
            ORDER BY id DESC
            LIMIT %s OFFSET %s
            """,
            [*params, limit, offset],
        )
        rows = cur.fetchall()

    return [_user_from_row(row) for row in rows]


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int) -> UserResponse:
    with get_db_cursor() as cur:
        cur.execute(
            """
            SELECT id, external_id, email, display_name
            FROM users
            WHERE id = %s
            """,
            (user_id,),
        )
        row = cur.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="user not found")
    return _user_from_row(row)


@router.post("", response_model=UserResponse)
async def create_user(body: UserCreateRequest) -> UserResponse:
    with get_db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO users(external_id, email, display_name)
            VALUES (%s, %s, %s)
            ON CONFLICT (email)
            DO UPDATE SET
                external_id = COALESCE(EXCLUDED.external_id, users.external_id),
                display_name = EXCLUDED.display_name,
                updated_at = NOW()
            RETURNING id, external_id, email, display_name
            """,
            (
                body.external_id.strip() if body.external_id else None,
                body.email.strip().lower(),
                body.display_name.strip(),
            ),
        )
        row = cur.fetchone()

    if row is None:
        raise HTTPException(status_code=500, detail="failed to create user")
    return _user_from_row(row)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, body: UserUpdateRequest) -> UserResponse:
    updates: list[str] = []
    values: list[object] = []

    if body.email is not None:
        updates.append("email = %s")
        values.append(body.email.strip().lower())
    if body.display_name is not None:
        updates.append("display_name = %s")
        values.append(body.display_name.strip())
    if body.external_id is not None:
        updates.append("external_id = %s")
        values.append(body.external_id.strip())

    if not updates:
        raise HTTPException(status_code=400, detail="no fields to update")

    updates.append("updated_at = NOW()")
    set_sql = ", ".join(updates)

    with get_db_cursor() as cur:
        cur.execute(
            f"""
            UPDATE users
            SET {set_sql}
            WHERE id = %s
            RETURNING id, external_id, email, display_name
            """,
            [*values, user_id],
        )
        row = cur.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="user not found")
    return _user_from_row(row)
