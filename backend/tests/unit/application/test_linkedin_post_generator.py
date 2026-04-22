"""Unit tests for LinkedInPostGenerator.

Gherkin: tests/features/linkedin_post.feature
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from rag_backend.application.services.linkedin_post_generator import (
    LINKEDIN_MAX_CHARS,
    LinkedInPostGenerator,
)
from rag_backend.application.services.writing_style_profile import VoiceSample
from rag_backend.domain.models import CarouselProject


def _project(
    blog_pt: str | None = "Blog em português.", blog_en: str | None = "Blog in English."
) -> CarouselProject:
    translations: dict[str, str] = {}
    if blog_pt:
        translations["pt"] = blog_pt
    if blog_en:
        translations["en"] = blog_en
    return CarouselProject(
        topic="Test topic",
        audience="Devs",
        niche="AI",
        blog_markdown=blog_pt,
        blog_translations=translations or None,
    )


def _style(samples: list[VoiceSample] | None = None) -> AsyncMock:
    mock = AsyncMock()
    mock.get_samples = AsyncMock(return_value=samples or [])
    return mock


@pytest.mark.unit
class TestLinkedInPostGenerationHappyPath:
    """Scenarios: Generates a LinkedIn post in PT and EN."""

    async def test_generates_portuguese_post(self) -> None:
        llm = AsyncMock()
        llm.generate = AsyncMock(return_value="Post gerado em português.\n\n#IA")
        gen = LinkedInPostGenerator(llm, _style())
        post = await gen.generate(_project(), "pt")
        assert post.language == "pt"
        assert "Post gerado" in post.text
        assert post.char_count <= LINKEDIN_MAX_CHARS

    async def test_generates_english_post(self) -> None:
        llm = AsyncMock()
        llm.generate = AsyncMock(return_value="An English post.\n\n#AI")
        gen = LinkedInPostGenerator(llm, _style())
        post = await gen.generate(_project(), "en")
        assert post.language == "en"
        assert post.text == "An English post.\n\n#AI"

    async def test_generate_both_produces_both(self) -> None:
        llm = AsyncMock()
        llm.generate = AsyncMock(side_effect=["PT post.\n\n#AI", "EN post.\n\n#AI"])
        gen = LinkedInPostGenerator(llm, _style())
        pt, en = await gen.generate_both(_project())
        assert pt is not None and pt.language == "pt"
        assert en is not None and en.language == "en"

    async def test_generate_both_skips_missing_language(self) -> None:
        llm = AsyncMock()
        llm.generate = AsyncMock(return_value="PT only post.")
        gen = LinkedInPostGenerator(llm, _style())
        pt, en = await gen.generate_both(_project(blog_en=None))
        assert pt is not None
        assert en is None


@pytest.mark.unit
class TestLinkedInPostGenerationEdgeCases:
    """Failure + cleanup scenarios."""

    async def test_missing_blog_language_raises(self) -> None:
        llm = AsyncMock()
        gen = LinkedInPostGenerator(llm, _style())
        with pytest.raises(ValueError, match="en"):
            await gen.generate(_project(blog_en=None), "en")

    async def test_voice_examples_inserted_into_prompt(self) -> None:
        llm = AsyncMock()
        llm.generate = AsyncMock(return_value="Generated.")
        samples = [VoiceSample("u", "pt", "exemplo de voz do autor")]
        gen = LinkedInPostGenerator(llm, _style(samples))
        await gen.generate(_project(), "pt")

        prompt = llm.generate.call_args.kwargs["messages"][0]["content"]
        assert "exemplo de voz do autor" in prompt
        assert "Voice examples" in prompt

    async def test_leading_label_is_stripped(self) -> None:
        llm = AsyncMock()
        llm.generate = AsyncMock(return_value="LinkedIn Post: real content here")
        gen = LinkedInPostGenerator(llm, _style())
        post = await gen.generate(_project(), "pt")
        assert post.text == "real content here"

    async def test_truncates_oversized_output_on_boundary(self) -> None:
        paragraph = "This is a sentence. " * 200  # ~4000 chars
        llm = AsyncMock()
        llm.generate = AsyncMock(return_value=paragraph)
        gen = LinkedInPostGenerator(llm, _style())
        post = await gen.generate(_project(), "pt")
        assert post.char_count <= LINKEDIN_MAX_CHARS
        assert post.text.rstrip().endswith(".")
