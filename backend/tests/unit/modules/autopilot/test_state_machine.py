"""Domain state machine for autopilot runs.

Gherkin: tests/features/autopilot_state_machine.feature
The table below is the architecture §4 spec, duplicated so a missing edge
fails this test instead of passing a loop over the implementation.

_SPEC mirrors docs/architecture/grokbot-autopilot.md §4 plus later edges: a refused
editorial approve keeps the owner review open, a POV run waits for the owner's thesis,
the owner sets a publish time, and the owner moves a scheduled run to another day or
time.
"""

from __future__ import annotations

import pytest

from rag_backend.modules.autopilot.constants import EVENT_TYPE_STATE_CHANGED
from rag_backend.modules.autopilot.domain.exceptions import InvalidAutopilotTransition
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRunState,
    TransitionPair,
)
from rag_backend.modules.autopilot.domain.state_machine import (
    ALLOWED_TRANSITIONS,
    assert_allowed,
)

_S = AutopilotRunState

_SPEC: frozenset[tuple[AutopilotRunState, AutopilotRunState]] = frozenset({
    (_S.QUEUED, _S.GENERATING),
    (_S.QUEUED, _S.FAILED),
    (_S.GENERATING, _S.AWAITING_OWNER),
    (_S.GENERATING, _S.ESCALATED),
    (_S.GENERATING, _S.FAILED),
    (_S.AWAITING_OWNER, _S.PUBLISHING),
    (_S.AWAITING_OWNER, _S.REWORKING),
    (_S.AWAITING_OWNER, _S.REJECTED),
    (_S.AWAITING_OWNER, _S.EXPIRED),
    (_S.REWORKING, _S.AWAITING_OWNER),
    (_S.REWORKING, _S.ESCALATED),
    (_S.ESCALATED, _S.AWAITING_OWNER),
    (_S.ESCALATED, _S.REJECTED),
    (_S.PUBLISHING, _S.PUBLISHED),
    (_S.PUBLISHING, _S.PUBLISH_FAILED),
    (_S.PUBLISH_FAILED, _S.PUBLISHING),
    (_S.PUBLISHING, _S.AWAITING_OWNER),
    (_S.QUEUED, _S.AWAITING_THESIS),
    (_S.AWAITING_THESIS, _S.QUEUED),
    (_S.AWAITING_THESIS, _S.REJECTED),
    (_S.AWAITING_THESIS, _S.EXPIRED),
    (_S.AWAITING_OWNER, _S.SCHEDULED),
    (_S.SCHEDULED, _S.PUBLISHING),
    (_S.SCHEDULED, _S.AWAITING_OWNER),
    (_S.SCHEDULED, _S.EXPIRED),
    (_S.SCHEDULED, _S.SCHEDULED),
})

_ILLEGAL = (
    (_S.PUBLISHED, _S.GENERATING),
    (_S.QUEUED, _S.PUBLISHED),
    (_S.FAILED, _S.QUEUED),
    (_S.REJECTED, _S.PUBLISHING),
    (_S.EXPIRED, _S.AWAITING_OWNER),
    (_S.PUBLISHED, _S.PUBLISHED),
    (_S.SCHEDULED, _S.PUBLISHED),
    (_S.SCHEDULED, _S.REJECTED),
)


def test_allowed_transitions_match_architecture_section_4() -> None:
    """Every §4 edge is allowed, and no extra edge is."""
    assert ALLOWED_TRANSITIONS == _SPEC


def test_every_state_appears_in_the_table() -> None:
    """The enum and the table name the same set of states."""
    mentioned = {state for pair in _SPEC for state in pair}
    assert mentioned == set(AutopilotRunState)


@pytest.mark.parametrize(("expected", "new"), sorted(_SPEC))
def test_spec_pair_is_allowed(
    expected: AutopilotRunState, new: AutopilotRunState
) -> None:
    """Scenario: Allowed transition persists and emits an event (domain half)."""
    assert_allowed(TransitionPair(expected=expected, new=new))


@pytest.mark.parametrize(("expected", "new"), _ILLEGAL)
def test_illegal_pair_raises(
    expected: AutopilotRunState, new: AutopilotRunState
) -> None:
    """Scenario: Illegal transition is rejected (see autopilot_state_machine.feature)."""
    with pytest.raises(InvalidAutopilotTransition) as caught:
        assert_allowed(TransitionPair(expected=expected, new=new))
    assert caught.value.expected == expected
    assert caught.value.new == new


def test_queued_to_failed_is_allowed() -> None:
    """Three provider failures on start may fail a queued run."""
    assert_allowed(TransitionPair(expected=_S.QUEUED, new=_S.FAILED))


def test_state_changed_event_type_matches_the_spec() -> None:
    """The outbox event name is the one the feature file names."""
    assert EVENT_TYPE_STATE_CHANGED == "content.autopilot.state_changed"


def test_state_values_match_the_architecture_doc() -> None:
    """State spellings are the §4 table, not display labels."""
    assert AutopilotRunState.QUEUED.value == "queued"
    assert AutopilotRunState.GENERATING.value == "generating"
    assert AutopilotRunState.AWAITING_OWNER.value == "awaiting_owner"
    assert AutopilotRunState.REWORKING.value == "reworking"
    assert AutopilotRunState.ESCALATED.value == "escalated"
    assert AutopilotRunState.FAILED.value == "failed"
    assert AutopilotRunState.PUBLISHING.value == "publishing"
    assert AutopilotRunState.PUBLISHED.value == "published"
    assert AutopilotRunState.PUBLISH_FAILED.value == "publish_failed"
    assert AutopilotRunState.REJECTED.value == "rejected"
    assert AutopilotRunState.EXPIRED.value == "expired"
