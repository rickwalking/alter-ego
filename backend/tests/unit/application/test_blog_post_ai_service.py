"""Unit tests for blog post AI assistance service.

Feature: Blog post AI suggestions and improvements
"""

import json
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rag_backend.application.services.blog_post_ai_service import BlogPostAIService
from rag_backend.domain.constants.blog_ai import ERR_INVALID_AI_ACTION
from rag_backend.domain.models.persona import PersonaProfile


@pytest.fixture(autouse=True)
def mock_blog_ai_observability() -> Iterator[None]:
    with (
        patch(
            "rag_backend.application.services.blog_post_ai_service.start_blog_workflow_trace",
            return_value=None,
        ),
        patch(
            "rag_backend.application.services.blog_post_ai_service.blog_ai_propagate",
            return_value=MagicMock(__enter__=MagicMock(), __exit__=MagicMock()),
        ),
    ):
        yield


class TestBlogPostAIService:
    """Tests for BlogPostAIService."""

    @pytest.fixture
    def llm_service(self) -> AsyncMock:
        service = AsyncMock()
        service.generate = AsyncMock(
            return_value=json.dumps(
                {"suggested_text": "Better text", "explanation": "Clearer wording"}
            )
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
    async def test_suggest_rejects_invalid_action(self, service: BlogPostAIService) -> None:
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
    async def test_improve_with_persona_uses_persona_agent(self, tmp_path: Path) -> None:
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
    async def test_generate_image_requires_service(self, service: BlogPostAIService) -> None:
        """Given no image service, when generating image, then RuntimeError is raised."""
        with pytest.raises(RuntimeError, match="image service unavailable"):
            await service.generate_image("post-1", "A blog hero image")
