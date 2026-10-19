"""The autopilot slide-fix settings (AE-0401, AE-0407, AE-0433).

A mixin of ``Settings``, split out to keep ``settings.py`` under 400 lines;
the fields and environment variables are unchanged.
"""

from __future__ import annotations

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings

from rag_backend.domain.constants.slide_fix import (
    AUTOFIX_ESCALATION_ATTEMPTS,
    AUTOFIX_MODEL_ATTEMPTS,
    PERSONA_UNSCORED_MAX_TICKS,
)


class AutopilotAutofixSettings(BaseSettings):
    """How hard the autopilot slide fix tries before it escalates."""

    # AE-0401: model attempts per failing slide in the autopilot autofix loop
    # (then the run escalates; the loop never spends a revise).
    autopilot_autofix_attempts: int = Field(
        default=AUTOFIX_MODEL_ATTEMPTS,
        ge=1,
        validation_alias=AliasChoices(
            "AUTOPILOT_AUTOFIX_ATTEMPTS",
            "autopilot_autofix_attempts",
        ),
    )

    # AE-0407: then up to this many attempts on the reasoning model before
    # the run escalates to the owner (0 turns the escalation off).
    autopilot_autofix_escalation_attempts: int = Field(
        default=AUTOFIX_ESCALATION_ATTEMPTS,
        ge=0,
        validation_alias=AliasChoices(
            "AUTOPILOT_AUTOFIX_ESCALATION_ATTEMPTS",
            "autopilot_autofix_escalation_attempts",
        ),
    )

    # AE-0433: ticks a fixed slide may stay unscored (persona judge down)
    # before the run escalates "persona_judge_unavailable".
    autopilot_persona_unscored_max_ticks: int = Field(
        default=PERSONA_UNSCORED_MAX_TICKS,
        ge=1,
        validation_alias=AliasChoices(
            "AUTOPILOT_PERSONA_UNSCORED_MAX_TICKS",
            "autopilot_persona_unscored_max_ticks",
        ),
    )


__all__ = ["AutopilotAutofixSettings"]
