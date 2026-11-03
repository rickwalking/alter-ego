"""The structure of the three prod carousels the copy budget step left blocked.

Read-only triage of the checkpoints (2026-11-02) gave, per slide: the slide type
and contract role, whether the draft came back as a bilingual blob (PT and EN
payloads written by the drafting model) or as plain PT copy translated later,
and for every visible field its length in characters and its emphasis markup.
No user text is kept: the builder fills each field with synthetic prose of the
recorded length and markup. ``B`` is a ``**`` pair, ``S`` a ``<strong>`` pair.

- ``6f36130e``: POV, 9 slides, blobs on 3, 4, 5, 7, 8; first gate 31 violations.
- ``d8da820a``: POV, 9 slides, blobs on 1, 2, 4, 5, 6, 8, 9; first gate 39.
- ``41c4f437``: POV news, 9 slides, no blob, a quote card on slide 5, and slide 4
  with an EN quote card its PT lost; first gate 1 (``translation_shape_mismatch``).
"""

from __future__ import annotations

from dataclasses import dataclass

NONE = ""
B = "**"
S = "<strong>"


@dataclass(frozen=True)
class Field:
    """One visible text: its recorded length and emphasis markup."""

    length: int
    mark: str = NONE


@dataclass(frozen=True)
class Item:
    """One structured item (feature or summary point)."""

    title: Field
    body: Field


@dataclass(frozen=True)
class Locale:
    """One locale payload of a blob slide (or the EN translation of a plain one)."""

    heading: Field
    body: Field
    items: tuple[Item, ...] = ()


@dataclass(frozen=True)
class Slide:
    """One slide: blob drafts carry both locales, plain ones PT plus a translation."""

    index: int
    slide_type: str
    role: str
    pt: Locale
    en: Locale
    blob: bool = False
    quote_card: bool = False
    en_only_quote_card: bool = False


def _f(length: int, mark: str = NONE) -> Field:
    return Field(length, mark)


def _items(*pairs: tuple[Field, Field]) -> tuple[Item, ...]:
    return tuple(Item(title, body) for title, body in pairs)


def _plain(index: int, kind: tuple[str, str], pt: Locale, en: Locale) -> Slide:
    return Slide(index, kind[0], kind[1], pt, en)


def _blob(index: int, kind: tuple[str, str], pt: Locale, en: Locale) -> Slide:
    return Slide(index, kind[0], kind[1], pt, en, blob=True)


INTRO = ("intro", "hook")
REHOOK = ("content", "rehook")
POV = ("content", "pov")
POINT = ("content", "point")
TWIST = ("content", "twist")
SAVE = ("summary", "save")
CTA = ("cta", "cta")

SHAPE_6F36130E: tuple[Slide, ...] = (
    _plain(1, INTRO, Locale(_f(49), _f(29)), Locale(_f(55), _f(40, S))),
    _plain(2, REHOOK, Locale(_f(53), _f(192, B)), Locale(_f(50), _f(193, S))),
    _blob(3, POV, Locale(_f(20), _f(232, B)), Locale(_f(14), _f(240, B))),
    _blob(4, POINT, Locale(_f(71), _f(347, B)), Locale(_f(73), _f(362, B))),
    _blob(
        5,
        POINT,
        Locale(
            _f(58),
            _f(287, B),
            _items((_f(26), _f(150, B)), (_f(20), _f(166, B)), (_f(24), _f(173, B))),
        ),
        Locale(
            _f(53),
            _f(313, B),
            _items((_f(21), _f(169, B)), (_f(26), _f(191, B)), (_f(26), _f(196, B))),
        ),
    ),
    _plain(6, POINT, Locale(_f(40), _f(186, B)), Locale(_f(46), _f(192, S))),
    _blob(7, TWIST, Locale(_f(75), _f(493, B)), Locale(_f(78), _f(540, B))),
    _blob(
        8,
        SAVE,
        Locale(
            _f(49, B),
            _f(0),
            _items((_f(27), _f(149, B)), (_f(37), _f(225, B)), (_f(45), _f(157))),
        ),
        Locale(
            _f(50, B),
            _f(0),
            _items((_f(29), _f(166, B)), (_f(43), _f(244, B)), (_f(38), _f(187))),
        ),
    ),
    _plain(9, CTA, Locale(_f(19), _f(199, B)), Locale(_f(21), _f(196, S))),
)

SHAPE_D8DA820A: tuple[Slide, ...] = (
    _blob(1, INTRO, Locale(_f(41), _f(499, B)), Locale(_f(42), _f(530, B))),
    _blob(2, REHOOK, Locale(_f(27), _f(333, B)), Locale(_f(30), _f(358, B))),
    _plain(3, POV, Locale(_f(20), _f(169, B)), Locale(_f(14), _f(196, S))),
    _blob(
        4,
        POINT,
        Locale(
            _f(39),
            _f(209, B),
            _items((_f(21), _f(160, B)), (_f(17), _f(158)), (_f(14), _f(164, B))),
        ),
        Locale(
            _f(40),
            _f(215, B),
            _items((_f(21), _f(153, B)), (_f(17), _f(171)), (_f(19), _f(180, B))),
        ),
    ),
    _blob(
        5,
        POINT,
        Locale(
            _f(53),
            _f(196),
            _items((_f(29, B), _f(116)), (_f(29, B), _f(126)), (_f(26, B), _f(118))),
        ),
        Locale(
            _f(47),
            _f(189),
            _items((_f(26, B), _f(129)), (_f(34, B), _f(123)), (_f(26, B), _f(132))),
        ),
    ),
    _blob(
        6,
        POINT,
        Locale(
            _f(57),
            _f(188, B),
            _items((_f(25), _f(193, B)), (_f(23), _f(149, B)), (_f(22), _f(168, B))),
        ),
        Locale(
            _f(58),
            _f(171, B),
            _items((_f(29), _f(194, B)), (_f(24), _f(168, B)), (_f(21), _f(171, B))),
        ),
    ),
    _plain(7, TWIST, Locale(_f(44), _f(143, B)), Locale(_f(55), _f(196, S))),
    _blob(
        8,
        SAVE,
        Locale(
            _f(26),
            _f(0),
            _items((_f(37), _f(266, B)), (_f(40), _f(295, B)), (_f(35), _f(238))),
        ),
        Locale(
            _f(28),
            _f(0),
            _items((_f(35), _f(282, B)), (_f(36), _f(322, B)), (_f(32), _f(232))),
        ),
    ),
    _blob(9, CTA, Locale(_f(50, B), _f(0)), Locale(_f(50, B), _f(0))),
)

SHAPE_41C4F437: tuple[Slide, ...] = (
    _plain(1, INTRO, Locale(_f(55), _f(25)), Locale(_f(59), _f(39))),
    _plain(2, REHOOK, Locale(_f(31), _f(145)), Locale(_f(31), _f(194, S))),
    _plain(3, POV, Locale(_f(24), _f(183, B)), Locale(_f(22), _f(195, S))),
    Slide(
        4,
        "content",
        "point",
        Locale(_f(23), _f(112)),
        Locale(_f(25), _f(196, S)),
        en_only_quote_card=True,
    ),
    Slide(
        5,
        "content",
        "point",
        Locale(_f(32), _f(132, B)),
        Locale(_f(38), _f(196, S)),
        quote_card=True,
    ),
    _plain(6, POINT, Locale(_f(31), _f(195, B)), Locale(_f(27), _f(196, S))),
    _plain(
        7,
        TWIST,
        Locale(
            _f(42),
            _f(181, B),
            _items((_f(27), _f(96, B)), (_f(24), _f(92, B)), (_f(23), _f(95, B))),
        ),
        Locale(
            _f(41),
            _f(196, S),
            _items((_f(29), _f(100, S)), (_f(25), _f(94, S)), (_f(20), _f(90, S))),
        ),
    ),
    _plain(
        8,
        SAVE,
        Locale(
            _f(63),
            _f(0),
            _items((_f(49), _f(90, B)), (_f(42), _f(83, B)), (_f(43), _f(88, B))),
        ),
        Locale(
            _f(62),
            _f(0),
            _items((_f(46), _f(90, S)), (_f(42), _f(90, S)), (_f(34), _f(87, S))),
        ),
    ),
    _plain(9, CTA, Locale(_f(16), _f(183, B)), Locale(_f(18), _f(196, S))),
)

SHAPES: dict[str, tuple[Slide, ...]] = {
    "6f36130e": SHAPE_6F36130E,
    "d8da820a": SHAPE_D8DA820A,
    "41c4f437": SHAPE_41C4F437,
}

__all__ = ["NONE", "SHAPES", "B", "Field", "Item", "Locale", "S", "Slide"]
