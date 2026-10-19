"""Unit tests of the pure blog editor helpers (AE-0424, ADR-0025).

Feature: backend/tests/features/blog_post_ai_contract_ae0424.feature
Strict ai-suggest parsing, version snapshots, the approval reset on edit and
targeted per-language document edits.
"""

from __future__ import annotations

import json

import pytest

from rag_backend.application.services.blog.ai_envelope import (
    parse_suggestion,
    strip_code_fence,
)
from rag_backend.application.services.blog.blog_document_edits import (
    BlogEditError,
    find_section,
    language_document,
    with_cover,
    with_section,
    with_translation,
)
from rag_backend.application.services.blog.blog_review_reset import (
    review_reset_values,
)
from rag_backend.application.services.blog.blog_version_history import (
    VersionSnapshot,
    append_version,
)
from rag_backend.domain.constants.blog_editor import (
    ERR_BLOG_SECTION_NOT_FOUND,
    ERR_BLOG_TRANSLATION_MISSING,
)
from rag_backend.domain.constants.blog_post import BlogPostStatus
from rag_backend.domain.models.blog_document import (
    BlogImage,
    BlogLanguageDocument,
    parse_blog_content,
)
from tests.blog_v2_support import v2_content, v2_section

SEC_2 = "sec_00000000-0000-4000-8000-000000000002"
FENCE = "```"


def _image(url: str = "https://cdn.example/a.jpg") -> BlogImage:
    return BlogImage(url=url, alt="Diagrama")


def _two_section_document() -> dict[str, object]:
    content = v2_content("Corpo um", "Um")
    content["sections"] = [
        v2_section("Corpo um", "Um"),
        v2_section("Corpo dois", "Dois", SEC_2),
    ]
    return content


class TestParseSuggestion:
    # Scenario: A clean JSON envelope is returned as plain suggested_text
    def test_clean_envelope(self) -> None:
        raw = json.dumps({"suggested_text": "Sharper lede", "explanation": "Why"})
        parsed = parse_suggestion(raw)
        assert parsed.text == "Sharper lede"
        assert parsed.explanation == "Why"

    # Scenario: A fenced JSON envelope is unwrapped
    def test_fenced_envelope(self) -> None:
        raw = f'{FENCE}json\n{{"suggested_text":"Sharper lede"}}\n{FENCE}'
        parsed = parse_suggestion(raw)
        assert parsed.text == "Sharper lede"
        assert FENCE not in parsed.text
        assert parsed.explanation is None

    # Scenario: A nested envelope is unwrapped once
    def test_nested_envelope(self) -> None:
        inner = json.dumps({"suggested_text": "Inner", "explanation": "inner why"})
        raw = json.dumps({"suggested_text": inner, "explanation": "outer"})
        parsed = parse_suggestion(raw)
        assert parsed.text == "Inner"
        assert parsed.explanation == "inner why"

    def test_nested_fenced_envelope_keeps_outer_explanation(self) -> None:
        inner = f'{FENCE}json\n{{"suggested_text": "Inner"}}\n{FENCE}'
        raw = json.dumps({"suggested_text": inner, "explanation": "outer"})
        parsed = parse_suggestion(raw)
        assert parsed.text == "Inner"
        assert parsed.explanation == "outer"

    # Scenario: Non-JSON model output degrades to the raw text
    def test_non_json_degrades_to_raw(self) -> None:
        parsed = parse_suggestion("  Just improve it, please  ")
        assert parsed.text == "Just improve it, please"
        assert parsed.explanation is None

    # Scenario: An empty model response is handled
    def test_empty_response(self) -> None:
        assert parse_suggestion("").text == ""

    def test_json_without_suggested_text_is_raw(self) -> None:
        raw = json.dumps({"other": 1})
        assert parse_suggestion(raw).text == raw

    def test_json_array_is_raw(self) -> None:
        assert parse_suggestion("[1, 2]").text == "[1, 2]"

    def test_null_suggested_text_is_empty(self) -> None:
        raw = json.dumps({"suggested_text": None, "explanation": "  "})
        parsed = parse_suggestion(raw)
        assert parsed.text == ""
        assert parsed.explanation is None


class TestStripCodeFence:
    def test_plain_text_is_stripped(self) -> None:
        assert strip_code_fence("  hi  ") == "hi"

    def test_fence_without_language(self) -> None:
        assert strip_code_fence(f"{FENCE}\nbody\n{FENCE}") == "body"

    def test_fence_with_inline_body_keeps_it(self) -> None:
        assert strip_code_fence(f"{FENCE}a b{FENCE}") == "a b"

    def test_unterminated_fence_is_left(self) -> None:
        assert strip_code_fence(f"{FENCE}json\nx") == f"{FENCE}json\nx"


class TestAppendVersion:
    def _snapshot(self, summary: str = "Saved") -> VersionSnapshot:
        return VersionSnapshot(
            post_id="p1",
            title="T",
            excerpt="E",
            content=v2_content(),
            author_id="u1",
            change_summary=summary,
        )

    # Scenario: Every PUT appends a version snapshot in the save transaction
    def test_first_entry_is_version_one_with_title_and_content(self) -> None:
        history = append_version([], self._snapshot())
        assert len(history) == 1
        entry = history[0]
        assert entry["version_number"] == 1
        assert entry["title"] == "T"
        assert entry["excerpt"] == "E"
        assert entry["snapshot"] == v2_content()
        assert entry["change_summary"] == "Saved"
        assert entry["content_id"] == "p1"
        assert entry["author_id"] == "u1"
        assert entry["content_type"] == "blog_post"
        assert isinstance(entry["created_at"], str)

    # Scenario: Version history accumulates across saves
    def test_numbers_continue_after_the_highest(self) -> None:
        history = append_version(
            [{"version_number": 4}, {"version_number": 2}, "junk"], self._snapshot()
        )
        assert [e["version_number"] for e in history] == [4, 2, 5]

    def test_non_list_history_starts_fresh(self) -> None:
        history = append_version(None, self._snapshot())
        assert history[0]["version_number"] == 1

    def test_entry_without_number_counts_as_zero(self) -> None:
        history = append_version([{"version_number": None}], self._snapshot())
        assert history[-1]["version_number"] == 1


class TestReviewReset:
    # Scenario: Editing after approval resets the post to draft
    @pytest.mark.parametrize(
        "status", [BlogPostStatus.APPROVED.value, BlogPostStatus.UNDER_REVIEW.value]
    )
    @pytest.mark.parametrize("field", ["content", "title", "excerpt"])
    def test_content_edit_resets(self, status: str, field: str) -> None:
        values = review_reset_values(status, {field: "x"})
        assert values == {
            "status": BlogPostStatus.DRAFT.value,
            "scheduled_publish_at": None,
            "submitted_for_review_at": None,
            "approved_at": None,
        }

    def test_draft_and_published_are_not_reset(self) -> None:
        assert review_reset_values(BlogPostStatus.DRAFT.value, {"content": 1}) == {}
        assert review_reset_values(BlogPostStatus.PUBLISHED.value, {"title": 1}) == {}

    def test_non_content_edit_keeps_approval(self) -> None:
        assert review_reset_values(BlogPostStatus.APPROVED.value, {"tags": []}) == {}


class TestDocumentEdits:
    def test_pt_language_is_the_document(self) -> None:
        document = parse_blog_content(v2_content())
        assert language_document(document, "pt") is document

    def test_missing_translation_raises(self) -> None:
        document = parse_blog_content(v2_content())
        with pytest.raises(BlogEditError) as exc:
            language_document(document, "en")
        assert exc.value.code == ERR_BLOG_TRANSLATION_MISSING

    def test_unknown_section_raises(self) -> None:
        document = parse_blog_content(v2_content())
        with pytest.raises(BlogEditError) as exc:
            find_section(document, "sec_unknown")
        assert exc.value.code == ERR_BLOG_SECTION_NOT_FOUND

    # Scenario: Rewriting a section replaces only that section's body
    def test_with_section_replaces_only_that_section(self) -> None:
        document = parse_blog_content(_two_section_document())
        target = document.sections[1].model_copy(update={"body_md": "Novo"})
        updated = with_section(document, "pt", target)
        assert [s.body_md for s in updated.sections] == ["Corpo um", "Novo"]
        assert updated.sections[0] == document.sections[0]

    def test_with_section_unknown_id_raises(self) -> None:
        document = parse_blog_content(v2_content())
        stray = document.sections[0].model_copy(update={"id": "sec_x"})
        with pytest.raises(BlogEditError):
            with_section(document, "pt", stray)

    def test_with_cover_sets_and_clears_pt(self) -> None:
        document = parse_blog_content(v2_content())
        covered = with_cover(document, "pt", _image())
        assert covered.cover == _image()
        assert with_cover(covered, "pt", None).cover is None

    # Scenario: Editing the EN document never mutates PT
    def test_en_edits_leave_pt_identical(self) -> None:
        document = parse_blog_content(_two_section_document())
        en_content = v2_content("Body EN", "One")
        en_content.pop("translations")
        english = BlogLanguageDocument.model_validate(en_content)
        translated = with_translation(document, english)
        assert translated.translations["en"] == english
        covered = with_cover(translated, "en", _image())
        assert covered.translations["en"].cover == _image()
        assert covered.cover is None
        en_section = english.sections[0].model_copy(update={"body_md": "Edited"})
        edited = with_section(covered, "en", en_section)
        assert edited.translations["en"].sections[0].body_md == "Edited"
        assert edited.sections == document.sections
