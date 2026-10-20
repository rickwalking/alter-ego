"""One label-scaffolding detector shared by the drafter parser and the gate (AE-0436).

Prod carousels ``7acaf967`` and ``5344b6c6`` shipped locale markers and field
labels as visible copy: ``**PT-BR**`` at the start of a PT body, ``**CTA
creator: radar IA.**`` at the end of an EN body, ``**PT** ** **`` and ``PT:
Heading:`` garbage in existing drafts. Each call site used to carry its own
regex and only the drafter parser stripped (``**PT**``/``**EN**`` only, line
starts only), so every other variant passed the content gate.

This module is the single, data-driven definition of what counts as label
scaffolding, used by BOTH:

- the drafter parser (``slide_scaffold_recovery``) to strip at the source, and
- the content gate (``contains_drafting_scaffold`` → blocking
  ``drafting_scaffold_present``, deterministically reparable).

Detection is positional: a marker or label is scaffolding wherever it sits in
the text (line start, inline, bold or plain, with or without a colon).

Pure: no I/O, no policy, no locale.

"""

from __future__ import annotations

import re

# Locale section markers in every variant the model has been seen to write.
# Longest-first so the alternation prefers "PT-BR" over "PT".
LOCALE_MARKERS: tuple[str, ...] = (
    "PT-BR",
    "PT_BR",
    "EN-US",
    "EN_US",
    "PT",
    "EN",
)

# Drafting field labels the scaffold may carry (bold or plain, colon after).
FIELD_LABELS: tuple[str, ...] = (
    "Long form notes",
    "Key points",
    "Key point",
    "CTA creator",
    "TL;DR",
    "Summary",
    "Subtitle",
    "Heading",
    "Body",
    "Title",
    "CTA",
)

_LOCALE_ALT = "|".join(re.escape(marker) for marker in LOCALE_MARKERS)
_LABEL_ALT = "|".join(re.escape(label) for label in FIELD_LABELS)
_ANY_LABEL_ALT = f"{_LABEL_ALT}|SLIDE\\s*\\d+|TITLE|BODY|KEY\\s*POINTS"

# ``**PT-BR**`` / ``**PT-BR:**`` / ``**PT**`` (bold locale marker, anywhere).
_BOLD_LOCALE_PATTERN = re.compile(
    rf"\*\*(?P<marker>{_LOCALE_ALT}):?\*\*", re.IGNORECASE
)
# ``**Heading:**`` / ``**CTA creator:**`` (bold field label, anywhere).
_BOLD_LABEL_PATTERN = re.compile(rf"\*\*(?P<label>{_LABEL_ALT}):?\*\*", re.IGNORECASE)
# Plain ``PT-BR:`` / ``Heading:`` / ``SLIDE 3:`` prefixes, anywhere in the text.
_PLAIN_PREFIX_PATTERN = re.compile(
    rf"\b(?P<label>{_LOCALE_ALT}|{_ANY_LABEL_ALT})\s*:",
    re.IGNORECASE,
)
# A line that is nothing but a locale marker: ``PT``, ``PT:``, ``**PT**``,
# ``**PT:**`` or ``**PT** ** **`` (the empty-bold residue seen on 5344b6c6).
_PURE_MARKER_LINE_PATTERN = re.compile(
    rf"^(?:\*\*)?\s*(?P<marker>{_LOCALE_ALT})\s*:?\s*(?:\*\*)?"
    r"(?:\s*\*\*\s*\*\*)?\s*$",
    re.IGNORECASE,
)
# A ``## <anything>`` scaffold section header line.
_SECTION_HEADER_LINE_PATTERN = re.compile(r"^\s*##\s+")
# A bold label that spans the whole phrase: ``**CTA creator: radar IA.**``.
_BOLD_LABEL_PHRASE_PATTERN = re.compile(
    rf"\*\*(?:{_LABEL_ALT})\s*:\s*(?P<value>[^*]*)\*\*",
    re.IGNORECASE,
)
# A bold label prefix left open: ``**Body:**`` or ``**Body:** rest``.
_BOLD_LABEL_PREFIX_PATTERN = re.compile(rf"\*\*(?:{_LABEL_ALT})\s*:", re.IGNORECASE)
# A label (bold or plain, field or locale) at the start of a line.
_LINE_LABEL_PREFIX_PATTERN = re.compile(
    rf"^(?:\*\*)?\s*(?:{_LABEL_ALT}|{_LOCALE_ALT})\s*:(?:\*\*)?\s*",
    re.IGNORECASE,
)


def _add(found: list[str], seen: set[str], label: str) -> None:
    key = label.casefold()
    if key not in seen:
        seen.add(key)
        found.append(label)


def scaffold_label_details(text: str) -> tuple[str, ...]:
    """The locale markers and field labels found in ``text``, in order.

    Covers every variant: bold or plain, with or without a colon, at the line
    start or inline. A plain locale marker without a colon counts only as a
    whole line, so a real word never matches.
    """
    found: list[str] = []
    seen: set[str] = set()
    for match in _BOLD_LOCALE_PATTERN.finditer(text):
        _add(found, seen, match.group("marker"))
    for match in _BOLD_LABEL_PATTERN.finditer(text):
        _add(found, seen, match.group("label"))
    for match in _PLAIN_PREFIX_PATTERN.finditer(text):
        _add(found, seen, match.group("label").strip())
    for line in text.splitlines():
        match = _PURE_MARKER_LINE_PATTERN.match(line.strip())
        if match is not None:
            _add(found, seen, match.group("marker"))
    return tuple(found)


def has_scaffold_labels(text: str) -> bool:
    """True when the text carries any locale marker or drafting field label."""
    return bool(scaffold_label_details(text))


def _strip_line(line: str) -> str:
    """One line with its scaffold markers and label prefixes removed ("" when gone)."""
    if _SECTION_HEADER_LINE_PATTERN.match(line):
        return ""
    stripped = line.strip()
    if _PURE_MARKER_LINE_PATTERN.match(stripped):
        return ""
    work = stripped
    # "PT: Heading: ..." chains two labels on one line: strip until stable.
    while True:
        shortened = _LINE_LABEL_PREFIX_PATTERN.sub("", work)
        if shortened == work:
            break
        work = shortened
    work = _BOLD_LABEL_PHRASE_PATTERN.sub(r"\g<value>", work)
    work = _BOLD_LABEL_PREFIX_PATTERN.sub("", work)
    return work.strip()


def strip_scaffold_labels(text: str) -> str:
    """The text without scaffold section headers, locale markers and field labels.

    Drops a line that is only a ``##`` header or a locale marker; strips label
    prefixes at line starts; unwraps a bold ``**Label: value**`` phrase to its
    value and drops an open bold ``**Label:**`` prefix anywhere. Lines left
    empty are dropped. Returns the original text when nothing is found.
    """
    cleaned = [_strip_line(line) for line in text.splitlines()]
    return "\n".join(line for line in cleaned if line)


__all__ = [
    "FIELD_LABELS",
    "LOCALE_MARKERS",
    "has_scaffold_labels",
    "scaffold_label_details",
    "strip_scaffold_labels",
]
