"""Map a topic candidate to and from its ORM row (shared by both stores).

PR #106 review: one copy for the repository and the intake store, so a new
scout field (v3 ``pov_format`` / ``slide_count``) is mapped once.
"""

from __future__ import annotations

from rag_backend.modules.autopilot.domain.models import TopicCandidate
from rag_backend.modules.autopilot.infrastructure.models import TopicCandidateModel


def topic_row(candidate: TopicCandidate) -> TopicCandidateModel:
    """The ORM row for ``candidate``."""
    return TopicCandidateModel(
        id=candidate.candidate_id,
        title=candidate.title,
        angle=candidate.angle,
        why_viral=candidate.why_viral,
        audience=candidate.audience,
        niche=candidate.niche,
        brief=candidate.brief,
        sources=list(candidate.sources),
        score=candidate.score,
        signal_hash=candidate.signal_hash,
        status=candidate.status,
        image_style=candidate.image_style,
        image_guidance=candidate.image_guidance,
        content_mode=candidate.content_mode,
        thesis_draft=candidate.thesis_draft,
        pov_format=candidate.pov_format,
        slide_count=candidate.slide_count,
    )


def topic_from_row(row: TopicCandidateModel) -> TopicCandidate:
    """The domain candidate stored in ``row``."""
    return TopicCandidate(
        candidate_id=row.id,
        title=row.title,
        angle=row.angle,
        why_viral=row.why_viral,
        audience=row.audience,
        niche=row.niche,
        brief=row.brief,
        sources=tuple(row.sources),
        score=row.score,
        signal_hash=row.signal_hash,
        status=row.status,
        image_style=row.image_style,
        image_guidance=row.image_guidance,
        content_mode=row.content_mode,
        thesis_draft=row.thesis_draft,
        pov_format=row.pov_format,
        slide_count=row.slide_count,
    )


__all__ = ["topic_from_row", "topic_row"]
