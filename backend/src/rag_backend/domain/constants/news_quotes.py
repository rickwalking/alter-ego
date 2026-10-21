"""Quote cards and the source footer of ``pov_news`` decks (ADR-0023).

A quote card goes on a point or twist slide, at most ``MAX_QUOTE_CARDS`` per
deck, and is rendered from the slide's ``insight`` dict by the ``insight_quote``
strategy. The deterministic check requires a placed quote to be exactly one of
the supplied quotes. The caption footer reads ``Fontes: @handle, domain.com``.
"""

from __future__ import annotations

from rag_backend.domain.constants.presentation_roles import ROLE_POINT, ROLE_TWIST

QUOTE_KEY_ID = "id"
QUOTE_KEY_URL = "url"
QUOTE_KEY_HANDLE = "handle"
QUOTE_KEY_NAME = "name"
QUOTE_KEY_EXCERPT = "excerpt"
QUOTE_KEY_LANG = "lang_original"
QUOTE_KEY_TEXT_PT = "text_pt"
QUOTE_KEY_TEXT_EN = "text_en"

QUOTE_CARD_ROLES: frozenset[str] = frozenset({ROLE_POINT, ROLE_TWIST})
MAX_QUOTE_CARDS = 2

INSIGHT_KEY = "insight"
CARD_KEY_QUOTE = "quote"
CARD_KEY_ATTRIBUTION = "attribution"
CARD_KEY_NAME = "name"
CARD_KEY_HANDLE = "handle"
CARD_KEY_QUOTE_ID = "quote_id"
HANDLE_PREFIX = "@"
ATTRIBUTION_HANDLE_TEMPLATE = "@{handle} · X"

RULE_QUOTE_NOT_VERBATIM = "quote_not_verbatim"
RULE_TOO_MANY_QUOTE_CARDS = "too_many_quote_cards"
MSG_QUOTE_NOT_VERBATIM = (
    "The quote card is not exactly one of the scout-verified quotes "
    "(text_pt on PT, text_en on EN)."
)
MSG_TOO_MANY_QUOTE_CARDS = "A pov_news deck shows at most 2 quote cards."

SLIDE_ROLE_KEY = "role"
SLIDE_INDEX_KEY = "slide_index"
LOCALE_PT = "pt"
LOCALE_EN = "en"
PRESENTATION_PT_KEY = "presentation_pt"
PRESENTATION_EN_KEY = "presentation_en"

SOURCE_FOOTER_PREFIX = "Fontes: "
SOURCE_FOOTER_SEPARATOR = ", "
CAPTION_FOOTER_JOIN = "\n\n"
X_SOURCE_HOSTS: frozenset[str] = frozenset({"x.com", "twitter.com"})
HOST_PREFIXES_DROPPED: tuple[str, ...] = ("www.", "mobile.")

__all__ = [
    "ATTRIBUTION_HANDLE_TEMPLATE",
    "CAPTION_FOOTER_JOIN",
    "CARD_KEY_ATTRIBUTION",
    "CARD_KEY_HANDLE",
    "CARD_KEY_NAME",
    "CARD_KEY_QUOTE",
    "CARD_KEY_QUOTE_ID",
    "HANDLE_PREFIX",
    "HOST_PREFIXES_DROPPED",
    "INSIGHT_KEY",
    "LOCALE_EN",
    "LOCALE_PT",
    "MAX_QUOTE_CARDS",
    "MSG_QUOTE_NOT_VERBATIM",
    "MSG_TOO_MANY_QUOTE_CARDS",
    "PRESENTATION_EN_KEY",
    "PRESENTATION_PT_KEY",
    "QUOTE_CARD_ROLES",
    "QUOTE_KEY_EXCERPT",
    "QUOTE_KEY_HANDLE",
    "QUOTE_KEY_ID",
    "QUOTE_KEY_LANG",
    "QUOTE_KEY_NAME",
    "QUOTE_KEY_TEXT_EN",
    "QUOTE_KEY_TEXT_PT",
    "QUOTE_KEY_URL",
    "RULE_QUOTE_NOT_VERBATIM",
    "RULE_TOO_MANY_QUOTE_CARDS",
    "SLIDE_INDEX_KEY",
    "SLIDE_ROLE_KEY",
    "SOURCE_FOOTER_PREFIX",
    "SOURCE_FOOTER_SEPARATOR",
    "X_SOURCE_HOSTS",
]
