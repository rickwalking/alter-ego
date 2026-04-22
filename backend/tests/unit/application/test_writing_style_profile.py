"""Unit tests for WritingStyleProfile.

Gherkin: tests/features/linkedin_post.feature
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from rag_backend.application.services.writing_style_profile import (
    VoiceSample,
    WritingStyleProfile,
    format_samples_for_prompt,
)


def _html_with_og(description: str) -> str:
    return (
        "<html><head>"
        f'<meta property="og:description" content="{description}">'
        "</head><body></body></html>"
    )


def _make_research_tool(responses: dict[str, str]) -> AsyncMock:
    tool = AsyncMock()

    async def _scrape(url: str) -> str:
        value = responses.get(url)
        if isinstance(value, Exception):
            raise value
        return value or ""

    tool.scrape_url.side_effect = _scrape
    return tool


@pytest.mark.unit
class TestWritingStyleProfileScraping:
    """Scenario: Voice samples are loaded from configured URLs."""

    async def test_scrapes_two_urls(self, tmp_path: Path) -> None:
        responses = {
            "https://li/one": _html_with_og("não é só um upgrade. é rápido."),
            "https://li/two": _html_with_og("The protocol provides access to data."),
        }
        profile = WritingStyleProfile(
            research_tool=_make_research_tool(responses),
            style_urls="https://li/one,https://li/two",
            cache_dir=str(tmp_path),
        )
        samples = await profile.get_samples()
        assert len(samples) == 2
        assert samples[0].language == "pt"
        assert samples[1].language == "en"

    async def test_cache_is_written_then_reused(self, tmp_path: Path) -> None:
        responses = {
            "https://li/one": _html_with_og("the quick brown fox"),
        }
        tool = _make_research_tool(responses)
        profile = WritingStyleProfile(
            research_tool=tool,
            style_urls="https://li/one",
            cache_dir=str(tmp_path),
        )
        await profile.get_samples()
        assert (tmp_path / "scraped_snippets.json").exists()

        # Second load on a fresh profile should use the cache, not re-scrape.
        tool2 = _make_research_tool({})
        profile2 = WritingStyleProfile(
            research_tool=tool2,
            style_urls="https://li/one",
            cache_dir=str(tmp_path),
        )
        samples = await profile2.get_samples()
        assert len(samples) == 1
        tool2.scrape_url.assert_not_called()

    async def test_scrape_failure_is_skipped(self, tmp_path: Path) -> None:
        responses = {
            "https://li/broken": RuntimeError("404"),
            "https://li/ok": _html_with_og("fine-tuning é uma técnica"),
        }
        profile = WritingStyleProfile(
            research_tool=_make_research_tool(responses),
            style_urls="https://li/broken,https://li/ok",
            cache_dir=str(tmp_path),
        )
        samples = await profile.get_samples()
        assert len(samples) == 1
        assert "fine-tuning" in samples[0].text

    async def test_empty_urls_returns_empty(self, tmp_path: Path) -> None:
        profile = WritingStyleProfile(
            research_tool=_make_research_tool({}),
            style_urls="",
            cache_dir=str(tmp_path),
        )
        assert await profile.get_samples() == []


@pytest.mark.unit
class TestWritingStyleProfileManualOverride:
    """Scenario: Manual samples file wins over URL scraping."""

    async def test_manual_samples_win(self, tmp_path: Path) -> None:
        manual = tmp_path / "writing_style_samples.yml"
        manual.write_text(
            "samples:\n"
            "  - source: my-blog\n"
            "    language: en\n"
            '    text: "High fidelity voice example from the author."\n',
            encoding="utf-8",
        )
        tool = _make_research_tool({})
        profile = WritingStyleProfile(
            research_tool=tool,
            style_urls="https://li/should-not-scrape",
            cache_dir=str(tmp_path),
            manual_samples_path=str(manual),
        )
        samples = await profile.get_samples()
        assert len(samples) == 1
        assert samples[0].source_url == "my-blog"
        tool.scrape_url.assert_not_called()

    async def test_malformed_manual_file_falls_back_to_scraping(self, tmp_path: Path) -> None:
        manual = tmp_path / "writing_style_samples.yml"
        manual.write_text("::not-yaml::", encoding="utf-8")
        responses = {"https://li/ok": _html_with_og("conteúdo válido")}
        profile = WritingStyleProfile(
            research_tool=_make_research_tool(responses),
            style_urls="https://li/ok",
            cache_dir=str(tmp_path),
            manual_samples_path=str(manual),
        )
        samples = await profile.get_samples()
        assert len(samples) == 1


@pytest.mark.unit
class TestFormatSamplesForPrompt:
    """Rendering helpers for prompt injection."""

    def test_empty_samples_yield_empty_block(self) -> None:
        assert format_samples_for_prompt([], "pt") == ""

    def test_primary_language_samples_come_first(self) -> None:
        samples = [
            VoiceSample("u1", "en", "english voice"),
            VoiceSample("u2", "pt", "voz portuguesa"),
        ]
        block = format_samples_for_prompt(samples, "pt")
        assert block.index("voz portuguesa") < block.index("english voice")
