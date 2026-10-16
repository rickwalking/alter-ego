"""Excerpt normalisation and matching (AE-0406, spec §4).

Gherkin: tests/features/autopilot_pov_news_ae0406.feature
"""

from __future__ import annotations

from rag_backend.modules.autopilot.domain.quote_text import (
    excerpt_in_post,
    normalize_quote_text,
    spaced,
    word_count,
)
from tests.unit.autopilot.news_quote_support import EXCERPT, POST_TEXT

# Curly quotes built from code points (ruff RUF001 flags them as literals).
_LDQ, _RDQ, _LSQ, _RSQ = chr(0x201C), chr(0x201D), chr(0x2018), chr(0x2019)


# Scenario: A pov_news topic with one verified quote is accepted and queued
def test_spec_example_excerpt_matches() -> None:
    assert excerpt_in_post(EXCERPT, POST_TEXT) is True


# Scenario: Excerpt matching ignores curly quotes, CRLF and whitespace runs only
def test_curly_quotes_become_straight() -> None:
    curly = f"{_LDQ}Agents{_RDQ} don{_RSQ}t {_LSQ}wait{_RSQ}"
    assert normalize_quote_text(curly) == "\"Agents\" don't 'wait'"


def test_crlf_and_whitespace_runs_become_one_space() -> None:
    post = 'He said "ship it"\r\n  and   then\tleft.'
    assert excerpt_in_post(f"said {_LDQ}ship it{_RDQ} and then left.", post) is True


def test_nfc_composes_accents() -> None:
    decomposed = "revisão"
    assert normalize_quote_text(decomposed) == "revisão"
    assert excerpt_in_post("revisão", f"a {decomposed} b") is True


def test_ends_are_trimmed() -> None:
    assert normalize_quote_text("  hello  \n") == "hello"


# Scenario: Emoji and case are compared exactly
def test_emoji_and_case_must_match() -> None:
    post = "Running agents \U0001f680 in parallel."
    assert excerpt_in_post("agents \U0001f680 in parallel", post) is True
    assert excerpt_in_post("Agents \U0001f680 in parallel", post) is False
    assert excerpt_in_post("agents in parallel", post) is False


def test_punctuation_and_ellipsis_must_match() -> None:
    assert excerpt_in_post("In just a day...", POST_TEXT) is False
    assert excerpt_in_post("[...] cloud agents", POST_TEXT) is False


# Scenario: an excerpt past the 600-character cut does not match
def test_excerpt_past_the_600_character_cut_never_matches() -> None:
    post = ("a" * 590) + " tail words that go past the cut"
    assert excerpt_in_post("a tail", post) is True
    assert excerpt_in_post("tail words that go past", post) is False


def test_blank_excerpt_never_matches() -> None:
    assert excerpt_in_post("   ", POST_TEXT) is False


def test_spaced_and_word_count() -> None:
    assert spaced("a\n\nb\tc") == "a b c"
    assert word_count("  one two\nthree ") == 3


# QA mutation review: the stored text is cut at exactly 600 characters.
def test_the_cut_is_exactly_600_characters() -> None:
    at_cut = "a" * 594 + " tail"  # 599 characters
    assert excerpt_in_post("a tail", at_cut + "x") is True
    past_cut = "a" * 596 + " tail"  # 601 characters
    assert excerpt_in_post("a tail", past_cut) is False
