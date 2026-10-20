"""AE-0437: which slides a revision may change (pure helpers).

Gherkin: tests/features/closing_actions_scoped_revisions_ae0437.feature
(section D).
"""

from __future__ import annotations

import pytest

from rag_backend.application.services.carousel.revision_scope import (
    blocked_slides,
    keep_unscoped_slides,
    merge_scoped_drafts,
    named_slides,
    revision_scope,
    scoped_draft_updates,
)


def _slide(index: int, body: str) -> dict[str, object]:
    payload = {"slide_type": "content", "heading": f"Título {index}", "body": body}
    return {
        "slide_index": index,
        "slide_type": "content",
        "presentation_pt": payload,
        "presentation_en": {**payload, "heading": f"Heading {index}"},
    }


def _state(**extra: object) -> dict[str, object]:
    return {
        "localized_slides": [_slide(n, f"Texto {n}.") for n in range(1, 8)],
        "slide_drafts": [{"slide_index": n, "draft_text": "x"} for n in range(1, 8)],
        **extra,
    }


def _gate(*indexes: int, severity: str = "blocker") -> dict[str, object]:
    return {
        "blocking": True,
        "violations": [
            {"slide_index": n, "severity": severity, "code": "body_empty"}
            for n in indexes
        ],
    }


@pytest.mark.unit
class TestNamedSlides:
    # Scenario Outline: The revision note names the slides it may change
    @pytest.mark.parametrize(
        ("note", "expected"),
        [
            ("Apenas no slide 6, crie 3 ações", {6}),
            ("Corrija os slides 2 e 6. Não altere nenhum outro slide.", {2, 6}),
            ("slides 2-4 and slide 7", {2, 3, 4, 7}),
            ("slides 4–2", {2, 3, 4}),
            ("slide 3 (pt body): body_empty. Slide renders only", {3}),
            ("Slide nº 5 e slides 1, 2 ou 3", {1, 2, 3, 5}),
            ("Deixe o tom mais leve", set()),
            ("slide 0", set()),
        ],
    )
    def test_named_slides(self, note: str, expected: set[int]) -> None:
        assert named_slides([note]) == frozenset(expected)

    def test_every_note_counts(self) -> None:
        assert named_slides(["slide 2", "slide 6"]) == frozenset({2, 6})


@pytest.mark.unit
class TestRevisionScope:
    def test_named_and_blocked_slides(self) -> None:
        state = _state(content_gate_validation=_gate(2, 9))
        assert revision_scope(state, ["Altere apenas o slide 6"]) == frozenset({2, 6})

    def test_general_note_means_whole_deck(self) -> None:
        """Scenario: A general revision note still rewrites the whole deck."""
        state = _state(content_gate_validation=_gate(2))
        assert revision_scope(state, ["Deixe o tom mais leve"]) is None

    def test_first_draft_is_never_scoped(self) -> None:
        """Scenario: A first draft is never scoped."""
        assert revision_scope({}, ["slide 6"]) is None
        no_drafts = {"localized_slides": _state()["localized_slides"]}
        assert revision_scope(no_drafts, ["slide 6"]) is None

    def test_slides_outside_the_deck_are_ignored(self) -> None:
        """Scenario: Slide numbers outside the deck are ignored."""
        assert revision_scope(_state(), ["slide 12"]) is None

    def test_blocked_slides_need_a_blocking_gate_and_blockers(self) -> None:
        assert blocked_slides({}) == frozenset()
        assert blocked_slides({"content_gate_validation": {"blocking": False}}) == (
            frozenset()
        )
        warnings = {"content_gate_validation": _gate(3, severity="warning")}
        assert blocked_slides(warnings) == frozenset()
        broken = {"content_gate_validation": {"blocking": True, "violations": "x"}}
        assert blocked_slides(broken) == frozenset()
        assert blocked_slides({"content_gate_validation": _gate(4)}) == frozenset({4})


@pytest.mark.unit
class TestMergeAndRestore:
    def test_fresh_drafts_replace_only_scoped_slides(self) -> None:
        stored: list[dict[str, object]] = [
            {"slide_index": n, "draft_text": "old"} for n in (1, 2, 3)
        ]
        fresh: list[dict[str, object]] = [
            {"slide_index": n, "draft_text": "new"} for n in (1, 2, 3)
        ]
        merged = merge_scoped_drafts(stored, fresh, frozenset({2}))
        assert [d["draft_text"] for d in merged] == ["old", "new", "old"]

    def test_scoped_draft_updates(self) -> None:
        state = _state()
        fresh = {"slide_drafts": [{"slide_index": 6, "draft_text": "new"}]}
        assert scoped_draft_updates(state, fresh, None) is fresh
        assert scoped_draft_updates(state, {"x": 1}, frozenset({6})) == {"x": 1}
        merged = scoped_draft_updates(state, fresh, frozenset({6}))
        drafts = merged["slide_drafts"]
        assert isinstance(drafts, list)
        assert [d["draft_text"] for d in drafts] == ["x"] * 5 + ["new", "x"]

    def test_unscoped_slides_get_their_stored_copy_back(self) -> None:
        state = _state()
        rebuilt = [_slide(n, f"Reescrito {n}.") for n in range(1, 8)]
        updates = keep_unscoped_slides(
            state, {"localized_slides": rebuilt}, frozenset({6})
        )
        slides = updates["localized_slides"]
        assert isinstance(slides, list)
        bodies = [slide["presentation_pt"]["body"] for slide in slides]
        assert bodies == [f"Texto {n}." for n in range(1, 6)] + [
            "Reescrito 6.",
            "Texto 7.",
        ]
        assert "presentation_validation" in updates

    def test_nothing_to_restore(self) -> None:
        assert keep_unscoped_slides({}, {"localized_slides": []}, frozenset({1})) == {}
        assert keep_unscoped_slides(_state(), {}, frozenset({1})) == {}
