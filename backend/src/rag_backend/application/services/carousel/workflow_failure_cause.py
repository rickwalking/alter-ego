"""The safe cause of a failed workflow run: error class plus a short code.

A pipeline error whose message is already a snake_case code (``persona_score_too_low``,
``en_translation_parse_failed``) keeps it; the few sentence-style error constants map
to a code; any other message (a formatted one, a Pydantic ``ValidationError`` that
echoes its input) becomes ``unclassified``, so no prompt or user content is stored.
"""

from __future__ import annotations

import re

from rag_backend.application.services.carousel.editorial_distribution_blog import (
    ERR_TRANSLATIONS_REQUIRED,
)
from rag_backend.domain.constants.ai_agents import ERR_INVALID_JSON
from rag_backend.domain.constants.artifact_build import (
    ERR_ARTIFACT_STAGING_INCOMPLETE,
)
from rag_backend.domain.constants.workflow_failure import (
    CAUSE_ARTIFACT_STAGING_INCOMPLETE,
    CAUSE_CODE_MAX_CHARS,
    CAUSE_CODE_PATTERN,
    CAUSE_INVALID_JSON,
    CAUSE_SEPARATOR,
    CAUSE_TRANSLATIONS_REQUIRED,
    CAUSE_UNCLASSIFIED,
)

_CODE = re.compile(CAUSE_CODE_PATTERN)
_SENTENCE_CODES: dict[str, str] = {
    ERR_INVALID_JSON: CAUSE_INVALID_JSON,
    ERR_ARTIFACT_STAGING_INCOMPLETE: CAUSE_ARTIFACT_STAGING_INCOMPLETE,
    ERR_TRANSLATIONS_REQUIRED: CAUSE_TRANSLATIONS_REQUIRED,
}


def failure_cause_code(exc: BaseException) -> str:
    """The short safe code of ``exc``; ``unclassified`` when it has none."""
    message = str(exc)
    mapped = _SENTENCE_CODES.get(message)
    if mapped is not None:
        return mapped
    if len(message) > CAUSE_CODE_MAX_CHARS or not _CODE.fullmatch(message):
        return CAUSE_UNCLASSIFIED
    return message


def failure_cause(exc: BaseException) -> str:
    """``<ErrorClass>: <code>`` for the carousel row and the generation run."""
    return f"{type(exc).__name__}{CAUSE_SEPARATOR}{failure_cause_code(exc)}"


__all__ = ["failure_cause", "failure_cause_code"]
