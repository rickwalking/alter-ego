"""Autopilot "Ponto de Vista" constants (ADR-0021 D10).

A POV topic never starts generation from an unconfirmed thesis: the run waits
in ``awaiting_thesis`` until the owner confirms, edits or discards the scout's
draft on Telegram. Radar IA (``news_analysis``) runs are capped per week.

- Scout v4 adds ``pov_news``: news through the owner's point of view.
- POV point slides default to neo-anime artwork; a scout topic that names another
  supported style keeps it. Slide 1 is always the owner's photo.
- Callback data is ``ap:<kind>:<run uuid>`` (52 bytes, under Telegram's 64).
- The pending-reply marker for “Editar” fits ``REWORK_PHASE_LENGTH``.
- A POV carousel needs the persona and the slide-1 photo.
- With ``AUTOPILOT_PERSONA_ID`` empty, the persona is resolved by name.
"""

from __future__ import annotations

from rag_backend.domain.constants.carousel import IMAGE_STYLE_NEO_ANIME
from rag_backend.domain.constants.content_mode import (
    CONTENT_MODE_NEWS_ANALYSIS,
    CONTENT_MODE_POV,
    CONTENT_MODE_POV_NEWS,
    POV_THESIS_MAX_CHARS,
)
from rag_backend.modules.autopilot.autofix_constants import (
    REASON_PERSONA_JUDGE_UNAVAILABLE,
    TEXT_PERSONA_JUDGE_UNAVAILABLE,
)
from rag_backend.modules.autopilot.cover_constants import (
    REASON_COVER_RENDER_FAILED,
    TEXT_COVER_RENDER_FAILED,
)

SCOUT_MODES: frozenset[str] = frozenset({
    CONTENT_MODE_NEWS_ANALYSIS,
    CONTENT_MODE_POV,
    CONTENT_MODE_POV_NEWS,
})
SCOUT_MODE_PATTERN = "^(news_analysis|pov|pov_news)$"
THESIS_DRAFT_MAX_CHARS = POV_THESIS_MAX_CHARS
POV_IMAGE_STYLE = IMAGE_STYLE_NEO_ANIME
CONTENT_MODE_COLUMN_LENGTH = 20

REASON_THESIS_MISSING = "thesis_missing"
REASON_WEEKLY_NEWS_CAP = "weekly_news_cap_reached"
MAX_NEWS_RUNS_PER_WEEK = 1
DAYS_PER_WEEK = 7

REASON_THESIS_REQUESTED = "thesis_requested"
REASON_THESIS_CONFIRMED = "owner_thesis_confirmed"
REASON_THESIS_DISCARDED = "owner_thesis_discarded"
REASON_THESIS_EXPIRED = "thesis_expired"

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
THESIS_PENDING_PHASE = "pov_thesis"

BUTTON_THESIS_CONFIRM = "✅ Confirmar"
BUTTON_THESIS_EDIT = "✏️ Editar"
BUTTON_THESIS_DISCARD = "❌ Descartar"
MODE_LABEL_POV = "Ponto de Vista"
MODE_LABEL_POV_NEWS = "Ponto de Vista: Notícia"
TEXT_THESIS_PROMPT = (
    "🧭 {mode} proposto\n\nTema: {title}\n\nTese (rascunho do scout):\n"
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

REASON_PERSONA_NOT_SCORED = "persona_not_scored"
REASON_HOOK_PHOTO_MISSING = "hook_photo_missing"
TEXT_PERSONA_NOT_SCORED = (
    "⚠️ POV precisa da persona Pedro configurada: o carrossel não recebeu nota "
    'de voz. Crie a persona "Pedro" (ou defina AUTOPILOT_PERSONA_ID) e gere de novo.'
)
TEXT_HOOK_PHOTO_MISSING = (
    '📸 POV sem foto do slide 1: envie uma foto com o papel "hook" na sua '
    "biblioteca de fotos do dashboard. Nada foi gerado."
)
POV_TEXT_BY_REASON: dict[str, str] = {
    REASON_PERSONA_NOT_SCORED: TEXT_PERSONA_NOT_SCORED,
    REASON_HOOK_PHOTO_MISSING: TEXT_HOOK_PHOTO_MISSING,
    REASON_COVER_RENDER_FAILED: TEXT_COVER_RENDER_FAILED,
    REASON_PERSONA_JUDGE_UNAVAILABLE: TEXT_PERSONA_JUDGE_UNAVAILABLE,
}
AUTOPILOT_PERSONA_NAME = "Pedro"
LOG_PERSONA_UNRESOLVED = "autopilot.persona_unresolved"

__all__ = [
    "ANSWER_THESIS_CONFIRMED",
    "ANSWER_THESIS_DISCARDED",
    "ANSWER_THESIS_EDIT",
    "AUTOPILOT_PERSONA_NAME",
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
    "LOG_PERSONA_UNRESOLVED",
    "LOG_THESIS",
    "MAX_NEWS_RUNS_PER_WEEK",
    "MODE_LABEL_POV",
    "MODE_LABEL_POV_NEWS",
    "POV_IMAGE_STYLE",
    "POV_TEXT_BY_REASON",
    "REASON_HOOK_PHOTO_MISSING",
    "REASON_PERSONA_NOT_SCORED",
    "REASON_THESIS_CONFIRMED",
    "REASON_THESIS_DISCARDED",
    "REASON_THESIS_EXPIRED",
    "REASON_THESIS_MISSING",
    "REASON_THESIS_REQUESTED",
    "REASON_WEEKLY_NEWS_CAP",
    "SCOUT_MODES",
    "SCOUT_MODE_PATTERN",
    "TEXT_HOOK_PHOTO_MISSING",
    "TEXT_PERSONA_NOT_SCORED",
    "TEXT_THESIS_ALREADY",
    "TEXT_THESIS_CONFIRMED",
    "TEXT_THESIS_DISCARDED",
    "TEXT_THESIS_EDIT",
    "TEXT_THESIS_PROMPT",
    "TEXT_THESIS_TOO_LONG",
    "THESIS_DRAFT_MAX_CHARS",
    "THESIS_PENDING_PHASE",
]
