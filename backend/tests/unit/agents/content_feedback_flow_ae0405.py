"""Shared harness for the content-feedback lifecycle tests.

A real ``CarouselWorkflowEngine`` (in-memory checkpointer) and a real
``PhaseArtifactRunner``; only the drafting model is a fake: a spy standing in
for ``generate_slide_drafts`` and for the fail-closed single-slide retry. A
review goes through ``prepare_resume_workflow`` then ``engine.resume`` exactly
like ``EditorialWorkflowService.resume_workflow``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast
from unittest.mock import MagicMock

from langgraph.checkpoint.memory import InMemorySaver

from rag_backend.agents.carousel_editorial_orchestrator import (
    CarouselEditorialOrchestrator,
)
from rag_backend.agents.carousel_workflow import CarouselWorkflowEngine
from rag_backend.application.services.carousel.editorial_workflow_generators import (
    SlideDraftGenerationParams,
)
from rag_backend.application.services.carousel.editorial_workflow_service_helpers import (
    ResumeContext,
    prepare_resume_workflow,
)
from rag_backend.application.services.carousel.editorial_workflow_support import (
    EditorialWorkflowStartInput,
)
from rag_backend.application.services.carousel.phase_artifact_runner import (
    PhaseArtifactRunner,
    PhaseArtifactRunnerConfig,
)
from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
)
from rag_backend.domain.constants.ai_agents import ERR_INVALID_JSON
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_CONTENT,
    REVIEW_ACTION_APPROVE,
    REVIEW_ACTION_REJECT,
    REVIEW_ACTION_REVISE,
    STRUCTURED_FEEDBACK_EDITED_SLIDES_KEY,
    STRUCTURED_FEEDBACK_KEY,
)

PROJECT_ID = "98a2e2f0-ae04-4050-8000-000000000405"
GENERATE_TARGET = (
    "rag_backend.application.services.carousel.phase_artifact_runner."
    "generate_slide_drafts"
)
_GENERATIONS = ("primeira", "segunda", "terceira", "quarta", "quinta")
_SLIDES = 7


def drafts_for(generation: int) -> list[dict[str, object]]:
    """Seven clean drafts whose copy names the generation that wrote them."""
    word = _GENERATIONS[generation % len(_GENERATIONS)]
    drafts: list[dict[str, object]] = [
        {
            "slide_index": 1,
            "slide_type": "intro",
            "title": "Gancho inicial",
            "draft_text": f"Uma promessa curta e concreta na {word} versao.",
        }
    ]
    for index in range(2, _SLIDES):
        drafts.append({
            "slide_index": index,
            "slide_type": "content",
            "title": f"Insight numero {index}",
            "draft_text": f"Detalhe pratico do insight {index} na {word} versao.",
            "content_kind": "features",
            "features": [
                {
                    "icon_name": "target",
                    "title": f"Pratica {index}",
                    "body": "Aplique no proximo ciclo.",
                }
            ],
        })
    drafts.append({
        "slide_index": _SLIDES,
        "slide_type": "cta",
        "title": "Chamada final",
        "draft_text": "Siga o perfil para acompanhar a serie completa.",
    })
    return drafts


def outline() -> list[dict[str, object]]:
    """A seven-slide outline (the outline phase never calls a model here)."""
    return [
        {"slide_index": index, "title": f"Slide {index}", "key_points": []}
        for index in range(1, _SLIDES + 1)
    ]


class DraftingModel:
    """Spy for every drafting-model entry point; records the notes it got."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []
        self.retries: list[int] = []
        self.fail_next = False
        self.content_ensures = 0

    async def __call__(
        self, _agent: object, params: SlideDraftGenerationParams
    ) -> list[dict[str, object]]:
        self.calls.append(list(params.revision_notes or []))
        if self.fail_next:
            self.fail_next = False
            raise ValueError(ERR_INVALID_JSON)
        return drafts_for(len(self.calls))

    async def retry(self, slide_index: int) -> dict[str, object] | None:
        self.retries.append(slide_index)
        return None


class _CountingRunner(PhaseArtifactRunner):
    """Real runner that counts content ensures (each may call the LLM)."""

    def __init__(self, config: PhaseArtifactRunnerConfig, model: DraftingModel) -> None:
        super().__init__(config)
        self._model = model

    async def ensure_for_phase(self, state: CarouselWorkflowState) -> dict[str, object]:
        if state.get("current_phase") == PHASE_CONTENT:
            self._model.content_ensures += 1
        return await super().ensure_for_phase(state)


class _Orchestrator:
    """The one attribute ``prepare_resume_workflow`` reads."""

    def __init__(self, engine: CarouselWorkflowEngine) -> None:
        self.engine = engine


@dataclass(frozen=True)
class Review:
    """One review decision, as the HTTP route or the autopilot sends it."""

    action: str
    feedback: str = ""
    structured: dict[str, object] | None = None


def build_engine(model: DraftingModel) -> CarouselWorkflowEngine:
    """Engine + real artifact runner whose only model is ``model``."""
    runner = _CountingRunner(
        PhaseArtifactRunnerConfig(
            outline_agent=MagicMock(),
            content_agent=MagicMock(),
            llm=MagicMock(),
            workflow_input=EditorialWorkflowStartInput(
                topic="Agentes", audience="devs", brief="b", sources=[]
            ),
            slide_draft_retry=model.retry,
        ),
        model,
    )
    return CarouselWorkflowEngine(checkpointer=InMemorySaver(), artifact_runner=runner)


async def park_at_content(engine: CarouselWorkflowEngine) -> None:
    """Start, then approve research and outline: the graph parks at content."""
    await engine.start(
        PROJECT_ID,
        {"topic": "Agentes"},
        research_findings=[{"source": "report", "key_points": ["risk"]}],
        outline=outline(),
    )
    for _ in range(2):
        await engine.resume(PROJECT_ID, {"action": REVIEW_ACTION_APPROVE})


async def state_of(engine: CarouselWorkflowEngine) -> CarouselWorkflowState:
    """The workflow state the API serves."""
    state = await engine.get_state(PROJECT_ID)
    assert state is not None
    return state


async def review(engine: CarouselWorkflowEngine, decision: Review) -> None:
    """Resume like ``EditorialWorkflowService.resume_workflow`` does."""
    await prepare_resume_workflow(
        ResumeContext(
            orchestrator=cast(CarouselEditorialOrchestrator, _Orchestrator(engine)),
            project_id=PROJECT_ID,
            action=decision.action,
            prior=await state_of(engine),
            feedback=decision.feedback,
            structured_feedback=decision.structured,
        )
    )
    graph_action = (
        REVIEW_ACTION_REJECT
        if decision.action == REVIEW_ACTION_REVISE
        else decision.action
    )
    human_input: dict[str, object] = {
        "action": graph_action,
        "reviewer_id": "owner",
        "feedback": decision.feedback,
    }
    if decision.structured:
        human_input[STRUCTURED_FEEDBACK_KEY] = decision.structured
    await engine.resume(PROJECT_ID, human_input)


def localized_slide(state: CarouselWorkflowState, index: int) -> dict[str, object]:
    """The localized slide ``index`` of ``state``."""
    slides = state.get("localized_slides") or []
    return next(slide for slide in slides if slide.get("slide_index") == index)


def edited_slide(state: CarouselWorkflowState, index: int) -> dict[str, object]:
    """Slide ``index`` with a hand-fixed PT and EN body (a manual fix)."""
    slide = localized_slide(state, index)
    pt = dict(cast(dict[str, object], slide["presentation_pt"]))
    en = dict(cast(dict[str, object], slide["presentation_en"]))
    pt["body"] = f"Texto corrigido a mao pelo dono no slide {index}."
    en["body"] = f"Copy fixed by hand by the owner on slide {index}."
    return {"slide_index": index, "presentation_pt": pt, "presentation_en": en}


def manual_fixes(*slides: dict[str, object]) -> Review:
    """The "Submit manual fixes": an edits-only revise, no feedback."""
    return Review(
        action=REVIEW_ACTION_REVISE,
        structured={STRUCTURED_FEEDBACK_EDITED_SLIDES_KEY: list(slides)},
    )
