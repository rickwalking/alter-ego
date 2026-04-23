"""Unit tests for the carousel LangGraph pipeline.

Scenarios (see features/carousel_graph.feature):
- Given a project with images enabled, the graph runs 9 nodes end-to-end.
- Given a project with images disabled, the graph skips the image node.
- Given a checkpointer, the compiled graph accepts a thread_id config.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from rag_backend.application.services.carousel.graph import (
    NODE_IMAGE_WORKER,
    CarouselDeps,
    build_graph,
)
from rag_backend.application.services.carousel.state import PipelineState
from rag_backend.application.services.carousel_template import CarouselTemplateBuilder
from rag_backend.application.services.image_provider_registry import ImageProviderRegistry
from rag_backend.domain.models import CarouselProject, CarouselStatus


def _content_response() -> str:
    return json.dumps(
        {
            "title_pt": "Título PT",
            "subtitle_pt": "Sub PT",
            "slides": [
                {
                    "number": 1,
                    "type": "intro",
                    "heading": "H1",
                    "body": "B1",
                    "image_prompt": "hero scene 1",
                },
                {
                    "number": 2,
                    "type": "content",
                    "heading": "H2",
                    "body": "B2",
                    "image_prompt": "hero scene 2",
                },
            ],
            "slides_en": [
                {"number": 1, "heading": "EN H1", "body": "EN B1"},
                {"number": 2, "heading": "EN H2", "body": "EN B2"},
            ],
            "blog_pt": "# Blog",
            "blog_en": "# Blog EN",
        }
    )


def _make_deps(
    *, generate_images: bool, tmp_path: Path
) -> tuple[CarouselDeps, CarouselProject, AsyncMock]:
    project = CarouselProject(
        topic="T",
        audience="A",
        niche="N",
        status=CarouselStatus.PENDING,
        generate_images=generate_images,
    )

    repo = AsyncMock()
    repo.update_project = AsyncMock(side_effect=lambda p: p)
    repo.create_slide = AsyncMock(side_effect=lambda s: s)
    repo.update_slide = AsyncMock(side_effect=lambda s: s)
    repo.get_slides_by_project = AsyncMock(return_value=[])
    repo.create_research_source = AsyncMock(side_effect=lambda s: s)

    llm = AsyncMock()
    llm.generate = AsyncMock(side_effect=[
        '{"title_pt": "T", "subtitle_pt": "S"}',
        _content_response(),
        "caption text",
    ])

    research_tool = AsyncMock()
    research_tool.search_web = AsyncMock(return_value=[])
    research_tool.scrape_url = AsyncMock(return_value="scraped")

    image_service = AsyncMock()
    image_service.generate_image = AsyncMock()
    registry = ImageProviderRegistry(
        gemini_service=image_service, openai_service=image_service
    )

    export = AsyncMock()
    export.export_slides = AsyncMock(
        return_value=[str(tmp_path / "slide_1.jpg"), str(tmp_path / "slide_2.jpg")]
    )

    pdf_builder = MagicMock()
    pdf_builder.build = MagicMock(return_value=str(tmp_path / "carousel.pdf"))

    deps = CarouselDeps(
        repo=repo,
        llm=llm,
        research_tool=research_tool,
        image_registry=registry,
        export=export,
        template=CarouselTemplateBuilder(),
        pdf_builder=pdf_builder,
    )
    return deps, project, image_service.generate_image


@pytest.mark.unit
class TestCarouselGraph:
    """End-to-end graph traversal against mock dependencies."""

    async def test_full_pipeline_with_images(self, tmp_path: Path) -> None:
        # Scenario: project with images enabled runs the image node.
        deps, project, generate_image = _make_deps(
            generate_images=True, tmp_path=tmp_path
        )
        graph = build_graph(deps)

        initial: PipelineState = {
            "project_id": project.id,
            "seed_urls": ["https://example.com"],
            "output_dir": str(tmp_path),
            "project": project,
        }
        final = await graph.ainvoke(initial)

        assert final["project"].status == CarouselStatus.COMPLETED
        assert final["caption"] == "caption text"
        assert len(final["slides_data"]) == 2
        assert generate_image.await_count == 2  # both slides got images

    async def test_pipeline_skips_images_when_disabled(self, tmp_path: Path) -> None:
        # Scenario: project with images disabled routes past the image node.
        deps, project, generate_image = _make_deps(
            generate_images=False, tmp_path=tmp_path
        )
        graph = build_graph(deps)

        initial: PipelineState = {
            "project_id": project.id,
            "seed_urls": [],
            "output_dir": str(tmp_path),
            "project": project,
        }
        final = await graph.ainvoke(initial)

        assert final["project"].status == CarouselStatus.COMPLETED
        assert generate_image.await_count == 0

    async def test_graph_accepts_checkpointer(self, tmp_path: Path) -> None:
        # Scenario: an InMemorySaver thread_id carries state between invocations.
        deps, project, _ = _make_deps(generate_images=False, tmp_path=tmp_path)
        saver = InMemorySaver()
        graph = build_graph(deps, checkpointer=saver)

        thread_id = f"carousel-{uuid4()}"
        config = {"configurable": {"thread_id": thread_id}}
        initial: PipelineState = {
            "project_id": project.id,
            "seed_urls": [],
            "output_dir": str(tmp_path),
            "project": project,
        }
        await graph.ainvoke(initial, config=config)

        snapshot = await graph.aget_state(config)
        assert snapshot.values["project"].status == CarouselStatus.COMPLETED
        assert NODE_IMAGE_WORKER not in {step.name for step in snapshot.tasks}

    async def test_image_worker_retries_on_transient_failure(
        self, tmp_path: Path
    ) -> None:
        # Scenario: the image API fails on first call, succeeds on retry.
        deps, project, generate_image = _make_deps(
            generate_images=True, tmp_path=tmp_path
        )
        call_count = {"n": 0}

        async def flaky_generate(*, prompt: str, output_path: str) -> None:
            call_count["n"] += 1
            # Fail the first attempt for each of the 2 slides, succeed after.
            if call_count["n"] in {1, 2}:
                raise ConnectionError("transient")

        generate_image.side_effect = flaky_generate

        graph = build_graph(deps)
        initial: PipelineState = {
            "project_id": project.id,
            "seed_urls": [],
            "output_dir": str(tmp_path),
            "project": project,
        }
        final = await graph.ainvoke(initial)

        assert final["project"].status == CarouselStatus.COMPLETED
        assert call_count["n"] >= 4  # 2 initial failures + 2 successful retries

    async def test_compiled_subagent_emits_summary(self, tmp_path: Path) -> None:
        # Scenario: a DeepAgents parent invokes the carousel subagent with a
        # JSON request message; the subagent returns an AIMessage summary.
        import json as _json

        from langchain_core.messages import HumanMessage

        from rag_backend.application.services.carousel.subagent import (
            build_carousel_subagent,
        )

        deps, project, _ = _make_deps(generate_images=False, tmp_path=tmp_path)
        deps.repo.get_project_by_id = AsyncMock(return_value=project)

        spec = build_carousel_subagent(deps, output_base_dir=str(tmp_path))
        assert spec["name"] == "generate_carousel"
        assert "description" in spec

        request_msg = HumanMessage(
            content=_json.dumps({"project_id": str(project.id), "seed_urls": []})
        )
        result = await spec["runnable"].ainvoke({"messages": [request_msg]})
        # Last message is the AI summary the parent gets as a ToolMessage.
        last = result["messages"][-1]
        assert "finished with status" in last.content
        assert str(project.id) in last.content

    async def test_compiled_subagent_rejects_bad_request(self, tmp_path: Path) -> None:
        from langchain_core.messages import HumanMessage

        from rag_backend.application.services.carousel.subagent import (
            build_carousel_subagent,
        )

        deps, _, _ = _make_deps(generate_images=False, tmp_path=tmp_path)
        spec = build_carousel_subagent(deps, output_base_dir=str(tmp_path))
        # Missing project_id
        result = await spec["runnable"].ainvoke(
            {"messages": [HumanMessage(content="{}")]}
        )
        assert "missing `project_id`" in result["messages"][-1].content

    async def test_stream_pipeline_yields_progress_events(
        self, tmp_path: Path
    ) -> None:
        # Scenario: stream_pipeline emits start/node/end events for each
        # completed node. Frontend consumes these as SSE data lines.
        from rag_backend.application.services.carousel_agent import CarouselAgent

        deps, project, _ = _make_deps(generate_images=False, tmp_path=tmp_path)
        deps.repo.get_project_by_id = AsyncMock(return_value=project)
        agent = CarouselAgent(
            repository=deps.repo,
            llm_service=deps.llm,
            research_tool=deps.research_tool,
            image_registry=deps.image_registry,
            export_service=deps.export,
            pdf_slide_builder=deps.pdf_builder,
            output_base_dir=str(tmp_path),
        )

        events = [e async for e in agent.stream_pipeline(project.id, seed_urls=[])]

        assert events[0]["node"] == "start"
        assert events[-1]["node"] == "end"
        node_names = [e["node"] for e in events]
        assert "research" in node_names
        assert "finalize" in node_names

    async def test_stream_pipeline_resumes_from_checkpoint(
        self, tmp_path: Path
    ) -> None:
        # Scenario: an SSE reconnect on a project that already has a
        # checkpoint does not restart from phase 1. The stream resumes
        # where the previous run left off.
        from rag_backend.application.services.carousel_agent import CarouselAgent

        deps, project, generate_image = _make_deps(
            generate_images=True, tmp_path=tmp_path
        )
        deps.repo.get_project_by_id = AsyncMock(return_value=project)
        # Pre-seed slide JPGs so the image workers short-circuit.
        images_dir = tmp_path / str(project.id) / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        for n in (1, 2):
            (images_dir / f"slide_{n}.jpg").write_bytes(b"done")

        saver = InMemorySaver()
        agent = CarouselAgent(
            repository=deps.repo,
            llm_service=deps.llm,
            research_tool=deps.research_tool,
            image_registry=deps.image_registry,
            export_service=deps.export,
            pdf_slide_builder=deps.pdf_builder,
            output_base_dir=str(tmp_path),
            checkpointer=saver,
        )

        # First run establishes the checkpoint.
        await agent.execute_pipeline(project.id, seed_urls=[])
        pre_stream_calls = generate_image.await_count

        # Second call via stream_pipeline must pick up the same checkpoint
        # and not re-run expensive nodes (image_worker short-circuits).
        events = [e async for e in agent.stream_pipeline(project.id, seed_urls=[])]

        assert events[0]["node"] == "start"
        assert events[-1]["node"] == "end"
        # No additional image API calls on the idempotent reconnect.
        assert generate_image.await_count == pre_stream_calls

    async def test_resume_pipeline_replays_from_checkpoint(
        self, tmp_path: Path
    ) -> None:
        # Scenario: a pipeline crashes during images; resume finishes it
        # without re-running the expensive LLM calls that already happened.
        from rag_backend.application.services.carousel_agent import CarouselAgent

        deps, project, generate_image = _make_deps(
            generate_images=True, tmp_path=tmp_path
        )
        # Pre-seed slide JPGs as if phase 5 already succeeded.
        images_dir = tmp_path / str(project.id) / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        for n in (1, 2):
            (images_dir / f"slide_{n}.jpg").write_bytes(b"done")

        saver = InMemorySaver()
        agent = CarouselAgent(
            repository=deps.repo,
            llm_service=deps.llm,
            research_tool=deps.research_tool,
            image_registry=deps.image_registry,
            export_service=deps.export,
            pdf_slide_builder=deps.pdf_builder,
            output_base_dir=str(tmp_path),
            checkpointer=saver,
        )

        # Agent.resume_pipeline() needs get_project_by_id to return a
        # project — wire the mock for that.
        deps.repo.get_project_by_id = AsyncMock(return_value=project)

        # First invocation establishes the thread.
        await agent.execute_pipeline(project.id, seed_urls=[])
        pre_resume_calls = generate_image.await_count

        # Resume is a no-op since the thread finished — but should succeed.
        result = await agent.resume_pipeline(project.id)
        assert result.status == CarouselStatus.COMPLETED
        # No additional image API calls on the idempotent resume.
        assert generate_image.await_count == pre_resume_calls

    async def test_resume_requires_checkpointer(self, tmp_path: Path) -> None:
        from rag_backend.application.services.carousel_agent import CarouselAgent

        deps, project, _ = _make_deps(generate_images=False, tmp_path=tmp_path)
        deps.repo.get_project_by_id = AsyncMock(return_value=project)
        agent = CarouselAgent(
            repository=deps.repo,
            llm_service=deps.llm,
            research_tool=deps.research_tool,
            image_registry=deps.image_registry,
            export_service=deps.export,
            pdf_slide_builder=deps.pdf_builder,
            output_base_dir=str(tmp_path),
            checkpointer=None,
        )
        with pytest.raises(RuntimeError, match="checkpointer"):
            await agent.resume_pipeline(project.id)

    async def test_image_worker_skips_when_file_exists(self, tmp_path: Path) -> None:
        # Scenario: a pre-existing JPG (from a prior partial run) is not
        # regenerated — the worker short-circuits and reports 'done'.
        deps, project, generate_image = _make_deps(
            generate_images=True, tmp_path=tmp_path
        )
        # Pre-seed the target files as if a previous run completed them.
        images_dir = tmp_path / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        (images_dir / "slide_1.jpg").write_bytes(b"already-there")
        (images_dir / "slide_2.jpg").write_bytes(b"already-there")

        graph = build_graph(deps)
        initial: PipelineState = {
            "project_id": project.id,
            "seed_urls": [],
            "output_dir": str(tmp_path),
            "project": project,
        }
        final = await graph.ainvoke(initial)

        assert final["project"].status == CarouselStatus.COMPLETED
        assert generate_image.await_count == 0  # API never called
        assert all(r.get("skipped") for r in final["image_results"])

    async def test_persist_slides_is_idempotent_on_resume(self, tmp_path: Path) -> None:
        # Scenario: on resume, persist_slides_node updates existing slides
        # instead of crashing with a UNIQUE constraint violation.
        from uuid import uuid4

        from rag_backend.domain.models import CarouselSlide

        deps, project, _ = _make_deps(generate_images=False, tmp_path=tmp_path)

        existing_slide = CarouselSlide(
            id=uuid4(),
            project_id=project.id,
            slide_number=1,
            slide_type="intro",
            heading="Old H1",
            body="Old B1",
            image_prompt="old prompt",
            image_path="/old/path.jpg",
        )
        deps.repo.get_slides_by_project = AsyncMock(return_value=[existing_slide])

        graph = build_graph(deps)
        initial: PipelineState = {
            "project_id": project.id,
            "seed_urls": [],
            "output_dir": str(tmp_path),
            "project": project,
        }
        final = await graph.ainvoke(initial)

        assert final["project"].status == CarouselStatus.COMPLETED
        # Should update the existing slide, not try to create a new one.
        assert deps.repo.create_slide.await_count == 1  # only slide 2 is new
        assert deps.repo.update_slide.await_count == 1  # slide 1 updated
        updated = deps.repo.update_slide.await_args[0][0]
        assert updated.heading == "H1"  # new content from LLM response
        assert updated.image_path == "/old/path.jpg"  # preserved from existing
