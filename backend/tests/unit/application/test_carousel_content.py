"""Unit tests for carousel content synthesis JSON parsing robustness.

Feature: Content synthesis JSON extraction
  As a carousel pipeline
  I want to tolerate malformed LLM JSON responses
  So that transient LLM mistakes don't fail the entire pipeline
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from rag_backend.application.services.carousel.nodes.content import (
    _ERR_JSON_NOT_FOUND,
    _extract_json_with_repair,
    extract_json,
    run_content,
)
from rag_backend.domain.models import CarouselProject


@pytest.mark.unit
class TestExtractJson:
    """Direct tests for extract_json heuristic strategies."""

    def test_parses_clean_json(self):
        """Given a clean JSON string, when extract_json is called,
        then returns parsed object."""
        payload = {"slides": [], "blog_pt": "# Blog"}
        result = extract_json(json.dumps(payload))
        assert result == payload

    def test_tolerates_markdown_fences(self):
        """Given JSON wrapped in ```json fences, when extract_json is called,
        then returns parsed object."""
        payload = {
            "slides": [{"number": 1, "type": "intro", "heading": "H", "body": "B"}]
        }
        raw = f"Here is the JSON:\n```json\n{json.dumps(payload)}\n```\nDone."
        result = extract_json(raw)
        assert result == payload

    def test_tolerates_multiple_code_blocks(self):
        """Given multiple markdown blocks, when extract_json is called,
        then finds the valid JSON block."""
        payload = {"slides": [], "blog_pt": "# Blog"}
        raw = (
            "```text\nSome explanation\n```\n"
            f"```json\n{json.dumps(payload)}\n```\n"
            "```\nMore text\n```"
        )
        result = extract_json(raw)
        assert result == payload

    def test_tolerates_trailing_commas(self):
        """Given JSON with trailing commas, when extract_json is called,
        then returns parsed object."""
        raw = (
            '{"slides": [{"number": 1, "type": "intro", "heading": "H", '
            '"body": "B",}], "blog_pt": "# Blog",}'
        )
        result = extract_json(raw)
        assert result["slides"][0]["heading"] == "H"

    def test_tolerates_prose_before_and_after(self):
        """Given prose surrounding JSON, when extract_json is called,
        then extracts the object."""
        payload = {"slides": [], "blog_pt": "# Blog"}
        raw = f"Sure thing! Here is your data:\n{json.dumps(payload)}\nHope that helps."
        result = extract_json(raw)
        assert result == payload

    def test_tolerates_nested_braces(self):
        """Given nested objects inside the main JSON, when extract_json is called,
        then extracts the outermost object."""
        payload = {
            "slides": [{"number": 1, "type": "intro", "heading": "H", "body": "B"}],
            "blog_pt": "# Blog",
        }
        raw = f"Some text {json.dumps(payload)} more text"
        result = extract_json(raw)
        assert result == payload

    def test_raises_when_no_json_found(self):
        """Given text with no JSON, when extract_json is called,
        then raises JSONDecodeError."""
        with pytest.raises(json.JSONDecodeError, match=_ERR_JSON_NOT_FOUND):
            extract_json("This is just plain text with no braces")

    def test_raises_when_malformed_json_cannot_be_recovered(self):
        """Given unrecoverable malformed JSON, when extract_json is called,
        then raises JSONDecodeError."""
        with pytest.raises(json.JSONDecodeError, match=_ERR_JSON_NOT_FOUND):
            extract_json("{ broken: json without quotes }")


@pytest.mark.unit
class TestExtractJsonWithRepair:
    """Tests for _extract_json_with_repair LLM retry logic."""

    async def test_repair_succeeds_on_second_attempt(self):
        """Given invalid JSON on first attempt and valid JSON on repair,
        when _extract_json_with_repair is called, then returns parsed object."""
        payload = {"slides": [], "blog_pt": "# Blog"}
        llm = AsyncMock()
        llm.generate = AsyncMock(return_value=json.dumps(payload))

        result = await _extract_json_with_repair(
            "not valid json",
            llm=llm,
            project_id="test-project",
        )

        assert result == payload
        assert llm.generate.call_count == 1

    async def test_raises_when_both_attempts_fail(self):
        """Given invalid JSON on both attempts, when _extract_json_with_repair
        is called, then raises JSONDecodeError."""
        llm = AsyncMock()
        llm.generate = AsyncMock(return_value="still not valid json")

        with pytest.raises(json.JSONDecodeError, match=_ERR_JSON_NOT_FOUND):
            await _extract_json_with_repair(
                "not valid json",
                llm=llm,
                project_id="test-project",
            )

        assert llm.generate.call_count == 1

    async def test_no_repair_when_first_attempt_succeeds(self):
        """Given valid JSON on first attempt, when _extract_json_with_repair
        is called, then does not call LLM repair."""
        payload = {"slides": [], "blog_pt": "# Blog"}
        llm = AsyncMock()
        llm.generate = AsyncMock()

        result = await _extract_json_with_repair(
            json.dumps(payload),
            llm=llm,
            project_id="test-project",
        )

        assert result == payload
        assert not llm.generate.called


@pytest.mark.unit
class TestRunContentImageMap:
    """Tests for blog_image_map extraction during content synthesis."""

    async def test_parses_valid_blog_image_map(self):
        """Given a JSON response with blog_image_map, when run_content is called,
        then stores the image map on the project."""
        llm = AsyncMock()
        template = MagicMock()
        template.build_content_prompt.return_value = "prompt"
        response = {
            "slides": [
                {"number": 1, "type": "intro", "heading": "Intro", "body": "B"},
                {"number": 2, "type": "content", "heading": "Stats", "body": "B"},
            ],
            "blog_pt": "# Blog",
            "blog_en": "# Blog EN",
            "blog_image_map": [
                {"slide_number": 2, "heading": "Stats", "alt": "Stats image"},
            ],
        }
        llm.generate = AsyncMock(return_value=json.dumps(response))

        project = CarouselProject(topic="T", audience="A", niche="N")
        await run_content(project, [], llm=llm, template=template)

        assert project.blog_image_map is not None
        assert len(project.blog_image_map) == 1
        assert project.blog_image_map[0]["slide_number"] == 2
        assert project.blog_image_map[0]["heading"] == "Stats"
        assert project.blog_image_map[0]["alt"] == "Stats image"

    async def test_ignores_invalid_slide_numbers(self):
        """Given a blog_image_map with out-of-range slide_numbers, when run_content
        is called, then filters out invalid entries."""
        llm = AsyncMock()
        template = MagicMock()
        template.build_content_prompt.return_value = "prompt"
        response = {
            "slides": [
                {"number": 1, "type": "intro", "heading": "Intro", "body": "B"},
            ],
            "blog_pt": "# Blog",
            "blog_image_map": [
                {"slide_number": 0, "heading": "Invalid", "alt": ""},
                {"slide_number": 8, "heading": "Invalid", "alt": ""},
                {"slide_number": 3, "heading": "Valid", "alt": "Valid image"},
            ],
        }
        llm.generate = AsyncMock(return_value=json.dumps(response))

        project = CarouselProject(topic="T", audience="A", niche="N")
        await run_content(project, [], llm=llm, template=template)

        assert project.blog_image_map is not None
        assert len(project.blog_image_map) == 1
        assert project.blog_image_map[0]["slide_number"] == 3

    async def test_ignores_missing_blog_image_map(self):
        """Given a JSON response without blog_image_map, when run_content is called,
        then project.blog_image_map remains None."""
        llm = AsyncMock()
        template = MagicMock()
        template.build_content_prompt.return_value = "prompt"
        response = {
            "slides": [
                {"number": 1, "type": "intro", "heading": "Intro", "body": "B"},
            ],
            "blog_pt": "# Blog",
        }
        llm.generate = AsyncMock(return_value=json.dumps(response))

        project = CarouselProject(topic="T", audience="A", niche="N")
        await run_content(project, [], llm=llm, template=template)

        assert project.blog_image_map is None


@pytest.mark.unit
class TestRunContentTitleEn:
    """Tests for title_en/subtitle_en storage during content synthesis."""

    async def test_stores_title_en_and_subtitle_en(self):
        """Given a JSON response with title_en and subtitle_en, when run_content
        is called, then stores the English title and subtitle on the project."""
        llm = AsyncMock()
        template = MagicMock()
        template.build_content_prompt.return_value = "prompt"
        response = {
            "slides": [
                {"number": 1, "type": "intro", "heading": "Intro", "body": "B"},
            ],
            "blog_pt": "# Blog",
            "blog_en": "# Blog EN",
            "title_pt": "Título PT",
            "subtitle_pt": "Subtítulo PT",
            "title_en": "English Title",
            "subtitle_en": "English Subtitle",
        }
        llm.generate = AsyncMock(return_value=json.dumps(response))

        project = CarouselProject(topic="T", audience="A", niche="N")
        await run_content(project, [], llm=llm, template=template)

        assert project.title == "Título PT"
        assert project.subtitle == "Subtítulo PT"
        assert project.title_en == "English Title"
        assert project.subtitle_en == "English Subtitle"

    async def test_ignores_missing_title_en(self):
        """Given a JSON response without title_en, when run_content is called,
        then title_en remains None."""
        llm = AsyncMock()
        template = MagicMock()
        template.build_content_prompt.return_value = "prompt"
        response = {
            "slides": [
                {"number": 1, "type": "intro", "heading": "Intro", "body": "B"},
            ],
            "blog_pt": "# Blog",
            "title_pt": "Título PT",
        }
        llm.generate = AsyncMock(return_value=json.dumps(response))

        project = CarouselProject(topic="T", audience="A", niche="N")
        await run_content(project, [], llm=llm, template=template)

        assert project.title == "Título PT"
        assert project.title_en is None
        assert project.subtitle_en is None


class TestRunContentSummaryAndTldr:
    """Tests for parsing summary_points and tldr_strip from LLM output."""

    async def test_parses_summary_points_on_summary_slide(self):
        """Given a JSON response with summary_points, when run_content is called,
        then SlideData includes the summary_points."""
        llm = AsyncMock()
        template = MagicMock()
        template.build_content_prompt.return_value = "prompt"
        response = {
            "slides": [
                {"number": 1, "type": "intro", "heading": "Intro", "body": "B"},
                {
                    "number": 2,
                    "type": "summary",
                    "heading": "Resumo",
                    "body": "",
                    "summary_points": [
                        {"icon": "🎯", "title": "T1", "body": "B1"},
                        {"icon": "🔍", "title": "T2", "body": "B2"},
                    ],
                },
            ],
            "blog_pt": "# Blog",
        }
        llm.generate = AsyncMock(return_value=json.dumps(response))

        project = CarouselProject(topic="T", audience="A", niche="N")
        slides_data, _ = await run_content(project, [], llm=llm, template=template)

        summary_slide = next(
            (s for s in slides_data if s.slide_type == "summary"), None
        )
        assert summary_slide is not None
        assert summary_slide.summary_points is not None
        assert len(summary_slide.summary_points) == 2
        assert summary_slide.summary_points[0]["icon"] == "🎯"
        assert summary_slide.summary_points[0]["title"] == "T1"

    async def test_parses_tldr_strip_on_intro_slide(self):
        """Given a JSON response with tldr_strip on intro, when run_content is called,
        then SlideData includes the tldr_strip."""
        llm = AsyncMock()
        template = MagicMock()
        template.build_content_prompt.return_value = "prompt"
        response = {
            "slides": [
                {
                    "number": 1,
                    "type": "intro",
                    "heading": "Intro",
                    "body": "B",
                    "tldr_strip": "TLDR: quick summary here.",
                },
            ],
            "blog_pt": "# Blog",
        }
        llm.generate = AsyncMock(return_value=json.dumps(response))

        project = CarouselProject(topic="T", audience="A", niche="N")
        slides_data, _ = await run_content(project, [], llm=llm, template=template)

        intro_slide = slides_data[0]
        assert intro_slide.tldr_strip == "TLDR: quick summary here."

    async def test_caps_summary_points_at_max_features(self):
        """Given summary_points exceeding MAX_FEATURE_ITEMS, when run_content is called,
        then points are truncated to MAX_FEATURE_ITEMS."""
        llm = AsyncMock()
        template = MagicMock()
        template.build_content_prompt.return_value = "prompt"
        response = {
            "slides": [
                {
                    "number": 2,
                    "type": "summary",
                    "heading": "Resumo",
                    "body": "",
                    "summary_points": [
                        {"icon": "1", "title": "T1", "body": "B1"},
                        {"icon": "2", "title": "T2", "body": "B2"},
                        {"icon": "3", "title": "T3", "body": "B3"},
                        {"icon": "4", "title": "T4", "body": "B4"},
                        {"icon": "5", "title": "T5", "body": "B5"},
                    ],
                },
            ],
            "blog_pt": "# Blog",
        }
        llm.generate = AsyncMock(return_value=json.dumps(response))

        project = CarouselProject(topic="T", audience="A", niche="N")
        slides_data, _ = await run_content(project, [], llm=llm, template=template)

        summary_slide = slides_data[0]
        assert summary_slide.summary_points is not None
        assert len(summary_slide.summary_points) == 4
