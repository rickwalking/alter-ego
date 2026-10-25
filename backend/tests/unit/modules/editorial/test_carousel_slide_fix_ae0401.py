"""The editorial facade of the slide fix (model, persona, report).

Gherkin: tests/features/autopilot_slide_autofix_ae0401.feature
"""

from __future__ import annotations

import json

import pytest
from langchain_core.language_models import BaseChatModel
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.carousel_autofix import AUTOFIX_STATUS_FIXED
from rag_backend.domain.models.persona import PersonaProfile
from rag_backend.infrastructure.config.settings import Settings
from rag_backend.infrastructure.external import chat_model_factory
from rag_backend.modules.editorial.infrastructure import carousel_slide_fix
from rag_backend.modules.editorial.infrastructure.carousel_slide_fix import (
    SlideFixRequest,
    run_slide_fix,
)
from rag_backend.modules.editorial.infrastructure.pov_inputs import PovInputsAcl
from tests.unit.application.content_gate_fixtures_ae0392 import (
    GateSeed,
    emoji_body_3,
    seed_gate,
)
from tests.unit.application.owner_autofix_fixtures_ae0367 import (
    LOCK_VERSION,
    FakeChatModel,
    build_engine,
)
from tests.unit.llm_fakes_ae0391 import CallLog, FakeChat

CLEAN = json.dumps({"pt": {"body": "O Argon resiste a ataques indiretos hoje."}})
SCORE = json.dumps({
    "tone_match": 90,
    "sentence_structure_match": 90,
    "opinion_strength": 90,
    "originality": 90,
    "human_authenticity": 90,
    "overall": 91,
})


def _reply(prompt: str) -> str:
    return SCORE if "Score how well the CONTENT" in prompt else CLEAN


@pytest.mark.unit
@pytest.mark.asyncio
class TestRunSlideFix:
    async def test_default_model_is_the_fast_role_and_persona_rescores(
        self, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The reasoning model is built for the escalation attempts."""
        engine = build_engine(FakeChatModel())
        project_id = await seed_gate(
            engine, db_session, GateSeed(breaks=(emoji_body_3,))
        )
        await engine.update_workflow_state(
            project_id, {"persona_scores": {"slide_3": {"overall": 75.0}}}
        )
        roles: list[str | None] = []
        log = CallLog()

        def _build(settings: Settings, role: str | None = None) -> BaseChatModel:
            del settings
            roles.append(role)
            return FakeChat(reply=_reply, log=log)

        async def _persona(self: PovInputsAcl, project: str) -> PersonaProfile:
            del self, project
            return PersonaProfile(name="Pedro", writing_samples=["Eu testo antes."])

        monkeypatch.setattr(chat_model_factory, "build_chat_model", _build)
        monkeypatch.setattr(PovInputsAcl, "project_persona", _persona)
        report = await run_slide_fix(
            SlideFixRequest(
                session=db_session,
                project_id=project_id,
                expected_version=LOCK_VERSION,
                phase="content",
                engine=engine,
            )
        )
        assert roles == ["fast", "reasoning"]
        assert report.status == AUTOFIX_STATUS_FIXED
        assert [(s.slide_index, s.fixed, s.attempts) for s in report.slides] == [
            (3, True, 1)
        ]
        assert [(a.attempt, a.outcome) for a in report.attempts] == [(1, "fixed")]
        assert len(log.models) == 2
        state = await engine.get_workflow_state(project_id)
        assert state is not None
        assert state["persona_scores"] == {"slide_3": {"overall": 91.0}}

    async def test_failing_slide_reports_its_text(
        self, db_session: AsyncSession
    ) -> None:
        engine = build_engine(FakeChatModel())
        project_id = await seed_gate(
            engine, db_session, GateSeed(breaks=(emoji_body_3,))
        )
        report = await run_slide_fix(
            SlideFixRequest(
                session=db_session,
                project_id=project_id,
                expected_version=LOCK_VERSION,
                phase="content",
                engine=engine,
                attempts=1,
                escalation_attempts=0,
                model_factory=lambda: FakeChat(reply=lambda _prompt: "no json"),
            )
        )
        assert report.slides[0].fixed is False
        assert report.slides[0].rules == ("visible_emoji_forbidden",)
        assert "🚀" in report.slides[0].text
        assert report.slides[0].attempts == 1


def test_persona_agent_style_guide_is_public() -> None:
    from rag_backend.agents.persona_agent import PersonaAgent

    agent = PersonaAgent(persona=PersonaProfile(name="Pedro"), llm=FakeChat())
    assert agent.style_guide() == agent._build_style_guide()


def test_slide_fix_attempts_setting_defaults_to_three() -> None:
    assert Settings.model_fields["autopilot_autofix_attempts"].default == 3
    assert carousel_slide_fix.AUTOFIX_MODEL_ATTEMPTS == 3
