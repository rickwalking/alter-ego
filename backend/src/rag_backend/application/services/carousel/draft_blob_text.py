"""Read a slide draft that the model wrote as a JSON object (AE-0400).

Models sometimes answer a slide draft with its bilingual JSON object instead
of the copy, and sometimes wrap it in a Markdown code fence (```` ```json ````).
Prod 2026-10-16 (carousel 98a2e2f0, slide 3): the fenced object was not
recognised, so the raw JSON became the slide's visible copy.
"""

from __future__ import annotations

import ast
import json
import re

_CODE_FENCE = re.compile(
    r"^```[A-Za-z0-9_-]*[ \t]*\n?(?P<body>.*?)\n?```$", flags=re.DOTALL
)
_OBJECT_START = "{"


def strip_code_fence(text: str) -> str:
    """The text inside a Markdown code fence, or the stripped text unchanged."""
    stripped = text.strip()
    match = _CODE_FENCE.match(stripped)
    return match.group("body").strip() if match else stripped


def looks_like_object(text: str) -> bool:
    """True when the (possibly fenced) text is a JSON/Python object literal."""
    return strip_code_fence(text).startswith(_OBJECT_START)


def parse_object_text(text: str) -> dict[str, object] | None:
    """Parse a (possibly fenced) JSON or Python dict literal; None otherwise."""
    body = strip_code_fence(text)
    if not body.startswith(_OBJECT_START):
        return None
    try:
        parsed: object = json.loads(body)
    except ValueError:
        try:
            parsed = ast.literal_eval(body)
        except (SyntaxError, ValueError):
            return None
    return dict(parsed) if isinstance(parsed, dict) else None


__all__ = ["looks_like_object", "parse_object_text", "strip_code_fence"]
