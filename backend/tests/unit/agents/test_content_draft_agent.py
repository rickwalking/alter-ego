"""Unit tests for ContentDraftAgent."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rag_backend.agents.content_draft_agent import ContentDraftAgent
from rag_backend.domain.models.persona import PersonaProfile
from rag_backend.infrastructure.cache.ai_response_cache import get_ai_response_cache
from rag_backend.infrastructure.config.llm_routing_constants import (
    LLM_ATTEMPTS_PER_MODEL,
)


class TestContentDraftAgent:
    @pytest.fixture(autouse=True)
    def clear_cache(self) -> None:
        get_ai_response_cache().clear()

    @pytest.fixture
    def mock_llm(self) -> AsyncMock:
        """draft_slide binds the model config, so .bind must return a runnable whose
        ainvoke is the configured mock (not an auto-created async child).
        """
        llm = AsyncMock()
        llm.bind = MagicMock(return_value=llm)
        return llm

    @pytest.fixture
    def agent(self, mock_llm: AsyncMock) -> ContentDraftAgent:
        return ContentDraftAgent(llm=mock_llm)

    async def test_draft_slide_returns_parsed_fields(
        self, agent: ContentDraftAgent, mock_llm: AsyncMock
    ) -> None:
        payload = {
            "draft_text": "Slide copy",
            "confidence_score": 0.9,
            "sources_used": ["source-1"],
        }
        mock_llm.ainvoke.return_value = MagicMock(content=json.dumps(payload))

        result = await agent.draft_slide(1, "Title", ["Point"])

        assert result["draft_text"] == "Slide copy"
        assert result["confidence_score"] == 0.9

    async def test_draft_slide_with_persona_enforces_voice(
        self, agent: ContentDraftAgent, mock_llm: AsyncMock
    ) -> None:
        draft_payload = {
            "draft_text": "Raw copy",
            "confidence_score": 0.8,
            "sources_used": [],
        }
        mock_llm.ainvoke.side_effect = [
            MagicMock(content=json.dumps(draft_payload)),
            MagicMock(content="Persona-enforced copy"),
        ]
        persona = PersonaProfile(name="Pedro")

        result = await agent.draft_slide(1, "Title", ["Point"], persona=persona)

        assert result["draft_text"] == "Persona-enforced copy"
        assert mock_llm.ainvoke.call_count == 2

    async def test_draft_slide_binds_v4_model_config(
        self, agent: ContentDraftAgent, mock_llm: AsyncMock
    ) -> None:
        """The v4 YAML model block reaches the LLM via .bind (not discarded)."""
        mock_llm.ainvoke.return_value = MagicMock(
            content=json.dumps({
                "draft_text": "c",
                "confidence_score": 0.5,
                "sources_used": [],
            })
        )

        await agent.draft_slide(1, "Title", ["Point"])

        bind_kwargs = mock_llm.bind.call_args.kwargs
        assert bind_kwargs["temperature"] == 0.7
        assert bind_kwargs["max_tokens"] == 32000

    async def test_draft_slide_threads_sibling_and_previous_draft_once(
        self, agent: ContentDraftAgent, mock_llm: AsyncMock
    ) -> None:
        """Sibling context + previous draft + a single imperative revision
        block reach the prompt; reviewer notes are NOT rendered twice."""
        mock_llm.ainvoke.return_value = MagicMock(
            content=json.dumps({
                "draft_text": "c",
                "confidence_score": 0.5,
                "sources_used": [],
            })
        )

        await agent.draft_slide(
            1,
            "Title",
            ["Point"],
            revision_notes="reviewer wants concrete stats",
            sibling_context="- Slide 2: Origins",
            previous_draft="the old rejected body",
        )

        prompt = mock_llm.ainvoke.await_args.args[0][0].content
        assert "origins" in prompt.lower()
        assert "the old rejected body" in prompt.lower()
        assert prompt.lower().count("reviewer wants concrete stats") == 1
        assert "regeneration" in prompt.lower()

    async def test_changed_previous_draft_busts_cache(
        self, agent: ContentDraftAgent, mock_llm: AsyncMock
    ) -> None:
        """Injecting the prior draft varies full_prompt so a regeneration
        does not return the cached (rejected) response."""
        mock_llm.ainvoke.return_value = MagicMock(
            content=json.dumps({
                "draft_text": "c",
                "confidence_score": 0.5,
                "sources_used": [],
            })
        )

        await agent.draft_slide(1, "Title", ["Point"], previous_draft="draft one")
        await agent.draft_slide(1, "Title", ["Point"], previous_draft="draft two")

        assert mock_llm.ainvoke.call_count == 2

    async def test_draft_slide_passes_langfuse_config(
        self, agent: ContentDraftAgent, mock_llm: AsyncMock
    ) -> None:
        """The content LLM call carries the Langfuse runnable config — the
        exact object returned by get_langfuse_runnable_config, not just non-None.

        The invocation lives in the shared retry helper, so the patch follows the call
        there; the second positional argument of ainvoke(messages, config) is the
        Langfuse config.
        """
        mock_llm.ainvoke.return_value = MagicMock(
            content=json.dumps({
                "draft_text": "c",
                "confidence_score": 0.5,
                "sources_used": [],
            })
        )
        sentinel = {"callbacks": ["langfuse-marker"]}

        with patch(
            "rag_backend.agents.llm_json_retry.get_langfuse_runnable_config",
            return_value=sentinel,
        ):
            await agent.draft_slide(1, "Title", ["Point"])

        assert mock_llm.ainvoke.await_args.args[1] == sentinel


class TestContentDraftCachePoisoning:
    """An unparseable response must never be cached.

    Live 2026-09-14: the content phase returned empty content, which was cached
    and made every retry fail instantly without calling the model at all.
    """

    @pytest.fixture(autouse=True)
    def clear_cache(self) -> None:
        get_ai_response_cache().clear()

    @pytest.fixture
    def mock_llm(self) -> AsyncMock:
        llm = AsyncMock()
        llm.bind = MagicMock(return_value=llm)
        return llm

    @pytest.fixture
    def agent(self, mock_llm: AsyncMock) -> ContentDraftAgent:
        return ContentDraftAgent(llm=mock_llm)

    @staticmethod
    def _payload() -> dict[str, object]:
        return {
            "draft_text": "Slide copy",
            "confidence_score": 0.9,
            "sources_used": ["source-1"],
        }

    async def test_empty_response_is_rerolled_instead_of_failing_the_phase(
        self, agent: ContentDraftAgent, mock_llm: AsyncMock
    ) -> None:
        # Scenario: an empty response is re-rolled (AE-0330)
        mock_llm.ainvoke.side_effect = [
            MagicMock(content=""),
            MagicMock(content=json.dumps(self._payload())),
        ]

        result = await agent.draft_slide(1, "Title", ["Point"])

        assert result["draft_text"] == "Slide copy"
        assert mock_llm.ainvoke.await_count == 2

    async def test_two_empty_responses_raise_and_cache_nothing(
        self, agent: ContentDraftAgent, mock_llm: AsyncMock
    ) -> None:
        """Each of the 5 attempts is a call plus its empty re-roll, so 10 empty answers
        exhaust the model.
        """
        # Scenario: the re-roll is bounded, and a failure caches nothing.
        empty_calls = 2 * LLM_ATTEMPTS_PER_MODEL
        mock_llm.ainvoke.side_effect = [
            *(MagicMock(content="") for _ in range(empty_calls)),
            MagicMock(content=json.dumps(self._payload())),
        ]
        with pytest.raises(ValueError, match="Invalid JSON"):
            await agent.draft_slide(1, "Title", ["Point"])

        result = await agent.draft_slide(1, "Title", ["Point"])

        assert result["draft_text"] == "Slide copy"
        assert mock_llm.ainvoke.await_count == empty_calls + 1

    async def test_malformed_response_is_repaired(
        self, agent: ContentDraftAgent, mock_llm: AsyncMock
    ) -> None:
        # Scenario: malformed-but-present output goes through the repair round-trip
        mock_llm.ainvoke.side_effect = [
            MagicMock(content="{not json"),
            MagicMock(content=json.dumps(self._payload())),
        ]

        result = await agent.draft_slide(1, "Title", ["Point"])

        assert result["draft_text"] == "Slide copy"
        assert mock_llm.ainvoke.await_count == 2

    async def test_poisoned_cache_entry_is_evicted(
        self, agent: ContentDraftAgent, mock_llm: AsyncMock
    ) -> None:
        # Scenario: a poisoned entry from an older deploy is evicted (AE-0330)
        mock_llm.ainvoke.return_value = MagicMock(content=json.dumps(self._payload()))
        await agent.draft_slide(1, "Title", ["Point"])
        prompt = mock_llm.ainvoke.call_args[0][0][0].content
        get_ai_response_cache().set(prompt, agent.model_id, "poisoned-not-json")

        result = await agent.draft_slide(1, "Title", ["Point"])

        assert result["draft_text"] == "Slide copy"
        assert mock_llm.ainvoke.await_count == 2
