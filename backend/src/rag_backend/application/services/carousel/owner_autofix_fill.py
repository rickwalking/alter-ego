"""Build missing structured items from the outline (AE-0367).

Prod carousel 8e350d6e slide 4 rendered only its title: no body and no
features. Its outline still had the key points the model was asked to cover.
A content slide without a body gets 3-4 features from those key points; a
summary slide without enough points gets them from its key points, or else
from the titles and first key points of the content slides. Each item takes
the contract's allowed icon for its position. Titles and bodies respect the
contract copy budgets, cut at a word boundary.
"""

from __future__ import annotations

from dataclasses import dataclass

from rag_backend.application.services.carousel.copy_hygiene_text import (
    ends_on_connector,
)
from rag_backend.application.services.carousel.sentence_case import (
    capitalize_first_letter,
)
from rag_backend.domain.constants.carousel_autofix import (
    FEATURE_BODY_MAX_CHARS,
    FEATURE_TITLE_MAX_CHARS,
    FILL_MAX_ITEMS,
    FILL_MIN_ITEMS,
    KEY_POINT_SEPARATORS,
    SUMMARY_BODY_MAX_CHARS,
    SUMMARY_TITLE_MAX_CHARS,
)

_ICON_NAME = "icon_name"
_TITLE = "title"
_BODY = "body"


@dataclass(frozen=True)
class ItemBudget:
    """Character budgets of one structured item kind."""

    title: int
    body: int


FEATURE_BUDGET = ItemBudget(title=FEATURE_TITLE_MAX_CHARS, body=FEATURE_BODY_MAX_CHARS)
SUMMARY_BUDGET = ItemBudget(title=SUMMARY_TITLE_MAX_CHARS, body=SUMMARY_BODY_MAX_CHARS)


@dataclass(frozen=True)
class FillSource:
    """Title/body pairs to turn into items, and the icons allowed."""

    pairs: tuple[tuple[str, str], ...]
    icons: tuple[str, ...]
    budget: ItemBudget


_COMMA = ", "


def _cut(text: str, limit: int) -> str:
    """At most ``limit`` characters, cut at the last word boundary."""
    clean = " ".join(text.split())
    if len(clean) <= limit:
        return clean
    head = clean[: limit + 1].rsplit(" ", 1)[0]
    return head.rstrip(" ,;:.-\u2013\u2014")


def _split_on_separator(point: str) -> tuple[str, str] | None:
    for separator in KEY_POINT_SEPARATORS:
        title, found, body = point.partition(separator)
        if found and title.strip() and body.strip():
            return title.strip(), body.strip()
    return None


def _split_on_words(point: str, title_limit: int) -> tuple[str, str] | None:
    words = point.split()
    title_words: list[str] = []
    for word in words[: max(len(words) // 2, 1)]:
        if len(" ".join([*title_words, word])) > title_limit:
            break
        title_words.append(word)
    # AE-0401: never end a title on a connector ("Comece com dois ou").
    while title_words and ends_on_connector(title_words[-1]):
        title_words.pop()
    rest = words[len(title_words) :]
    if not title_words or not rest:
        return None
    return " ".join(title_words), " ".join(rest)


def _split_on_comma(point: str, title_limit: int) -> tuple[str, str] | None:
    """AE-0401: "Comece com dois ou três agentes, não dez." splits at the comma."""
    title, found, body = point.partition(_COMMA)
    if not found or not body.strip() or len(title) > title_limit:
        return None
    return title.strip(), body.strip()


def split_key_point(point: str, title_limit: int) -> tuple[str, str] | None:
    """A key point as (title, body), or None when it is too short to split."""
    clean = " ".join(point.split())
    if not clean:
        return None
    return (
        _split_on_separator(clean)
        or _split_on_comma(clean, title_limit)
        or _split_on_words(clean, title_limit)
    )


def key_point_pairs(
    points: tuple[str, ...], title_limit: int
) -> tuple[tuple[str, str], ...]:
    """Every key point that splits into a title and a body."""
    pairs = (split_key_point(point, title_limit) for point in points)
    return tuple(pair for pair in pairs if pair is not None)


def _item(pair: tuple[str, str], icon: str, budget: ItemBudget) -> dict[str, object]:
    title, body = pair
    return {
        _ICON_NAME: icon,
        _TITLE: capitalize_first_letter(_cut(title, budget.title)),
        _BODY: capitalize_first_letter(_cut(body, budget.body)),
    }


def build_items(source: FillSource) -> list[dict[str, object]] | None:
    """3-4 items with a per-position icon, or None when fewer than 3 pairs."""
    pairs = [pair for pair in source.pairs if pair[0].strip() and pair[1].strip()]
    if len(pairs) < FILL_MIN_ITEMS or not source.icons:
        return None
    icons = source.icons
    return [
        _item(pair, icons[position % len(icons)], source.budget)
        for position, pair in enumerate(pairs[:FILL_MAX_ITEMS])
    ]


__all__ = [
    "FEATURE_BUDGET",
    "SUMMARY_BUDGET",
    "FillSource",
    "ItemBudget",
    "build_items",
    "key_point_pairs",
    "split_key_point",
]
