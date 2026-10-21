"""Human issue lines for the owner's Telegram review.

"Slide 5: heading starts lowercase", "Slide 4: no body or features",
"Slide 6 EN: not translated". Built from the validator's blocking
violations over the persisted slides, the untranslated EN texts and the
lowercased proper nouns the autofix plan found. Deduplicated, ordered by slide
(PT before EN) and capped at ``AUTOFIX_MAX_ISSUE_LINES`` lines.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from rag_backend.application.services.carousel.localized_slide_builder import (
    PRESENTATION_EN_KEY,
    PRESENTATION_PT_KEY,
    as_dict,
)
from rag_backend.application.services.carousel.owner_autofix_paths import (
    text_at,
    visible_paths,
)
from rag_backend.application.services.carousel.owner_autofix_plan import (
    RetranslateTarget,
)
from rag_backend.application.services.carousel.owner_autofix_text import (
    lowercase_nouns,
)
from rag_backend.domain.constants.carousel import LANGUAGE_EN
from rag_backend.domain.constants.carousel_autofix import (
    AUTOFIX_MAX_ISSUE_LINES,
    ISSUE_LINE_CAROUSEL,
    ISSUE_LINE_MORE,
    ISSUE_LINE_SLIDE,
    ISSUE_LINE_SLIDE_EN,
    ISSUE_TEXT_BODY_EMPTY,
    ISSUE_TEXT_BODY_LOWERCASE,
    ISSUE_TEXT_CLOSING_ACTIONS,
    ISSUE_TEXT_HEADING_LOWERCASE,
    ISSUE_TEXT_ITEM_LOWERCASE,
    ISSUE_TEXT_MARKUP,
    ISSUE_TEXT_NOT_TRANSLATED,
    ISSUE_TEXT_PROPER_NOUN,
    ISSUE_TEXT_SUMMARY_POINTS,
    ITEM_LABELS,
)
from rag_backend.domain.constants.carousel_presentation import (
    VIOLATION_BODY_EMPTY,
    VIOLATION_BODY_NOT_SENTENCE_CASE_EN,
    VIOLATION_BODY_NOT_SENTENCE_CASE_PT,
    VIOLATION_CLOSING_ACTIONS_MISSING,
    VIOLATION_EMPHASIS_MARKUP_INVALID,
    VIOLATION_HEADING_NOT_SENTENCE_CASE_EN,
    VIOLATION_HEADING_NOT_SENTENCE_CASE_PT,
    VIOLATION_SUMMARY_POINTS_MISSING,
    VIOLATION_TRANSLATION_NOT_ENGLISH,
)
from rag_backend.domain.constants.workflow_state_fields import STATE_FIELD_SLIDE_INDEX
from rag_backend.domain.models.carousel_presentation import (
    SlideValidationReport,
    SlideValidationViolation,
)

_FIELD_HEADING = "heading"
_FIELD_BODY = "body"
_CASING_CODES = frozenset({
    VIOLATION_HEADING_NOT_SENTENCE_CASE_PT,
    VIOLATION_HEADING_NOT_SENTENCE_CASE_EN,
    VIOLATION_BODY_NOT_SENTENCE_CASE_PT,
    VIOLATION_BODY_NOT_SENTENCE_CASE_EN,
})
_CODE_TEXTS: dict[str, str] = {
    VIOLATION_BODY_EMPTY: ISSUE_TEXT_BODY_EMPTY,
    VIOLATION_CLOSING_ACTIONS_MISSING: ISSUE_TEXT_CLOSING_ACTIONS,
    VIOLATION_SUMMARY_POINTS_MISSING: ISSUE_TEXT_SUMMARY_POINTS,
    VIOLATION_EMPHASIS_MARKUP_INVALID: ISSUE_TEXT_MARKUP,
    VIOLATION_TRANSLATION_NOT_ENGLISH: ISSUE_TEXT_NOT_TRANSLATED,
}


@dataclass(frozen=True, order=True)
class Issue:
    """One issue of one slide. ``slide`` 0 = the whole carousel."""

    slide: int
    english: bool
    text: str


@dataclass(frozen=True)
class NounFinding:
    """A proper noun one slide writes fully lowercase."""

    slide: int
    noun: str
    english: bool = False


def _casing_text(field: str) -> str:
    if field == _FIELD_HEADING:
        return ISSUE_TEXT_HEADING_LOWERCASE
    if field == _FIELD_BODY:
        return ISSUE_TEXT_BODY_LOWERCASE
    list_field = field.split("[", 1)[0]
    item = ITEM_LABELS.get(list_field, list_field.replace("_", " "))
    return ISSUE_TEXT_ITEM_LOWERCASE.format(item=item)


def _violation_text(violation: SlideValidationViolation) -> str:
    if violation.code in _CASING_CODES:
        return _casing_text(violation.field or _FIELD_HEADING)
    return _CODE_TEXTS.get(violation.code, violation.code.replace("_", " "))


def violation_issues(report: SlideValidationReport) -> list[Issue]:
    """One issue per blocking violation."""
    return [
        Issue(
            slide=violation.slide_index or 0,
            english=violation.locale == LANGUAGE_EN,
            text=_violation_text(violation),
        )
        for violation in report.violations
        if violation.is_blocker
    ]


def translation_issues(targets: Iterable[RetranslateTarget]) -> list[Issue]:
    """One "not translated" issue per slide with untranslated EN text."""
    return [
        Issue(slide=target.slide_index, english=True, text=ISSUE_TEXT_NOT_TRANSLATED)
        for target in targets
    ]


def noun_issues(findings: Iterable[NounFinding]) -> list[Issue]:
    """One issue per lowercased proper noun."""
    return [
        Issue(
            slide=finding.slide,
            english=finding.english,
            text=ISSUE_TEXT_PROPER_NOUN.format(noun=finding.noun),
        )
        for finding in findings
    ]


def _payload_nouns(
    payload: Mapping[str, object], vocabulary: tuple[str, ...]
) -> list[str]:
    found: list[str] = []
    for path in visible_paths(payload):
        found.extend(lowercase_nouns(text_at(payload, path), vocabulary))
    return found


def noun_findings(
    records: Iterable[Mapping[str, object]], vocabulary: tuple[str, ...]
) -> list[NounFinding]:
    """Every proper noun of the vocabulary a slide writes fully lowercase."""
    findings: list[NounFinding] = []
    for record in records:
        index = record.get(STATE_FIELD_SLIDE_INDEX)
        slide = index if isinstance(index, int) else 0
        for key, english in ((PRESENTATION_PT_KEY, False), (PRESENTATION_EN_KEY, True)):
            payload = as_dict(record.get(key)) or {}
            findings.extend(
                NounFinding(slide=slide, noun=noun, english=english)
                for noun in _payload_nouns(payload, vocabulary)
            )
    return findings


def _line(issue: Issue) -> str:
    if issue.slide <= 0:
        return ISSUE_LINE_CAROUSEL.format(text=issue.text)
    template = ISSUE_LINE_SLIDE_EN if issue.english else ISSUE_LINE_SLIDE
    return template.format(slide=issue.slide, text=issue.text)


def issue_lines(issues: Iterable[Issue]) -> tuple[str, ...]:
    """Deduplicated, ordered lines; at most ``AUTOFIX_MAX_ISSUE_LINES``."""
    lines = list(dict.fromkeys(_line(issue) for issue in sorted(set(issues))))
    if len(lines) <= AUTOFIX_MAX_ISSUE_LINES:
        return tuple(lines)
    shown = lines[: AUTOFIX_MAX_ISSUE_LINES - 1]
    hidden = len(lines) - len(shown)
    return (*shown, ISSUE_LINE_MORE.format(count=hidden))


__all__ = [
    "Issue",
    "NounFinding",
    "issue_lines",
    "noun_findings",
    "noun_issues",
    "translation_issues",
    "violation_issues",
]
