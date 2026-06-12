"""Unit tests for LangFuse monitoring integration.

Feature: Observability and tracing
"""

from unittest.mock import MagicMock, patch

import pytest

from rag_backend.domain.models.carousels import ReviewEventParams
from rag_backend.infrastructure.langfuse_client import init_langfuse
from rag_backend.infrastructure.monitoring_langfuse import (
    LangfuseCallbackHandler,
    _ErrorParams,
    _ScoreParams,
    _TraceConfig,
    add_error_span,
    add_quality_score,
    add_voice_match_score,
    create_workflow_trace,
    record_human_review,
)


class TestLangfuseInit:
    """Tests for LangFuse initialization."""

    def test_init_langfuse_with_none_keys(self) -> None:
        """Given None keys, when initializing, then None is returned."""
        result = init_langfuse(None, "", "")

        assert result is None

    @patch("rag_backend.infrastructure.langfuse_client.Langfuse")
    def test_init_langfuse_with_valid_keys(self, mock_langfuse: MagicMock) -> None:
        """Given valid keys, when initializing, then Langfuse instance is returned."""
        mock_instance = MagicMock()
        mock_langfuse.return_value = mock_instance

        result = init_langfuse("public", "secret", "http://localhost")

        assert result == mock_instance


class TestLangfuseCallbackHandler:
    """Tests for LangfuseCallbackHandler."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create a mock Langfuse client."""
        return MagicMock()

    @pytest.fixture
    def handler(self, mock_client: MagicMock) -> LangfuseCallbackHandler:
        """Create a LangfuseCallbackHandler instance."""
        return LangfuseCallbackHandler(mock_client)

    def test_init(
        self, handler: LangfuseCallbackHandler, mock_client: MagicMock
    ) -> None:
        """Given client, when initializing, then handler is created."""
        assert handler.client == mock_client
        assert handler._current_trace is None
        assert handler._current_span is None
        assert handler._run_stack == []

    def test_on_text(
        self, handler: LangfuseCallbackHandler, mock_client: MagicMock
    ) -> None:
        """Given run, when on_text is called, then trace is created."""
        run = MagicMock()
        run.name = "test_run"
        run.id = "123"
        run.tags = ["tag1"]
        run.run_type = "llm"
        run.inputs = {}

        handler.on_text(run)

        assert handler._current_trace is not None
        mock_client.trace.assert_called_once()

    def test_on_error(
        self, handler: LangfuseCallbackHandler, mock_client: MagicMock
    ) -> None:
        """Given error, when on_error is called, then span is updated."""
        run = MagicMock()
        run.name = "test"
        run.id = "123"
        run.tags = []
        run.run_type = "llm"
        run.inputs = {}
        handler.on_text(run)

        handler.on_error(run, Exception("test error"))

        assert handler._current_span.update.called

    def test_set_tags(
        self, handler: LangfuseCallbackHandler, mock_client: MagicMock
    ) -> None:
        """Given tags, when set_tags is called, then trace is updated."""
        run = MagicMock()
        run.name = "test"
        run.id = "123"
        run.tags = []
        run.run_type = "llm"
        run.inputs = {}
        handler.on_text(run)

        handler.set_tags(["new_tag"])

        handler._current_trace.update.assert_called_with(tags=["new_tag"])

    def test_set_metadata(
        self, handler: LangfuseCallbackHandler, mock_client: MagicMock
    ) -> None:
        """Given metadata, when set_metadata is called, then trace is updated."""
        run = MagicMock()
        run.name = "test"
        run.id = "123"
        run.tags = []
        run.run_type = "llm"
        run.inputs = {}
        handler.on_text(run)

        handler.set_metadata({"key": "value"})

        handler._current_trace.update.assert_called_with(metadata={"key": "value"})

    def test_add_score(
        self, handler: LangfuseCallbackHandler, mock_client: MagicMock
    ) -> None:
        """Given score, when add_score is called, then score is added."""
        run = MagicMock()
        run.name = "test"
        run.id = "123"
        run.tags = []
        run.run_type = "llm"
        run.inputs = {}
        handler.on_text(run)

        handler.add_score("quality", 0.85, {"detail": "test"})

        handler._current_trace.score.assert_called_once()

    def test_create_child_trace(
        self, handler: LangfuseCallbackHandler, mock_client: MagicMock
    ) -> None:
        """Given parent trace, when creating child trace, then child is linked."""
        handler.create_child_trace(
            config=_TraceConfig(
                parent_trace_id="parent123",
                name="child_trace",
                metadata={"key": "value"},
            ),
        )

        mock_client.trace.assert_called_once()


class TestTraceFunctions:
    """Tests for standalone trace functions."""

    @patch("rag_backend.infrastructure.monitoring_langfuse.get_langfuse_client")
    def test_create_workflow_trace_with_none_client(
        self, mock_get_client: MagicMock
    ) -> None:
        """Given None client, when creating trace, then None is returned."""
        mock_get_client.return_value = None

        result = create_workflow_trace(
            config=_TraceConfig(
                project_id=MagicMock(),
                user_id="user123",
                content_type="carousel",
            ),
        )

        assert result is None

    @patch("rag_backend.infrastructure.monitoring_langfuse.get_langfuse_client")
    def test_create_workflow_trace_with_v3_client(
        self, mock_get_client: MagicMock
    ) -> None:
        """Given Langfuse v3 client, create a workflow span via start_span()."""
        mock_span = MagicMock()
        mock_client = MagicMock()
        mock_client.start_span.return_value = mock_span
        mock_get_client.return_value = mock_client

        result = create_workflow_trace(
            config=_TraceConfig(
                project_id=MagicMock(),
                user_id="user123",
                content_type="carousel",
            ),
        )

        assert result is mock_span
        mock_client.start_span.assert_called_once()

    @patch("rag_backend.infrastructure.langfuse_client.get_langfuse_client")
    def test_add_quality_score_with_none_trace(
        self, mock_get_client: MagicMock
    ) -> None:
        """Given None trace, when adding score, then no exception is raised."""
        add_quality_score(
            trace=None,
            params=_ScoreParams(
                criterion="tone",
                score=85.0,
                threshold=70.0,
                passed=True,
            ),
        )

    @patch("rag_backend.infrastructure.langfuse_client.get_langfuse_client")
    def test_add_voice_match_score_with_none_trace(
        self, mock_get_client: MagicMock
    ) -> None:
        """Given None trace, when adding score, then no exception is raised."""
        add_voice_match_score(
            trace=None,
            score=90.0,
            suggestions=["improve"],
        )

    @patch("rag_backend.infrastructure.langfuse_client.get_langfuse_client")
    def test_record_human_review_with_none_trace(
        self, mock_get_client: MagicMock
    ) -> None:
        """Given None trace, when recording review, then no exception is raised."""
        record_human_review(
            trace=None,
            params=ReviewEventParams(
                phase="content",
                action="approve",
                reviewer_id="user123",
                time_to_respond=None,
                feedback=None,
            ),
        )

    @patch("rag_backend.infrastructure.langfuse_client.get_langfuse_client")
    def test_add_error_span_with_none_trace(self, mock_get_client: MagicMock) -> None:
        """Given None trace, when adding error, then no exception is raised."""
        add_error_span(
            trace=None,
            params=_ErrorParams(
                error_type="test_error",
                error_message="test message",
            ),
        )
