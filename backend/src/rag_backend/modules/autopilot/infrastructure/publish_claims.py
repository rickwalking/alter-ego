"""SQLAlchemy adapter for ``PublishClaims`` (QA r1 H1).

Each claim is committed immediately so a concurrent session sees it.
"""

from __future__ import annotations

from typing import cast
from uuid import UUID

from sqlalchemy import CursorResult, or_, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.domain.publish_claims import (
    ManualClaim,
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
        """CAS ``publish_claimed_at`` while publishing and unclaimed or stale."""
        claimed_at = AutopilotRunModel.publish_claimed_at
        result = await self._session.execute(
            update(AutopilotRunModel)
            .where(
                AutopilotRunModel.id == claim.run_id,
                AutopilotRunModel.state == AutopilotRunState.PUBLISHING.value,
                or_(claimed_at.is_(None), claimed_at < claim.stale_before),
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
        )

    async def claim_manual(self, claim: ManualClaim) -> bool:
        """Insert the ledger row, or take over a failed or stale one."""
        if await self._insert(claim):
            return True
        result = await self._session.execute(
            update(ManualPublishModel)
            .where(
                ManualPublishModel.carousel_project_id == claim.project_id,
                ManualPublishModel.state != MANUAL_STATE_PUBLISHED,
                or_(
                    ManualPublishModel.state != MANUAL_STATE_PUBLISHING,
                    ManualPublishModel.claimed_at < claim.stale_before,
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
