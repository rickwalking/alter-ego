"""Caption and LinkedIn post edits are saved through the real route.

Feature: carousel_copy_edit_ae0492.feature
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Final
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from rag_backend.domain.constants.carousel_workflow import (
    PHASE_CONTENT,
    PHASE_STATUS_AWAITING_HUMAN,
    PHASE_STATUS_IN_PROGRESS,
    WORKFLOW_STATUS_APPROVED_FOR_PUBLISH,
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


async def _make_engine(db_path: str) -> AsyncEngine:
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


@pytest_asyncio.fixture
async def copy_env(
    tmp_path: object, monkeypatch: pytest.MonkeyPatch
) -> AsyncGenerator[CopyEnv, None]:
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
    engine = await _make_engine(str(tmp_path / "copy_env.db"))
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


async def _patch_copy(
    client: AsyncClient,
    project_id: str,
    body: dict[str, object],
    lock_version: int | None = INITIAL_LOCK_VERSION,
) -> Response:
    headers = {} if lock_version is None else {IF_MATCH: str(lock_version)}
    return await client.patch(
        f"/api/carousels/{project_id}/copy", json=body, headers=headers
    )


async def _saved(env: CopyEnv, project_id: str) -> dict[str, object]:
    async with env.client_for(env.owner) as client:
        resp = await client.get(f"/api/carousels/{project_id}")
    assert resp.status_code == 200
    body: dict[str, object] = resp.json()
    return body


@pytest.mark.asyncio
async def test_owner_saves_an_edited_caption(copy_env: CopyEnv) -> None:
    # Scenario: The owner saves an edited caption
    project_id = await copy_env.seed_carousel()
    async with copy_env.client_for(copy_env.owner) as client:
        resp = await _patch_copy(client, project_id, {"caption": EDITED_CAPTION})
    assert resp.status_code == 200
    body = resp.json()
    assert body["caption"] == EDITED_CAPTION
    assert body["linkedin_post_pt"] == GENERATED_LINKEDIN_PT
    assert body["lock_version"] == INITIAL_LOCK_VERSION + 1
    saved = await _saved(copy_env, project_id)
    assert saved["caption"] == EDITED_CAPTION


@pytest.mark.asyncio
async def test_linkedin_posts_are_saved_per_language(copy_env: CopyEnv) -> None:
    # Scenario: The LinkedIn posts are saved per language
    project_id = await copy_env.seed_carousel()
    async with copy_env.client_for(copy_env.owner) as client:
        resp = await _patch_copy(
            client,
            project_id,
            {
                "linkedin_post_pt": EDITED_LINKEDIN_PT,
                "linkedin_post_en": EDITED_LINKEDIN_EN,
            },
        )
    assert resp.status_code == 200
    saved = await _saved(copy_env, project_id)
    assert saved["linkedin_post_pt"] == EDITED_LINKEDIN_PT
    assert saved["linkedin_post_en"] == EDITED_LINKEDIN_EN
    assert saved["caption"] == GENERATED_CAPTION


@pytest.mark.asyncio
async def test_another_editor_cannot_change_the_texts(copy_env: CopyEnv) -> None:
    # Scenario: Someone else cannot change the texts
    project_id = await copy_env.seed_carousel()
    async with copy_env.client_for(copy_env.other) as client:
        resp = await _patch_copy(client, project_id, {"caption": EDITED_CAPTION})
    assert resp.status_code == 403
    saved = await _saved(copy_env, project_id)
    assert saved["caption"] == GENERATED_CAPTION


@pytest.mark.asyncio
async def test_admin_can_save_the_texts_of_any_carousel(copy_env: CopyEnv) -> None:
    # Scenario: An admin can save the texts of any carousel
    project_id = await copy_env.seed_carousel()
    async with copy_env.client_for(copy_env.admin) as client:
        resp = await _patch_copy(
            client, project_id, {"linkedin_post_en": EDITED_LINKEDIN_EN}
        )
    assert resp.status_code == 200
    saved = await _saved(copy_env, project_id)
    assert saved["linkedin_post_en"] == EDITED_LINKEDIN_EN


@pytest.mark.asyncio
async def test_unknown_carousel_is_not_found(copy_env: CopyEnv) -> None:
    # Scenario: Someone else cannot change the texts
    async with copy_env.client_for(copy_env.owner) as client:
        resp = await _patch_copy(client, str(uuid4()), {"caption": EDITED_CAPTION})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_save_without_if_match_is_refused(copy_env: CopyEnv) -> None:
    # Scenario: A save without the lock version is refused
    project_id = await copy_env.seed_carousel()
    async with copy_env.client_for(copy_env.owner) as client:
        resp = await _patch_copy(
            client, project_id, {"caption": EDITED_CAPTION}, lock_version=None
        )
    assert resp.status_code == 428


@pytest.mark.asyncio
async def test_save_from_a_stale_page_is_refused(copy_env: CopyEnv) -> None:
    # Scenario: A save from a stale page is refused
    project_id = await copy_env.seed_carousel()
    await copy_env.set_project(project_id, {"lock_version": INITIAL_LOCK_VERSION + 1})
    async with copy_env.client_for(copy_env.owner) as client:
        resp = await _patch_copy(client, project_id, {"caption": EDITED_CAPTION})
    assert resp.status_code == 409
    assert resp.json()["detail"] == "version_conflict"
    saved = await _saved(copy_env, project_id)
    assert saved["caption"] == GENERATED_CAPTION


@pytest.mark.asyncio
async def test_published_caption_is_read_only(copy_env: CopyEnv) -> None:
    # Scenario: The caption of a carousel published on Instagram is read-only
    project_id = await copy_env.seed_carousel()
    await copy_env.mark_instagram_published(project_id)
    async with copy_env.client_for(copy_env.owner) as client:
        resp = await _patch_copy(client, project_id, {"caption": EDITED_CAPTION})
    assert resp.status_code == 409
    assert resp.json()["detail"] == "caption_published"
    saved = await _saved(copy_env, project_id)
    assert saved["caption"] == GENERATED_CAPTION


@pytest.mark.asyncio
async def test_linkedin_post_stays_editable_after_instagram_publish(
    copy_env: CopyEnv,
) -> None:
    # Scenario: The caption of a carousel published on Instagram is read-only
    project_id = await copy_env.seed_carousel()
    await copy_env.mark_instagram_published(project_id)
    async with copy_env.client_for(copy_env.owner) as client:
        resp = await _patch_copy(
            client, project_id, {"linkedin_post_pt": EDITED_LINKEDIN_PT}
        )
    assert resp.status_code == 200
    saved = await _saved(copy_env, project_id)
    assert saved["linkedin_post_pt"] == EDITED_LINKEDIN_PT


@pytest.mark.asyncio
async def test_texts_cannot_change_while_a_run_is_active(copy_env: CopyEnv) -> None:
    # Scenario: The texts cannot change while a workflow run is active
    project_id = await copy_env.seed_carousel()
    await copy_env.set_project(project_id, {"phase_status": PHASE_STATUS_IN_PROGRESS})
    async with copy_env.client_for(copy_env.owner) as client:
        resp = await _patch_copy(client, project_id, {"caption": EDITED_CAPTION})
    assert resp.status_code == 409
    assert resp.json()["detail"] == "resume_already_in_progress"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body",
    [
        {},
        {"caption": None},
        {"caption": "x" * (IG_CAPTION_LIMIT + 1)},
        {"linkedin_post_pt": "x" * 3001},
    ],
)
async def test_empty_or_oversized_save_is_rejected(
    copy_env: CopyEnv, body: dict[str, object]
) -> None:
    # Scenario: An empty or oversized save is rejected
    project_id = await copy_env.seed_carousel()
    async with copy_env.client_for(copy_env.owner) as client:
        resp = await _patch_copy(client, project_id, body)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_saving_the_texts_keeps_the_carousel_approved(
    copy_env: CopyEnv, tmp_path: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Scenario: Saving the texts keeps the carousel approved for publish
    from unittest.mock import AsyncMock

    from rag_backend.domain.protocols import PublishResult
    from rag_backend.infrastructure.config.settings import get_settings
    from rag_backend.infrastructure.container import get_container
    from tests.integration.carousel_consolidation.helpers import (
        create_minimal_carousel_artifacts,
    )

    project_id = await copy_env.seed_carousel()
    output_dir = str(tmp_path) + "/carousel-output"
    await copy_env.set_project(
        project_id,
        {
            "workflow_status": WORKFLOW_STATUS_APPROVED_FOR_PUBLISH,
            "output_dir": output_dir,
        },
    )
    await create_minimal_carousel_artifacts(project_id, output_dir=output_dir)
    monkeypatch.setenv("CAROUSEL_PUBLIC_BASE_URL", PUBLIC_BASE_URL)
    get_settings.cache_clear()
    publisher = AsyncMock()
    publisher.publish_instagram = AsyncMock(
        return_value=PublishResult(status="published", post_id=PUBLISHED_POST_ID),
    )
    container = get_container()
    container.instagram_publisher.override(publisher)
    try:
        async with copy_env.client_for(copy_env.owner) as client:
            saved = await _patch_copy(client, project_id, {"caption": EDITED_CAPTION})
            status_after_save = await copy_env.workflow_status(project_id)
            published = await client.post(
                f"/api/carousels/{project_id}/publish/instagram",
                json={"caption": EDITED_CAPTION},
            )
    finally:
        container.instagram_publisher.reset_override()
    assert saved.status_code == 200
    assert status_after_save == WORKFLOW_STATUS_APPROVED_FOR_PUBLISH
    assert published.status_code == 200, published.text
    assert published.json()["ig_post_id"] == PUBLISHED_POST_ID
    assert publisher.publish_instagram.call_args[0][0] == EDITED_CAPTION
