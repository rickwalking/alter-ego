"""Which text of a slide the persona judge scores, and when its last score still holds.

Prod carousel 2fe43d2c: the judge scored ``draft_text`` alone, the PT body a
reviewer edit mirrors, so a checklist slide was judged on a bare heading-less
line (slide 8 scored 15 on unchanged copy), and every content run re-judged every
slide at sampling temperature, so one revise of slide 9 moved slide 1 from 90 to
38. The judge now reads the slide's visible PT copy (heading, body, checklist
items and the TL;DR strip), and a slide whose copy did not change keeps its last
score: each stored entry carries the fingerprint of the text it judged.

Only the PT copy is judged and fingerprinted (the voice gate is about the owner's
Portuguese; the EN copy is a translation of it). Stats (numbers and labels) and
insight quotes (someone else's words) are left out on purpose. The fingerprint is
the real stabiliser: the judge also runs at temperature 0, which some reasoning
models ignore.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from functools import partial

from rag_backend.application.services.carousel.bounded_gather import gather_bounded
from rag_backend.application.services.carousel.persona_judge import (
    VoiceJudge,
    judge_voice,
)
from rag_backend.domain.constants.carousel_workflow import SLIDE_DRAFT_TEXT_KEY
from rag_backend.domain.constants.slide_fix import (
    PERSONA_SCORE_RESCORE_PENDING_KEY,
    PERSONA_SCORE_SLIDE_KEY,
)
from rag_backend.domain.persona_score import on_hundred_scale_entry, stored_overall

VOICE_TEXT_FINGERPRINT_KEY = "text_sha256"
_PRESENTATION_PT_KEY = "presentation_pt"
_HEADING_KEY = "heading"
_BODY_KEY = "body"
_TITLE_KEY = "title"
_ITEM_LIST_KEYS = ("features", "summary_points", "actions")
_TLDR_KEY = "tldr_strip"
_ITEM_SEPARATOR = ": "
_LINE_SEPARATOR = "\n"
_FINGERPRINT_LENGTH = 16


def _text(source: Mapping[str, object], key: str) -> str:
    value = source.get(key)
    return value.strip() if isinstance(value, str) else ""


def _item_lines(source: Mapping[str, object]) -> list[str]:
    lines: list[str] = []
    for list_key in _ITEM_LIST_KEYS:
        items = source.get(list_key)
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, Mapping):
                continue
            parts = [_text(item, _TITLE_KEY), _text(item, _BODY_KEY)]
            line = _ITEM_SEPARATOR.join(part for part in parts if part)
            if line:
                lines.append(line)
    return lines


def voice_text(draft: Mapping[str, object]) -> str:
    """The slide's visible PT copy: heading, body, every checklist item, TL;DR.

    The PT presentation payload wins (what the slide renders and the reviewer
    edits); a draft without one falls back to its title and ``draft_text``.
    """
    presentation = draft.get(_PRESENTATION_PT_KEY)
    source = presentation if isinstance(presentation, Mapping) else draft
    heading = _text(source, _HEADING_KEY) or _text(draft, _TITLE_KEY)
    body = _text(source, _BODY_KEY) or _text(draft, SLIDE_DRAFT_TEXT_KEY)
    lines = [heading, body, *_item_lines(source), _text(source, _TLDR_KEY)]
    return _LINE_SEPARATOR.join(line for line in lines if line)


def text_fingerprint(text: str) -> str:
    """A short, stable fingerprint of the judged text."""
    return hashlib.sha256(text.encode()).hexdigest()[:_FINGERPRINT_LENGTH]


def reusable_score(
    previous: object, key: str, fingerprint: str
) -> dict[str, object] | None:
    """The last score of ``key`` when it judged this exact text, else None.

    An entry without a fingerprint (scored before fingerprints existed), an
    unscored one, or one the autopilot marked for a re-score is judged again.
    """
    entry = previous.get(key) if isinstance(previous, Mapping) else None
    if not isinstance(entry, Mapping):
        return None
    still_valid = (
        entry.get(VOICE_TEXT_FINGERPRINT_KEY) == fingerprint
        and entry.get(PERSONA_SCORE_RESCORE_PENDING_KEY) is not True
        and stored_overall(entry) is not None
    )
    return dict(entry) if still_valid else None


def _stale_entry(previous: object, key: str) -> dict[str, object] | None:
    entry = previous.get(key) if isinstance(previous, Mapping) else None
    if not isinstance(entry, Mapping) or stored_overall(entry) is None:
        return None
    return {**entry, PERSONA_SCORE_RESCORE_PENDING_KEY: True}


@dataclass(frozen=True)
class SlideVoiceScoring:
    """The drafts to score, the judges, and the scores the state already holds."""

    slide_drafts: list[object]
    judge: VoiceJudge
    fallback: VoiceJudge | None
    previous: object
    concurrency: int


@dataclass(frozen=True)
class _ToJudge:
    key: str
    text: str
    fingerprint: str


async def score_slide_voices(command: SlideVoiceScoring) -> dict[str, object]:
    """``slide_N`` scores in slide order; only slides whose copy changed are judged.

    Judged slides run concurrently (bounded). Every judged entry stores the
    fingerprint of its text. When the judge gives no score, the slide keeps its
    previous entry marked ``rescore_pending`` (still gating on its last score, so a
    judge timeout never opens the gate); a slide with no previous entry stays
    unscored, as before.
    """
    kept: dict[int, dict[str, object]] = {}
    pending: dict[int, _ToJudge] = {}
    for index, slide in enumerate(command.slide_drafts):
        text = voice_text(slide) if isinstance(slide, Mapping) else ""
        if not text:
            continue
        key = PERSONA_SCORE_SLIDE_KEY.format(index=index + 1)
        fingerprint = text_fingerprint(text)
        reused = reusable_score(command.previous, key, fingerprint)
        if reused is not None:
            kept[index] = reused
            continue
        pending[index] = _ToJudge(key, text, fingerprint)
    results = await gather_bounded(
        [
            partial(judge_voice, command.judge, item.text, command.fallback)
            for item in pending.values()
        ],
        command.concurrency,
    )
    for (index, item), result in zip(pending.items(), results, strict=True):
        if result is not None:
            kept[index] = {
                **on_hundred_scale_entry(result),
                VOICE_TEXT_FINGERPRINT_KEY: item.fingerprint,
            }
            continue
        stale = _stale_entry(command.previous, item.key)
        if stale is not None:
            kept[index] = stale
    return {
        PERSONA_SCORE_SLIDE_KEY.format(index=index + 1): kept[index]
        for index in sorted(kept)
    }


__all__ = [
    "VOICE_TEXT_FINGERPRINT_KEY",
    "SlideVoiceScoring",
    "reusable_score",
    "score_slide_voices",
    "text_fingerprint",
    "voice_text",
]
