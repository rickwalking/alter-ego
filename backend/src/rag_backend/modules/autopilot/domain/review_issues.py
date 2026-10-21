"""Quality issues and the "Fix issues" button on the review message."""

from __future__ import annotations

from uuid import UUID

from rag_backend.modules.autopilot.domain.messages import (
    InlineButton,
    InlineKeyboard,
    callback_data,
    review_keyboard,
)
from rag_backend.modules.autopilot.notify_constants import (
    BUTTON_FIX,
    CALLBACK_FIX_PREFIX,
    ISSUE_BULLET,
    ISSUES_HEADER,
    ISSUES_SEPARATOR,
)


def review_keyboard_with_fix(run_id: UUID, *, fixable: bool) -> InlineKeyboard:
    """Approve, Rework, Reject, plus "Fix issues" when something is fixable."""
    keyboard = review_keyboard(run_id)
    if not fixable:
        return keyboard
    fix = InlineButton(
        text=BUTTON_FIX,
        callback_data=callback_data(CALLBACK_FIX_PREFIX, run_id),
    )
    first, *rest = keyboard.rows
    return InlineKeyboard(rows=((*first, fix), *rest))


def with_issues(body: str, lines: tuple[str, ...]) -> str:
    """Append the issue list (already capped by the editorial side)."""
    if not lines:
        return body
    bullets = "\n".join(ISSUE_BULLET.format(line=line) for line in lines)
    return f"{body}{ISSUES_SEPARATOR}{ISSUES_HEADER}\n{bullets}"
