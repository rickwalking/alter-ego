"""AE-0392: repair-first content/design gate on the real editorial engine.

Real: the SQLite rows and lock version, ``EditorialWorkflowService`` with a
LangGraph checkpoint, the editorial facade, the owner autofix service (gate
repair), the autopilot snapshot, policy, feedback and runner. Fake: the chat
model (EN re-translate) and the resume (recorded, not run).

Gherkin: tests/features/autopilot_content_quality_gate_ae0392.feature
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import cast

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from structlog.testing import capture_logs

from rag_backend.application.services.carousel.editorial_workflow_service import (
    EditorialWorkflowService,
)
from rag_backend.domain.constants.carousel_workflow import PHASE_DESIGN
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.modules.autopilot.application.runner import (
    AutopilotRunner,
    RunnerDependencies,
)
from rag_backend.modules.autopilot.constants import REASON_FORBIDDEN
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.infrastructure.content_autofixer import (
    AutofixerConfig,
    InProcessContentAutofixer,
)
from rag_backend.modules.autopilot.quality_constants import (
    LOG_CONTENT_AUTOREPAIRED,
    REASON_CONTENT_QUALITY,
)
from rag_backend.modules.editorial.public import (
    REVIEW_ACTION_APPROVE,
    REVIEW_ACTION_REVISE,
)
from tests.unit.application.content_gate_fixtures_ae0392 import (
    EMOJI_BODY_3,
    FIXED_HEADING_5,
    FORBIDDEN_PHRASE,
    GateSeed,
    RealGate,
    emoji_body_3,
    empty_slide_4,
    lowercase_heading_5,
    seed_gate,
)
from tests.unit.application.owner_autofix_fixtures_ae0367 import (
    LOCK_VERSION,
    FakeChatModel,
    build_engine,
)
from tests.unit.modules.autopilot.project_inputs_fake import FakeProjectInputs
from tests.unit.modules.autopilot.test_autopilot_runner import _Recovery
from tests.unit.modules.autopilot.test_owner_actions import (
    _Notices,
    _Runs,
    _Topics,
    _world,
)


@dataclass
class _Flow:
    db: AsyncSession
    project_id: str
    llm: FakeChatModel
    engine: EditorialWorkflowService
    gate: RealGate
    runs: _Runs


async def _flow(db: AsyncSession, seed: GateSeed) -> _Flow:
    llm = FakeChatModel()
    engine = build_engine(llm)
    project_id = await seed_gate(engine, db, seed)
    base = _world()
    run = replace(
        base.runs.run,
        carousel_project_id=project_id,
        state=AutopilotRunState.GENERATING,
    )
    return _Flow(
        db=db,
        project_id=project_id,
        llm=llm,
        engine=engine,
        gate=RealGate(db=db, engine=engine),
        runs=_Runs(run=run),
    )


async def _tick(flow: _Flow, *, repair: bool = True) -> None:
    autofixer = InProcessContentAutofixer(
        AutofixerConfig(session=flow.db, engine_factory=lambda: flow.engine)
    )
    runner = AutopilotRunner(
        RunnerDependencies(
            runs=flow.runs,
            topics=_Topics(),
            editorial=flow.gate,
            notices=_Notices(),
            recovery=_Recovery(runs=flow.runs),
            owner_user_id="owner",
            inputs=FakeProjectInputs(),
            autofix=autofixer,
            gate_repair=autofixer if repair else None,
        )
    )
    await runner.tick()


async def _lock_version(flow: _Flow) -> int:
    version = await flow.db.scalar(
        select(CarouselProjectModel.lock_version).where(
            CarouselProjectModel.id == flow.project_id
        )
    )
    return int(version or 0)


async def _pt(flow: _Flow, index: int) -> dict[str, object]:
    state = await flow.engine.get_workflow_state(flow.project_id)
    assert state is not None
    slides = cast(list[dict[str, object]], state["localized_slides"])
    return cast(dict[str, object], slides[index - 1]["presentation_pt"])


def _only_resume(flow: _Flow) -> tuple[str, str]:
    assert len(flow.gate.resumes) == 1
    command = flow.gate.resumes[0]
    return command.action, command.feedback


@pytest.mark.unit
@pytest.mark.asyncio
class TestContentQualityGateFlow:
    """Scenarios of autopilot_content_quality_gate_ae0392.feature, real engine."""

    async def test_casing_only_is_repaired_and_approved(
        self, db_session: AsyncSession
    ) -> None:
        """Scenario: A casing-only violation is repaired and approved without a revise."""
        flow = await _flow(db_session, GateSeed(breaks=(lowercase_heading_5,)))
        with capture_logs() as logs:
            await _tick(flow)
        assert (await _pt(flow, 5))["heading"] == FIXED_HEADING_5
        action, feedback = _only_resume(flow)
        assert (action, feedback) == (REVIEW_ACTION_APPROVE, "")
        assert flow.gate.resumes[0].expected_version == LOCK_VERSION + 1
        repaired = [log for log in logs if log["event"] == LOG_CONTENT_AUTOREPAIRED]
        assert repaired[0]["fixed_rules"] == ["heading_not_sentence_case_pt"]
        assert repaired[0]["remaining_rules"] == []
        assert flow.llm.calls == 0
        state = await flow.engine.get_workflow_state(flow.project_id)
        assert state is not None
        assert state["content_gate_validation"] == {}
        assert state["revision_count"] == {"content": 0}

    async def test_empty_body_is_filled_and_approved(
        self, db_session: AsyncSession
    ) -> None:
        """Scenario: An empty body the repair can fill is approved."""
        flow = await _flow(db_session, GateSeed(breaks=(empty_slide_4,)))
        await _tick(flow)
        features = cast(list[dict[str, str]], (await _pt(flow, 4))["features"])
        assert [item["title"] for item in features] == [
            "Simulação Real2Sim",
            "Braços robóticos",
            "Parada segura",
        ]
        assert _only_resume(flow)[0] == REVIEW_ACTION_APPROVE
        assert flow.llm.calls == 1

    async def test_unrepairable_violation_gets_a_targeted_revise(
        self, db_session: AsyncSession
    ) -> None:
        """Scenario: A violation the repair cannot fix gets a targeted revise."""
        flow = await _flow(db_session, GateSeed(breaks=(emoji_body_3,)))
        await _tick(flow)
        action, feedback = _only_resume(flow)
        assert action == REVIEW_ACTION_REVISE
        assert f"Reason: {REASON_CONTENT_QUALITY}." in feedback
        assert "Measured: visible_emoji_forbidden@3." in feedback
        assert "slide 3 (pt body): visible_emoji_forbidden." in feedback
        assert EMOJI_BODY_3 in feedback
        assert "Fix only these slides" in feedback
        assert await _lock_version(flow) == LOCK_VERSION
        assert flow.gate.resumes[0].expected_version == LOCK_VERSION

    async def test_partial_repair_revises_only_what_is_left(
        self, db_session: AsyncSession
    ) -> None:
        """Scenario: Repairing part of the violations revises only what is left."""
        breaks = (lowercase_heading_5, emoji_body_3)
        flow = await _flow(db_session, GateSeed(breaks=breaks))
        await _tick(flow)
        assert (await _pt(flow, 5))["heading"] == FIXED_HEADING_5
        action, feedback = _only_resume(flow)
        assert action == REVIEW_ACTION_REVISE
        assert "slide 3" in feedback
        assert "slide 5" not in feedback
        assert "@5" not in feedback
        assert flow.gate.resumes[0].expected_version == LOCK_VERSION + 1

    async def test_design_gate_is_repaired_and_approved(
        self, db_session: AsyncSession
    ) -> None:
        """Scenario: The design gate gets the same treatment."""
        seed = GateSeed(breaks=(lowercase_heading_5,), phase=PHASE_DESIGN)
        flow = await _flow(db_session, seed)
        await _tick(flow)
        assert (await _pt(flow, 5))["heading"] == FIXED_HEADING_5
        assert _only_resume(flow)[0] == REVIEW_ACTION_APPROVE

    async def test_repair_runs_before_escalation_at_the_cap(
        self, db_session: AsyncSession
    ) -> None:
        """Scenario: Repair still runs before an escalation at the revision cap."""
        seed = GateSeed(breaks=(lowercase_heading_5,), revisions=2)
        flow = await _flow(db_session, seed)
        await _tick(flow)
        assert _only_resume(flow)[0] == REVIEW_ACTION_APPROVE
        assert flow.runs.run.state is AutopilotRunState.GENERATING

    async def test_forbidden_phrase_still_revises_without_repair(
        self, db_session: AsyncSession
    ) -> None:
        """Scenario: A real forbidden phrase still revises as forbidden_phrase."""
        flow = await _flow(db_session, GateSeed())
        flow.gate.forbidden_hits = (FORBIDDEN_PHRASE,)
        await _tick(flow)
        action, feedback = _only_resume(flow)
        assert action == REVIEW_ACTION_REVISE
        assert f"Reason: {REASON_FORBIDDEN}." in feedback
        assert f"Measured: {FORBIDDEN_PHRASE}." in feedback
        assert await _lock_version(flow) == LOCK_VERSION

    async def test_without_a_repairer_the_runner_revises(
        self, db_session: AsyncSession
    ) -> None:
        """Scenario: Without a gate repairer the runner revises as before."""
        flow = await _flow(db_session, GateSeed(breaks=(lowercase_heading_5,)))
        await _tick(flow, repair=False)
        action, feedback = _only_resume(flow)
        assert action == REVIEW_ACTION_REVISE
        assert "heading_not_sentence_case_pt@5" in feedback
