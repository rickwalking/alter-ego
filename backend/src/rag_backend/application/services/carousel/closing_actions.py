"""A closing slide's items live under ``actions``.

Two places put them under ``features``: the drafting skill told the model to
return the closing checklist as ``features``, and the slide row stores a
closing slide's actions in its ``features`` column (there is no ``actions``
column). Every payload built for the workflow state goes through
``restore_closing_actions`` so the closing items keep one key end to end.
"""

from __future__ import annotations

from collections.abc import Mapping

from rag_backend.domain.constants.carousel import SLIDE_TYPE_CLOSING

_FEATURES = "features"
_ACTIONS = "actions"
_SLIDE_TYPE_KEYS = ("slide_type", "type")


def _is_closing(payload: Mapping[str, object], slide_type: str) -> bool:
    if slide_type:
        return slide_type == SLIDE_TYPE_CLOSING
    return any(payload.get(key) == SLIDE_TYPE_CLOSING for key in _SLIDE_TYPE_KEYS)


def restore_closing_actions(
    payload: dict[str, object], slide_type: str = ""
) -> dict[str, object]:
    """Move a closing payload's ``features`` under ``actions`` (in place).

    ``slide_type`` is the record's type when the payload carries none. Only
    when the payload has no actions yet: real actions always win.
    """
    if not _is_closing(payload, slide_type):
        return payload
    if payload.get(_ACTIONS) or not isinstance(payload.get(_FEATURES), list):
        return payload
    payload[_ACTIONS] = payload.pop(_FEATURES)
    return payload


__all__ = ["restore_closing_actions"]
