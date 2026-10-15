"""Autopilot "Ponto de Vista" constants (AE-0377, ADR-0021 D10).

A POV topic never starts generation from an unconfirmed thesis: the run waits
in ``awaiting_thesis`` until the owner confirms, edits or discards the scout's
draft on Telegram. Radar IA (``news_analysis``) runs are capped per week.
"""

from __future__ import annotations

from rag_backend.domain.constants import IMAGE_STYLE_POV_EDITORIAL
from rag_backend.domain.constants.content_mode import (
    CONTENT_MODE_NEWS_ANALYSIS,
    CONTENT_MODE_POV,
    POV_THESIS_MAX_CHARS,
)

SCOUT_MODES: frozenset[str] = frozenset({CONTENT_MODE_NEWS_ANALYSIS, CONTENT_MODE_POV})
SCOUT_MODE_PATTERN = "^(news_analysis|pov)$"
THESIS_DRAFT_MAX_CHARS = POV_THESIS_MAX_CHARS
POV_IMAGE_STYLE = IMAGE_STYLE_POV_EDITORIAL
CONTENT_MODE_COLUMN_LENGTH = 20

# Intake rejections.
REASON_THESIS_MISSING = "thesis_missing"
REASON_WEEKLY_NEWS_CAP = "weekly_news_cap_reached"
# Growth plan 16.4 #10: Radar IA at most one post a week.
MAX_NEWS_RUNS_PER_WEEK = 1
DAYS_PER_WEEK = 7

# Run transition reasons.
REASON_THESIS_REQUESTED = "thesis_requested"
REASON_THESIS_CONFIRMED = "owner_thesis_confirmed"
REASON_THESIS_DISCARDED = "owner_thesis_discarded"
REASON_THESIS_EXPIRED = "thesis_expired"

# Callback data: ``ap:<kind>:<run uuid>`` (52 bytes, under Telegram's 64).
KIND_THESIS_CONFIRM = "thok"
KIND_THESIS_EDIT = "thed"
KIND_THESIS_DISCARD = "thno"
CALLBACK_THESIS_CONFIRM_PREFIX = "ap:thok:"
CALLBACK_THESIS_EDIT_PREFIX = "ap:thed:"
CALLBACK_THESIS_DISCARD_PREFIX = "ap:thno:"
CALLBACK_THESIS_PATTERN = (
    r"^ap:(thok|thed|thno):"
    r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12})$"
)
# The pending-reply marker for "Editar" (fits REWORK_PHASE_LENGTH).
THESIS_PENDING_PHASE = "pov_thesis"

BUTTON_THESIS_CONFIRM = "✅ Confirmar"
BUTTON_THESIS_EDIT = "✏️ Editar"
BUTTON_THESIS_DISCARD = "❌ Descartar"
TEXT_THESIS_PROMPT = (
    "🧭 Ponto de Vista proposto\n\nTema: {title}\n\nTese (rascunho do scout):\n"
    "«{thesis}»\n\nA tese é sua: confirme, edite ou descarte. Nada é gerado antes "
    "da sua confirmação."
)
TEXT_THESIS_CONFIRMED = "✅ Tese confirmada: «{thesis}». Gerando o carrossel."
TEXT_THESIS_EDIT = "✏️ Responda a esta mensagem com a sua tese (até 280 caracteres)."
TEXT_THESIS_DISCARDED = "❌ Tema descartado. Nada foi gerado."
TEXT_THESIS_TOO_LONG = (
    "A tese tem mais de 280 caracteres. Responda de novo, mais curta."
)
TEXT_THESIS_ALREADY = "Esta tese já foi resolvida."
ANSWER_THESIS_CONFIRMED = "Tese confirmada"
ANSWER_THESIS_DISCARDED = "Descartado"
ANSWER_THESIS_EDIT = "Responda com a sua tese"

LOG_THESIS = "autopilot.thesis"

__all__ = [
    "ANSWER_THESIS_CONFIRMED",
    "ANSWER_THESIS_DISCARDED",
    "ANSWER_THESIS_EDIT",
    "BUTTON_THESIS_CONFIRM",
    "BUTTON_THESIS_DISCARD",
    "BUTTON_THESIS_EDIT",
    "CALLBACK_THESIS_CONFIRM_PREFIX",
    "CALLBACK_THESIS_DISCARD_PREFIX",
    "CALLBACK_THESIS_EDIT_PREFIX",
    "CALLBACK_THESIS_PATTERN",
    "CONTENT_MODE_COLUMN_LENGTH",
    "DAYS_PER_WEEK",
    "KIND_THESIS_CONFIRM",
    "KIND_THESIS_DISCARD",
    "KIND_THESIS_EDIT",
    "LOG_THESIS",
    "MAX_NEWS_RUNS_PER_WEEK",
    "POV_IMAGE_STYLE",
    "REASON_THESIS_CONFIRMED",
    "REASON_THESIS_DISCARDED",
    "REASON_THESIS_EXPIRED",
    "REASON_THESIS_MISSING",
    "REASON_THESIS_REQUESTED",
    "REASON_WEEKLY_NEWS_CAP",
    "SCOUT_MODES",
    "SCOUT_MODE_PATTERN",
    "TEXT_THESIS_ALREADY",
    "TEXT_THESIS_CONFIRMED",
    "TEXT_THESIS_DISCARDED",
    "TEXT_THESIS_EDIT",
    "TEXT_THESIS_PROMPT",
    "TEXT_THESIS_TOO_LONG",
    "THESIS_DRAFT_MAX_CHARS",
    "THESIS_PENDING_PHASE",
]
