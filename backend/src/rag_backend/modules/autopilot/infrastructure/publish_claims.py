"""SQLAlchemy adapter for ``PublishClaims`` (QA r1 H1).

Each claim is committed immediately so a concurrent session sees it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import cast
from uuid import UUID

from sqlalchemy import ColumnElement, CursorResult, and_, not_, or_, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.modules.autopilot.constants import CONTAINER_REUSE_HOURS
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.domain.publish_claims import (
    ManualClaim,
    ManualContainer,
    ManualRecord,
    RunClaim,
)
from rag_backend.modules.autopilot.infrastructure.models import (
    AutopilotRunModel,
    ManualPublishModel,
)
from rag_backend.modules.autopilot.recovery_constants import (
    MANUAL_STATE_PUBLISHED,
    MANUAL_STATE_PUBLISHING,
)


class SqlPublishClaims:
    """Compare-and-set claims on the run row and the manual ledger."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def claim_run(self, claim: RunClaim) -> bool:
        """CAS ``publish_claimed_at`` while publishing and unclaimed or stale.

        A stale claim is not taken over while a container younger than 24 hours
        has no post id: its status is unknown (QA r2 R4a).
        """
        claimed_at = AutopilotRunModel.publish_claimed_at
        model = AutopilotRunModel
        in_flight = _unknown_container(
            _ContainerColumns(
                container_id=model.ig_container_id.is_not(None),
                post_id=model.ig_post_id.is_(None),
                created_at=model.ig_container_created_at > _fresh_after(claim.now),
            )
        )
        result = await self._session.execute(
            update(AutopilotRunModel)
            .where(
                AutopilotRunModel.id == claim.run_id,
                AutopilotRunModel.state == AutopilotRunState.PUBLISHING.value,
                or_(
                    claimed_at.is_(None),
                    and_(claimed_at < claim.stale_before, not_(in_flight)),
                ),
            )
            .values(publish_claimed_at=claim.now)
        )
        won = cast(CursorResult[object], result).rowcount == 1
        await self._session.commit()
        return won

    async def release_run(self, run_id: UUID) -> None:
        """Clear the claim and commit."""
        await self._session.execute(
            update(AutopilotRunModel)
            .where(AutopilotRunModel.id == run_id)
            .values(publish_claimed_at=None)
        )
        await self._session.commit()

    async def manual_record(self, project_id: str) -> ManualRecord | None:
        """The ledger row, refreshed from the database."""
        row = await self._session.get(
            ManualPublishModel, project_id, populate_existing=True
        )
        if row is None:
            return None
        return ManualRecord(
            project_id=row.carousel_project_id,
            state=row.state,
            ig_post_id=row.ig_post_id,
            ig_permalink=row.ig_permalink,
            error=row.error,
            ig_container_id=row.ig_container_id,
            ig_container_created_at=row.ig_container_created_at,
        )

    async def claim_manual(self, claim: ManualClaim) -> bool:
        """Insert the ledger row, or take over a failed or stale one.

        A stale ``publishing`` row with a container younger than 24 hours and
        no post id is not taken over (QA r2 R4a).
        """
        if await self._insert(claim):
            return True
        row = ManualPublishModel
        in_flight = _unknown_container(
            _ContainerColumns(
                container_id=row.ig_container_id.is_not(None),
                post_id=row.ig_post_id.is_(None),
                created_at=row.ig_container_created_at > _fresh_after(claim.now),
            )
        )
        result = await self._session.execute(
            update(ManualPublishModel)
            .where(
                ManualPublishModel.carousel_project_id == claim.project_id,
                ManualPublishModel.state != MANUAL_STATE_PUBLISHED,
                or_(
                    ManualPublishModel.state != MANUAL_STATE_PUBLISHING,
                    and_(
                        ManualPublishModel.claimed_at < claim.stale_before,
                        not_(in_flight),
                    ),
                ),
            )
            .values(state=MANUAL_STATE_PUBLISHING, claimed_at=claim.now, error=None)
        )
        won = cast(CursorResult[object], result).rowcount == 1
        await self._session.commit()
        return won

    async def finish_manual(self, record: ManualRecord) -> None:
        """Store the outcome and commit."""
        await self._session.execute(
            update(ManualPublishModel)
            .where(ManualPublishModel.carousel_project_id == record.project_id)
            .values(
                state=record.state,
                ig_post_id=record.ig_post_id,
                ig_permalink=record.ig_permalink,
                error=record.error,
                ig_container_id=record.ig_container_id,
                ig_container_created_at=record.ig_container_created_at,
            )
        )
        await self._session.commit()

    async def save_manual_container(self, container: ManualContainer) -> None:
        """Store the container id before ``media_publish``, and commit."""
        await self._session.execute(
            update(ManualPublishModel)
            .where(ManualPublishModel.carousel_project_id == container.project_id)
            .values(
                ig_container_id=container.container_id,
                ig_container_created_at=container.created_at,
            )
        )
        await self._session.commit()

    async def _insert(self, claim: ManualClaim) -> bool:
        try:
            async with self._session.begin_nested():
                self._session.add(
                    ManualPublishModel(
                        carousel_project_id=claim.project_id,
                        state=MANUAL_STATE_PUBLISHING,
                        claimed_at=claim.now,
                    )
                )
                await self._session.flush()
        except IntegrityError:
            return False
        await self._session.commit()
        return True


@dataclass(frozen=True, kw_only=True)
class _ContainerColumns:
    """The three conditions of a container whose publish status is unknown."""

    container_id: ColumnElement[bool]
    post_id: ColumnElement[bool]
    created_at: ColumnElement[bool]


def _unknown_container(columns: _ContainerColumns) -> ColumnElement[bool]:
    return and_(columns.container_id, columns.post_id, columns.created_at)


def _fresh_after(now: datetime) -> datetime:
    return now - timedelta(hours=CONTAINER_REUSE_HOURS)
