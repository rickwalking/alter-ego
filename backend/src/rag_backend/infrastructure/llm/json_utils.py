"""JSON parsing utilities for LLM response extraction."""

from __future__ import annotations

import json
import re
from typing import cast

from rag_backend.domain.protocols import LLMService
from rag_backend.infrastructure.logging import get_logger

logger = get_logger()

_ERR_JSON_NOT_FOUND = "No valid JSON object found"

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)

_JSON_REPAIR_PROMPT = (
    "Your previous response contained invalid JSON. "
    "Please return ONLY the corrected JSON object, with no additional text, "
    "no markdown fences, and no explanations."
)


def _strip_trailing_commas(text: str) -> str:
    return re.sub(r",(\s*[}\]])", r"\1", text)


def _find_json_object(text: str) -> str | None:
    depth = 0
    start = None
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                return text[start : i + 1]
    return None


def extract_json(raw: str) -> object:
    """Parse JSON from raw LLM output, including markdown-fenced payloads."""
    candidate = raw.strip()

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    for match in _JSON_FENCE_RE.finditer(candidate):
        block = match.group(1).strip()
        try:
            return json.loads(block)
        except json.JSONDecodeError:
            pass

    obj_text = _find_json_object(candidate)
    if obj_text:
        try:
            return json.loads(obj_text)
        except json.JSONDecodeError:
            pass
        cleaned = _strip_trailing_commas(obj_text)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

    first = candidate.find("{")
    last = candidate.rfind("}")
    if first != -1 and last != -1 and last > first:
        snippet = _strip_trailing_commas(candidate[first : last + 1])
        try:
            return json.loads(snippet)
        except json.JSONDecodeError:
            pass

    raise json.JSONDecodeError(_ERR_JSON_NOT_FOUND, raw, 0)


async def extract_json_with_repair(
    raw: str,
    *,
    llm: LLMService,
    project_id: str,
) -> dict[str, object]:
    """Parse JSON from LLM output, with a single repair retry on failure."""
    try:
        return cast(dict[str, object], extract_json(raw))
    except json.JSONDecodeError as exc:
        logger.warning(
            "carousel_content_json_parse_failed_attempt_1",
            project_id=project_id,
            error=str(exc),
            raw_response=raw[:2000],
        )

    repair_response = await llm.generate(
        messages=[
            {"role": "user", "content": raw},
            {"role": "assistant", "content": _JSON_REPAIR_PROMPT},
        ],
        temperature=0.2,
    )

    try:
        return cast(dict[str, object], extract_json(repair_response))
    except json.JSONDecodeError as exc:
        logger.exception(
            "carousel_content_json_parse_failed_attempt_2",
            project_id=project_id,
            error=str(exc),
            raw_response=raw[:2000],
            repair_response=repair_response[:2000],
        )
        raise


__all__ = ["extract_json", "extract_json_with_repair"]
