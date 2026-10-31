"""Deterministic first-person voice check for the Alter-Ego chat.

Finds third-person references to Pedro in a chat reply or in the chat system
prompt. It is the recorded judge of the first-person eval: no model call, only
the patterns in ``domain.constants.alter_ego_voice``.
"""

from __future__ import annotations

import re

from rag_backend.domain.constants.alter_ego_voice import (
    FIRST_PERSON_RULE_HEADING,
    THIRD_PERSON_PRONOUN_PATTERNS,
    THIRD_PERSON_REPLY_PATTERNS,
)

_REPLY_REGEXES = tuple(
    re.compile(pattern, re.IGNORECASE) for pattern in THIRD_PERSON_REPLY_PATTERNS
)
_PROMPT_REGEXES = _REPLY_REGEXES + tuple(
    re.compile(pattern, re.IGNORECASE) for pattern in THIRD_PERSON_PRONOUN_PATTERNS
)


def _findings(text: str, regexes: tuple[re.Pattern[str], ...]) -> list[str]:
    """Return every matched third-person phrase, in pattern order."""
    return [match.group(0) for regex in regexes for match in regex.finditer(text)]


def third_person_reply_findings(reply: str) -> list[str]:
    """Return the third-person references to Pedro found in a chat reply."""
    return _findings(reply, _REPLY_REGEXES)


def is_first_person_reply(reply: str) -> bool:
    """Tell whether a chat reply speaks as Pedro, never about him."""
    return not third_person_reply_findings(reply)


def strip_first_person_rule(prompt: str) -> str:
    """Drop the first-person rule section, the only place forbidden phrases are quoted.

    The section runs from ``FIRST_PERSON_RULE_HEADING`` to the next blank line.
    A prompt without the heading is returned unchanged.
    """
    start = prompt.find(FIRST_PERSON_RULE_HEADING)
    if start < 0:
        return prompt
    end = prompt.find("\n\n", start)
    tail = "" if end < 0 else prompt[end:]
    return prompt[:start] + tail


def third_person_prompt_findings(prompt: str) -> list[str]:
    """Return third-person references to Pedro in a system prompt.

    The first-person rule section is skipped, and bare pronouns count too,
    because the prompt describes no one but Pedro.
    """
    return _findings(strip_first_person_rule(prompt), _PROMPT_REGEXES)
