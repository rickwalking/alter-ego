"""The content phase's quality-rubric step: the carousel's rubric and its scores.

The rubric is read from the project row (like the content mode), so manual,
autopilot and resumed runs draft against the same criteria. Once the drafts
exist, the judge scores them (0-100 per criterion) in one attempt under a hard
timeout; the evaluation goes into the workflow state's ``rubric_scores`` (with
the hash of the scored text) and replaces the carousel's score row. Drafts
whose text did not change are not scored again. Any judge failure (provider
error, timeout, unusable answer) is logged and the run goes on without scores,
clearing the scores of the drafts it replaced; no rewrite pass. The score rows
are only flushed: the phase's run commits its session.
"""

from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.carousel_rubric import (
    LOG_EVENT_RUBRIC_SCORED,
    LOG_EVENT_RUBRIC_SCORING_FAILED,
    LOG_EVENT_RUBRIC_SCORING_SKIPPED,
    RUBRIC_JUDGE_TIMEOUT_SECONDS,
    STATE_KEY_CONTENT_HASH,
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
    previous_scores: object = None


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


def content_hash(rubric: CarouselRubric, content: str) -> str:
    """What a score is for: the slides' text and the rubric version it used."""
    key = f"{rubric.id}:{rubric.version}\n{content}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def _previous(scores: object) -> dict[str, object]:
    return scores if isinstance(scores, dict) else {}


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
        previous = _previous(request.previous_scores)
        if previous and not request.regenerated:
            return {}
        content = slides_text(request.slide_drafts)
        if not content:
            return {}
        scored_for = content_hash(rubric, content)
        if previous.get(STATE_KEY_CONTENT_HASH) == scored_for:
            logger.info(LOG_EVENT_RUBRIC_SCORING_SKIPPED, project_id=request.project_id)
            return {}
        return await self._judge(request, rubric, (content, scored_for))

    async def _judge(
        self,
        request: RubricScoreInput,
        rubric: CarouselRubric,
        scored: tuple[str, str],
    ) -> dict[str, object]:
        """One judge call under the hard timeout; a failure keeps the run going."""
        content, scored_for = scored
        judge, db = self.judge, self.db
        if judge is None or db is None:
            return {}
        try:
            evaluation = await asyncio.wait_for(
                judge.score(
                    RubricJudgeRequest(
                        rubric=rubric, content=content, project_id=request.project_id
                    )
                ),
                timeout=RUBRIC_JUDGE_TIMEOUT_SECONDS,
            )
        except Exception as exc:
            logger.warning(
                LOG_EVENT_RUBRIC_SCORING_FAILED,
                project_id=request.project_id,
                rubric_id=rubric.id,
                error=type(exc).__name__,
            )
            return await self._drop_stale_scores(request)
        await CarouselRubricAcl(db).replace_scores(request.project_id, evaluation)
        logger.info(
            LOG_EVENT_RUBRIC_SCORED,
            project_id=request.project_id,
            rubric_id=rubric.id,
            overall_score=evaluation.overall_score,
            passed=evaluation.passed,
        )
        return {
            STATE_KEY_RUBRIC_SCORES: {
                **evaluation.to_state(),
                STATE_KEY_CONTENT_HASH: scored_for,
            }
        }

    async def _drop_stale_scores(self, request: RubricScoreInput) -> dict[str, object]:
        """After a failed re-score, the old scores belong to copy that is gone."""
        if self.db is None or not _previous(request.previous_scores):
            return {}
        await CarouselRubricAcl(self.db).clear_scores(request.project_id)
        return {STATE_KEY_RUBRIC_SCORES: {}}


__all__ = ["CarouselRubricStep", "RubricScoreInput", "content_hash", "slides_text"]
