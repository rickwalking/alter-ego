"""The reply a chat agent gives when it runs out of steps before answering."""

import re

from rag_backend.domain.constants.chat_stream import (
    NO_KNOWLEDGE_REPLY_EN,
    NO_KNOWLEDGE_REPLY_PT,
)

_PORTUGUESE_LETTERS = re.compile(r"[ãõç]", re.IGNORECASE)
_PORTUGUESE_WORDS = frozenset({
    "é",
    "está",
    "você",
    "voce",
    "não",
    "nao",
    "olá",
    "ola",
    "oi",
    "quem",
    "qual",
    "como",
    "onde",
    "quando",
    "porque",
    "obrigado",
    "obrigada",
    "tudo",
    "bem",
    "seu",
    "sua",
    "sobre",
    "tem",
    "trabalho",
})
_WORD = re.compile(r"\w+", re.UNICODE)


def looks_portuguese(message: str) -> bool:
    """Whether ``message`` reads as Portuguese (ã/õ/ç or common Portuguese words).

    Other accents alone ("résumé", "café", "Pokémon") do not count.
    """
    if _PORTUGUESE_LETTERS.search(message):
        return True
    words = {word.lower() for word in _WORD.findall(message)}
    return not words.isdisjoint(_PORTUGUESE_WORDS)


def no_knowledge_reply(message: str) -> str:
    """An honest "not in my knowledge yet" reply in the visitor's language."""
    if looks_portuguese(message):
        return NO_KNOWLEDGE_REPLY_PT
    return NO_KNOWLEDGE_REPLY_EN
