"""Unit tests for FeedbackLearningLoop.

Feature: Continuous persona improvement from human corrections
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from rag_backend.agents.feedback_learning import (
    CorrectionClassifier,
    FeedbackLearningLoop,
)


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
    def loop(
        self, mock_session: AsyncMock, mock_embeddings: MagicMock
    ) -> FeedbackLearningLoop:
        """Create a FeedbackLearningLoop instance."""
        return FeedbackLearningLoop(session=mock_session, embeddings=mock_embeddings)

    # Scenario: Record a correction
    async def test_record_correction_does_not_raise(
        self, loop: FeedbackLearningLoop
    ) -> None:
        """Given correction data, when record_correction is called, then no exception is raised."""
        await loop.record_correction(
            _original="original text",
            _corrected="corrected text",
            _context="test context",
            _persona_id="test-id",
            _correction_type="tone",
        )

    async def test_record_then_retrieve_correction(
        self, loop: FeedbackLearningLoop
    ) -> None:
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
    def test_cosine_similarity_with_identical_vectors(
        self, loop: FeedbackLearningLoop
    ) -> None:
        """Given identical vectors, when calculating similarity, then 1.0 is returned."""
        a = [1.0, 0.0, 0.0]
        b = [1.0, 0.0, 0.0]

        result = loop._cosine_similarity(a, b)

        assert result == 1.0

    def test_cosine_similarity_with_orthogonal_vectors(
        self, loop: FeedbackLearningLoop
    ) -> None:
        """Given orthogonal vectors, when calculating similarity, then 0.0 is returned."""
        a = [1.0, 0.0]
        b = [0.0, 1.0]

        result = loop._cosine_similarity(a, b)

        assert result == 0.0

    def test_cosine_similarity_with_zero_vector(
        self, loop: FeedbackLearningLoop
    ) -> None:
        """Given zero vector, when calculating similarity, then 0.0 is returned."""
        a = [0.0, 0.0]
        b = [1.0, 0.0]

        result = loop._cosine_similarity(a, b)

        assert result == 0.0

    # Scenario: Classify correction
    async def test_classify_correction_detects_tone(
        self, loop: FeedbackLearningLoop
    ) -> None:
        """Given tone-related correction, when classifying, then "tone" is returned."""
        original = "Hello"
        corrected = "Hello!"

        result = await loop.classify_correction(original, corrected)

        assert result == "tone"

    async def test_classify_correction_detects_content(
        self, loop: FeedbackLearningLoop
    ) -> None:
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

    async def test_classify_correction_returns_minor_edit_for_same_text(
        self, loop: FeedbackLearningLoop
    ) -> None:
        """Given identical text, when classifying, then minor_edit is returned."""
        result = await loop.classify_correction("same text", "same text")

        assert result == "minor_edit"

    async def test_get_relevant_examples_respects_k_limit(
        self, loop: FeedbackLearningLoop
    ) -> None:
        """Given many corrections, when retrieving examples, then only k are returned."""
        for idx in range(5):
            await loop.record_correction(
                _original=f"orig {idx}",
                _corrected=f"corr {idx}",
                _context="ctx",
                _persona_id="persona-1",
                _correction_type="tone",
            )

        examples = await loop.get_relevant_examples(_persona_id="persona-1", _k=2)

        assert examples == ["corr 3", "corr 4"]

    # Scenario: Suggest improvements
    async def test_suggest_improvements_returns_empty_list(
        self, loop: FeedbackLearningLoop
    ) -> None:
        """Given no examples, when suggesting improvements, then empty list is returned."""
        result = await loop.suggest_improvements("content", _persona_id="test-id")

        assert result == []

    # Scenario: Analyze voice drift
    async def test_analyze_voice_drift_with_no_samples(
        self, loop: FeedbackLearningLoop
    ) -> None:
        """Given no samples, when analyzing drift, then zero score is returned."""
        result = await loop.analyze_voice_drift(
            _persona_id="test-id", recent_samples=[]
        )

        assert result["drift_score"] == 0.0
        assert result["trends"] == []

    async def test_record_correction_auto_classifies_when_type_missing(
        self, loop: FeedbackLearningLoop
    ) -> None:
        """Given no correction type, when recording, then type is inferred."""
        await loop.record_correction(
            _original="old text",
            _corrected="new text",
            _context="ctx",
            _persona_id="persona-1",
        )

        examples = await loop.get_relevant_examples(_persona_id="persona-1")
        assert examples == ["new text"]

    async def test_record_correction_accepts_non_string_persona_id(
        self, loop: FeedbackLearningLoop
    ) -> None:
        """Given UUID persona id, when recording, then correction is stored under str id."""
        persona_id = uuid4()
        await loop.record_correction(
            _original="hello",
            _corrected="hello!",
            _context="greeting",
            _persona_id=persona_id,
            _correction_type="tone",
        )

        examples = await loop.get_relevant_examples(_persona_id=str(persona_id))

        assert examples == ["hello!"]

    async def test_suggest_improvements_returns_ranked_suggestions(
        self, loop: FeedbackLearningLoop, mock_embeddings: MagicMock
    ) -> None:
        """Given stored corrections, when suggesting, then ranked suggestions returned."""
        mock_embeddings.embed = AsyncMock(
            side_effect=[[1.0, 0.0], [0.9, 0.1], [0.5, 0.5]]
        )
        await loop.record_correction(
            _original="hello",
            _corrected="hello!",
            _context="greeting",
            _persona_id="persona-1",
            _correction_type="tone",
        )
        await loop.record_correction(
            _original="world",
            _corrected="world!",
            _context="greeting",
            _persona_id="persona-1",
            _correction_type="tone",
        )

        result = await loop.suggest_improvements("hello there", _persona_id="persona-1")

        assert len(result) > 0
        assert result[0].startswith("Consider:")

    async def test_analyze_voice_drift_reports_stable_voice(
        self, loop: FeedbackLearningLoop, mock_embeddings: MagicMock
    ) -> None:
        """Given similar samples, when analyzing drift, then voice is stable."""
        mock_embeddings.embed = AsyncMock(return_value=[1.0, 0.0])

        result = await loop.analyze_voice_drift(
            _persona_id="test-id",
            recent_samples=[("sample1", "sample1")],
        )

        assert result["drift_score"] == 0.0
        assert result["trends"] == ["voice_stable"]

    async def test_analyze_voice_drift_reports_drifting_voice(
        self, loop: FeedbackLearningLoop, mock_embeddings: MagicMock
    ) -> None:
        """Given dissimilar samples, when analyzing drift, then voice is drifting."""
        mock_embeddings.embed = AsyncMock(side_effect=[[1.0, 0.0], [0.0, 1.0]])

        result = await loop.analyze_voice_drift(
            _persona_id="test-id",
            recent_samples=[("sample1", "sample2")],
        )

        assert result["drift_score"] > 0.2
        assert result["trends"] == ["voice_drifting"]

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

    def test_classify_uses_default_confidence_for_minor_edit(self) -> None:
        """Given unchanged text, when classifying, then default confidence is used."""
        result = CorrectionClassifier.classify("same text", "same text")

        assert result["correction_type"] == "tone"
        assert result["confidence"] == 0.5
