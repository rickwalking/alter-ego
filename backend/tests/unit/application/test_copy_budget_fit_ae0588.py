"""The shorten step rewrites only the over-budget fields, checked by code.

Gherkin: tests/features/copy_fits_slide_budgets_ae0588.feature (section B).
The model is a fake; the validator and the contracts are the real ones.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import replace
from typing import cast

import pytest

from rag_backend.application.services.carousel import copy_budget_fit
from rag_backend.application.services.carousel.copy_budget_fit import (
    LENGTH_VIOLATION_CODES,
    BudgetFitCommand,
    fit_slides_to_budgets,
)
from rag_backend.application.services.carousel.copy_budget_fit_llm import (
    FitRequest,
    FitTarget,
)
from rag_backend.application.services.carousel.presentation_review_pipeline import (
    validate_localized_slides,
)
from rag_backend.domain.constants.copy_budget_fit import COPY_BUDGET_FIT_MAX_ATTEMPTS
from tests.unit.application.copy_budget_fit_fixtures_ae0588 import (
    EN_ANSWERS,
    EN_SENTENCES,
    POLICY_V4,
    PT_ANSWERS,
    PT_SENTENCES,
    FakeFitter,
    content_slide,
    locale_payload,
    localized_slide,
    prose,
    summary_items,
)

_SHORT_PT = PT_SENTENCES[0]
_SHORT_EN = EN_SENTENCES[0]
_LONG_PT = prose(PT_SENTENCES, 230)
_LONG_EN = prose(EN_SENTENCES, 230)
_ENGLISH_FOR_PT = (
    "I see the team lose hours on reviews without a clear goal, and it is the "
    "rule that is missing."
)
_ITEM_ANSWER = "Eu meço o tempo de cada revisão e corto o que sobra."


def _command(
    slides: list[dict[str, object]],
    fitter: FakeFitter,
    tweak: Callable[[BudgetFitCommand], BudgetFitCommand] | None = None,
) -> BudgetFitCommand:
    command = BudgetFitCommand(
        slides=slides, fitter=fitter, policy_version=POLICY_V4, project_id="p"
    )
    return tweak(command) if tweak is not None else command


def _payload(slide: dict[str, object], locale: str) -> dict[str, object]:
    return cast(dict[str, object], slide[f"presentation_{locale}"])


def _length_violations(slides: list[dict[str, object]]) -> list[tuple[object, ...]]:
    report = validate_localized_slides(slides, policy_version=POLICY_V4)
    return [
        (violation.slide_index, violation.locale, violation.field, violation.code)
        for violation in report.violations
        if violation.code in LENGTH_VIOLATION_CODES
    ]


def _summary_slide(long_index: int) -> dict[str, object]:
    titles = ("Defina o dono", "Escreva a regra", "Meça o tempo")
    en_titles = ("Pick the owner", "Write the rule", "Measure the time")
    pt_items = summary_items(PT_ANSWERS, titles, 40)
    en_items = summary_items(EN_ANSWERS, en_titles, 40)
    pt_items[long_index]["body"] = prose(PT_SENTENCES[2:], 115)
    pt = {
        **locale_payload("summary", "Três hábitos de revisão", "Resumo do que muda."),
        "summary_points": pt_items,
    }
    en = {
        **locale_payload("summary", "Three review habits", "What changes, in short."),
        "summary_points": en_items,
    }
    return localized_slide(2, pt, en)


@pytest.mark.unit
@pytest.mark.asyncio
class TestOverBudgetFields:
    async def test_over_budget_body_is_rewritten_and_passes(self) -> None:
        """Scenario: Over-budget fields are rewritten within budget and pass."""
        slides = [content_slide(3, pt_body=_LONG_PT, en_body=_SHORT_EN)]
        fitter = FakeFitter()

        outcome = await fit_slides_to_budgets(_command(slides, fitter))

        assert fitter.calls == [["3:pt:body"]]
        assert _payload(outcome.slides[0], "pt")["body"] == PT_ANSWERS[0]
        assert _length_violations(outcome.slides) == []
        assert outcome.changed_indices == frozenset({3})
        assert (outcome.attempts, outcome.accepted, outcome.still_over) == (1, 1, 0)

    async def test_fields_within_budget_are_never_sent(self) -> None:
        """Scenario: Fields within budget are never sent to the model."""
        slides = [content_slide(3, pt_body=_LONG_PT, en_body=_SHORT_EN)]
        fitter = FakeFitter(answers={"3:pt:heading": "Outro título qualquer"})

        outcome = await fit_slides_to_budgets(_command(slides, fitter))

        asked = [item for call in fitter.calls for item in call]
        assert "3:pt:heading" not in asked and "3:en:body" not in asked
        assert _payload(outcome.slides[0], "pt")["heading"] == (
            "Revisões precisam de um dono"
        )

    async def test_nothing_over_budget_means_no_model_call(self) -> None:
        """Scenario: Fields within budget are never sent to the model (no call)."""
        slides = [content_slide(3, pt_body=_SHORT_PT, en_body=_SHORT_EN)]
        fitter = FakeFitter()

        outcome = await fit_slides_to_budgets(_command(slides, fitter))

        assert fitter.calls == []
        assert outcome.slides == slides and outcome.changed_indices == frozenset()

    async def test_portuguese_and_english_are_both_handled(self) -> None:
        """Scenario: Portuguese and English fields are both handled."""
        slides = [content_slide(3, pt_body=_LONG_PT, en_body=_LONG_EN)]
        fitter = FakeFitter()

        outcome = await fit_slides_to_budgets(_command(slides, fitter))

        assert fitter.calls == [["3:en:body", "3:pt:body"]]
        en_target = next(
            item for item in fitter.requests[0].targets if item.target.locale == "en"
        )
        assert en_target.target.source_text == _LONG_PT
        assert en_target.limit.max_characters == 220
        assert _payload(outcome.slides[0], "en")["body"] == EN_ANSWERS[0]
        assert _length_violations(outcome.slides) == []

    async def test_nested_summary_point_body_is_shortened(self) -> None:
        """Scenario: Nested summary point bodies are shortened."""
        slide = _summary_slide(long_index=1)
        before = _payload(slide, "pt")["summary_points"]
        fitter = FakeFitter(answers={"2:pt:summary_points[1].body": _ITEM_ANSWER})

        outcome = await fit_slides_to_budgets(_command([slide], fitter))

        assert fitter.calls == [["2:pt:summary_points[1].body"]]
        assert fitter.requests[0].targets[0].limit.max_characters == 90
        after = cast(
            list[dict[str, object]], _payload(outcome.slides[0], "pt")["summary_points"]
        )
        items = cast(list[dict[str, object]], before)
        assert after[0] == items[0] and after[2] == items[2]
        assert after[1]["body"] == _ITEM_ANSWER
        assert after[1]["title"] == items[1]["title"]
        assert _length_violations(outcome.slides) == []


@pytest.mark.unit
@pytest.mark.asyncio
class TestBoundedAndBestEffort:
    async def test_attempts_are_bounded(self) -> None:
        """Scenario: The attempts are bounded."""
        slides = [content_slide(3, pt_body=_LONG_PT, en_body=_SHORT_EN)]
        fitter = FakeFitter(answers={"3:pt:body": _LONG_PT + " Mais um ponto."})

        outcome = await fit_slides_to_budgets(_command(slides, fitter))

        assert len(fitter.calls) == COPY_BUDGET_FIT_MAX_ATTEMPTS == 2
        assert outcome.rejected == 2 and outcome.accepted == 0
        assert _payload(outcome.slides[0], "pt")["body"] == _LONG_PT
        assert outcome.still_over == 1

    async def test_custom_attempt_bound(self) -> None:
        """Scenario: The attempts are bounded (one attempt)."""
        slides = [content_slide(3, pt_body=_LONG_PT, en_body=_SHORT_EN)]
        fitter = FakeFitter(answers={"3:pt:body": _LONG_PT + " Mais um ponto."})

        await fit_slides_to_budgets(
            _command(slides, fitter, lambda c: replace(c, max_attempts=1))
        )

        assert len(fitter.calls) == 1

    async def test_shorter_but_still_too_long_is_kept_as_best_effort(self) -> None:
        """Scenario: A rewrite that is still too long is kept only when it is shorter."""
        longer = prose(PT_SENTENCES, 300)
        shorter = prose(PT_SENTENCES, 230)
        shortest = prose(PT_SENTENCES, 225)
        answers = iter([shorter, shortest])

        def answer(_item: FitTarget) -> str:
            return next(answers)

        slides = [content_slide(3, pt_body=longer, en_body=_SHORT_EN)]
        fitter = FakeFitter(answer_fn=answer)

        outcome = await fit_slides_to_budgets(_command(slides, fitter))

        body = str(_payload(outcome.slides[0], "pt")["body"])
        assert len(fitter.calls) == 2
        assert body == min(shorter, shortest, key=len)
        assert len(body) < len(longer)
        assert _length_violations(outcome.slides) == [
            (3, "pt", "body", "body_too_long")
        ]
        assert outcome.still_over == 1

    async def test_unbalanced_emphasis_is_rejected(self) -> None:
        """Scenario: A rewrite that breaks emphasis is rejected."""
        slides = [content_slide(3, pt_body=_LONG_PT, en_body=_SHORT_EN)]
        fitter = FakeFitter(
            answers={"3:pt:body": "Eu defino um **dono para cada pedido."}
        )

        outcome = await fit_slides_to_budgets(_command(slides, fitter))

        assert _payload(outcome.slides[0], "pt")["body"] == _LONG_PT
        assert outcome.changed_indices == frozenset()

    async def test_rewrite_repeating_another_field_is_rejected(self) -> None:
        """Scenario: A rewrite that breaks emphasis is rejected (any new violation)."""
        slide = _summary_slide(long_index=1)
        items = cast(list[dict[str, object]], _payload(slide, "pt")["summary_points"])
        fitter = FakeFitter(
            answers={"2:pt:summary_points[1].body": str(items[0]["body"])}
        )

        outcome = await fit_slides_to_budgets(_command([slide], fitter))

        assert outcome.changed_indices == frozenset() and outcome.rejected == 2

    async def test_dropped_final_punctuation_is_rejected(self) -> None:
        """Scenario: A rewrite that drops the final punctuation is rejected."""
        slides = [content_slide(3, pt_body=_LONG_PT, en_body=_SHORT_EN)]
        fitter = FakeFitter(
            answers={"3:pt:body": "Eu defino um dono para cada pedido de revisão,"}
        )

        outcome = await fit_slides_to_budgets(_command(slides, fitter))

        assert _payload(outcome.slides[0], "pt")["body"] == _LONG_PT

    async def test_forbidden_phrase_is_rejected(self) -> None:
        """Scenario: A rewrite with a forbidden persona phrase is rejected."""
        slides = [content_slide(3, pt_body=_LONG_PT, en_body=_SHORT_EN)]
        fitter = FakeFitter(
            answers={"3:pt:body": "Eu acho que um dono por pedido é um game changer."}
        )

        outcome = await fit_slides_to_budgets(
            _command(
                slides,
                fitter,
                lambda c: replace(c, forbidden_phrases=("Game Changer", " ")),
            )
        )

        assert _payload(outcome.slides[0], "pt")["body"] == _LONG_PT

    async def test_portuguese_answer_for_english_field_is_rejected(self) -> None:
        """Scenario: Portuguese and English fields are both handled (EN stays EN)."""
        slides = [content_slide(3, pt_body=_SHORT_PT, en_body=_LONG_EN)]
        fitter = FakeFitter(answers={"3:en:body": PT_ANSWERS[1]})

        outcome = await fit_slides_to_budgets(_command(slides, fitter))

        assert _payload(outcome.slides[0], "en")["body"] == _LONG_EN

    async def test_empty_or_identical_answers_are_rejected(self) -> None:
        """Scenario: A rewrite that is still too long is kept only when it is shorter."""
        slides = [content_slide(3, pt_body=_LONG_PT, en_body=_LONG_EN)]
        fitter = FakeFitter(answers={"3:pt:body": "  ", "3:en:body": _LONG_EN})

        outcome = await fit_slides_to_budgets(_command(slides, fitter))

        assert outcome.accepted == 0 and outcome.rejected == 4

    async def test_failing_model_leaves_the_copy(self) -> None:
        """Scenario: A failing model leaves the copy as it was."""
        slides = [content_slide(3, pt_body=_LONG_PT, en_body=_LONG_EN)]
        fitter = FakeFitter(error=RuntimeError("provider down"))

        outcome = await fit_slides_to_budgets(_command(slides, fitter))

        assert outcome.slides == slides
        assert len(fitter.calls) == 1 and outcome.changed_indices == frozenset()

    async def test_only_allowed_slides_are_touched(self) -> None:
        """Scenario: Fields within budget are never sent to the model (scope)."""
        slides = [
            content_slide(3, pt_body=_LONG_PT, en_body=_SHORT_EN),
            content_slide(4, pt_body=prose(PT_SENTENCES[1:], 230), en_body=_SHORT_EN),
        ]
        fitter = FakeFitter()

        outcome = await fit_slides_to_budgets(
            _command(slides, fitter, lambda c: replace(c, only_slides=frozenset({4})))
        )

        assert fitter.calls == [["4:pt:body"]]
        assert outcome.changed_indices == frozenset({4})


class _SlowFitter(FakeFitter):
    async def fit(self, request: FitRequest) -> dict[str, str]:
        await asyncio.sleep(1)
        return await super().fit(request)


@pytest.mark.unit
@pytest.mark.asyncio
class TestModelTimeoutAndLanguage:
    async def test_timeout_keeps_the_copy(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scenario: A model that times out leaves the copy as it was."""
        monkeypatch.setattr(copy_budget_fit, "COPY_BUDGET_FIT_TIMEOUT_SECONDS", 0.01)
        slides = [content_slide(3, pt_body=_LONG_PT, en_body=_SHORT_EN)]

        outcome = await fit_slides_to_budgets(_command(slides, _SlowFitter()))

        assert outcome.slides == slides
        assert outcome.attempts == 1 and outcome.changed_indices == frozenset()

    async def test_portuguese_field_answered_in_english_is_rejected(self) -> None:
        """Scenario: A Portuguese field answered in English is rejected."""
        slides = [content_slide(3, pt_body=_LONG_PT, en_body=_SHORT_EN)]
        fitter = FakeFitter(answers={"3:pt:body": _ENGLISH_FOR_PT})

        outcome = await fit_slides_to_budgets(
            _command(
                slides,
                fitter,
                lambda c: replace(c, policy_version="hero_lower_third_v1"),
            )
        )

        assert _payload(outcome.slides[0], "pt")["body"] == _LONG_PT
        assert outcome.rejected == 2

    async def test_excluded_field_is_never_asked(self) -> None:
        """Scenario: The owner's hook heading is never rewritten (excluded address)."""
        slides = [content_slide(3, pt_body=_LONG_PT, en_body=_LONG_EN)]
        fitter = FakeFitter()

        await fit_slides_to_budgets(
            _command(
                slides,
                fitter,
                lambda c: replace(c, excluded_fields=frozenset({(3, "pt", "body")})),
            )
        )

        assert fitter.calls == [["3:en:body"]]
