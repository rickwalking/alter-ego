"""Unit tests for BlogPostHideService.

Gherkin: tests/features/blog_no_carousel_slides_ae0422.feature

* Scenario: Every published carousel-origin post is hidden, regardless of body length
* Scenario: A published standalone post is not hidden
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.workflow_event_service import WorkflowEventService
from rag_backend.domain.constants.blog_post import BlogPostOrigin, BlogPostStatus
from rag_backend.domain.constants.workflow_events import (
    AGGREGATE_TYPE_BLOG_POST,
    EVENT_TYPE_BLOGPOST_STATUS_CHANGED,
)
from rag_backend.infrastructure.database.blog_post_hide import (
    HIDDEN_BAD_POST_KEY,
    BlogPostHideService,
    HideRun,
    is_hide_target,
)
from rag_backend.infrastructure.database.models.blog_post import BlogPostModel
from rag_backend.infrastructure.database.models.workflow_audit_log import (
    WorkflowAuditLogModel,
)
from rag_backend.infrastructure.events.memory_event_publisher import (
    MemoryEventPublisher,
)

# AE-0446: commits here would run the outbox relay on a foreign engine.
pytestmark = pytest.mark.usefixtures("no_outbox_relay")

_NOW = datetime(2026, 10, 18, 12, 0, 0, tzinfo=UTC)
_REASON = "AE-0422 AC6 test"
_RUN = HideRun(reason=_REASON, now=_NOW)


def _service() -> BlogPostHideService:
    return BlogPostHideService(WorkflowEventService(MemoryEventPublisher()))


async def _seed_post(
    db: AsyncSession,
    *,
    origin: BlogPostOrigin,
    status: BlogPostStatus,
    ai_generation_metadata: dict[str, object] | None = None,
    with_stamps: bool = False,
) -> str:
    post_id = str(uuid4())
    row = BlogPostModel.from_entity({
        "id": post_id,
        "origin": origin.value,
        "title": "Seed",
        "slug": f"seed-{post_id}",
        "status": status.value,
        "content": {"markdown": "# seed"},
        "ai_generation_metadata": ai_generation_metadata or {},
        "published_at": _NOW if with_stamps else None,
        "submitted_for_review_at": _NOW if with_stamps else None,
    })
    db.add(row)
    await db.flush()
    return post_id


async def _audit_events(db: AsyncSession, post_id: str) -> list[WorkflowAuditLogModel]:
    rows = await db.execute(
        select(WorkflowAuditLogModel).where(
            WorkflowAuditLogModel.aggregate_id == post_id
        )
    )
    return list(rows.scalars().all())


@pytest.mark.unit
class TestBlogPostHideService:
    async def test_hides_every_published_carousel_post(
        self, db_session: AsyncSession
    ) -> None:
        post_id = await _seed_post(
            db_session,
            origin=BlogPostOrigin.CAROUSEL,
            status=BlogPostStatus.PUBLISHED,
            with_stamps=True,
        )

        report = await _service().hide(db_session, _RUN)

        assert report.ids == [post_id]
        db_session.expire_all()
        row = await db_session.get(BlogPostModel, post_id)
        assert row is not None
        assert row.status == BlogPostStatus.DRAFT.value
        assert row.published_at is None
        assert row.submitted_for_review_at is None
        assert row.lock_version == 2
        assert row.ai_generation_metadata[HIDDEN_BAD_POST_KEY] == {
            "at": _NOW.isoformat(),
            "reason": _REASON,
        }
        events = await _audit_events(db_session, post_id)
        assert [e.event_type for e in events] == [EVENT_TYPE_BLOGPOST_STATUS_CHANGED]
        assert events[0].aggregate_type == AGGREGATE_TYPE_BLOG_POST

    async def test_rerun_is_a_noop(self, db_session: AsyncSession) -> None:
        await _seed_post(
            db_session,
            origin=BlogPostOrigin.CAROUSEL,
            status=BlogPostStatus.PUBLISHED,
        )
        service = _service()

        first = await service.hide(db_session, _RUN)
        second = await service.hide(db_session, _RUN)

        assert first.count == 1
        assert second.count == 0

    async def test_standalone_published_post_is_untouched(
        self, db_session: AsyncSession
    ) -> None:
        standalone_id = await _seed_post(
            db_session,
            origin=BlogPostOrigin.STANDALONE,
            status=BlogPostStatus.PUBLISHED,
        )

        report = await _service().hide(db_session, _RUN)

        assert report.ids == []
        assert await _audit_events(db_session, standalone_id) == []
        db_session.expire_all()
        row = await db_session.get(BlogPostModel, standalone_id)
        assert row is not None
        assert row.status == BlogPostStatus.PUBLISHED.value
        assert HIDDEN_BAD_POST_KEY not in row.ai_generation_metadata

    async def test_draft_carousel_post_is_not_touched(
        self, db_session: AsyncSession
    ) -> None:
        await _seed_post(
            db_session,
            origin=BlogPostOrigin.CAROUSEL,
            status=BlogPostStatus.DRAFT,
        )

        report = await _service().hide(db_session, _RUN)

        assert report.count == 0

    async def test_marker_preserves_existing_metadata(
        self, db_session: AsyncSession
    ) -> None:
        post_id = await _seed_post(
            db_session,
            origin=BlogPostOrigin.CAROUSEL,
            status=BlogPostStatus.PUBLISHED,
            ai_generation_metadata={"kept": {"x": 1}},
        )

        await _service().hide(db_session, _RUN)

        db_session.expire_all()
        row = await db_session.get(BlogPostModel, post_id)
        assert row is not None
        assert row.ai_generation_metadata["kept"] == {"x": 1}
        assert HIDDEN_BAD_POST_KEY in row.ai_generation_metadata

    async def test_preview_writes_nothing(self, db_session: AsyncSession) -> None:
        post_id = await _seed_post(
            db_session,
            origin=BlogPostOrigin.CAROUSEL,
            status=BlogPostStatus.PUBLISHED,
        )

        report = await _service().preview(db_session)

        assert report.ids == [post_id]
        assert await _audit_events(db_session, post_id) == []
        db_session.expire_all()
        row = await db_session.get(BlogPostModel, post_id)
        assert row is not None
        assert row.status == BlogPostStatus.PUBLISHED.value

    def test_is_hide_target_only_matches_published_carousel(self) -> None:
        def row(origin: str, status: str) -> BlogPostModel:
            return BlogPostModel.from_entity({
                "id": str(uuid4()),
                "origin": origin,
                "status": status,
            })

        assert is_hide_target(
            row(BlogPostOrigin.CAROUSEL.value, BlogPostStatus.PUBLISHED.value)
        )
        assert not is_hide_target(
            row(BlogPostOrigin.CAROUSEL.value, BlogPostStatus.DRAFT.value)
        )
        assert not is_hide_target(
            row(BlogPostOrigin.STANDALONE.value, BlogPostStatus.PUBLISHED.value)
        )


class TestHideLoggingUnderAppConfig:
    async def test_hide_logs_under_the_app_structlog_config(
        self, db_session: AsyncSession
    ) -> None:
        """Regression: a %-style log call raised "_proxy_to_logger() takes 2 to 3
        positional arguments" once the app had configured structlog, so the hide failed
        depending on test order.
        """
        import structlog

        from rag_backend.infrastructure.logging import setup_logging

        setup_logging(debug=False)
        try:
            await _seed_post(
                db_session,
                origin=BlogPostOrigin.CAROUSEL,
                status=BlogPostStatus.PUBLISHED,
                with_stamps=True,
            )
            report = await _service().hide(db_session, _RUN)
            assert len(report.ids) == 1
        finally:
            structlog.reset_defaults()
