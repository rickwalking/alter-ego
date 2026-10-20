"""AE-0439: stored persona-score entries are normalized on 0-100 at the write
boundary (QA F-12) and pending re-scores are visible to the gate read (#154 B).

Gherkin: tests/features/blog_carousel_minors_ae0439.feature
  - Scenario: Stored persona scores are on 0-100 even for a raw 0-10 judge answer
  - Scenario: A stored raw 0-10 row still reads on 0-100
  - Scenario: A passing gate with pending re-scores waits instead of approving
"""

from __future__ import annotations

import pytest

from rag_backend.domain.persona_score import (
    lowest_overall,
    on_hundred_scale_entry,
    pending_rescores,
    stored_overall,
)


@pytest.mark.unit
class TestOnHundredScaleEntry:
    def test_a_raw_ten_point_answer_is_scaled_once(self) -> None:
        """Scenario: Stored persona scores are on 0-100 for a raw 0-10 answer."""
        entry = on_hundred_scale_entry(
            {
                "tone_match": 9.0,
                "sentence_structure_match": 8.8,
                "opinion_strength": 7.8,
                "originality": 8.5,
                "human_authenticity": 8.4,
                "overall": 8.5,
                "suggestions": ["keep the contract"],
            }
        )
        assert entry["overall"] == pytest.approx(85.0)
        assert entry["tone_match"] == pytest.approx(90.0)
        assert entry["sentence_structure_match"] == pytest.approx(88.0)
        assert entry["opinion_strength"] == pytest.approx(78.0)
        assert entry["originality"] == pytest.approx(85.0)
        assert entry["human_authenticity"] == pytest.approx(84.0)
        assert entry["suggestions"] == ["keep the contract"]

    def test_the_overall_is_scaled_on_its_own_like_the_agent(self) -> None:
        """A 0-10 overall with 0-100 sub-scores scales only the overall."""
        entry = on_hundred_scale_entry({"tone_match": 78.0, "overall": 7.8})
        assert entry["overall"] == pytest.approx(78.0)
        assert entry["tone_match"] == 78.0

    def test_a_hundred_point_entry_is_kept(self) -> None:
        entry = on_hundred_scale_entry({"tone_match": 86.0, "overall": 83.0})
        assert entry["overall"] == 83.0
        assert entry["tone_match"] == 86.0

    def test_pending_markers_survive_the_normalization(self) -> None:
        """The stored rescore marker of an unscored rewrite is never dropped."""
        entry = on_hundred_scale_entry(
            {"overall": 8.0, "rescore_pending": True, "unscored_ticks": 2}
        )
        assert entry["overall"] == pytest.approx(80.0)
        assert entry["rescore_pending"] is True
        assert entry["unscored_ticks"] == 2


@pytest.mark.unit
class TestPendingRescores:
    def test_pending_slide_entries_are_listed_with_their_ticks(self) -> None:
        scores = {
            "slide_1": {"overall": 85.0},
            "slide_3": {"overall": 55.0, "rescore_pending": True, "unscored_ticks": 2},
            "slide_7": {"overall": 70.0, "rescore_pending": True, "unscored_ticks": 1},
        }
        assert pending_rescores(scores) == {3: 2, 7: 1}

    def test_a_malformed_tick_reads_as_one(self) -> None:
        assert pending_rescores(
            {"slide_3": {"overall": 55.0, "rescore_pending": True}}
        ) == {3: 1}
        assert pending_rescores(
            {"slide_3": {"overall": 55.0, "rescore_pending": True, "unscored_ticks": "x"}}
        ) == {3: 1}

    def test_non_pending_and_non_slide_entries_are_ignored(self) -> None:
        scores = {
            "slide_2": {"overall": 80.0, "rescore_pending": False},
            "voice": {"rescore_pending": True},
            "slide_x": {"rescore_pending": True},
        }
        assert pending_rescores(scores) == {}

    def test_a_non_mapping_reads_empty(self) -> None:
        assert pending_rescores(None) == {}
        assert pending_rescores("slide_1") == {}


@pytest.mark.unit
class TestReadsKeepWorking:
    def test_a_raw_stored_row_still_reads_on_hundred(self) -> None:
        """Scenario: A stored raw 0-10 row still reads on 0-100."""
        assert stored_overall({"overall": 8.5}) == pytest.approx(85.0)
        assert lowest_overall({"slide_1": {"overall": 8.5}}) == pytest.approx(85.0)
