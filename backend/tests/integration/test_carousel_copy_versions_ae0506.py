"""Caption and LinkedIn post edits are kept as versions and can be restored.

Feature: carousel_copy_versions_ae0506.feature
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Final
from uuid import uuid4

import pytest
import pytest_asyncio

from rag_backend.domain.constants.carousel_conflicts import (
    CONFLICT_CODE_RUN_IN_PROGRESS,
)
from rag_backend.domain.constants.carousel_copy_versions import (
    CONTENT_TYPE_CAROUSEL_COPY,
)
from rag_backend.domain.constants.carousel_workflow import PHASE_STATUS_IN_PROGRESS
from tests.integration.carousel_copy_support import (
    EDITED_CAPTION,
    EDITED_LINKEDIN_PT,
    GENERATED_CAPTION,
    GENERATED_LINKEDIN_PT,
    INITIAL_LOCK_VERSION,
    CopyEnv,
    copy_env_context,
    patch_copy,
    saved_project,
)

if TYPE_CHECKING:
    from httpx import AsyncClient, Response

SECOND_CAPTION: Final = "Segunda legenda editada"
REFINED_CAPTION: Final = "Legenda refinada pelo chat"
IF_MATCH: Final = "If-Match"
FIELD_CAPTION: Final = "caption"


@pytest_asyncio.fixture
async def copy_env(
    tmp_path: object, monkeypatch: pytest.MonkeyPatch
) -> AsyncGenerator[CopyEnv, None]:
    """File-backed database and app with an owner, another editor and an admin."""
    async with copy_env_context(tmp_path, monkeypatch) as env:
        yield env


async def _versions(client: AsyncClient, project_id: str) -> Response:
    return await client.get(f"/api/carousels/{project_id}/copy/versions")


async def _restore(
    client: AsyncClient, project_id: str, number: int, lock_version: int | None
) -> Response:
    headers = {} if lock_version is None else {IF_MATCH: str(lock_version)}
    return await client.post(
        f"/api/carousels/{project_id}/copy/versions/{number}/restore",
        headers=headers,
    )


async def _add_foreign_version(project_id: str) -> None:
    """A ``carousel_copy`` row whose snapshot names no copy field."""
    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.models.source_comment import (
        ContentVersionModel,
    )

    async with get_session_maker()() as session:
        session.add(
            ContentVersionModel(
                content_id=project_id,
                content_type=CONTENT_TYPE_CAROUSEL_COPY,
                version_number=7,
                snapshot={"field": "caption_en", "text": "x"},
            )
        )
        await session.commit()


async def _owner_versions(env: CopyEnv, project_id: str) -> list[dict[str, object]]:
    async with env.client_for(env.owner) as client:
        resp = await _versions(client, project_id)
    assert resp.status_code == 200, resp.text
    versions: list[dict[str, object]] = resp.json()["versions"]
    return versions


@pytest.mark.asyncio
async def test_first_caption_edit_stores_the_original_and_the_new_text(
    copy_env: CopyEnv,
) -> None:
    """Scenario: Saving a changed caption stores the original and the new text as versions."""
    project_id = await copy_env.seed_carousel()
    async with copy_env.client_for(copy_env.owner) as client:
        saved = await patch_copy(client, project_id, {"caption": EDITED_CAPTION})
    assert saved.status_code == 200

    versions = await _owner_versions(copy_env, project_id)

    assert [v["version_number"] for v in versions] == [2, 1]
    newest, original = versions
    assert newest["field"] == FIELD_CAPTION
    assert newest["text"] == EDITED_CAPTION
    assert newest["author_id"] == str(copy_env.owner.id)
    assert newest["author_name"] == copy_env.owner.full_name
    assert newest["created_at"]
    assert original["text"] == GENERATED_CAPTION
    assert original["author_id"] is None
    assert original["author_name"] is None


@pytest.mark.asyncio
async def test_later_edit_stores_only_the_new_text(copy_env: CopyEnv) -> None:
    """Scenario: A later edit of the same text stores only the new text."""
    project_id = await copy_env.seed_carousel()
    async with copy_env.client_for(copy_env.owner) as client:
        await patch_copy(client, project_id, {"caption": EDITED_CAPTION})
        second = await patch_copy(
            client,
            project_id,
            {"caption": SECOND_CAPTION},
            lock_version=INITIAL_LOCK_VERSION + 1,
        )
    assert second.status_code == 200

    versions = await _owner_versions(copy_env, project_id)

    assert [(v["version_number"], v["text"]) for v in versions] == [
        (3, SECOND_CAPTION),
        (2, EDITED_CAPTION),
        (1, GENERATED_CAPTION),
    ]


@pytest.mark.asyncio
async def test_unchanged_text_stores_no_version(copy_env: CopyEnv) -> None:
    """Scenario: A text that did not change stores no version."""
    project_id = await copy_env.seed_carousel()
    async with copy_env.client_for(copy_env.owner) as client:
        saved = await patch_copy(client, project_id, {"caption": GENERATED_CAPTION})
    assert saved.status_code == 200

    assert await _owner_versions(copy_env, project_id) == []


@pytest.mark.asyncio
async def test_each_carousel_numbers_its_versions_from_one(copy_env: CopyEnv) -> None:
    """Scenario: Each carousel numbers its versions from 1."""
    first = await copy_env.seed_carousel()
    second = await copy_env.seed_carousel()
    async with copy_env.client_for(copy_env.owner) as client:
        for project_id in (first, second):
            resp = await patch_copy(client, project_id, {"caption": EDITED_CAPTION})
            assert resp.status_code == 200, resp.text

    for project_id in (first, second):
        numbers = [
            v["version_number"] for v in await _owner_versions(copy_env, project_id)
        ]
        assert numbers == [2, 1]


@pytest.mark.asyncio
async def test_only_the_owner_or_an_admin_sees_the_versions(copy_env: CopyEnv) -> None:
    """Scenario: Only the owner or an admin sees the versions."""
    project_id = await copy_env.seed_carousel()
    async with copy_env.client_for(copy_env.owner) as client:
        await patch_copy(client, project_id, {"caption": EDITED_CAPTION})
    async with copy_env.client_for(copy_env.other) as client:
        refused = await _versions(client, project_id)
    async with copy_env.client_for(copy_env.admin) as client:
        allowed = await _versions(client, project_id)

    assert refused.status_code == 403
    assert allowed.status_code == 200
    assert len(allowed.json()["versions"]) == 2


@pytest.mark.asyncio
async def test_restore_saves_the_version_text_as_a_new_version(
    copy_env: CopyEnv,
) -> None:
    """Scenario: Restoring a version saves its text as a new version."""
    project_id = await copy_env.seed_carousel()
    async with copy_env.client_for(copy_env.owner) as client:
        await patch_copy(client, project_id, {"caption": EDITED_CAPTION})
        restored = await _restore(client, project_id, 1, INITIAL_LOCK_VERSION + 1)

    assert restored.status_code == 200, restored.text
    assert restored.json()["caption"] == GENERATED_CAPTION
    assert restored.json()["lock_version"] == INITIAL_LOCK_VERSION + 2
    assert (await saved_project(copy_env, project_id))["caption"] == GENERATED_CAPTION
    newest = (await _owner_versions(copy_env, project_id))[0]
    assert newest["version_number"] == 3
    assert newest["text"] == GENERATED_CAPTION
    assert newest["restored_from"] == 1


@pytest.mark.asyncio
async def test_restore_with_a_stale_lock_is_refused(copy_env: CopyEnv) -> None:
    """Scenario: A restore is refused when it cannot be applied."""
    project_id = await copy_env.seed_carousel()
    async with copy_env.client_for(copy_env.owner) as client:
        await patch_copy(client, project_id, {"caption": EDITED_CAPTION})
        stale = await _restore(client, project_id, 1, INITIAL_LOCK_VERSION)
        missing = await _restore(client, project_id, 9, INITIAL_LOCK_VERSION + 1)

    assert stale.status_code == 409
    assert stale.json()["detail"] == "version_conflict"
    assert missing.status_code == 404
    assert (await saved_project(copy_env, project_id))["caption"] == EDITED_CAPTION


@pytest.mark.asyncio
async def test_restoring_a_published_caption_is_refused(copy_env: CopyEnv) -> None:
    """Scenario: A restore is refused when it cannot be applied."""
    project_id = await copy_env.seed_carousel()
    async with copy_env.client_for(copy_env.owner) as client:
        await patch_copy(client, project_id, {"caption": EDITED_CAPTION})
    await copy_env.mark_instagram_published(project_id)
    async with copy_env.client_for(copy_env.owner) as client:
        refused = await _restore(client, project_id, 1, INITIAL_LOCK_VERSION + 1)

    assert refused.status_code == 409
    assert refused.json()["detail"] == "caption_published"


@pytest.mark.asyncio
async def test_someone_else_cannot_restore(copy_env: CopyEnv) -> None:
    """Scenario: Only the owner or an admin restores a version."""
    project_id = await copy_env.seed_carousel()
    async with copy_env.client_for(copy_env.owner) as client:
        await patch_copy(client, project_id, {"caption": EDITED_CAPTION})
    async with copy_env.client_for(copy_env.other) as client:
        refused = await _restore(client, project_id, 1, INITIAL_LOCK_VERSION + 1)

    assert refused.status_code == 403


@pytest.mark.asyncio
async def test_one_save_of_several_texts_versions_each(copy_env: CopyEnv) -> None:
    """Scenario: One save of several texts stores a version of each."""
    project_id = await copy_env.seed_carousel()
    async with copy_env.client_for(copy_env.owner) as client:
        saved = await patch_copy(
            client,
            project_id,
            {"caption": EDITED_CAPTION, "linkedin_post_pt": EDITED_LINKEDIN_PT},
        )
    assert saved.status_code == 200

    versions = await _owner_versions(copy_env, project_id)

    assert [(v["version_number"], v["field"], v["text"]) for v in versions] == [
        (4, "linkedin_post_pt", EDITED_LINKEDIN_PT),
        (3, "linkedin_post_pt", GENERATED_LINKEDIN_PT),
        (2, FIELD_CAPTION, EDITED_CAPTION),
        (1, FIELD_CAPTION, GENERATED_CAPTION),
    ]


@pytest.mark.asyncio
async def test_an_admin_can_restore(copy_env: CopyEnv) -> None:
    """Scenario: Only the owner or an admin restores a version."""
    project_id = await copy_env.seed_carousel()
    async with copy_env.client_for(copy_env.owner) as client:
        await patch_copy(client, project_id, {"caption": EDITED_CAPTION})
    async with copy_env.client_for(copy_env.admin) as client:
        restored = await _restore(client, project_id, 1, INITIAL_LOCK_VERSION + 1)

    assert restored.status_code == 200
    newest = (await _owner_versions(copy_env, project_id))[0]
    assert newest["author_id"] == str(copy_env.admin.id)


@pytest.mark.asyncio
async def test_restore_guards_of_the_save(copy_env: CopyEnv) -> None:
    """Scenario: A restore is refused when it cannot be applied."""
    project_id = await copy_env.seed_carousel()
    async with copy_env.client_for(copy_env.owner) as client:
        await patch_copy(client, project_id, {"caption": EDITED_CAPTION})
        without_if_match = await _restore(client, project_id, 1, None)
        unknown_carousel = await _restore(client, str(uuid4()), 1, 1)
    await _add_foreign_version(project_id)
    async with copy_env.client_for(copy_env.owner) as client:
        foreign = await _restore(client, project_id, 7, INITIAL_LOCK_VERSION + 1)
    await copy_env.set_project(project_id, {"phase_status": PHASE_STATUS_IN_PROGRESS})
    async with copy_env.client_for(copy_env.owner) as client:
        running = await _restore(client, project_id, 1, INITIAL_LOCK_VERSION + 1)

    assert without_if_match.status_code == 428
    assert unknown_carousel.status_code == 404
    assert foreign.status_code == 404
    assert running.status_code == 409
    assert running.json()["detail"] == CONFLICT_CODE_RUN_IN_PROGRESS
    assert (await saved_project(copy_env, project_id))["caption"] == EDITED_CAPTION


async def _refine_caption(project_id: str, text: str) -> None:
    """Rewrite the caption the way the chat refine does (repository write)."""
    from uuid import UUID

    from rag_backend.infrastructure.database.carousel_repository import (
        PostgresCarouselRepository,
    )
    from rag_backend.infrastructure.database.config import get_session_maker

    async with get_session_maker()() as session:
        repo = PostgresCarouselRepository(session)
        project = await repo.get_project_by_id(UUID(project_id))
        assert project is not None
        project.caption = text
        await repo.update_project(project)


@pytest.mark.asyncio
async def test_a_refined_caption_is_kept_before_the_next_edit(
    copy_env: CopyEnv,
) -> None:
    """Scenario: A text changed outside the editor is kept before the next edit."""
    project_id = await copy_env.seed_carousel()
    async with copy_env.client_for(copy_env.owner) as client:
        await patch_copy(client, project_id, {"caption": EDITED_CAPTION})
    await _refine_caption(project_id, REFINED_CAPTION)
    async with copy_env.client_for(copy_env.owner) as client:
        saved = await patch_copy(
            client,
            project_id,
            {"caption": SECOND_CAPTION},
            lock_version=INITIAL_LOCK_VERSION + 1,
        )
        assert saved.status_code == 200, saved.text
        versions = await _owner_versions(copy_env, project_id)
        restored = await _restore(client, project_id, 3, INITIAL_LOCK_VERSION + 2)

    assert [(v["version_number"], v["text"], v["author_id"]) for v in versions] == [
        (4, SECOND_CAPTION, str(copy_env.owner.id)),
        (3, REFINED_CAPTION, None),
        (2, EDITED_CAPTION, str(copy_env.owner.id)),
        (1, GENERATED_CAPTION, None),
    ]
    assert restored.status_code == 200
    assert restored.json()["caption"] == REFINED_CAPTION


@pytest.mark.asyncio
async def test_the_history_is_read_a_page_at_a_time(copy_env: CopyEnv) -> None:
    """Scenario: The history is read a page at a time."""
    project_id = await copy_env.seed_carousel()
    async with copy_env.client_for(copy_env.owner) as client:
        await patch_copy(client, project_id, {"caption": EDITED_CAPTION})
        await patch_copy(
            client,
            project_id,
            {"caption": SECOND_CAPTION},
            lock_version=INITIAL_LOCK_VERSION + 1,
        )
        first = await client.get(
            f"/api/carousels/{project_id}/copy/versions", params={"limit": 2}
        )
        cursor = first.json()["next_before"]
        second = await client.get(
            f"/api/carousels/{project_id}/copy/versions",
            params={"limit": 2, "before": cursor},
        )
        too_big = await client.get(
            f"/api/carousels/{project_id}/copy/versions", params={"limit": 201}
        )

    assert [v["version_number"] for v in first.json()["versions"]] == [3, 2]
    assert cursor == 2
    assert [v["version_number"] for v in second.json()["versions"]] == [1]
    assert second.json()["next_before"] is None
    assert too_big.status_code == 422


@pytest.mark.asyncio
async def test_restoring_the_current_text_changes_nothing(copy_env: CopyEnv) -> None:
    """Scenario: Restoring the current text changes nothing."""
    project_id = await copy_env.seed_carousel()
    async with copy_env.client_for(copy_env.owner) as client:
        await patch_copy(client, project_id, {"caption": EDITED_CAPTION})
        same = await _restore(client, project_id, 2, INITIAL_LOCK_VERSION + 1)
        after = await patch_copy(
            client,
            project_id,
            {"caption": SECOND_CAPTION},
            lock_version=INITIAL_LOCK_VERSION + 1,
        )

    assert same.status_code == 200
    assert same.json()["caption"] == EDITED_CAPTION
    assert same.json()["lock_version"] == INITIAL_LOCK_VERSION + 1
    assert after.status_code == 200
    assert [
        v["version_number"] for v in await _owner_versions(copy_env, project_id)
    ] == [
        3,
        2,
        1,
    ]
