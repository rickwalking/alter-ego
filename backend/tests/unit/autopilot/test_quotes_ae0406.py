"""Scout quote rules of one ``pov_news`` topic (AE-0406, spec §4).

Gherkin: tests/features/autopilot_pov_news_ae0406.feature
"""

from __future__ import annotations

import pytest

from rag_backend.modules.autopilot.domain.quotes import (
    QuoteFacts,
    QuoteProblem,
    clean_quote,
    keyed_post_texts,
    quote_urls,
    quotes_problem,
    status_key,
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
        ({"excerpt": ""}, "quote_invalid", "quotes[0].excerpt"),
        # PR #124 review: a missing (blank) field is quote_invalid on that field.
        ({"url": ""}, "quote_invalid", "quotes[0].url"),
        ({"handle": ""}, "quote_invalid", "quotes[0].handle"),
        ({"lang_original": ""}, "quote_invalid", "quotes[0].lang_original"),
        ({"quote_id": ""}, "quote_invalid", "quotes[0].id"),
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


# PR #124 review: the stored post and the cited URL differ only in handle case.
def test_handle_case_does_not_matter_for_the_stored_post_or_the_sources() -> None:
    stored = "https://x.com/KanishkSJ01/status/1234567890"
    facts = QuoteFacts(sources=frozenset({stored}), post_texts={stored: POST_TEXT})
    assert quotes_problem((quote(),), facts) is None
    shouting = quote(url=stored, handle="KANISHKSJ01")
    assert quotes_problem((shouting,), _FACTS) is None


def test_status_key_lowercases_handle_and_keeps_other_urls() -> None:
    assert status_key("https://x.com/KanishkSJ01/status/1") == (
        "https://x.com/kanishksj01/status/1"
    )
    assert status_key("https://twitter.com/A/status/2") == "https://x.com/a/status/2"
    assert status_key("https://Example.com/A") == "https://Example.com/A"
    assert keyed_post_texts({
        "https://x.com/A/status/1": "a",
        "https://x.com/a/status/1": "b",
    }) == {"https://x.com/a/status/1": "a"}


def test_the_first_blank_field_wins() -> None:
    blank = quote(text_pt="", text_en="", name="")
    assert quotes_problem((blank,), _FACTS) == QuoteProblem(
        reason="quote_invalid", field="quotes[0].name"
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


# QA mutation review: boundaries of the spec §4 limits.
def test_name_of_60_characters_and_pt_language_are_accepted() -> None:
    assert _problem(name="x" * 60) is None
    assert _problem(lang_original="pt") is None


def test_excerpt_of_280_characters_is_accepted_and_281_is_not() -> None:
    longest = "w" * 280
    post = f"{longest}w "
    facts = QuoteFacts(sources=frozenset({POST_URL}), post_texts={POST_URL: post})
    assert quotes_problem((quote(excerpt=longest),), facts) is None
    assert quotes_problem((quote(excerpt=longest + "w"),), facts) == QuoteProblem(
        reason="quote_not_in_post", field="quotes[0].excerpt"
    )


def test_a_stored_post_not_listed_in_sources_is_a_source_problem() -> None:
    facts = QuoteFacts(sources=frozenset({OTHER_URL}), post_texts={POST_URL: POST_TEXT})
    assert quotes_problem((quote(),), facts) == QuoteProblem(
        reason="quote_source_invalid", field="quotes[0].url"
    )


def test_clean_quote_cleans_every_field() -> None:
    dirty = quote(
        url=f" {POST_URL}\x00",
        handle=" kanishksj01 ",
        lang_original=" en\x00",
        text_pt=" t\x00 ",
        text_en=" e ",
    )
    cleaned = clean_quote(dirty)
    assert (cleaned.url, cleaned.handle, cleaned.lang_original) == (
        POST_URL,
        "kanishksj01",
        "en",
    )
    assert (cleaned.text_pt, cleaned.text_en) == ("t", "e")


# QA security review: control characters never reach the stored excerpt.
def test_clean_quote_spaces_line_breaks_and_drops_controls_in_the_excerpt() -> None:
    cleaned = clean_quote(quote(excerpt=" In just a day\x00 I have\r\nrun "))
    assert cleaned.excerpt == "In just a day I have run"
