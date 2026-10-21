"""Voice / AI-cliché data for the blog quality gate (ADR-0025).

The banned stock phrases are *data*: the deterministic scan reports every one it
finds in a generated section, and a finding sends the article to the single
rewrite pass. Phrases are matched case-insensitively on word boundaries, so add
them in lowercase. PT phrases gate the canonical document; EN phrases gate
``translations.en``.

An article scoring below the voice threshold gets exactly one rewrite. Sentences shorter
than the repeated-sentence minimum are not reported, since short connective lines ("Mas
não é só isso.") recur legitimately in human text, and short long-form notes are not
checked for verbatim copies. A PT section reads as English when it has at least
``ENGLISH_MIN_HITS`` English function words that also outnumber its Portuguese ones
``ENGLISH_DOMINANCE`` to 1. Each section gets a distinct narrative role in reading
order: the first is always the lede, the last always the close, and the middle cycles
through the argument roles.
"""

from typing import Final

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

REPEATED_SENTENCE_MIN_CHARS: Final = 40

VERBATIM_NOTE_MIN_CHARS: Final = 60

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
