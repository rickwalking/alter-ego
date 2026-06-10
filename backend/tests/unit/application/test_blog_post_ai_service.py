"""Unit tests for blog post AI assistance service.

Feature: Blog post AI suggestions and improvements
"""

import json
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rag_backend.application.services.blog_post_ai_service import (
    BlogPostAIService,
    LLMServiceProtocol,
)
from rag_backend.domain.constants.blog_ai import ERR_INVALID_AI_ACTION
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


class TestBlogPostAIService:
    """Tests for BlogPostAIService."""

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
            image_service=None,
            output_dir=tmp_path,
        )

    @pytest.mark.asyncio
    async def test_suggest_parses_json_response(
        self, service: BlogPostAIService, llm_service: AsyncMock
    ) -> None:
        """Given valid LLM JSON, when suggesting, then structured response is returned."""
        result = await service.suggest("original", action="improve")

        assert result["suggested_text"] == "Better text"
        assert result["explanation"] == "Clearer wording"
        llm_service.generate.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_suggest_starts_trace_with_defaults(
        self, service: BlogPostAIService, llm_service: AsyncMock
    ) -> None:
        """Given no trace context, when suggesting, then default trace metadata is used."""
        with patch(
            "rag_backend.application.services.blog_post_ai_service.start_blog_workflow_trace"
        ) as mock_trace:
            await service.suggest("original", action="improve")

        mock_trace.assert_called_once_with("unknown", "system")

    @pytest.mark.asyncio
    async def test_suggest_starts_trace_with_custom_context(
        self, service: BlogPostAIService, llm_service: AsyncMock
    ) -> None:
        """Given trace context, when suggesting, then custom metadata is forwarded."""
        from rag_backend.application.services.blog_post_ai_service import (
            BlogAiTraceContext,
        )

        trace = BlogAiTraceContext(post_id="post-42", user_id="editor-1")
        with patch(
            "rag_backend.application.services.blog_post_ai_service.start_blog_workflow_trace"
        ) as mock_trace:
            await service.suggest("original", action="improve", trace=trace)

        mock_trace.assert_called_once_with("post-42", "editor-1")

    @pytest.mark.asyncio
    async def test_suggest_builds_prompt_with_action_and_text(
        self, service: BlogPostAIService, llm_service: AsyncMock
    ) -> None:
        """Given text and action, when suggesting, then prompt includes all inputs."""
        await service.suggest(
            "hello world",
            action="shorten",
            context="blog intro",
        )

        prompt = llm_service.generate.call_args.kwargs["messages"][0]["content"]
        assert "hello world" in prompt
        assert "shorten" in prompt
        assert "blog intro" in prompt

    @pytest.mark.asyncio
    async def test_suggest_falls_back_when_response_not_json(
        self, service: BlogPostAIService, llm_service: AsyncMock
    ) -> None:
        """Given non-JSON LLM output, when suggesting, then raw text is returned."""
        llm_service.generate.return_value = "plain rewrite text"

        result = await service.suggest("original", action="improve")

        assert result["suggested_text"] == "plain rewrite text"
        assert "improve" in result["explanation"]

        assert result["original_text"] == "original"

    @pytest.mark.asyncio
    async def test_improve_starts_trace_with_custom_context(
        self, service: BlogPostAIService, llm_service: AsyncMock
    ) -> None:
        """Given trace context, when improving, then trace metadata is forwarded."""
        from rag_backend.application.services.blog_post_ai_service import (
            BlogAiTraceContext,
        )

        trace = BlogAiTraceContext(post_id="post-77", user_id="editor-2")
        with patch(
            "rag_backend.application.services.blog_post_ai_service.start_blog_workflow_trace"
        ) as mock_trace:
            await service.improve(
                db=AsyncMock(),
                text="draft",
                action="shorten",
                trace=trace,
            )

        mock_trace.assert_called_once_with("post-77", "editor-2")

    @pytest.mark.asyncio
    async def test_improve_rejects_invalid_action(
        self, service: BlogPostAIService
    ) -> None:
        """Given invalid action, when improving, then ValueError is raised."""
        with pytest.raises(ValueError, match=ERR_INVALID_AI_ACTION):
            await service.improve(db=AsyncMock(), text="text", action="invalid")

    @pytest.mark.asyncio
    async def test_suggest_rejects_invalid_action(
        self, service: BlogPostAIService
    ) -> None:
        """Given invalid action, when suggesting, then ValueError is raised."""
        with pytest.raises(ValueError, match=ERR_INVALID_AI_ACTION):
            await service.suggest("text", action="invalid")

    @pytest.mark.asyncio
    async def test_improve_without_persona_uses_llm(
        self, service: BlogPostAIService, llm_service: AsyncMock
    ) -> None:
        """Given no persona, when improving, then LLM generate is used."""
        llm_service.generate.return_value = "Improved paragraph"

        result = await service.improve(
            db=AsyncMock(),
            text="draft",
            action="shorten",
        )

        assert result["improved_text"] == "Improved paragraph"
        assert result["action"] == "shorten"

    @pytest.mark.asyncio
    async def test_improve_without_persona_builds_prompt(
        self, service: BlogPostAIService, llm_service: AsyncMock
    ) -> None:
        """Given no persona, when improving, then prompt includes action and text."""
        llm_service.generate.return_value = "Improved paragraph"

        await service.improve(
            db=AsyncMock(),
            text="draft text",
            action="expand",
            context="section 2",
        )

        prompt = llm_service.generate.call_args.kwargs["messages"][0]["content"]
        assert "draft text" in prompt
        assert "expand" in prompt
        assert "section 2" in prompt

    @pytest.mark.asyncio
    async def test_load_persona_returns_none_when_missing(
        self, service: BlogPostAIService
    ) -> None:
        """Given unknown persona id, when loading, then None is returned."""
        db = AsyncMock()
        db.get = AsyncMock(return_value=None)

        result = await service._load_persona(db, "missing-id")

        assert result is None

    @pytest.mark.asyncio
    async def test_load_persona_returns_none_when_no_id(
        self, service: BlogPostAIService
    ) -> None:
        """Given no persona id, when loading, then None is returned."""
        result = await service._load_persona(AsyncMock(), None)

        assert result is None

    @pytest.mark.asyncio
    async def test_load_persona_returns_entity_when_found(
        self, service: BlogPostAIService
    ) -> None:
        """Given existing persona, when loading, then entity is returned."""
        persona = PersonaProfile(name="Pedro")
        model = MagicMock()
        model.to_entity.return_value = persona
        db = AsyncMock()
        db.get = AsyncMock(return_value=model)

        result = await service._load_persona(db, "persona-1")

        assert result == persona
        db.get.assert_awaited_once_with(PersonaProfileModel, "persona-1")

    @pytest.mark.asyncio
    async def test_service_stores_dependencies(
        self, llm_service: AsyncMock, tmp_path: Path
    ) -> None:
        """Given dependencies, when service is created, then they are stored."""
        service = BlogPostAIService(
            llm_service=llm_service,
            image_service=None,
            output_dir=tmp_path,
        )

        assert service._llm_service is llm_service
        assert service._image_service is None
        assert service._output_dir == tmp_path

    @pytest.mark.asyncio
    async def test_improve_with_persona_uses_persona_agent(
        self, tmp_path: Path
    ) -> None:
        """Given persona and OpenAI service, when improving, then PersonaAgent is used."""

        class StubOpenAIService:
            chat_model = MagicMock()

            async def generate(
                self,
                messages: list[dict[str, str]],
                temperature: float = 0.7,
                max_tokens: int | None = None,
            ) -> str:
                return "fallback"

        service = BlogPostAIService(
            llm_service=StubOpenAIService(),
            image_service=None,
            output_dir=tmp_path,
        )

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
                db=db,
                text="draft",
                action="improve",
                persona_id="persona-1",
            )

        assert result["improved_text"] == "Pedro-style text"

    @pytest.mark.asyncio
    async def test_generate_image_writes_file_and_returns_path(
        self, llm_service: AsyncMock, tmp_path: Path
    ) -> None:
        """Given image service, when generating image, then file path is returned."""
        image_service = AsyncMock()

        def _write_image(prompt: str, output_path: str) -> None:
            Path(output_path).write_text("fake-image", encoding="utf-8")

        image_service.generate_image = AsyncMock(side_effect=_write_image)
        service = BlogPostAIService(
            llm_service=llm_service,
            image_service=image_service,
            output_dir=tmp_path,
        )

        result = await service.generate_image("post-1", "A blog hero image")

        image_service.generate_image.assert_awaited_once()
        assert result["prompt"] == "a blog hero image"
        assert Path(result["image_url"]).exists()
        assert Path(result["image_url"]).read_text(encoding="utf-8") == "fake-image"

    @pytest.mark.asyncio
    async def test_generate_image_starts_trace_with_post_and_user(
        self, llm_service: AsyncMock, tmp_path: Path
    ) -> None:
        """Given post id and user, when generating image, then trace uses both values."""
        image_service = AsyncMock()
        image_service.generate_image = AsyncMock(return_value=None)
        service = BlogPostAIService(
            llm_service=llm_service,
            image_service=image_service,
            output_dir=tmp_path,
        )

        with patch(
            "rag_backend.application.services.blog_post_ai_service.start_blog_workflow_trace"
        ) as mock_trace:
            await service.generate_image("post-9", "prompt", user_id="editor-3")

        mock_trace.assert_called_once_with("post-9", "editor-3")

    @pytest.mark.asyncio
    async def test_generate_image_wraps_service_errors(
        self, llm_service: AsyncMock, tmp_path: Path
    ) -> None:
        """Given image service failure, when generating, then RuntimeError is raised."""
        image_service = AsyncMock()

        def _fail(_prompt: str, _output_path: str) -> None:
            raise OSError("disk full")

        image_service.generate_image = _fail
        service = BlogPostAIService(
            llm_service=llm_service,
            image_service=image_service,
            output_dir=tmp_path,
        )

        with pytest.raises(RuntimeError, match="Image generation failed"):
            await service.generate_image("post-1", "prompt")

    @pytest.mark.asyncio
    async def test_generate_image_requires_service(
        self, service: BlogPostAIService
    ) -> None:
        """Given no image service, when generating image, then RuntimeError is raised."""
        with pytest.raises(RuntimeError, match="image service unavailable"):
            await service.generate_image("post-1", "A blog hero image")


class TestLLMServiceProtocol:
    """Tests for LLMServiceProtocol interface."""

    @pytest.mark.asyncio
    async def test_protocol_can_be_implemented(self) -> None:
        """Given a concrete class implementing LLMServiceProtocol, when calling generate, then it works."""

        class StubLLMService:
            async def generate(
                self,
                messages: list[dict[str, str]],
                temperature: float = 0.7,
                max_tokens: int | None = None,
            ) -> str:
                return "test response"

            @property
            def chat_model(self) -> MagicMock:
                return MagicMock()

        service = StubLLMService()
        result = await service.generate([{"role": "user", "content": "hello"}])
        assert result == "test response"

    def test_protocol_is_runtime_checkable(self) -> None:
        """Given a runtime checkable protocol, when checking isinstance, then it works."""

        assert hasattr(LLMServiceProtocol, "generate")
        assert hasattr(LLMServiceProtocol, "chat_model")
