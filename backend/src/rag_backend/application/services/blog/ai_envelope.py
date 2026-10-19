"""Strict parsing of the ``ai-suggest`` model answer (AE-0424, F-10).

The model is asked for ``{"suggested_text", "explanation"}`` but answers in
three shapes: the clean JSON, the same JSON inside a ```json fence, or a JSON
whose ``suggested_text`` is itself an (optionally fenced) envelope. All three
become plain text here; anything that is not an envelope degrades to the raw
text. The caller never shows a fenced blob in a user field.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from rag_backend.domain.constants.blog_editor import (
    CODE_FENCE,
    SUGGEST_KEY_EXPLANATION,
    SUGGEST_KEY_TEXT,
)

_FENCED_BLOCK = re.compile(r"```[A-Za-z]*[ \t]*\n?(.*?)```", re.DOTALL)


@dataclass(frozen=True)
class SuggestionText:
    """The plain suggestion; ``explanation`` is ``None`` when it was no envelope."""

    text: str
    explanation: str | None


def strip_code_fence(raw: str) -> str:
    """Drop a surrounding ```lang ... ``` fence; other text is returned stripped."""
    text = raw.strip()
    if not (text.startswith(CODE_FENCE) and text.endswith(CODE_FENCE)):
        return text
    inner = text[len(CODE_FENCE) : -len(CODE_FENCE)]
    first_line, _, rest = inner.partition("\n")
    body = rest if first_line.strip().isalpha() or not first_line.strip() else inner
    return body.strip()


def _as_envelope(candidate: str) -> dict[str, object] | None:
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict) or SUGGEST_KEY_TEXT not in data:
        return None
    return data


def _candidates(raw: str) -> list[str]:
    """The whole answer, every fenced block, then the outermost ``{...}``.

    Models often write a line of prose before the fenced JSON; the envelope is
    still found so the raw blob never reaches the user (AE-0424 review).
    """
    found = [strip_code_fence(raw)]
    found.extend(match.group(1).strip() for match in _FENCED_BLOCK.finditer(raw))
    start, end = raw.find("{"), raw.rfind("}")
    if 0 <= start < end:
        found.append(raw[start : end + 1])
    return found


def _envelope(raw: str) -> dict[str, object] | None:
    for candidate in _candidates(raw):
        data = _as_envelope(candidate)
        if data is not None:
            return data
    return None


def _explanation(data: dict[str, object]) -> str:
    value = data.get(SUGGEST_KEY_EXPLANATION)
    return "" if value is None else str(value)


def parse_suggestion(raw: str) -> SuggestionText:
    """Plain suggestion text from the model answer (unwraps one nested envelope)."""
    data = _envelope(raw)
    if data is None:
        return SuggestionText(strip_code_fence(raw), None)
    text = str(data.get(SUGGEST_KEY_TEXT) or "")
    explanation = _explanation(data)
    inner = _envelope(text)
    if inner is not None:
        text = str(inner.get(SUGGEST_KEY_TEXT) or "")
        explanation = _explanation(inner) or explanation
    return SuggestionText(strip_code_fence(text), explanation)


__all__ = ["SuggestionText", "parse_suggestion", "strip_code_fence"]
