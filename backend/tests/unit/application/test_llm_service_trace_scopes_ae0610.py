"""Each LLMService caller says which phase, agent and content its call belongs to.

Gherkin: tests/features/llm_service_params_ae0610.feature
The LLM doubles stand in for the adapter, which opens the trace a call names.
Nothing is exported: the Langfuse client, where one is needed, is the test collector.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rag_backend.api.dependencies import conversation as conversation_deps
from rag_backend.application.services.blog_post_ai_service import (
    BlogPostAIService,
    _ImproveInput,
    _SuggestInput,
)
from rag_backend.domain.models import CarouselProject, CarouselStatus
from rag_backend.domain.protocols import LlmCallTrace
from tests.langfuse_trace_fakes import (
    RecordedTrace,
    TraceCollector,
    install_trace_collector,
)
from tests.unit.application.carousel_refinement_helpers import (
    make_refinement_service_with_mocks,
    make_test_slide,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

_ANSWER = "the answer"
_MESSAGES = [{"role": "user", "content": "the prompt"}]


@dataclass
class _TracingLlm:
    """An LLM double that records the active trace of each call."""

    collector: TraceCollector
    traces: list[RecordedTrace | None] = field(default_factory=list)

    async def generate(
        self, messages: list[dict[str, str]], temperature: float = 0.7
    ) -> str:
        self.traces.append(self.collector.current())
        return _ANSWER

    @property
    def chat_model(self) -> MagicMock:
        return MagicMock()


@pytest.fixture
def collector(monkeypatch: pytest.MonkeyPatch) -> TraceCollector:
    return install_trace_collector(monkeypatch)


def _attributes(trace: RecordedTrace | None) -> tuple[object, object, object]:
    assert trace is not None
    metadata = trace.span_metadata
    return metadata["phase"], metadata["agent_name"], metadata["content_type"]


def _project(tmp_path: Path) -> CarouselProject:
    return CarouselProject(
        topic="T",
        audience="A",
        niche="N",
        status=CarouselStatus.COMPLETED,
        output_dir=str(tmp_path),
    )


def _refinement(project: CarouselProject) -> tuple[MagicMock, AsyncMock]:
    agent, repo, _, _ = make_refinement_service_with_mocks()
    repo.get_project_by_id = AsyncMock(return_value=project)
    repo.get_slides_by_project = AsyncMock(return_value=[make_test_slide(1)])
    generate = AsyncMock(return_value=_ANSWER)
    agent._llm.generate = generate
    return agent, generate


# Scenario: A blog AI call is traced with its phase, agent and content type
async def test_a_blog_suggest_is_traced(collector: TraceCollector) -> None:
    llm = _TracingLlm(collector)

    await BlogPostAIService(llm).suggest(_SuggestInput(text="t", action="improve"))

    assert _attributes(llm.traces[0]) == ("ai_suggest", "blog_ai", "blog_post")


# Scenario: A blog AI call is traced with its phase, agent and content type
async def test_a_blog_improve_is_traced(collector: TraceCollector) -> None:
    llm = _TracingLlm(collector)

    await BlogPostAIService(llm).improve(
        _ImproveInput(db=MagicMock(), text="t", action="improve")
    )

    assert _attributes(llm.traces[0]) == ("ai_improve", "blog_ai", "blog_post")


# Scenario: A refinement names its own phase
@patch("rag_backend.application.services.carousel_refinement.run_image_one")
async def test_a_refined_slide_image_names_its_phase(
    _image: AsyncMock, tmp_path: Path
) -> None:
    project = _project(tmp_path)
    agent, generate = _refinement(project)

    await agent.regenerate_slide_image(project.id, 1, "make it brighter")

    assert generate.await_args.kwargs["trace"] == LlmCallTrace(
        phase="refine_image",
        agent_name="carousel_refinement",
        content_type="carousel",
        project_id=str(project.id),
    )


# Scenario: A refinement names its own phase
async def test_a_refined_carousel_design_names_its_phase(tmp_path: Path) -> None:
    project = _project(tmp_path)
    agent, generate = _refinement(project)

    await agent.refine_carousel_design(project.id, "more padding")

    assert generate.await_args.kwargs["trace"] == LlmCallTrace(
        phase="refine_design",
        agent_name="carousel_refinement",
        content_type="carousel",
        project_id=str(project.id),
    )


# Scenario: A conversation title names its own phase
async def test_a_conversation_title_names_its_phase(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    generate = AsyncMock(return_value=_ANSWER)
    container = MagicMock()
    container.llm_service.return_value.generate = generate
    monkeypatch.setattr(conversation_deps, "get_container", lambda: container)

    title = await conversation_deps.get_conversation_title_generator()(_MESSAGES)

    assert title == _ANSWER
    generate.assert_awaited_once_with(
        _MESSAGES,
        trace=LlmCallTrace(
            phase="conversation_title",
            agent_name="conversation_title",
            content_type="chat",
        ),
    )
