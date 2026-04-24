"""Unit tests for CarouselAgent with mocked dependencies."""

import asyncio
import contextlib
import json
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from rag_backend.application.services.carousel_agent import CarouselAgent, SlideData
from rag_backend.application.services.image_provider_registry import (
    ImageProviderRegistry,
)
from rag_backend.domain.models import (
    CarouselProject,
    CarouselStatus,
    CarouselTheme,
    ResearchSource,
    ResearchSourceType,
)


@pytest.fixture
def mock_repository():
    """Create a mock carousel repository."""
    repo = AsyncMock()
    repo.create_project = AsyncMock()
    repo.get_project_by_id = AsyncMock()
    repo.update_project = AsyncMock()
    repo.delete_project = AsyncMock()
    repo.create_slide = AsyncMock()
    repo.get_slides_by_project = AsyncMock()
    repo.update_slide = AsyncMock()
    repo.delete_slides_by_project = AsyncMock()
    repo.create_research_source = AsyncMock()
    repo.get_sources_by_project = AsyncMock()
    repo.count = AsyncMock(return_value=0)
    return repo


@pytest.fixture
def mock_llm_service():
    """Create a mock LLM service."""
    llm = AsyncMock()
    llm.generate = AsyncMock()
    llm.generate_stream = AsyncMock()
    return llm


@pytest.fixture
def mock_research_tool():
    """Create a mock research tool."""
    tool = AsyncMock()
    tool.search_web = AsyncMock(return_value=[])
    tool.scrape_url = AsyncMock(return_value="")
    return tool


@pytest.fixture
def mock_image_service():
    """Create a mock image generation service."""
    service = AsyncMock()
    service.generate_image = AsyncMock(return_value="/path/to/image.jpg")
    return service


@pytest.fixture
def mock_export_service():
    """Create a mock export service."""
    service = AsyncMock()
    service.export_slides = AsyncMock(return_value=["/path/slide_1.jpg", "/path/slide_2.jpg"])
    return service


@pytest.fixture
def sample_project():
    """Create a sample carousel project."""
    project_id = uuid4()
    project = CarouselProject(
        topic="Machine Learning Basics",
        audience="Beginners",
        niche="AI Education",
        theme=CarouselTheme.AI_COMPETITION,
        id=project_id,
    )
    project.set_title(title="Master ML in 6 Slides", subtitle="A beginner's guide")
    return project


@pytest.fixture
def sample_research_source(sample_project):
    """Create a sample research source."""
    return ResearchSource(
        project_id=sample_project.id,
        source_url="https://example.com/ml",
        source_type=ResearchSourceType.BLOG,
        title="ML Basics",
        extracted_content="Machine learning content...",
    )


def build_agent(
    mock_repository,
    mock_llm_service,
    mock_research_tool,
    mock_image_service,
    mock_export_service,
):
    """Build a CarouselAgent with mocked dependencies."""
    registry = ImageProviderRegistry(
        gemini_service=mock_image_service,
        openai_service=mock_image_service,
    )
    return CarouselAgent(
        repository=mock_repository,
        llm_service=mock_llm_service,
        research_tool=mock_research_tool,
        image_registry=registry,
        export_service=mock_export_service,
        output_base_dir="./tmp/test_carousels",
    )


@pytest.mark.unit
class TestCarouselAgent:
    """Tests for CarouselAgent."""

    async def test_execute_pipeline_project_not_found(
        self,
        mock_repository,
        mock_llm_service,
        mock_research_tool,
        mock_image_service,
        mock_export_service,
    ):
        """Should raise ValueError when project does not exist."""
        mock_repository.get_project_by_id.return_value = None

        agent = build_agent(
            mock_repository,
            mock_llm_service,
            mock_research_tool,
            mock_image_service,
            mock_export_service,
        )

        with pytest.raises(ValueError, match="not found"):
            await agent.execute_pipeline(uuid4())

    async def test_execute_pipeline_marks_project_researching(
        self,
        mock_repository,
        mock_llm_service,
        mock_research_tool,
        mock_image_service,
        mock_export_service,
        sample_project,
    ):
        """Should update project status to RESEARCHING at start of pipeline."""
        call_order = []

        def track_update(project):
            call_order.append(project.status)
            return project

        mock_repository.get_project_by_id.return_value = sample_project
        mock_repository.update_project.side_effect = track_update
        mock_research_tool.search_web.return_value = []
        mock_llm_service.generate.return_value = json.dumps(
            {
                "title": "T",
                "subtitle": "S",
                "slides": [
                    {"number": 1, "type": "intro", "heading": "H", "body": "B"},
                ],
                "blog_markdown": "",
            }
        )

        agent = build_agent(
            mock_repository,
            mock_llm_service,
            mock_research_tool,
            mock_image_service,
            mock_export_service,
        )

        await agent.execute_pipeline(sample_project.id)

        assert CarouselStatus.RESEARCHING in call_order

    async def test_execute_pipeline_marks_project_failed_on_error(
        self,
        mock_repository,
        mock_llm_service,
        mock_research_tool,
        mock_image_service,
        mock_export_service,
        sample_project,
    ):
        """Should mark project as FAILED when pipeline raises exception."""
        mock_repository.get_project_by_id.return_value = sample_project
        mock_repository.update_project.return_value = sample_project
        mock_research_tool.search_web.side_effect = RuntimeError("Network error")

        agent = build_agent(
            mock_repository,
            mock_llm_service,
            mock_research_tool,
            mock_image_service,
            mock_export_service,
        )

        with pytest.raises(RuntimeError, match="Network error"):
            await agent.execute_pipeline(sample_project.id)

        update_calls = [call.args[0] for call in mock_repository.update_project.call_args_list]
        failed_found = any(p.status == CarouselStatus.FAILED for p in update_calls)
        assert failed_found

    async def test_phase1_research_creates_sources(
        self,
        mock_repository,
        mock_llm_service,
        mock_research_tool,
        mock_image_service,
        mock_export_service,
        sample_project,
    ):
        """Should create research sources from search results."""
        mock_research_tool.search_web.return_value = [
            {"url": "https://example.com/1", "title": "Result 1"},
            {"url": "https://example.com/2", "title": "Result 2"},
        ]
        mock_repository.create_research_source.return_value = ResearchSource(
            project_id=sample_project.id,
            source_url="https://example.com/1",
            source_type=ResearchSourceType.BLOG,
        )

        agent = build_agent(
            mock_repository,
            mock_llm_service,
            mock_research_tool,
            mock_image_service,
            mock_export_service,
        )

        sources = await agent._phase1_research(sample_project, [])

        assert mock_research_tool.search_web.called
        assert mock_repository.create_research_source.called

    async def test_phase2_3_content_parses_llm_json(
        self,
        mock_repository,
        mock_llm_service,
        mock_research_tool,
        mock_image_service,
        mock_export_service,
        sample_project,
    ):
        """Should parse slide data from bilingual LLM JSON response."""
        llm_response = json.dumps(
            {
                "title_pt": "Titulo Otimizado",
                "subtitle_pt": "Subtitulo",
                "slides": [
                    {
                        "number": 1,
                        "type": "intro",
                        "heading": "Intro Heading",
                        "body": "Intro Body",
                        "image_prompt": "A comic style intro image",
                    },
                    {
                        "number": 2,
                        "type": "content",
                        "heading": "Content Heading",
                        "body": "Content Body",
                        "image_prompt": "A comic style content image",
                    },
                ],
                "blog_pt": "# Blog PT\n\nConteudo em portugues.",
                "blog_en": "# Blog EN\n\nContent in English.",
            }
        )

        mock_llm_service.generate.return_value = llm_response

        agent = build_agent(
            mock_repository,
            mock_llm_service,
            mock_research_tool,
            mock_image_service,
            mock_export_service,
        )

        slides_data, blog_markdown = await agent._phase2_3_content(sample_project, [])

        assert len(slides_data) == 2
        assert slides_data[0].heading == "Intro Heading"
        assert slides_data[1].slide_type == "content"
        assert "Blog PT" in blog_markdown

    async def test_phase2_3_content_caps_features_at_four(
        self,
        mock_repository,
        mock_llm_service,
        mock_research_tool,
        mock_image_service,
        mock_export_service,
        sample_project,
    ):
        """LLM-emitted features array is truncated to 4 items max.

        The .feature-grid CSS overflows the slide footer past 4 items, so
        the agent defensively slices regardless of what the prompt asked.
        """
        oversized = [
            {"icon": "🧠", "title": f"Item {i}", "body": f"Body {i}"}
            for i in range(1, 7)  # 6 items
        ]
        llm_response = json.dumps(
            {
                "title_pt": "Titulo",
                "slides": [
                    {
                        "number": 5,
                        "type": "closing",
                        "heading": "Closing",
                        "body": "Intro line",
                        "features": oversized,
                    },
                ],
                "blog_pt": "# Blog",
                "blog_en": "# Blog EN",
            }
        )
        mock_llm_service.generate.return_value = llm_response
        agent = build_agent(
            mock_repository,
            mock_llm_service,
            mock_research_tool,
            mock_image_service,
            mock_export_service,
        )

        slides_data, _ = await agent._phase2_3_content(sample_project, [])

        assert slides_data[0].features is not None
        assert len(slides_data[0].features) == 4
        assert slides_data[0].features[0]["title"] == "Item 1"
        assert slides_data[0].features[3]["title"] == "Item 4"

    async def test_phase2_3_content_raises_on_invalid_json(
        self,
        mock_repository,
        mock_llm_service,
        mock_research_tool,
        mock_image_service,
        mock_export_service,
        sample_project,
    ):
        """LLM returning non-JSON must surface an error, not silently degrade.

        The old behavior (fallback to a single stub slide + empty blog + mark
        project `completed`) masked real failures — the content phase must
        raise so the pipeline marks the project `failed`.
        """
        mock_llm_service.generate.return_value = "not valid json"

        agent = build_agent(
            mock_repository,
            mock_llm_service,
            mock_research_tool,
            mock_image_service,
            mock_export_service,
        )

        with pytest.raises(ValueError, match="non-JSON"):
            await agent._phase2_3_content(sample_project, [])

    async def test_phase2_3_content_tolerates_markdown_fences(
        self,
        mock_repository,
        mock_llm_service,
        mock_research_tool,
        mock_image_service,
        mock_export_service,
        sample_project,
    ):
        """Anthropic often wraps JSON in ```json fences — parsing must handle that."""
        payload = {
            "slides": [
                {"number": 1, "type": "intro", "heading": "H", "body": "B"},
            ],
            "blog_pt": "# Blog",
        }
        mock_llm_service.generate.return_value = (
            f"Sure, here you go:\n```json\n{json.dumps(payload)}\n```\nDone."
        )

        agent = build_agent(
            mock_repository,
            mock_llm_service,
            mock_research_tool,
            mock_image_service,
            mock_export_service,
        )

        slides_data, blog_markdown = await agent._phase2_3_content(sample_project, [])

        assert len(slides_data) == 1
        assert slides_data[0].heading == "H"
        assert blog_markdown == "# Blog"

    async def test_phase2_3_content_sets_blog_translations(
        self,
        mock_repository,
        mock_llm_service,
        mock_research_tool,
        mock_image_service,
        mock_export_service,
        sample_project,
    ):
        """Should set blog_translations on project from bilingual response."""
        llm_response = json.dumps(
            {
                "title_pt": "Titulo PT",
                "subtitle_pt": "Sub PT",
                "slides": [
                    {"number": 1, "type": "intro", "heading": "H", "body": "B"},
                ],
                "blog_pt": "# Blog PT\n\nConteudo.",
                "blog_en": "# Blog EN\n\nContent.",
            }
        )
        mock_llm_service.generate.return_value = llm_response

        agent = build_agent(
            mock_repository,
            mock_llm_service,
            mock_research_tool,
            mock_image_service,
            mock_export_service,
        )

        await agent._phase2_3_content(sample_project, [])

        assert sample_project.blog_translations is not None
        assert "pt" in sample_project.blog_translations
        assert "en" in sample_project.blog_translations
        assert sample_project.blog_markdown is not None

    async def test_phase4_design_generates_html(
        self,
        mock_repository,
        mock_llm_service,
        mock_research_tool,
        mock_image_service,
        mock_export_service,
        sample_project,
    ):
        """Should generate HTML carousel from slide data and set design tokens."""
        slides = [
            SlideData(
                slide_number=1,
                slide_type="intro",
                heading="Intro",
                body="Body",
            ),
        ]

        agent = build_agent(
            mock_repository,
            mock_llm_service,
            mock_research_tool,
            mock_image_service,
            mock_export_service,
        )

        html = agent._phase4_design(sample_project, slides)

        assert "<!DOCTYPE html>" in html
        assert "Intro" in html
        assert sample_project.primary_color is not None
        assert sample_project.design_tokens is not None
        assert sample_project.design_tokens["colors"]["primary"] is not None

    async def test_phase5_images_skips_content_slides_without_prompt(
        self,
        mock_repository,
        mock_llm_service,
        mock_research_tool,
        mock_image_service,
        mock_export_service,
        sample_project,
        tmp_path,
    ):
        """Should not generate images for slides without image_prompt."""
        slides = [
            SlideData(
                slide_number=1,
                slide_type="content",
                heading="H",
                body="B",
                image_prompt=None,
            ),
        ]

        agent = build_agent(
            mock_repository,
            mock_llm_service,
            mock_research_tool,
            mock_image_service,
            mock_export_service,
        )

        await agent._phase5_images(sample_project, slides, tmp_path)

        assert not mock_image_service.generate_image.called

    async def test_phase7_caption_generates_text(
        self,
        mock_repository,
        mock_llm_service,
        mock_research_tool,
        mock_image_service,
        mock_export_service,
        sample_project,
    ):
        """Should generate caption from LLM."""
        mock_llm_service.generate.return_value = "Great carousel! #ML #AI"

        slides = [
            SlideData(slide_number=1, slide_type="intro", heading="Intro", body="B"),
            SlideData(slide_number=2, slide_type="content", heading="Content", body="B"),
        ]

        agent = build_agent(
            mock_repository,
            mock_llm_service,
            mock_research_tool,
            mock_image_service,
            mock_export_service,
        )

        caption = await agent._phase7_caption(sample_project, slides)

        assert caption == "Great carousel! #ML #AI"
        assert mock_llm_service.generate.called

    async def test_resolve_theme_auto_returns_default(
        self,
        mock_repository,
        mock_llm_service,
        mock_research_tool,
        mock_image_service,
        mock_export_service,
        sample_project,
    ):
        """Should return ai_competition theme when AUTO is selected."""
        sample_project.theme = CarouselTheme.AUTO

        agent = build_agent(
            mock_repository,
            mock_llm_service,
            mock_research_tool,
            mock_image_service,
            mock_export_service,
        )

        theme = agent._resolve_theme(sample_project)

        assert theme["primary"] == "#3b82f6"
        assert theme["accent"] == "#f59e0b"

    async def test_resolve_theme_specific_theme(
        self,
        mock_repository,
        mock_llm_service,
        mock_research_tool,
        mock_image_service,
        mock_export_service,
        sample_project,
    ):
        """Should return correct theme when specific theme is selected."""
        sample_project.theme = CarouselTheme.CYBERSECURITY

        agent = build_agent(
            mock_repository,
            mock_llm_service,
            mock_research_tool,
            mock_image_service,
            mock_export_service,
        )

        theme = agent._resolve_theme(sample_project)

        assert theme["primary"] == "#ef4444"
        assert theme["accent"] == "#00d4ff"

    async def test_slide_data_dataclass_defaults(
        self,
    ):
        """SlideData should have None as default for image_prompt."""
        slide = SlideData(
            slide_number=1,
            slide_type="intro",
            heading="H",
            body="B",
        )

        assert slide.image_prompt is None

    async def test_start_pipeline_creates_background_task(
        self,
        mock_repository,
        mock_llm_service,
        mock_research_tool,
        mock_image_service,
        mock_export_service,
        sample_project,
    ):
        """Given no running task, when start_pipeline is called,
        then a background asyncio.Task is created."""
        mock_repository.get_project_by_id = AsyncMock(return_value=sample_project)
        agent = build_agent(
            mock_repository,
            mock_llm_service,
            mock_research_tool,
            mock_image_service,
            mock_export_service,
        )
        thread_id = agent._thread_id(sample_project.id)

        # Clear any previous tasks
        agent._tasks.pop(thread_id, None)

        agent.start_pipeline(sample_project.id, seed_urls=None)

        assert thread_id in agent._tasks
        task = agent._tasks[thread_id]
        assert isinstance(task, asyncio.Task)
        # Clean up
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    async def test_start_pipeline_is_idempotent(
        self,
        mock_repository,
        mock_llm_service,
        mock_research_tool,
        mock_image_service,
        mock_export_service,
        sample_project,
    ):
        """Given a running task, when start_pipeline is called again,
        then it is a no-op and the original task is preserved."""
        mock_repository.get_project_by_id = AsyncMock(return_value=sample_project)
        agent = build_agent(
            mock_repository,
            mock_llm_service,
            mock_research_tool,
            mock_image_service,
            mock_export_service,
        )
        thread_id = agent._thread_id(sample_project.id)

        # Clear any previous tasks
        agent._tasks.pop(thread_id, None)

        agent.start_pipeline(sample_project.id, seed_urls=None)
        first_task = agent._tasks[thread_id]

        agent.start_pipeline(sample_project.id, seed_urls=None)
        second_task = agent._tasks[thread_id]

        assert first_task is second_task
        # Clean up
        first_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await first_task

    async def test_run_graph_producer_uses_session_maker_when_provided(
        self,
        mock_repository,
        mock_llm_service,
        mock_research_tool,
        mock_image_service,
        mock_export_service,
        sample_project,
    ):
        """Given a session_maker, when _run_graph_producer runs,
        then it creates a fresh session and repository for the background
        task instead of reusing the request-scoped one."""
        mock_repository.get_project_by_id = AsyncMock(return_value=sample_project)

        session_maker = MagicMock()
        session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_repository)
        session_maker.return_value.__aexit__ = AsyncMock(return_value=False)

        registry = ImageProviderRegistry(
            gemini_service=mock_image_service,
            openai_service=mock_image_service,
        )
        agent = CarouselAgent(
            repository=mock_repository,
            llm_service=mock_llm_service,
            research_tool=mock_research_tool,
            image_registry=registry,
            export_service=mock_export_service,
            output_base_dir="./tmp/test_carousels",
            session_maker=session_maker,
            repository_factory=lambda _session: mock_repository,
        )

        # Patch _run_graph_body so we don't need to mock the entire graph
        body_calls: list = []

        async def capture_body(project_id, seed_urls, queue, repo):
            body_calls.append(repo)
            await queue.put({"node": "start", "status": "pending", "phase_progress": None})
            await queue.put({"node": "end", "status": "completed", "phase_progress": None})

        agent._run_graph_body = capture_body

        queue: asyncio.Queue[dict] = asyncio.Queue()
        await agent._run_graph_producer(sample_project.id, None, queue)

        assert session_maker.called
        # _run_graph_body should have been called with the repo from the factory
        assert len(body_calls) == 1
        assert body_calls[0] is mock_repository
