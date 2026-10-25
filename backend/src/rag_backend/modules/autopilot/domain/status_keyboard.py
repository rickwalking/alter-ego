"""Which keyboard a status notice carries (QA r2 R3).

Kept apart from ``messages.py`` so neither file exceeds the 400-line limit.
"""

from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID

from rag_backend.modules.autopilot.constants import PAYLOAD_OFFER_RETRY
from rag_backend.modules.autopilot.domain.dead_letter import (
    dead_letter_keyboard,
    is_parked_notice,
)
from rag_backend.modules.autopilot.domain.messages import (
    InlineKeyboard,
    reason_of,
    retry_keyboard,
    review_keyboard,
)
from rag_backend.modules.autopilot.notify_constants import (
    KIND_PUBLISH_FAILED,
    KIND_REVIEW_REOPENED,
)
from rag_backend.modules.autopilot.recovery_constants import NO_RETRY_REASONS


def status_keyboard(
    kind: str, run_id: UUID, payload: Mapping[str, object]
) -> InlineKeyboard | None:
    """Retry for a failed publish, the review buttons for a reopened review.

    A run the generation queue parked gets "Tentar de novo" and "Descartar".
    """
    if is_parked_notice(kind, reason_of(payload)):
        return dead_letter_keyboard(run_id)
    if kind == KIND_PUBLISH_FAILED:
        return _retry_keyboard(run_id, payload)
    if kind == KIND_REVIEW_REOPENED:
        return review_keyboard(run_id)
    return None


def _retry_keyboard(
    run_id: UUID, payload: Mapping[str, object]
) -> InlineKeyboard | None:
    """No Retry when the post may already be live (QA r2 R3)."""
    if payload.get(PAYLOAD_OFFER_RETRY) is False:
        return None
    if reason_of(payload) in NO_RETRY_REASONS:
        return None
    return retry_keyboard(run_id)
