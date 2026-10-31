"""Deterministic first-person voice oracle for the Alter-Ego chat eval.

Finds third-person references to Pedro in a chat reply or in the chat system
prompt. It is the recorded judge of the first-person eval: no model call, only
the patterns in ``tests.support.first_person_patterns``. In the prompt, only
the exact lines that quote the forbidden phrases as forbidden are skipped, so a
new third-person line anywhere else, the rule section included, is caught.
"""

from __future__ import annotations

import re

from tests.support.first_person_patterns import (
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


def strip_lines(prompt: str, lines: tuple[str, ...]) -> str:
    """Remove each exact line from the prompt; fail if one is missing."""
    kept = prompt.splitlines()
    for line in lines:
        if line not in kept:
            raise ValueError(line)
        kept.remove(line)
    return "\n".join(kept)


def third_person_prompt_findings(
    prompt: str, quoted_lines: tuple[str, ...]
) -> list[str]:
    """Return third-person references to Pedro in a system prompt.

    ``quoted_lines`` are the exact rule lines that quote forbidden phrases;
    every other line is scanned, bare pronouns included, because the prompt
    describes no one but Pedro.
    """
    scanned = strip_lines(prompt, quoted_lines)
    return [
        hit for line in scanned.splitlines() for hit in _findings(line, _PROMPT_REGEXES)
    ]
