"""In-graph phase artifact generation (CP-004)."""

from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.agents.content_draft_agent import ContentDraftAgent
from rag_backend.agents.feedback_learning import FeedbackLearningLoop
from rag_backend.agents.outline_agent import OutlineAgent
from rag_backend.agents.persona_agent import PersonaAgent
from rag_backend.application.services.carousel.editorial_visual_pipeline import (
    CarouselImageGenerationContext,
    apply_design_tokens,
    ensure_slides_from_outline,
    generate_carousel_images,
)
from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
)
from rag_backend.application.services.image_provider_registry import (
    ImageProviderRegistry,
)
from rag_backend.domain.constants.ai_agents import ERR_INVALID_JSON
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_CONTENT,
    PHASE_DESIGN,
    PHASE_IMAGES,
    PHASE_OUTLINE,
    PHASE_STATUS_FAILED,
    WORKFLOW_ERROR_KEY,
)
from rag_backend.domain.models.persona import PersonaProfile
from rag_backend.infrastructure.external.openai_embeddings import (  # type: ignore[attr-defined]
    OpenAIEmbeddings,
)

from .editorial_workflow_generators import (
    SlideDraftGenerationParams,
    generate_outline,
    generate_slide_drafts,
    resolve_workflow_input,
)
from .editorial_workflow_support import (
    EditorialWorkflowStartInput,
    publish_workflow_artifacts_from_updates,
)


class PhaseArtifactRunner:
    """Generate phase artifacts inside LangGraph nodes before human gates."""

    def __init__(
        self,
        *,
        outline_agent: OutlineAgent,
        content_agent: ContentDraftAgent,
        llm: BaseChatModel,
        image_registry: ImageProviderRegistry | None = None,
        db: AsyncSession | None = None,
        workflow_input: EditorialWorkflowStartInput | None = None,
    ) -> None:
        self._outline_agent = outline_agent
        self._content_agent = content_agent
        self._llm = llm
        self._image_registry = image_registry
        self._db = db
        self._workflow_input = workflow_input

    def with_context(
        self,
        *,
        db: AsyncSession | None = None,
        workflow_input: EditorialWorkflowStartInput | None = None,
    ) -> PhaseArtifactRunner:
        """Return a runner scoped to the current resume/request context."""
        return PhaseArtifactRunner(
            outline_agent=self._outline_agent,
            content_agent=self._content_agent,
            llm=self._llm,
            image_registry=self._image_registry,
            db=db if db is not None else self._db,
            workflow_input=workflow_input or self._workflow_input,
        )

    async def ensure_for_phase(self, state: CarouselWorkflowState) -> dict[str, object]:
        """Build missing artifacts for the active workflow phase."""
        phase = str(state.get("current_phase", ""))
        if self._workflow_input is None:
            return {}
        resolved = resolve_workflow_input(state, self._workflow_input)
        updates: dict[str, object] = {}

        if phase == PHASE_OUTLINE and not state.get("outline"):
            updates["outline"] = await generate_outline(self._outline_agent, resolved)
        elif phase == PHASE_CONTENT:
            updates.update(
                await self._ensure_content_artifacts(state, resolved, updates)
            )
        elif phase == PHASE_DESIGN:
            updates.update(await self._ensure_design_artifacts(state, updates))
        elif phase == PHASE_IMAGES:
            updates.update(await self._ensure_image_artifacts(state))

        if updates:
            project_id = str(state.get("project_id", ""))
            if project_id:
                await publish_workflow_artifacts_from_updates(
                    project_id,
                    phase,
                    updates,
                )

        return updates

    async def _ensure_content_artifacts(
        self,
        state: CarouselWorkflowState,
        resolved: EditorialWorkflowStartInput,
        pending: dict[str, object],
    ) -> dict[str, object]:
        updates: dict[str, object] = {}
        outline = pending.get("outline") or state.get("outline") or []
        revision_notes = self._content_revision_notes(state)
        should_regenerate = not state.get("slide_drafts") or bool(revision_notes)
        if should_regenerate and isinstance(outline, list):
            draft_updates = await self._generate_content_drafts(
                resolved,
                outline,
                revision_notes,
            )
            if draft_updates.get("phase_status") == PHASE_STATUS_FAILED:
                return draft_updates
            updates.update(draft_updates)
        slide_drafts = updates.get("slide_drafts") or state.get("slide_drafts") or []
        persona_updates = await self._score_content_drafts(resolved, slide_drafts)
        updates.update(persona_updates)
        design_updates = await self._apply_content_design(state, outline)
        updates.update(design_updates)
        return updates

    async def _generate_content_drafts(
        self,
        resolved: EditorialWorkflowStartInput,
        outline: list[object],
        revision_notes: list[str],
    ) -> dict[str, object]:
        learned_examples = await self._load_learned_examples(resolved.persona)
        try:
            slide_drafts = await generate_slide_drafts(
                self._content_agent,
                SlideDraftGenerationParams(
                    outline=[slide for slide in outline if isinstance(slide, dict)],
                    persona=resolved.persona,
                    revision_notes=revision_notes or None,
                    learned_examples=learned_examples or None,
                ),
            )
        except ValueError as exc:
            if str(exc) == ERR_INVALID_JSON:
                return {
                    "phase_status": PHASE_STATUS_FAILED,
                    WORKFLOW_ERROR_KEY: ERR_INVALID_JSON,
                }
            raise
        return {"slide_drafts": slide_drafts}

    async def _score_content_drafts(
        self,
        resolved: EditorialWorkflowStartInput,
        slide_drafts: object,
    ) -> dict[str, object]:
        if resolved.persona is None:
            return {}
        if not isinstance(slide_drafts, list) or not slide_drafts:
            return {}
        return {
            "persona_scores": await self._score_slides(
                slide_drafts,
                resolved.persona,
            )
        }

    async def _apply_content_design(
        self,
        state: CarouselWorkflowState,
        outline: object,
    ) -> dict[str, object]:
        if self._db is None or not isinstance(outline, list):
            return {}
        slides = await ensure_slides_from_outline(
            self._db,
            str(state.get("project_id", "")),
            [slide for slide in outline if isinstance(slide, dict)],
        )
        if not slides:
            return {}
        await apply_design_tokens(
            self._db,
            str(state.get("project_id", "")),
            slides,
        )
        return {"design_applied": True}

    @staticmethod
    def _content_revision_notes(state: CarouselWorkflowState) -> list[str]:
        phase_feedback = state.get("phase_feedback") or {}
        if not isinstance(phase_feedback, dict):
            return []
        raw_notes = phase_feedback.get(PHASE_CONTENT, [])
        if not isinstance(raw_notes, list):
            return []
        return [str(note) for note in raw_notes if str(note).strip()]

    async def _load_learned_examples(
        self,
        persona: PersonaProfile | None,
    ) -> list[str]:
        if persona is None or self._db is None:
            return []
        feedback_loop = FeedbackLearningLoop(
            session=self._db,
            embeddings=OpenAIEmbeddings(),
        )
        return await feedback_loop.get_relevant_examples(str(persona.id))

    async def _ensure_design_artifacts(
        self,
        state: CarouselWorkflowState,
        pending: dict[str, object],
    ) -> dict[str, object]:
        if self._db is None:
            return {}
        outline = pending.get("outline") or state.get("outline") or []
        if not isinstance(outline, list):
            return {}
        slides = await ensure_slides_from_outline(
            self._db,
            str(state.get("project_id", "")),
            [slide for slide in outline if isinstance(slide, dict)],
        )
        if not slides:
            return {}
        await apply_design_tokens(
            self._db,
            str(state.get("project_id", "")),
            slides,
        )
        return {"design_applied": True}

    async def _ensure_image_artifacts(
        self,
        state: CarouselWorkflowState,
    ) -> dict[str, object]:
        if self._db is None or self._image_registry is None:
            return {}
        outline = state.get("outline") or []
        if not isinstance(outline, list):
            return {}
        slides = await ensure_slides_from_outline(
            self._db,
            str(state.get("project_id", "")),
            [slide for slide in outline if isinstance(slide, dict)],
        )
        if not slides:
            return {}
        assets = await generate_carousel_images(
            self._db,
            CarouselImageGenerationContext(
                project_id=str(state.get("project_id", "")),
                slides=slides,
                image_registry=self._image_registry,
            ),
        )
        return {"image_assets": assets, "design_applied": True}

    async def _score_slides(
        self,
        slide_drafts: list[object],
        persona: PersonaProfile,
    ) -> dict[str, object]:
        persona_agent = PersonaAgent(persona=persona, llm=self._llm)
        persona_scores: dict[str, object] = {}
        for index, slide in enumerate(slide_drafts):
            if not isinstance(slide, dict):
                continue
            draft_text = str(slide.get("draft_text", ""))
            if not draft_text:
                continue
            persona_scores[f"slide_{index + 1}"] = await persona_agent.evaluate_match(
                draft_text
            )
        return persona_scores


__all__ = ["PhaseArtifactRunner"]
