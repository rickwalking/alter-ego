"""Request/response schemas of ``POST /carousels/cover-prompt-ideas``.

Only the carousel topic and the slide palette are accepted: only the topic and
the palette reach the model. The palette colours reuse the
catalog's strict ``#rrggbb`` allow-list and its name rule, so no free text other
than the topic and a short palette name reaches the prompt.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from rag_backend.api.schemas.palette import normalise_hex, normalise_name
from rag_backend.domain.constants.cover_prompt_ideas import (
    ERR_TOPIC_TOO_SHORT,
    TOPIC_MAX_LEN,
    TOPIC_MIN_LEN,
    IdeaLocale,
)
from rag_backend.domain.constants.palette_catalog import NAME_MAX_LEN, NAME_MIN_LEN
from rag_backend.domain.constants.palette_types import PaletteMode


class CoverIdeasPaletteRequest(BaseModel):
    """The slide palette the ideas should suit."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=NAME_MIN_LEN, max_length=NAME_MAX_LEN)
    mode: PaletteMode
    background: str
    primary: str
    accent: str

    @field_validator("name")
    @classmethod
    def _check_name(cls, value: str) -> str:
        return normalise_name(value)

    @field_validator("background", "primary", "accent")
    @classmethod
    def _check_hex(cls, value: str) -> str:
        return normalise_hex(value)


class CoverPromptIdeasRequest(BaseModel):
    """The carousel topic, its palette (none for "auto") and the UI language."""

    model_config = ConfigDict(extra="forbid")

    topic: str = Field(..., min_length=TOPIC_MIN_LEN, max_length=TOPIC_MAX_LEN)
    palette: CoverIdeasPaletteRequest | None = None
    locale: IdeaLocale = IdeaLocale.PT

    @field_validator("topic")
    @classmethod
    def _check_topic(cls, value: str) -> str:
        stripped = value.strip()
        if len(stripped) < TOPIC_MIN_LEN:
            raise ValueError(ERR_TOPIC_TOO_SHORT)
        return stripped


class CoverPromptIdeasResponse(BaseModel):
    """Three to six prompt ideas for a new cover photo (nothing is stored)."""

    ideas: list[str]


__all__ = [
    "CoverIdeasPaletteRequest",
    "CoverPromptIdeasRequest",
    "CoverPromptIdeasResponse",
]
