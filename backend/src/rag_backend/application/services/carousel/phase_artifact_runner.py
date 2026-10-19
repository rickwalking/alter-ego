"""In-graph phase artifact generation (CP-004)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from typing import TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import RunnableConfig
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.agents.content_draft_agent import ContentDraftAgent
from rag_backend.agents.feedback_learning import FeedbackLearningLoop
from rag_backend.agents.outline_agent import OutlineAgent
from rag_backend.agents.persona_agent import PersonaAgent
from rag_backend.application.services.carousel.blog_composition import (
    research_summary_from_findings,
)
from rag_backend.application.services.carousel.bounded_gather import gather_bounded
from rag_backend.application.services.carousel.content_fail_closed import (
    FailClosedReviewCommand,
    SlideDraftRetryFn,
    build_fail_closed_review_updates,
)
from rag_backend.application.services.carousel.content_feedback_lifecycle import (
    active_feedback_notes,
    consume_feedback_notes,
)
from rag_backend.application.services.carousel.content_gate_repair import (
    GateFieldRepairer,
    LlmGateFieldRepairer,
    LlmGateRepairConfig,
)
from rag_backend.application.services.carousel.content_gate_repair_flow import (
    GateRepairContext,
    gate_violation_note,
    repair_blocked_content_gate,
    visible_copy_changed,
)
from rag_backend.application.services.carousel.editorial_visual_pipeline import (
    CarouselImageGenerationContext,
    apply_design_tokens,
    ensure_slides_from_outline,
    generate_carousel_images,
)
from rag_backend.application.services.carousel.persona_judge import judge_voice
from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
)
from rag_backend.application.services.image_provider_registry import (
    ImageProviderRegistry,
)
from rag_backend.domain.constants.ai_agents import ERR_INVALID_JSON
from rag_backend.domain.constants.carousel_workflow import (
    DEFAULT_CONTENT_DRAFT_CONCURRENCY,
    DESIGN_VALIDATION_RECOVERY_HINT,
    PHASE_CONTENT,
    PHASE_DESIGN,
    PHASE_IMAGES,
    PHASE_OUTLINE,
    PHASE_STATUS_FAILED,
    WORKFLOW_ERROR_KEY,
)
from rag_backend.domain.constants.content_feedback import (
    FEEDBACK_STATUS_APPLIED,
    FEEDBACK_STATUS_UNCHANGED,
)
from rag_backend.domain.constants.presentation_policy import (
    DEFAULT_PRESENTATION_POLICY_VERSION,
)
from rag_backend.domain.constants.workflow_state_fields import (
    STATE_FIELD_DESIGN_RECOVERY_HINT,
    STATE_FIELD_PRESENTATION_VALIDATION,
    STATE_FIELD_RESEARCH_FINDINGS,
    STATE_FIELD_SLIDE_DRAFTS,
)
from rag_backend.domain.models.persona import PersonaProfile
from rag_backend.infrastructure.external.openai_embeddings import (  # type: ignore[attr-defined]
    OpenAIEmbeddings,
)

from .content_mode_brief import ContentModeBrief, load_content_mode_brief
from .editorial_distribution_pack import (
    DistributionBuildContext,
    build_editorial_distribution_updates,
)
from .editorial_workflow_generators import (
    ContentRegenInputs,
    SlideDraftGenerationParams,
    build_slide_draft_retry,
    generate_outline,
    generate_slide_drafts,
    resolve_workflow_input,
)
from .editorial_workflow_support import (
    EditorialWorkflowStartInput,
    publish_workflow_artifacts_from_updates,
)
from .localized_rows_sync import sync_rows_to_localized
from .outline_normalize import normalize_editorial_outline


@dataclass
class PhaseArtifactRunnerConfig:
    outline_agent: OutlineAgent
    content_agent: ContentDraftAgent
    llm: BaseChatModel
    image_registry: ImageProviderRegistry | None = None
    db: AsyncSession | None = None
    workflow_input: EditorialWorkflowStartInput | None = None
    # AE-0309: injectable single-slide re-draft used by the fail-closed content
    # chain. Defaults to a ContentDraftAgent-backed retry when None.
    slide_draft_retry: SlideDraftRetryFn | None = None
    # AE-0391: slides drafted / persona-scored concurrently (bounded).
    draft_concurrency: int = DEFAULT_CONTENT_DRAFT_CONCURRENCY
    # AE-0430: rewrites only the fields a blocked content gate names. When
    # unset, ``gate_repair_tracing`` (the orchestrator's Langfuse config) turns
    # on the fast-model repairer built from ``llm``; with neither, it is off.
    gate_repairer: GateFieldRepairer | None = None
    gate_repair_tracing: Callable[[], RunnableConfig] | None = None


_TRANSLATIONS_EN_KEY = "translations_en"


def _state_policy_version(state: CarouselWorkflowState) -> str | None:
    """Resolve the seeded presentation policy version from workflow state."""
    value = state.get("presentation_policy_version")
    return value if isinstance(value, str) and value.strip() else None


def _review_translations(
    state: CarouselWorkflowState,
    updates: dict[str, object],
) -> object:
    """EN translations for the content review build (AE-0413).

    Fresh translations win. When the drafts were NOT regenerated the stored
    translations still match them: dropping them made the builder fall back
    to the PT draft, so the EN copy silently became Portuguese.
    """
    fresh = updates.get(_TRANSLATIONS_EN_KEY)
    if fresh is not None or STATE_FIELD_SLIDE_DRAFTS in updates:
        return fresh
    return state.get(_TRANSLATIONS_EN_KEY)


def _llm_gate_repairer(config: PhaseArtifactRunnerConfig) -> GateFieldRepairer | None:
    """AE-0430: the fast-model field repairer, on when tracing is configured."""
    if config.gate_repair_tracing is None:
        return None
    return LlmGateFieldRepairer(
        LlmGateRepairConfig(llm=config.llm, runnable_config=config.gate_repair_tracing)
    )


def _settle_used_notes(
    state: CarouselWorkflowState,
    updates: dict[str, object],
) -> dict[str, object]:
    """AE-0405: the notes a regeneration used move to the history.

    AE-0430: as "unchanged" when the visible slide copy did not change.
    """
    status = (
        FEEDBACK_STATUS_APPLIED
        if visible_copy_changed(state, updates)
        else FEEDBACK_STATUS_UNCHANGED
    )
    return consume_feedback_notes(state, PHASE_CONTENT, status)


@dataclass(frozen=True)
class ContentReviewContext:
    """Inputs for building the fail-closed content review updates."""

    project_id: str
    slide_drafts: object
    translations_en: object
    retry_draft: SlideDraftRetryFn | None
    policy_version: str | None = None


class DistributionCheckParams(TypedDict):
    state: CarouselWorkflowState
    outline: object
    slide_drafts: object
    updates: dict[str, object]


class PhaseArtifactRunner:
    """Generate phase artifacts inside LangGraph nodes before human gates."""

    def __init__(
        self,
        config: PhaseArtifactRunnerConfig,
    ) -> None:
        self._outline_agent = config.outline_agent
        self._content_agent = config.content_agent
        self._llm = config.llm
        self._image_registry = config.image_registry
        self._db = config.db
        self._workflow_input = config.workflow_input
        self._slide_draft_retry = config.slide_draft_retry
        self._draft_concurrency = config.draft_concurrency
        self._gate_repair_tracing = config.gate_repair_tracing
        self._gate_repairer = config.gate_repairer or _llm_gate_repairer(config)

    def with_context(
        self,
        *,
        db: AsyncSession | None = None,
        workflow_input: EditorialWorkflowStartInput | None = None,
    ) -> PhaseArtifactRunner:
        """Return a runner scoped to the current resume/request context."""
        return PhaseArtifactRunner(
            PhaseArtifactRunnerConfig(
                outline_agent=self._outline_agent,
                content_agent=self._content_agent,
                llm=self._llm,
                image_registry=self._image_registry,
                db=db if db is not None else self._db,
                workflow_input=workflow_input or self._workflow_input,
                slide_draft_retry=self._slide_draft_retry,
                draft_concurrency=self._draft_concurrency,
                gate_repairer=self._gate_repairer,
                gate_repair_tracing=self._gate_repair_tracing,
            )
        )

    @staticmethod
    def _normalize_outline_in_state(
        state: CarouselWorkflowState,
    ) -> tuple[CarouselWorkflowState, dict[str, object]]:
        """Normalize outline dicts in state if they differ from persisted format."""
        updates: dict[str, object] = {}
        raw_outline = state.get("outline")
        if not isinstance(raw_outline, list):
            return state, updates
        outline_dicts = [slide for slide in raw_outline if isinstance(slide, dict)]
        if not outline_dicts:
            return state, updates
        normalized_outline = normalize_editorial_outline(outline_dicts)
        from rag_backend.application.services.carousel.workflow_state_sanitize import (
            workflow_artifacts_differ,
        )

        if not workflow_artifacts_differ(outline_dicts, normalized_outline):
            return state, updates
        updates["outline"] = normalized_outline
        state = {**state, "outline": normalized_outline}  # type: ignore[arg-type]
        return state, updates

    @staticmethod
    async def _publish_phase_updates(
        state: CarouselWorkflowState,
        phase: str,
        updates: dict[str, object],
    ) -> None:
        """Publish phase artifact updates to the event stream if present."""
        if not updates:
            return
        project_id = str(state.get("project_id", ""))
        if not project_id:
            return
        await publish_workflow_artifacts_from_updates(project_id, phase, updates)

    async def _regen_inputs(self, state: CarouselWorkflowState) -> ContentRegenInputs:
        """Reviewer notes, the prior drafts and the content mode for a regeneration."""
        prior_drafts = [
            draft
            for draft in (state.get("slide_drafts") or [])
            if isinstance(draft, dict)
        ]
        notes = self._content_revision_notes(state)
        # AE-0430: a revision also gets the gate's blocking violations.
        violations = gate_violation_note(state) if notes else None
        return ContentRegenInputs(
            revision_notes=[*notes, violations] if violations else notes,
            previous_drafts=prior_drafts,
            mode=await self._mode_brief(state),
        )

    async def _mode_brief(
        self, state: CarouselWorkflowState
    ) -> ContentModeBrief | None:
        """AE-0375: the project's content mode, read from its row (ADR-0021 D4)."""
        return await load_content_mode_brief(self._db, str(state.get("project_id", "")))

    async def ensure_for_phase(self, state: CarouselWorkflowState) -> dict[str, object]:
        """Build missing artifacts for the active workflow phase."""
        phase = str(state.get("current_phase", ""))
        if self._workflow_input is None:
            return {}
        resolved = resolve_workflow_input(state, self._workflow_input)
        state, outline_updates = self._normalize_outline_in_state(state)
        updates: dict[str, object] = {**outline_updates}

        if phase == PHASE_OUTLINE and not state.get("outline"):
            updates["outline"] = await generate_outline(
                self._outline_agent, resolved, await self._mode_brief(state)
            )
        elif phase == PHASE_CONTENT:
            updates.update(
                await self._ensure_content_artifacts(state, resolved, updates)
            )
        elif phase == PHASE_DESIGN:
            updates.update(await self._ensure_design_artifacts(state, updates))
        elif phase == PHASE_IMAGES:
            updates.update(await self._ensure_image_artifacts(state))
        if phase in {PHASE_CONTENT, PHASE_DESIGN}:
            # AE-0401: render what the gate validated (rows = localized copy).
            await sync_rows_to_localized(
                self._db, str(state.get("project_id", "")), {**state, **updates}
            )

        await self._publish_phase_updates(state, phase, updates)
        return updates

    @staticmethod
    async def _resolve_outline(
        pending: dict[str, object],
        state: CarouselWorkflowState,
    ) -> tuple[list[object], dict[str, object]]:
        """Resolve and normalize the outline from pending/state."""
        updates: dict[str, object] = {}
        raw_outline = pending.get("outline") or state.get("outline") or []
        outline: list[object] = raw_outline  # type: ignore[assignment]
        if isinstance(raw_outline, list):
            outline_dicts = [slide for slide in raw_outline if isinstance(slide, dict)]
            if outline_dicts:
                from rag_backend.application.services.carousel.workflow_state_sanitize import (
                    workflow_artifacts_differ,
                )

                normalized_outline = normalize_editorial_outline(outline_dicts)
                if workflow_artifacts_differ(outline_dicts, normalized_outline):
                    outline = normalized_outline
                    updates["outline"] = normalized_outline
        return outline, updates

    async def _build_distribution_if_needed(
        self,
        state: CarouselWorkflowState,
        outline: list[object],
        config: tuple[object, dict[str, object]],
    ) -> dict[str, object]:
        """Build editorial distribution if conditions are met."""
        slide_drafts, updates = config
        if self._db is None:
            return {}
        if not self._should_build_distribution(
            DistributionCheckParams(
                state=state, outline=outline, slide_drafts=slide_drafts, updates=updates
            )
        ):
            return {}
        from rag_backend.infrastructure.container import get_container

        container = get_container()
        return await build_editorial_distribution_updates(
            DistributionBuildContext(
                db=self._db,
                llm=self._llm,
                project_id=str(state.get("project_id", "")),
                outline=[slide for slide in outline if isinstance(slide, dict)],
                slide_drafts=[
                    slide for slide in slide_drafts if isinstance(slide, dict)
                ],
                research_summary=research_summary_from_findings(
                    state.get(STATE_FIELD_RESEARCH_FINDINGS)
                ),
            ),
            linkedin_generator=container.linkedin_post_generator(),
        )

    async def _ensure_content_artifacts(
        self,
        state: CarouselWorkflowState,
        resolved: EditorialWorkflowStartInput,
        pending: dict[str, object],
    ) -> dict[str, object]:
        updates: dict[str, object] = {}
        outline, outline_updates = await self._resolve_outline(pending, state)
        updates.update(outline_updates)
        regen = await self._regen_inputs(state)
        should_regenerate = not state.get("slide_drafts") or bool(regen.revision_notes)
        regenerated = should_regenerate and isinstance(outline, list)
        if regenerated:
            draft_updates = await self._generate_content_drafts(
                resolved, outline, regen
            )
            if draft_updates.get("phase_status") == PHASE_STATUS_FAILED:
                return draft_updates
            updates.update(draft_updates)
        slide_drafts = updates.get("slide_drafts") or state.get("slide_drafts") or []
        persona_updates = await self._score_content_drafts(resolved, slide_drafts)
        updates.update(persona_updates)
        distribution = await self._build_distribution_if_needed(
            state, outline, (slide_drafts, updates)
        )
        updates.update(distribution)
        design_updates = await self._apply_content_design(state, outline)
        updates.update(design_updates)
        from rag_backend.application.services.carousel.workflow_state_sanitize import (
            SanitizeWorkflowStateCommand,
            sanitize_workflow_state_artifacts,
        )

        sanitized_state = sanitize_workflow_state_artifacts(
            SanitizeWorkflowStateCommand(
                state={
                    **state,
                    **updates,
                    "outline": updates.get("outline") or state.get("outline") or [],
                    "slide_drafts": updates.get("slide_drafts")
                    or state.get("slide_drafts")
                    or [],
                },
                # AE-0413: the project's budgets, not the v1 defaults.
                policy_version=_state_policy_version(state)
                or DEFAULT_PRESENTATION_POLICY_VERSION,
                rebuild_validation=False,
            ),
        )
        if isinstance(sanitized_state.get("outline"), list):
            updates["outline"] = sanitized_state["outline"]
        if isinstance(sanitized_state.get("slide_drafts"), list):
            updates["slide_drafts"] = sanitized_state["slide_drafts"]
        updates.update(
            await self._build_presentation_review_updates(
                ContentReviewContext(
                    project_id=str(state.get("project_id", "")),
                    slide_drafts=sanitized_state.get("slide_drafts") or [],
                    translations_en=_review_translations(state, updates),
                    retry_draft=self._resolve_slide_draft_retry(
                        resolved, outline, regen
                    ),
                    policy_version=_state_policy_version(state),
                )
            )
        )
        await self._repair_content_gate(state, updates, resolved)
        if regenerated:
            updates.update(_settle_used_notes(state, updates))
        return updates

    async def _repair_content_gate(
        self,
        state: CarouselWorkflowState,
        updates: dict[str, object],
        resolved: EditorialWorkflowStartInput,
    ) -> None:
        """AE-0430: targeted field repair of a blocked content gate (in place)."""
        style_guide = (
            PersonaAgent(resolved.persona, self._llm).style_guide()
            if resolved.persona
            else ""
        )
        updates.update(
            await repair_blocked_content_gate(
                state,
                updates,
                GateRepairContext(
                    repairer=self._gate_repairer,
                    style_guide=style_guide,
                    project_id=str(state.get("project_id", "")),
                ),
            )
        )

    def _resolve_slide_draft_retry(
        self,
        resolved: EditorialWorkflowStartInput,
        outline: object,
        regen: ContentRegenInputs | None = None,
    ) -> SlideDraftRetryFn | None:
        """Injected retry double when configured, else the agent-backed retry.

        AE-0413: the re-draft of a blocking slide carries the reviewer notes of
        this regeneration too, so a retried slide does not ignore the feedback.
        """
        if self._slide_draft_retry is not None:
            return self._slide_draft_retry
        if not isinstance(outline, list):
            return None
        outline_dicts = [slide for slide in outline if isinstance(slide, dict)]
        if not outline_dicts:
            return None
        return build_slide_draft_retry(
            self._content_agent,
            SlideDraftGenerationParams(
                outline=outline_dicts,
                persona=resolved.persona,
                revision_notes=(regen.revision_notes or None) if regen else None,
                mode=regen.mode if regen else None,
            ),
        )

    @staticmethod
    async def _build_presentation_review_updates(
        context: ContentReviewContext,
    ) -> dict[str, object]:
        """Build content review updates through the fail-closed chain (AE-0309)."""
        from rag_backend.application.services.carousel.presentation_review import (
            deserialize_translations_en,
        )

        slide_drafts = context.slide_drafts
        draft_dicts = (
            [slide for slide in slide_drafts if isinstance(slide, dict)]
            if isinstance(slide_drafts, list)
            else []
        )
        translations = (
            deserialize_translations_en(context.translations_en)
            if context.translations_en is not None
            else None
        )
        return await build_fail_closed_review_updates(
            FailClosedReviewCommand(
                project_id=context.project_id,
                slide_drafts=draft_dicts,
                translations_en=translations,
                policy_version=context.policy_version,
                retry_draft=context.retry_draft,
            )
        )

    async def _generate_content_drafts(
        self,
        resolved: EditorialWorkflowStartInput,
        outline: list[object],
        regen: ContentRegenInputs,
    ) -> dict[str, object]:
        learned_examples = await self._load_learned_examples(resolved.persona)
        try:
            slide_drafts = await generate_slide_drafts(
                self._content_agent,
                SlideDraftGenerationParams(
                    outline=[slide for slide in outline if isinstance(slide, dict)],
                    persona=resolved.persona,
                    revision_notes=regen.revision_notes or None,
                    learned_examples=learned_examples or None,
                    previous_drafts=regen.previous_drafts or None,
                    mode=regen.mode,
                    concurrency=self._draft_concurrency,
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
    def _should_build_distribution(
        params: DistributionCheckParams,
    ) -> bool:
        if not isinstance(params["outline"], list) or not isinstance(
            params["slide_drafts"], list
        ):
            return False
        if not params["slide_drafts"]:
            return False
        drafts_were_generated = "slide_drafts" in params["updates"]
        needs_distribution = (
            not params["state"].get("caption")
            or not params["state"].get("blog_markdown")
            or not params["state"].get("linkedin_post_pt")
            or not params["state"].get("linkedin_post_en")
        )
        return drafts_were_generated or needs_distribution

    @staticmethod
    def _content_revision_notes(state: CarouselWorkflowState) -> list[str]:
        return active_feedback_notes(state, PHASE_CONTENT)

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
        """Apply design tokens AND re-validate localized slides (AE-0310).

        Validation runs on EVERY execution — the 38affb3e dead-end happened
        because the design ensure re-applied tokens unconditionally but never
        validated, so the stored report went stale by omission.
        """
        updates = await self._apply_design_tokens_updates(state, pending)
        updates.update(self._design_validation_updates(state))
        return updates

    async def _apply_design_tokens_updates(
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

    @staticmethod
    def _design_validation_updates(
        state: CarouselWorkflowState,
    ) -> dict[str, object]:
        """Fresh presentation validation for the design ensure (AE-0310).

        Stores a new report (``validated_at`` advances) plus the recovery hint
        while the report still blocks; the hint is cleared once it passes.
        """
        from rag_backend.application.services.carousel.presentation_review import (
            WORKFLOW_STATE_LOCALIZED_SLIDES_KEY,
            WORKFLOW_STATE_PRESENTATION_POLICY_VERSION_KEY,
            validate_localized_slides,
            validation_report_to_dict,
        )

        localized = state.get(WORKFLOW_STATE_LOCALIZED_SLIDES_KEY)
        slides = (
            [slide for slide in localized if isinstance(slide, dict)]
            if isinstance(localized, list)
            else []
        )
        if not slides:
            return {}
        policy_raw = state.get(WORKFLOW_STATE_PRESENTATION_POLICY_VERSION_KEY)
        report = validate_localized_slides(
            slides,
            policy_version=str(policy_raw) if policy_raw else None,
        )
        return {
            STATE_FIELD_PRESENTATION_VALIDATION: validation_report_to_dict(report),
            STATE_FIELD_DESIGN_RECOVERY_HINT: (
                DESIGN_VALIDATION_RECOVERY_HINT if report.blocking else ""
            ),
        }

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
        texts = {
            index: str(slide.get("draft_text", ""))
            for index, slide in enumerate(slide_drafts)
            if isinstance(slide, dict) and str(slide.get("draft_text", ""))
        }
        # AE-0391: scored concurrently (bounded), keyed back in slide order.
        # AE-0407: retried once; a slide the judge never scored is left out.
        scores = await gather_bounded(
            [partial(judge_voice, persona_agent, text) for text in texts.values()],
            self._draft_concurrency,
        )
        return {
            f"slide_{index + 1}": score
            for index, score in zip(texts, scores, strict=True)
            if score is not None
        }


__all__ = ["PhaseArtifactRunner"]
