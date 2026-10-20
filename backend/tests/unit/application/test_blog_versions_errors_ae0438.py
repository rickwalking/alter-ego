"""Unit tests for the AE-0438 blog editor fixes (F-05, F-08).

Feature: backend/tests/features/blog_versions_errors_ae0438.feature
"""

from __future__ import annotations

import pytest

from rag_backend.application.services.blog.blog_version_history import (
    VersionSnapshot,
    append_version,
    drop_empty_entries,
    is_empty_document,
)
from rag_backend.application.services.blog_post_ai_service import (
    _rewrite_context,
    strip_heading_echo,
)
from rag_backend.domain.constants.blog_editor import REWRITE_NO_HEADING_INSTRUCTION
from tests.blog_v2_support import v2_content

BOOTSTRAP = {
    "schema": "blog.v2",
    "cover": None,
    "sections": [],
    "translations": {},
    "quality": None,
}


def _snapshot(content: object, summary: str = "Before save") -> VersionSnapshot:
    return VersionSnapshot(
        post_id="p1",
        title="T",
        excerpt=None,
        content=content,
        author_id="u1",
        change_summary=summary,
    )


def _entry(number: int, content: object) -> dict[str, object]:
    return {
        "id": f"e{number}",
        "content_id": "p1",
        "content_type": "blog_post",
        "version_number": number,
        "title": "T",
        "excerpt": None,
        "snapshot": content,
        "change_summary": "Before save",
        "author_id": "u1",
        "created_at": "2026-10-20T00:00:00Z",
    }


class TestIsEmptyDocument:
    def test_bootstrap_is_empty(self) -> None:
        assert is_empty_document(BOOTSTRAP)

    def test_document_with_a_body_is_not_empty(self) -> None:
        assert not is_empty_document(v2_content("Corpo"))

    def test_heading_only_is_not_empty(self) -> None:
        assert not is_empty_document(v2_content("", "Título"))

    def test_cover_only_is_not_empty(self) -> None:
        content = v2_content("")
        content["cover"] = {"url": "/api/blog-images/x/a.jpg", "alt": "Capa"}
        assert not is_empty_document(content)

    def test_quality_only_is_not_empty(self) -> None:
        content = v2_content("")
        content["quality"] = {
            "voice_score": 80.0,
            "voice_breakdown": {},
            "repetition": {"repeated_sentences": [], "banned_phrases": []},
            "rewrite_passes": 0,
            "checked_at": None,
        }
        assert not is_empty_document(content)

    def test_translation_content_counts(self) -> None:
        content = v2_content("")
        english = v2_content("English body")
        content["translations"] = {"en": english}
        assert not is_empty_document(content)

    def test_non_dict_and_garbage_are_empty(self) -> None:
        assert is_empty_document(None)
        assert is_empty_document("markdown")
        assert is_empty_document({})
        assert is_empty_document({"sections": "nope"})
        assert is_empty_document({"sections": [{"body_md": None}]})


class TestAppendVersionSkipsEmpty:
    # Scenario: Generation's first write does not snapshot the empty bootstrap
    def test_empty_snapshot_appends_nothing(self) -> None:
        assert append_version([], _snapshot(BOOTSTRAP)) == []

    # Scenario: The first appended version is the first stored AI draft
    def test_first_non_empty_snapshot_is_version_one(self) -> None:
        history = append_version([], _snapshot(BOOTSTRAP))
        draft = v2_content("Artigo original")
        history = append_version(history, _snapshot(draft))
        assert [entry["version_number"] for entry in history] == [1]
        assert history[0]["snapshot"] == draft

    def test_existing_history_is_left_untouched_by_an_empty_write(self) -> None:
        history = append_version([], _snapshot(v2_content("V1")))
        assert append_version(history, _snapshot(BOOTSTRAP)) == history


class TestDropEmptyEntries:
    # Scenario: The apply command drops empty entries and renumbers idempotently
    def test_drops_and_renumbers(self) -> None:
        history = [
            _entry(1, BOOTSTRAP),
            _entry(2, v2_content("Artigo")),
            _entry(3, v2_content("Edição")),
        ]
        cleaned = drop_empty_entries(history)
        assert cleaned is not None
        assert [entry["version_number"] for entry in cleaned] == [1, 2]
        assert [entry["snapshot"] for entry in cleaned] == [
            v2_content("Artigo"),
            v2_content("Edição"),
        ]

    def test_drops_middle_empties_and_renumbers(self) -> None:
        history = [
            _entry(1, v2_content("Artigo")),
            _entry(2, BOOTSTRAP),
            _entry(3, v2_content("Edição")),
        ]
        cleaned = drop_empty_entries(history)
        assert cleaned is not None
        assert [entry["version_number"] for entry in cleaned] == [1, 2]

    def test_clean_history_is_unchanged(self) -> None:
        history = [_entry(1, v2_content("Artigo"))]
        assert drop_empty_entries(history) is None

    def test_non_list_history_is_clean(self) -> None:
        assert drop_empty_entries(None) is None
        assert drop_empty_entries("junk") is None

    def test_all_empty_history_becomes_empty_list(self) -> None:
        assert drop_empty_entries([_entry(1, BOOTSTRAP)]) == []


class TestStripHeadingEcho:
    HEADING = "Planilha vence torcida"

    # Scenario: A bold heading echoed into the rewrite result is stripped
    def test_bold_echo_is_stripped(self) -> None:
        body = f"**{self.HEADING}**\n\nMinha cadência é mensal"
        assert strip_heading_echo(body, self.HEADING) == "Minha cadência é mensal"

    # Scenario: A markdown or plain heading echo is stripped too
    @pytest.mark.parametrize(
        "echo",
        [
            "# Planilha vence torcida",
            "## Planilha vence torcida",
            "Planilha vence torcida",
            "planilha vence torcida",
            "  **PLANILHA VENCE TORCIDA**  ",
        ],
    )
    def test_markdown_and_plain_echoes_are_stripped(self, echo: str) -> None:
        body = f"{echo}\n\nMinha cadência é mensal"
        assert strip_heading_echo(body, self.HEADING) == "Minha cadência é mensal"

    def test_leading_blank_lines_are_skipped_before_the_echo(self) -> None:
        body = f"\n\n**{self.HEADING}**\nMinha cadência é mensal"
        assert strip_heading_echo(body, self.HEADING) == "Minha cadência é mensal"

    # Scenario: A body that starts differently is kept untouched
    def test_non_echo_first_line_is_kept(self) -> None:
        body = "A planilha vence a torcida.\n\nMinha cadência é mensal"
        assert strip_heading_echo(body, self.HEADING) == body

    # Scenario: A rewrite of a section without a heading is not altered
    def test_no_heading_returns_the_body(self) -> None:
        body = "Minha cadência é mensal"
        assert strip_heading_echo(body, None) == body

    def test_non_string_result_degrades_to_empty(self) -> None:
        assert strip_heading_echo(["x"], self.HEADING) == ""

    def test_only_the_echo_is_removed_when_it_is_the_whole_body(self) -> None:
        assert strip_heading_echo(f"**{self.HEADING}**", self.HEADING) == ""


class TestRewriteContext:
    # Scenario: The rewrite request tells the model not to repeat the heading
    def test_context_holds_the_heading_and_the_instruction(self) -> None:
        context = _rewrite_context("Planilha vence torcida")
        assert "Planilha vence torcida" in context
        assert REWRITE_NO_HEADING_INSTRUCTION in context

    def test_context_without_heading_still_holds_the_instruction(self) -> None:
        assert _rewrite_context(None) == REWRITE_NO_HEADING_INSTRUCTION
