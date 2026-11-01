"""Shared app helpers for the change-password and forced-change tests."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from uuid import UUID

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncEngine

from rag_backend.domain.models import User, UserRole
from rag_backend.infrastructure.auth import hash_password
from tests.integration.conftest import auth_headers_for

TOKEN_URL = "/api/auth/token"
ME_URL = "/api/auth/me"
CHANGE_URL = "/api/auth/change-password"
LOGOUT_URL = "/api/auth/logout"
CONVERSATIONS_URL = "/api/conversations"
OLD_PASSWORD = "SecurePass123!"
NEW_PASSWORD = "NewSecurePass456!"
CODE_CHANGE_REQUIRED = "password_change_required"


@dataclass(frozen=True)
class FlowEnv:
    """The real app over a prepared database."""

    app: FastAPI

    def client(self, headers: dict[str, str] | None = None) -> AsyncClient:
        """A client for the app, optionally carrying auth headers."""
        return AsyncClient(
            transport=ASGITransport(app=self.app),
            base_url="http://test",
            headers=headers or {},
        )

    def client_for(self, user: User) -> AsyncClient:
        """A client signed in as ``user`` with a freshly issued token."""
        return self.client(auth_headers_for(user))


@asynccontextmanager
async def app_over(engine: AsyncEngine) -> AsyncIterator[FlowEnv]:
    """The app using ``engine`` as its database, with a fresh rate limiter."""
    import rag_backend.infrastructure.database.config as db_config
    from rag_backend.api.app import create_app
    from rag_backend.api.middleware.rate_limiting import limiter

    limiter.reset()
    db_config.c_engine = engine
    try:
        yield FlowEnv(app=create_app())
    finally:
        db_config.c_engine = None


async def seed_user(email: str, role: UserRole) -> User:
    """Persist a user whose password is ``OLD_PASSWORD`` and commit."""
    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.user_repository import (
        PostgresUserRepository,
    )

    async with get_session_maker()() as session:
        user = User(
            email=email,
            full_name="Flow User",
            role=role,
            hashed_password=hash_password(OLD_PASSWORD),
        )
        created = await PostgresUserRepository(session).create(user)
        await session.commit()
    return created


async def stored_user(user_id: UUID) -> User:
    """Read the user back in a fresh session."""
    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.user_repository import (
        PostgresUserRepository,
    )

    async with get_session_maker()() as session:
        user = await PostgresUserRepository(session).get_by_id(user_id)
    assert user is not None
    return user


async def login(env: FlowEnv, credentials: tuple[str, str]) -> Response:
    """POST the email and password to the token endpoint."""
    email, password = credentials
    async with env.client() as client:
        return await client.post(TOKEN_URL, json={"email": email, "password": password})


def bearer(token_response: Response) -> dict[str, str]:
    """Auth headers carrying the token a login returned."""
    return {"Authorization": f"Bearer {token_response.json()['access_token']}"}


async def reset_by_admin(env: FlowEnv, admin: User, target: User) -> str:
    """Reset ``target``'s password as ``admin``; the temporary password."""
    async with env.client_for(admin) as client:
        resp = await client.post(f"/api/admin/users/{target.id}/reset-password")
    assert resp.status_code == 200
    return str(resp.json()["temp_password"])


def change_body(current: str, new: str) -> dict[str, str]:
    """The change-password request body."""
    return {"current_password": current, "new_password": new}
