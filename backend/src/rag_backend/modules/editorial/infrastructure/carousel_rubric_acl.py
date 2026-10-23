"""The quality rubric of a carousel: choice at create, reads, scores, delete guard.

- ``rubric_for_create``: the rubric a new carousel stores. An explicit id must
  name a rubric applicable to carousels; without one the default carousel rubric
  (the oldest when several are flagged) is used, or none.
- ``project_rubric``: the carousel's rubric for drafting and scoring.
- ``replace_scores``: the carousel's single ``rubric_evaluation_scores`` row
  (a regeneration replaces it), committed; ``clear_scores`` removes it.
- ``carousels_using``: the carousels that reference a rubric (its delete guard).

The ORM models are imported lazily (the editorial facade loads while the ORM
registry is still initialising).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.carousel_rubric import (
    ERR_RUBRIC_NOT_FOR_CAROUSELS,
    ERR_RUBRIC_NOT_FOUND,
    RUBRIC_CONTENT_TYPE_CAROUSEL,
)
from rag_backend.domain.models.carousel_rubric import (
    CarouselRubric,
    CarouselRubricEvaluation,
)
from rag_backend.domain.models.rubric import RubricCriterion
from rag_backend.domain.rubric_scoring import normalize_criteria


class RubricChoiceError(ValueError):
    """The rubric asked for at create cannot be used (``str(error)`` is the code)."""


def _applies_to_carousels(content_types: object) -> bool:
    return isinstance(content_types, list) and (
        RUBRIC_CONTENT_TYPE_CAROUSEL in content_types
    )


def _criteria(raw: object) -> tuple[RubricCriterion, ...]:
    rows = raw if isinstance(raw, list) else []
    return tuple(normalize_criteria(cast("list[RubricCriterion]", rows)))


class CarouselRubricAcl:
    """Session-scoped rubric reads and writes for carousels."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def rubric_for_create(self, rubric_id: str | None) -> str | None:
        """The rubric id a new carousel stores; ``RubricChoiceError`` when invalid."""
        from rag_backend.infrastructure.database.models.persona_rubric import (
            QualityRubricModel,
        )

        if rubric_id is None:
            return await self._default_rubric_id()
        model = await self._session.get(QualityRubricModel, rubric_id)
        if model is None:
            raise RubricChoiceError(ERR_RUBRIC_NOT_FOUND)
        if not _applies_to_carousels(model.applicable_content_types):
            raise RubricChoiceError(ERR_RUBRIC_NOT_FOR_CAROUSELS)
        return str(model.id)

    async def _default_rubric_id(self) -> str | None:
        from rag_backend.infrastructure.database.models.persona_rubric import (
            QualityRubricModel,
        )

        rows = await self._session.execute(
            select(QualityRubricModel.id, QualityRubricModel.applicable_content_types)
            .where(QualityRubricModel.is_default.is_(True))
            .order_by(QualityRubricModel.created_at, QualityRubricModel.id)
        )
        for rubric_id, content_types in rows:
            if _applies_to_carousels(content_types):
                return str(rubric_id)
        return None

    async def project_rubric(self, project_id: str) -> CarouselRubric | None:
        """The carousel's rubric with its criteria, or ``None``."""
        from rag_backend.infrastructure.database.models.carousel import (
            CarouselProjectModel,
        )
        from rag_backend.infrastructure.database.models.persona_rubric import (
            QualityRubricModel,
        )

        row = (
            await self._session.execute(
                select(
                    QualityRubricModel.id,
                    QualityRubricModel.name,
                    QualityRubricModel.criteria,
                )
                .join(
                    CarouselProjectModel,
                    CarouselProjectModel.rubric_id == QualityRubricModel.id,
                )
                .where(CarouselProjectModel.id == project_id)
            )
        ).one_or_none()
        if row is None:
            return None
        rubric_id, name, criteria = row
        return CarouselRubric(
            id=str(rubric_id), name=str(name), criteria=_criteria(criteria)
        )

    async def clear_scores(self, project_id: str) -> None:
        """Remove the carousel's score row and commit."""
        from rag_backend.infrastructure.database.models.persona_rubric import (
            RubricEvaluationScoreModel,
        )

        await self._session.execute(
            delete(RubricEvaluationScoreModel).where(
                RubricEvaluationScoreModel.content_id == project_id,
                RubricEvaluationScoreModel.content_type
                == RUBRIC_CONTENT_TYPE_CAROUSEL,
            )
        )
        await self._session.commit()

    async def replace_scores(
        self, project_id: str, evaluation: CarouselRubricEvaluation
    ) -> None:
        """Store the carousel's evaluation as its only score row and commit."""
        from rag_backend.infrastructure.database.models.persona_rubric import (
            RubricEvaluationScoreModel,
        )

        await self._session.execute(
            delete(RubricEvaluationScoreModel).where(
                RubricEvaluationScoreModel.content_id == project_id,
                RubricEvaluationScoreModel.content_type == RUBRIC_CONTENT_TYPE_CAROUSEL,
            )
        )
        self._session.add(
            RubricEvaluationScoreModel(
                rubric_id=evaluation.rubric_id,
                content_id=project_id,
                content_type=RUBRIC_CONTENT_TYPE_CAROUSEL,
                evaluated_at=datetime.now(UTC),
                scores=evaluation.criterion_rows(),
                overall_score=evaluation.overall_score,
                passed=evaluation.passed,
                feedback=[evaluation.feedback] if evaluation.feedback else [],
            )
        )
        await self._session.commit()

    async def carousels_using(self, rubric_id: str) -> list[tuple[str, str]]:
        """``(id, topic)`` of every carousel that references the rubric."""
        from rag_backend.infrastructure.database.models.carousel import (
            CarouselProjectModel,
        )

        rows = await self._session.execute(
            select(CarouselProjectModel.id, CarouselProjectModel.topic)
            .where(CarouselProjectModel.rubric_id == rubric_id)
            .order_by(CarouselProjectModel.created_at)
        )
        return [(str(pid), str(topic or "")) for pid, topic in rows]


__all__ = ["CarouselRubricAcl", "RubricChoiceError"]
