"""Plain-text Telegram copy for a boost request."""

from __future__ import annotations

from rag_backend.modules.autopilot.boost_constants import (
    CALLBACK_NO,
    CALLBACK_OK,
    CALLBACK_PREFIX,
    CALLBACK_STOP,
)
from rag_backend.modules.autopilot.domain.boost import BoostRequest, format_money
from rag_backend.modules.autopilot.domain.messages import InlineButton, InlineKeyboard
from rag_backend.modules.autopilot.domain.topic_text import strip_controls


def boost_message(request: BoostRequest, week_cents: int, cap_cents: int) -> str:
    """The owner prompt. ``reason`` is already control-stripped."""
    reason = strip_controls(request.reason)
    budget = format_money(request.daily_budget_cents)
    total = format_money(request.total_budget_cents)
    week = format_money(week_cents)
    cap = format_money(cap_cents)
    link = request.permalink or request.media_id
    return (
        "Pedido de impulsionamento\n"
        f"Post: {link}\n"
        f"Orcamento: {budget}/dia x {request.days} dias = {total}\n"
        f"Objetivo: engajamento\n"
        f"Motivo: {reason}\n"
        f"Semana: {week} de {cap} comprometidos\n"
        "Expira em 12h."
    )


def boost_keyboard(request: BoostRequest) -> InlineKeyboard:
    """Approve and Reject. Callback data stays under 64 bytes."""
    total = format_money(request.total_budget_cents)
    approve = f"{CALLBACK_PREFIX}{CALLBACK_OK}:{request.id}"
    reject = f"{CALLBACK_PREFIX}{CALLBACK_NO}:{request.id}"
    return InlineKeyboard(
        rows=(
            (
                InlineButton(text=f"Aprovar {total}", callback_data=approve),
                InlineButton(text="Rejeitar", callback_data=reject),
            ),
        )
    )


def stop_data(request_id: str) -> str:
    """Callback data for the phase-3 Stop button."""
    return f"{CALLBACK_PREFIX}{CALLBACK_STOP}:{request_id}"


__all__ = ["boost_keyboard", "boost_message", "stop_data"]
