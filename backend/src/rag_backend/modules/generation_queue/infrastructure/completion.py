"""Existing-stream completion refresh for settled generation runs."""

from __future__ import annotations

import structlog

from rag_backend.application.services.carousel.editorial_workflow_run_events import (
    publish_run_finished,
)
from rag_backend.domain.constants.carousel_run import (
    RUN_FINISHED_REASON_COMPLETED,
    RUN_FINISHED_REASON_FAILED,
)

logger = structlog.get_logger()
_LOG_REFRESH_FAILED = "generation_completion_refresh_failed"


class SseGenerationRunCompletion:
    """Publish the existing run-finished event without failing generation."""

    @staticmethod
    async def completed(project_id: str, *, succeeded: bool = True) -> None:
        reason = (
            RUN_FINISHED_REASON_COMPLETED if succeeded else RUN_FINISHED_REASON_FAILED
        )
        try:
            await publish_run_finished(project_id, reason)
        except Exception:
            logger.warning(_LOG_REFRESH_FAILED, project_id=project_id)


__all__ = ["SseGenerationRunCompletion"]
