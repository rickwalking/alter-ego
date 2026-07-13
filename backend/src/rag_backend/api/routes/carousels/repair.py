"""Deterministic carousel repair route (AE-0311).

Thin HTTP adapter: authenticate (owner or assigned reviewer), snapshot the row,
then run the bounded deterministic repair pipeline under the shared per-project
advisory lock via ``CarouselRepairService``. The service owns the two-commit
contract; typed 409 conflicts (``resume_already_in_progress`` while a run is
active, ``mutation_in_progress`` while another mutator holds the lock,
``version_conflict`` when a concurrent resume wins the CAS) propagate to the
app-wide carousel-conflict handler (AE-0316).

Read-gap contract: between the projection commit and the checkpoint write the
workflow-state fast path still serves the old stored report, so the response
carries the FRESH report and the client re-fetches workflow state after a 200.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from rag_backend.api.dependencies.carousel_access import (
    get_carousel_project_for_workflow_user,
)
from rag_backend.api.dependencies.roles import EditorUser
from rag_backend.api.routes.carousels.deps import (
    CarouselRepairRouteDeps,
    get_carousel_repair_route_deps,
)
from rag_backend.api.schemas.carousel_conflict import CarouselConflictResponse
from rag_backend.api.schemas.carousel_repair import (
    CarouselRepairResponse,
    RepairSlideDiffResponse,
)
from rag_backend.application.services.carousel.carousel_repair_service import (
    RepairCarouselCommand,
    RepairResult,
)
from rag_backend.domain.models.carousel_presentation import SlideValidationReport

router = APIRouter(tags=["carousels-repair"])


def _to_response(project_id: str, result: RepairResult) -> CarouselRepairResponse:
    """Map the service result onto the API response (fresh report included)."""
    return CarouselRepairResponse(
        project_id=project_id,
        status=result.status,
        repaired=[
            RepairSlideDiffResponse(
                slide_index=diff.slide_index,
                locale=diff.locale,
                repaired=diff.repaired,
                repaired_codes=list(diff.repaired_codes),
                remaining_codes=list(diff.remaining_codes),
            )
            for diff in result.diffs
        ],
        validation=SlideValidationReport.model_validate(result.report),
        needs_republish=result.needs_republish,
    )


@router.post(
    "/{project_id}/repair",
    response_model=CarouselRepairResponse,
    summary="Deterministically repair a carousel's localized slides",
    responses={
        status.HTTP_409_CONFLICT: {
            "description": (
                "Typed conflict: a workflow run is in progress, another mutator "
                "holds the project lock, or a concurrent resume won the CAS "
                "(AE-0311/AE-0316)."
            ),
            "model": CarouselConflictResponse,
        },
    },
)
async def repair_carousel(
    project_id: UUID,
    deps: Annotated[CarouselRepairRouteDeps, Depends(get_carousel_repair_route_deps)],
    current_user: EditorUser,
) -> CarouselRepairResponse:
    """Run the bounded deterministic repair and return per-slide diffs."""
    project = await get_carousel_project_for_workflow_user(
        deps.db, project_id, current_user
    )
    command = RepairCarouselCommand(
        project_id=str(project_id),
        status=str(project.status),
        phase_status=str(project.phase_status or ""),
        lock_version=int(project.lock_version or 1),
        policy_version=project.presentation_policy_version,
        actor_user_id=str(current_user.id),
    )
    result = await deps.service.repair(command)
    return _to_response(str(project_id), result)


__all__ = ["router"]
