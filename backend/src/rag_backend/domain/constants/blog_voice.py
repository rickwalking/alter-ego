"""Voice / AI-cliché data for the blog quality gate (AE-0425, ADR-0025).

The banned stock phrases are *data*: the deterministic scan reports every one it
finds in a generated section, and a finding sends the article to the single
rewrite pass. Phrases are matched case-insensitively on word boundaries, so add
them in lowercase. PT phrases gate the canonical document; EN phrases gate
``translations.en``.
"""

from typing import Final

# ADR-0003's voice bar: an article scoring below it gets exactly one rewrite.
VOICE_SCORE_THRESHOLD: Final = 70.0
MAX_REWRITE_PASSES: Final = 1

BANNED_PHRASES_PT: Final[tuple[str, ...]] = (
    "no mundo de hoje",
    "nos dias de hoje",
    "é importante ressaltar",
    "é importante destacar",
    "vale ressaltar",
    "vale destacar",
    "em resumo",
    "em suma",
    "neste artigo",
    "neste post",
    "sem dúvida alguma",
    "cada vez mais",
    "mergulhar fundo",
    "no cenário atual",
    "revolucionar a forma",
    "uma verdadeira revolução",
    "não é exagero dizer",
    "em um mundo cada vez mais",
)

BANNED_PHRASES_EN: Final[tuple[str, ...]] = (
    "in today's world",
    "in today's fast-paced",
    "it is important to note",
    "it's important to note",
    "in conclusion",
    "in summary",
    "in this article",
    "dive deep",
    "delve into",
    "game-changer",
    "revolutionize the way",
    "ever-evolving landscape",
    "at the end of the day",
)

# A sentence shorter than this (characters, after normalization) is not
# reported as repeated: short connective lines ("Mas não é só isso.") recur
# legitimately in a human text.
REPEATED_SENTENCE_MIN_CHARS: Final = 40

# A long-form note shorter than this is not checked for a verbatim copy.
VERBATIM_NOTE_MIN_CHARS: Final = 60

# Cheap language check of a PT section (F-05 beyond verbatim copies): a
# section with at least ENGLISH_MIN_HITS English function words that also
# outnumber its Portuguese ones ENGLISH_DOMINANCE to 1 reads as English.
ENGLISH_FUNCTION_WORDS: Final[frozenset[str]] = frozenset({
    "the",
    "and",
    "of",
    "to",
    "is",
    "are",
    "that",
    "this",
    "with",
    "for",
    "it",
    "was",
    "be",
    "have",
    "has",
    "which",
    "from",
    "they",
    "their",
    "will",
})
PORTUGUESE_FUNCTION_WORDS: Final[frozenset[str]] = frozenset({
    "de",
    "que",
    "não",
    "uma",
    "um",
    "para",
    "com",
    "é",
    "os",
    "as",
    "do",
    "da",
    "em",
    "no",
    "na",
    "mais",
    "mas",
    "eu",
    "isso",
    "por",
})
ENGLISH_MIN_HITS: Final = 8
ENGLISH_DOMINANCE: Final = 2

# Distinct narrative role of each section, in reading order. The writer gets one
# role per section (``narrative_roles``): the first is always the lede and the
# last always the close, the middle cycles through the argument roles.
ROLE_LEDE: Final = "lede"
ROLE_CLOSE: Final = "close"
MIDDLE_ROLES: Final[tuple[str, ...]] = (
    "context",
    "thesis",
    "evidence",
    "example",
    "counterpoint",
    "practice",
    "implication",
    "risk",
    "lesson",
)

__all__ = [
    "BANNED_PHRASES_EN",
    "BANNED_PHRASES_PT",
    "ENGLISH_DOMINANCE",
    "ENGLISH_FUNCTION_WORDS",
    "ENGLISH_MIN_HITS",
    "MAX_REWRITE_PASSES",
    "MIDDLE_ROLES",
    "PORTUGUESE_FUNCTION_WORDS",
    "REPEATED_SENTENCE_MIN_CHARS",
    "ROLE_CLOSE",
    "ROLE_LEDE",
    "VERBATIM_NOTE_MIN_CHARS",
    "VOICE_SCORE_THRESHOLD",
]
