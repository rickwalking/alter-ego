"""The content phase's quality-rubric step: the carousel's rubric and its scores.

The rubric is read from the project row (like the content mode), so manual,
autopilot and resumed runs draft against the same criteria. Once the drafts
exist, the judge scores them (0-100 per criterion); the evaluation goes into the
workflow state's ``rubric_scores`` and replaces the carousel's score row. Drafts
that were not regenerated keep their scores. A judge that never answers usable
JSON (or times out) leaves the run going without scores; no rewrite pass.
"""

from __future__ import annotations

from dataclasses import dataclass

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.carousel_rubric import (
    LOG_EVENT_RUBRIC_SCORED,
    LOG_EVENT_RUBRIC_SCORING_FAILED,
    STATE_KEY_RUBRIC_SCORES,
)
from rag_backend.domain.models.carousel_rubric import (
    CarouselRubric,
    RubricJudgeRequest,
)
from rag_backend.domain.protocols.carousel_rubric import RubricJudge
from rag_backend.modules.editorial.public import CarouselRubricAcl

logger = structlog.get_logger(__name__)

_DRAFT_TEXT_KEY = "draft_text"
_SLIDE_INDEX_KEY = "slide_index"


@dataclass(frozen=True)
class RubricScoreInput:
    """The drafts to score, whether they are new, and the scores already held."""

    project_id: str
    rubric: CarouselRubric | None
    slide_drafts: object
    regenerated: bool
    has_scores: bool


def slides_text(slide_drafts: object) -> str:
    """The drafted slides as one text, slide by slide, for the judge."""
    if not isinstance(slide_drafts, list):
        return ""
    lines: list[str] = []
    for position, slide in enumerate(slide_drafts, start=1):
        if not isinstance(slide, dict):
            continue
        text = str(slide.get(_DRAFT_TEXT_KEY, "")).strip()
        if text:
            number = slide.get(_SLIDE_INDEX_KEY, position)
            lines.append(f"Slide {number}: {text}")
    return "\n\n".join(lines)


@dataclass(frozen=True)
class CarouselRubricStep:
    """Reads the carousel's rubric and scores its drafts against it."""

    db: AsyncSession | None
    judge: RubricJudge | None

    async def project_rubric(self, project_id: str) -> CarouselRubric | None:
        """The carousel's rubric, or ``None`` without a session or a rubric."""
        if self.db is None or not project_id:
            return None
        return await CarouselRubricAcl(self.db).project_rubric(project_id)

    async def score(self, request: RubricScoreInput) -> dict[str, object]:
        """``{"rubric_scores": ...}`` for new drafts, or no update."""
        rubric = request.rubric
        if rubric is None or self.judge is None or self.db is None:
            return {}
        if request.has_scores and not request.regenerated:
            return {}
        content = slides_text(request.slide_drafts)
        if not content:
            return {}
        try:
            evaluation = await self.judge.score(
                RubricJudgeRequest(
                    rubric=rubric, content=content, project_id=request.project_id
                )
            )
        except (ValueError, TimeoutError) as exc:
            logger.warning(
                LOG_EVENT_RUBRIC_SCORING_FAILED,
                project_id=request.project_id,
                rubric_id=rubric.id,
                error=str(exc),
            )
            return {}
        await CarouselRubricAcl(self.db).replace_scores(request.project_id, evaluation)
        logger.info(
            LOG_EVENT_RUBRIC_SCORED,
            project_id=request.project_id,
            rubric_id=rubric.id,
            overall_score=evaluation.overall_score,
            passed=evaluation.passed,
        )
        return {STATE_KEY_RUBRIC_SCORES: evaluation.to_state()}


__all__ = ["CarouselRubricStep", "RubricScoreInput", "slides_text"]
