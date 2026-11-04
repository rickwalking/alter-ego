"""Constants of the owner's carousel Retry on Telegram.

The escalation notice of a run that did not dead-letter carries
"🔁 Tentar de novo" with callback ``ap:cr:<run uuid>`` (``ap:retry:`` is the
publish retry, ``ap:qrt:`` the dead-letter retry). The refusal codes are the
generation queue's Retry codes.
"""

from __future__ import annotations

CALLBACK_CAROUSEL_RETRY_PREFIX = "ap:cr:"
CALLBACK_CAROUSEL_RETRY_PATTERN = (
    r"ap:cr:([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
)
BUTTON_CAROUSEL_RETRY = "🔁 Tentar de novo"
ANSWER_CAROUSEL_RETRY = "Refazendo"
ANSWER_CAROUSEL_RETRY_REFUSED = "Não foi possível tentar de novo"
TEXT_CAROUSEL_RETRY_ACCEPTED = "🔁 Refazendo a fase {phase}…"
TEXT_CAROUSEL_RETRY_REFUSED = "Não foi possível tentar de novo ({code})."

REFUSAL_RUN_IN_PROGRESS = "resume_already_in_progress"
REFUSAL_AUTOPILOT_ACTIVE = "autopilot_active"
REFUSAL_USE_REPROCESS = "use_reprocess"
REFUSAL_REVISION_CAP = "revision_cap_exceeded"
REFUSAL_NO_CHECKPOINT = "no_checkpoint"
REFUSAL_NOT_RETRYABLE = "not_retryable"
REFUSAL_NOT_OWNER = "not_owner"

TEXT_CAROUSEL_RETRY_BY_REFUSAL: dict[str, str] = {
    REFUSAL_RUN_IN_PROGRESS: "Esta fase já está rodando.",
    REFUSAL_AUTOPILOT_ACTIVE: "O autopilot já está trabalhando neste carrossel.",
    REFUSAL_USE_REPROCESS: "Este carrossel parou na fila: use o reprocessar.",
    REFUSAL_REVISION_CAP: (
        "Esta fase já usou todas as revisões. Edite o texto direto no site."
    ),
    REFUSAL_NO_CHECKPOINT: (
        "O ponto de retomada deste carrossel não existe mais; comece de novo no site."
    ),
    REFUSAL_NOT_RETRYABLE: "Não há nada para tentar de novo neste carrossel.",
    REFUSAL_NOT_OWNER: "Só o dono do carrossel pode tentar de novo.",
}
