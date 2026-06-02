"""Unit tests for FeedbackLearningLoop.

Feature: Continuous persona improvement from human corrections
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rag_backend.agents.feedback_learning import (
    CorrectionClassifier,
    FeedbackLearningLoop,
)
from rag_backend.infrastructure.database.persona_correction_repository import (
    PersonaCorrectionRecord,
)


class TestFeedbackLearningLoop:
    """Tests for FeedbackLearningLoop."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture
    def mock_embeddings(self) -> MagicMock:
        mock = MagicMock()
        mock.embed = AsyncMock(return_value=[0.1, 0.2, 0.3])
        return mock

    @pytest.fixture
    def mock_repository(self) -> MagicMock:
        repo = MagicMock()
        repo.create = AsyncMock()
        repo.list_recent_by_persona = AsyncMock(return_value=[])
        repo.list_all_by_persona = AsyncMock(return_value=[])
        return repo

    @pytest.fixture
    def loop(
        self,
        mock_session: AsyncMock,
        mock_embeddings: MagicMock,
        mock_repository: MagicMock,
    ) -> FeedbackLearningLoop:
        feedback_loop = FeedbackLearningLoop(
            session=mock_session, embeddings=mock_embeddings
        )
        feedback_loop._repository = mock_repository
        return feedback_loop

    async def test_record_correction_persists_to_repository(
        self, loop: FeedbackLearningLoop, mock_repository: MagicMock
    ) -> None:
        await loop.record_correction(
            _original="original text",
            _corrected="corrected text",
            _context="test context",
            _persona_id="test-id",
            _correction_type="tone",
        )
        mock_repository.create.assert_awaited_once()

    async def test_record_then_retrieve_correction(
        self, loop: FeedbackLearningLoop, mock_repository: MagicMock
    ) -> None:
        mock_repository.list_recent_by_persona.return_value = [
            PersonaCorrectionRecord(
                original_text="Hello",
                corrected_text="Hello!",
                context="greeting",
                correction_type="tone",
            )
        ]

        examples = await loop.get_relevant_examples(_persona_id="persona-1", _k=3)

        assert examples == ["Hello!"]

    async def test_get_relevant_examples_returns_empty_list(
        self, loop: FeedbackLearningLoop, mock_repository: MagicMock
    ) -> None:
        result = await loop.get_relevant_examples(_persona_id="test-id", _k=3)
        assert result == []

    def test_cosine_similarity_with_identical_vectors(
        self, loop: FeedbackLearningLoop
    ) -> None:
        assert loop._cosine_similarity([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)

    async def test_classify_correction_conciseness(
        self, loop: FeedbackLearningLoop
    ) -> None:
        result = await loop.classify_correction(
            "This is a very long original sentence with many words.",
            "Short.",
        )
        assert result == "conciseness"

    async def test_get_relevant_examples_respects_k_limit(
        self, loop: FeedbackLearningLoop, mock_repository: MagicMock
    ) -> None:
        mock_repository.list_recent_by_persona.return_value = [
            PersonaCorrectionRecord("a", "b", "c", "tone"),
            PersonaCorrectionRecord("d", "e", "f", "tone"),
        ]

        examples = await loop.get_relevant_examples(_persona_id="persona-1", _k=2)

        mock_repository.list_recent_by_persona.assert_awaited_once_with("persona-1", 2)
        assert len(examples) == 2

    async def test_suggest_improvements_empty_when_no_corrections(
        self, loop: FeedbackLearningLoop, mock_repository: MagicMock
    ) -> None:
        suggestions = await loop.suggest_improvements("content", "persona-1")
        assert suggestions == []

    @patch(
        "rag_backend.agents.feedback_learning.PersonaCorrectionRepository",
        autospec=True,
    )
    def test_repository_constructed_from_session(
        self,
        mock_repo_cls: MagicMock,
        mock_session: AsyncMock,
        mock_embeddings: MagicMock,
    ) -> None:
        FeedbackLearningLoop(session=mock_session, embeddings=mock_embeddings)
        mock_repo_cls.assert_called_once_with(mock_session)


class TestCorrectionClassifier:
    def test_classify_detects_tone_change(self) -> None:
        result = CorrectionClassifier.classify("Hello", "Hello!")
        assert result["correction_type"] == "tone"
