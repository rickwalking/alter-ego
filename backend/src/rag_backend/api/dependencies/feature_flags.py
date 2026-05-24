"""FastAPI dependencies for feature flag gating (DEPLOY-003)."""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status

from rag_backend.domain.constants.feature_flags import (
    ERR_FEATURE_DISABLED,
    FLAG_CONTENT_CALENDAR,
    FLAG_EDITORIAL_WORKFLOW,
    FLAG_QUALITY_CHECKS,
    FLAG_WORKFLOW_BOARD,
)
from rag_backend.infrastructure.config.settings import Settings, get_settings


def _is_enabled(settings: Settings, flag: str) -> bool:
    flags = settings.feature_flags
    return bool(flags.get(flag, False))


def require_feature(flag: str) -> Callable[..., None]:
    """Return a dependency that rejects requests when a feature flag is disabled."""

    def _check(settings: Annotated[Settings, Depends(get_settings)]) -> None:
        if not _is_enabled(settings, flag):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=ERR_FEATURE_DISABLED,
            )

    return _check


RequireEditorialWorkflow = Depends(require_feature(FLAG_EDITORIAL_WORKFLOW))
RequireQualityChecks = Depends(require_feature(FLAG_QUALITY_CHECKS))
RequireWorkflowBoard = Depends(require_feature(FLAG_WORKFLOW_BOARD))
RequireContentCalendar = Depends(require_feature(FLAG_CONTENT_CALENDAR))

__all__ = [
    "RequireContentCalendar",
    "RequireEditorialWorkflow",
    "RequireQualityChecks",
    "RequireWorkflowBoard",
    "require_feature",
]
