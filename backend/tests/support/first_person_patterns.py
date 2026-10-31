"""Third-person patterns of the Alter-Ego first-person voice oracle.

The chat speaks as Pedro, so a reply (or the system prompt that shapes it) must
never describe Pedro in the third person. ``THIRD_PERSON_REPLY_PATTERNS`` are
anchored on Pedro, on the "alter ego / assistant" self-description, or on a
reply that opens with a third-person pronoun, so a reply that says "he" about a
named someone else later on is not flagged. ``THIRD_PERSON_PRONOUN_PATTERNS``
add the bare pronouns and only apply to the system prompt, which describes no
one but Pedro.
"""

from __future__ import annotations

PEDRO_NAME = r"Pedro(?:\s+Marins)?"
NEXT_WORD = r"\s+(?!Marins\b)[^\W\d_]+"

THIRD_PERSON_REPLY_PATTERNS: tuple[str, ...] = (
    r"\bPedro['\u2019]s\b",
    rf"(?:^|[.!?:;]\s+){PEDRO_NAME}{NEXT_WORD}",
    rf"\b{PEDRO_NAME}\s+(?:is|has|was|does|did|uses|used|builds|built|leads|led"
    r"|works|worked|likes|thinks|wrote|writes|knows|é|está|tem|foi|usa|faz)\b",
    rf"(?<!sou\s)\bo\s+{PEDRO_NAME}{NEXT_WORD}",
    r"\b(?:about|for|from|of|ask|asking)\s+Pedro\b",
    r"\b(?:his|her|their)\s+(?:alter[\s-]ego|assistant)\b",
    r"\b(?:alter[\s-]ego|assistant|assistente)\s+(?:dele|do\s+Pedro|of\s+Pedro)\b",
    r"\b(?:assistant|assistente)\s+(?:for|do|de)\s+Pedro\b",
    r"\b(?:do|da|sobre\s+o|com\s+o|pro|para\s+o)\s+Pedro\b",
    r"^\W*(?:he|ele)\b",
)
THIRD_PERSON_PRONOUN_PATTERNS: tuple[str, ...] = (
    r"\bhe\b",
    r"\bhis\b",
    r"\bhim\b",
    r"\bele\b",
    r"\bdele\b",
)
