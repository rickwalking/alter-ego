"""Unit tests for the per-row cutover plan (AE-0423 review fixes).

Feature: backend/tests/features/blog_sections_ae0423.feature
"""

from __future__ import annotations

import pytest

from rag_backend.domain.constants.blog_document import (
    BLOG_SCHEMA_V2,
    CUTOVER_METADATA_KEY,
)
from rag_backend.domain.models.blog_cutover_plan import (
    COLUMN_CONTENT,
    COLUMN_FEATURED_IMAGE_URL,
    COLUMN_METADATA,
    COLUMN_VERSION_HISTORY,
    CutoverRowState,
    is_valid_v2_content,
    plan_apply,
    plan_rollback,
    rewrite_history,
)
from rag_backend.domain.models.blog_document import (
    drop_invalid_translations,
    parse_blog_content,
)
from rag_backend.domain.models.blog_document_split import (
    convert_legacy_content,
    split_markdown,
)

SEC = "sec_00000000-0000-4000-8000-000000000001"
V2 = {
    "schema": BLOG_SCHEMA_V2,
    "cover": None,
    "sections": [{"id": SEC, "heading": "A", "body_md": "Corpo", "image": None}],
    "translations": {},
    "quality": None,
}
EN = {
    "schema": BLOG_SCHEMA_V2,
    "sections": [{"id": SEC, "heading": None, "body_md": "x"}],
}


def _state(**overrides: object) -> CutoverRowState:
    base: dict = {
        "content": {"markdown": "## A\n\nCorpo"},
        "featured_image_url": None,
        "version_history": [],
        "metadata": {},
    }
    base.update(overrides)
    return CutoverRowState(**base)


class TestStrictVerifyAndRepair:
    # Scenario: --verify uses the same strict parse as the read path
    def test_marker_v2_with_a_bad_translation_key_is_not_valid(self) -> None:
        bad = {**V2, "translations": {"en-US": EN}}
        assert is_valid_v2_content(V2)
        assert not is_valid_v2_content(bad)
        assert not is_valid_v2_content({"markdown": "x"})

    # Scenario: A v2 row with an invalid translation keeps its PT document
    def test_apply_drops_only_the_invalid_translations(self) -> None:
        bad = {**V2, "translations": {"en-US": EN, "en": EN, "es": "## E\n\nx"}}
        change = plan_apply(_state(content=bad, featured_image_url="https://c/x"))
        assert change is not None
        content = change.values[COLUMN_CONTENT]
        assert isinstance(content, dict)
        assert content["sections"] == V2["sections"]
        assert set(content["translations"]) == {"en", "es"}
        assert is_valid_v2_content(content)
        # The cover (and so its projection) is untouched on a repaired v2 row.
        assert COLUMN_FEATURED_IMAGE_URL not in change.values

    def test_drop_invalid_translations_is_none_when_nothing_to_drop(self) -> None:
        assert drop_invalid_translations(V2) is None
        assert drop_invalid_translations({"markdown": "x"}) is None
        assert drop_invalid_translations([]) is None
        repaired = drop_invalid_translations({**V2, "translations": "en"})
        assert repaired is not None
        assert repaired["translations"] == {}

    def test_drop_rejects_non_string_language_keys(self) -> None:
        repaired = drop_invalid_translations({**V2, "translations": {1: EN}})
        assert repaired is not None
        assert repaired["translations"] == {}


class TestBlankTranslations:
    # Scenario: A blank translation is not migrated (PT fallback is kept)
    @pytest.mark.parametrize("blank", ["", "   \n"])
    def test_blank_translation_string_is_skipped(self, blank: str) -> None:
        converted = convert_legacy_content({
            "markdown": "## A\n\nCorpo",
            "translations": {"en": blank},
        })
        assert converted["translations"] == {}

    def test_blank_stray_translation_on_a_v2_row_is_dropped(self) -> None:
        change = plan_apply(_state(content={**V2, "translations": {"en": ""}}))
        assert change is not None
        content = change.values[COLUMN_CONTENT]
        assert isinstance(content, dict)
        assert content["translations"] == {}


class TestFenceInfoString:
    # Scenario: A "## " line inside a fenced code block is not a section boundary
    def test_info_string_fence_inside_a_fence_does_not_close_it(self) -> None:
        md = "## A\n\n```\n```python\n## still code\n```\n\n## B\n\nx"
        chunks = split_markdown(md)
        assert [c.heading for c in chunks] == ["A", "B"]
        assert "## still code" in chunks[0].body


class TestVersionHistory:
    # Scenario: Pre-cutover versions stay restorable
    def test_apply_migrates_every_snapshot(self) -> None:
        history = [
            {"version_number": 1, "snapshot": {"markdown": "## Old\n\nv1"}},
            {"version_number": 2, "snapshot": V2},
            "legacy-string-entry",
            {"version_number": 3},
        ]
        change = plan_apply(_state(content=V2, version_history=history))
        assert change is not None
        assert COLUMN_CONTENT not in change.values
        rewritten = change.values[COLUMN_VERSION_HISTORY]
        assert isinstance(rewritten, list)
        snapshot = parse_blog_content(rewritten[0]["snapshot"])
        assert snapshot.sections[0].heading == "Old"
        assert rewritten[1] is history[1]
        assert rewritten[2:] == history[2:]

    def test_rollback_restores_v1_snapshots(self) -> None:
        history = [{"version_number": 1, "snapshot": {"markdown": "## Old\n\nv1"}}]
        applied = plan_apply(_state(version_history=history))
        assert applied is not None
        migrated = applied.values[COLUMN_VERSION_HISTORY]
        rolled = plan_rollback(
            _state(content=applied.values[COLUMN_CONTENT], version_history=migrated)
        )
        assert rolled is not None
        restored = rolled.values[COLUMN_VERSION_HISTORY]
        assert isinstance(restored, list)
        assert restored[0]["snapshot"] == {
            "markdown": "## Old\n\nv1",
            "translations": {},
        }

    def test_history_that_is_not_a_list_is_left_alone(self) -> None:
        assert rewrite_history(None, lambda _: None) is None
        assert plan_apply(_state(content=V2, version_history=None)) is None


class TestFeaturedImageRollback:
    # Scenario: Rollback restores the featured_image_url the cutover cleared
    def test_apply_stashes_and_rollback_restores(self) -> None:
        applied = plan_apply(
            _state(featured_image_url="https://cdn/old.jpg", metadata={"m": 1})
        )
        assert applied is not None
        assert applied.values[COLUMN_FEATURED_IMAGE_URL] is None
        assert applied.cleared_featured_image_url == "https://cdn/old.jpg"
        metadata = applied.values[COLUMN_METADATA]
        assert isinstance(metadata, dict)
        assert metadata["m"] == 1
        assert CUTOVER_METADATA_KEY in metadata

        rolled = plan_rollback(
            _state(content=applied.values[COLUMN_CONTENT], metadata=metadata)
        )
        assert rolled is not None
        assert rolled.values[COLUMN_FEATURED_IMAGE_URL] == "https://cdn/old.jpg"
        assert rolled.values[COLUMN_METADATA] == {"m": 1}

    def test_rollback_keeps_a_cover_set_after_the_cutover(self) -> None:
        metadata = {CUTOVER_METADATA_KEY: {"featured_image_url": "https://old"}}
        rolled = plan_rollback(
            _state(content=V2, featured_image_url="https://new", metadata=metadata)
        )
        assert rolled is not None
        assert COLUMN_FEATURED_IMAGE_URL not in rolled.values
        assert rolled.values[COLUMN_METADATA] == {}

    def test_apply_without_a_featured_image_stashes_nothing(self) -> None:
        applied = plan_apply(_state())
        assert applied is not None
        assert COLUMN_METADATA not in applied.values
        assert applied.values[COLUMN_FEATURED_IMAGE_URL] is None

    def test_rollback_of_a_row_without_stash_leaves_metadata(self) -> None:
        rolled = plan_rollback(_state(content=V2, metadata={"m": 1}))
        assert rolled is not None
        assert COLUMN_METADATA not in rolled.values
        assert plan_rollback(_state()) is None
