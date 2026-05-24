"""API routes for quality rubric management."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies.database import get_db
from rag_backend.api.dependencies.roles import EditorUser
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.api.schemas.persona_rubric import (
    QualityRubricCreate,
    QualityRubricListResponse,
    QualityRubricResponse,
    QualityRubricUpdate,
    RubricEvaluationRequest,
    RubricEvaluationResponse,
)
from rag_backend.application.services.quality_evaluation_service import QualityEvaluationService
from rag_backend.domain.constants.rate_limits import RATE_LIMIT_AI_ENDPOINTS
from rag_backend.domain.models.rubric import QualityRubric
from rag_backend.infrastructure.container import get_container
from rag_backend.infrastructure.database.models import (
    QualityRubricModel,
    RubricEvaluationScoreModel,
)

MIN_PASSING_SCORE = 70.0

router = APIRouter(tags=["rubrics"])


def _to_domain_rubric(model: QualityRubricModel) -> QualityRubric:
    return QualityRubric(
        id=UUID(str(model.id)),
        name=model.name,
        description=model.description or "",
        criteria=model.criteria or [],
        applicable_content_types=model.applicable_content_types or [],
        is_default=model.is_default,
    )


def _build_quality_service() -> QualityEvaluationService:
    container = get_container()
    return QualityEvaluationService(llm=container.llm_service().chat_model)


@router.post(
    "/rubrics",
    response_model=QualityRubricResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create rubric",
)
async def create_rubric(
    data: QualityRubricCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> QualityRubricResponse:
    """Create a new quality rubric."""
    criteria_data = [c.model_dump() if hasattr(c, "model_dump") else c for c in data.criteria]
    rubric = QualityRubricModel(
        name=data.name,
        description=data.description,
        criteria=criteria_data,
        applicable_content_types=data.applicable_content_types,
        is_default=data.is_default,
    )
    db.add(rubric)
    await db.commit()
    await db.refresh(rubric)
    return rubric


@router.get(
    "/rubrics",
    response_model=QualityRubricListResponse,
    summary="List rubrics",
)
async def list_rubrics(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
    is_default: bool | None = Query(None),
) -> QualityRubricListResponse:
    """List all quality rubrics."""
    query = select(QualityRubricModel)

    if is_default is not None:
        query = query.where(QualityRubricModel.is_default == is_default)

    result = await db.execute(query)
    rubrics = result.scalars().all()
    return QualityRubricListResponse(items=list(rubrics), total=len(rubrics))


@router.get(
    "/rubrics/{rubric_id}",
    response_model=QualityRubricResponse,
    summary="Get rubric",
)
async def get_rubric(
    rubric_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> QualityRubricResponse:
    """Get a specific quality rubric."""
    rubric = await db.get(QualityRubricModel, str(rubric_id))
    if not rubric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rubric not found: {rubric_id}",
        )
    return rubric


@router.put(
    "/rubrics/{rubric_id}",
    response_model=QualityRubricResponse,
    summary="Update rubric",
)
async def update_rubric(
    rubric_id: UUID,
    data: QualityRubricUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> QualityRubricResponse:
    """Update a quality rubric."""
    rubric = await db.get(QualityRubricModel, str(rubric_id))
    if not rubric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rubric not found: {rubric_id}",
        )

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(rubric, key, value)

    await db.commit()
    await db.refresh(rubric)
    return rubric


@router.delete(
    "/rubrics/{rubric_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete rubric",
)
async def delete_rubric(
    rubric_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> None:
    """Delete a quality rubric."""
    rubric = await db.get(QualityRubricModel, str(rubric_id))
    if not rubric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rubric not found: {rubric_id}",
        )

    if rubric.is_default:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete default rubric. Create a new one first.",
        )

    await db.delete(rubric)
    await db.commit()


@router.post(
    "/rubrics/{rubric_id}/evaluate",
    response_model=RubricEvaluationResponse,
    summary="Evaluate content",
)
@limiter.limit(RATE_LIMIT_AI_ENDPOINTS)
async def evaluate_content(
    request: Request,
    rubric_id: UUID,
    body: RubricEvaluationRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> RubricEvaluationResponse:
    """Evaluate content against a rubric using QualityAgent."""
    rubric = await db.get(QualityRubricModel, str(rubric_id))
    if not rubric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rubric not found: {rubric_id}",
        )

    service = _build_quality_service()
    domain_rubric = _to_domain_rubric(rubric)
    evaluation_result = await service.evaluate_with_thresholds(
        rubric=domain_rubric,
        content=body.content_text,
        sources=body.sources or None,
        project_id=rubric_id,
        user_id=current_user.id,
        content_type=body.content_type,
    )

    criteria_scores = evaluation_result.get("criteria_scores", {})
    scores: dict[str, dict[str, object]] = {}
    if isinstance(criteria_scores, dict):
        for criterion_id, data in criteria_scores.items():
            if isinstance(data, dict):
                scores[str(criterion_id)] = {
                    "score": float(data.get("score", 0)),
                    "weight": float(data.get("weight", 0)),
                    "passed": bool(data.get("passed", False)),
                }

    overall_score = float(evaluation_result.get("overall_score", 0))
    passed = bool(evaluation_result.get("passed", overall_score >= MIN_PASSING_SCORE))
    feedback = evaluation_result.get("feedback", [])
    if not isinstance(feedback, list):
        feedback = []

    evaluation = RubricEvaluationScoreModel(
        rubric_id=rubric_id,
        content_id=UUID(int=0),
        content_type=body.content_type,
        scores=scores,
        overall_score=overall_score,
        passed=passed,
        feedback=feedback,
    )

    db.add(evaluation)
    await db.commit()
    await db.refresh(evaluation)

    return RubricEvaluationResponse(
        rubric_id=evaluation.rubric_id,
        content_id=evaluation.content_id,
        content_type=evaluation.content_type,
        evaluated_at=evaluation.evaluated_at,
        scores=evaluation.scores,
        overall_score=evaluation.overall_score,
        passed=evaluation.passed,
        feedback=evaluation.feedback,
    )
