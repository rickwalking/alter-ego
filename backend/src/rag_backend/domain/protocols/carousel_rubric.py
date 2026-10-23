"""The judge that scores a carousel against its quality rubric."""

from __future__ import annotations

from typing import Protocol

from rag_backend.domain.models.carousel_rubric import (
    CarouselRubricEvaluation,
    RubricJudgeRequest,
)


class RubricJudge(Protocol):
    """Scores every criterion of a rubric on 0-100 for one carousel."""

    async def score(self, request: RubricJudgeRequest) -> CarouselRubricEvaluation:
        """The evaluation; raises ``ValueError`` when the answer never parses."""
        ...


__all__ = ["RubricJudge"]
