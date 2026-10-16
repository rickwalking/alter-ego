"""Scout quote rules of one ``pov_news`` topic (AE-0406, spec §4).

Gherkin: tests/features/autopilot_pov_news_ae0406.feature
"""

from __future__ import annotations

import pytest

from rag_backend.modules.autopilot.domain.quotes import (
    QuoteFacts,
    QuoteProblem,
    clean_quote,
    quote_urls,
    quotes_problem,
)
from tests.unit.autopilot.news_quote_support import (
    OTHER_URL,
    POST_TEXT,
    POST_URL,
    quote,
)

_FACTS = QuoteFacts(
    sources=frozenset({POST_URL, OTHER_URL}), post_texts={POST_URL: POST_TEXT}
)
_SIXTEEN = " ".join(["palavra"] * 16)
_NINETEEN = " ".join(["word"] * 19)


def _problem(**changes: str) -> QuoteProblem | None:
    return quotes_problem((quote(**changes),), _FACTS)


# Scenario: A pov_news topic with one verified quote is accepted and queued
def test_the_spec_example_is_verified() -> None:
    assert quotes_problem((quote(),), _FACTS) is None
    assert quotes_problem((), _FACTS) is None


def test_handle_comparison_ignores_case() -> None:
    assert _problem(handle="KanishkSJ01") is None


def test_word_limits_are_inclusive() -> None:
    assert _problem(text_pt=" ".join(["p"] * 15), text_en=" ".join(["w"] * 18)) is None


# Scenario Outline: A quote problem rejects only that topic
@pytest.mark.parametrize(
    ("changes", "reason", "field"),
    [
        ({"quote_id": "q0"}, "quote_invalid", "quotes[0].id"),
        ({"quote_id": "q10"}, "quote_invalid", "quotes[0].id"),
        ({"quote_id": "Q1"}, "quote_invalid", "quotes[0].id"),
        ({"name": "x" * 61}, "quote_invalid", "quotes[0].name"),
        ({"name": ""}, "quote_invalid", "quotes[0].name"),
        ({"lang_original": "es"}, "quote_invalid", "quotes[0].lang_original"),
        ({"text_pt": ""}, "quote_invalid", "quotes[0].text_pt"),
        ({"text_en": ""}, "quote_invalid", "quotes[0].text_en"),
        ({"name": "see www.evil.example"}, "url_in_text", "quotes[0].name"),
        ({"excerpt": "go to https://e.x now"}, "url_in_text", "quotes[0].excerpt"),
        ({"text_pt": "veja www.e.com"}, "url_in_text", "quotes[0].text_pt"),
        ({"text_en": "see https://e.x"}, "url_in_text", "quotes[0].text_en"),
        (
            {"url": "https://x.com/someone/status/99"},
            "quote_source_invalid",
            "quotes[0].url",
        ),
        (
            {"url": "https://twitter.com/kanishksj01/status/1234567890"},
            "quote_source_invalid",
            "quotes[0].url",
        ),
        ({"url": "https://example.com/post"}, "quote_source_invalid", "quotes[0].url"),
        (
            {"url": OTHER_URL, "handle": "alexcovo_eth"},
            "quote_source_invalid",
            "quotes[0].url",
        ),
        ({"handle": "someone_else"}, "quote_handle_mismatch", "quotes[0].handle"),
        ({"excerpt": "hundreds of agents"}, "quote_not_in_post", "quotes[0].excerpt"),
        ({"excerpt": "in just a day"}, "quote_not_in_post", "quotes[0].excerpt"),
        ({"excerpt": "a" * 281}, "quote_not_in_post", "quotes[0].excerpt"),
        ({"excerpt": ""}, "quote_not_in_post", "quotes[0].excerpt"),
        ({"text_pt": _SIXTEEN}, "quote_too_long", "quotes[0].text_pt"),
        ({"text_en": _NINETEEN}, "quote_too_long", "quotes[0].text_en"),
    ],
)
def test_each_rule_names_its_reason_and_field(
    changes: dict[str, str], reason: str, field: str
) -> None:
    assert _problem(**changes) == QuoteProblem(reason=reason, field=field)


# Scenario: Four quotes are one topic's quote_invalid
def test_more_than_three_quotes_is_invalid() -> None:
    quotes = tuple(quote(quote_id=f"q{i}") for i in range(1, 5))
    assert quotes_problem(quotes, _FACTS) == QuoteProblem(
        reason="quote_invalid", field="quotes"
    )


def test_three_quotes_are_allowed() -> None:
    quotes = tuple(quote(quote_id=f"q{i}") for i in range(1, 4))
    assert quotes_problem(quotes, _FACTS) is None


# Scenario: Duplicate quote ids are invalid
def test_duplicate_ids_point_at_the_second_quote() -> None:
    assert quotes_problem((quote(), quote()), _FACTS) == QuoteProblem(
        reason="quote_invalid", field="quotes[1].id"
    )


def test_the_second_quote_is_named_by_its_index() -> None:
    bad = quote(quote_id="q2", handle="other")
    assert quotes_problem((quote(), bad), _FACTS) == QuoteProblem(
        reason="quote_handle_mismatch", field="quotes[1].handle"
    )


def test_clean_quote_strips_controls_and_spaces() -> None:
    dirty = quote(
        name=" Kanishk\x00 Jain ", quote_id=" q1 ", excerpt=f"  {quote().excerpt} "
    )
    cleaned = clean_quote(dirty)
    assert cleaned.name == "Kanishk Jain"
    assert cleaned.quote_id == "q1"
    assert cleaned.excerpt == quote().excerpt


def test_quote_urls_keeps_only_status_urls() -> None:
    quotes = (quote(), quote(url="https://example.com/a"))
    assert quote_urls(quotes) == (POST_URL,)
