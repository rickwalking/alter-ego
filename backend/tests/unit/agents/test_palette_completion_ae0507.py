"""The palette generator's chat model call carries the token cap and temperature.

Gherkin: tests/features/palette_generate_ae0507.feature
"""

from __future__ import annotations

import pytest

from rag_backend.agents.palette_prompts import PaletteCompletion
from rag_backend.domain.constants.palette_generation import (
    GENERATION_MAX_TOKENS,
    GENERATION_TEMPERATURE,
)
from rag_backend.infrastructure.config.llm_routing_constants import LLM_ROLE_FAST
from rag_backend.infrastructure.external.routed_chat_model import RoutedChatModel
from tests.unit.llm_fakes_ae0391 import CallLog, FakeChat


@pytest.mark.asyncio
async def test_the_routed_model_call_gets_the_cap() -> None:
    """Scenario: The model call carries the token cap and temperature."""
    log = CallLog()
    primary = FakeChat(reply=lambda prompt: f"answer to {prompt}", log=log)
    routed = RoutedChatModel(
        primary=primary, role=LLM_ROLE_FAST, timeout_seconds=5.0, attempts=1
    )

    answer = await PaletteCompletion(routed).complete("palette prompt")

    assert answer == "answer to palette prompt"
    assert log.kwargs == [
        {"max_tokens": GENERATION_MAX_TOKENS, "temperature": GENERATION_TEMPERATURE}
    ]
