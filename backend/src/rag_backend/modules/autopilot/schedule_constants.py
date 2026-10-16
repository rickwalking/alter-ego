"""Scheduled Instagram publish constants (AE-0370).

Instagram has no native scheduling and its containers expire after 24 hours,
so the schedule is our own queue: ``scheduled_at`` on the run, and the
containers are created only when the run is due. Kept beside
``webhook_constants.py`` so neither file exceeds the 400-line limit.
"""

from __future__ import annotations

from rag_backend.modules.autopilot.constants import DAILY_CAP_TIMEZONE

# Good posting times, local to the owner's audience.
SCHEDULE_TIMEZONE = DAILY_CAP_TIMEZONE
SCHEDULE_SLOTS: tuple[str, ...] = ("12:00", "18:00", "21:00")
SCHEDULE_MIN_LEAD_MINUTES = 15
SCHEDULE_MAX_AHEAD_DAYS = 30
# A due run published this many minutes late says so in the notice.
SCHEDULE_LATE_NOTICE_MINUTES = 10
SCHEDULE_SCAN_LIMIT = 20
SECONDS_PER_MINUTE = 60
INDEX_RUNS_STATE_SCHEDULED_AT = "idx_autopilot_runs_state_scheduled_at"

# ``AUTOPILOT_DEFAULT_PUBLISH``: what Approve does.
PUBLISH_MODE_NOW = "now"
PUBLISH_MODE_NEXT_SLOT = "next_slot"

# Callback kinds. Each is the token between ``ap:`` and the run id.
KIND_PUBLISH_NOW = "pubnow"
KIND_SCHEDULE = "sched"
KIND_OTHER_TIME = "other"
KIND_UNSCHEDULE = "unsched"
KIND_SLOT = "at"
# AE-0404: the day step of the picker and its way back.
KIND_DAY = "d"
KIND_DAYS = "days"
CALLBACK_PUBLISH_NOW_PREFIX = "ap:pubnow:"
CALLBACK_SCHEDULE_PREFIX = "ap:sched:"
CALLBACK_OTHER_TIME_PREFIX = "ap:other:"
CALLBACK_UNSCHEDULE_PREFIX = "ap:unsched:"
CALLBACK_DAYS_PREFIX = "ap:days:"
# ``ap:d:<yyyymmdd>:<run id>``: 50 bytes, under Telegram's 64.
CALLBACK_DAY_FORMAT = "ap:d:{day}:"
CALLBACK_DAY_DATE_FORMAT = "%Y%m%d"
# ``ap:at:<unix seconds>:<run id>``: 53 bytes, under Telegram's 64.
CALLBACK_SLOT_FORMAT = "ap:at:{epoch}:"
CALLBACK_SCHEDULE_PATTERN = (
    r"^ap:(pubnow|sched|other|unsched|days):"
    r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12})$"
)
CALLBACK_SLOT_PATTERN = (
    r"^ap:at:([0-9]{1,10}):"
    r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12})$"
)
CALLBACK_DAY_PATTERN = (
    r"^ap:d:([0-9]{8}):"
    r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12})$"
)

# The pending-reply marker for "Outro horário" (fits REWORK_PHASE_LENGTH).
SCHEDULE_PENDING_PHASE = "schedule_time"

# Owner-typed times: ``HH:MM`` or ``DD/MM HH:MM``.
TIME_PATTERN = r"^([0-9]{1,2}):([0-9]{2})$"
DATE_TIME_PATTERN = r"^([0-9]{1,2})/([0-9]{1,2})\s+([0-9]{1,2}):([0-9]{2})$"
TIME_SEPARATOR = ":"
LOCAL_TIME_FORMAT = "%H:%M"
ERR_TIME_FORMAT = "time_format"
ERR_TIME_PAST = "time_past"
ERR_TIME_TOO_FAR = "time_too_far"

REASON_OWNER_SCHEDULED = "owner_scheduled"
REASON_OWNER_RESCHEDULED = "owner_rescheduled"
REASON_SCHEDULE_DUE = "schedule_due"
REASON_OWNER_UNSCHEDULED = "owner_unscheduled"
REASON_OWNER_PUBLISH_NOW = "owner_publish_now"
REASON_SCHEDULE_WITHDRAWN = "schedule_withdrawn"
REASON_SCHEDULE_RELEASE_FAILED = "schedule_release_failed"
LOG_SCHEDULE_DUE = "autopilot_schedule_due"

BUTTON_PUBLISH_NOW = "\U0001f680 Publicar agora"
BUTTON_SCHEDULE = "\U0001f5d3 Agendar"
BUTTON_OTHER_TIME = "✏️ Outro horário"
BUTTON_CANCEL_SCHEDULE = "❌ Cancelar agendamento"
BUTTON_CHANGE_SCHEDULE = "\U0001f5d3 Mudar dia/horário"
BUTTON_BACK_TO_DAYS = "← Dias"

ANSWER_CHOOSE = "Publicar agora ou agendar?"
ANSWER_SCHEDULED = "Agendado"
ANSWER_UNSCHEDULED = "Agendamento cancelado"
TEXT_PUBLISH_CHOICE = "Aprovado. Publicar agora ou agendar?"
TEXT_SCHEDULED = "\U0001f5d3 Agendado para {when}"
TEXT_SCHEDULED_REASON = "\U0001f5d3 Agendado para {when} ({reason})"
TEXT_CHOOSE_DAY = (
    "Escolha o dia (horário de Brasília). ⭐ = melhores dias pelo seu público."
)
TEXT_CHOOSE_TIME = "Escolha o horário para {day} (horário de Brasília):"
TEXT_TIME_LINE = "{time} — {reason}"
TEXT_DAY_OUT_OF_RANGE = "Esse dia não está mais disponível. Escolha outro."
TEXT_ASK_TIME = "Quando publicar? Responda HH:MM ou DD/MM HH:MM (horário de Brasília)."
TEXT_TIME_FORMAT = "Não entendi. Use HH:MM ou DD/MM HH:MM."
TEXT_TIME_PAST = "Esse horário já passou. Escolha um horário futuro."
TEXT_TIME_TOO_FAR = "No máximo 30 dias à frente. Escolha uma data mais próxima."
TEXT_UNSCHEDULED = "Agendamento cancelado. A revisão continua aberta."
TEXT_LATE_SUFFIX = " (publicado com atraso de {minutes} min)"
TEXT_SCHEDULE_WITHDRAWN = (
    "\U0001f5d3 Agendamento expirado: o carrossel não está mais aprovado. "
    "Nada foi publicado."
)

TIME_ERROR_TEXT: dict[str, str] = {
    ERR_TIME_FORMAT: TEXT_TIME_FORMAT,
    ERR_TIME_PAST: TEXT_TIME_PAST,
    ERR_TIME_TOO_FAR: TEXT_TIME_TOO_FAR,
}
# The ``expired`` notice text by state reason; others keep the 72 h text.
EXPIRED_TEXT_BY_REASON: dict[str, str] = {
    REASON_SCHEDULE_WITHDRAWN: TEXT_SCHEDULE_WITHDRAWN,
}
# Outbox payload key on ``content.autopilot.publish_notice``.
PAYLOAD_LATE_MINUTES = "late_minutes"
