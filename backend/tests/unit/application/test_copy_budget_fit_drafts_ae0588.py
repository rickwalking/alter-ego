"""The shorten step on content drafts: write-back and the QA evidence shapes.

Gherkin: tests/features/copy_fits_slide_budgets_ae0588.feature (section B).
The QA run of 2026-11-01 (``hero_lower_third_v4``) stopped at the content gate
with slide 1 PT/EN bodies of 237/245 characters, headings of 77 and 87
characters and slide 2 summary point bodies of 99-123 characters.
"""

from __future__ import annotations

from typing import cast

import pytest

from rag_backend.application.services.carousel.copy_budget_fit import (
    LENGTH_VIOLATION_CODES,
)
from rag_backend.application.services.carousel.copy_budget_fit_drafts import (
    DraftFitCommand,
    fit_drafts_to_budgets,
)
from rag_backend.application.services.carousel.copy_budget_fit_llm import FitTarget
from rag_backend.application.services.carousel.localized_slide_builder import (
    build_localized_slides,
)
from rag_backend.application.services.carousel.presentation_policy import (
    load_presentation_policy,
)
from rag_backend.application.services.carousel.presentation_review_pipeline import (
    validate_localized_slides,
)
from tests.unit.application.copy_budget_fit_fixtures_ae0588 import (
    EN_ANSWERS,
    EN_SENTENCES,
    POLICY_V4,
    PT_ANSWERS,
    PT_SENTENCES,
    FakeFitter,
    prose,
)

_PT_ITEM_BODIES = (
    "Eu reviso cada pedido com um dono claro e o time decide mais rápido no fim do "
    "dia, sem discussão sobre gosto.",
    "Uma regra escrita evita que a mesma conversa volte toda semana e libera o time "
    "para o que importa no código.",
    "Eu meço o tempo de cada revisão e corto o que sobra antes que vire retrabalho "
    "para quem entrega a versão.",
)
_EN_ITEM_BODIES = (
    "I review every request with a clear owner and the team decides faster at the "
    "end of the day, with no debate.",
    "A written rule stops the same talk from coming back every week and frees the "
    "team for what matters in the code.",
    "I measure the time of every review and cut the excess before it turns into "
    "rework for whoever ships.",
)
_INTRO_HEADING_PT = (
    "Revisões de código sem dono custam horas, retrabalho, brigas e atraso no time"
)
_CONTENT_HEADING_PT = (
    "O time perde horas toda semana quando as revisões de código não têm um dono "
    "muito claro"
)
_ITEM_TITLES_PT = ("Um dono por pedido", "Regra escrita", "Tempo medido")
_ITEM_TITLES_EN = ("One owner per request", "Written rule", "Measured time")


def _items(titles: tuple[str, ...], bodies: tuple[str, ...]) -> list[dict[str, object]]:
    return [
        {"icon_name": "target", "title": title, "body": body}
        for title, body in zip(titles, bodies, strict=True)
    ]


def _qa_drafts() -> list[dict[str, object]]:
    """Slide 1 (intro) and 2 (summary) and 3 (content) as the QA run had them."""
    intro_pt = {
        "slide_type": "intro",
        "heading": _INTRO_HEADING_PT,
        "body": prose(PT_SENTENCES, 237),
    }
    intro_en = {
        "slide_type": "intro",
        "heading": "Code reviews without an owner cost hours, rework and fights",
        "body": prose(EN_SENTENCES, 245),
    }
    summary_pt = {
        "slide_type": "summary",
        "heading": "O que muda quando cada revisão tem um dono",
        "body": "Resumo do que muda.",
        "summary_points": _items(_ITEM_TITLES_PT, _PT_ITEM_BODIES),
    }
    summary_en = {
        "slide_type": "summary",
        "heading": "What changes when every review has an owner",
        "body": "What changes, in short.",
        "summary_points": _items(_ITEM_TITLES_EN, _EN_ITEM_BODIES),
    }
    content_pt = {
        "slide_type": "content",
        "heading": _CONTENT_HEADING_PT,
        "body": PT_ANSWERS[2],
    }
    content_en = {
        "slide_type": "content",
        "heading": "Reviews need an owner",
        "body": EN_ANSWERS[2],
    }
    pairs = ((intro_pt, intro_en), (summary_pt, summary_en), (content_pt, content_en))
    return [
        {
            "slide_index": index,
            "slide_type": pt["slide_type"],
            "policy_version": POLICY_V4,
            "title": pt["heading"],
            "draft_text": pt["body"],
            "presentation_pt": pt,
            "presentation_en": en,
        }
        for index, (pt, en) in enumerate(pairs, start=1)
    ]


_FITTING: dict[str, tuple[str, ...]] = {
    "pt:heading": ("Revisão sem dono custa horas", "Um dono por revisão de código"),
    "en:heading": ("Reviews without an owner cost hours",),
    "pt:body": (
        "Eu vejo o time perder horas com revisões sem um objetivo claro.",
        "Eu reviso cada pedido com um dono e o time decide rápido.",
        "Uma regra escrita evita que a mesma conversa volte toda semana.",
        "Eu meço cada revisão e corto o que sobra antes do retrabalho.",
    ),
    "en:body": (
        "I see the team lose hours on reviews without a clear goal.",
        "I review every request with an owner and the team decides fast.",
        "A written rule stops the same talk from coming back every week.",
        "I measure every review and cut the excess before it becomes rework.",
    ),
}


def _within_limit(item: FitTarget) -> str:
    """A limit-respecting model: the first unused sentence of its kind that fits."""
    kind = item.target.field.rsplit(".", 1)[-1]
    pool = _FITTING[f"{item.target.locale}:{kind}"]
    position = int(item.target.target_id.split(":", 1)[0]) + item.target.field.count(
        "1"
    )
    position += 2 * item.target.field.count("2")
    for offset in range(len(pool)):
        text = pool[(position + offset) % len(pool)]
        if len(text) <= item.limit.max_characters:
            return text
    return pool[0]


def _length_codes(drafts: list[dict[str, object]]) -> list[tuple[object, ...]]:
    """Length violations of the drafts as built, before any repair."""
    report = validate_localized_slides(
        build_localized_slides(drafts), policy_version=POLICY_V4
    )
    return sorted(
        (v.slide_index, v.locale, v.field, v.code)
        for v in report.violations
        if v.code in LENGTH_VIOLATION_CODES
    )


@pytest.mark.unit
class TestQaEvidenceShapes:
    def test_the_drafts_reproduce_the_qa_lengths(self) -> None:
        """Scenario: The QA evidence shapes end with no length violation (background)."""
        drafts = _qa_drafts()
        intro_pt = cast(dict[str, object], drafts[0]["presentation_pt"])
        intro_en = cast(dict[str, object], drafts[0]["presentation_en"])
        policy = load_presentation_policy(POLICY_V4)

        assert len(str(intro_pt["body"])) >= 237 and len(str(intro_en["body"])) >= 245
        assert len(_INTRO_HEADING_PT) == 77 and len(_CONTENT_HEADING_PT) == 87
        assert (
            len(str(intro_pt["heading"]))
            > policy.copy_budgets["intro_heading"].max_characters
        )
        assert all(99 <= len(body) <= 123 for body in _PT_ITEM_BODIES + _EN_ITEM_BODIES)
        assert len(_length_codes(drafts)) == 10


@pytest.mark.unit
@pytest.mark.asyncio
class TestDraftWriteBack:
    async def test_qa_shapes_end_with_no_length_violation(self) -> None:
        """Scenario: The QA evidence shapes end with no length violation."""
        fitter = FakeFitter(answer_fn=_within_limit)

        result = await fit_drafts_to_budgets(
            DraftFitCommand(
                slide_drafts=_qa_drafts(), fitter=fitter, policy_version=POLICY_V4
            )
        )

        assert len(fitter.calls) == 1 and len(fitter.calls[0]) == 10
        assert _length_codes(result.slide_drafts) == []
        assert result.changed_indices == frozenset({1, 2, 3})

    async def test_shortened_copy_lands_in_drafts_and_translations(self) -> None:
        """Scenario: Shortened copy is written back to the drafts and EN translations."""
        drafts: list[dict[str, object]] = [
            {
                "slide_index": 3,
                "slide_type": "content",
                "policy_version": POLICY_V4,
                "title": "Revisões precisam de um dono",
                "draft_text": prose(PT_SENTENCES, 230),
            }
        ]
        translations = {
            "3": {
                "heading": "Reviews need an owner",
                "body": prose(EN_SENTENCES, 230),
                "long_form_notes": "Notes stay.",
            }
        }
        fitter = FakeFitter()

        result = await fit_drafts_to_budgets(
            DraftFitCommand(
                slide_drafts=drafts, fitter=fitter, translations_en=translations
            )
        )

        draft = result.slide_drafts[0]
        assert draft["draft_text"] == PT_ANSWERS[0]
        assert (
            cast(dict[str, object], draft["presentation_pt"])["body"] == PT_ANSWERS[0]
        )
        assert (
            cast(dict[str, object], draft["presentation_en"])["body"] == EN_ANSWERS[0]
        )
        en = cast(dict[str, dict[str, object]], result.translations_en)["3"]
        assert en["body"] == EN_ANSWERS[0] and en["long_form_notes"] == "Notes stay."
        assert _length_codes(result.slide_drafts) == []

    async def test_no_translations_stay_absent(self) -> None:
        """Scenario: Shortened copy is written back to the drafts and EN translations (none)."""
        result = await fit_drafts_to_budgets(
            DraftFitCommand(
                slide_drafts=_qa_drafts(),
                fitter=FakeFitter(answer_fn=_within_limit),
                policy_version=POLICY_V4,
            )
        )

        assert result.translations_en is None

    async def test_nothing_to_fit_returns_the_input(self) -> None:
        """Scenario: Fields within budget are never sent to the model (drafts)."""
        fitter = FakeFitter()
        empty = await fit_drafts_to_budgets(DraftFitCommand([], fitter))
        drafts = _qa_drafts()[2:]
        cast(dict[str, object], drafts[0]["presentation_pt"])["heading"] = "Curto"

        same = await fit_drafts_to_budgets(
            DraftFitCommand(drafts, fitter, translations_en={"3": {}})
        )

        assert empty.slide_drafts == [] and fitter.calls == []
        assert same.slide_drafts is drafts and same.translations_en == {"3": {}}

    async def test_scope_limits_the_slides(self) -> None:
        """Scenario: Fields within budget are never sent to the model (scoped revision)."""
        fitter = FakeFitter(answer_fn=_within_limit)

        result = await fit_drafts_to_budgets(
            DraftFitCommand(
                slide_drafts=_qa_drafts(),
                fitter=fitter,
                policy_version=POLICY_V4,
                scope=frozenset({3}),
            )
        )

        assert fitter.calls == [["3:pt:heading"]]
        assert result.changed_indices == frozenset({3})


_LONG_EN_HOOK = (
    "Code reviews without a clear owner cost the whole team hours, rework and fights"
)


def _hook_drafts() -> list[dict[str, object]]:
    drafts = _qa_drafts()[:1]
    en = cast(dict[str, object], drafts[0]["presentation_en"])
    en["heading"] = _LONG_EN_HOOK
    return drafts


async def _asked(command_hook: tuple[str, str]) -> list[str]:
    hook_text, approved = command_hook
    fitter = FakeFitter(answer_fn=_within_limit)
    await fit_drafts_to_budgets(
        DraftFitCommand(
            slide_drafts=_hook_drafts(),
            fitter=fitter,
            policy_version=POLICY_V4,
            hook_text=hook_text,
            approved_hook_title=approved,
        )
    )
    return fitter.calls[0]


@pytest.mark.unit
@pytest.mark.asyncio
class TestOwnerHook:
    async def test_picked_hook_heading_is_left_to_block(self) -> None:
        """Scenario: The owner's hook heading is never rewritten."""
        asked = await _asked(("Revisões sem dono custam horas", ""))

        assert len(_LONG_EN_HOOK) > 72
        assert "1:pt:heading" not in asked
        assert "1:en:heading" in asked

    async def test_approved_outline_title_is_left_to_block(self) -> None:
        """Scenario: The owner's hook heading is never rewritten (approved outline title)."""
        asked = await _asked(("", _INTRO_HEADING_PT))

        assert "1:pt:heading" not in asked and "1:en:heading" in asked

    async def test_unowned_hook_heading_is_shortened(self) -> None:
        """Scenario: The owner's hook heading is never rewritten (not the owner's)."""
        asked = await _asked(("", "Outro título aprovado"))

        assert "1:pt:heading" in asked
