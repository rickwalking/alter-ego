"""Pure text detectors for the copy-hygiene rules.

Prod carousel 98a2e2f0 (2026-10-16) showed what a model can leave in visible
slide copy: a ```` ```json ```` fenced bilingual object (slide 3), an HTML tag
(slide 3 again) and a Markdown heading (``## Checklist
para salvar``, slide 8 PT). Each detector answers one question about one text
and returns a short detail ("" when the text is clean). The detectors stay
tolerant of legitimate copy: the pipeline's emphasis (``**bold**`` in PT,
balanced ``<strong>`` in EN), proper nouns, numbers and first-person
Portuguese are never flagged.

No I/O, no policy: ``presentation_copy_rules`` decides which rules are active.

EMPHASIS_TAG_PATTERN matches <strong>, the EN emphasis format whose balance
emphasis_markup_invalid checks; every other tag is a leak. The placeholder-marker match
is case-sensitive because the lowercase word is Portuguese ("o dia todo").
DOUBLED_WORD_ALLOWLIST holds grammatical doubles ("what it had had", "the fact that
that"). An item title never ends on a _TITLE_CONNECTORS word (as in "Comece com dois
ou"), and a finished sentence never ends on a _DANGLING_CONNECTORS word (as in "isso
muda tudo e.").
"""

from __future__ import annotations

import re

from rag_backend.application.services.carousel.draft_blob_text import (
    looks_like_object,
)
from rag_backend.application.services.carousel.owner_autofix_text import (
    looks_portuguese,
)
from rag_backend.domain.constants.carousel_autofix import (
    ENGLISH_MARKERS,
    PORTUGUESE_MARKERS,
)
from rag_backend.domain.constants.carousel_presentation import (
    MIN_LANGUAGE_CHECK_WORDS,
    MIN_REPEATED_SENTENCE_WORDS,
    MIN_WRONG_LANGUAGE_MARKERS,
)

BOLD_MARK = "**"
EMPTY_BOLD = "****"
CODE_FENCE = "```"
BACKTICK = "`"
LITERAL_ESCAPES: tuple[str, ...] = ("\\n", '\\"', "\\t")
ELLIPSIS_MARKS: tuple[str, ...] = ("...", "…")

HTML_TAG_PATTERN = re.compile(r"</?\s*[A-Za-z][A-Za-z0-9]*(?:\s[^<>]*)?/?>")
EMPHASIS_TAG_PATTERN = re.compile(r"<\s*/?\s*strong\s*>", flags=re.IGNORECASE)
_EMPTY_STRONG_PATTERN = re.compile(r"<strong>\s*</strong>", flags=re.IGNORECASE)
MARKDOWN_HEADING_PATTERN = re.compile(r"(?m)^[ \t]{0,3}#{1,6}[ \t]+")
_KEY_LEAK_PATTERN = re.compile(
    r"[\"']\s*(?:heading|body|title|pt|en|presentation_pt|presentation_en"
    r"|draft_text|slide_index)\s*[\"']\s*:",
    flags=re.IGNORECASE,
)
_LIST_PATTERN = re.compile(r"(?m)^[ \t]*(?:[-*+•]|\d{1,2}[.)])[ \t]+\S")
_TABLE_PATTERN = re.compile(r"(?m)^[ \t]*\|.*\|[ \t]*$|\|[ \t]*:?-{3,}")
_CHATTER_START_PATTERN = re.compile(
    r"^\W*(?:here(?:'s|\s+is|\s+are)\s+(?:the\s+|your\s+|a\s+|an\s+)?"
    r"(?:slide|revised|updated|rewritten|corrected|fixed|json|copy|text|version"
    r"|translation|draft)|sure[,!]|certainly[,!]|of course[,!]|claro[!,]"
    r"|com certeza[!,]|aqui (?:est[áa]|v[aã]o|segue)\s+(?:o|a|os|as)\s+"
    r"(?:slide|texto|vers[ãa]o|tradu[çc][ãa]o|json|copy|conte[úu]do|rascunho)"
    r"|(?:assistant|assistente|ai|ia)\s*:)",
    flags=re.IGNORECASE,
)
_CHATTER_ANYWHERE_PATTERN = re.compile(
    r"\bas an ai\b|\bcomo (?:uma )?ia\b,|(?:^|\n|\()\s*(?:note|nota|obs)\s*:"
    r"|\bword count\b|\bcontagem de palavras\b"
    r"|\(\s*\d+\s*(?:characters|caracteres|palavras|words)\s*\)"
    r"|\bi hope this helps\b|\blet me know\b|\bespero que (?:isso|isto) ajude\b",
    flags=re.IGNORECASE,
)
_PLACEHOLDER_PATTERN = re.compile(
    r"\[\s*(?:insert|inserir|insira|adicione|add|placeholder|tbd|todo|xxx"
    r"|\.\.\.|…)[^\]]*\]|\{\{?\s*[A-Za-z_][A-Za-z0-9_]*\s*\}?\}"
    r"|\blorem ipsum\b|\(\s*(?:\.\.\.|…)\s*\)",
    flags=re.IGNORECASE,
)
_PLACEHOLDER_MARKER_PATTERN = re.compile(r"\b(?:TODO|TBD|FIXME|XXX)\b")
_STUB_PATTERN = re.compile(r"^\W*(?:\.\.\.|…)\W*$")
MOJIBAKE_PATTERN = re.compile(r"Ã[^\x00-\x7f]|Â[^\x00-\x7f]|â€|\ufffd")
CONTROL_CHAR_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
_WORD_PATTERN = re.compile(r"[^\W_]+(?:['\u2019][^\W_]+)?")
_LETTER_WORD_PATTERN = re.compile(r"[^\W\d_]+")
DOUBLED_WORD_PATTERN = re.compile(
    r"(?<![\w])([^\W\d_]+)(\s+)\1(?![\w])", flags=re.IGNORECASE
)
DOUBLED_WORD_ALLOWLIST: frozenset[str] = frozenset({"had", "that"})
_SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+|\n+")
_TITLE_CONNECTORS: frozenset[str] = frozenset({
    "ou",
    "e",
    "de",
    "com",
    "or",
    "and",
    "of",
    "with",
})
_TERMINAL_PUNCTUATION = ".!?"
_TRAILING_CLOSERS = "\"'\u201d\u2019\u00bb)]*"
_DANGLING_PUNCTUATION = ",:;-\u2013\u2014("
_DANGLING_CONNECTORS: frozenset[str] = frozenset({
    "e",
    "ou",
    "mas",
    "de",
    "da",
    "do",
    "dos",
    "das",
    "com",
    "the",
    "and",
    "or",
    "but",
    "an",
})


def plain_text(text: str) -> str:
    """The text without HTML tags or ``**`` marks, whitespace collapsed."""
    without_tags = HTML_TAG_PATTERN.sub("", text).replace(BOLD_MARK, "")
    return " ".join(without_tags.split())


def word_count(text: str) -> int:
    """Words (numbers included) in the visible text."""
    return len(_WORD_PATTERN.findall(plain_text(text)))


def structured_payload_detail(text: str) -> str:
    """A code fence, a JSON/dict object, or a leaked copy key."""
    if CODE_FENCE in text:
        return "code fence"
    if looks_like_object(text) or text.lstrip().startswith("[{"):
        return "JSON object"
    match = _KEY_LEAK_PATTERN.search(text)
    return f"leaked key {match.group(0)}" if match else ""


_MARKUP_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (MARKDOWN_HEADING_PATTERN, "Markdown heading (#)"),
    (_LIST_PATTERN, "Markdown list syntax"),
    (_TABLE_PATTERN, "Markdown table syntax"),
)


def markup_leak_detail(text: str) -> str:
    """HTML (other than ``<strong>``), Markdown, backticks or literal escapes."""
    tag = next(
        (
            match.group(0)
            for match in HTML_TAG_PATTERN.finditer(text)
            if not EMPHASIS_TAG_PATTERN.fullmatch(match.group(0))
        ),
        "",
    )
    if tag:
        return f"HTML tag {tag}"
    found = next(
        (detail for pattern, detail in _MARKUP_PATTERNS if pattern.search(text)), ""
    )
    if found:
        return found
    if BACKTICK in text:
        return "inline code backticks"
    escape = next((item for item in LITERAL_ESCAPES if item in text), "")
    return f"literal {escape}" if escape else ""


def emphasis_unbalanced_detail(text: str) -> str:
    """An empty ``****`` or an odd number of ``**`` marks."""
    if EMPTY_BOLD in text or _EMPTY_STRONG_PATTERN.search(text):
        return "empty emphasis"
    if text.count(BOLD_MARK) % 2 == 1:
        return "odd number of **"
    return ""


def emphasis_locale_detail(text: str, *, portuguese: bool) -> str:
    """Emphasis written with the OTHER locale's markup.

    The convention: PT copy marks emphasis ``**…**``, EN copy
    ``<strong>…</strong>``. PT copy carrying a ``<strong>`` tag, or EN copy
    carrying ``**``, is a locale mismatch the write-time normalizer fixes.
    """
    if portuguese:
        return "uses <strong> emphasis" if EMPHASIS_TAG_PATTERN.search(text) else ""
    return "uses ** emphasis" if BOLD_MARK in text else ""


def assistant_chatter_detail(text: str) -> str:
    """A chat preamble or a meta note about the task."""
    match = _CHATTER_START_PATTERN.search(text) or _CHATTER_ANYWHERE_PATTERN.search(
        text
    )
    return f'"{match.group(0).strip()}"' if match else ""


def placeholder_detail(text: str) -> str:
    """A template placeholder, a to-do marker, lorem ipsum, or an ellipsis stub."""
    match = _PLACEHOLDER_PATTERN.search(text) or _PLACEHOLDER_MARKER_PATTERN.search(
        text
    )
    if match:
        return f'"{match.group(0)}"'
    return "ellipsis stub" if _STUB_PATTERN.match(text) else ""


def encoding_detail(text: str) -> str:
    """Mojibake, the U+FFFD replacement character, or a control character."""
    match = MOJIBAKE_PATTERN.search(text)
    if match:
        return f"mojibake {match.group(0)!r}"
    return "control character" if CONTROL_CHAR_PATTERN.search(text) else ""


def _open_ending(plain: str) -> str:
    if plain.endswith(ELLIPSIS_MARKS):
        return "ends with an ellipsis"
    if plain[-1] in _DANGLING_PUNCTUATION:
        return f'ends with "{plain[-1]}"'
    return ""


def truncation_detail(text: str) -> str:
    """The body stops mid-sentence (no closing ``.!?`` or a dangling ending)."""
    plain = plain_text(text)
    if not plain:
        return ""
    open_ending = _open_ending(plain)
    if open_ending:
        return open_ending
    closed = plain.rstrip(_TRAILING_CLOSERS)
    if not closed or closed[-1] not in _TERMINAL_PUNCTUATION:
        return "no closing punctuation"
    words = _LETTER_WORD_PATTERN.findall(closed.casefold())
    if words and words[-1] in _DANGLING_CONNECTORS:
        return f'ends on "{words[-1]}"'
    return ""


def open_ending_detail(text: str) -> str:
    """An ellipsis or a dangling ``,:;-`` at the end of the copy, else empty."""
    plain = plain_text(text)
    return _open_ending(plain) if plain else ""


def wrong_language_detail(text: str, *, portuguese: bool) -> str:
    """Copy that reads as the other language (stopword markers).

    EN copy is also flagged when the autofix would call it Portuguese
    (``looks_portuguese``: one marker plus an accented letter in 3+ words).
    The validator used to need 4+ words and 2+ markers, so short Portuguese
    EN headings ("Agentes de código mudam o review") passed unflagged while
    the autofix treated them as untranslated.
    """
    if not portuguese and looks_portuguese(text):
        return "reads as Portuguese"
    words = _LETTER_WORD_PATTERN.findall(plain_text(text).casefold())
    if len(words) < MIN_LANGUAGE_CHECK_WORDS:
        return ""
    own, other = (
        (PORTUGUESE_MARKERS, ENGLISH_MARKERS)
        if portuguese
        else (ENGLISH_MARKERS, PORTUGUESE_MARKERS)
    )
    own_hits = sum(1 for word in words if word in own)
    other_hits = sum(1 for word in words if word in other)
    if other_hits >= MIN_WRONG_LANGUAGE_MARKERS and other_hits > own_hits:
        return "reads as English" if portuguese else "reads as Portuguese"
    return ""


def doubled_word_detail(text: str) -> str:
    """A word written twice in a row ("o o", "the the")."""
    for match in DOUBLED_WORD_PATTERN.finditer(plain_text(text)):
        if match.group(1).casefold() not in DOUBLED_WORD_ALLOWLIST:
            return f'doubled word "{match.group(1)}"'
    return ""


def ends_on_connector(text: str) -> bool:
    """True when the text's last word is a connector ("ou", "and", "with")."""
    words = _LETTER_WORD_PATTERN.findall(plain_text(text).casefold())
    return bool(words) and words[-1] in _TITLE_CONNECTORS


def item_split_detail(text: str) -> str:
    """An item title cut mid-phrase: it ends on a connector word."""
    if not ends_on_connector(text):
        return ""
    words = _LETTER_WORD_PATTERN.findall(plain_text(text).casefold())
    return f'title ends on "{words[-1]}"'


def sentence_keys(text: str) -> list[str]:
    """Normalized sentences long enough to count as a repeat."""
    keys: list[str] = []
    for sentence in _SENTENCE_SPLIT_PATTERN.split(plain_text(text)):
        words = _WORD_PATTERN.findall(sentence.casefold())
        if len(words) >= MIN_REPEATED_SENTENCE_WORDS:
            keys.append(" ".join(words))
    return keys


__all__ = [
    "BACKTICK",
    "BOLD_MARK",
    "CODE_FENCE",
    "CONTROL_CHAR_PATTERN",
    "DOUBLED_WORD_ALLOWLIST",
    "DOUBLED_WORD_PATTERN",
    "ELLIPSIS_MARKS",
    "EMPHASIS_TAG_PATTERN",
    "EMPTY_BOLD",
    "HTML_TAG_PATTERN",
    "LITERAL_ESCAPES",
    "MARKDOWN_HEADING_PATTERN",
    "MOJIBAKE_PATTERN",
    "assistant_chatter_detail",
    "doubled_word_detail",
    "emphasis_locale_detail",
    "emphasis_unbalanced_detail",
    "encoding_detail",
    "ends_on_connector",
    "item_split_detail",
    "markup_leak_detail",
    "open_ending_detail",
    "placeholder_detail",
    "plain_text",
    "sentence_keys",
    "structured_payload_detail",
    "truncation_detail",
    "word_count",
    "wrong_language_detail",
]
