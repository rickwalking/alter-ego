"""Scout quote rules for ``pov_news`` topics (AE-0406, ADR-0023, spec §4).

A quote is verified data: its excerpt must be a piece of a post the backend
stored through ``POST /x-signals``. Every problem rejects only that topic.
"""

from __future__ import annotations

from typing import Final

from rag_backend.modules.autopilot.constants import X_POST_TEXT_MAX_CHARS

QUOTES_MAX = 3
# Schema abuse caps only: the real limits are domain rules with reason codes,
# so a long name is ``quote_invalid`` for one topic, not a 422 for the batch.
QUOTES_SCHEMA_MAX = 10
QUOTE_FIELD_SCHEMA_MAX_CHARS = 2000
QUOTE_ID_PATTERN = r"^q[1-9]$"
QUOTE_NAME_MAX_CHARS = 60
QUOTE_EXCERPT_MAX_CHARS = 280
QUOTE_TEXT_PT_MAX_WORDS = 15
QUOTE_TEXT_EN_MAX_WORDS = 18
QUOTE_LANG_EN = "en"
QUOTE_LANG_PT = "pt"
QUOTE_LANGUAGES: frozenset[str] = frozenset({QUOTE_LANG_EN, QUOTE_LANG_PT})
# The stored post text is cut at 600 characters; an excerpt past it never matches.
STORED_POST_TEXT_MAX_CHARS = X_POST_TEXT_MAX_CHARS

# Excerpt normalisation (spec §4): curly quotes become straight ones.
CURLY_QUOTE_TABLE: dict[int, str] = {
    0x201C: '"',  # left double quotation mark
    0x201D: '"',  # right double quotation mark
    0x2018: "'",  # left single quotation mark
    0x2019: "'",  # right single quotation mark
}
UNICODE_NFC: Final = "NFC"
WHITESPACE_RUN_PATTERN = r"\s+"
SINGLE_SPACE = " "

# Reason codes (new in spec v2).
REASON_QUOTE_INVALID = "quote_invalid"
REASON_QUOTE_SOURCE_INVALID = "quote_source_invalid"
REASON_QUOTE_HANDLE_MISMATCH = "quote_handle_mismatch"
REASON_QUOTE_NOT_IN_POST = "quote_not_in_post"
REASON_QUOTE_TOO_LONG = "quote_too_long"

# ``field`` paths on a rejection.
FIELD_QUOTES = "quotes"
FIELD_QUOTE_TEMPLATE = "quotes[{index}].{name}"
FIELD_ID = "id"
FIELD_URL = "url"
FIELD_HANDLE = "handle"
FIELD_NAME = "name"
FIELD_EXCERPT = "excerpt"
FIELD_LANG = "lang_original"
FIELD_TEXT_PT = "text_pt"
FIELD_TEXT_EN = "text_en"

__all__ = [
    "CURLY_QUOTE_TABLE",
    "FIELD_EXCERPT",
    "FIELD_HANDLE",
    "FIELD_ID",
    "FIELD_LANG",
    "FIELD_NAME",
    "FIELD_QUOTES",
    "FIELD_QUOTE_TEMPLATE",
    "FIELD_TEXT_EN",
    "FIELD_TEXT_PT",
    "FIELD_URL",
    "QUOTES_MAX",
    "QUOTES_SCHEMA_MAX",
    "QUOTE_EXCERPT_MAX_CHARS",
    "QUOTE_FIELD_SCHEMA_MAX_CHARS",
    "QUOTE_ID_PATTERN",
    "QUOTE_LANGUAGES",
    "QUOTE_LANG_EN",
    "QUOTE_LANG_PT",
    "QUOTE_NAME_MAX_CHARS",
    "QUOTE_TEXT_EN_MAX_WORDS",
    "QUOTE_TEXT_PT_MAX_WORDS",
    "REASON_QUOTE_HANDLE_MISMATCH",
    "REASON_QUOTE_INVALID",
    "REASON_QUOTE_NOT_IN_POST",
    "REASON_QUOTE_SOURCE_INVALID",
    "REASON_QUOTE_TOO_LONG",
    "SINGLE_SPACE",
    "STORED_POST_TEXT_MAX_CHARS",
    "UNICODE_NFC",
    "WHITESPACE_RUN_PATTERN",
]
