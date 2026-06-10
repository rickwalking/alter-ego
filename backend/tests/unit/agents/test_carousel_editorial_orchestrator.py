"""Unit tests for CarouselEditorialOrchestrator.

Feature: Carousel editorial orchestration with subagent delegation
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rag_backend.agents.carousel_editorial_orchestrator import (
    CarouselEditorialOrchestrator,
)


class TestCarouselEditorialOrchestrator:
    """Tests for CarouselEditorialOrchestrator."""

    @pytest.fixture
    def orchestrator(self) -> CarouselEditorialOrchestrator:
        llm = MagicMock()
        return CarouselEditorialOrchestrator(llm=llm)

    # ------------------------------------------------------------------
    # __init__
    # ------------------------------------------------------------------

    @patch("rag_backend.agents.carousel_editorial_orchestrator.SourceSynthesisAgent")
    @patch("rag_backend.agents.carousel_editorial_orchestrator.CarouselWorkflowEngine")
    @patch("rag_backend.agents.carousel_editorial_orchestrator.PhaseArtifactRunner")
    def test_init_creates_artifact_runner_with_llm(
        self,
        mock_runner_cls: MagicMock,
        mock_engine_cls: MagicMock,
        mock_source_cls: MagicMock,
    ) -> None:
        """Given llm, when constructing, then PhaseArtifactRunner is created with llm."""
        llm = MagicMock()
        CarouselEditorialOrchestrator(llm=llm)

        mock_runner_cls.assert_called_once_with(
            outline_agent=mock_runner_cls.call_args.kwargs["outline_agent"],
            content_agent=mock_runner_cls.call_args.kwargs["content_agent"],
            llm=llm,
            image_registry=None,
        )
        call_kwargs = mock_runner_cls.call_args.kwargs
        assert call_kwargs["llm"] is llm
        assert call_kwargs["image_registry"] is None

    @patch("rag_backend.agents.carousel_editorial_orchestrator.SourceSynthesisAgent")
    @patch("rag_backend.agents.carousel_editorial_orchestrator.CarouselWorkflowEngine")
    @patch("rag_backend.agents.carousel_editorial_orchestrator.PhaseArtifactRunner")
    def test_init_creates_engine_with_runner_and_checkpointer(
        self,
        mock_runner_cls: MagicMock,
        mock_engine_cls: MagicMock,
        mock_source_cls: MagicMock,
    ) -> None:
        """Given checkpointer, when constructing, then engine is created with checkpointer and runner."""
        llm = MagicMock()
        checkpointer = MagicMock()
        CarouselEditorialOrchestrator(llm=llm, checkpointer=checkpointer)

        mock_engine_cls.assert_called_once()
        call_kwargs = mock_engine_cls.call_args.kwargs
        assert call_kwargs["checkpointer"] is checkpointer
        assert call_kwargs["artifact_runner"] is mock_runner_cls.return_value

    @patch("rag_backend.agents.carousel_editorial_orchestrator.SourceSynthesisAgent")
    @patch("rag_backend.agents.carousel_editorial_orchestrator.CarouselWorkflowEngine")
    @patch("rag_backend.agents.carousel_editorial_orchestrator.PhaseArtifactRunner")
    def test_init_creates_source_synthesis_agent(
        self,
        mock_runner_cls: MagicMock,
        mock_engine_cls: MagicMock,
        mock_source_cls: MagicMock,
    ) -> None:
        """Given llm, when constructing, then SourceSynthesisAgent is created with llm."""
        llm = MagicMock()
        CarouselEditorialOrchestrator(llm=llm)

        mock_source_cls.assert_called_once_with(llm=llm)

    @patch("rag_backend.agents.carousel_editorial_orchestrator.SourceSynthesisAgent")
    @patch("rag_backend.agents.carousel_editorial_orchestrator.CarouselWorkflowEngine")
    @patch("rag_backend.agents.carousel_editorial_orchestrator.PhaseArtifactRunner")
    def test_init_stores_llm_as_instance_attribute(
        self,
        mock_runner_cls: MagicMock,
        mock_engine_cls: MagicMock,
        mock_source_cls: MagicMock,
    ) -> None:
        """Given llm, when constructing, then _llm is stored on instance."""
        llm = MagicMock()
        orchestrator = CarouselEditorialOrchestrator(llm=llm)

        assert orchestrator._llm is llm

    @patch("rag_backend.agents.carousel_editorial_orchestrator.SourceSynthesisAgent")
    @patch("rag_backend.agents.carousel_editorial_orchestrator.CarouselWorkflowEngine")
    @patch("rag_backend.agents.carousel_editorial_orchestrator.PhaseArtifactRunner")
    def test_init_stores_artifact_runner_as_instance_attribute(
        self,
        mock_runner_cls: MagicMock,
        mock_engine_cls: MagicMock,
        mock_source_cls: MagicMock,
    ) -> None:
        """Given llm, when constructing, then _artifact_runner is stored on instance."""
        llm = MagicMock()
        orchestrator = CarouselEditorialOrchestrator(llm=llm)

        assert orchestrator._artifact_runner is mock_runner_cls.return_value

    @patch("rag_backend.agents.carousel_editorial_orchestrator.SourceSynthesisAgent")
    @patch("rag_backend.agents.carousel_editorial_orchestrator.CarouselWorkflowEngine")
    @patch("rag_backend.agents.carousel_editorial_orchestrator.PhaseArtifactRunner")
    def test_init_stores_engine_as_instance_attribute(
        self,
        mock_runner_cls: MagicMock,
        mock_engine_cls: MagicMock,
        mock_source_cls: MagicMock,
    ) -> None:
        """Given llm, when constructing, then _engine is stored on instance."""
        llm = MagicMock()
        orchestrator = CarouselEditorialOrchestrator(llm=llm)

        assert orchestrator._engine is mock_engine_cls.return_value

    @patch("rag_backend.agents.carousel_editorial_orchestrator.SourceSynthesisAgent")
    @patch("rag_backend.agents.carousel_editorial_orchestrator.CarouselWorkflowEngine")
    @patch("rag_backend.agents.carousel_editorial_orchestrator.PhaseArtifactRunner")
    def test_init_stores_source_agent_as_instance_attribute(
        self,
        mock_runner_cls: MagicMock,
        mock_engine_cls: MagicMock,
        mock_source_cls: MagicMock,
    ) -> None:
        """Given llm, when constructing, then _source_agent is stored on instance."""
        llm = MagicMock()
        orchestrator = CarouselEditorialOrchestrator(llm=llm)

        assert orchestrator._source_agent is mock_source_cls.return_value

    @patch("rag_backend.agents.carousel_editorial_orchestrator.SourceSynthesisAgent")
    @patch("rag_backend.agents.carousel_editorial_orchestrator.CarouselWorkflowEngine")
    @patch("rag_backend.agents.carousel_editorial_orchestrator.PhaseArtifactRunner")
    def test_init_passes_image_registry_to_runner(
        self,
        mock_runner_cls: MagicMock,
        mock_engine_cls: MagicMock,
        mock_source_cls: MagicMock,
    ) -> None:
        """Given image_registry, when constructing, then runner receives image_registry."""
        llm = MagicMock()
        image_registry = MagicMock()
        CarouselEditorialOrchestrator(llm=llm, image_registry=image_registry)

        call_kwargs = mock_runner_cls.call_args.kwargs
        assert call_kwargs["image_registry"] is image_registry

    # ------------------------------------------------------------------
    # engine property
    # ------------------------------------------------------------------

    def test_engine_property_returns_internal_engine(
        self, orchestrator: CarouselEditorialOrchestrator
    ) -> None:
        """Given orchestrator, when accessing engine, then internal engine is returned."""
        result = orchestrator.engine

        assert result is orchestrator._engine

    # ------------------------------------------------------------------
    # _bind_resume_context
    # ------------------------------------------------------------------

    def test_bind_resume_context_calls_with_context(
        self, orchestrator: CarouselEditorialOrchestrator
    ) -> None:
        """Given db and workflow_input, when binding, then with_context is called with exact args."""
        db = MagicMock()
        workflow_input = MagicMock()
        orchestrator._artifact_runner.with_context = MagicMock(return_value=MagicMock())

        orchestrator._bind_resume_context(db=db, workflow_input=workflow_input)

        orchestrator._artifact_runner.with_context.assert_called_once_with(
            db=db, workflow_input=workflow_input
        )

    def test_bind_resume_context_calls_set_artifact_runner_with_scoped(
        self, orchestrator: CarouselEditorialOrchestrator
    ) -> None:
        """Given db and workflow_input, when binding, then set_artifact_runner is called with scoped runner."""
        scoped_runner = MagicMock()
        orchestrator._artifact_runner.with_context = MagicMock(
            return_value=scoped_runner
        )
        orchestrator._engine.set_artifact_runner = MagicMock()

        orchestrator._bind_resume_context(db=MagicMock(), workflow_input=MagicMock())

        orchestrator._engine.set_artifact_runner.assert_called_once_with(scoped_runner)

    def test_bind_resume_context_with_none_args(
        self, orchestrator: CarouselEditorialOrchestrator
    ) -> None:
        """Given None args, when binding, then with_context is called with None args."""
        orchestrator._artifact_runner.with_context = MagicMock(return_value=MagicMock())
        orchestrator._engine.set_artifact_runner = MagicMock()

        orchestrator._bind_resume_context(db=None, workflow_input=None)

        orchestrator._artifact_runner.with_context.assert_called_once_with(
            db=None, workflow_input=None
        )

    # ------------------------------------------------------------------
    # start
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_start_calls_bind_resume_context(
        self, orchestrator: CarouselEditorialOrchestrator
    ) -> None:
        """Given project_id, when starting, then _bind_resume_context is called with exact args."""
        orchestrator._bind_resume_context = MagicMock()
        orchestrator._engine.start = AsyncMock(return_value=MagicMock())
        db = MagicMock()
        workflow_input = MagicMock()

        await orchestrator.start("project-1", db=db, workflow_input=workflow_input)

        orchestrator._bind_resume_context.assert_called_once_with(
            db=db, workflow_input=workflow_input
        )

    @pytest.mark.asyncio
    async def test_start_calls_engine_start_with_project_id_and_brief(
        self, orchestrator: CarouselEditorialOrchestrator
    ) -> None:
        """Given project_id and brief, when starting, then engine.start is called with exact args."""
        orchestrator._bind_resume_context = MagicMock()
        expected_state = MagicMock()
        orchestrator._engine.start = AsyncMock(return_value=expected_state)
        brief = {"topic": "AI"}

        result = await orchestrator.start("project-1", brief)

        orchestrator._engine.start.assert_awaited_once_with("project-1", brief)
        assert result is expected_state

    @pytest.mark.asyncio
    async def test_start_passes_state_overrides_to_engine(
        self, orchestrator: CarouselEditorialOrchestrator
    ) -> None:
        """Given state_overrides, when starting, then engine.start receives overrides."""
        orchestrator._bind_resume_context = MagicMock()
        expected_state = MagicMock()
        orchestrator._engine.start = AsyncMock(return_value=expected_state)

        result = await orchestrator.start("project-1", None, extra="value", count=42)

        orchestrator._engine.start.assert_awaited_once_with(
            "project-1", None, extra="value", count=42
        )
        assert result is expected_state

    @pytest.mark.asyncio
    async def test_start_with_none_brief(
        self, orchestrator: CarouselEditorialOrchestrator
    ) -> None:
        """Given None brief, when starting, then engine.start is called with None brief."""
        orchestrator._bind_resume_context = MagicMock()
        expected_state = MagicMock()
        orchestrator._engine.start = AsyncMock(return_value=expected_state)

        result = await orchestrator.start("project-1", None)

        orchestrator._engine.start.assert_awaited_once_with("project-1", None)
        assert result is expected_state

    # ------------------------------------------------------------------
    # resume
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_resume_calls_bind_resume_context(
        self, orchestrator: CarouselEditorialOrchestrator
    ) -> None:
        """Given project_id, when resuming, then _bind_resume_context is called with exact args."""
        orchestrator._bind_resume_context = MagicMock()
        orchestrator._engine.resume = AsyncMock(return_value=MagicMock())
        db = MagicMock()
        workflow_input = MagicMock()

        await orchestrator.resume("project-1", db=db, workflow_input=workflow_input)

        orchestrator._bind_resume_context.assert_called_once_with(
            db=db, workflow_input=workflow_input
        )

    @pytest.mark.asyncio
    async def test_resume_calls_engine_resume_with_project_id_and_human_input(
        self, orchestrator: CarouselEditorialOrchestrator
    ) -> None:
        """Given project_id and human_input, when resuming, then engine.resume is called with exact args."""
        orchestrator._bind_resume_context = MagicMock()
        expected_state = MagicMock()
        orchestrator._engine.resume = AsyncMock(return_value=expected_state)
        human_input = {"feedback": "looks good"}

        result = await orchestrator.resume("project-1", human_input)

        orchestrator._engine.resume.assert_awaited_once_with("project-1", human_input)
        assert result is expected_state

    @pytest.mark.asyncio
    async def test_resume_with_none_human_input(
        self, orchestrator: CarouselEditorialOrchestrator
    ) -> None:
        """Given None human_input, when resuming, then engine.resume is called with None."""
        orchestrator._bind_resume_context = MagicMock()
        expected_state = MagicMock()
        orchestrator._engine.resume = AsyncMock(return_value=expected_state)

        result = await orchestrator.resume("project-1", None)

        orchestrator._engine.resume.assert_awaited_once_with("project-1", None)
        assert result is expected_state

    # ------------------------------------------------------------------
    # get_state
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_get_state_delegates_to_engine(
        self, orchestrator: CarouselEditorialOrchestrator
    ) -> None:
        """Given project_id, when getting state, then engine.get_state is called and result returned."""
        expected_state = MagicMock()
        orchestrator._engine.get_state = AsyncMock(return_value=expected_state)

        result = await orchestrator.get_state("project-1")

        orchestrator._engine.get_state.assert_awaited_once_with("project-1")
        assert result is expected_state

    @pytest.mark.asyncio
    async def test_get_state_returns_none_when_engine_returns_none(
        self, orchestrator: CarouselEditorialOrchestrator
    ) -> None:
        """Given project_id, when engine returns None, then get_state returns None."""
        orchestrator._engine.get_state = AsyncMock(return_value=None)

        result = await orchestrator.get_state("project-1")

        assert result is None

    # ------------------------------------------------------------------
    # synthesize_research
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_synthesize_research_delegates_to_agent(
        self, orchestrator: CarouselEditorialOrchestrator
    ) -> None:
        """Given research sources, when synthesizing, then source agent is called."""
        with patch(
            "rag_backend.agents.carousel_editorial_orchestrator.synthesize_research",
            new_callable=AsyncMock,
            return_value=[{"source": "test", "key_points": ["point"]}],
        ) as mock_synthesize:
            result = await orchestrator.synthesize_research([
                {"source": "test", "key_points": "point"}
            ])

        mock_synthesize.assert_awaited_once()
        assert result == [{"source": "test", "key_points": ["point"]}]

    @pytest.mark.asyncio
    async def test_synthesize_research_passes_sources_through(
        self, orchestrator: CarouselEditorialOrchestrator
    ) -> None:
        """Given sources list, when synthesizing, then sources are passed to agent."""
        with patch(
            "rag_backend.agents.carousel_editorial_orchestrator.synthesize_research",
            new_callable=AsyncMock,
        ) as mock_synthesize:
            sources = [{"source": "a", "key_points": "x"}]
            await orchestrator.synthesize_research(sources)

        mock_synthesize.assert_awaited_once_with(orchestrator._source_agent, sources)

    @pytest.mark.asyncio
    async def test_synthesize_research_returns_empty_list(
        self, orchestrator: CarouselEditorialOrchestrator
    ) -> None:
        """Given empty sources, when synthesizing, then empty list is returned."""
        with patch(
            "rag_backend.agents.carousel_editorial_orchestrator.synthesize_research",
            new_callable=AsyncMock,
            return_value=[],
        ) as mock_synthesize:
            result = await orchestrator.synthesize_research([])

        assert result == []

    # ------------------------------------------------------------------
    # update_state
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_update_state_delegates_to_engine(
        self, orchestrator: CarouselEditorialOrchestrator
    ) -> None:
        """Given project id and values, when updating state, then engine is called."""
        orchestrator._engine.update_state = AsyncMock()
        await orchestrator.update_state("project-1", {"status": "active"})

        orchestrator._engine.update_state.assert_awaited_once_with(
            "project-1", {"status": "active"}
        )

    @pytest.mark.asyncio
    async def test_update_state_with_empty_values(
        self, orchestrator: CarouselEditorialOrchestrator
    ) -> None:
        """Given empty values dict, when updating state, then engine is called with empty dict."""
        orchestrator._engine.update_state = AsyncMock()
        await orchestrator.update_state("project-1", {})

        orchestrator._engine.update_state.assert_awaited_once_with("project-1", {})

    @pytest.mark.asyncio
    async def test_update_state_returns_none(
        self, orchestrator: CarouselEditorialOrchestrator
    ) -> None:
        """Given valid inputs, when updating state, then None is returned."""
        orchestrator._engine.update_state = AsyncMock(return_value=None)
        result = await orchestrator.update_state("project-1", {"status": "active"})

        assert result is None
