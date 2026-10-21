"""One label-scaffolding detector shared by the drafter parser and the gate.

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

Detection and stripping share the SAME positional rules (orchestrator review,
PR #158), so every flagged text is deterministically repairable:

- a **bold field label** (``**Heading:**``, ``**CTA creator: radar IA.**``)
  counts anywhere in the text;
- a **plain** label or locale marker (``Heading:``, ``PT-BR:``, ``SLIDE 3:``)
  counts only at a line start (optionally after a bold opener) or as a
  whole-line marker — a mid-sentence plain "body:" is NOT scaffolding;
- plain ``TL;DR:`` is always real copy (a legitimate rhetorical lead-in); only
  its bold scaffold form (``**TL;DR:**``) counts;
- a **bold locale marker** (``**PT-BR**``, ``**PT** ** **``) counts only at a
  line start or as a whole line.

Pure: no I/O, no policy, no locale.


Locale markers are listed longest-first so the alternation prefers "PT-BR" over "PT".
"TL;DR:" is a legitimate rhetorical lead-in in real slide copy ("TL;DR: o custo caiu
3x."), so it only counts as a label in its bold scaffold form, never as a plain
line-start label. A bold locale marker may be followed by empty-bold residue (``**PT**
** **``), which the line patterns also match.
"""

from __future__ import annotations

import re

LOCALE_MARKERS: tuple[str, ...] = (
    "PT-BR",
    "PT_BR",
    "EN-US",
    "EN_US",
    "PT",
    "EN",
)

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
_PLAIN_LINE_LABEL_ALT = "|".join(
    re.escape(label) for label in FIELD_LABELS if label != "TL;DR"
)

_BOLD_LABEL_PATTERN = re.compile(rf"\*\*(?P<label>{_LABEL_ALT}):\*\*", re.IGNORECASE)
_BOLD_LABEL_PHRASE_PATTERN = re.compile(
    rf"\*\*(?P<label>{_LABEL_ALT})\s*:\s*(?P<value>[^*\n]*)\*\*",
    re.IGNORECASE,
)
_BOLD_LABEL_PREFIX_PATTERN = re.compile(
    rf"\*\*(?:{_LABEL_ALT})\s*:(?:\*\*)?", re.IGNORECASE
)
_LINE_LABEL_PREFIX_PATTERN = re.compile(
    rf"^(?:\*\*)?\s*(?P<label>{_PLAIN_LINE_LABEL_ALT}|{_LOCALE_ALT}|SLIDE\s*\d+"
    r"|TITLE|BODY|KEY\s*POINTS)\s*:(?:\*\*)?\s*",
    re.IGNORECASE,
)
_LINE_BOLD_LOCALE_PATTERN = re.compile(
    rf"^\s*\*\*(?P<marker>{_LOCALE_ALT}):?\*\*:?(?:\s*\*\*\s*\*\*)?\s*",
    re.IGNORECASE,
)
_PURE_MARKER_LINE_PATTERN = re.compile(
    rf"^(?:\*\*)?\s*(?P<marker>{_LOCALE_ALT})\s*:?\s*(?:\*\*)?"
    r"(?:\s*\*\*\s*\*\*)?\s*$",
    re.IGNORECASE,
)
_SECTION_HEADER_LINE_PATTERN = re.compile(r"^\s*##\s+")


def _add(found: list[str], seen: set[str], label: str) -> None:
    key = label.casefold()
    if key not in seen:
        seen.add(key)
        found.append(label)


def scaffold_label_details(text: str) -> tuple[str, ...]:
    """The locale markers and field labels found in ``text``, in order.

    Bold field labels count anywhere; plain labels and locale markers count
    only at a line start (optionally after a bold opener) or as a whole-line
    marker, so mid-sentence plain "body:" / "TL;DR:" copy is never flagged.
    """
    found: list[str] = []
    seen: set[str] = set()
    for match in _BOLD_LABEL_PATTERN.finditer(text):
        _add(found, seen, match.group("label"))
    for match in _BOLD_LABEL_PHRASE_PATTERN.finditer(text):
        _add(found, seen, match.group("label"))
    for line in text.splitlines():
        work = line.strip()
        marker = _PURE_MARKER_LINE_PATTERN.match(work)
        if marker is not None:
            _add(found, seen, marker.group("marker"))
            continue
        bold = _LINE_BOLD_LOCALE_PATTERN.match(work)
        if bold is not None:
            _add(found, seen, bold.group("marker"))
            work = _LINE_BOLD_LOCALE_PATTERN.sub("", work, count=1).strip()
        prefix = _LINE_LABEL_PREFIX_PATTERN.match(work)
        if prefix is not None:
            _add(found, seen, prefix.group("label").strip())
    return tuple(found)


def has_scaffold_labels(text: str) -> bool:
    """True when the text carries any locale marker or drafting field label."""
    return bool(scaffold_label_details(text))


def _strip_line(line: str) -> str:
    """One line with its scaffold markers and label prefixes removed ("" when gone).

    A line may chain two labels ("PT: Heading: ..."), so stripping repeats until the
    line is stable.
    """
    if _SECTION_HEADER_LINE_PATTERN.match(line):
        return ""
    stripped = line.strip()
    if _PURE_MARKER_LINE_PATTERN.match(stripped):
        return ""
    work = _LINE_BOLD_LOCALE_PATTERN.sub("", stripped, count=1).strip()
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

    Drops a line that is only a ``##`` header or a locale marker; strips
    bold-locale and label prefixes at line starts; unwraps a bold
    ``**Label: value**`` phrase to its value and drops a bold ``**Label:**``
    prefix anywhere. Lines left empty are dropped.
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
