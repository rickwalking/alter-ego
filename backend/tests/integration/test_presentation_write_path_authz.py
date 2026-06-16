"""Authorization-parity contract tests for the presentation WRITE entry points
(AE-0118, extending AE-0113 / ADR-0009 §5).

AE-0113 covered the carousel editorial-WORKFLOW write paths. This module extends
the same deny-by-default, owner/admin policy contract to the PRESENTATION write
entry points the AE-0118 presentation single-writer/ACL now backs:

  1. design-token refresh  -> POST /api/admin/carousels/refresh-design-tokens
  2. render-slides          -> POST /api/admin/carousels/render-slides
  3. creator-asset upload   -> POST /api/carousels/{id}/creator-asset/upload
  4. strategy apply         -> PUT  /api/carousels/{id}/strategy

The contract under test (ADR-0009 §5: HTTP routes enforce the context-owned
policy; deny-by-default). Each presentation write path has a defined access
class, and these tests assert the SAME allow/deny OUTCOME holds for it:

  * **admin-only paths** (refresh-design-tokens, render-slides): unauthorized and
    authenticated non-admin -> DENIED; admin -> ALLOWED.
  * **owner-or-admin path** (creator-asset upload): unauthorized and
    authenticated non-owner -> DENIED; owner and admin -> ALLOWED past the
    authorization boundary.
  * **authenticated path** (strategy apply): unauthorized -> DENIED; an
    authenticated actor passes the authorization boundary (the route enforces
    authentication, then resolves the project — behavior-preserving, NOT changed
    by AE-0118).

These are AUTHORIZATION-OUTCOME assertions: an ALLOWED actor is asserted to pass
the auth boundary (status is NOT 401/403); a DENIED actor is asserted to be
rejected at it (401 or 403). No external client (LLM, image gen, Pinecone) is
ever invoked — the database is in-memory SQLite, matching tests/integration.

Gherkin (see ticket AE-0118 AC: authorization parity on presentation write paths):

  Feature: Presentation write-path authorization parity
    Scenario Outline: same authorization across presentation write entry points
      Given an actor of class <actor>
      When a presentation write is attempted via <entry_point>
      Then access is <outcome> consistent with that path's access class
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from dataclasses import dataclass

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from rag_backend.domain.models import (
    CarouselProject,
    CarouselStatus,
    CarouselTheme,
    User,
    UserRole,
)

TEST_SECRET = "test-secret-for-presentation-authz-contract!!"
ANON_SECRET = "test-anon-secret-for-presentation-authz"

# Auth outcomes the contract asserts.
OUTCOME_ALLOW = "allow"
OUTCOME_DENY = "deny"
_DENY_STATUSES = (401, 403)

# Presentation write entry points + their access class.
PATH_REFRESH_DESIGN = "/api/admin/carousels/refresh-design-tokens"
PATH_RENDER_SLIDES = "/api/admin/carousels/render-slides"


def _auth_headers(user: User) -> dict[str, str]:
    from datetime import UTC, datetime, timedelta

    import jwt

    from rag_backend.domain.constants import JWT_ALGORITHM, JWT_TYPE_AUTH

    payload: dict[str, object] = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value,
        "type": JWT_TYPE_AUTH,
        "exp": datetime.now(UTC) + timedelta(hours=1),
        "iat": datetime.now(UTC),
    }
    token = jwt.encode(payload, TEST_SECRET, algorithm=JWT_ALGORITHM)
    return {"Authorization": f"Bearer {token}"}


async def _create_user(email: str, role: UserRole) -> User:
    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.user_repository import (
        PostgresUserRepository,
    )

    session_maker = get_session_maker()
    async with session_maker() as session:
        repo = PostgresUserRepository(session)
        user = User(
            email=email,
            full_name=email.split("@")[0].title(),
            role=role,
            hashed_password="not-used",
        )
        created = await repo.create(user)
        await session.commit()
        return created


async def _create_project(owner: User) -> str:
    from rag_backend.infrastructure.database.carousel_repository import (
        PostgresCarouselRepository,
    )
    from rag_backend.infrastructure.database.config import get_session_maker

    session_maker = get_session_maker()
    async with session_maker() as session:
        repo = PostgresCarouselRepository(session)
        project = CarouselProject(
            topic="Presentation Authz Project",
            audience="Devs",
            niche="AI",
            theme=CarouselTheme.AUTO,
            owner_id=str(owner.id),
            status=CarouselStatus.COMPLETED,
            output_dir="/tmp/pres-authz-output",
        )
        created = await repo.create_project(project)
        await session.commit()
        return str(created.id)


@dataclass(frozen=True)
class _Harness:
    """Live ASGI app + persisted users/project for one presentation-authz scenario."""

    client: AsyncClient
    owner: User
    admin: User
    non_owner: User
    project_id: str


@pytest_asyncio.fixture
async def harness() -> AsyncIterator[_Harness]:
    """Async client with in-memory SQLite plus owner/admin/non-owner + a project."""
    from sqlalchemy.ext.asyncio import create_async_engine

    import rag_backend.infrastructure.database.config as db_config
    from rag_backend.api.app import create_app
    from rag_backend.infrastructure.config.settings import get_settings
    from rag_backend.infrastructure.database.config import Base, close_db

    get_settings.cache_clear()
    os.environ["SECRET_KEY"] = TEST_SECRET
    os.environ["ANON_SECRET_KEY"] = ANON_SECRET

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    db_config.c_engine = engine

    owner = await _create_user("pres-owner@authz.test", UserRole.EDITOR)
    admin = await _create_user("pres-admin@authz.test", UserRole.ADMIN)
    non_owner = await _create_user("pres-intruder@authz.test", UserRole.EDITOR)
    project_id = await _create_project(owner)

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield _Harness(
            client=client,
            owner=owner,
            admin=admin,
            non_owner=non_owner,
            project_id=project_id,
        )

    db_config.c_engine = None
    await close_db()
    await engine.dispose()
    get_settings.cache_clear()


def _png_bytes() -> bytes:
    import io

    from PIL import Image

    image = Image.new("RGB", (64, 64), color=(1, 2, 3))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


# === Admin-only write paths (refresh-design-tokens, render-slides) =============
class TestAdminOnlyPresentationWrites:
    """Scenario: admin-only presentation writes deny-by-default for non-admins."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", [PATH_REFRESH_DESIGN, PATH_RENDER_SLIDES])
    async def test_denies_unauthorized(self, harness: _Harness, path: str) -> None:
        """No JWT -> denied at the admin presentation write boundary."""
        resp = await harness.client.post(path)
        assert resp.status_code in _DENY_STATUSES

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", [PATH_REFRESH_DESIGN, PATH_RENDER_SLIDES])
    async def test_denies_authenticated_non_admin(
        self, harness: _Harness, path: str
    ) -> None:
        """Authenticated non-admin editor -> denied (admin-only path)."""
        resp = await harness.client.post(path, headers=_auth_headers(harness.non_owner))
        assert resp.status_code == 403

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", [PATH_REFRESH_DESIGN, PATH_RENDER_SLIDES])
    async def test_authorizes_admin(self, harness: _Harness, path: str) -> None:
        """Admin clears the authorization boundary (status is NOT 401/403).

        The admin presentation refresh routes the write through the AE-0118
        presentation single-writer/ACL; a non-401/403 status proves the admin
        passed the authorization gate (the body succeeds against the seeded
        project — no external client is invoked).
        """
        resp = await harness.client.post(path, headers=_auth_headers(harness.admin))
        assert resp.status_code not in _DENY_STATUSES


# === Owner-or-admin write path (creator-asset upload) =========================
class TestCreatorAssetWriteAuthorization:
    """Scenario: creator-asset upload enforces owner-or-admin."""

    def _url(self, harness: _Harness) -> str:
        return f"/api/carousels/{harness.project_id}/creator-asset/upload"

    @pytest.mark.asyncio
    async def test_denies_unauthorized(self, harness: _Harness) -> None:
        """No JWT -> denied at the creator-asset upload boundary."""
        resp = await harness.client.post(
            self._url(harness),
            files={"file": ("brand.png", _png_bytes(), "image/png")},
        )
        assert resp.status_code in _DENY_STATUSES

    @pytest.mark.asyncio
    async def test_denies_authenticated_non_owner(self, harness: _Harness) -> None:
        """Authenticated non-owner editor -> denied (owner-or-admin path)."""
        resp = await harness.client.post(
            self._url(harness),
            files={"file": ("brand.png", _png_bytes(), "image/png")},
            headers=_auth_headers(harness.non_owner),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    @pytest.mark.parametrize("actor", ["owner", "admin"])
    async def test_authorizes_owner_and_admin(
        self, harness: _Harness, actor: str
    ) -> None:
        """Owner and admin clear the creator-asset authorization boundary."""
        user = harness.owner if actor == "owner" else harness.admin
        resp = await harness.client.post(
            self._url(harness),
            files={"file": ("brand.png", _png_bytes(), "image/png")},
            headers=_auth_headers(user),
        )
        assert resp.status_code not in _DENY_STATUSES


# === Authenticated write path (strategy apply) ================================
class TestStrategyApplyAuthorization:
    """Scenario: strategy apply requires authentication (behavior-preserving)."""

    def _url(self, harness: _Harness) -> str:
        return f"/api/carousels/{harness.project_id}/strategy?name=default"

    @pytest.mark.asyncio
    async def test_denies_unauthorized(self, harness: _Harness) -> None:
        """No JWT -> denied at the strategy-apply boundary."""
        resp = await harness.client.put(self._url(harness))
        assert resp.status_code in _DENY_STATUSES

    @pytest.mark.asyncio
    async def test_authenticated_actor_passes_auth_boundary(
        self, harness: _Harness
    ) -> None:
        """An authenticated actor passes the authentication gate.

        The strategy route enforces authentication (router-level), then resolves
        the project; a non-401 status proves the authentication boundary was
        passed. AE-0118 does NOT change this access class (behavior-preserving).
        """
        resp = await harness.client.put(
            self._url(harness),
            headers=_auth_headers(harness.owner),
        )
        assert resp.status_code != 401
