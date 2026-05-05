"""Carousel content synthesis subpackage.

Public exports:
- ``run_content`` — phases 2-3 entry point
- ``extract_json`` — robust JSON extraction from LLM responses
"""

from rag_backend.application.services.carousel.nodes.content.core import run_content
from rag_backend.application.services.carousel.nodes.content.json_utils import (
    _ERR_JSON_NOT_FOUND,
    _extract_json_with_repair,
    extract_json,
)

__all__ = [
    "_ERR_JSON_NOT_FOUND",
    "_extract_json_with_repair",
    "extract_json",
    "run_content",
]
