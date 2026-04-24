"""Unit tests for carousel content synthesis JSON parsing robustness.

Feature: Content synthesis JSON extraction
  As a carousel pipeline
  I want to tolerate malformed LLM JSON responses
  So that transient LLM mistakes don't fail the entire pipeline
"""

import json
from unittest.mock import AsyncMock

import pytest

from rag_backend.application.services.carousel.nodes.content import (
    _ERR_JSON_NOT_FOUND,
    _extract_json_with_repair,
    extract_json,
)


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
        payload = {"slides": [{"number": 1, "type": "intro", "heading": "H", "body": "B"}]}
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
