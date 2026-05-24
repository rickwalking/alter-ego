"""Admin API routes for Phase 5 data migration."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies.database import get_db
from rag_backend.api.dependencies.roles import AdminUser
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.application.services.phase5_migration_service import (
    Phase5MigrationReport,
    Phase5MigrationService,
)
from rag_backend.domain.constants.rate_limits import RATE_LIMIT_ADMIN_MIGRATION
from rag_backend.infrastructure.logging import get_logger

router = APIRouter(prefix="/admin/migration", tags=["admin"])
logger = get_logger()


class Phase5MigrationResponse(BaseModel):
    """Response body for Phase 5 migration run."""

    creative_briefs_updated: int
    persona_created: bool
    persona_id: str | None
    rubric_created: bool
    rubric_id: str | None
    workflow_states_updated: int
    projects_linked: int
    dry_run: bool
    errors: list[str] = Field(default_factory=list)


def _to_response(report: Phase5MigrationReport) -> Phase5MigrationResponse:
    return Phase5MigrationResponse(
        creative_briefs_updated=report.creative_briefs_updated,
        persona_created=report.persona_created,
        persona_id=report.persona_id,
        rubric_created=report.rubric_created,
        rubric_id=report.rubric_id,
        workflow_states_updated=report.workflow_states_updated,
        projects_linked=report.projects_linked,
        dry_run=report.dry_run,
        errors=report.errors,
    )


@router.post(
    "/phase5",
    response_model=Phase5MigrationResponse,
    summary="Run Phase 5 data migration (MIG-001-MIG-004)",
)
@limiter.limit(RATE_LIMIT_ADMIN_MIGRATION)
async def run_phase5_migration(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: AdminUser,
    dry_run: bool = Query(default=False, description="Preview changes without committing"),
) -> Phase5MigrationResponse:
    """Migrate legacy carousel projects to editorial workflow schema."""
    service = Phase5MigrationService()
    report = await service.run(db, dry_run=dry_run)
    logger.info(
        "phase5_migration_completed",
        admin_id=str(admin.id),
        dry_run=dry_run,
        creative_briefs=report.creative_briefs_updated,
        workflow_states=report.workflow_states_updated,
        projects_linked=report.projects_linked,
        persona_created=report.persona_created,
        rubric_created=report.rubric_created,
        error_count=len(report.errors),
    )
    return _to_response(report)
