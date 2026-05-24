"""API routes for quality rubric management."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies.database import get_db
from rag_backend.api.dependencies.roles import EditorUser
from rag_backend.api.schemas.persona_rubric import (
    QualityRubricCreate,
    QualityRubricListResponse,
    QualityRubricResponse,
    QualityRubricUpdate,
    RubricEvaluationResponse,
)
from rag_backend.infrastructure.database.models import (
    QualityRubricModel,
    RubricEvaluationScoreModel,
)

MIN_PASSING_SCORE = 0.7

router = APIRouter(tags=["rubrics"])


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
async def evaluate_content(
    rubric_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
    content_type: str = Query(...),
    content_text: str = Query(..., min_length=1),
) -> RubricEvaluationResponse:
    """Evaluate content against a rubric.

    Performs a basic deterministic evaluation based on content metrics.
    In production, this should be replaced with AI-powered evaluation.
    """
    rubric = await db.get(QualityRubricModel, str(rubric_id))
    if not rubric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rubric not found: {rubric_id}",
        )

    content_length = len(content_text)
    word_count = len(content_text.split())

    scores: dict[str, dict[str, object]] = {}
    overall_score = 0.0
    total_weight = 0.0

    for criterion in rubric.criteria:
        criterion_id = criterion.get("id", "unknown")
        weight = criterion.get("weight", 0.25)
        min_threshold = criterion.get("min_threshold", 0.7)

        # Basic deterministic scoring based on content metrics
        criterion_name = criterion.get("name", "").lower()
        if "length" in criterion_name or "size" in criterion_name:
            score = min(content_length / 1000, 1.0)
        elif "word" in criterion_name or "count" in criterion_name:
            score = min(word_count / 200, 1.0)
        else:
            score = 0.75  # Default moderate score

        passed = score >= min_threshold
        scores[criterion_id] = {
            "score": round(score * 100, 1),
            "weight": weight,
            "passed": passed,
        }
        overall_score += score * weight
        total_weight += weight

    if total_weight > 0:
        overall_score = overall_score / total_weight

    passed = overall_score >= MIN_PASSING_SCORE
    overall_score_normalized = round(overall_score * 100, 1)

    evaluation = RubricEvaluationScoreModel(
        rubric_id=rubric_id,
        content_id=UUID(int=0),
        content_type=content_type,
        scores=scores,
        overall_score=overall_score_normalized,
        passed=passed,
        feedback=[],
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
