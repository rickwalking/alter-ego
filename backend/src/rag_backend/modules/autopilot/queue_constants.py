"""Constants of the Telegram queue flow: position, approve-all, dead letters, backlog.

The generation worker drives one carousel at a time in strict FIFO order (Pedro).
Callback data stays under Telegram's 64 bytes: ``ap:thall``, ``ap:qrt:<run uuid>``,
``ap:qdc:<run uuid>`` and ``ap:qnow:<topic uuid>``.

Backlog themes are topic candidates in one of the ``CANDIDATE_BACKLOG_*``
statuses: kept when the daily cap had no room, announced once, promoted to a
queued run by the next morning's intake or by "Gerar agora", or expired after
``BACKLOG_EXPIRY_DAYS``. A "Gerar agora" run does not count toward the daily cap.
"""

from __future__ import annotations

CALLBACK_APPROVE_ALL = "ap:thall"
CALLBACK_DEAD_RETRY_PREFIX = "ap:qrt:"
CALLBACK_DEAD_DISCARD_PREFIX = "ap:qdc:"
CALLBACK_GENERATE_NOW_PREFIX = "ap:qnow:"
CALLBACK_QUEUE_PATTERN = (
    r"ap:(qrt|qdc|qnow):"
    r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
)
KIND_DEAD_RETRY = "qrt"
KIND_DEAD_DISCARD = "qdc"
KIND_GENERATE_NOW = "qnow"

REASON_DEAD_LETTER_PREFIX = "queue_dead_letter:"
REASON_DEAD_RETRY = "owner_queue_retry"
REASON_DEAD_DISCARD = "owner_queue_discard"
REASON_BACKLOG_FULL = "backlog_full"

CANDIDATE_BACKLOG = "backlog"
CANDIDATE_BACKLOG_NOTED = "backlog_noted"
CANDIDATE_BACKLOG_EXPIRED = "backlog_expired"
CANDIDATE_PROMOTED = "promoted"
CANDIDATE_GENERATE_NOW = "generate_now"
BACKLOG_WAITING = (CANDIDATE_BACKLOG, CANDIDATE_BACKLOG_NOTED)

BACKLOG_MAX = 10
BACKLOG_EXPIRY_DAYS = 7
APPROVE_ALL_LIMIT = 10
DEFAULT_DRIVE_MINUTES = 15
RECENT_DRIVES = 10
QUEUE_TIMEZONE = "America/Sao_Paulo"
ETA_FORMAT = "%H:%M"

THESIS_BATCH_NOTICE_KEY = "thesis_batch"
THESIS_BATCH_MIN = 2

BUTTON_APPROVE_ALL = "✅ Aprovar todas"
BUTTON_DEAD_RETRY = "🔁 Tentar de novo"
BUTTON_DEAD_DISCARD = "🗑 Descartar"
BUTTON_GENERATE_NOW = "⚡ Gerar agora: {title}"
BUTTON_TITLE_MAX_CHARS = 40
LIST_TITLE_MAX_CHARS = 80
LIST_SEPARATOR = "; "
ELLIPSIS = "…"

TEXT_QUEUE_POSITION = "Na fila: posição {position} de {total} — início estimado {eta}."
TEXT_THESIS_CONFIRMED_QUEUED = "✅ Tese confirmada: «{thesis}». {position}"
TEXT_BATCH_HEADER = "📋 {count} teses esperando a sua confirmação:"
TEXT_BATCH_LINE = "{index}. «{thesis}»"
TEXT_BATCH_NO_DRAFT = "{index}. {title} (sem tese: use Editar na mensagem do tema)"
TEXT_APPROVED_HEADER = "✅ {count} teses confirmadas:"
TEXT_APPROVED_LINE = "{index}. «{thesis}» — posição {position} de {total}, início {eta}"
TEXT_APPROVED_NEED_EDIT = "Sem tese, confirme pelo Editar: {titles}"
TEXT_APPROVED_NONE = "Estas teses já foram resolvidas."
TEXT_DEAD_LETTER = (
    "⚠️ A fila parou este carrossel: {reason}\n"
    "Toque em Tentar de novo para recolocar na fila ou em Descartar."
)
TEXT_DEAD_RETRIED = "🔁 De volta à fila. {position}"
TEXT_DEAD_RETRIED_PLAIN = "🔁 De volta à fila."
TEXT_DEAD_DISCARDED = "🗑 Descartado. Nada mais será gerado para este tema."
TEXT_QUEUE_ALREADY = "Isto já foi resolvido."
TEXT_BACKLOG_NEW = (
    "🕗 {count} tema(s) passaram do limite diário e ficaram para amanhã. "
    "Toque em um para gerar agora:"
)
TEXT_BACKLOG_EXPIRED = (
    f"⌛ Saíram da fila de espera depois de {BACKLOG_EXPIRY_DAYS} dias: {{titles}}"
)
TEXT_GENERATED_NOW = "⚡ Gerando agora: «{title}». {position}"
TEXT_GENERATED_NOW_PLAIN = "⚡ Gerando agora: «{title}»."
ANSWER_APPROVED = "Teses confirmadas"
ANSWER_DEAD_RETRIED = "De volta à fila"
ANSWER_DEAD_DISCARDED = "Descartado"
ANSWER_GENERATED_NOW = "Na fila"

DEAD_LETTER_TEXT_BY_CODE: dict[str, str] = {
    "transient": "um erro temporário se repetiu até o limite de tentativas",
    "permanent": "um erro que não se resolve sozinho",
    "phase_budget_exhausted": (
        "a mesma fase falhou várias vezes seguidas (pode ser falta de memória "
        "na renderização das imagens)"
    ),
    "run_budget_exhausted": (
        "o carrossel parou várias vezes sem avançar (pode ser falta de memória "
        "na renderização das imagens)"
    ),
    "held_by_queue": "a fila desistiu do trabalho depois de várias quedas",
}
DEAD_LETTER_TEXT_DEFAULT = "um erro na fila de geração ({code})"

LOG_QUEUE_FLOW = "autopilot.queue_flow"
LOG_BACKLOG_PROMOTED = "autopilot_backlog_promoted"
LOG_BACKLOG_PROMOTION_FAILED = "autopilot_backlog_promotion_failed"
BACKLOG_PROMOTION_ENTRYPOINT = "autopilot_backlog_promotion"
BACKLOG_PROMOTION_CRON_UTC = "5 11 * * *"
