"""An archived carousel is not auto-rejected, gets no reminder, and comes back when worked on."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.notification_service import NotificationService
from rag_backend.application.services.optimistic_lock_service import (
    CarouselVersionBumpParams,
    OptimisticLockService,
)
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_STATUS_FAILED,
    PHASE_STATUS_IN_PROGRESS,
)
from rag_backend.domain.constants.notifications import (
    NOTIFICATION_STATUS_UNREAD,
    NOTIFICATION_TYPE_REVIEW_REQUEST,
)
from rag_backend.domain.constants.workflow_validation import CONTENT_TYPE_CAROUSEL
from rag_backend.infrastructure.database.models import archive_where
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.infrastructure.database.models.notification import NotificationModel
from rag_backend.infrastructure.database.workflow_timeout_repository import (
    WorkflowTimeoutRepository,
)
from tests.unit.application.test_carousel_archive_ae0527 import (
    _archived,
    _project,
    session,
)

__all__ = ["session"]

_NOW = datetime.now(UTC)
_LONG_AGO = _NOW - timedelta(days=10)


@pytest.fixture
async def db(session: AsyncSession) -> AsyncIterator[AsyncSession]:
    yield session


async def _seed(db: AsyncSession, *, archived: bool, **fields: object) -> str:
    project = _project(_LONG_AGO, archived_at=_LONG_AGO if archived else None, **fields)
    db.add(project)
    await db.commit()
    return str(project.id)


@pytest.mark.asyncio
async def test_an_archived_carousel_is_not_auto_rejected(db: AsyncSession) -> None:
    """Scenario: An archived carousel raises no alerts"""
    archived = await _seed(db, archived=True)
    active = await _seed(db, archived=False)

    stuck = await WorkflowTimeoutRepository._find_stuck(db, _NOW - timedelta(hours=72))

    assert [str(project.id) for project in stuck] == [active]
    assert archived not in [str(project.id) for project in stuck]


@pytest.mark.asyncio
async def test_an_archived_carousel_gets_no_deadline_reminder(db: AsyncSession) -> None:
    """Scenario: An archived carousel raises no alerts"""
    archived = await _seed(db, archived=True)
    active = await _seed(db, archived=False)
    for content_id in (archived, active):
        db.add(
            NotificationModel(
                user_id="admin-id",
                notification_type=NOTIFICATION_TYPE_REVIEW_REQUEST,
                title="Review",
                status=NOTIFICATION_STATUS_UNREAD,
                content_id=content_id,
                content_type=CONTENT_TYPE_CAROUSEL,
                metadata_json={},
                deadline_at=_LONG_AGO,
            )
        )
    await db.commit()

    with patch.object(NotificationService, "_send_email", AsyncMock(return_value=True)):
        sent = await NotificationService().send_deadline_reminders(db)

    assert sent == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("phase_status", PHASE_STATUS_IN_PROGRESS),
        ("caption", "Edited caption"),
        ("lock_version", 99),
    ],
    ids=["run-starts", "caption-edit", "orm-lock-version-change"],
)
async def test_working_on_an_archived_carousel_restores_it(
    db: AsyncSession, field: str, value: object
) -> None:
    """Scenario: Working on an archived carousel brings it back to the board"""
    project_id = await _seed(db, archived=True)
    project = await db.get(CarouselProjectModel, project_id)
    assert project is not None

    setattr(project, field, value)
    await db.commit()

    assert not await _archived(db, project_id)


@pytest.mark.asyncio
async def test_bookkeeping_keeps_an_archived_carousel_archived(
    db: AsyncSession,
) -> None:
    """Scenario: Working on an archived carousel brings it back to the board"""
    project_id = await _seed(db, archived=True)
    project = await db.get(CarouselProjectModel, project_id)
    assert project is not None

    project.phase_status = PHASE_STATUS_FAILED
    project.error_message = "reaped"
    await db.commit()

    assert await _archived(db, project_id)


@pytest.mark.asyncio
async def test_archiving_and_editing_in_one_flush_stays_archived(
    db: AsyncSession,
) -> None:
    """Scenario: Working on an archived carousel brings it back to the board"""
    project_id = await _seed(db, archived=False)
    project = await db.get(CarouselProjectModel, project_id)
    assert project is not None

    project.archived_at = _NOW
    project.caption = "Last words"
    await db.commit()

    assert await _archived(db, project_id)


async def _archive_behind_the_session(db: AsyncSession, project_id: str) -> None:
    """Archive the row with a Core UPDATE the loaded ORM object does not see."""
    archived = await archive_where(
        db, [CarouselProjectModel.id == project_id], datetime.now(UTC)
    )
    assert archived == [project_id]


@pytest.mark.asyncio
async def test_an_edit_on_a_stale_object_still_restores_the_carousel(
    db: AsyncSession,
) -> None:
    """Scenario: An edit on a carousel archived after it was loaded restores it"""
    project_id = await _seed(db, archived=False)
    project = await db.get(CarouselProjectModel, project_id)
    assert project is not None
    await _archive_behind_the_session(db, project_id)
    assert project.archived_at is None

    project.caption = "Edited after the archive"
    await db.commit()

    assert not await _archived(db, project_id)


@pytest.mark.asyncio
async def test_the_lock_version_claim_restores_an_archived_carousel(
    db: AsyncSession,
) -> None:
    """Scenario: The run claim restores a carousel archived after it was loaded"""
    project_id = await _seed(db, archived=False)
    project = await db.get(CarouselProjectModel, project_id)
    assert project is not None
    await _archive_behind_the_session(db, project_id)

    new_version = await OptimisticLockService().bump_carousel_version(
        db, CarouselVersionBumpParams(project_id=project_id, expected_version=None)
    )
    await db.commit()

    assert new_version == 2
    assert not await _archived(db, project_id)
