"""Mutation-focused unit tests for blog post AI assistance service.

Feature: Blog post AI suggestions and improvements — mutation killers
"""

import json
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rag_backend.application.services.blog_post_ai_service import (
    BlogAiTraceContext,
    BlogPostAIService,
    _ImproveInput,
    _SuggestInput,
)
from rag_backend.application.services.blog_workflow_observability import StartupParams
from rag_backend.domain.constants.blog_ai import (
    PROMPT_AI_IMPROVE,
    PROMPT_AI_SUGGEST,
)
from rag_backend.domain.models.persona import PersonaProfile
from rag_backend.infrastructure.database.models import PersonaProfileModel


@pytest.fixture(autouse=True)
def mock_blog_ai_observability() -> Iterator[None]:
    with (
        patch(
            "rag_backend.application.services.blog_post_ai_service.start_blog_workflow_trace",
            return_value=None,
        ),
        patch(
            "rag_backend.application.services.blog_post_ai_service.blog_ai_propagate",
            return_value=MagicMock(
                __enter__=MagicMock(),
                __exit__=MagicMock(return_value=False),
            ),
        ),
    ):
        yield


class TestBlogPostAIServiceMutationKillers:
    """Mutation-killing tests for BlogPostAIService."""

    @pytest.fixture
    def llm_service(self) -> AsyncMock:
        service = AsyncMock()
        service.generate = AsyncMock(
            return_value=json.dumps({
                "suggested_text": "Better text",
                "explanation": "Clearer wording",
            })
        )
        service.chat_model = MagicMock()
        return service

    @pytest.fixture
    def service(self, llm_service: AsyncMock, tmp_path: Path) -> BlogPostAIService:
        return BlogPostAIService(
            llm_service=llm_service,
        )

    @pytest.mark.asyncio
    async def test_suggest_default_trace_context(
        self, service: BlogPostAIService, llm_service: AsyncMock
    ) -> None:
        """Given no trace, when suggesting, then default trace is used."""
        with patch(
            "rag_backend.application.services.blog_post_ai_service.start_blog_workflow_trace"
        ) as mock_trace:
            await service.suggest(_SuggestInput("text", action="improve"))

        mock_trace.assert_called_once_with(
            StartupParams(post_id="unknown", user_id="system")
        )

    @pytest.mark.asyncio
    async def test_suggest_trace_with_empty_post_id(
        self, service: BlogPostAIService, llm_service: AsyncMock
    ) -> None:
        """Given empty post_id, when suggesting, then trace uses unknown."""
        trace = BlogAiTraceContext(post_id="", user_id="u1")
        with patch(
            "rag_backend.application.services.blog_post_ai_service.start_blog_workflow_trace"
        ) as mock_trace:
            await service.suggest(_SuggestInput("text", action="improve", trace=trace))

        mock_trace.assert_called_once_with(
            StartupParams(post_id="unknown", user_id="u1")
        )

    @pytest.mark.asyncio
    async def test_suggest_uses_exact_blog_ai_propagate(
        self, service: BlogPostAIService, llm_service: AsyncMock
    ) -> None:
        """Given post id, when suggesting, then blog_ai_propagate gets exact args."""
        trace = BlogAiTraceContext(post_id="post-1", user_id="u1")
        llm_service.generate.return_value = json.dumps({
            "suggested_text": "ok",
            "explanation": "ok",
        })

        with patch(
            "rag_backend.application.services.blog_post_ai_service.blog_ai_propagate",
            return_value=MagicMock(
                __enter__=MagicMock(),
                __exit__=MagicMock(return_value=False),
            ),
        ) as mock_propagate:
            await service.suggest(_SuggestInput("text", action="improve", trace=trace))

        mock_propagate.assert_called_once_with("post-1", "ai_suggest")

    @pytest.mark.asyncio
    async def test_suggest_exact_prompt(
        self, service: BlogPostAIService, llm_service: AsyncMock
    ) -> None:
        """Given text and context, when suggesting, then exact prompt is sent."""
        llm_service.generate.return_value = json.dumps({
            "suggested_text": "ok",
            "explanation": "ok",
        })

        await service.suggest(
            _SuggestInput("draft text", action="improve", context="blog intro")
        )

        expected = PROMPT_AI_SUGGEST.format(
            action="improve",
            context="blog intro",
            text="draft text",
        )
        prompt = llm_service.generate.call_args.kwargs["messages"][0]["content"]
        assert prompt == expected

    @pytest.mark.asyncio
    async def test_suggest_exact_prompt_without_context(
        self, service: BlogPostAIService, llm_service: AsyncMock
    ) -> None:
        """Given no context, when suggesting, then prompt has empty context."""
        llm_service.generate.return_value = json.dumps({
            "suggested_text": "ok",
            "explanation": "ok",
        })

        await service.suggest(
            _SuggestInput("draft text", action="improve", context=None)
        )

        expected = PROMPT_AI_SUGGEST.format(
            action="improve",
            context="",
            text="draft text",
        )
        prompt = llm_service.generate.call_args.kwargs["messages"][0]["content"]
        assert prompt == expected

    @pytest.mark.asyncio
    async def test_suggest_exact_prompt_with_sanitized_text(
        self, service: BlogPostAIService, llm_service: AsyncMock
    ) -> None:
        """Given text with special chars, when suggesting, then exact sanitized prompt is sent."""
        llm_service.generate.return_value = json.dumps({
            "suggested_text": "ok",
            "explanation": "ok",
        })

        await service.suggest(
            _SuggestInput("Hello <World>", action="improve", context="CTX")
        )

        expected = PROMPT_AI_SUGGEST.format(
            action="improve",
            context="CTX",
            text="Hello World",
        )
        prompt = llm_service.generate.call_args.kwargs["messages"][0]["content"]
        assert prompt == expected

    @pytest.mark.asyncio
    async def test_suggest_exact_llm_call(
        self, service: BlogPostAIService, llm_service: AsyncMock
    ) -> None:
        """Given inputs, when suggesting, then exact LLM call is made."""
        llm_service.generate.return_value = json.dumps({
            "suggested_text": "ok",
            "explanation": "ok",
        })

        await service.suggest(_SuggestInput("draft", action="improve"))

        llm_service.generate.assert_awaited_once_with(
            messages=[
                {
                    "role": "user",
                    "content": PROMPT_AI_SUGGEST.format(
                        action="improve",
                        context="",
                        text="draft",
                    ),
                }
            ],
            temperature=0.7,
        )

    @pytest.mark.asyncio
    async def test_suggest_exact_return_dict_with_json(
        self, service: BlogPostAIService, llm_service: AsyncMock
    ) -> None:
        """Given JSON LLM response, when suggesting, then exact dict is returned."""
        llm_service.generate.return_value = json.dumps({
            "suggested_text": "Better text",
            "explanation": "Clearer wording",
        })

        result = await service.suggest(_SuggestInput("original", action="improve"))

        assert result == {
            "original_text": "original",
            "suggested_text": "Better text",
            "suggestion_type": "improve",
            "explanation": "Clearer wording",
        }

    @pytest.mark.asyncio
    async def test_suggest_uses_raw_default_when_suggested_text_missing(
        self, service: BlogPostAIService, llm_service: AsyncMock
    ) -> None:
        """Given JSON without suggested_text, when suggesting, then raw is used."""
        llm_service.generate.return_value = json.dumps({"explanation": "only exp"})

        result = await service.suggest(_SuggestInput("original", action="improve"))

        assert result["suggested_text"] == json.dumps({"explanation": "only exp"})

    @pytest.mark.asyncio
    async def test_suggest_uses_empty_string_default_when_explanation_missing(
        self, service: BlogPostAIService, llm_service: AsyncMock
    ) -> None:
        """Given JSON without explanation, when suggesting, then empty string is used."""
        llm_service.generate.return_value = json.dumps({
            "suggested_text": "Better text"
        })

        result = await service.suggest(_SuggestInput("original", action="improve"))

        assert result["explanation"] == ""

    @pytest.mark.asyncio
    async def test_suggest_str_wraps_non_string_suggested_text(
        self, service: BlogPostAIService, llm_service: AsyncMock
    ) -> None:
        """Given JSON with int suggested_text, when suggesting, then str is applied."""
        llm_service.generate.return_value = json.dumps({"suggested_text": 42})

        result = await service.suggest(_SuggestInput("original", action="improve"))

        assert result["suggested_text"] == "42"

    @pytest.mark.asyncio
    async def test_suggest_str_wraps_non_string_explanation(
        self, service: BlogPostAIService, llm_service: AsyncMock
    ) -> None:
        """Given JSON with int explanation, when suggesting, then str is applied."""
        llm_service.generate.return_value = json.dumps({
            "suggested_text": "ok",
            "explanation": 99,
        })

        result = await service.suggest(_SuggestInput("original", action="improve"))

        assert result["explanation"] == "99"

    @pytest.mark.asyncio
    async def test_suggest_falls_back_exact_values_when_not_json(
        self, service: BlogPostAIService, llm_service: AsyncMock
    ) -> None:
        """Given non-JSON response, when suggesting, then exact fallback is used."""
        llm_service.generate.return_value = "plain rewrite text"

        result = await service.suggest(_SuggestInput("original", action="improve"))

        assert result["suggested_text"] == "plain rewrite text"
        assert result["explanation"] == "Suggested improve rewrite."

    @pytest.mark.asyncio
    async def test_suggest_strips_raw_text_when_not_json(
        self, service: BlogPostAIService, llm_service: AsyncMock
    ) -> None:
        """Given non-JSON with whitespace, when suggesting, then strip is applied."""
        llm_service.generate.return_value = "  plain text  "

        result = await service.suggest(_SuggestInput("original", action="improve"))

        assert result["suggested_text"] == "plain text"

    @pytest.mark.asyncio
    async def test_suggest_exact_explanation_for_shorten_action(
        self, service: BlogPostAIService, llm_service: AsyncMock
    ) -> None:
        """Given shorten action and non-JSON, when suggesting, then exact explanation."""
        llm_service.generate.return_value = "raw"

        result = await service.suggest(_SuggestInput("original", action="shorten"))

        assert result["explanation"] == "Suggested shorten rewrite."

    @pytest.mark.asyncio
    async def test_suggest_original_text_is_sanitized(
        self, service: BlogPostAIService, llm_service: AsyncMock
    ) -> None:
        """Given text with special chars, when suggesting, then original_text is sanitized."""
        llm_service.generate.return_value = json.dumps({
            "suggested_text": "ok",
            "explanation": "ok",
        })

        result = await service.suggest(_SuggestInput("Hello <World>", action="improve"))

        assert result["original_text"] == "Hello World"

    @pytest.mark.asyncio
    async def test_improve_default_trace_context(
        self, service: BlogPostAIService, llm_service: AsyncMock
    ) -> None:
        """Given no trace, when improving, then default trace is used."""
        with patch(
            "rag_backend.application.services.blog_post_ai_service.start_blog_workflow_trace"
        ) as mock_trace:
            await service.improve(
                _ImproveInput(db=AsyncMock(), text="text", action="improve")
            )

        mock_trace.assert_called_once_with(
            StartupParams(post_id="unknown", user_id="system")
        )

    @pytest.mark.asyncio
    async def test_improve_trace_with_empty_post_id(
        self, service: BlogPostAIService, llm_service: AsyncMock
    ) -> None:
        """Given empty post_id, when improving, then trace uses unknown."""
        trace = BlogAiTraceContext(post_id="", user_id="u1")
        with patch(
            "rag_backend.application.services.blog_post_ai_service.start_blog_workflow_trace"
        ) as mock_trace:
            await service.improve(
                _ImproveInput(
                    db=AsyncMock(),
                    text="text",
                    action="improve",
                    trace=trace,
                )
            )

        mock_trace.assert_called_once_with(
            StartupParams(post_id="unknown", user_id="u1")
        )

    @pytest.mark.asyncio
    async def test_improve_uses_exact_blog_ai_propagate(
        self, service: BlogPostAIService, llm_service: AsyncMock
    ) -> None:
        """Given post id, when improving, then blog_ai_propagate gets exact args."""
        trace = BlogAiTraceContext(post_id="post-1", user_id="u1")
        llm_service.generate.return_value = "Improved paragraph"

        with patch(
            "rag_backend.application.services.blog_post_ai_service.blog_ai_propagate",
            return_value=MagicMock(
                __enter__=MagicMock(),
                __exit__=MagicMock(return_value=False),
            ),
        ) as mock_propagate:
            await service.improve(
                _ImproveInput(
                    db=AsyncMock(),
                    text="text",
                    action="improve",
                    trace=trace,
                )
            )

        mock_propagate.assert_called_once_with("post-1", "ai_improve")

    @pytest.mark.asyncio
    async def test_improve_exact_prompt_without_persona(
        self, service: BlogPostAIService, llm_service: AsyncMock
    ) -> None:
        """Given inputs, when improving without persona, then exact prompt is sent."""
        llm_service.generate.return_value = "Improved paragraph"

        await service.improve(
            _ImproveInput(
                db=AsyncMock(),
                text="draft text",
                action="expand",
                context="section 2",
            )
        )

        expected = PROMPT_AI_IMPROVE.format(
            action="expand",
            context="section 2",
            text="draft text",
        )
        prompt = llm_service.generate.call_args.kwargs["messages"][0]["content"]
        assert prompt == expected

    @pytest.mark.asyncio
    async def test_improve_exact_prompt_without_persona_and_no_context(
        self, service: BlogPostAIService, llm_service: AsyncMock
    ) -> None:
        """Given no context, when improving without persona, then exact prompt is sent."""
        llm_service.generate.return_value = "Improved paragraph"

        await service.improve(
            _ImproveInput(
                db=AsyncMock(),
                text="draft text",
                action="expand",
                context=None,
            )
        )

        expected = PROMPT_AI_IMPROVE.format(
            action="expand",
            context="",
            text="draft text",
        )
        prompt = llm_service.generate.call_args.kwargs["messages"][0]["content"]
        assert prompt == expected

    @pytest.mark.asyncio
    async def test_improve_exact_prompt_with_sanitized_text(
        self, service: BlogPostAIService, llm_service: AsyncMock
    ) -> None:
        """Given text with special chars, when improving, then exact sanitized prompt is sent."""
        llm_service.generate.return_value = "Improved paragraph"

        await service.improve(
            _ImproveInput(
                db=AsyncMock(),
                text="Hello <World>",
                action="improve",
                context="CTX",
            )
        )

        expected = PROMPT_AI_IMPROVE.format(
            action="improve",
            context="CTX",
            text="Hello World",
        )
        prompt = llm_service.generate.call_args.kwargs["messages"][0]["content"]
        assert prompt == expected

    @pytest.mark.asyncio
    async def test_improve_exact_llm_call_without_persona(
        self, service: BlogPostAIService, llm_service: AsyncMock
    ) -> None:
        """Given inputs, when improving without persona, then exact LLM call is made."""
        llm_service.generate.return_value = "Improved paragraph"

        await service.improve(
            _ImproveInput(db=AsyncMock(), text="draft", action="improve")
        )

        llm_service.generate.assert_awaited_once_with(
            messages=[
                {
                    "role": "user",
                    "content": PROMPT_AI_IMPROVE.format(
                        action="improve",
                        context="",
                        text="draft",
                    ),
                }
            ],
            temperature=0.7,
        )

    @pytest.mark.asyncio
    async def test_improve_strips_llm_output_without_persona(
        self, service: BlogPostAIService, llm_service: AsyncMock
    ) -> None:
        """Given LLM output with whitespace, when improving, then strip is applied."""
        llm_service.generate.return_value = "  Improved paragraph  "

        result = await service.improve(
            _ImproveInput(db=AsyncMock(), text="draft", action="improve")
        )

        assert result["improved_text"] == "Improved paragraph"

    @pytest.mark.asyncio
    async def test_improve_exact_return_dict_without_persona(
        self, service: BlogPostAIService, llm_service: AsyncMock
    ) -> None:
        """Given no persona, when improving, then exact dict is returned."""
        llm_service.generate.return_value = "Improved paragraph"

        result = await service.improve(
            _ImproveInput(db=AsyncMock(), text="draft", action="shorten")
        )

        assert result == {
            "original_text": "draft",
            "improved_text": "Improved paragraph",
            "action": "shorten",
        }

    @pytest.mark.asyncio
    async def test_improve_exact_return_dict_with_persona(
        self, service: BlogPostAIService, llm_service: AsyncMock
    ) -> None:
        """Given persona, when improving, then exact dict is returned."""
        persona = PersonaProfile(name="Pedro")
        db = AsyncMock()
        db.get = AsyncMock(return_value=MagicMock(to_entity=lambda: persona))

        mock_agent = AsyncMock()
        mock_agent.enforce = AsyncMock(return_value="Pedro-style text")

        with patch(
            "rag_backend.application.services.blog_post_ai_service.PersonaAgent",
            return_value=mock_agent,
        ):
            result = await service.improve(
                _ImproveInput(
                    db=db,
                    text="draft",
                    action="improve",
                    persona_id="persona-1",
                )
            )

        assert result == {
            "original_text": "draft",
            "improved_text": "Pedro-style text",
            "action": "improve",
        }

    @pytest.mark.asyncio
    async def test_improve_with_persona_uses_exact_agent_arguments(
        self, service: BlogPostAIService, llm_service: AsyncMock
    ) -> None:
        """Given persona, when improving, then PersonaAgent gets exact args."""
        persona = PersonaProfile(name="Pedro")
        db = AsyncMock()
        db.get = AsyncMock(return_value=MagicMock(to_entity=lambda: persona))

        mock_agent = AsyncMock()
        mock_agent.enforce = AsyncMock(return_value="ok")

        with patch(
            "rag_backend.application.services.blog_post_ai_service.PersonaAgent",
            return_value=mock_agent,
        ) as mock_agent_cls:
            await service.improve(
                _ImproveInput(
                    db=db,
                    text="draft",
                    action="improve",
                    persona_id="persona-1",
                )
            )

        mock_agent_cls.assert_called_once_with(
            persona=persona,
            llm=llm_service.chat_model,
        )

    @pytest.mark.asyncio
    async def test_improve_with_persona_uses_exact_enforce_arguments(
        self, service: BlogPostAIService, llm_service: AsyncMock
    ) -> None:
        """Given persona, when improving, then enforce gets exact args."""
        persona = PersonaProfile(name="Pedro")
        db = AsyncMock()
        db.get = AsyncMock(return_value=MagicMock(to_entity=lambda: persona))

        mock_agent = AsyncMock()
        mock_agent.enforce = AsyncMock(return_value="ok")

        with patch(
            "rag_backend.application.services.blog_post_ai_service.PersonaAgent",
            return_value=mock_agent,
        ):
            await service.improve(
                _ImproveInput(
                    db=db,
                    text="draft text",
                    action="improve",
                    persona_id="persona-1",
                    context="blog context",
                )
            )

        mock_agent.enforce.assert_awaited_once_with(
            "draft text",
            context="blog context",
        )

    @pytest.mark.asyncio
    async def test_improve_with_persona_does_not_call_llm_generate(
        self, service: BlogPostAIService, llm_service: AsyncMock
    ) -> None:
        """Given persona, when improving, then llm.generate is not called."""
        persona = PersonaProfile(name="Pedro")
        db = AsyncMock()
        db.get = AsyncMock(return_value=MagicMock(to_entity=lambda: persona))

        mock_agent = AsyncMock()
        mock_agent.enforce = AsyncMock(return_value="ok")

        with patch(
            "rag_backend.application.services.blog_post_ai_service.PersonaAgent",
            return_value=mock_agent,
        ):
            await service.improve(
                _ImproveInput(
                    db=db,
                    text="draft",
                    action="improve",
                    persona_id="persona-1",
                )
            )

        llm_service.generate.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_improve_original_text_is_sanitized(
        self, service: BlogPostAIService, llm_service: AsyncMock
    ) -> None:
        """Given text with special chars, when improving, then original_text is sanitized."""
        llm_service.generate.return_value = "Improved paragraph"

        result = await service.improve(
            _ImproveInput(
                db=AsyncMock(),
                text="Hello <World>",
                action="improve",
            )
        )

        assert result["original_text"] == "Hello World"

    @pytest.mark.asyncio
    async def test_load_persona_does_not_call_db_when_no_id(
        self, service: BlogPostAIService
    ) -> None:
        """Given no persona id, when loading, then db.get is not called."""
        db = AsyncMock()

        await service._load_persona(db, None)

        db.get.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_load_persona_awaits_db_get(self, service: BlogPostAIService) -> None:
        """Given persona id, when loading, then db.get is awaited with exact args."""
        db = AsyncMock()
        db.get = AsyncMock(return_value=None)

        await service._load_persona(db, "persona-1")

        db.get.assert_awaited_once_with(PersonaProfileModel, "persona-1")

    @pytest.mark.asyncio
    async def test_load_persona_calls_to_entity(
        self, service: BlogPostAIService
    ) -> None:
        """Given existing model, when loading, then to_entity is called."""
        expected = PersonaProfile(name="Test")
        model = MagicMock()
        model.to_entity.return_value = expected
        db = AsyncMock()
        db.get = AsyncMock(return_value=model)

        result = await service._load_persona(db, "persona-1")

        model.to_entity.assert_called_once()
        assert result is expected

    @pytest.mark.asyncio
    async def test_blog_ai_trace_context_defaults(
        self,
    ) -> None:
        """Given no args, when creating trace context, then defaults are set."""
        ctx = BlogAiTraceContext()

        assert ctx.post_id == ""
        assert ctx.user_id == "system"
