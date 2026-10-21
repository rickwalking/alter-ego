"""Persona scores on one 0-100 scale, on every read path.

Read paths: the shared helper, the slide-fix targets (``slide_scores`` /
``select_targets``), the autopilot snapshot (``persona_score``) and the
engine's content-approve check (``validate_content_approve_persona_score``).

Gherkin: tests/features/autofix_escalation_ae0407.feature
(Scenario Outline "A stored overall is read on the 0-100 scale",
Scenario "An unscored slide is not a low voice score").

_READS is the Examples table: (stored overall, what every read path reads).
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import cast

import pytest

from rag_backend.application.services.carousel.editorial_workflow_service_helpers import (
    validate_content_approve_persona_score,
)
from rag_backend.application.services.carousel.slide_fix_targets import (
    TargetQuery,
    select_targets,
    slide_scores,
)
from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
)
from rag_backend.domain.constants.carousel_workflow import ERR_PERSONA_SCORE_TOO_LOW
from rag_backend.domain.persona_score import (
    lowest_overall,
    on_hundred_scale,
    stored_overall,
)
from rag_backend.modules.autopilot.domain.gate import GateAction, SnapshotParts
from rag_backend.modules.autopilot.domain.policy import decide
from rag_backend.modules.autopilot.domain.snapshot import assemble_snapshot
from tests.unit.application.copy_hygiene_fixtures_ae0401 import POV, prod_deck

pytestmark = pytest.mark.unit

_SLIDES = 9
_READS: list[tuple[object, float | None]] = [
    (8.7, 87.0),
    (75, 75.0),
    (0.0, None),
    ("bad", None),
]


def _state(scores: Mapping[str, object]) -> dict[str, object]:
    return {
        "current_phase": "content",
        "phase_status": "awaiting_human",
        "slide_drafts": [{"draft_text": f"Draft {i}"} for i in range(_SLIDES)],
        "persona_scores": dict(scores),
    }


def _snapshot_score(state: Mapping[str, object]) -> float | None:
    snapshot = assemble_snapshot(
        SnapshotParts(
            state=state, images=(), slides_total=_SLIDES, lock_version=1, stale=False
        )
    )
    return snapshot.persona_score


def _engine_allows(state: Mapping[str, object]) -> bool:
    try:
        validate_content_approve_persona_score(cast(CarouselWorkflowState, dict(state)))
    except ValueError as exc:
        assert str(exc) == ERR_PERSONA_SCORE_TOO_LOW
        return False
    return True


# Scenario Outline: A stored overall is read on the 0-100 scale
@pytest.mark.parametrize(("stored", "read"), _READS)
def test_the_helper_reads_the_hundred_point_scale(
    stored: object, read: float | None
) -> None:
    assert stored_overall({"overall": stored}) == read
    assert stored_overall(stored) == read


@pytest.mark.parametrize(("stored", "read"), _READS)
def test_slide_fix_targets_read_the_hundred_point_scale(
    stored: object, read: float | None
) -> None:
    scores = slide_scores({"persona_scores": {"slide_1": {"overall": stored}}})
    assert scores.get(1) == read


@pytest.mark.parametrize(("stored", "read"), _READS)
def test_the_snapshot_reads_the_hundred_point_scale(
    stored: object, read: float | None
) -> None:
    assert _snapshot_score(_state({"slide_1": {"overall": stored}})) == read


@pytest.mark.parametrize(("stored", "read"), _READS)
def test_the_engine_check_reads_the_hundred_point_scale(
    stored: object, read: float | None
) -> None:
    """87, 75 and unscored all clear the 70 floor."""
    del read
    assert _engine_allows(_state({"slide_1": {"overall": stored}}))


@pytest.mark.parametrize("stored", [6.5, 65])
def test_a_low_score_on_either_scale_is_low_everywhere(stored: float) -> None:
    state = _state({"slide_1": {"overall": stored}, "slide_2": {"overall": 80}})
    assert _snapshot_score(state) == 65.0
    assert slide_scores(state) == {1: 65.0, 2: 80.0}
    assert not _engine_allows(state)
    assert (
        decide(
            assemble_snapshot(
                SnapshotParts(
                    state=state,
                    images=(),
                    slides_total=_SLIDES,
                    lock_version=1,
                    stale=False,
                )
            )
        ).action
        is not GateAction.APPROVE
    )


def test_an_unscored_slide_is_not_a_low_voice_score() -> None:
    """Scenario: An unscored slide is not a low voice score."""
    scores = {f"slide_{n}": {"overall": 80} for n in range(2, _SLIDES + 1)}
    state = _state({"slide_1": {"overall": 0.0}, **scores})
    assert _snapshot_score(state) == 80.0
    assert _engine_allows(state)
    selection = select_targets(
        TargetQuery(
            records=prod_deck(),
            state=state,
            policy_version=POV,
            phase="content",
            voice_floor=70.0,
        )
    )
    assert 1 not in [target.slide_index for target in selection.targets]


def test_lowest_overall_edges() -> None:
    assert lowest_overall("bad") is None
    assert lowest_overall({}) is None
    assert lowest_overall({"a": {"overall": 0}, "b": True}) is None
    assert lowest_overall({"a": 9.1, "b": {"overall": 72}}) == 72.0


@pytest.mark.parametrize(
    ("value", "scaled"),
    [(10.0, 100.0), (10.5, 10.5), (0.1, 1.0), (0.0, 0.0), (-3.0, -3.0), (95.0, 95.0)],
)
def test_on_hundred_scale_bounds(value: float, scaled: float) -> None:
    assert on_hundred_scale(value) == pytest.approx(scaled)


def test_nan_and_negative_are_unscored() -> None:
    assert stored_overall(math.nan) is None
    assert stored_overall({"overall": -5}) is None
    assert stored_overall({"tone_match": 80}) is None
