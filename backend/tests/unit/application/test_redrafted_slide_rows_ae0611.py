"""The slide rows follow the fail-closed retry.

Gherkin: tests/features/redrafted_slide_en_copy_ae0611.feature
Real runner, real rows and real fail-closed chain; the
retry and the translation model are doubles, and a probe stands in for the gate
repair step to read the row at the moment that step starts.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TypeVar, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.carousel.carousel_repair_projection import (
    localized_from_slides,
)
from rag_backend.application.services.carousel.editorial_distribution_persist import (
    SlideDraftsContext,
    apply_slide_drafts_to_database,
)
from rag_backend.application.services.carousel.editorial_workflow_support import (
    EditorialWorkflowStartInput,
)
from rag_backend.application.services.carousel.localized_rows_sync import (
    sync_rows_to_localized,
)
from rag_backend.application.services.carousel.phase_artifact_runner import (
    PhaseArtifactRunner,
    PhaseArtifactRunnerConfig,
)
from rag_backend.application.services.carousel.presentation_review_pipeline import (
    validate_localized_slides,
)
from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
)
from rag_backend.domain.constants.carousel_presentation import (
    VIOLATION_TRANSLATION_SHAPE_MISMATCH,
)
from rag_backend.domain.constants.carousel_workflow import PHASE_CONTENT
from tests.unit.application.content_quality_fixtures_ae0366 import clean_drafts
from tests.unit.application.owner_autofix_fixtures_ae0367 import V3, rows, seed_carousel

T = TypeVar("T")

_SLIDE = 3
_PT = "presentation_pt"
_EN = "presentation_en"
_TRANSLATION = "translation_en"
_INSIGHT = "insight"
_KIND = "content_kind"
_UNPARSABLE = "## PT\n**Heading:**\n**Body:**\n## EN\n**Heading:**\n**Body:**\n"
_CARD = {"quote": "A synthetic quote.", "attribution": "A. Person"}
_OLD_HEADING_EN = "The old english heading"
_OLD_BODY_EN = "The old english body."
_NEW_HEADING_PT = "Regra nova para o time"
_NEW_BODY_PT = "Eu escrevo a regra nova antes de abrir o pedido."
_NEW_HEADING_EN = "A new rule for the team"
_NEW_BODY_EN = "I write the new rule before I open the request."
_ORIGINAL_HEADING_PT = "Cartão antigo"
_DISTRIBUTION = (
    "rag_backend.application.services.carousel.phase_artifact_runner."
    "build_editorial_distribution_updates"
)
_GATE_REPAIR = (
    "rag_backend.application.services.carousel.phase_artifact_runner."
    "repair_blocked_content_gate"
)
_CONTAINER = "rag_backend.infrastructure.container.get_container"


def _first_drafts() -> list[dict[str, object]]:
    """Valid drafts; the slide under test is plain PT and shows a quote card."""
    drafts = clean_drafts()
    for draft in drafts:
        if draft["slide_index"] != _SLIDE:
            continue
        del draft[_EN]
        pt = dict(cast(dict[str, object], draft[_PT]))
        pt.update(heading=_ORIGINAL_HEADING_PT, insight=dict(_CARD))
        pt.pop("features", None)
        draft[_PT] = pt
    return drafts


def _translations() -> dict[int, dict[str, object]]:
    return {
        _SLIDE: {
            "heading": _OLD_HEADING_EN,
            "body": _OLD_BODY_EN,
            _INSIGHT: dict(_CARD),
            _KIND: _INSIGHT,
        },
    }


def _blocked(draft: dict[str, object]) -> dict[str, object]:
    kept = {key: value for key, value in draft.items() if key not in (_PT, _EN)}
    return {**kept, "title": "", "draft_text": _UNPARSABLE}


def _review_drafts() -> list[dict[str, object]]:
    """The first drafts, with the slide under test blocking the first review."""
    return [
        _blocked(draft) if draft["slide_index"] == _SLIDE else draft
        for draft in _first_drafts()
    ]


def _distribution() -> dict[str, object]:
    """What the distribution step hands the review: this run's translations."""
    return {
        "translations_en": _translations(),
        "caption": "c",
        "blog_markdown": "b",
        "linkedin_post_pt": "p",
        "linkedin_post_en": "e",
    }


def _fresh() -> dict[str, object]:
    return {
        "slide_index": _SLIDE,
        "slide_type": "content",
        "title": _NEW_HEADING_PT,
        "draft_text": _NEW_BODY_PT,
    }


@dataclass
class _Answers:
    """The JSON caller of the translator: English for every slide it was sent."""

    calls: int = 0

    async def __call__(self, prompt: str, parse: Callable[[str], T]) -> T:
        self.calls += 1
        del prompt
        return parse(
            json.dumps({
                "slides_en": [
                    {
                        "slide_index": _SLIDE,
                        "heading": _NEW_HEADING_EN,
                        "body": _NEW_BODY_EN,
                    }
                ]
            })
        )


@dataclass
class _RepairProbe:
    """Stands in for the gate repair step and reads the row when it starts."""

    db: AsyncSession
    project_id: str
    seen: list[dict[str, object]] = field(default_factory=list)

    async def __call__(
        self, state: object, updates: object, context: object
    ) -> dict[str, object]:
        del state, updates, context
        row = next(
            r for r in await rows(self.db, self.project_id) if r.slide_number == _SLIDE
        )
        self.seen.append({"heading": row.heading, "extras": dict(row.extras or {})})
        return {}


async def _seed_first_rows(db: AsyncSession) -> str:
    project_id = await seed_carousel(db)
    drafts = _first_drafts()
    await apply_slide_drafts_to_database(
        SlideDraftsContext(
            db=db,
            project_id=project_id,
            outline=[{"slide_index": draft["slide_index"]} for draft in drafts],
            slide_drafts=drafts,
            translations_en=_translations(),
        )
    )
    return project_id


async def _run_content_phase(
    db: AsyncSession,
    project_id: str,
    fresh: dict[str, object] | None,
) -> tuple[_RepairProbe, _Answers]:
    """The content ensure of a deck whose slide 3 blocks the first review."""

    async def retry(slide_index: int) -> dict[str, object] | None:
        return fresh if slide_index == _SLIDE else None

    probe = _RepairProbe(db=db, project_id=project_id)
    answers = _Answers()
    runner = PhaseArtifactRunner(
        PhaseArtifactRunnerConfig(
            outline_agent=MagicMock(),
            content_agent=MagicMock(),
            llm=MagicMock(),
            db=db,
            workflow_input=EditorialWorkflowStartInput(
                topic="t", audience="a", brief="b", sources=[]
            ),
            slide_draft_retry=retry,
            translation_answers=answers,
        )
    )
    drafts = _review_drafts()
    state = {
        "project_id": project_id,
        "current_phase": PHASE_CONTENT,
        "presentation_policy_version": V3,
        "outline": [{"slide_index": draft["slide_index"]} for draft in drafts],
        "slide_drafts": drafts,
    }
    with (
        patch(_DISTRIBUTION, AsyncMock(return_value=_distribution())),
        patch(_CONTAINER, MagicMock()),
        patch(_GATE_REPAIR, probe),
    ):
        await runner.ensure_for_phase(cast(CarouselWorkflowState, state))
    return probe, answers


@pytest.mark.unit
@pytest.mark.asyncio
class TestRowsFollowTheRetry:
    async def test_the_row_is_new_before_the_gate_repair(
        self, db_session: AsyncSession
    ) -> None:
        """Scenario: The slide row follows the retry before the gate repair runs."""
        project_id = await _seed_first_rows(db_session)

        probe, answers = await _run_content_phase(db_session, project_id, _fresh())

        assert answers.calls == 1
        seen = probe.seen[0]
        extras = cast(dict[str, object], seen["extras"])
        translation = cast(dict[str, object], extras[_TRANSLATION])
        assert seen["heading"] == _NEW_HEADING_PT
        assert translation["heading"] == _NEW_HEADING_EN
        assert translation["body"] == _NEW_BODY_EN
        assert _INSIGHT not in extras
        assert _INSIGHT not in translation
        assert translation.get(_KIND) != _INSIGHT

    async def test_no_redraft_leaves_the_rows_alone(
        self, db_session: AsyncSession
    ) -> None:
        """Scenario: The rows are not rewritten when no slide was re-drafted."""
        project_id = await _seed_first_rows(db_session)

        probe, answers = await _run_content_phase(db_session, project_id, None)

        assert answers.calls == 0
        seen = probe.seen[0]
        extras = cast(dict[str, object], seen["extras"])
        assert seen["heading"] == _ORIGINAL_HEADING_PT
        assert _INSIGHT in extras


@pytest.mark.unit
@pytest.mark.asyncio
class TestRowContentKind:
    async def test_the_row_en_kind_follows_the_new_en(
        self, db_session: AsyncSession
    ) -> None:
        """Scenario: The row EN content kind follows the new EN copy."""
        project_id = await _seed_first_rows(db_session)
        localized = localized_from_slides(await rows(db_session, project_id))
        slide = next(s for s in localized if s["slide_index"] == _SLIDE)
        for key, heading in ((_PT, _NEW_HEADING_PT), (_EN, _NEW_HEADING_EN)):
            payload = dict(cast(dict[str, object], slide[key]))
            payload.pop(_INSIGHT, None)
            payload.pop(_KIND, None)
            payload["heading"] = heading
            slide[key] = payload

        await sync_rows_to_localized(
            db_session, project_id, {"localized_slides": localized}
        )

        row = next(
            r for r in await rows(db_session, project_id) if r.slide_number == _SLIDE
        )
        translation = cast(dict[str, object], (row.extras or {})[_TRANSLATION])
        assert translation.get(_KIND) != _INSIGHT
        rebuilt = localized_from_slides(await rows(db_session, project_id))
        report = validate_localized_slides(rebuilt, policy_version=V3)
        assert VIOLATION_TRANSLATION_SHAPE_MISMATCH not in {
            violation.code
            for violation in report.violations
            if violation.slide_index == _SLIDE
        }
