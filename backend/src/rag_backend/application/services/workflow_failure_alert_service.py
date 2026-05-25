"""Workflow failure detection and alerting (MON-002)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.auth import ROLE_ADMIN
from rag_backend.domain.constants.carousel import CAROUSEL_STATUS_FAILED
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_PUBLISHED,
    PHASE_STATUS_REJECTED,
)
from rag_backend.domain.constants.notifications import (
    NOTIFICATION_STATUS_UNREAD,
)
from rag_backend.domain.constants.workflow_alerts import (
    ALERT_FAILURE_RATE_THRESHOLD,
    ALERT_FAILURE_WINDOW_HOURS,
    ALERT_LOG_EVENT,
    ALERT_REASON_TRUNCATE_LENGTH,
    ALERT_STUCK_WORKFLOW_HOURS,
    ALERT_TYPE_CAROUSEL_FAILED,
    ALERT_TYPE_HIGH_FAILURE_RATE,
    ALERT_TYPE_STUCK_WORKFLOW,
    ALERT_UNKNOWN_ERROR,
    NOTIFICATION_BODY_CAROUSEL_FAILED,
    NOTIFICATION_BODY_HIGH_FAILURE_RATE,
    NOTIFICATION_BODY_STUCK_WORKFLOW,
    NOTIFICATION_TITLE_WORKFLOW_FAILURE,
    NOTIFICATION_TYPE_WORKFLOW_FAILURE,
)
from rag_backend.domain.constants.workflow_validation import CONTENT_TYPE_CAROUSEL
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.infrastructure.database.models.notification import NotificationModel
from rag_backend.infrastructure.database.models.user import UserModel
from rag_backend.infrastructure.logging import get_logger

logger = get_logger()


class WorkflowFailureAlertService:
    """Detects workflow failures and emits structured alerts for monitoring."""

    async def check_and_alert(self, db: AsyncSession) -> int:
        """Run all workflow health checks; return count of alerts emitted."""
        alerts = 0
        alerts += await self._alert_failed_carousels(db)
        alerts += await self._alert_stuck_workflows(db)
        alerts += await self._alert_high_failure_rate(db)
        return alerts

    async def _has_recent_notification(
        self,
        db: AsyncSession,
        *,
        content_id: str | None,
        notification_type: str,
    ) -> bool:
        window_start = datetime.now(UTC) - timedelta(hours=ALERT_FAILURE_WINDOW_HOURS)
        query = select(NotificationModel.id).where(
            NotificationModel.notification_type == notification_type,
            NotificationModel.created_at >= window_start,
        )
        if content_id is not None:
            query = query.where(NotificationModel.content_id == content_id)
        result = await db.execute(query.limit(1))
        return result.scalar_one_or_none() is not None

    async def _alert_failed_carousels(self, db: AsyncSession) -> int:
        window_start = datetime.now(UTC) - timedelta(hours=ALERT_FAILURE_WINDOW_HOURS)
        result = await db.execute(
            select(CarouselProjectModel).where(
                CarouselProjectModel.status == CAROUSEL_STATUS_FAILED,
                CarouselProjectModel.updated_at >= window_start,
            )
        )
        failed = list(result.scalars().all())
        admin_ids = await self._admin_user_ids(db)
        count = 0
        for project in failed:
            project_id = str(project.id)
            if await self._has_recent_notification(
                db,
                content_id=project_id,
                notification_type=NOTIFICATION_TYPE_WORKFLOW_FAILURE,
            ):
                continue
            reason = project.error_message or ALERT_UNKNOWN_ERROR
            logger.error(
                ALERT_LOG_EVENT,
                alert_type=ALERT_TYPE_CAROUSEL_FAILED,
                project_id=project_id,
                reason=reason,
            )
            for admin_id in admin_ids:
                db.add(
                    NotificationModel(
                        user_id=admin_id,
                        notification_type=NOTIFICATION_TYPE_WORKFLOW_FAILURE,
                        title=NOTIFICATION_TITLE_WORKFLOW_FAILURE,
                        body=NOTIFICATION_BODY_CAROUSEL_FAILED.format(
                            project_id=project_id,
                            reason=reason[:ALERT_REASON_TRUNCATE_LENGTH],
                        ),
                        status=NOTIFICATION_STATUS_UNREAD,
                        content_id=project_id,
                        content_type=CONTENT_TYPE_CAROUSEL,
                    )
                )
            count += 1
        return count

    async def _alert_stuck_workflows(self, db: AsyncSession) -> int:
        cutoff = datetime.now(UTC) - timedelta(hours=ALERT_STUCK_WORKFLOW_HOURS)
        result = await db.execute(
            select(CarouselProjectModel).where(
                CarouselProjectModel.current_phase != PHASE_PUBLISHED,
                CarouselProjectModel.phase_status != PHASE_STATUS_REJECTED,
                CarouselProjectModel.updated_at <= cutoff,
            )
        )
        stuck = list(result.scalars().all())
        admin_ids = await self._admin_user_ids(db)
        count = 0
        for project in stuck:
            project_id = str(project.id)
            logger.warning(
                ALERT_LOG_EVENT,
                alert_type=ALERT_TYPE_STUCK_WORKFLOW,
                project_id=project_id,
                current_phase=project.current_phase,
                phase_status=project.phase_status,
                hours_stuck=ALERT_STUCK_WORKFLOW_HOURS,
            )
            if await self._has_recent_notification(
                db,
                content_id=project_id,
                notification_type=NOTIFICATION_TYPE_WORKFLOW_FAILURE,
            ):
                continue
            for admin_id in admin_ids:
                db.add(
                    NotificationModel(
                        user_id=admin_id,
                        notification_type=NOTIFICATION_TYPE_WORKFLOW_FAILURE,
                        title=NOTIFICATION_TITLE_WORKFLOW_FAILURE,
                        body=NOTIFICATION_BODY_STUCK_WORKFLOW.format(
                            project_id=project_id,
                            hours=ALERT_STUCK_WORKFLOW_HOURS,
                        ),
                        status=NOTIFICATION_STATUS_UNREAD,
                        content_id=project_id,
                        content_type=CONTENT_TYPE_CAROUSEL,
                    )
                )
            count += 1
        return count

    async def _alert_high_failure_rate(self, db: AsyncSession) -> int:
        if await self._has_recent_notification(
            db,
            content_id=None,
            notification_type=NOTIFICATION_TYPE_WORKFLOW_FAILURE,
        ):
            return 0
        window_start = datetime.now(UTC) - timedelta(hours=ALERT_FAILURE_WINDOW_HOURS)
        total_result = await db.execute(
            select(func.count())
            .select_from(CarouselProjectModel)
            .where(CarouselProjectModel.updated_at >= window_start)
        )
        failed_result = await db.execute(
            select(func.count())
            .select_from(CarouselProjectModel)
            .where(
                CarouselProjectModel.status == CAROUSEL_STATUS_FAILED,
                CarouselProjectModel.updated_at >= window_start,
            )
        )
        total = int(total_result.scalar_one())
        failed = int(failed_result.scalar_one())
        if total == 0:
            return 0
        rate = failed / total
        if rate <= ALERT_FAILURE_RATE_THRESHOLD:
            return 0
        logger.error(
            ALERT_LOG_EVENT,
            alert_type=ALERT_TYPE_HIGH_FAILURE_RATE,
            failure_rate=rate,
            failed_count=failed,
            total_count=total,
        )
        admin_ids = await self._admin_user_ids(db)
        for admin_id in admin_ids:
            db.add(
                NotificationModel(
                    user_id=admin_id,
                    notification_type=NOTIFICATION_TYPE_WORKFLOW_FAILURE,
                    title=NOTIFICATION_TITLE_WORKFLOW_FAILURE,
                    body=NOTIFICATION_BODY_HIGH_FAILURE_RATE.format(rate=rate),
                    status=NOTIFICATION_STATUS_UNREAD,
                )
            )
        return 1

    async def _admin_user_ids(self, db: AsyncSession) -> list[str]:
        result = await db.execute(
            select(UserModel.id).where(
                UserModel.role == ROLE_ADMIN, UserModel.is_active.is_(True)
            )
        )
        return [str(row) for row in result.scalars().all()]


__all__ = ["WorkflowFailureAlertService"]
