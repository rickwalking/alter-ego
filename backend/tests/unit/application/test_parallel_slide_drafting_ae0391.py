"""AE-0391: parallel slide drafting (bounded, ordered) and per-role wiring.

Scenarios: see tests/features/llm_model_routing_ae0391.feature
"""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Callable
from typing import cast

import pytest

from rag_backend.agents.content_draft_agent import ContentDraftAgent
from rag_backend.application.services.carousel.bounded_gather import gather_bounded
from rag_backend.application.services.carousel.editorial_workflow_generators import (
    SlideDraftGenerationParams,
    generate_slide_drafts,
)
from rag_backend.application.services.carousel.editorial_workflow_service import (
    EditorialWorkflowConfig,
    EditorialWorkflowService,
)
from rag_backend.application.services.carousel.editorial_workflow_types import (
    ChatModelRoles,
    EditorialWorkflowStartInput,
)
from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
)
from rag_backend.domain.constants.carousel_workflow import PHASE_CONTENT
from rag_backend.infrastructure.cache.ai_response_cache import get_ai_response_cache
from rag_backend.infrastructure.config.llm_routing_constants import (
    LLM_ROLE_FAST,
    LLM_ROLE_REASONING,
    LLM_TAG_FALLBACK,
)
from rag_backend.infrastructure.external.routed_chat_model import RoutedChatModel
from tests.unit.llm_fakes_ae0391 import CallLog, FakeChat

SLIDE_COUNT = 7
# Deliberately unrelated bodies so the distinctness check never re-drafts.
BODIES = [
    "Agentes autônomos planejam tarefas longas com memória persistente.",
    "Custos de inferência caíram quando o roteamento escolheu modelos menores.",
    "Robôs industriais aprendem com demonstrações gravadas em vídeo.",
    "Segurança exige revisar permissões antes de liberar ferramentas externas.",
    "Bancos vetoriais híbridos combinam busca esparsa e densa no mesmo índice.",
    "Equipes pequenas entregam mais quando automatizam testes de regressão.",
    "Compiladores modernos otimizam laços usando instruções vetoriais SIMD.",
]
_SLIDE_RE = re.compile(r"Slide index: (\d+)")


def _outline() -> list[dict[str, object]]:
    return [
        {"slide_index": n, "title": f"Título {n}", "key_points": [f"ponto {n}"]}
        for n in range(1, SLIDE_COUNT + 1)
    ]


def _draft_json(slide: int) -> str:
    return json.dumps({
        "draft_text": BODIES[slide - 1],
        "confidence_score": 0.9,
        "sources_used": [],
        "long_form_notes": f"Notas {slide}",
    })


def _reply(bad_slide: int | None = None) -> Callable[[str], str]:
    def reply(prompt: str) -> str:
        if "not json" in prompt:
            return "not json"
        match = _SLIDE_RE.search(prompt)
        slide = int(match.group(1)) if match else 1
        return "not json" if slide == bad_slide else _draft_json(slide)

    return reply


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    get_ai_response_cache().clear()


# --- gather_bounded ----------------------------------------------------------


async def test_gather_bounded_keeps_order_and_respects_the_limit() -> None:
    # Scenario: slides are drafted concurrently and kept in slide order
    log = CallLog()

    async def work(value: int) -> int:
        log.in_flight += 1
        log.max_in_flight = max(log.max_in_flight, log.in_flight)
        await asyncio.sleep(0.01 * (SLIDE_COUNT - value))
        log.in_flight -= 1
        return value

    results = await gather_bounded([lambda v=v: work(v) for v in range(SLIDE_COUNT)], 4)

    assert results == list(range(SLIDE_COUNT))
    assert log.max_in_flight == 4


async def test_gather_bounded_settles_siblings_before_raising() -> None:
    # Scenario: a slide that still fails fails the phase after siblings settle
    finished: list[int] = []

    async def work(value: int) -> int:
        if value == 1:
            raise RuntimeError("boom")
        await asyncio.sleep(0.02)
        finished.append(value)
        return value

    with pytest.raises(RuntimeError, match="boom"):
        await gather_bounded([lambda v=v: work(v) for v in range(4)], 0)

    assert sorted(finished) == [0, 2, 3]


# --- generate_slide_drafts ---------------------------------------------------


class _RecordingAgent:
    """ContentDraftAgent stand-in recording sibling context and concurrency."""

    def __init__(self) -> None:
        self.log = CallLog()
        self.sibling_contexts: dict[int, str] = {}
        self.previous_drafts: dict[int, str] = {}

    async def draft_slide(
        self, slide_index: int, **kwargs: object
    ) -> dict[str, object]:
        self.log.in_flight += 1
        self.log.max_in_flight = max(self.log.max_in_flight, self.log.in_flight)
        self.sibling_contexts[slide_index] = str(kwargs["sibling_context"])
        self.previous_drafts[slide_index] = str(kwargs["previous_draft"])
        # Later slides finish first: order must still follow the outline.
        await asyncio.sleep(0.005 * (SLIDE_COUNT - slide_index))
        self.log.in_flight -= 1
        return {"draft_text": BODIES[slide_index - 1], "confidence_score": 0.9}


async def test_generate_slide_drafts_parallel_ordered_and_outline_context_only() -> (
    None
):
    # Scenario: a slide draft only sees sibling OUTLINE context
    agent = _RecordingAgent()

    drafts = await generate_slide_drafts(
        cast(ContentDraftAgent, agent),
        SlideDraftGenerationParams(outline=_outline(), concurrency=4),
    )

    assert [d["slide_index"] for d in drafts] == list(range(1, SLIDE_COUNT + 1))
    assert [d["draft_text"] for d in drafts] == BODIES
    assert agent.log.max_in_flight == 4
    context = agent.sibling_contexts[3]
    assert "Título 1" in context
    assert "Título 3" not in context
    assert all(body not in context for body in BODIES)
    assert set(agent.previous_drafts.values()) == {""}


async def test_generate_slide_drafts_default_concurrency_is_four() -> None:
    agent = _RecordingAgent()

    await generate_slide_drafts(
        cast(ContentDraftAgent, agent),
        SlideDraftGenerationParams(outline=_outline()),
    )

    assert agent.log.max_in_flight == 4


# --- integration: real editorial service, fake chat models -----------------------


def _roles(log: CallLog, bad_slide: int | None = None) -> ChatModelRoles:
    reasoning = RoutedChatModel(
        primary=FakeChat(model_name="reasoning-model", log=log),
        fallback=FakeChat(model_name="glm-fallback", log=log),
        role=LLM_ROLE_REASONING,
        timeout_seconds=5.0,
    )
    fast = RoutedChatModel(
        primary=FakeChat(
            model_name="fast-model", log=log, reply=_reply(bad_slide), delay=0.02
        ),
        fallback=FakeChat(
            model_name="glm-fallback", log=log, reply=_reply(None), delay=0.02
        ),
        role=LLM_ROLE_FAST,
        timeout_seconds=5.0,
    )
    return ChatModelRoles(reasoning=reasoning, fast=fast)


def _service(roles: ChatModelRoles) -> EditorialWorkflowService:
    return EditorialWorkflowService(EditorialWorkflowConfig(llm=roles))


async def _run_content_phase(service: EditorialWorkflowService) -> dict[str, object]:
    runner = service._orchestrator._artifact_runner.with_context(
        workflow_input=EditorialWorkflowStartInput(
            topic="IA", audience="devs", brief="b", sources=[]
        )
    )
    state = cast(
        CarouselWorkflowState,
        {"project_id": "p-1", "current_phase": PHASE_CONTENT, "outline": _outline()},
    )
    return await runner.ensure_for_phase(state)


def test_editorial_service_wires_each_task_to_its_role() -> None:
    # Scenario: the carousel pipeline uses the right role per task
    roles = _roles(CallLog())
    service = _service(roles)
    orchestrator = service._orchestrator
    runner = orchestrator._artifact_runner

    assert runner._outline_agent.llm is roles.reasoning
    assert orchestrator._source_agent.llm is roles.reasoning
    assert runner._content_agent.llm is roles.fast
    assert runner._llm is roles.fast
    assert service.chat_model is roles.fast
    assert runner._draft_concurrency == roles.draft_concurrency


def test_draft_concurrency_survives_with_context() -> None:
    roles = ChatModelRoles(reasoning=FakeChat(), fast=FakeChat(), draft_concurrency=2)
    runner = _service(roles)._orchestrator._artifact_runner

    assert runner.with_context()._draft_concurrency == 2


async def test_content_phase_drafts_in_parallel_on_the_fast_model() -> None:
    # Scenario: slides are drafted concurrently and kept in slide order
    log = CallLog()

    updates = await _run_content_phase(_service(_roles(log)))

    drafts = updates["slide_drafts"]
    assert isinstance(drafts, list)
    assert [d["slide_index"] for d in drafts] == list(range(1, SLIDE_COUNT + 1))
    assert set(log.models) == {"fast-model"}
    assert 2 <= log.max_in_flight <= 4
    assert all("role:fast" in tags for tags in log.tags)


async def test_one_failing_slide_is_retried_then_falls_back_alone() -> None:
    # Scenario: one failing slide does not redo the others
    log = CallLog()
    agent = ContentDraftAgent(llm=_roles(log, bad_slide=3).fast)

    drafts = await generate_slide_drafts(
        agent, SlideDraftGenerationParams(outline=_outline(), concurrency=4)
    )

    assert [d["draft_text"] for d in drafts] == BODIES
    # 7 first attempts + 1 repair for slide 3 on the primary, then 1 fallback call.
    assert log.models.count("fast-model") == SLIDE_COUNT + 1
    assert log.models.count("glm-fallback") == 1
    fallback_tags = [tags for tags in log.tags if LLM_TAG_FALLBACK in tags]
    assert len(fallback_tags) == 1
