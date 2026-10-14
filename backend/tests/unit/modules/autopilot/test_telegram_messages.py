"""Pure Telegram copy, keyboards, and event classification (AE-0355).

Gherkin: tests/features/autopilot_telegram_notify.feature
"""

from __future__ import annotations

from uuid import UUID

import pytest

from rag_backend.modules.autopilot.constants import (
    CALLBACK_RETRY_PREFIX,
    EVENT_TYPE_PUBLISH_NOTICE,
    EVENT_TYPE_READY_FOR_OWNER,
    EVENT_TYPE_STATE_CHANGED,
    TEXT_ENCODING,
)
from rag_backend.modules.autopilot.domain.exceptions import CallbackDataTooLongError
from rag_backend.modules.autopilot.domain.messages import (
    ScoreSummary,
    StatusCopy,
    album_caption,
    callback_data,
    caption_preview,
    notice_kind,
    owner_ui_link,
    retry_keyboard,
    review_keyboard,
    status_text,
)
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
    EVENT_TYPE_IG_EXPIRING,
    KIND_ESCALATED,
    KIND_FAILED,
    KIND_IG_EXPIRING,
    KIND_PUBLISH_FAILED,
    KIND_PUBLISHED,
    KIND_REVIEW,
)

_RUN = UUID("11111111-1111-4111-8111-111111111111")


def test_callback_data_fits_the_telegram_limit() -> None:
    """Approve, Rework, Reject, and Retry callbacks are at most 64 bytes."""
    values = (
        callback_data(CALLBACK_APPROVE_PREFIX, _RUN),
        callback_data(CALLBACK_REWORK_PREFIX, _RUN),
        callback_data(CALLBACK_REJECT_PREFIX, _RUN),
        callback_data(CALLBACK_RETRY_PREFIX, _RUN),
    )
    assert values[0] == f"{CALLBACK_APPROVE_PREFIX}{_RUN}"
    for value in values:
        assert len(value.encode(TEXT_ENCODING)) <= CALLBACK_DATA_MAX_BYTES


def test_callback_data_rejects_an_overlong_prefix() -> None:
    with pytest.raises(CallbackDataTooLongError):
        callback_data("x" * 40, _RUN)


def test_review_keyboard_has_the_three_actions() -> None:
    """Scenario: Owner receives slides and buttons."""
    buttons = review_keyboard(_RUN).rows[0]
    assert [button.text for button in buttons] == [
        BUTTON_APPROVE,
        BUTTON_REWORK,
        BUTTON_REJECT,
    ]
    assert buttons[0].callback_data.startswith(CALLBACK_APPROVE_PREFIX)


def test_retry_keyboard_uses_the_retry_prefix() -> None:
    """Scenario: Publish failure offers retry."""
    button = retry_keyboard(_RUN).rows[0][0]
    assert button.text == BUTTON_RETRY
    assert button.callback_data == f"{CALLBACK_RETRY_PREFIX}{_RUN}"


def test_album_caption_includes_score_and_sources() -> None:
    text = album_caption(
        ScoreSummary(title="Agents", persona_score=82.4, sources_count=4)
    )
    assert text.startswith("Agents")
    assert "82" in text
    assert "4" in text


def test_album_caption_marks_a_missing_score() -> None:
    text = album_caption(
        ScoreSummary(title="Agents", persona_score=None, sources_count=0)
    )
    assert "Persona: not scored" in text


def test_caption_preview_truncates_and_fills_empty() -> None:
    assert caption_preview("") == "Review the slides above."
    long = "a" * (CAPTION_PREVIEW_CHARS + 25)
    assert len(caption_preview(long)) == CAPTION_PREVIEW_CHARS


def test_owner_link_uses_the_dashboard_path() -> None:
    """Scenario: Escalated run includes the reason and a link."""
    link = owner_ui_link("https://marinssolutions.com/", "proj-1")
    assert link == "https://marinssolutions.com/dashboard/create/proj-1"
    assert owner_ui_link("", "proj-1") == ""
    assert owner_ui_link("https://example.com", "") == ""


def test_notice_kind_maps_the_autopilot_family() -> None:
    assert notice_kind(EVENT_TYPE_READY_FOR_OWNER, {}) == KIND_REVIEW
    assert notice_kind(EVENT_TYPE_IG_EXPIRING, {}) == KIND_IG_EXPIRING
    published = {"outcome": "published"}
    failed = {"outcome": "publish_failed"}
    assert notice_kind(EVENT_TYPE_PUBLISH_NOTICE, published) == KIND_PUBLISHED
    assert notice_kind(EVENT_TYPE_PUBLISH_NOTICE, failed) == KIND_PUBLISH_FAILED
    assert notice_kind(EVENT_TYPE_PUBLISH_NOTICE, {"outcome": "queued"}) is None
    escalated = {"state": AutopilotRunState.ESCALATED.value}
    broken = {"state": AutopilotRunState.FAILED.value}
    assert notice_kind(EVENT_TYPE_STATE_CHANGED, escalated) == KIND_ESCALATED
    assert notice_kind(EVENT_TYPE_STATE_CHANGED, broken) == KIND_FAILED
    assert notice_kind(EVENT_TYPE_STATE_CHANGED, {"state": "generating"}) is None
    assert notice_kind("content.other", {}) is None


def test_status_text_quotes_reason_link_and_permalink() -> None:
    copy = StatusCopy(
        reason="persona_score_below_threshold",
        link="https://example.com/dashboard/create/p",
        permalink="https://instagram.com/p/abc",
        days_remaining=6,
    )
    assert "persona_score_below_threshold" in status_text(KIND_ESCALATED, copy)
    assert "https://example.com/dashboard/create/p" in status_text(KIND_ESCALATED, copy)
    assert "https://instagram.com/p/abc" in status_text(KIND_PUBLISHED, copy)
    assert "persona_score_below_threshold" in status_text(KIND_FAILED, copy)
    retry = status_text(KIND_PUBLISH_FAILED, copy)
    assert "publish failed" in retry
    assert "6" in status_text(KIND_IG_EXPIRING, copy)
    assert status_text(KIND_REVIEW, copy) == ""


def test_status_text_omits_a_missing_link_and_permalink() -> None:
    copy = StatusCopy(reason="phase_failed", link="", permalink="", days_remaining=None)
    escalated = status_text(KIND_ESCALATED, copy)
    assert "phase_failed" in escalated
    assert "http" not in escalated
    assert "posted" in status_text(KIND_PUBLISHED, copy)
    assert "expiring" in status_text(KIND_IG_EXPIRING, copy)
