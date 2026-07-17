"""Typed inputs for editorial workflow web-research enrichment (AE-0317)."""

from __future__ import annotations

from dataclasses import dataclass

from rag_backend.domain.protocols.carousel import ResearchTool


@dataclass(frozen=True)
class ResearchEnrichmentParams:
    """Bundles the topic and research tool for one enrichment run.

    ``research_tool=None`` disables enrichment entirely (CI, tests, or the
    ``research_enrichment_enabled`` kill switch) — sources pass through
    unchanged.
    """

    topic: str
    research_tool: ResearchTool | None


__all__ = ["ResearchEnrichmentParams"]
