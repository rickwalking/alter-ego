"""The Instagram route publishes a carousel still at final review.

Gherkin: tests/features/instagram_publish_from_final_review_ae0624.feature
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from rag_backend.domain.constants.carousel_workflow import (
    PHASE_CONTENT,
    PHASE_FINAL_REVIEW,
    PHASE_STATUS_AWAITING_HUMAN,
)
from rag_backend.domain.protocols import PublishResult
from tests.integration.test_publish_api import (
    SAVED_CAPTION,
    UNSAVED_CAPTION,
    _seed_completed_project,
    _test_settings,
    client_and_container,
)

_ROUTE_MODULE = "rag_backend.api.routes.carousels.publishing"
_PENDING_WORKFLOW = "draft"

__all__ = ["_test_settings", "client_and_container"]


async def _set_phase(project_id: str, phase: str) -> None:
    """Put the seeded project back before its approval, at ``phase``."""
    from sqlalchemy.ext.asyncio import async_sessionmaker

    import rag_backend.infrastructure.database.config as db_config
    from rag_backend.infrastructure.database.models.carousel import (
        CarouselProjectModel,
    )

    assert db_config.c_engine is not None
    session_factory = async_sessionmaker(db_config.c_engine, expire_on_commit=False)
    async with session_factory() as session:
        model = await session.get(CarouselProjectModel, project_id)
        assert model is not None
        model.workflow_status = _PENDING_WORKFLOW
        model.current_phase = phase
        model.phase_status = PHASE_STATUS_AWAITING_HUMAN
        await session.commit()


async def _seeded(client: AsyncClient, phase: str, monkeypatch) -> str:
    project_id = await _seed_completed_project(client)
    await _set_phase(project_id, phase)
    monkeypatch.setenv("CAROUSEL_PUBLIC_BASE_URL", "https://public.test")
    from rag_backend.infrastructure.config.settings import get_settings

    get_settings.cache_clear()
    return project_id


def _publisher(container) -> AsyncMock:
    fake = AsyncMock()
    fake.publish_instagram = AsyncMock(
        return_value=PublishResult(status="published", post_id="IG_final_review"),
    )
    container.instagram_publisher.override(fake)
    return fake


def _approval(monkeypatch, approved: bool) -> AsyncMock:
    approve = AsyncMock(return_value=approved)
    monkeypatch.setattr(f"{_ROUTE_MODULE}.approve_for_site_publish", approve)
    return approve


@pytest.mark.integration
class TestPublishFromFinalReview:
    # Scenario: A carousel at final review without an autopilot run is approved and published
    @pytest.mark.asyncio
    async def test_final_review_is_approved_then_published(
        self, client_and_container, monkeypatch
    ):
        client, container = client_and_container
        project_id = await _seeded(client, PHASE_FINAL_REVIEW, monkeypatch)
        approve = _approval(monkeypatch, approved=True)
        fake = _publisher(container)

        resp = await client.post(
            f"/api/carousels/{project_id}/publish/instagram", json={}
        )
        container.instagram_publisher.reset_override()

        assert resp.status_code == 200
        assert resp.json()["ig_post_id"] == "IG_final_review"
        assert approve.await_args.args[2] == project_id
        assert fake.publish_instagram.await_args.args[0] == SAVED_CAPTION

    # Scenario: A refused final-review approve publishes nothing
    @pytest.mark.asyncio
    async def test_refused_approve_publishes_nothing(
        self, client_and_container, monkeypatch
    ):
        client, container = client_and_container
        project_id = await _seeded(client, PHASE_FINAL_REVIEW, monkeypatch)
        _approval(monkeypatch, approved=False)
        fake = _publisher(container)

        resp = await client.post(
            f"/api/carousels/{project_id}/publish/instagram", json={}
        )
        container.instagram_publisher.reset_override()

        assert resp.status_code == 409
        assert resp.json()["detail"] == "final_review_approve_refused"
        assert fake.publish_instagram.await_count == 0

    # Scenario: The approve runs only after every other check passed
    @pytest.mark.asyncio
    async def test_unsaved_caption_is_refused_before_the_approve(
        self, client_and_container, monkeypatch
    ):
        client, container = client_and_container
        project_id = await _seeded(client, PHASE_FINAL_REVIEW, monkeypatch)
        approve = _approval(monkeypatch, approved=True)
        fake = _publisher(container)

        resp = await client.post(
            f"/api/carousels/{project_id}/publish/instagram",
            json={"caption": UNSAVED_CAPTION},
        )
        container.instagram_publisher.reset_override()

        assert resp.status_code == 409
        assert resp.json()["detail"] == "caption_not_saved"
        assert approve.await_count == 0
        assert fake.publish_instagram.await_count == 0

    # Scenario: A carousel before final review is still refused
    @pytest.mark.asyncio
    async def test_content_phase_is_refused(self, client_and_container, monkeypatch):
        client, container = client_and_container
        project_id = await _seeded(client, PHASE_CONTENT, monkeypatch)
        approve = _approval(monkeypatch, approved=True)
        fake = _publisher(container)

        resp = await client.post(
            f"/api/carousels/{project_id}/publish/instagram", json={}
        )
        container.instagram_publisher.reset_override()

        assert resp.status_code == 403
        assert resp.json()["detail"] == "workflow_not_approved_for_publish"
        assert approve.await_count == 0
        assert fake.publish_instagram.await_count == 0
