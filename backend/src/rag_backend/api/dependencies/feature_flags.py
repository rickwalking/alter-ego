"""FastAPI dependencies for deployment-availability gating (DEPLOY-003).

Two flavors live here because both derive request-time availability from
``Settings``: boolean feature flags (DEPLOY-003) and the AE-0308 image-provider
key guard (a preset is only available when its provider has an API key).
"""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status

from rag_backend.api.schemas.carousel import CarouselProjectCreate
from rag_backend.domain.constants import ERR_IMAGE_PROVIDER_UNCONFIGURED
from rag_backend.domain.constants.feature_flags import (
    ERR_FEATURE_DISABLED,
    FLAG_CONTENT_CALENDAR,
    FLAG_EDITORIAL_WORKFLOW,
    FLAG_PALETTE_CATALOG,
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


def require_image_provider_configured(
    request: CarouselProjectCreate,
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    """Reject creation when the requested image provider has no API key (AE-0308).

    Fails fast with 422 BEFORE any workflow spend — the prod failure mode this
    guards against burned research/outline/content and a human design approval,
    then died at the images phase. Mirrors the AE-0215 startup guard's
    environment policy: production-like deployments reject, dev/test tolerate a
    missing key so local runs and stubbed tests keep working.
    """
    key = settings.image_provider_api_key(request.image_model)
    if key is not None and key.get_secret_value():
        return
    if not settings.is_production_like:
        return
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=ERR_IMAGE_PROVIDER_UNCONFIGURED.format(request.image_model),
    )


RequireEditorialWorkflow = Depends(require_feature(FLAG_EDITORIAL_WORKFLOW))
RequireQualityChecks = Depends(require_feature(FLAG_QUALITY_CHECKS))
RequireWorkflowBoard = Depends(require_feature(FLAG_WORKFLOW_BOARD))
RequireContentCalendar = Depends(require_feature(FLAG_CONTENT_CALENDAR))
RequirePaletteCatalog = Depends(require_feature(FLAG_PALETTE_CATALOG))

__all__ = [
    "RequireContentCalendar",
    "RequireEditorialWorkflow",
    "RequirePaletteCatalog",
    "RequireQualityChecks",
    "RequireWorkflowBoard",
    "require_feature",
    "require_image_provider_configured",
]
