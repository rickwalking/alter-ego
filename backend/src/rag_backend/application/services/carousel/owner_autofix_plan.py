"""Plan the owner autofix over localized slide records.

Pure: no DB, no LLM. Per slide and locale, in this order:

1. fill a content slide's empty features from its outline key points, a
   summary slide's missing points and a closing slide's missing actions
   (``structure_fill``; the EN side gets the PT items, which the
   re-translate step then translates);
2. balance ``<strong>`` tags and restore the carousel's proper nouns in every
   visible text, then the copy-hygiene repair (JSON blobs, markup,
   emphasis, encoding, doubled words) where the policy enables it;
3. the ``repair_casing`` (first letter of every heading, body sentence
   and item text, pt-BR accent aware; configured proper nouns).

EN texts that are still Portuguese (or the PT copy pasted as-is) become
re-translate targets; ``apply_translations`` writes the model's answers back
and runs steps 2-3 again on them.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass, field

from rag_backend.application.services.carousel.copy_hygiene_repair import (
    repair_copy_hygiene,
)
from rag_backend.application.services.carousel.localized_slide_builder import (
    PRESENTATION_EN_KEY,
    PRESENTATION_PT_KEY,
    as_dict,
)
from rag_backend.application.services.carousel.owner_autofix_paths import (
    map_texts,
    text_at,
    visible_paths,
    with_text,
)
from rag_backend.application.services.carousel.owner_autofix_text import (
    balance_strong,
    is_untranslated,
    looks_portuguese,
    normalize_emphasis,
    restore_proper_nouns,
)
from rag_backend.application.services.carousel.presentation_casing import (
    repair_casing,
)
from rag_backend.application.services.carousel.presentation_content_rules import (
    rule_active,
    slide_type_of,
)
from rag_backend.application.services.carousel.presentation_policy_types import (
    CarouselPresentationPolicy,
)
from rag_backend.application.services.carousel.structure_fill import (
    SlideOutline,
    SlideRef,
    StructureFillContext,
    fill_missing_items,
    mirror_missing_items,
)
from rag_backend.domain.constants.carousel import LANGUAGE_EN, LANGUAGE_PT
from rag_backend.domain.constants.carousel_autofix import AUTOFIX_TARGET_ID
from rag_backend.domain.constants.carousel_presentation import (
    VIOLATION_EMPHASIS_MARKUP_LOCALE_MISMATCH,
)
from rag_backend.domain.constants.workflow_state_fields import (
    STATE_FIELD_SLIDE_INDEX,
    STATE_FIELD_SLIDE_TYPE,
)


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


def _slide_index(record: Mapping[str, object]) -> int:
    value = record.get(STATE_FIELD_SLIDE_INDEX)
    return value if isinstance(value, int) else 0


def _slide_of(record: Mapping[str, object], payload: Mapping[str, object]) -> SlideRef:
    slide_type = payload.get(STATE_FIELD_SLIDE_TYPE) or record.get(
        STATE_FIELD_SLIDE_TYPE
    )
    return SlideRef(index=_slide_index(record), slide_type=str(slide_type or ""))


def _fill_context(context: AutofixContext) -> StructureFillContext:
    return StructureFillContext(
        icons=context.policy.lucide_icon_allowlist, outline=context.outline
    )


def _polish(
    payload: Mapping[str, object], locale: str, context: AutofixContext
) -> dict[str, object]:
    """Balance tags, restore proper nouns, copy hygiene, then casing."""
    nouns = context.vocabulary
    cleaned = map_texts(
        payload, lambda text: restore_proper_nouns(balance_strong(text), nouns)
    )
    cleaned = repair_copy_hygiene(cleaned, locale, context.policy)
    if rule_active(
        context.policy,
        VIOLATION_EMPHASIS_MARKUP_LOCALE_MISMATCH,
        slide_type_of(cleaned),
    ):
        cleaned = map_texts(cleaned, lambda text: normalize_emphasis(locale, text))
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
    fill_missing_items(portuguese, slide, _fill_context(context))
    portuguese = _polish(portuguese, LANGUAGE_PT, context)
    fixed[PRESENTATION_PT_KEY] = portuguese
    english = as_dict(fixed.get(PRESENTATION_EN_KEY))
    if english is None:
        return _RecordFix(record=fixed, targets=[])
    copied = mirror_missing_items(english, portuguese, slide)
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
