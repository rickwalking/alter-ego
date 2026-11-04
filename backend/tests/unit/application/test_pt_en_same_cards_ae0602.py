"""PT and EN keep the same cards when the PT draft loses its quote card.

Gherkin: tests/features/pt_en_same_cards_ae0602.feature
The deck is the recorded structure of prod 41c4f437 (synthetic text, the shared
gate shape builder). Real localized builder, real fail-closed review and real gate
validation; only the single retry is a double, and it applies the real
``place_quote_cards`` the production retry applies.
"""

from __future__ import annotations

import pytest

from rag_backend.application.services.carousel.content_fail_closed import (
    FailClosedReviewCommand,
    build_fail_closed_review_updates,
)
from rag_backend.application.services.carousel.content_gate_repair_targets import (
    fill_missing_en_structure,
)
from rag_backend.application.services.carousel.localized_slide_builder import (
    build_localized_slide,
)
from rag_backend.domain.constants.carousel_presentation import (
    VIOLATION_TRANSLATION_SHAPE_MISMATCH,
)
from rag_backend.domain.models.carousel_presentation_adapters import (
    structural_signature,
)
from rag_backend.domain.news_quote_cards import place_quote_cards
from tests.unit.application.gate_shape_builder_ae0599 import (
    POLICY,
    drafts_and_translations,
)
from tests.unit.application.gate_shape_specs_ae0599 import SHAPES

_PROJECT = "ae0602-shape"
_SHAPE = "41c4f437"
_SLIDE = 4
_KEPT_CARD_SLIDE = 5
_PT = "presentation_pt"
_EN = "presentation_en"
_INSIGHT = "insight"
_KIND = "content_kind"
_FEATURES = "features"
_EMPTY_FEATURES = "features:0"
_CARD = {"quote": "A synthetic quote.", "attribution": "A. Person", "quote_id": "q-1"}
_UNPARSABLE = "## PT\n**Heading:**\n**Body:**\n## EN\n**Heading:**\n**Body:**\n"
_FRESH_SCAFFOLD = (
    "## PT\n**Heading:** Revisão com dono\n**Body:** Eu dou um dono a cada pedido.\n"
    "## EN\n**Heading:** Owned reviews\n**Body:** I give every request an owner.\n"
)


def _deck() -> tuple[list[dict[str, object]], dict[int, dict[str, object]]]:
    drafts, translations = drafts_and_translations(SHAPES[_SHAPE])
    return drafts, {int(index): entry for index, entry in translations.items()}


def _draft(slide_index: int, **extras: object) -> dict[str, object]:
    return {
        "slide_index": slide_index,
        "slide_type": "content",
        "title": "Regra visível",
        "draft_text": "Eu escrevo a regra antes do código.",
        **extras,
    }


def _translation(**extras: object) -> dict[str, object]:
    return {"heading": "Visible rule", "body": "I write the rule first.", **extras}


def _slide(updates: dict[str, object], slide_index: int) -> dict[str, object]:
    slides = updates["localized_slides"]
    assert isinstance(slides, list)
    return next(slide for slide in slides if slide["slide_index"] == slide_index)


def _shapes(slide: dict[str, object]) -> tuple[str, str]:
    pt, en = slide[_PT], slide[_EN]
    assert isinstance(pt, dict)
    assert isinstance(en, dict)
    return structural_signature(pt), structural_signature(en)


def _mismatches(updates: dict[str, object]) -> list[dict[str, object]]:
    report = updates["presentation_validation"]
    assert isinstance(report, dict)
    violations = report["violations"]
    assert isinstance(violations, list)
    return [
        item
        for item in violations
        if item["code"] == VIOLATION_TRANSLATION_SHAPE_MISMATCH
    ]


async def _review(
    drafts: list[dict[str, object]],
    translations: dict[int, dict[str, object]],
) -> dict[str, object]:
    return await build_fail_closed_review_updates(
        FailClosedReviewCommand(
            project_id=_PROJECT,
            slide_drafts=drafts,
            translations_en=translations,
            policy_version=POLICY,
        )
    )


@pytest.mark.unit
class TestRecordedShape:
    async def test_the_card_only_in_en_does_not_reach_the_gate(self) -> None:
        """Scenario: The PT draft loses a quote card."""
        drafts, translations = _deck()
        assert _INSIGHT in translations[_SLIDE]

        updates = await _review(drafts, translations)

        slide = _slide(updates, _SLIDE)
        assert _INSIGHT not in slide[_EN]
        assert _shapes(slide) == (_EMPTY_FEATURES, _EMPTY_FEATURES)
        assert _mismatches(updates) == []

    async def test_a_card_pt_still_has_stays_in_both_locales(self) -> None:
        """Scenario: A card PT still has stays in both locales."""
        drafts, translations = _deck()

        updates = await _review(drafts, translations)

        slide = _slide(updates, _KEPT_CARD_SLIDE)
        assert isinstance(slide[_PT][_INSIGHT], dict)
        assert isinstance(slide[_EN][_INSIGHT], dict)


@pytest.mark.unit
class TestFailClosedRetry:
    async def test_a_redrafted_slide_loses_the_card_in_both_locales(self) -> None:
        """Scenario: The fail-closed retry re-drafts a slide that showed a quote card."""
        drafts, translations = _deck()
        position = next(
            at for at, draft in enumerate(drafts) if draft["slide_index"] == _SLIDE
        )
        drafts[position] = {
            **drafts[position],
            "draft_text": _UNPARSABLE,
            _INSIGHT: dict(_CARD),
        }
        retried: list[int] = []

        async def retry(slide_index: int) -> dict[str, object] | None:
            retried.append(slide_index)
            if slide_index != _SLIDE:
                return None
            fresh = {
                **_draft(slide_index, quote_id="q-1", draft_text=_FRESH_SCAFFOLD),
                "role": "point",
            }
            return place_quote_cards([fresh], ())[0]

        first = await _review(drafts, translations)
        assert _INSIGHT in _slide(first, _SLIDE)[_PT]

        updates = await build_fail_closed_review_updates(
            FailClosedReviewCommand(
                project_id=_PROJECT,
                slide_drafts=drafts,
                translations_en=translations,
                policy_version=POLICY,
                retry_draft=retry,
            )
        )

        assert _SLIDE in retried
        slide = _slide(updates, _SLIDE)
        assert _INSIGHT not in slide[_PT]
        assert _INSIGHT not in slide[_EN]
        assert _shapes(slide) == (_EMPTY_FEATURES, _EMPTY_FEATURES)
        assert _mismatches(updates) == []


@pytest.mark.unit
class TestContentKind:
    def test_en_takes_the_pt_kind_when_the_card_goes(self) -> None:
        """Scenario: The EN content kind follows PT when the card goes."""
        slide = build_localized_slide(
            _draft(_SLIDE, content_kind="features", features=[{"title": "A"}]),
            slide_index=_SLIDE,
            translations_en={
                _SLIDE: _translation(content_kind=_INSIGHT, insight=dict(_CARD))
            },
        )

        assert slide[_EN][_KIND] == "features"
        assert _INSIGHT not in slide[_EN]

    async def test_en_is_recovered_like_pt_without_a_kind(self) -> None:
        """Scenario: The EN card goes when PT has no content kind either."""
        drafts = [_draft(_SLIDE)]
        translations = {
            _SLIDE: _translation(content_kind=_INSIGHT, insight=dict(_CARD))
        }

        updates = await _review(drafts, translations)

        assert _shapes(_slide(updates, _SLIDE)) == (_EMPTY_FEATURES, _EMPTY_FEATURES)
        assert _mismatches(updates) == []


@pytest.mark.unit
class TestPtReplacedTheCard:
    def test_gate_repair_fills_the_pt_items_and_no_card_stays(self) -> None:
        """Scenario: PT replaced the card with feature items."""
        items = [{"icon_name": "target", "title": "Dono", "body": "Um por pedido."}]
        slide = build_localized_slide(
            _draft(_SLIDE, content_kind=_FEATURES, features=items),
            slide_index=_SLIDE,
            translations_en={_SLIDE: _translation(insight=dict(_CARD))},
        )

        filled, paths = fill_missing_en_structure(slide)

        en = filled[_EN]
        assert isinstance(en, dict)
        assert en[_FEATURES] == items
        assert _INSIGHT not in en
        assert "features[0].title" in paths
        assert structural_signature(en) == structural_signature(slide[_PT])
