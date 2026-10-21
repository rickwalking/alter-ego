"""A correct model rewrite clears casing markers; @handles keep case.

Gherkin: tests/features/autofix_escalation_ae0407.feature (items 4 and 5).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import pytest

from rag_backend.application.services.carousel.owner_autofix_plan import (
    AutofixContext,
)
from rag_backend.application.services.carousel.presentation_casing import (
    repair_casing,
    sentence_case_findings,
)
from rag_backend.application.services.carousel.presentation_policy import (
    load_presentation_policy,
)
from rag_backend.application.services.carousel.sentence_case import (
    capitalize_first_letter,
    capitalize_sentence_starts,
    has_lowercase_sentence,
    starts_lowercase,
)
from rag_backend.application.services.carousel.slide_fix_casing import (
    MarkerClear,
    clear_rewritten_casing_markers,
)
from rag_backend.application.services.carousel.slide_fix_loop import (
    LoopContext,
    fix_slide,
)
from rag_backend.application.services.carousel.slide_fix_targets import slide_issues
from rag_backend.application.services.carousel.slide_fix_types import (
    DeckContext,
    SlideFixSettings,
    SlideFixTools,
    SlideTarget,
)
from tests.unit.application.copy_hygiene_fixtures_ae0401 import (
    POV,
    en,
    prod_deck,
    pt,
)

SLIDE = 8
HEADING_CODE_PT = "heading_not_sentence_case_pt"
HEADING_CODE_EN = "heading_not_sentence_case_en"
NEW_HEADING_PT = "Checklist para salvar antes do PR"
POLICY = load_presentation_policy(POV)


def _marker(locale: str, code: str, path: str = "heading") -> dict[str, object]:
    return {"locale": locale, "field": path, "code": code}


def _slide_8(*markers: dict[str, object]) -> list[dict[str, object]]:
    deck = prod_deck()
    deck[SLIDE - 1]["casing_repairs"] = list(markers)
    return deck


def _answer(**locales: dict[str, object]) -> str:
    return json.dumps(locales, ensure_ascii=False)


def _with_answer(record: dict[str, object], **copy: str) -> dict[str, object]:
    updated = dict(record)
    updated["presentation_pt"] = {**pt([record], 1), **copy}
    return updated


@dataclass
class _Rewriter:
    answer: str
    prompts: list[str] = field(default_factory=list)

    async def rewrite(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.answer


@pytest.mark.unit
class TestMarkerClear:
    def test_the_marker_blocks_like_in_prod(self) -> None:
        deck = _slide_8(_marker("pt", HEADING_CODE_PT))
        codes = [issue.code for issue in slide_issues(deck, POV).get(SLIDE, [])]
        assert codes == [HEADING_CODE_PT]

    def test_a_correct_rewrite_drops_the_marker(self) -> None:
        record = _slide_8(_marker("pt", HEADING_CODE_PT))[SLIDE - 1]
        candidate = _with_answer(record, heading=NEW_HEADING_PT)
        answer = _answer(pt={"heading": NEW_HEADING_PT})
        cleared = clear_rewritten_casing_markers(candidate, MarkerClear(answer, POLICY))
        assert "casing_repairs" not in cleared
        assert record["casing_repairs"] == [_marker("pt", HEADING_CODE_PT)]

    def test_a_lowercase_rewrite_keeps_the_marker(self) -> None:
        """Scenario: A rewrite that still starts lowercase keeps the marker."""
        record = _slide_8(_marker("pt", HEADING_CODE_PT))[SLIDE - 1]
        lowered = "checklist para salvar antes do PR"
        candidate = _with_answer(record, heading=lowered)
        answer = _answer(pt={"heading": lowered})
        cleared = clear_rewritten_casing_markers(candidate, MarkerClear(answer, POLICY))
        assert cleared["casing_repairs"] == [_marker("pt", HEADING_CODE_PT)]

    def test_an_unanswered_field_keeps_its_marker(self) -> None:
        """Scenario: A field the model did not answer keeps its marker."""
        record = _slide_8(
            _marker("pt", HEADING_CODE_PT), _marker("en", HEADING_CODE_EN)
        )[SLIDE - 1]
        candidate = _with_answer(record, heading=NEW_HEADING_PT)
        answer = _answer(pt={"heading": NEW_HEADING_PT})
        cleared = clear_rewritten_casing_markers(candidate, MarkerClear(answer, POLICY))
        assert cleared["casing_repairs"] == [_marker("en", HEADING_CODE_EN)]

    def test_an_answer_that_did_not_land_keeps_the_marker(self) -> None:
        """A list of another size is not merged, so the old text stays."""
        record = _slide_8(_marker("pt", HEADING_CODE_PT, "summary_points[0].title"))[
            SLIDE - 1
        ]
        answer = _answer(pt={"summary_points": [{"title": "Arquivos certos"}]})
        cleared = clear_rewritten_casing_markers(record, MarkerClear(answer, POLICY))
        assert cleared["casing_repairs"] == record["casing_repairs"]

    def test_an_item_rewrite_drops_its_marker(self) -> None:
        record = _slide_8(
            _marker("pt", "body_not_sentence_case_pt", "summary_points[1].body")
        )[SLIDE - 1]
        points = pt([record], 1)["summary_points"]
        assert isinstance(points, list)
        answered = [dict(point) for point in points]
        answered[1]["body"] = "Liste o que o agente não pode tocar."
        candidate = _with_answer(record)
        candidate["presentation_pt"] = {**pt([record], 1), "summary_points": answered}
        answer = _answer(pt={"summary_points": answered})
        cleared = clear_rewritten_casing_markers(candidate, MarkerClear(answer, POLICY))
        assert "casing_repairs" not in cleared

    @pytest.mark.parametrize("answer", ["not json", _answer(de={"heading": "X"})])
    def test_no_usable_answer_changes_nothing(self, answer: str) -> None:
        record = _slide_8(_marker("pt", HEADING_CODE_PT))[SLIDE - 1]
        assert (
            clear_rewritten_casing_markers(record, MarkerClear(answer, POLICY))
            == record
        )

    def test_a_record_without_markers_is_returned_as_is(self) -> None:
        record = prod_deck()[0]
        assert (
            clear_rewritten_casing_markers(record, MarkerClear("{}", POLICY)) is record
        )

    def test_malformed_markers_are_kept(self) -> None:
        record = _slide_8()[SLIDE - 1]
        record["casing_repairs"] = ["junk", _marker("pt", HEADING_CODE_PT)]
        candidate = _with_answer(record, heading=NEW_HEADING_PT)
        answer = _answer(pt={"heading": NEW_HEADING_PT})
        cleared = clear_rewritten_casing_markers(candidate, MarkerClear(answer, POLICY))
        assert cleared["casing_repairs"] == ["junk"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_slide_8_with_only_markers_is_fixed() -> None:
    """Scenario: Slide 8: casing markers only, rewritten correctly, slide fixed."""
    deck = _slide_8(_marker("pt", HEADING_CODE_PT))
    issues = tuple(slide_issues(deck, POV)[SLIDE])
    rewriter = _Rewriter(_answer(pt={"heading": NEW_HEADING_PT}))
    context = LoopContext(
        deck=DeckContext(
            records=deck,
            policy_version=POV,
            autofix=AutofixContext(policy=POLICY),
            scored=False,
        ),
        tools=SlideFixTools(rewriter=rewriter),
        settings=SlideFixSettings(),
    )
    result = await fix_slide(
        SlideTarget(slide_index=SLIDE, record=deck[SLIDE - 1], issues=issues), context
    )
    assert result.fixed
    assert [a.outcome for a in result.attempts] == ["fixed"]
    assert "casing_repairs" not in result.record
    assert pt([result.record], 1)["heading"] == NEW_HEADING_PT
    assert en([result.record], 1) == en(deck, SLIDE)


@pytest.mark.unit
class TestHandlesAndUrls:
    """Item 5: an @handle or a URL keeps its case."""

    def test_a_handle_start_is_left_alone(self) -> None:
        """Scenario: A sentence starting with an @handle is left alone."""
        text = "@taylorhbuilds viu o modelo falhar. depois testou."
        assert capitalize_sentence_starts(text) == (
            "@taylorhbuilds viu o modelo falhar. Depois testou."
        )
        assert has_lowercase_sentence(text)
        assert not has_lowercase_sentence("@taylorhbuilds viu o modelo falhar.")
        assert not starts_lowercase("@taylorhbuilds viu")
        assert capitalize_first_letter("@taylorhbuilds viu") == "@taylorhbuilds viu"

    @pytest.mark.parametrize(
        "text",
        [
            "https://example.com mostra os números",
            "http://example.com mostra",
            "www.example.com mostra",
            "HTTPS://example.com mostra",
            '"@karpathy disse isso"',
            "<strong>@karpathy</strong> disse",
        ],
    )
    def test_a_url_or_quoted_handle_start_is_left_alone(self, text: str) -> None:
        """Scenario: A sentence starting with a URL is left alone."""
        assert not starts_lowercase(text)
        assert capitalize_first_letter(text) == text

    def test_a_plain_lowercase_start_is_still_repaired(self) -> None:
        """Scenario: A plain lowercase start is still repaired."""
        assert starts_lowercase("taylor viu o modelo falhar")
        assert capitalize_first_letter("taylor viu o modelo falhar") == (
            "Taylor viu o modelo falhar"
        )
        assert (
            capitalize_first_letter("e-mail a@b.com chegou") == "E-mail a@b.com chegou"
        )

    def test_the_casing_rules_and_repair_keep_the_handle(self) -> None:
        handle = {"slide_type": "point", "heading": "@taylorhbuilds testou"}
        plain = {"slide_type": "point", "heading": "taylor testou"}

        def fields(payload: dict[str, object]) -> set[str]:
            return {f.field for f in sentence_case_findings(payload, "pt", POLICY)}

        assert "heading" not in fields(handle)
        assert "heading" in fields(plain)
        assert repair_casing(handle, "pt", POLICY)["heading"] == "@taylorhbuilds testou"
        assert repair_casing(plain, "pt", POLICY)["heading"] == "Taylor testou"
