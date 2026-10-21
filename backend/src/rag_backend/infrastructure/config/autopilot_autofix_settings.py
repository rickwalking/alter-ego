"""The autopilot slide-fix settings.

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

    autopilot_autofix_attempts: int = Field(
        default=AUTOFIX_MODEL_ATTEMPTS,
        ge=1,
        validation_alias=AliasChoices(
            "AUTOPILOT_AUTOFIX_ATTEMPTS",
            "autopilot_autofix_attempts",
        ),
    )

    autopilot_autofix_escalation_attempts: int = Field(
        default=AUTOFIX_ESCALATION_ATTEMPTS,
        ge=0,
        validation_alias=AliasChoices(
            "AUTOPILOT_AUTOFIX_ESCALATION_ATTEMPTS",
            "autopilot_autofix_escalation_attempts",
        ),
    )

    autopilot_persona_unscored_max_ticks: int = Field(
        default=PERSONA_UNSCORED_MAX_TICKS,
        ge=1,
        validation_alias=AliasChoices(
            "AUTOPILOT_PERSONA_UNSCORED_MAX_TICKS",
            "autopilot_persona_unscored_max_ticks",
        ),
    )


__all__ = ["AutopilotAutofixSettings"]
