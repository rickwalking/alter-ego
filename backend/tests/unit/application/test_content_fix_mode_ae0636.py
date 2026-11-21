"""Which content revisions fix the blocked fields instead of re-drafting.

Gherkin: tests/features/content_fix_revision_ae0636.feature (section A outline,
the first-draft scenario) and section B (the repair loop limits).
"""

from __future__ import annotations

import pytest

from rag_backend.application.services.carousel.content_fix_mode import (
    is_fix_revision,
)
from rag_backend.application.services.carousel.content_gate_repair import (
    FieldRepairRequest,
    GateRepairCommand,
    run_gate_repair,
)
from rag_backend.domain.constants.content_gate_repair import (
    GATE_REPAIR_TIMEOUT_SECONDS,
)
from rag_backend.infrastructure.config.llm_routing_constants import (
    LLM_TIMEOUT_FALLBACK_SECONDS,
    LLM_TIMEOUT_FAST_SECONDS,
)
from tests.unit.application.content_gate_repair_fixtures_ae0430 import (
    POLICY_V4,
    PROD_ANSWERS,
    prod_slides,
)

_SYSTEM = "The owner asked to retry the content phase."
_OWNER = "Make slide 2 more concrete"
_BLOCKING_GATE = {
    "blocking": True,
    "violations": [
        {"code": "body_too_long", "slide_index": 2, "severity": "blocker"},
    ],
}
_SOURCES = {"autopilot": _SYSTEM, "human": _OWNER}


def _state(
    sources: list[str], *, blocking: bool = True, drafts: bool = True
) -> dict[str, object]:
    texts = [
        _SOURCES.get(source, f"legacy note {n}") for n, source in enumerate(sources)
    ]
    tagged = [
        {"note": _SOURCES[source], "source": source, "added_at": ""}
        for source in sources
        if source in _SOURCES
    ]
    return {
        "phase_feedback": {"content": texts},
        "phase_feedback_notes": {"content": tagged},
        "content_gate_validation": {**_BLOCKING_GATE, "blocking": blocking},
        "localized_slides": [{"slide_index": 2}],
        "slide_drafts": [{"slide_index": 2}] if drafts else [],
    }


@pytest.mark.unit
class TestIsFixRevision:
    @pytest.mark.parametrize(
        ("sources", "blocking", "fix"),
        [
            (["autopilot"], True, True),
            (["autopilot", "human"], True, False),
            (["human"], True, False),
            (["untagged"], True, False),
            (["autopilot"], False, False),
            ([], True, False),
        ],
    )
    def test_only_a_blocked_gate_with_system_notes_is_a_fix(
        self, sources: list[str], blocking: bool, fix: bool
    ) -> None:
        """Scenario Outline: Only a blocked gate with system notes is a fix"""
        assert is_fix_revision(_state(sources, blocking=blocking)) is fix

    def test_first_draft_is_never_a_fix(self) -> None:
        """Scenario: A first draft is never a fix"""
        assert is_fix_revision(_state(["autopilot"], drafts=False)) is False

    def test_no_stored_slides_is_never_a_fix(self) -> None:
        """Scenario: A first draft is never a fix"""
        state = {**_state(["autopilot"]), "localized_slides": []}
        assert is_fix_revision(state) is False

    def test_a_warning_only_gate_is_not_a_fix(self) -> None:
        """Scenario Outline: Only a blocked gate with system notes is a fix"""
        state = _state(["autopilot"])
        state["content_gate_validation"] = {
            "blocking": True,
            "violations": [{"slide_index": 2, "severity": "warning"}],
        }
        assert is_fix_revision(state) is False


class _FlakyRepairer:
    """Raises on the first round, answers from the prod table after."""

    def __init__(self) -> None:
        self.calls = 0

    async def repair(self, request: FieldRepairRequest) -> dict[str, str]:
        self.calls += 1
        if self.calls == 1:
            raise TimeoutError
        return {t.target_id: PROD_ANSWERS.get(t.target_id, "") for t in request.targets}


@pytest.mark.unit
class TestRepairLoopLimits:
    @pytest.mark.asyncio
    async def test_failed_round_does_not_end_the_loop(self) -> None:
        """Scenario: A failed repair round does not end the loop"""
        repairer = _FlakyRepairer()
        outcome = await run_gate_repair(
            GateRepairCommand(
                slides=prod_slides(), repairer=repairer, policy_version=POLICY_V4
            )
        )

        assert repairer.calls == 2
        assert outcome.report.blocking is False
        assert outcome.changed_indices

    def test_round_timeout_outlasts_fast_model_and_fallback(self) -> None:
        """Scenario: One repair round waits longer than the fast model and its fallback"""
        assert GATE_REPAIR_TIMEOUT_SECONDS > (
            LLM_TIMEOUT_FAST_SECONDS + LLM_TIMEOUT_FALLBACK_SECONDS
        )
