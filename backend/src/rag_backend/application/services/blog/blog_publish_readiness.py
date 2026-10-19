"""One publish guard for every path to ``published`` (AE-0424 review).

"Publish now", submit-for-review, schedule and the due-post sweep all check the
same two things: the ``blog.v2`` document has >= 1 non-empty section, and the
AI-disclosure label is valid for publication. A scheduled post that fails is
never published by the sweep.
"""

from __future__ import annotations

from typing import Protocol

from rag_backend.application.services.ai_disclosure_service import AiDisclosureService
from rag_backend.application.services.blog.blog_document_service import (
    BlogDocumentService,
)
from rag_backend.domain.constants.ai_disclosure import ERR_DISCLOSURE_REQUIRED


class PublishCandidate(Protocol):
    """The row fields the publish guard reads."""

    content: object
    ai_disclosure_label: object
    ai_generation_metadata: object


class DisclosureRequiredError(ValueError):
    """The AI-disclosure label is missing or invalid for publication."""

    code = ERR_DISCLOSURE_REQUIRED


def disclosure_label(post: PublishCandidate) -> str:
    """The stored label, else the one derived from the AI usage metadata."""
    metadata = post.ai_generation_metadata
    usage = metadata if isinstance(metadata, dict) else {}
    stored = post.ai_disclosure_label
    return str(stored or AiDisclosureService.compute_label(usage))


def assert_ready_to_publish(post: PublishCandidate) -> None:
    """Raise ``InvalidBlogDocumentError`` / :class:`DisclosureRequiredError`."""
    BlogDocumentService.assert_publishable(post.content)
    if not AiDisclosureService.validate_for_publish(disclosure_label(post)):
        raise DisclosureRequiredError(ERR_DISCLOSURE_REQUIRED)


__all__ = [
    "DisclosureRequiredError",
    "PublishCandidate",
    "assert_ready_to_publish",
    "disclosure_label",
]
