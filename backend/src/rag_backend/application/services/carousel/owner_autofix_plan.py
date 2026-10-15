"""Plan the owner autofix over localized slide records (AE-0367).

Pure: no DB, no LLM. Per slide and locale, in this order:

1. fill a content slide's empty features from its outline key points and a
   summary slide's missing points (the EN side gets the PT items, which the
   re-translate step then translates);
2. balance ``<strong>`` tags and restore the carousel's proper nouns in every
   visible text;
3. the AE-0366 ``repair_casing`` (first letter of every heading, body sentence
   and item text, pt-BR accent aware; configured proper nouns).

EN texts that are still Portuguese (or the PT copy pasted as-is) become
re-translate targets; ``apply_translations`` writes the model's answers back
and runs steps 2-3 again on them.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass, field

from rag_backend.application.services.carousel.localized_slide_builder import (
    PRESENTATION_EN_KEY,
    PRESENTATION_PT_KEY,
    as_dict,
)
from rag_backend.application.services.carousel.owner_autofix_fill import (
    FEATURE_BUDGET,
    SUMMARY_BUDGET,
    FillSource,
    build_items,
    key_point_pairs,
)
from rag_backend.application.services.carousel.owner_autofix_paths import (
    complete_items,
    map_texts,
    text_at,
    visible_paths,
    with_text,
)
from rag_backend.application.services.carousel.owner_autofix_text import (
    balance_strong,
    is_untranslated,
    looks_portuguese,
    restore_proper_nouns,
)
from rag_backend.application.services.carousel.presentation_casing import (
    repair_casing,
)
from rag_backend.application.services.carousel.presentation_policy_types import (
    CarouselPresentationPolicy,
)
from rag_backend.domain.constants.carousel import (
    LANGUAGE_EN,
    LANGUAGE_PT,
    SLIDE_TYPE_CONTENT,
    SLIDE_TYPE_SUMMARY,
)
from rag_backend.domain.constants.carousel_autofix import (
    AUTOFIX_TARGET_ID,
    FILL_MIN_ITEMS,
)
from rag_backend.domain.constants.workflow_state_fields import (
    STATE_FIELD_SLIDE_INDEX,
    STATE_FIELD_SLIDE_TYPE,
)

_FEATURES = "features"
_SUMMARY_POINTS = "summary_points"
_BODY = "body"


@dataclass(frozen=True)
class SlideOutline:
    """The outline entry of one slide."""

    title: str = ""
    key_points: tuple[str, ...] = ()
    slide_type: str = ""


@dataclass(frozen=True)
class AutofixContext:
    """Everything the plan reads besides the records."""

    policy: CarouselPresentationPolicy
    vocabulary: tuple[str, ...] = ()
    outline: Mapping[int, SlideOutline] = field(default_factory=dict)


@dataclass(frozen=True)
class RetranslateTarget:
    """One EN text to translate again from its PT source."""

    slide_index: int
    path: str
    source: str

    @property
    def target_id(self) -> str:
        """Stable id the model echoes back."""
        return AUTOFIX_TARGET_ID.format(slide=self.slide_index, path=self.path)


@dataclass(frozen=True)
class AutofixPlan:
    """Repaired records, whether anything changed, and EN texts to translate."""

    records: list[dict[str, object]]
    changed: bool
    retranslate: tuple[RetranslateTarget, ...] = ()

    @property
    def fixable(self) -> bool:
        """True when applying the plan would change or translate something."""
        return self.changed or bool(self.retranslate)


@dataclass(frozen=True)
class _Slide:
    index: int
    slide_type: str


def _slide_index(record: Mapping[str, object]) -> int:
    value = record.get(STATE_FIELD_SLIDE_INDEX)
    return value if isinstance(value, int) else 0


def _slide_of(record: Mapping[str, object], payload: Mapping[str, object]) -> _Slide:
    slide_type = payload.get(STATE_FIELD_SLIDE_TYPE) or record.get(
        STATE_FIELD_SLIDE_TYPE
    )
    return _Slide(index=_slide_index(record), slide_type=str(slide_type or ""))


def _summary_pairs(index: int, context: AutofixContext) -> tuple[tuple[str, str], ...]:
    own = context.outline.get(index, SlideOutline())
    pairs = key_point_pairs(own.key_points, SUMMARY_BUDGET.title)
    if len(pairs) >= FILL_MIN_ITEMS:
        return pairs
    return tuple(
        (entry.title, entry.key_points[0])
        for _, entry in sorted(context.outline.items())
        if entry.slide_type == SLIDE_TYPE_CONTENT and entry.title and entry.key_points
    )


def _needs_features(payload: Mapping[str, object], slide_type: str) -> bool:
    if slide_type != SLIDE_TYPE_CONTENT or str(payload.get(_BODY) or "").strip():
        return False
    return complete_items(payload, _FEATURES) < FILL_MIN_ITEMS


def _needs_summary(payload: Mapping[str, object], slide_type: str) -> bool:
    if slide_type != SLIDE_TYPE_SUMMARY:
        return False
    return complete_items(payload, _SUMMARY_POINTS) < FILL_MIN_ITEMS


def _feature_items(
    slide: _Slide, context: AutofixContext
) -> list[dict[str, object]] | None:
    points = context.outline.get(slide.index, SlideOutline()).key_points
    return build_items(
        FillSource(
            pairs=key_point_pairs(points, FEATURE_BUDGET.title),
            icons=context.policy.lucide_icon_allowlist,
            budget=FEATURE_BUDGET,
        )
    )


def _summary_items(
    slide: _Slide, context: AutofixContext
) -> list[dict[str, object]] | None:
    return build_items(
        FillSource(
            pairs=_summary_pairs(slide.index, context),
            icons=context.policy.lucide_icon_allowlist,
            budget=SUMMARY_BUDGET,
        )
    )


def _fill(payload: dict[str, object], slide: _Slide, context: AutofixContext) -> None:
    """Fill a PT payload's missing items in place."""
    if _needs_features(payload, slide.slide_type):
        features = _feature_items(slide, context)
        if features is not None:
            payload[_FEATURES] = features
    if _needs_summary(payload, slide.slide_type):
        points = _summary_items(slide, context)
        if points is not None:
            payload[_SUMMARY_POINTS] = points


def _mirror_fill(
    english: dict[str, object], portuguese: Mapping[str, object], slide: _Slide
) -> tuple[str, ...]:
    """Give the EN payload the PT items it lacks; return the lists copied.

    The copied items are Portuguese, so all of them are translated afterwards.
    """
    copied: list[str] = []
    checks = ((_FEATURES, _needs_features), (_SUMMARY_POINTS, _needs_summary))
    for list_field, needs in checks:
        if needs(english, slide.slide_type) and complete_items(portuguese, list_field):
            english[list_field] = copy.deepcopy(portuguese[list_field])
            copied.append(list_field)
    return tuple(copied)


def _polish(
    payload: Mapping[str, object], locale: str, context: AutofixContext
) -> dict[str, object]:
    """Balance tags, restore proper nouns, then the AE-0366 casing repair."""
    nouns = context.vocabulary
    cleaned = map_texts(
        payload, lambda text: restore_proper_nouns(balance_strong(text), nouns)
    )
    return repair_casing(cleaned, locale, context.policy)


@dataclass(frozen=True)
class _Pair:
    index: int
    english: Mapping[str, object]
    portuguese: Mapping[str, object]
    copied: tuple[str, ...] = ()


def _needs_translation(pair: _Pair, path: str) -> str:
    """The source text when the EN text at ``path`` must be translated, else ""."""
    text = text_at(pair.english, path)
    source = text_at(pair.portuguese, path)
    if source and path.split("[", 1)[0] in pair.copied and text == source:
        return source
    if source and is_untranslated(text, source):
        return source
    if not source and text and looks_portuguese(text):
        return text
    return ""


def _targets(pair: _Pair) -> list[RetranslateTarget]:
    targets: list[RetranslateTarget] = []
    for path in visible_paths(pair.english):
        source = _needs_translation(pair, path)
        if source:
            targets.append(
                RetranslateTarget(slide_index=pair.index, path=path, source=source)
            )
    return targets


@dataclass(frozen=True)
class _RecordFix:
    record: dict[str, object]
    targets: list[RetranslateTarget]


def _fix_record(record: Mapping[str, object], context: AutofixContext) -> _RecordFix:
    fixed = copy.deepcopy(dict(record))
    portuguese = as_dict(fixed.get(PRESENTATION_PT_KEY))
    if portuguese is None:
        return _RecordFix(record=fixed, targets=[])
    slide = _slide_of(fixed, portuguese)
    _fill(portuguese, slide, context)
    portuguese = _polish(portuguese, LANGUAGE_PT, context)
    fixed[PRESENTATION_PT_KEY] = portuguese
    english = as_dict(fixed.get(PRESENTATION_EN_KEY))
    if english is None:
        return _RecordFix(record=fixed, targets=[])
    copied = _mirror_fill(english, portuguese, slide)
    english = _polish(english, LANGUAGE_EN, context)
    fixed[PRESENTATION_EN_KEY] = english
    pair = _Pair(
        index=slide.index, english=english, portuguese=portuguese, copied=copied
    )
    return _RecordFix(record=fixed, targets=_targets(pair))


def plan_autofix(
    records: list[dict[str, object]], context: AutofixContext
) -> AutofixPlan:
    """Repair every record and collect the EN texts to translate again."""
    fixes = [_fix_record(record, context) for record in records]
    repaired = [fix.record for fix in fixes]
    targets = tuple(target for fix in fixes for target in fix.targets)
    return AutofixPlan(
        records=repaired, changed=repaired != records, retranslate=targets
    )


def _translated_record(
    record: dict[str, object], texts: Mapping[str, str], context: AutofixContext
) -> dict[str, object]:
    english = as_dict(record.get(PRESENTATION_EN_KEY))
    if english is None:
        return record
    index = _slide_index(record)
    updated = english
    for path in visible_paths(english):
        text = texts.get(AUTOFIX_TARGET_ID.format(slide=index, path=path))
        if text:
            updated = with_text(updated, path, text)
    if updated == english:
        return record
    return {**record, PRESENTATION_EN_KEY: _polish(updated, LANGUAGE_EN, context)}


def apply_translations(
    records: list[dict[str, object]],
    texts: Mapping[str, str],
    context: AutofixContext,
) -> list[dict[str, object]]:
    """Write the re-translated EN texts (by target id) and polish them."""
    if not texts:
        return records
    return [_translated_record(record, texts, context) for record in records]


__all__ = [
    "AutofixContext",
    "AutofixPlan",
    "RetranslateTarget",
    "SlideOutline",
    "apply_translations",
    "plan_autofix",
]
