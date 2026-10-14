"""Pure Telegram copy and keyboards. No HTTP."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from uuid import UUID

from rag_backend.modules.autopilot.constants import (
    CALLBACK_RETRY_PREFIX,
    EVENT_TYPE_PUBLISH_NOTICE,
    EVENT_TYPE_READY_FOR_OWNER,
    EVENT_TYPE_STATE_CHANGED,
    NOTICE_PUBLISH_FAILED,
    NOTICE_PUBLISHED,
    PAYLOAD_ERROR_CODE,
    PAYLOAD_OUTCOME,
    PAYLOAD_PERMALINK,
    PAYLOAD_REASON,
    PAYLOAD_STATE,
    TEXT_ENCODING,
)
from rag_backend.modules.autopilot.domain.exceptions import CallbackDataTooLongError
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.notify_constants import (
    BUTTON_APPROVE,
    BUTTON_REJECT,
    BUTTON_RETRY,
    BUTTON_REWORK,
    CALLBACK_APPROVE_PREFIX,
    CALLBACK_DATA_MAX_BYTES,
    CALLBACK_REJECT_PREFIX,
    CALLBACK_REWORK_PREFIX,
    CAPTION_PREVIEW_CHARS,
    CAPTION_TEMPLATE,
    EVENT_TYPE_IG_EXPIRING,
    KIND_ESCALATED,
    KIND_EXPIRED,
    KIND_FAILED,
    KIND_IG_EXPIRING,
    KIND_PUBLISH_FAILED,
    KIND_PUBLISHED,
    KIND_REMINDER,
    KIND_REVIEW,
    KIND_REVIEW_REOPENED,
    LABEL_PERSONA,
    LABEL_SCORE_MISSING,
    LABEL_SOURCES,
    PATH_OWNER_UI,
    PAYLOAD_DAYS_REMAINING,
    PAYLOAD_PERSONA_SCORE,
    PAYLOAD_REVISION,
    PAYLOAD_SOURCES_COUNT,
    PERSONA_SCORE_FORMAT,
    TEXT_CAPTION_MISSING,
    TEXT_ESCALATED,
    TEXT_ESCALATED_WITH_LINK,
    TEXT_EXPIRED,
    TEXT_FAILED,
    TEXT_IG_EXPIRY,
    TEXT_IG_EXPIRY_DAYS,
    TEXT_PUBLISH_FAILED,
    TEXT_PUBLISHED,
    TEXT_PUBLISHED_NO_LINK,
    TEXT_REMINDER,
    TEXT_REVIEW_REOPENED,
)
from rag_backend.modules.autopilot.recovery_constants import (
    REASON_REVIEW_REOPENED,
    REASON_REWORK_RETRY,
)
from rag_backend.modules.autopilot.webhook_constants import (
    BUTTON_PHASE_DESIGN,
    BUTTON_PHASE_IMAGES,
    BUTTON_PHASE_OUTLINE,
    BUTTON_PHASE_TEXT,
    CALLBACK_PHASE_PREFIX,
    PHASE_SLUG_DESIGN,
    PHASE_SLUG_IMAGES,
    PHASE_SLUG_OUTLINE,
    PHASE_SLUG_TEXT,
)


@dataclass(frozen=True, kw_only=True)
class InlineButton:
    """One inline-keyboard button."""

    text: str
    callback_data: str


@dataclass(frozen=True, kw_only=True)
class InlineKeyboard:
    """Rows of inline buttons. Empty means no keyboard."""

    rows: tuple[tuple[InlineButton, ...], ...]


@dataclass(frozen=True, kw_only=True)
class ScoreSummary:
    """Album caption inputs."""

    title: str
    persona_score: float | None
    sources_count: int


@dataclass(frozen=True, kw_only=True)
class StatusCopy:
    """Facts a status message may quote."""

    reason: str
    link: str
    permalink: str
    days_remaining: int | None


def callback_data(prefix: str, run_id: UUID) -> str:
    """``ap:<action>:<run_id>``. Raises when the UTF-8 form exceeds 64 bytes."""
    value = f"{prefix}{run_id}"
    size = len(value.encode(TEXT_ENCODING))
    if size > CALLBACK_DATA_MAX_BYTES:
        raise CallbackDataTooLongError(size)
    return value


def review_keyboard(run_id: UUID) -> InlineKeyboard:
    """Approve, Rework, and Reject for one run."""
    row = (
        InlineButton(
            text=BUTTON_APPROVE,
            callback_data=callback_data(CALLBACK_APPROVE_PREFIX, run_id),
        ),
        InlineButton(
            text=BUTTON_REWORK,
            callback_data=callback_data(CALLBACK_REWORK_PREFIX, run_id),
        ),
        InlineButton(
            text=BUTTON_REJECT,
            callback_data=callback_data(CALLBACK_REJECT_PREFIX, run_id),
        ),
    )
    return InlineKeyboard(rows=(row,))


def rework_phase_keyboard(run_id: UUID) -> InlineKeyboard:
    """Text, Design, Images, and Outline. Text's callback token maps to content."""
    buttons = (
        (BUTTON_PHASE_TEXT, PHASE_SLUG_TEXT),
        (BUTTON_PHASE_DESIGN, PHASE_SLUG_DESIGN),
        (BUTTON_PHASE_IMAGES, PHASE_SLUG_IMAGES),
        (BUTTON_PHASE_OUTLINE, PHASE_SLUG_OUTLINE),
    )
    row = tuple(
        InlineButton(
            text=label,
            callback_data=callback_data(f"{CALLBACK_PHASE_PREFIX}{token}:", run_id),
        )
        for label, token in buttons
    )
    return InlineKeyboard(rows=(row[:2], row[2:]))


def retry_keyboard(run_id: UUID) -> InlineKeyboard:
    """The publish-failed Retry button."""
    button = InlineButton(
        text=BUTTON_RETRY,
        callback_data=callback_data(CALLBACK_RETRY_PREFIX, run_id),
    )
    return InlineKeyboard(rows=((button,),))


def album_caption(summary: ScoreSummary) -> str:
    """Title plus persona score and source count, for the first slide."""
    score = LABEL_SCORE_MISSING
    if summary.persona_score is not None:
        score = format(summary.persona_score, PERSONA_SCORE_FORMAT)
    return CAPTION_TEMPLATE.format(
        title=summary.title,
        persona=LABEL_PERSONA,
        score=score,
        sources=summary.sources_count,
        sources_label=LABEL_SOURCES,
    )


def caption_preview(caption: str) -> str:
    """The keyboard message body, at most 1000 characters."""
    text = caption.strip()
    if not text:
        return TEXT_CAPTION_MISSING
    return text[:CAPTION_PREVIEW_CHARS]


def owner_ui_link(base_url: str, project_id: str) -> str:
    """Web UI URL for an escalated carousel. Empty when the base is unset."""
    base = base_url.strip().rstrip("/")
    if not base or not project_id:
        return ""
    return f"{base}{PATH_OWNER_UI}/{project_id}"


def notice_kind(event_type: str, payload: Mapping[str, object]) -> str | None:
    """Which notice an outbox event asks for, or None to ignore it."""
    if event_type == EVENT_TYPE_READY_FOR_OWNER:
        return KIND_REVIEW
    if event_type == EVENT_TYPE_IG_EXPIRING:
        return KIND_IG_EXPIRING
    if event_type == EVENT_TYPE_PUBLISH_NOTICE:
        return _publish_kind(payload)
    if event_type == EVENT_TYPE_STATE_CHANGED:
        return _state_kind(payload)
    return None


def status_text(kind: str, copy: StatusCopy) -> str:
    """Body for a non-review notice. Unknown kinds are empty."""
    builder = _STATUS_TEXT.get(kind)
    if builder is None:
        return ""
    return builder(copy)


def revision_of(payload: Mapping[str, object]) -> int:
    """Lock version captured when the run became ready. Missing means 0."""
    return _int_or_zero(payload.get(PAYLOAD_REVISION))


def persona_score_of(payload: Mapping[str, object]) -> float | None:
    """Persona score copied onto the ready event."""
    value = payload.get(PAYLOAD_PERSONA_SCORE)
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value)


def sources_count_of(payload: Mapping[str, object]) -> int:
    """Research-source count copied onto the ready event."""
    return _int_or_zero(payload.get(PAYLOAD_SOURCES_COUNT))


def reason_of(payload: Mapping[str, object]) -> str:
    """State or publish reason. Empty when the payload omits it."""
    reason = payload.get(PAYLOAD_REASON)
    if isinstance(reason, str) and reason:
        return reason
    code = payload.get(PAYLOAD_ERROR_CODE)
    if isinstance(code, str):
        return code
    return ""


def permalink_of(payload: Mapping[str, object]) -> str:
    """Published permalink, or empty."""
    value = payload.get(PAYLOAD_PERMALINK)
    if isinstance(value, str):
        return value
    return ""


def days_remaining_of(payload: Mapping[str, object]) -> int | None:
    """Days until the Instagram token expires, when the event carries them."""
    value = payload.get(PAYLOAD_DAYS_REMAINING)
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _publish_kind(payload: Mapping[str, object]) -> str | None:
    outcome = payload.get(PAYLOAD_OUTCOME)
    if outcome == NOTICE_PUBLISHED:
        return KIND_PUBLISHED
    if outcome == NOTICE_PUBLISH_FAILED:
        return KIND_PUBLISH_FAILED
    return None


def _state_kind(payload: Mapping[str, object]) -> str | None:
    state = payload.get(PAYLOAD_STATE)
    if state == AutopilotRunState.AWAITING_OWNER.value:
        return _reopened_kind(payload)
    return _STATE_KINDS.get(str(state))


def _reopened_kind(payload: Mapping[str, object]) -> str | None:
    """Back to the owner without a new revision: send the buttons again."""
    if payload.get(PAYLOAD_REASON) in _REOPEN_REASONS:
        return KIND_REVIEW_REOPENED
    return None


_STATE_KINDS: dict[str, str] = {
    AutopilotRunState.ESCALATED.value: KIND_ESCALATED,
    AutopilotRunState.FAILED.value: KIND_FAILED,
    AutopilotRunState.EXPIRED.value: KIND_EXPIRED,
}
_REOPEN_REASONS = frozenset({REASON_REWORK_RETRY, REASON_REVIEW_REOPENED})


def _failed(copy: StatusCopy) -> str:
    return TEXT_FAILED.format(reason=copy.reason)


def _publish_failed(copy: StatusCopy) -> str:
    return TEXT_PUBLISH_FAILED.format(reason=copy.reason)


def _expired(copy: StatusCopy) -> str:
    del copy
    return TEXT_EXPIRED


def _reopened(copy: StatusCopy) -> str:
    return TEXT_REVIEW_REOPENED.format(reason=copy.reason)


def _reminder(copy: StatusCopy) -> str:
    del copy
    return TEXT_REMINDER


def _escalated(copy: StatusCopy) -> str:
    if not copy.link:
        return TEXT_ESCALATED.format(reason=copy.reason)
    return TEXT_ESCALATED_WITH_LINK.format(reason=copy.reason, link=copy.link)


def _published(permalink: str) -> str:
    if not permalink:
        return TEXT_PUBLISHED_NO_LINK
    return TEXT_PUBLISHED.format(permalink=permalink)


def _token(days: int | None) -> str:
    if days is None:
        return TEXT_IG_EXPIRY
    return TEXT_IG_EXPIRY_DAYS.format(days=days)


def _published_copy(copy: StatusCopy) -> str:
    return _published(copy.permalink)


def _token_copy(copy: StatusCopy) -> str:
    return _token(copy.days_remaining)


_STATUS_TEXT: dict[str, Callable[[StatusCopy], str]] = {
    KIND_ESCALATED: _escalated,
    KIND_FAILED: _failed,
    KIND_PUBLISHED: _published_copy,
    KIND_PUBLISH_FAILED: _publish_failed,
    KIND_IG_EXPIRING: _token_copy,
    KIND_REMINDER: _reminder,
    KIND_EXPIRED: _expired,
    KIND_REVIEW_REOPENED: _reopened,
}


def _int_or_zero(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return 0
    return value
