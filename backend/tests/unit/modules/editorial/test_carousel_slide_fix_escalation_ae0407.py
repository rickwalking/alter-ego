"""The editorial facade builds the reasoning model only when needed.

Gherkin: tests/features/autofix_escalation_ae0407.feature
(Scenario "Escalation attempts 0 escalates after 3 attempts").
"""

from __future__ import annotations

import json

import pytest
from langchain_core.language_models import BaseChatModel
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.slide_fix import AUTOFIX_ESCALATION_ATTEMPTS
from rag_backend.domain.models.persona import PersonaProfile
from rag_backend.infrastructure.config.settings import Settings
from rag_backend.infrastructure.external import chat_model_factory
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
from tests.unit.llm_fakes_ae0391 import FakeChat

STILL_EMOJI = json.dumps({"pt": {"body": "O Argon resiste a ataques 🚀 hoje."}})


@pytest.mark.unit
@pytest.mark.asyncio
async def test_escalation_off_builds_only_the_fast_model(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = build_engine(FakeChatModel())
    project_id = await seed_gate(engine, db_session, GateSeed(breaks=(emoji_body_3,)))
    roles: list[str | None] = []

    def _build(settings: Settings, role: str | None = None) -> BaseChatModel:
        del settings
        roles.append(role)
        return FakeChat(reply=lambda _prompt: STILL_EMOJI)

    async def _no_persona(self: PovInputsAcl, project: str) -> PersonaProfile | None:
        del self, project
        return None

    monkeypatch.setattr(chat_model_factory, "build_chat_model", _build)
    monkeypatch.setattr(PovInputsAcl, "project_persona", _no_persona)
    report = await run_slide_fix(
        SlideFixRequest(
            session=db_session,
            project_id=project_id,
            expected_version=LOCK_VERSION,
            phase="content",
            engine=engine,
            escalation_attempts=0,
        )
    )
    assert roles == ["fast"]
    assert [a.model_role for a in report.attempts] == ["fast"] * 3
    assert report.slides[0].attempts == 3


def test_escalation_setting_defaults_to_two_and_allows_zero() -> None:
    field = Settings.model_fields["autopilot_autofix_escalation_attempts"]
    assert field.default == AUTOFIX_ESCALATION_ATTEMPTS == 2
    settings = Settings(autopilot_autofix_escalation_attempts=0)
    assert settings.autopilot_autofix_escalation_attempts == 0
    with pytest.raises(ValueError, match="greater than or equal to 0"):
        Settings(autopilot_autofix_escalation_attempts=-1)
