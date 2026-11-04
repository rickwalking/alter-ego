"""Each LLMService caller runs in a trace that names its phase, agent and content.

Gherkin: tests/features/llm_service_params_ae0610.feature
The LLM double reads the active trace the way a LangChain generation attaches to
the active span. Nothing is exported: the Langfuse client is the test collector.
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
from rag_backend.application.services.linkedin_post_generator import (
    LinkedInPostGenerator,
)
from rag_backend.domain.models import CarouselProject, CarouselStatus
from rag_backend.infrastructure.langfuse_phase_trace import (
    current_generation_run_name,
    phase_trace,
)
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
    """An LLM double that records the trace and run name of each call."""

    collector: TraceCollector
    traces: list[RecordedTrace | None] = field(default_factory=list)
    run_names: list[str] = field(default_factory=list)

    async def generate(
        self, messages: list[dict[str, str]], temperature: float = 0.7
    ) -> str:
        self.traces.append(self.collector.current())
        self.run_names.append(current_generation_run_name())
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


# Scenario: A refined slide image prompt is traced
@patch("rag_backend.application.services.carousel_refinement.run_image_one")
async def test_a_refined_slide_image_prompt_is_traced(
    _image: AsyncMock, collector: TraceCollector, tmp_path: Path
) -> None:
    agent, repo, _, _ = make_refinement_service_with_mocks()
    project = _project(tmp_path)
    repo.get_project_by_id = AsyncMock(return_value=project)
    repo.get_slides_by_project = AsyncMock(return_value=[make_test_slide(1)])
    llm = _TracingLlm(collector)
    agent._llm = llm

    await agent.regenerate_slide_image(project.id, 1, "make it brighter")

    trace = llm.traces[0]
    assert _attributes(trace) == ("refine_image", "carousel_refinement", "carousel")
    assert trace is not None
    assert trace.span_metadata["project_id"] == str(project.id)


# Scenario: A refined carousel design is traced
async def test_a_refined_carousel_design_is_traced(
    collector: TraceCollector, tmp_path: Path
) -> None:
    agent, repo, _, _ = make_refinement_service_with_mocks()
    project = _project(tmp_path)
    repo.get_project_by_id = AsyncMock(return_value=project)
    repo.get_slides_by_project = AsyncMock(return_value=[make_test_slide(1)])
    llm = _TracingLlm(collector)
    agent._llm = llm

    await agent.refine_carousel_design(project.id, "more padding")

    trace = llm.traces[0]
    assert _attributes(trace) == ("refine_design", "carousel_refinement", "carousel")
    assert trace is not None
    assert trace.span_metadata["project_id"] == str(project.id)


# Scenario: A LinkedIn post is a named generation of the running phase
async def test_a_linkedin_post_is_a_named_generation(
    collector: TraceCollector,
) -> None:
    llm = _TracingLlm(collector)
    style = AsyncMock()
    style.get_samples = AsyncMock(return_value=[])
    project = CarouselProject(topic="T", audience="A", niche="N", blog_markdown="Blog.")

    with phase_trace({"phase": "content"}):
        await LinkedInPostGenerator(llm, style).generate(project, "pt")

    assert llm.run_names == ["carousel.content linkedin pt"]


# Scenario: A conversation title is traced
async def test_a_conversation_title_is_traced(
    collector: TraceCollector, monkeypatch: pytest.MonkeyPatch
) -> None:
    llm = _TracingLlm(collector)
    container = MagicMock()
    container.llm_service.return_value = llm
    monkeypatch.setattr(conversation_deps, "get_container", lambda: container)

    title = await conversation_deps.get_conversation_title_generator()(_MESSAGES)

    assert title == _ANSWER
    assert _attributes(llm.traces[0]) == (
        "conversation_title",
        "conversation_title",
        "chat",
    )
