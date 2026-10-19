"""Constants for the autopilot model fix of failing slides (AE-0401).

Content-quality and voice-score failures at the content and design gates go
through deterministic repair, then up to 3 fast-model attempts per failing
slide and 2 more on the reasoning model (AE-0407), then straight to the
owner: they never spend the revise budget.
"""

from __future__ import annotations

from rag_backend.modules.autopilot.constants import REASON_PERSONA_SCORE
from rag_backend.modules.autopilot.quality_constants import REASON_CONTENT_QUALITY

# Reasons the model fix handles (owner decision 2026-10-16: low voice too).
AUTOFIX_REASONS: frozenset[str] = frozenset({
    REASON_CONTENT_QUALITY,
    REASON_PERSONA_SCORE,
})

# Langfuse metadata of the model-fix calls.
PHASE_AUTOFIX = "autofix"
AGENT_NAME_SLIDE_FIXER = "slide_fixer"

LOG_SLIDE_AUTOFIX = "autopilot_slide_autofix"
LOG_SLIDE_AUTOFIX_CONFLICT = "autopilot_slide_autofix_conflict"
LOG_SLIDE_AUTOFIX_ESCALATED = "autopilot_slide_autofix_escalated"
LOG_FIELD_SLIDE = "slide"
LOG_FIELD_ATTEMPT = "attempt"
LOG_FIELD_RULES_BEFORE = "rules_before"
LOG_FIELD_RULES_AFTER = "rules_after"
LOG_FIELD_OUTCOME = "outcome"
LOG_FIELD_MODEL_ROLE = "model_role"
LOG_FIELD_FAILING_SLIDES = "failing_slides"

# AE-0433: a judge that gave no score is not "below threshold". The run waits
# for a re-score on the next tick, then escalates with its own reason.
REASON_PERSONA_RESCORE_PENDING = "persona_rescore_pending"
REASON_PERSONA_JUDGE_UNAVAILABLE = "persona_judge_unavailable"
LOG_SLIDE_AUTOFIX_UNSCORED = "autopilot_slide_autofix_unscored"
LOG_FIELD_UNSCORED_SLIDES = "unscored_slides"
LOG_FIELD_JUDGE_UNAVAILABLE = "judge_unavailable"
ESCALATION_UNSCORED_LINE = (
    "- slides {slides}: pass every rule, but the persona judge gave no voice score"
)
ESCALATION_SLIDE_SEPARATOR = ", "
TEXT_PERSONA_JUDGE_UNAVAILABLE = (
    "⚠️ O juiz de voz da persona não respondeu em vários ticks seguidos: os "
    "slides passam nas regras, mas ficaram sem nota de voz. Verifique a fila "
    "de modelos (LLM_MODEL_QUEUE_FAST) e reenvie o carrossel."
)

# The Telegram escalation lists every slide the fix gave up on.
ESCALATION_HEADER = "Autofix could not fix these slides:"
ESCALATION_SLIDE_LINE = (
    '- slide {slide}: {rules}. Current text: "{text}" ({attempts} fix attempts)'
)
ESCALATION_CAROUSEL_LINE = "- carousel: {rules} (no slide fix possible)"
ESCALATION_RULE_SEPARATOR = ", "
ESCALATION_TEXT_MAX_CHARS = 120
ESCALATION_TEXT_ELLIPSIS = "..."
ESCALATION_MAX_SLIDES = 10
