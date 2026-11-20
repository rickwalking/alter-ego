"""Plain-text Telegram copy and buttons for a repost draft. Pure."""

from __future__ import annotations

from dataclasses import dataclass

from rag_backend.modules.autopilot.domain.insights import InsightMetrics
from rag_backend.modules.autopilot.domain.messages import InlineButton, InlineKeyboard
from rag_backend.modules.autopilot.domain.repost import Repost
from rag_backend.modules.autopilot.domain.schedule import when_label
from rag_backend.modules.autopilot.repost_constants import (
    BUTTON_APPROVE,
    BUTTON_CAPTION,
    BUTTON_ORIGINAL,
    BUTTON_REJECT,
    CALLBACK_CAPTION,
    CALLBACK_NO,
    CALLBACK_OK,
    CALLBACK_ORIGINAL,
    CALLBACK_PREFIX,
    COVER_GROK,
    TEXT_CAPTION,
    TEXT_DECIDED_APPROVED,
    TEXT_EXPIRES,
    TEXT_HEADER,
    TEXT_HOOK,
    TEXT_METRICS,
    TEXT_NOW,
    TEXT_ORIGINAL,
    TEXT_PREVIEW_LINK,
    TEXT_REASON,
    TEXT_UNKNOWN,
    TEXT_WINDOW,
)

_COVER_LABELS = {COVER_GROK: "nova (Grok)"}
_COVER_ORIGINAL_LABEL = "original"


@dataclass(frozen=True, kw_only=True)
class ApprovalNotice:
    """The draft, its original Reel's metrics, and a preview link when needed."""

    repost: Repost
    metrics: InsightMetrics
    preview_link: str | None = None


def approval_text(notice: ApprovalNotice) -> str:
    """The owner prompt: original, metrics, hook, reason, window, caption."""
    repost = notice.repost
    parts = [
        TEXT_HEADER,
        TEXT_ORIGINAL.format(permalink=repost.permalink or repost.media_id),
        metrics_line(notice.metrics),
    ]
    if repost.hook_text:
        parts.append(TEXT_HOOK.format(hook=repost.hook_text))
    parts.append(TEXT_REASON.format(reason=repost.reason))
    if repost.window is not None:
        parts.append(
            TEXT_WINDOW.format(
                earliest=when_label(repost.window.earliest),
                latest=when_label(repost.window.latest),
            )
        )
    if notice.preview_link:
        parts.append(TEXT_PREVIEW_LINK.format(url=notice.preview_link))
    parts += [TEXT_CAPTION.format(caption=repost.caption), TEXT_EXPIRES]
    return "\n\n".join(parts)


def metrics_line(metrics: InsightMetrics) -> str:
    """The original Reel's counts; unknown values show a dash."""
    return TEXT_METRICS.format(
        views=_count(metrics.views),
        reach=_count(metrics.reach),
        likes=_count(metrics.likes),
        comments=_count(metrics.comments),
        saved=_count(metrics.saved),
        shares=_count(metrics.shares),
        follows=_count(metrics.follows),
    )


def approval_keyboard(repost: Repost) -> InlineKeyboard:
    """Aprovar, Usar capa original, Editar legenda, Rejeitar (under 64 bytes)."""
    return InlineKeyboard(
        rows=(
            (_button(BUTTON_APPROVE, CALLBACK_OK, repost),),
            (_button(BUTTON_ORIGINAL, CALLBACK_ORIGINAL, repost),),
            (_button(BUTTON_CAPTION, CALLBACK_CAPTION, repost),),
            (_button(BUTTON_REJECT, CALLBACK_NO, repost),),
        )
    )


def approved_text(repost: Repost) -> str:
    """The prompt after approval: when it goes out and which cover."""
    when = TEXT_NOW
    publish_at, approved_at = repost.publish_at, repost.approved_at
    if publish_at is not None and approved_at is not None and publish_at > approved_at:
        when = when_label(publish_at)
    cover = _COVER_LABELS.get(repost.cover_choice or "", _COVER_ORIGINAL_LABEL)
    return TEXT_DECIDED_APPROVED.format(when=when, cover=cover)


def _button(text: str, action: str, repost: Repost) -> InlineButton:
    return InlineButton(
        text=text, callback_data=f"{CALLBACK_PREFIX}{action}:{repost.id}"
    )


def _count(value: int | None) -> str:
    return TEXT_UNKNOWN if value is None else f"{value:,}".replace(",", ".")


__all__ = [
    "ApprovalNotice",
    "approval_keyboard",
    "approval_text",
    "approved_text",
    "metrics_line",
]
