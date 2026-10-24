"""Plan the repair of checklist items whose edited text sits in the hidden body.

A checklist slide shows one line per item: the item title, else its body. The
editor used to write only the body, so an edited item kept showing its old title.
The repair moves a non-empty body that differs from the title into the title and
clears the body, in PT and EN, for the checklist slides only. A repaired item has
an empty body, so a second plan over the repaired copy finds nothing to move.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from rag_backend.application.services.carousel.editorial_distribution_constants import (
    SLIDE_INDEX_KEY,
)
from rag_backend.application.services.carousel.localized_slide_builder import (
    PRESENTATION_EN_KEY,
    PRESENTATION_PT_KEY,
    as_dict,
)
from rag_backend.application.services.carousel_template.strategies.save_checklist import (
    CHECKLIST_ITEM_KEYS,
)

ITEM_TITLE_KEY = "title"
ITEM_BODY_KEY = "body"
LOCALE_PT = "pt"
LOCALE_EN = "en"
_LOCALE_BY_PAYLOAD_KEY = {
    PRESENTATION_PT_KEY: LOCALE_PT,
    PRESENTATION_EN_KEY: LOCALE_EN,
}
_SLIDE_TYPE_KEY = "slide_type"


@dataclass(frozen=True)
class ChecklistItemMove:
    """One item whose body becomes its displayed title."""

    slide_index: int
    locale: str
    list_key: str
    item_index: int
    old_title: str
    new_title: str


@dataclass(frozen=True)
class ChecklistRepairPlan:
    """The moves to make and the edited slides that carry them."""

    moves: tuple[ChecklistItemMove, ...]
    edited_slides: list[dict[str, object]]


@dataclass(frozen=True)
class _ItemSite:
    slide_index: int
    locale: str
    list_key: str


def _text(item: Mapping[str, object], key: str) -> str:
    return str(item.get(key) or "").strip()


def _repair_items(
    raw: list[object], site: _ItemSite, moves: list[ChecklistItemMove]
) -> list[object]:
    """Items with each hidden body moved into the title (others unchanged)."""
    repaired: list[object] = []
    for position, item in enumerate(raw):
        if not isinstance(item, dict):
            repaired.append(item)
            continue
        title, body = _text(item, ITEM_TITLE_KEY), _text(item, ITEM_BODY_KEY)
        if not body or body == title:
            repaired.append(item)
            continue
        moves.append(
            ChecklistItemMove(
                slide_index=site.slide_index,
                locale=site.locale,
                list_key=site.list_key,
                item_index=position,
                old_title=title,
                new_title=body,
            )
        )
        repaired.append({**item, ITEM_TITLE_KEY: body, ITEM_BODY_KEY: ""})
    return repaired


def _repair_payload(
    payload: Mapping[str, object],
    site: _ItemSite,
    moves: list[ChecklistItemMove],
) -> dict[str, object]:
    """One locale payload with every checklist list repaired."""
    repaired = dict(payload)
    for list_key in CHECKLIST_ITEM_KEYS:
        raw = payload.get(list_key)
        if isinstance(raw, list):
            list_site = _ItemSite(site.slide_index, site.locale, list_key)
            repaired[list_key] = _repair_items(raw, list_site, moves)
    return repaired


def _repair_record(
    record: Mapping[str, object], moves: list[ChecklistItemMove]
) -> dict[str, object] | None:
    """The edited slide for one record, ``None`` when nothing moves."""
    index = record.get(SLIDE_INDEX_KEY)
    if not isinstance(index, int):
        return None
    before = len(moves)
    edited: dict[str, object] = {
        SLIDE_INDEX_KEY: index,
        _SLIDE_TYPE_KEY: record.get(_SLIDE_TYPE_KEY),
    }
    for payload_key, locale in _LOCALE_BY_PAYLOAD_KEY.items():
        payload = as_dict(record.get(payload_key)) or {}
        edited[payload_key] = _repair_payload(
            payload, _ItemSite(index, locale, ""), moves
        )
    return edited if len(moves) > before else None


def plan_checklist_repair(
    records: list[dict[str, object]], checklist_numbers: frozenset[int]
) -> ChecklistRepairPlan:
    """Moves and edited slides for the checklist slides among ``records``."""
    moves: list[ChecklistItemMove] = []
    edited_slides: list[dict[str, object]] = []
    for record in records:
        if record.get(SLIDE_INDEX_KEY) not in checklist_numbers:
            continue
        edited = _repair_record(record, moves)
        if edited is not None:
            edited_slides.append(edited)
    return ChecklistRepairPlan(moves=tuple(moves), edited_slides=edited_slides)


__all__ = [
    "ChecklistItemMove",
    "ChecklistRepairPlan",
    "plan_checklist_repair",
]
