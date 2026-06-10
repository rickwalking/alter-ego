"""Phase artifact generation helpers for the editorial workflow service."""

from __future__ import annotations

from dataclasses import dataclass

from rag_backend.agents.content_draft_agent import ContentDraftAgent
from rag_backend.agents.outline_agent import OutlineAgent
from rag_backend.agents.source_synthesis_agent import SourceSynthesisAgent
from rag_backend.application.services.carousel.malformed_draft_normalizer import (
    normalize_slide_draft,
)
from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
)
from rag_backend.domain.constants.carousel import LANGUAGE_PT
from rag_backend.domain.constants.carousel_workflow import SOURCE_TYPE_DOCUMENT
from rag_backend.domain.models.persona import PersonaProfile

from .editorial_workflow_support import EditorialWorkflowStartInput


@dataclass(frozen=True)
class SlideDraftGenerationParams:
    """Inputs for generating slide drafts from an outline."""

    outline: list[dict[str, object]]
    persona: PersonaProfile | None = None
    revision_notes: list[str] | None = None
    learned_examples: list[str] | None = None


async def synthesize_research(
    source_agent: SourceSynthesisAgent,
    sources: list[dict[str, str]],
) -> list[dict[str, object]]:
    """Extract research findings from source documents."""
    research_findings: list[dict[str, object]] = []
    for source in sources:
        extracted = await source_agent.extract_key_points(
            title=source.get("title", ""),
            content=source.get("content", ""),
            source_type=source.get("source_type", SOURCE_TYPE_DOCUMENT),
        )
        research_findings.append({
            "source": source.get("title", ""),
            **extracted,
        })
    return research_findings


async def generate_outline(
    outline_agent: OutlineAgent,
    workflow_input: EditorialWorkflowStartInput,
) -> list[dict[str, object]]:
    """Generate carousel outline from brief and sources."""
    source_texts = [s.get("content", "") for s in workflow_input.sources]
    outline = await outline_agent.generate_outline(
        topic=workflow_input.topic,
        audience=workflow_input.audience,
        brief=workflow_input.brief,
        sources=source_texts,
    )
    return [slide for slide in outline if isinstance(slide, dict)]


async def generate_slide_drafts(
    content_agent: ContentDraftAgent,
    params: SlideDraftGenerationParams,
) -> list[dict[str, object]]:
    """Draft slide copy for each outline entry."""
    persona_context_parts: list[str] = []
    if params.revision_notes:
        persona_context_parts.append(
            "Apply these reviewer notes:\n"
            + "\n".join(f"- {note}" for note in params.revision_notes if note.strip())
        )
    if params.learned_examples:
        persona_context_parts.append(
            "Past successful corrections:\n"
            + "\n".join(
                f"- {example}" for example in params.learned_examples if example.strip()
            )
        )
    persona_context = "\n\n".join(persona_context_parts)
    revision_notes = (
        "\n".join(note for note in params.revision_notes if note.strip())
        if params.revision_notes
        else ""
    )
    slide_drafts: list[dict[str, object]] = []
    for slide in params.outline:
        draft = await content_agent.draft_slide(
            slide_index=int(slide.get("slide_index", 0)),
            title=str(slide.get("title", "")),
            key_points=[
                str(p) for p in slide.get("key_points", []) if isinstance(p, str)
            ],
            persona=params.persona,
            persona_context=persona_context,
            locale=LANGUAGE_PT,
            revision_notes=revision_notes,
        )
        slide_drafts.append(normalize_slide_draft({**slide, **draft}))
    return slide_drafts


def resolve_workflow_input(
    prior: CarouselWorkflowState,
    workflow_input: EditorialWorkflowStartInput,
) -> EditorialWorkflowStartInput:
    """Merge persisted brief with caller-provided workflow input."""
    brief = prior.get("brief")
    if not isinstance(brief, dict):
        return workflow_input
    raw_sources = brief.get("sources", workflow_input.sources)
    sources = raw_sources if isinstance(raw_sources, list) else workflow_input.sources
    return EditorialWorkflowStartInput(
        topic=str(brief.get("topic", workflow_input.topic)),
        audience=str(brief.get("audience", workflow_input.audience)),
        brief=str(brief.get("brief", workflow_input.brief)),
        sources=sources,
        persona=workflow_input.persona,
        user_id=workflow_input.user_id,
        reviewer_id=workflow_input.reviewer_id,
    )


__all__ = [
    "SlideDraftGenerationParams",
    "generate_outline",
    "generate_slide_drafts",
    "resolve_workflow_input",
    "synthesize_research",
]
