"""The publish route answers a release that keeps losing its version race with 409.

Feature: backend/tests/features/approve_keeps_caption_ae0545.feature
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from rag_backend.domain.constants.carousel_workflow import (
    WORKFLOW_STATUS_APPROVED_FOR_PUBLISH,
)
from rag_backend.domain.constants.optimistic_locking import ERR_VERSION_CONFLICT
from rag_backend.domain.models import CarouselStatus, UserRole
from rag_backend.modules.publishing import LegacyPublishingAcl
from tests.integration.carousel_consolidation.helpers import (
    auth_header,
    create_carousel,
    create_minimal_carousel_artifacts,
    create_user,
    set_carousel_status,
    set_workflow_status,
)


async def _always_lost(_acl: LegacyPublishingAcl, _project_id: str) -> bool:
    return False


@pytest.mark.asyncio
async def test_a_lost_release_race_is_a_409(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Scenario: The public release never overwrites a caption edited after the load"""
    editor = await create_user("race-publish@example.com", UserRole.EDITOR)
    project_id = await create_carousel(editor, is_public=False)
    await create_minimal_carousel_artifacts(project_id)
    await set_workflow_status(project_id, WORKFLOW_STATUS_APPROVED_FOR_PUBLISH)
    await set_carousel_status(project_id, CarouselStatus.COMPLETED)
    monkeypatch.setattr(LegacyPublishingAcl, "_release_row", _always_lost)

    response = await client.post(
        f"/api/carousels/{project_id}/publish",
        headers=auth_header(editor),
    )

    assert response.status_code == 409
    assert response.json()["detail"] == ERR_VERSION_CONFLICT
