"""The three prod shapes blocked after the copy budget deploy reach the gate clean.

Gherkin: tests/features/content_gate_after_copy_budget_ae0599.feature (A, B).
Real ``run_content_budget_step``, real fail-closed review build and real content
gate validation; only the fit model is a double. The drafts and translations
are rebuilt from the recorded structure of 6f36130e, d8da820a and 41c4f437
(field lengths and emphasis markup, synthetic text). With the fit model down,
the same drafts give the prod first gates field for field (31, 39 and 1
violations) on the code before this fix.
"""

from __future__ import annotations

import pytest

from rag_backend.application.services.carousel.content_budget_step import (
    ContentBudgetContext,
    run_content_budget_step,
)
from rag_backend.application.services.carousel.content_fail_closed import (
    FailClosedReviewCommand,
    build_fail_closed_review_updates,
)
from rag_backend.application.services.carousel.copy_budget_fit import (
    LENGTH_VIOLATION_CODES,
)
from rag_backend.application.services.carousel.copy_budget_fit_drafts import (
    DraftFitResult,
)
from rag_backend.application.services.carousel.localized_slide_builder import (
    build_localized_slides,
)
from rag_backend.application.services.carousel.presentation_review import (
    deserialize_translations_en,
)
from rag_backend.application.services.carousel.presentation_review_pipeline import (
    validate_localized_slides,
)
from rag_backend.domain.constants.carousel_presentation import (
    VIOLATION_EMPHASIS_MARKUP_LOCALE_MISMATCH,
    VIOLATION_TRANSLATION_SHAPE_MISMATCH,
)
from tests.unit.application.gate_shape_builder_ae0599 import (
    POLICY,
    ShapeFitter,
    drafts_and_translations,
)
from tests.unit.application.gate_shape_specs_ae0599 import SHAPES

_BOLD = "**"
_GATE = "content_gate_validation"
_VIOLATIONS = "violations"


def _state(translations: dict[str, dict[str, object]]) -> dict[str, object]:
    return {
        "project_id": "ae0599-shape",
        "presentation_policy_version": POLICY,
        "translations_en": translations,
    }


async def _step(shape: str, fitter: ShapeFitter) -> DraftFitResult:
    drafts, translations = drafts_and_translations(SHAPES[shape])
    return await run_content_budget_step(
        fitter,
        ContentBudgetContext(
            state=_state(translations),
            updates={"translations_en": translations},
            slide_drafts=drafts,
        ),
    )


async def _gate(shape: str, fitter: ShapeFitter) -> list[dict[str, object]]:
    """The content gate's violations after the step and the fail-closed review."""
    fit = await _step(shape, fitter)
    updates = await build_fail_closed_review_updates(
        FailClosedReviewCommand(
            project_id="ae0599-shape",
            slide_drafts=fit.slide_drafts,
            translations_en=deserialize_translations_en(fit.translations_en),
            policy_version=POLICY,
        )
    )
    gate = updates.get(_GATE)
    violations = gate.get(_VIOLATIONS) if isinstance(gate, dict) else None
    return [item for item in violations or [] if isinstance(item, dict)]


def _localized(fit: DraftFitResult) -> list[dict[str, object]]:
    return build_localized_slides(
        fit.slide_drafts,
        translations_en=deserialize_translations_en(fit.translations_en),
    )


def _en_texts(slides: list[dict[str, object]]) -> list[str]:
    texts: list[str] = []
    for slide in slides:
        payload = slide.get("presentation_en")
        if not isinstance(payload, dict):
            continue
        texts.extend(str(payload.get(key) or "") for key in ("heading", "body"))
        for key in ("features", "summary_points"):
            items = payload.get(key)
            for item in items if isinstance(items, list) else []:
                texts.extend([str(item.get("title")), str(item.get("body"))])
    return texts


@pytest.mark.unit
class TestEmphasisMeasuredInLocaleConvention:
    async def test_en_titles_reach_the_model_in_strong_emphasis(self) -> None:
        """Scenario: EN copy with PT emphasis markers is converted before it is measured."""
        fitter = ShapeFitter()

        fit = await _step("d8da820a", fitter)

        asked = [
            item.target
            for request in fitter.calls
            for item in request.targets
            if item.target.locale == "en"
        ]
        assert asked
        assert all(_BOLD not in target.text for target in asked)
        titles = {target.field for target in asked if target.slide_index == 5}
        assert {"features[0].title", "features[2].title"} <= titles
        slides = _localized(fit)
        assert all(_BOLD not in text for text in _en_texts(slides))
        report = validate_localized_slides(slides, policy_version=POLICY)
        assert not [v for v in report.violations if v.code in LENGTH_VIOLATION_CODES]


@pytest.mark.unit
class TestBlockedShapesPassTheGate:
    @pytest.mark.parametrize("shape", ["6f36130e", "d8da820a"])
    async def test_shape_passes_the_content_gate(self, shape: str) -> None:
        """Scenario Outline: A blocked prod shape passes the content gate after the step."""
        violations = await _gate(shape, ShapeFitter())

        assert violations == []

    async def test_news_shape_keeps_only_its_quote_card_blocker(self) -> None:
        """Scenario: The quote card keeps the same shape in PT and EN through the step.

        41c4f437 blocked on one ``translation_shape_mismatch``: slide 4's EN
        translation kept a quote card its PT draft no longer had. No copy budget
        path touches that, so the gate still reports it, and only it.
        """
        violations = await _gate("41c4f437", ShapeFitter())

        assert [(v["code"], v["slide_index"]) for v in violations] == [
            (VIOLATION_TRANSLATION_SHAPE_MISMATCH, 4)
        ]

    async def test_quote_card_stays_in_both_locales(self) -> None:
        """Scenario: The quote card keeps the same shape in PT and EN through the step."""
        fit = await _step("41c4f437", ShapeFitter())

        slide = next(s for s in _localized(fit) if s.get("slide_index") == 5)
        for key in ("presentation_pt", "presentation_en"):
            payload = slide[key]
            assert isinstance(payload, dict)
            assert isinstance(payload.get("insight"), dict)


@pytest.mark.unit
class TestShortenModelDown:
    @pytest.mark.parametrize("shape", ["6f36130e", "d8da820a"])
    async def test_gate_blocks_on_length_only(self, shape: str) -> None:
        """Scenario Outline: With the shorten model down the gate still blocks, on length only."""
        violations = await _gate(shape, ShapeFitter(fail=True))

        codes = {str(v["code"]) for v in violations}
        assert violations
        assert VIOLATION_EMPHASIS_MARKUP_LOCALE_MISMATCH not in codes
        assert codes <= LENGTH_VIOLATION_CODES
