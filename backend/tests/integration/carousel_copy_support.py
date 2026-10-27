"""Shared app, users and helpers of the carousel copy route tests.

Feature: carousel_copy_edit_ae0492.feature, carousel_copy_versions_ae0506.feature
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Final
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from rag_backend.domain.constants.carousel_workflow import (
    PHASE_CONTENT,
    PHASE_STATUS_AWAITING_HUMAN,
)
from rag_backend.domain.models import (
    CarouselProject,
    CarouselStatus,
    CarouselTheme,
    UserRole,
)
from tests.integration.conftest import TEST_SECRET, auth_headers_for, create_test_user

if TYPE_CHECKING:
    from fastapi import FastAPI
    from httpx import Response
    from sqlalchemy.ext.asyncio import AsyncEngine

    from rag_backend.domain.models import User

ANON_SECRET: Final = "test-anon-secret-key-for-copy-edit-tests"
OWNER_EMAIL: Final = "copy-owner@example.com"
OTHER_EMAIL: Final = "copy-other@example.com"
ADMIN_EMAIL: Final = "copy-admin@example.com"
GENERATED_CAPTION: Final = "Legenda gerada"
GENERATED_LINKEDIN_PT: Final = "Post gerado"
GENERATED_LINKEDIN_EN: Final = "Generated post"
EDITED_CAPTION: Final = "Legenda editada pelo dono"
EDITED_LINKEDIN_PT: Final = "Post editado em portugues"
EDITED_LINKEDIN_EN: Final = "Edited English post"
IG_CAPTION_LIMIT: Final = 2200
INITIAL_LOCK_VERSION: Final = 1
STATE_PUBLISHED: Final = "published"
STUB_IG_POST_ID: Final = "17890000000000001"
IF_MATCH: Final = "If-Match"
PUBLIC_BASE_URL: Final = "https://public.test"
PUBLISHED_POST_ID: Final = "IG_after_copy_edit"


async def make_engine(db_path: str) -> AsyncEngine:
    from sqlalchemy.ext.asyncio import create_async_engine

    import rag_backend.infrastructure.database.config as db_config
    from rag_backend.infrastructure.database.config import Base

    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    db_config.c_engine = engine
    return engine


class CopyEnv:
    """App, users and seeding helpers for the copy edit route."""

    def __init__(self, app: FastAPI, users: dict[str, User]) -> None:
        self._app = app
        self.owner = users[OWNER_EMAIL]
        self.other = users[OTHER_EMAIL]
        self.admin = users[ADMIN_EMAIL]

    def client_for(self, user: User) -> AsyncClient:
        """An HTTP client authenticated as ``user``."""
        return AsyncClient(
            transport=ASGITransport(app=self._app),
            base_url="http://test",
            headers=auth_headers_for(user),
        )

    def anonymous_client(self) -> AsyncClient:
        """An HTTP client without authentication."""
        return AsyncClient(
            transport=ASGITransport(app=self._app), base_url="http://test"
        )

    async def seed_carousel(self) -> str:
        """A completed carousel of the owner with its canonical distribution row."""
        from rag_backend.domain.constants.blog_post import (
            BlogPostOrigin,
            BlogPostStatus,
        )
        from rag_backend.infrastructure.database.carousel_repository import (
            PostgresCarouselRepository,
        )
        from rag_backend.infrastructure.database.config import get_session_maker
        from rag_backend.infrastructure.database.distribution_home import (
            build_distribution,
        )
        from rag_backend.infrastructure.database.models import BlogPostModel

        async with get_session_maker()() as session:
            project = CarouselProject(
                topic="Copy topic",
                audience="Copy audience",
                niche="COPY",
                theme=CarouselTheme.AI_COMPETITION,
                owner_id=str(self.owner.id),
                status=CarouselStatus.COMPLETED,
                generate_images=False,
                caption=GENERATED_CAPTION,
                linkedin_post_pt=GENERATED_LINKEDIN_PT,
                linkedin_post_en=GENERATED_LINKEDIN_EN,
                current_phase=PHASE_CONTENT,
                phase_status=PHASE_STATUS_AWAITING_HUMAN,
            )
            created = await PostgresCarouselRepository(session).create_project(project)
            project_id = str(created.id)
            session.add(
                BlogPostModel.from_entity({
                    "id": str(uuid4()),
                    "project_id": project_id,
                    "origin": BlogPostOrigin.CAROUSEL.value,
                    "title": "Copy title",
                    "slug": f"carousel-{project_id}",
                    "status": BlogPostStatus.DRAFT.value,
                    "content": {},
                    "distribution": build_distribution(project),
                })
            )
            await session.commit()
        return project_id

    async def set_project(self, project_id: str, values: dict[str, object]) -> None:
        """Overwrite columns of the carousel row."""
        from rag_backend.infrastructure.database.config import get_session_maker
        from rag_backend.infrastructure.database.models.carousel import (
            CarouselProjectModel,
        )

        async with get_session_maker()() as session:
            model = await session.get(CarouselProjectModel, project_id)
            assert model is not None
            for key, value in values.items():
                setattr(model, key, value)
            await session.commit()

    async def workflow_status(self, project_id: str) -> str:
        """The carousel row's ``workflow_status``."""
        from rag_backend.infrastructure.database.config import get_session_maker
        from rag_backend.infrastructure.database.models.carousel import (
            CarouselProjectModel,
        )

        async with get_session_maker()() as session:
            model = await session.get(CarouselProjectModel, project_id)
            assert model is not None
            return model.workflow_status

    async def mark_instagram_published(self, project_id: str) -> None:
        """Record a finished manual Instagram publish for the carousel."""
        from rag_backend.infrastructure.database.config import get_session_maker
        from rag_backend.modules.autopilot.infrastructure.models import (
            ManualPublishModel,
        )

        async with get_session_maker()() as session:
            session.add(
                ManualPublishModel(
                    carousel_project_id=project_id,
                    state=STATE_PUBLISHED,
                    ig_post_id=STUB_IG_POST_ID,
                    claimed_at=datetime.now(UTC),
                )
            )
            await session.commit()


@asynccontextmanager
async def copy_env_context(
    tmp_path: object, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[CopyEnv]:
    """File-backed database and app with an owner, another editor and an admin."""
    from pathlib import Path

    import rag_backend.infrastructure.database.config as db_config
    from rag_backend.api.app import create_app
    from rag_backend.infrastructure.config.settings import get_settings
    from rag_backend.infrastructure.database.config import close_db

    assert isinstance(tmp_path, Path)
    os.environ["SECRET_KEY"] = TEST_SECRET
    os.environ["ANON_SECRET_KEY"] = ANON_SECRET
    monkeypatch.setenv("DEBUG", "false")
    get_settings.cache_clear()
    engine = await make_engine(str(tmp_path / "copy_env.db"))
    users = {
        OWNER_EMAIL: await create_test_user(OWNER_EMAIL, UserRole.EDITOR),
        OTHER_EMAIL: await create_test_user(OTHER_EMAIL, UserRole.EDITOR),
        ADMIN_EMAIL: await create_test_user(ADMIN_EMAIL, UserRole.ADMIN),
    }
    try:
        yield CopyEnv(app=create_app(), users=users)
    finally:
        db_config.c_engine = None
        await close_db()
        await engine.dispose()
        get_settings.cache_clear()


async def patch_copy(
    client: AsyncClient,
    project_id: str,
    body: dict[str, object],
    lock_version: int | None = INITIAL_LOCK_VERSION,
) -> Response:
    headers = {} if lock_version is None else {IF_MATCH: str(lock_version)}
    return await client.patch(
        f"/api/carousels/{project_id}/copy", json=body, headers=headers
    )


async def saved_project(env: CopyEnv, project_id: str) -> dict[str, object]:
    async with env.client_for(env.owner) as client:
        resp = await client.get(f"/api/carousels/{project_id}")
    assert resp.status_code == 200
    body: dict[str, object] = resp.json()
    return body
