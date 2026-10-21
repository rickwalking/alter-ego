"""Quote cards, the caption footer and stored quote rows (ADR-0023).

Gherkin: tests/features/autopilot_pov_news_ae0406.feature
"""

from __future__ import annotations

from rag_backend.domain.content_mode import (
    is_pov_family,
    is_pov_news,
    pov_prompt_domain,
)
from rag_backend.domain.models.news_quote import (
    quote_from_row,
    quote_rows,
    quotes_from_rows,
)
from rag_backend.domain.news_quote_cards import (
    QuoteCardProblem,
    place_quote_cards,
    quote_card,
    quote_card_problems,
    with_en_quote_cards,
)
from rag_backend.domain.source_footer import (
    source_footer,
    source_label,
    with_source_footer,
)
from tests.unit.autopilot.news_quote_support import quote

_Q1 = quote()
_Q2 = quote(quote_id="q2", text_pt="Outra citação.", text_en="Another quote.")


def _draft(index: int, role: str, quote_id: str | None = None) -> dict[str, object]:
    draft: dict[str, object] = {"slide_index": index, "role": role, "title": "T"}
    if quote_id is not None:
        draft["quote_id"] = quote_id
    return draft


def _record(index: int, pt: str | None, en: str | None) -> dict[str, object]:
    def payload(text: str | None) -> dict[str, object]:
        body: dict[str, object] = {"heading": "H", "body": "B"}
        if text is not None:
            body["insight"] = {**quote_card(_Q1, text)}
        return body

    return {
        "slide_index": index,
        "presentation_pt": payload(pt),
        "presentation_en": payload(en),
    }


def test_mode_predicates() -> None:
    assert is_pov_family("pov") and is_pov_family("pov_news")
    assert not is_pov_family("news_analysis") and not is_pov_family(None)
    assert is_pov_news("pov_news") and not is_pov_news("pov")
    assert pov_prompt_domain("pov_news") == "carousel_pov_news"
    assert pov_prompt_domain("pov") == "carousel_pov"


# Scenario: A quote is placed verbatim by id, at most twice
def test_cards_are_placed_on_point_and_twist_at_most_twice() -> None:
    """Slot 1 is the hook (not a quote role), slot 5 would reuse q1, slot 7 is past the
    two-card cap and slot 8 is an unknown id.
    """
    drafts = [
        _draft(1, "hook", "q1"),
        _draft(4, "point", "q1"),
        _draft(5, "point", "q1"),
        _draft(6, "point", "q2"),
        _draft(7, "twist", "q2"),
        _draft(8, "twist", "q9"),
    ]
    placed = place_quote_cards(drafts, (_Q1, _Q2))
    cards = {d["slide_index"]: d.get("insight") for d in placed}
    assert cards[1] is None
    assert cards[4] == quote_card(_Q1, _Q1.text_pt)
    assert cards[5] is None
    assert cards[6] == quote_card(_Q2, _Q2.text_pt)
    assert cards[7] is None
    assert cards[8] is None
    assert all("quote_id" not in d for d in placed)


# Scenario: A model-written quote never reaches a slide
def test_model_written_insight_is_dropped() -> None:
    draft = {**_draft(4, "point"), "insight": {"quote": "Invented words"}}
    (placed,) = place_quote_cards([draft], (_Q1,))
    assert "insight" not in placed


def test_card_shape() -> None:
    assert quote_card(_Q1, "x") == {
        "quote": "x",
        "attribution": "Kanishk Jain",
        "name": "Kanishk Jain",
        "handle": "kanishksj01",
        "quote_id": "q1",
    }


def test_en_cards_follow_the_placed_pt_cards() -> None:
    """The input translations are left untouched."""
    placed = place_quote_cards([_draft(4, "point", "q1"), _draft(5, "point")], (_Q1,))
    translations: dict[int, dict[str, object]] = {
        4: {"heading": "EN", "body": "EN body"},
        5: {"heading": "EN 5", "body": "b"},
    }
    result = with_en_quote_cards(translations, placed, (_Q1,))
    assert result[4]["insight"] == quote_card(_Q1, _Q1.text_en)
    assert result[4]["heading"] == "EN"
    assert "insight" not in result[5]
    assert "insight" not in translations[4]


def test_en_cards_skip_missing_translations_and_unknown_ids() -> None:
    placed = place_quote_cards([_draft(4, "point", "q1")], (_Q1,))
    assert with_en_quote_cards({}, placed, (_Q1,)) == {}
    assert with_en_quote_cards({4: {}}, placed, ()) == {4: {}}
    no_index = [{"insight": quote_card(_Q1, "x")}]
    assert with_en_quote_cards({4: {}}, no_index, (_Q1,)) == {4: {}}


# Scenario: The autopilot content gate blocks an altered quote card
def test_verbatim_cards_have_no_problem() -> None:
    slides = [_record(4, _Q1.text_pt, _Q1.text_en), _record(5, None, None)]
    assert quote_card_problems(slides, (_Q1,)) == []


def test_altered_or_swapped_text_is_a_problem() -> None:
    slides = [
        _record(4, "Em um dia rodei agentes.", _Q1.text_en),
        _record(5, _Q1.text_pt, _Q1.text_pt),
    ]
    assert quote_card_problems(slides, (_Q1,)) == [
        QuoteCardProblem(rule="quote_not_verbatim", slide_index=4, locale="pt"),
        QuoteCardProblem(rule="quote_not_verbatim", slide_index=5, locale="en"),
    ]


def test_a_card_without_a_known_id_is_a_problem() -> None:
    slide = {
        "presentation_pt": {"insight": {"quote": "Anything"}},
        "presentation_en": "not a dict",
    }
    assert quote_card_problems([slide], (_Q1,)) == [
        QuoteCardProblem(rule="quote_not_verbatim", slide_index=None, locale="pt")
    ]


def test_a_third_card_is_a_deck_problem() -> None:
    slides = [_record(i, _Q1.text_pt, _Q1.text_en) for i in (4, 5, 6)]
    assert quote_card_problems(slides, (_Q1,)) == [
        QuoteCardProblem(rule="too_many_quote_cards")
    ]


# Scenario: The caption footer is written by code
def test_footer_labels_dedupes_and_keeps_source_order() -> None:
    sources = (
        "https://x.com/kanishksj01/status/1",
        "https://www.anthropic.com/news/x",
        "https://x.com/kanishksj01/status/2",
        "https://twitter.com/alexcovo_eth/status/3",
        "https://mobile.twitter.com/Other/status/4",
    )
    assert source_footer(sources) == (
        "Fontes: @kanishksj01, anthropic.com, @alexcovo_eth, @Other"
    )


def test_footer_dedupes_handles_case_insensitively() -> None:
    sources = (
        "https://x.com/KanishkSJ01/status/1",
        "https://x.com/kanishksj01/status/2",
        "https://www.Anthropic.com/a",
        "https://anthropic.com/b",
    )
    assert source_footer(sources) == "Fontes: @KanishkSJ01, anthropic.com"


def test_source_label_edge_cases() -> None:
    assert source_label("https://x.com/") == "x.com"
    assert source_label("not a url") == ""
    assert (
        source_label("https://News.YCombinator.com/item?id=1") == "news.ycombinator.com"
    )
    assert source_footer(("not a url",)) == ""


def test_with_source_footer_is_idempotent() -> None:
    sources = ("https://x.com/kanishksj01/status/1",)
    once = with_source_footer("Legenda.\n#ia", sources)
    assert once == "Legenda.\n#ia\n\nFontes: @kanishksj01"
    assert with_source_footer(once, sources) == once
    assert with_source_footer("", sources) == "Fontes: @kanishksj01"
    assert with_source_footer("Legenda.", ()) == "Legenda."


def test_quote_rows_round_trip() -> None:
    rows = quote_rows((_Q1, _Q2))
    assert quotes_from_rows(rows) == (_Q1, _Q2)
    assert rows[0]["id"] == "q1" and rows[0]["lang_original"] == "en"


def test_bad_rows_are_skipped() -> None:
    assert quotes_from_rows(None) == ()
    assert quotes_from_rows([1, {"id": "q1"}]) == ()
    assert quote_from_row({**_Q1.to_row(), "name": 3}) is None


_Q3 = quote(quote_id="q3", text_pt="Terceira.", text_en="Third.")


def test_a_third_distinct_quote_is_not_placed() -> None:
    drafts = [
        _draft(4, "point", "q1"),
        _draft(5, "point", "q2"),
        _draft(6, "point", "q3"),
    ]
    placed = place_quote_cards(drafts, (_Q1, _Q2, _Q3))
    assert [("insight" in d) for d in placed] == [True, True, False]


def test_exactly_two_cards_is_not_a_problem() -> None:
    slides = [_record(i, _Q1.text_pt, _Q1.text_en) for i in (4, 5)]
    assert quote_card_problems(slides, (_Q1,)) == []


def test_the_card_count_reads_the_pt_payloads() -> None:
    slides = [_record(i, _Q1.text_pt, None) for i in (4, 5, 6)]
    assert quote_card_problems(slides, (_Q1,)) == [
        QuoteCardProblem(rule="too_many_quote_cards")
    ]


def test_an_insight_without_quote_text_is_ignored() -> None:
    slide = {"presentation_pt": {"insight": {"heading": "x"}}}
    assert quote_card_problems([slide], (_Q1,)) == []


def test_a_non_text_quote_id_places_nothing() -> None:
    draft: dict[str, object] = {**_draft(4, "point"), "quote_id": ["q1"]}
    (placed,) = place_quote_cards([draft], (_Q1,))
    assert "insight" not in placed


def test_footer_after_trailing_whitespace() -> None:
    sources = ("https://x.com/kanishksj01/status/1",)
    assert with_source_footer("Legenda.\n", sources) == (
        "Legenda.\n\nFontes: @kanishksj01"
    )
    once = "Legenda.\n\nFontes: @kanishksj01"
    assert with_source_footer(once + "\n", sources) == once + "\n"
