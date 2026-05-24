"""Unit tests for FeedbackLearningLoop.

Feature: Continuous persona improvement from human corrections
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from rag_backend.agents.feedback_learning import CorrectionClassifier, FeedbackLearningLoop


class TestFeedbackLearningLoop:
    """Tests for FeedbackLearningLoop."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock database session."""
        return AsyncMock()

    @pytest.fixture
    def mock_embeddings(self) -> MagicMock:
        """Create a mock embeddings model."""
        mock = MagicMock()
        mock.embed = AsyncMock(return_value=[[0.1, 0.2, 0.3]])
        return mock

    @pytest.fixture
    def loop(self, mock_session: AsyncMock, mock_embeddings: MagicMock) -> FeedbackLearningLoop:
        """Create a FeedbackLearningLoop instance."""
        return FeedbackLearningLoop(session=mock_session, embeddings=mock_embeddings)

    # Scenario: Record a correction
    async def test_record_correction_does_not_raise(self, loop: FeedbackLearningLoop) -> None:
        """Given correction data, when record_correction is called, then no exception is raised."""
        await loop.record_correction(
            _original="original text",
            _corrected="corrected text",
            _context="test context",
            _persona_id="test-id",
            _correction_type="tone",
        )

    async def test_record_then_retrieve_correction(self, loop: FeedbackLearningLoop) -> None:
        """Given a recorded correction, when retrieving examples, then corrected text is returned."""
        await loop.record_correction(
            _original="Hello",
            _corrected="Hello!",
            _context="greeting",
            _persona_id="persona-1",
            _correction_type="tone",
        )

        examples = await loop.get_relevant_examples(_persona_id="persona-1", _k=3)

        assert examples == ["hello!"]

    # Scenario: Get relevant examples
    async def test_get_relevant_examples_returns_empty_list(
        self, loop: FeedbackLearningLoop
    ) -> None:
        """Given no corrections, when get_relevant_examples is called, then empty list."""
        result = await loop.get_relevant_examples(_persona_id="test-id", _k=3)

        assert result == []

    # Scenario: Cosine similarity
    def test_cosine_similarity_with_identical_vectors(self, loop: FeedbackLearningLoop) -> None:
        """Given identical vectors, when calculating similarity, then 1.0 is returned."""
        a = [1.0, 0.0, 0.0]
        b = [1.0, 0.0, 0.0]

        result = loop._cosine_similarity(a, b)

        assert result == 1.0

    def test_cosine_similarity_with_orthogonal_vectors(self, loop: FeedbackLearningLoop) -> None:
        """Given orthogonal vectors, when calculating similarity, then 0.0 is returned."""
        a = [1.0, 0.0]
        b = [0.0, 1.0]

        result = loop._cosine_similarity(a, b)

        assert result == 0.0

    def test_cosine_similarity_with_zero_vector(self, loop: FeedbackLearningLoop) -> None:
        """Given zero vector, when calculating similarity, then 0.0 is returned."""
        a = [0.0, 0.0]
        b = [1.0, 0.0]

        result = loop._cosine_similarity(a, b)

        assert result == 0.0

    # Scenario: Classify correction
    async def test_classify_correction_detects_tone(self, loop: FeedbackLearningLoop) -> None:
        """Given tone-related correction, when classifying, then "tone" is returned."""
        original = "Hello"
        corrected = "Hello!"

        result = await loop.classify_correction(original, corrected)

        assert result == "tone"

    async def test_classify_correction_detects_content(self, loop: FeedbackLearningLoop) -> None:
        """Given content correction, when classifying, then "content" is returned."""
        original = "old text"
        corrected = "new text"

        result = await loop.classify_correction(original, corrected)

        assert result == "content"

    async def test_classify_correction_detects_conciseness(
        self, loop: FeedbackLearningLoop
    ) -> None:
        """Given concise correction, when classifying, then "conciseness" is returned."""
        original = "This is a very long sentence with many words"
        corrected = "Short"

        result = await loop.classify_correction(original, corrected)

        assert result == "conciseness"

    # Scenario: Suggest improvements
    async def test_suggest_improvements_returns_empty_list(
        self, loop: FeedbackLearningLoop
    ) -> None:
        """Given no examples, when suggesting improvements, then empty list is returned."""
        result = await loop.suggest_improvements("content", _persona_id="test-id")

        assert result == []

    # Scenario: Analyze voice drift
    async def test_analyze_voice_drift_with_no_samples(self, loop: FeedbackLearningLoop) -> None:
        """Given no samples, when analyzing drift, then zero score is returned."""
        result = await loop.analyze_voice_drift(_persona_id="test-id", recent_samples=[])

        assert result["drift_score"] == 0.0
        assert result["trends"] == []

    async def test_analyze_voice_drift_with_samples(
        self, loop: FeedbackLearningLoop, mock_embeddings: MagicMock
    ) -> None:
        """Given samples, when analyzing drift, then drift score is calculated."""
        mock_embeddings.embed.return_value = [1.0, 0.0]

        result = await loop.analyze_voice_drift(
            _persona_id="test-id",
            recent_samples=[("sample1", "corrected1"), ("sample2", "corrected2")],
        )

        assert "drift_score" in result
        assert "trends" in result


class TestCorrectionClassifier:
    """Tests for CorrectionClassifier."""

    def test_classify_detects_tone(self) -> None:
        """Given tone change, when classifying, then tone type is detected."""
        result = CorrectionClassifier.classify("Hello", "Hello!")

        assert result["correction_type"] == "tone"

    def test_classify_detects_grammar(self) -> None:
        """Given grammar fix, when classifying, then grammar type is detected."""
        result = CorrectionClassifier.classify("text  with  spaces", "text with spaces")

        assert result["correction_type"] == "grammar"

    def test_classify_detects_content(self) -> None:
        """Given content change, when classifying, then content type is detected."""
        result = CorrectionClassifier.classify("old text", "new text")

        assert result["correction_type"] == "content"
