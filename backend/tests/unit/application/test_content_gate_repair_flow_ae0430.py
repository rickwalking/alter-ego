"""AE-0430: the content ensure's use of the gate repair, and the model adapter.

Gherkin: tests/features/content_gate_repair_ae0430.feature (sections A and B).
"""

from __future__ import annotations

from typing import cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from rag_backend.application.services.carousel.content_feedback_lifecycle import (
    consume_feedback_notes,
)
from rag_backend.application.services.carousel.content_gate_repair import (
    FieldRepairRequest,
    LlmGateFieldRepairer,
    LlmGateRepairConfig,
    parse_fixes,
    render_field_repair_prompt,
)
from rag_backend.application.services.carousel.content_gate_repair_flow import (
    GateRepairContext,
    gate_violation_note,
    repair_blocked_content_gate,
    visible_copy_changed,
)
from rag_backend.application.services.carousel.content_gate_repair_targets import (
    FieldRepairTarget,
    field_budget,
)
from rag_backend.application.services.carousel.presentation_policy import (
    load_presentation_policy,
)
from rag_backend.application.services.carousel.presentation_policy_types import (
    TextBudget,
)
from rag_backend.domain.constants.content_feedback import (
    FEEDBACK_STATUS_UNCHANGED,
)
from rag_backend.domain.constants.content_gate_repair import (
    GATE_REVISION_NOTE_HEADER,
)
from tests.unit.application.content_gate_repair_fixtures_ae0430 import (
    POLICY_V4,
    FakeRepairer,
    load_fixture,
    prod_slides,
)

_TARGET = FieldRepairTarget(
    target_id="3:en:features[0].body",
    slide_index=3,
    locale="en",
    field="features[0].body",
    text="Browser, terminal and files live in its environment.",
    problems=("body_too_long: features[0].body exceeds max 100 characters (got 121)",),
    slide_heading="Ele não usa o seu notebook",
    source_text="Navegador, terminal e arquivos ficam no ambiente dele.",
    max_characters=100,
)


def _prod_state() -> dict[str, object]:
    fixture = load_fixture()
    return {
        "project_id": "5344b6c6-1d66-4b0e-9989-93f1316f8829",
        "presentation_policy_version": POLICY_V4,
        "localized_slides": prod_slides(),
        "content_gate_validation": fixture["content_gate_validation"],
        "presentation_validation": fixture["content_gate_validation"],
        "slide_drafts": [
            {"slide_index": index, "title": f"Slide {index}", "draft_text": "x"}
            for index in range(1, 8)
        ],
    }


@pytest.mark.unit
@pytest.mark.asyncio
class TestRepairBlockedContentGate:
    async def test_blocked_gate_is_repaired_and_written_back(self) -> None:
        """Scenario: The regression fixture from prod ends green (write-back)."""
        state = _prod_state()

        updates = await repair_blocked_content_gate(
            state, {}, GateRepairContext(repairer=FakeRepairer(), project_id="p")
        )

        assert updates["content_gate_validation"] == {}
        drafts = cast(list[dict[str, object]], updates["slide_drafts"])
        first = drafts[0]
        assert cast(dict[str, object], first["presentation_en"])["tldr_strip"]
        # Slides nobody repaired keep their draft fields.
        assert "presentation_en" not in drafts[1]

    async def test_no_repairer_or_passing_gate_does_nothing(self) -> None:
        """Scenario: Repair is off without a repairer or a blocking gate."""
        state = _prod_state()
        repairer = FakeRepairer()

        off = await repair_blocked_content_gate(state, {}, GateRepairContext(None))
        passing = await repair_blocked_content_gate(
            state, {"content_gate_validation": {}}, GateRepairContext(repairer)
        )
        empty = await repair_blocked_content_gate(
            state, {"localized_slides": []}, GateRepairContext(repairer)
        )

        assert off == {} and passing == {} and empty == {}
        assert repairer.calls == []

    async def test_failing_model_writes_nothing(self) -> None:
        """Scenario: A failing model leaves the copy and the report as they were."""
        state = _prod_state()
        slides = [s for s in prod_slides() if s["slide_index"] != 1]

        updates = await repair_blocked_content_gate(
            state,
            {"localized_slides": slides},
            GateRepairContext(FakeRepairer(fail=True)),
        )

        assert updates == {}


@pytest.mark.unit
class TestRevisionCarriesViolations:
    def test_note_lists_every_blocking_violation(self) -> None:
        """Scenario: A revision request carries the blocking violations."""
        note = gate_violation_note(_prod_state())

        assert note is not None
        lines = note.splitlines()
        assert lines[0] == GATE_REVISION_NOTE_HEADER
        assert len(lines) == 13
        assert (
            "- Slide 3 EN features[0].body: body_too_long: features[0].body exceeds "
            "max 100 characters (got 121)"
        ) in lines
        assert any(line.startswith("- Slide 1 PT+EN slide:") for line in lines)

    def test_no_note_without_blocking_violations(self) -> None:
        """Scenario: No violation note when the gate passes or has only warnings."""
        warning = {
            "blocking": True,
            "violations": [{"code": "x", "message": "m", "severity": "warning"}],
        }
        assert gate_violation_note({}) is None
        assert (
            gate_violation_note({"content_gate_validation": {"blocking": False}})
            is None
        )
        assert gate_violation_note({"content_gate_validation": warning}) is None
        assert (
            gate_violation_note({"content_gate_validation": {"blocking": True}}) is None
        )

    def test_unchanged_copy_settles_note_as_unchanged(self) -> None:
        """Scenario: A revision that changes nothing is not recorded as applied."""
        state = {**_prod_state(), "phase_feedback": {"content": ["Fix them"]}}
        same = {"localized_slides": prod_slides()}
        different = {"localized_slides": prod_slides()[1:]}

        assert visible_copy_changed(state, same) is False
        assert visible_copy_changed(state, different) is True
        assert visible_copy_changed(state, {}) is False
        updates = consume_feedback_notes(state, "content", FEEDBACK_STATUS_UNCHANGED)
        history = cast(
            dict[str, list[dict[str, object]]], updates["phase_feedback_history"]
        )
        assert history["content"][0]["status"] == FEEDBACK_STATUS_UNCHANGED


@pytest.mark.unit
@pytest.mark.asyncio
class TestLlmRepairer:
    async def test_one_call_with_the_fields_and_parsed_fixes(self) -> None:
        """Scenario: The request carries the current text, the limit and the slide heading."""
        llm = MagicMock()
        llm.ainvoke = AsyncMock(
            return_value=AIMessage(
                content='```json\n{"fixes": [{"id": "3:en:features[0].body", '
                '"text": " Short. "}, {"id": 4, "text": "x"}, "bad"]}\n```'
            )
        )
        config_calls: list[int] = []

        def runnable_config() -> RunnableConfig:
            config_calls.append(1)
            return RunnableConfig(tags=["t"])

        repairer = LlmGateFieldRepairer(
            LlmGateRepairConfig(llm=llm, runnable_config=runnable_config)
        )
        fixes = await repairer.repair(FieldRepairRequest((_TARGET,), "Voz direta."))

        assert fixes == {"3:en:features[0].body": "Short."}
        prompt = llm.ainvoke.await_args.args[0][0].content
        assert '"max_characters": 100' in prompt
        assert '"slide_heading": "Ele não usa o seu notebook"' in prompt
        assert "Voz direta." in prompt
        assert config_calls == [1]


@pytest.mark.unit
class TestPromptAndParse:
    def test_prompt_omits_absent_limits(self) -> None:
        """Scenario: A field without a budget carries no limit keys."""
        target = FieldRepairTarget(
            target_id="1:pt:tldr_strip",
            slide_index=1,
            locale="pt",
            field="tldr_strip",
            text="Resumo",
            problems=("p",),
        )
        prompt = render_field_repair_prompt(FieldRepairRequest((target,)))
        assert "max_characters" not in prompt.split("Fields:")[1].split("Rules")[0]
        assert "portuguese_source" not in prompt.split("Fields:")[1].split("Rules")[0]

    def test_unparseable_answer_raises(self) -> None:
        """Scenario: A non-JSON answer is a failed round (the loop catches it)."""
        with pytest.raises(TypeError):
            parse_fixes("no json here")
        with pytest.raises(TypeError):
            parse_fixes('{"fixes": "nope"}')


def _max(budget: TextBudget | None) -> int:
    assert budget is not None
    return budget.max_characters


@pytest.mark.unit
class TestFieldBudget:
    def test_budgets_match_the_validator(self) -> None:
        """Scenario: Each target carries the exact limit the validator enforces."""
        policy = load_presentation_policy(POLICY_V4)
        intro = {"slide_type": "intro"}
        content = {"slide_type": "content"}

        assert _max(field_budget(intro, "heading", policy)) == 72
        assert _max(field_budget(intro, "body", policy)) == 180
        assert _max(field_budget(content, "features[0].body", policy)) == 100
        assert _max(field_budget(content, "actions[1].title", policy)) == 30
        assert _max(field_budget(content, "summary_points[0].body", policy)) == 90
        assert field_budget(content, "tldr_strip", policy) is None
        assert field_budget(content, "stats[0].body", policy) is None
