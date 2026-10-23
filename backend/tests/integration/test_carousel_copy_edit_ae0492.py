"""Caption and LinkedIn post edits are saved through the real route.

Feature: carousel_copy_edit_ae0492.feature
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio

from rag_backend.domain.constants.carousel_workflow import (
    PHASE_STATUS_IN_PROGRESS,
    WORKFLOW_STATUS_APPROVED_FOR_PUBLISH,
)
from tests.integration.carousel_copy_support import (
    EDITED_CAPTION,
    EDITED_LINKEDIN_EN,
    EDITED_LINKEDIN_PT,
    GENERATED_CAPTION,
    GENERATED_LINKEDIN_PT,
    IG_CAPTION_LIMIT,
    INITIAL_LOCK_VERSION,
    PUBLIC_BASE_URL,
    PUBLISHED_POST_ID,
    CopyEnv,
    copy_env_context,
    patch_copy,
    saved_project,
)


@pytest_asyncio.fixture
async def copy_env(
    tmp_path: object, monkeypatch: pytest.MonkeyPatch
) -> AsyncGenerator[CopyEnv, None]:
    """File-backed database and app with an owner, another editor and an admin."""
    async with copy_env_context(tmp_path, monkeypatch) as env:
        yield env


@pytest.mark.asyncio
async def test_owner_saves_an_edited_caption(copy_env: CopyEnv) -> None:
    """Scenario: The owner saves an edited caption."""
    project_id = await copy_env.seed_carousel()
    async with copy_env.client_for(copy_env.owner) as client:
        resp = await patch_copy(client, project_id, {"caption": EDITED_CAPTION})
    assert resp.status_code == 200
    body = resp.json()
    assert body["caption"] == EDITED_CAPTION
    assert body["linkedin_post_pt"] == GENERATED_LINKEDIN_PT
    assert body["lock_version"] == INITIAL_LOCK_VERSION + 1
    saved = await saved_project(copy_env, project_id)
    assert saved["caption"] == EDITED_CAPTION


@pytest.mark.asyncio
async def test_linkedin_posts_are_saved_per_language(copy_env: CopyEnv) -> None:
    """Scenario: The LinkedIn posts are saved per language."""
    project_id = await copy_env.seed_carousel()
    async with copy_env.client_for(copy_env.owner) as client:
        resp = await patch_copy(
            client,
            project_id,
            {
                "linkedin_post_pt": EDITED_LINKEDIN_PT,
                "linkedin_post_en": EDITED_LINKEDIN_EN,
            },
        )
    assert resp.status_code == 200
    saved = await saved_project(copy_env, project_id)
    assert saved["linkedin_post_pt"] == EDITED_LINKEDIN_PT
    assert saved["linkedin_post_en"] == EDITED_LINKEDIN_EN
    assert saved["caption"] == GENERATED_CAPTION


@pytest.mark.asyncio
async def test_another_editor_cannot_change_the_texts(copy_env: CopyEnv) -> None:
    """Scenario: Someone else cannot change the texts."""
    project_id = await copy_env.seed_carousel()
    async with copy_env.client_for(copy_env.other) as client:
        resp = await patch_copy(client, project_id, {"caption": EDITED_CAPTION})
    assert resp.status_code == 403
    saved = await saved_project(copy_env, project_id)
    assert saved["caption"] == GENERATED_CAPTION


@pytest.mark.asyncio
async def test_admin_can_save_the_texts_of_any_carousel(copy_env: CopyEnv) -> None:
    """Scenario: An admin can save the texts of any carousel."""
    project_id = await copy_env.seed_carousel()
    async with copy_env.client_for(copy_env.admin) as client:
        resp = await patch_copy(
            client, project_id, {"linkedin_post_en": EDITED_LINKEDIN_EN}
        )
    assert resp.status_code == 200
    saved = await saved_project(copy_env, project_id)
    assert saved["linkedin_post_en"] == EDITED_LINKEDIN_EN


@pytest.mark.asyncio
async def test_unknown_carousel_is_not_found(copy_env: CopyEnv) -> None:
    """Scenario: Someone else cannot change the texts."""
    async with copy_env.client_for(copy_env.owner) as client:
        resp = await patch_copy(client, str(uuid4()), {"caption": EDITED_CAPTION})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_save_without_if_match_is_refused(copy_env: CopyEnv) -> None:
    """Scenario: A save without the lock version is refused."""
    project_id = await copy_env.seed_carousel()
    async with copy_env.client_for(copy_env.owner) as client:
        resp = await patch_copy(
            client, project_id, {"caption": EDITED_CAPTION}, lock_version=None
        )
    assert resp.status_code == 428


@pytest.mark.asyncio
async def test_save_from_a_stale_page_is_refused(copy_env: CopyEnv) -> None:
    """Scenario: A save from a stale page is refused."""
    project_id = await copy_env.seed_carousel()
    await copy_env.set_project(project_id, {"lock_version": INITIAL_LOCK_VERSION + 1})
    async with copy_env.client_for(copy_env.owner) as client:
        resp = await patch_copy(client, project_id, {"caption": EDITED_CAPTION})
    assert resp.status_code == 409
    assert resp.json()["detail"] == "version_conflict"
    saved = await saved_project(copy_env, project_id)
    assert saved["caption"] == GENERATED_CAPTION


@pytest.mark.asyncio
async def test_published_caption_is_read_only(copy_env: CopyEnv) -> None:
    """Scenario: The caption of a carousel published on Instagram is read-only."""
    project_id = await copy_env.seed_carousel()
    await copy_env.mark_instagram_published(project_id)
    async with copy_env.client_for(copy_env.owner) as client:
        resp = await patch_copy(client, project_id, {"caption": EDITED_CAPTION})
    assert resp.status_code == 409
    assert resp.json()["detail"] == "caption_published"
    saved = await saved_project(copy_env, project_id)
    assert saved["caption"] == GENERATED_CAPTION


@pytest.mark.asyncio
async def test_linkedin_post_stays_editable_after_instagram_publish(
    copy_env: CopyEnv,
) -> None:
    """Scenario: The caption of a carousel published on Instagram is read-only."""
    project_id = await copy_env.seed_carousel()
    await copy_env.mark_instagram_published(project_id)
    async with copy_env.client_for(copy_env.owner) as client:
        resp = await patch_copy(
            client, project_id, {"linkedin_post_pt": EDITED_LINKEDIN_PT}
        )
    assert resp.status_code == 200
    saved = await saved_project(copy_env, project_id)
    assert saved["linkedin_post_pt"] == EDITED_LINKEDIN_PT


@pytest.mark.asyncio
async def test_texts_cannot_change_while_a_run_is_active(copy_env: CopyEnv) -> None:
    """Scenario: The texts cannot change while a workflow run is active."""
    project_id = await copy_env.seed_carousel()
    await copy_env.set_project(project_id, {"phase_status": PHASE_STATUS_IN_PROGRESS})
    async with copy_env.client_for(copy_env.owner) as client:
        resp = await patch_copy(client, project_id, {"caption": EDITED_CAPTION})
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
    """Scenario: An empty or oversized save is rejected."""
    project_id = await copy_env.seed_carousel()
    async with copy_env.client_for(copy_env.owner) as client:
        resp = await patch_copy(client, project_id, body)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_saving_the_texts_keeps_the_carousel_approved(
    copy_env: CopyEnv, tmp_path: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Scenario: Saving the texts keeps the carousel approved for publish."""
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
            saved = await patch_copy(client, project_id, {"caption": EDITED_CAPTION})
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
