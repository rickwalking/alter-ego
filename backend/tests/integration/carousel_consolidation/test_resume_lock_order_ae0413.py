"""A rejected structured feedback never bumps the lock version.

Gherkin: tests/features/content_gate_backend_ae0413.feature
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from rag_backend.api.routes.carousels import editorial_workflow as resume_route
from rag_backend.domain.constants.carousel_workflow import (
    ERR_EDITED_SLIDES_PHASE_NOT_ALLOWED,
    PHASE_OUTLINE,
    PHASE_STATUS_AWAITING_HUMAN,
)
from rag_backend.domain.models import UserRole
from tests.integration.carousel_consolidation.helpers import (
    auth_header,
    create_carousel,
    create_user,
    get_lock_version,
    seed_workflow_phase,
)

_EDITED_SLIDE = {
    "slide_index": 1,
    "slide_type": "intro",
    "presentation_pt": {"heading": "Titulo", "body": "Corpo."},
    "presentation_en": {"heading": "Title", "body": "Body."},
}


@pytest.mark.integration
class TestResumeLockOrder:
    @pytest.mark.asyncio
    async def test_rejected_edits_leave_the_lock_version_unchanged(
        self, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scenario: A rejected manual fix does not bump the lock version.

        The structured-feedback check runs before the lock compare-and-swap, so
        a 422 never even attempts the bump.
        """
        bump = AsyncMock(wraps=resume_route.bump_resume_lock_version)
        monkeypatch.setattr(resume_route, "bump_resume_lock_version", bump)
        editor = await create_user("lockorder@example.com", UserRole.EDITOR)
        project_id = await create_carousel(editor, is_public=False)
        await seed_workflow_phase(
            client,
            project_id,
            phase=PHASE_OUTLINE,
            phase_status=PHASE_STATUS_AWAITING_HUMAN,
        )
        version = await get_lock_version(project_id)

        response = await client.post(
            f"/api/carousels/{project_id}/workflow/resume",
            json={
                "action": "revise",
                "expected_version": version,
                "structured_feedback": {"edited_localized_slides": [_EDITED_SLIDE]},
            },
            headers=auth_header(editor),
        )

        assert response.status_code == 422
        assert response.json()["detail"] == ERR_EDITED_SLIDES_PHASE_NOT_ALLOWED
        assert await get_lock_version(project_id) == version
        bump.assert_not_awaited()
