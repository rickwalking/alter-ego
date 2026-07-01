"""Phase artifact generation helpers for the editorial workflow service."""

from __future__ import annotations

from dataclasses import dataclass, field

import structlog

from rag_backend.agents.content_draft_agent import ContentDraftAgent
from rag_backend.agents.outline_agent import OutlineAgent
from rag_backend.agents.source_synthesis_agent import SourceSynthesisAgent
from rag_backend.application.services.carousel.content_distinctness import (
    find_duplicate_slide_indices,
    max_similarity_against,
)
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

logger = structlog.get_logger(__name__)

_DRAFT_TEXT_KEY = "draft_text"
_SLIDE_INDEX_KEY = "slide_index"
_TITLE_KEY = "title"
_KEY_POINTS_KEY = "key_points"
# AE-0291: intensified note fed to a re-draft when a body is a near-duplicate.
DISTINCTNESS_REDRAFT_NOTE = (
    "Your previous draft was too similar to another slide in this carousel. "
    "Rewrite it with different wording, examples, and concrete detail so it is "
    "clearly distinct from the other slides."
)


@dataclass(frozen=True)
class SlideDraftGenerationParams:
    """Inputs for generating slide drafts from an outline."""

    outline: list[dict[str, object]]
    persona: PersonaProfile | None = None
    revision_notes: list[str] | None = None
    learned_examples: list[str] | None = None
    # AE-0291: prior slide drafts (from checkpoint) so a regeneration can show the
    # model its previously-rejected copy to diff against (also busts the cache).
    previous_drafts: list[dict[str, object]] | None = None


@dataclass(frozen=True)
class ContentRegenInputs:
    """AE-0291: revision notes + prior drafts bundled for one content regeneration."""

    revision_notes: list[str]
    previous_drafts: list[dict[str, object]] = field(default_factory=list)


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


def _learned_persona_context(params: SlideDraftGenerationParams) -> str:
    """Past successful corrections as extra persona context (kept from v3)."""
    if not params.learned_examples:
        return ""
    lines = "\n".join(
        f"- {example}" for example in params.learned_examples if example.strip()
    )
    return f"Past successful corrections:\n{lines}" if lines else ""


def _joined_revision_notes(notes: list[str] | None) -> str:
    """AE-0291: reviewer notes as a single block (rendered imperatively downstream)."""
    if not notes:
        return ""
    return "\n".join(note for note in notes if note.strip())


def _build_sibling_context(outline: list[dict[str, object]], current_index: int) -> str:
    """Other slides' headings + key points so the model can differentiate copy."""
    lines: list[str] = []
    for index, slide in enumerate(outline):
        if index == current_index:
            continue
        title = str(slide.get(_TITLE_KEY, "")).strip()
        points = ", ".join(
            str(p) for p in slide.get(_KEY_POINTS_KEY, []) if isinstance(p, str)
        )
        number = slide.get(_SLIDE_INDEX_KEY, index)
        lines.append(f"- Slide {number}: {title} — {points}".rstrip(" —"))
    return "\n".join(lines)


def _previous_draft_body(
    previous_drafts: list[dict[str, object]] | None, slide_index: int
) -> str:
    """Prior draft body for a slide index, or empty when this is a fresh run."""
    if not previous_drafts:
        return ""
    for draft in previous_drafts:
        if int(draft.get(_SLIDE_INDEX_KEY, -1)) == slide_index:
            return str(draft.get(_DRAFT_TEXT_KEY, ""))
    return ""


def _draft_body(draft: dict[str, object]) -> str:
    return str(draft.get(_DRAFT_TEXT_KEY, ""))


@dataclass(frozen=True)
class _SlideDraftRunner:
    """Groups draft state so per-slide helpers stay within the 3-argument limit."""

    content_agent: ContentDraftAgent
    outline: list[dict[str, object]]
    persona: PersonaProfile | None
    persona_context: str
    revision_notes: str
    previous_drafts: list[dict[str, object]] = field(default_factory=list)

    async def draft_at(self, index: int) -> dict[str, object]:
        slide = self.outline[index]
        slide_index = int(slide.get(_SLIDE_INDEX_KEY, 0))
        draft = await self.content_agent.draft_slide(
            slide_index=slide_index,
            title=str(slide.get(_TITLE_KEY, "")),
            key_points=self._key_points(slide),
            persona=self.persona,
            persona_context=self.persona_context,
            locale=LANGUAGE_PT,
            revision_notes=self.revision_notes,
            sibling_context=_build_sibling_context(self.outline, index),
            previous_draft=_previous_draft_body(self.previous_drafts, slide_index),
        )
        return normalize_slide_draft({**slide, **draft})

    async def redraft_at(self, index: int, prior_body: str) -> dict[str, object]:
        """AE-0291: one bounded re-draft of a near-duplicate slide.

        Feeds the too-similar body back as the previous draft plus an intensified
        distinctness note (kept alongside any active reviewer notes).
        """
        slide = self.outline[index]
        slide_index = int(slide.get(_SLIDE_INDEX_KEY, 0))
        notes = f"{DISTINCTNESS_REDRAFT_NOTE}\n{self.revision_notes}".strip()
        draft = await self.content_agent.draft_slide(
            slide_index=slide_index,
            title=str(slide.get(_TITLE_KEY, "")),
            key_points=self._key_points(slide),
            persona=self.persona,
            persona_context=self.persona_context,
            locale=LANGUAGE_PT,
            revision_notes=notes,
            sibling_context=_build_sibling_context(self.outline, index),
            previous_draft=prior_body,
        )
        return normalize_slide_draft({**slide, **draft})

    @staticmethod
    def _key_points(slide: dict[str, object]) -> list[str]:
        return [str(p) for p in slide.get(_KEY_POINTS_KEY, []) if isinstance(p, str)]


def _others(bodies: list[str], index: int) -> list[str]:
    return [body for position, body in enumerate(bodies) if position != index]


async def _redraft_duplicates(
    runner: _SlideDraftRunner, drafts: list[dict[str, object]]
) -> list[dict[str, object]]:
    """Re-draft each near-duplicate slide at most once, keeping the more distinct."""
    bodies = [_draft_body(draft) for draft in drafts]
    for index in find_duplicate_slide_indices(bodies):
        candidate = await runner.redraft_at(index, bodies[index])
        candidate_body = _draft_body(candidate)
        others = _others(bodies, index)
        improved = max_similarity_against(
            candidate_body, others
        ) < max_similarity_against(bodies[index], others)
        if improved:
            drafts[index] = candidate
            bodies[index] = candidate_body
        else:
            logger.warning("carousel_slide_still_similar", slide_index=index)
    return drafts


async def generate_slide_drafts(
    content_agent: ContentDraftAgent,
    params: SlideDraftGenerationParams,
) -> list[dict[str, object]]:
    """Draft slide copy for each outline entry with cross-slide distinctness."""
    runner = _SlideDraftRunner(
        content_agent=content_agent,
        outline=params.outline,
        persona=params.persona,
        persona_context=_learned_persona_context(params),
        revision_notes=_joined_revision_notes(params.revision_notes),
        previous_drafts=params.previous_drafts or [],
    )
    drafts = [await runner.draft_at(index) for index in range(len(params.outline))]
    return await _redraft_duplicates(runner, drafts)


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
    "ContentRegenInputs",
    "SlideDraftGenerationParams",
    "generate_outline",
    "generate_slide_drafts",
    "resolve_workflow_input",
    "synthesize_research",
]
