"""Mirror the owner autofix onto the workflow presentation copy (AE-0367).

The repaired PT/EN payloads replace the checkpoint's ``localized_slides``
payloads of the same slide, with a fresh validation report in the same patch.
The owner's fix supersedes the AE-0366 casing-repair markers (as a reviewer
edit does), so they are dropped. A closing slide keeps its ``actions`` key:
the rows store closing actions under ``features``.
"""

from __future__ import annotations

from collections.abc import Mapping

from rag_backend.application.services.carousel.localized_slide_builder import (
    PRESENTATION_EN_KEY,
    PRESENTATION_PT_KEY,
    as_dict,
)
from rag_backend.application.services.carousel.presentation_casing_markers import (
    drop_casing_repair_markers,
)
from rag_backend.application.services.carousel.presentation_review_pipeline import (
    WORKFLOW_STATE_LOCALIZED_SLIDES_KEY,
    WORKFLOW_STATE_PRESENTATION_VALIDATION_KEY,
    validate_localized_slides,
    validation_report_to_dict,
)
from rag_backend.domain.constants.carousel import LANGUAGE_EN, LANGUAGE_PT
from rag_backend.domain.constants.workflow_state_fields import STATE_FIELD_SLIDE_INDEX

_ACTIONS = "actions"
_FEATURES = "features"
_LOCALES: tuple[tuple[str, str], ...] = (
    (PRESENTATION_PT_KEY, LANGUAGE_PT),
    (PRESENTATION_EN_KEY, LANGUAGE_EN),
)


def _keep_actions_key(
    repaired: Mapping[str, object], previous: Mapping[str, object]
) -> dict[str, object]:
    payload = dict(repaired)
    renamed = _ACTIONS in previous and _FEATURES not in previous
    if renamed and _ACTIONS not in payload and _FEATURES in payload:
        payload[_ACTIONS] = payload.pop(_FEATURES)
    return payload


def _patched_slide(
    slide: Mapping[str, object], record: Mapping[str, object]
) -> dict[str, object]:
    updated = dict(slide)
    for payload_key, locale in _LOCALES:
        repaired = as_dict(record.get(payload_key))
        if repaired is None:
            continue
        previous = as_dict(slide.get(payload_key)) or {}
        updated[payload_key] = _keep_actions_key(repaired, previous)
        drop_casing_repair_markers(updated, locale)
    return updated


def _localized(state: Mapping[str, object]) -> list[Mapping[str, object]]:
    raw = state.get(WORKFLOW_STATE_LOCALIZED_SLIDES_KEY)
    if not isinstance(raw, list):
        return []
    return [slide for slide in raw if isinstance(slide, Mapping)]


def checkpoint_patch(
    state: Mapping[str, object],
    records: list[dict[str, object]],
    policy_version: str,
) -> dict[str, object] | None:
    """The single ``update_state`` patch, or None when there is no copy to patch."""
    slides = _localized(state)
    if not slides:
        return None
    by_index = {record.get(STATE_FIELD_SLIDE_INDEX): record for record in records}
    patched: list[dict[str, object]] = []
    for slide in slides:
        record = by_index.get(slide.get(STATE_FIELD_SLIDE_INDEX))
        patched.append(dict(slide) if record is None else _patched_slide(slide, record))
    report = validate_localized_slides(patched, policy_version=policy_version)
    return {
        WORKFLOW_STATE_LOCALIZED_SLIDES_KEY: patched,
        WORKFLOW_STATE_PRESENTATION_VALIDATION_KEY: validation_report_to_dict(report),
    }


__all__ = ["checkpoint_patch"]
