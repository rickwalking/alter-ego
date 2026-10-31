"""Prompt id and first-person voice patterns of the Alter-Ego public chat.

The chat speaks as Pedro, so a reply (or the system prompt that shapes it) must
never describe Pedro in the third person. ``THIRD_PERSON_REPLY_PATTERNS`` are
anchored on Pedro or on the "alter ego / assistant" self-description, so a
normal reply that says "he" about someone else is not flagged.
``THIRD_PERSON_PRONOUN_PATTERNS`` add the bare pronouns and only apply to the
system prompt, which talks about no one but Pedro.
"""

from __future__ import annotations

ALTER_EGO_PROMPT_AGENT = "alter_ego"
ALTER_EGO_PROMPT_VERSION = "v4"
FIRST_PERSON_RULE_HEADING = "SPEAKING AS ME (FIRST PERSON ONLY):"

THIRD_PERSON_REPLY_PATTERNS: tuple[str, ...] = (
    r"\bPedro['\u2019]s\b",
    r"\bPedro\s+(?:is|has|was|does|did|works|worked|likes|thinks|wrote|built|knows)\b",
    r"\b(?:about|for|from|of|ask|asking)\s+Pedro\b",
    r"\b(?:his|her|their)\s+alter[\s-]ego\b",
    r"\balter[\s-]ego\s+(?:dele|do\s+Pedro|of\s+Pedro)\b",
    r"\b(?:assistant|assistente)\s+(?:for|do|de|of)\s+Pedro\b",
    r"\b(?:do|da|sobre\s+o|com\s+o|pro|para\s+o)\s+Pedro\b",
    r"\bo\s+Pedro\s+(?:é|está|tem|foi|fez|faz|usa|usou|acha|trabalha|trabalhou|gosta|pensa|escreveu|sabe)\b",
)
THIRD_PERSON_PRONOUN_PATTERNS: tuple[str, ...] = (
    r"\bhe\b",
    r"\bhis\b",
    r"\bhim\b",
    r"\bele\b",
    r"\bdele\b",
)
