"""Unit tests for ContentDraftAgent."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rag_backend.agents.content_draft_agent import ContentDraftAgent
from rag_backend.domain.models.persona import PersonaProfile
from rag_backend.infrastructure.cache.ai_response_cache import get_ai_response_cache


class TestContentDraftAgent:
    @pytest.fixture(autouse=True)
    def clear_cache(self) -> None:
        get_ai_response_cache().clear()

    @pytest.fixture
    def mock_llm(self) -> AsyncMock:
        llm = AsyncMock()
        # AE-0291: draft_slide binds the model config; .bind must return a runnable
        # whose ainvoke is the configured mock (not an auto-created async child).
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
        """AE-0291: the v4 YAML model block reaches the LLM via .bind (not discarded)."""
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
        """AE-0291: sibling context + previous draft + a single imperative revision
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
        """AE-0291: injecting the prior draft varies full_prompt so a regeneration
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
        """AE-0291: the content LLM call carries the Langfuse runnable config — the
        exact object returned by get_langfuse_runnable_config, not just non-None."""
        mock_llm.ainvoke.return_value = MagicMock(
            content=json.dumps({
                "draft_text": "c",
                "confidence_score": 0.5,
                "sources_used": [],
            })
        )
        sentinel = {"callbacks": ["langfuse-marker"]}

        with patch(
            "rag_backend.agents.content_draft_agent.get_langfuse_runnable_config",
            return_value=sentinel,
        ):
            await agent.draft_slide(1, "Title", ["Point"])

        # ainvoke(messages, config) — the second positional is the Langfuse config.
        assert mock_llm.ainvoke.await_args.args[1] == sentinel
