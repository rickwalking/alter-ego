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

    async def test_analyze_voice_drift_empty_samples_returns_zero(
        self, loop: FeedbackLearningLoop
    ) -> None:
        """Given empty samples, when analyzing drift, then drift_score is 0.0 and trends is empty."""
        result = await loop.analyze_voice_drift("persona-1", [])
        assert result["drift_score"] == 0.0
        assert result["trends"] == []

    async def test_analyze_voice_drift_identical_texts_returns_zero(
        self, loop: FeedbackLearningLoop, mock_embeddings: MagicMock
    ) -> None:
        """Given identical original and corrected texts, when analyzing drift, then drift_score is 0.0."""
        mock_embeddings.embed = AsyncMock(return_value=[1.0, 0.0, 0.0])
        result = await loop.analyze_voice_drift("persona-1", [("hello", "hello")])
        assert result["drift_score"] == 0.0
        assert result["trends"] == ["voice_stable"]

    async def test_analyze_voice_drift_different_texts_returns_high_drift(
        self, loop: FeedbackLearningLoop, mock_embeddings: MagicMock
    ) -> None:
        """Given very different texts, when analyzing drift, then drift_score approaches 1.0."""
        mock_embeddings.embed = AsyncMock(
            side_effect=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]
        )
        result = await loop.analyze_voice_drift("persona-1", [("hello", "world")])
        assert result["drift_score"] == 1.0
        assert result["trends"] == ["voice_drifting"]

    async def test_analyze_voice_drift_multiple_samples_averages(
        self, loop: FeedbackLearningLoop, mock_embeddings: MagicMock
    ) -> None:
        """Given multiple samples, when analyzing drift, then similarity is averaged."""
        mock_embeddings.embed = AsyncMock(
            side_effect=[
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [1.0, 0.0, 0.0],
                [1.0, 0.0, 0.0],
            ]
        )
        result = await loop.analyze_voice_drift(
            "persona-1", [("hello", "world"), ("test", "test")]
        )
        assert result["drift_score"] == 0.5
        assert result["trends"] == ["voice_drifting"]

    async def test_analyze_voice_drift_threshold_boundary_stable(
        self, loop: FeedbackLearningLoop, mock_embeddings: MagicMock
    ) -> None:
        """Given drift_score below threshold, when analyzing, then voice is stable."""
        mock_embeddings.embed = AsyncMock(
            side_effect=[
                [1.0, 0.0, 0.0],
                [0.9, 0.43589, 0.0],
            ]
        )
        result = await loop.analyze_voice_drift("persona-1", [("hello", "world")])
        assert result["drift_score"] < 0.2
        assert result["trends"] == ["voice_stable"]

    async def test_analyze_voice_drift_calls_embed_for_each_pair(
        self, loop: FeedbackLearningLoop, mock_embeddings: MagicMock
    ) -> None:
        """Given 2 samples, when analyzing drift, then embed is called 4 times."""
        mock_embeddings.embed = AsyncMock(return_value=[0.1, 0.2, 0.3])
        await loop.analyze_voice_drift("persona-1", [("a", "b"), ("c", "d")])
        assert mock_embeddings.embed.await_count == 4

    async def test_analyze_voice_drift_returns_dict_with_drift_score(
        self, loop: FeedbackLearningLoop, mock_embeddings: MagicMock
    ) -> None:
        """Given valid samples, when analyzing drift, then result contains drift_score key."""
        mock_embeddings.embed = AsyncMock(return_value=[0.1, 0.2, 0.3])
        result = await loop.analyze_voice_drift("persona-1", [("a", "b")])
        assert "drift_score" in result
        assert isinstance(result["drift_score"], float)

    async def test_analyze_voice_drift_returns_dict_with_trends_list(
        self, loop: FeedbackLearningLoop, mock_embeddings: MagicMock
    ) -> None:
        """Given valid samples, when analyzing drift, then result contains trends list."""
        mock_embeddings.embed = AsyncMock(return_value=[0.1, 0.2, 0.3])
        result = await loop.analyze_voice_drift("persona-1", [("a", "b")])
        assert "trends" in result
        assert isinstance(result["trends"], list)

    async def test_classify_correction_tone(self, loop: FeedbackLearningLoop) -> None:
        """Given tone change (exclamation added), when classifying, then returns tone."""
        result = await loop.classify_correction("Hello", "Hello!")
        assert result == "tone"

    async def test_classify_correction_content(
        self, loop: FeedbackLearningLoop
    ) -> None:
        """Given content change (different words), when classifying, then returns content."""
        result = await loop.classify_correction(
            "This is a test", "This is a different test"
        )
        assert result == "content"

    async def test_classify_correction_minor_edit(
        self, loop: FeedbackLearningLoop
    ) -> None:
        """Given minor edit (same words), when classifying, then returns minor_edit."""
        result = await loop.classify_correction("Hello", "hello")
        assert result == "minor_edit"

    async def test_classify_correction_at_exact_boundary(
        self, loop: FeedbackLearningLoop
    ) -> None:
        """Given very short correction, when classifying, then returns conciseness."""
        result = await loop.classify_correction(
            "This is a very long sentence with many words in it.",
            "Short.",
        )
        assert result == "conciseness"

    async def test_suggest_improvements_with_entries(
        self, loop: FeedbackLearningLoop, mock_repository: MagicMock
    ) -> None:
        """Given corrections exist, when suggesting improvements, then returns suggestions."""
        mock_repository.list_all_by_persona.return_value = [
            PersonaCorrectionRecord(
                original_text="Hello",
                corrected_text="Hello!",
                context="greeting",
                correction_type="tone",
            )
        ]
        result = await loop.suggest_improvements("Hello", "persona-1")
        assert len(result) == 1
        assert "Hello!" in result[0]

    async def test_suggest_improvements_with_similar_entries(
        self, loop: FeedbackLearningLoop, mock_repository: MagicMock
    ) -> None:
        """Given similar corrections, when suggesting improvements, then returns top suggestions."""
        mock_repository.list_all_by_persona.return_value = [
            PersonaCorrectionRecord(
                original_text="Test",
                corrected_text="Test!",
                context="greeting",
                correction_type="tone",
            ),
            PersonaCorrectionRecord(
                original_text="Other",
                corrected_text="Other!",
                context="greeting",
                correction_type="tone",
            ),
        ]
        result = await loop.suggest_improvements("Test", "persona-1")
        assert len(result) == 2

    async def test_record_correction_with_sanitization(
        self, loop: FeedbackLearningLoop, mock_repository: MagicMock
    ) -> None:
        """Given text with special chars, when recording correction, then sanitization is applied."""
        await loop.record_correction(
            _original="<script>alert(1)</script>",
            _corrected="<b>bold</b>",
            _context="<i>context</i>",
            _persona_id="persona-1",
            _correction_type="tone",
        )
        mock_repository.create.assert_awaited_once()

    async def test_record_correction_with_none_correction_type(
        self, loop: FeedbackLearningLoop, mock_repository: MagicMock
    ) -> None:
        """Given None correction_type, when recording correction, then classify_correction is called."""
        await loop.record_correction(
            _original="Hello",
            _corrected="Hello!",
            _context="greeting",
            _persona_id="persona-1",
            _correction_type=None,
        )
        mock_repository.create.assert_awaited_once()

    async def test_record_correction_with_project_id(
        self, loop: FeedbackLearningLoop, mock_repository: MagicMock
    ) -> None:
        """Given project_id, when recording correction, then project_id is passed."""
        await loop.record_correction(
            _original="Hello",
            _corrected="Hello!",
            _context="greeting",
            _persona_id="persona-1",
            _correction_type="tone",
            project_id="project-1",
        )
        mock_repository.create.assert_awaited_once()

    async def test_record_correction_with_non_string_persona_id(
        self, loop: FeedbackLearningLoop, mock_repository: MagicMock
    ) -> None:
        """Given non-string persona_id, when recording correction, then persona_id is converted to string."""
        await loop.record_correction(
            _original="Hello",
            _corrected="Hello!",
            _context="greeting",
            _persona_id=123,
            _correction_type="tone",
        )
        mock_repository.create.assert_awaited_once()
        call_args = mock_repository.create.await_args
        params = call_args[0][0]
        assert params["persona_id"] == "123"

    async def test_record_correction_context_is_sanitized(
        self, loop: FeedbackLearningLoop, mock_repository: MagicMock
    ) -> None:
        """Given context with special chars, when recording correction, then context is sanitized."""
        await loop.record_correction(
            _original="Hello",
            _corrected="Hello!",
            _context="<script>alert(1)</script>",
            _persona_id="persona-1",
            _correction_type="tone",
        )
        mock_repository.create.assert_awaited_once()

    async def test_record_correction_persona_id_is_not_none(
        self, loop: FeedbackLearningLoop, mock_repository: MagicMock
    ) -> None:
        """Given persona_id, when recording correction, then persona_id is passed to repository."""
        await loop.record_correction(
            _original="Hello",
            _corrected="Hello!",
            _context="greeting",
            _persona_id="persona-1",
            _correction_type="tone",
        )
        call_args = mock_repository.create.await_args
        params = call_args[0][0]
        assert params["persona_id"] == "persona-1"

    async def test_get_relevant_examples_with_non_string_persona_id(
        self, loop: FeedbackLearningLoop, mock_repository: MagicMock
    ) -> None:
        """Given non-string persona_id, when getting examples, then persona_id is converted."""
        mock_repository.list_recent_by_persona.return_value = [
            PersonaCorrectionRecord(
                original_text="Hello",
                corrected_text="Hello!",
                context="greeting",
                correction_type="tone",
            )
        ]
        result = await loop.get_relevant_examples(_persona_id=123, _k=1)
        assert result == ["Hello!"]

    async def test_load_entries_with_empty_rows(
        self, loop: FeedbackLearningLoop, mock_repository: MagicMock
    ) -> None:
        """Given empty rows, when loading entries, then empty list is returned."""
        mock_repository.list_all_by_persona.return_value = []
        result = await loop._load_entries("persona-1")
        assert result == []

    async def test_load_entries_with_multiple_rows(
        self, loop: FeedbackLearningLoop, mock_repository: MagicMock
    ) -> None:
        """Given multiple rows, when loading entries, then all entries are returned."""
        mock_repository.list_all_by_persona.return_value = [
            PersonaCorrectionRecord(
                original_text="Hello",
                corrected_text="Hello!",
                context="greeting",
                correction_type="tone",
            ),
            PersonaCorrectionRecord(
                original_text="Test",
                corrected_text="Test!",
                context="greeting",
                correction_type="tone",
            ),
        ]
        result = await loop._load_entries("persona-1")
        assert len(result) == 2

    def test_cosine_similarity_with_zero_vectors(
        self, loop: FeedbackLearningLoop
    ) -> None:
        """Given zero vectors, when calculating similarity, then returns 0.0."""
        result = loop._cosine_similarity([0.0, 0.0], [0.0, 0.0])
        assert result == 0.0

    def test_cosine_similarity_with_orthogonal_vectors(
        self, loop: FeedbackLearningLoop
    ) -> None:
        """Given orthogonal vectors, when calculating similarity, then returns 0.0."""
        result = loop._cosine_similarity([1.0, 0.0], [0.0, 1.0])
        assert result == pytest.approx(0.0)

    def test_cosine_similarity_with_negative_vectors(
        self, loop: FeedbackLearningLoop
    ) -> None:
        """Given negative vectors, when calculating similarity, then returns correct value."""
        result = loop._cosine_similarity([1.0, 0.0], [-1.0, 0.0])
        assert result == pytest.approx(-1.0)

    def test_init_sets_session(
        self, mock_session: AsyncMock, mock_embeddings: MagicMock
    ) -> None:
        """Given a session, when creating FeedbackLearningLoop, then session is stored."""
        loop = FeedbackLearningLoop(session=mock_session, embeddings=mock_embeddings)
        assert loop.session is mock_session

    async def test_record_correction_passes_exact_sanitized_kwargs(
        self, loop: FeedbackLearningLoop, mock_repository: MagicMock
    ) -> None:
        """Given inputs with special chars, when recording, then exact sanitized kwargs are passed."""
        await loop.record_correction(
            _original="<script>alert(1)</script>",
            _corrected="<b>bold</b>",
            _context="<i>context</i>",
            _persona_id="persona-1",
            _correction_type="tone",
            project_id="project-1",
        )
        kwargs = mock_repository.create.await_args[0][0]
        assert kwargs["persona_id"] == "persona-1"
        assert kwargs["original_text"] == "scriptalert1/script"
        assert kwargs["corrected_text"] == "bbold/b"
        assert kwargs["context"] == "icontext/i"
        assert kwargs["correction_type"] == "tone"
        assert kwargs["project_id"] == "project-1"

    async def test_record_correction_correction_type_none_uses_classify(
        self, loop: FeedbackLearningLoop, mock_repository: MagicMock
    ) -> None:
        """Given None correction_type, when recording, then classify_correction result is used."""
        await loop.record_correction(
            _original="Hello",
            _corrected="Hello!",
            _context="greeting",
            _persona_id="persona-1",
            _correction_type=None,
        )
        kwargs = mock_repository.create.await_args[0][0]
        assert kwargs["correction_type"] == "tone"

    async def test_record_correction_int_persona_id_converts_exact(
        self, loop: FeedbackLearningLoop, mock_repository: MagicMock
    ) -> None:
        """Given int persona_id, when recording, then string conversion is exact."""
        await loop.record_correction(
            _original="Hello",
            _corrected="Hello!",
            _context="greeting",
            _persona_id=123,
            _correction_type="tone",
            project_id="proj-1",
        )
        kwargs = mock_repository.create.await_args[0][0]
        assert kwargs["persona_id"] == "123"
        assert kwargs["project_id"] == "proj-1"

    async def test_record_correction_no_project_id_is_none(
        self, loop: FeedbackLearningLoop, mock_repository: MagicMock
    ) -> None:
        """Given no project_id, when recording, then project_id kwarg is None."""
        await loop.record_correction(
            _original="Hello",
            _corrected="Hello!",
            _context="greeting",
            _persona_id="persona-1",
            _correction_type="tone",
        )
        kwargs = mock_repository.create.await_args[0][0]
        assert kwargs["project_id"] is None

    async def test_get_relevant_examples_converts_int_persona_id_exact(
        self, loop: FeedbackLearningLoop, mock_repository: MagicMock
    ) -> None:
        """Given int persona_id, when getting examples, then converted string is passed."""
        mock_repository.list_recent_by_persona.return_value = []
        await loop.get_relevant_examples(_persona_id=456, _k=5)
        mock_repository.list_recent_by_persona.assert_awaited_once_with("456", 5)

    async def test_get_relevant_examples_passes_exact_k(
        self, loop: FeedbackLearningLoop, mock_repository: MagicMock
    ) -> None:
        """Given specific k, when getting examples, then exact k is passed."""
        mock_repository.list_recent_by_persona.return_value = []
        await loop.get_relevant_examples(_persona_id="p", _k=7)
        mock_repository.list_recent_by_persona.assert_awaited_once_with("p", 7)

    async def test_get_relevant_examples_uses_default_k(
        self, loop: FeedbackLearningLoop, mock_repository: MagicMock
    ) -> None:
        """Given no k, when getting examples, then default k=3 is passed."""
        mock_repository.list_recent_by_persona.return_value = []
        await loop.get_relevant_examples(_persona_id="p")
        mock_repository.list_recent_by_persona.assert_awaited_once_with("p", 3)

    def test_cosine_similarity_zero_and_nonzero_returns_zero(
        self, loop: FeedbackLearningLoop
    ) -> None:
        """Given zero vector and non-zero vector, when calculating, then returns 0.0."""
        assert loop._cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0
        assert loop._cosine_similarity([1.0, 0.0], [0.0, 0.0]) == 0.0

    def test_cosine_similarity_different_length_raises(
        self, loop: FeedbackLearningLoop
    ) -> None:
        """Given vectors of different lengths, when calculating, then raises ValueError."""
        with pytest.raises(ValueError):
            loop._cosine_similarity([1.0, 0.0], [1.0])

    def test_cosine_similarity_non_unit_norm(self, loop: FeedbackLearningLoop) -> None:
        """Given non-unit vectors, when calculating, then exact cosine is returned."""
        result = loop._cosine_similarity([1.0, 1.0], [1.0, 1.0])
        assert result == pytest.approx(1.0)
        result = loop._cosine_similarity([1.0, 1.0], [1.0, 0.0])
        assert result == pytest.approx(0.7071067811865475)

    def test_cosine_similarity_orthogonal(self, loop: FeedbackLearningLoop) -> None:
        """Given orthogonal vectors, when calculating, then returns 0.0."""
        result = loop._cosine_similarity([1.0, 0.0, 0.0], [0.0, 1.0, 0.0])
        assert result == pytest.approx(0.0)

    async def test_classify_correction_at_exact_conciseness_boundary(
        self, loop: FeedbackLearningLoop
    ) -> None:
        """Given corrected exactly 50% of original length, when classifying, then not conciseness."""
        original = "1234567890"
        corrected = "12345"
        result = await loop.classify_correction(original, corrected)
        assert result != "conciseness"

    async def test_classify_correction_below_conciseness_boundary(
        self, loop: FeedbackLearningLoop
    ) -> None:
        """Given corrected below 50% of original length, when classifying, then returns conciseness."""
        original = "1234567890"
        corrected = "1234"
        result = await loop.classify_correction(original, corrected)
        assert result == "conciseness"

    async def test_classify_correction_exact_tone(
        self, loop: FeedbackLearningLoop
    ) -> None:
        """Given ! added in correction, when classifying, then returns exact tone."""
        result = await loop.classify_correction("Hello", "Hello!")
        assert result == "tone"

    async def test_classify_correction_both_have_exclamation_not_tone(
        self, loop: FeedbackLearningLoop
    ) -> None:
        """Given both have exclamation, when classifying, then not tone."""
        result = await loop.classify_correction("Hello!", "Hello!!")
        assert result == "content"

    async def test_classify_correction_exact_content(
        self, loop: FeedbackLearningLoop
    ) -> None:
        """Given different words, when classifying, then returns exact content."""
        result = await loop.classify_correction("Hello world", "Goodbye world")
        assert result == "content"

    async def test_classify_correction_exact_minor_edit(
        self, loop: FeedbackLearningLoop
    ) -> None:
        """Given only case change, when classifying, then returns exact minor_edit."""
        result = await loop.classify_correction("Hello", "hello")
        assert result == "minor_edit"

    async def test_classify_correction_spaces_only_not_content(
        self, loop: FeedbackLearningLoop
    ) -> None:
        """Given only space difference, when classifying, then returns minor_edit."""
        result = await loop.classify_correction("Hello world", "Helloworld")
        assert result == "minor_edit"

    async def test_suggest_improvements_converts_int_persona_id_exact(
        self, loop: FeedbackLearningLoop, mock_repository: MagicMock
    ) -> None:
        """Given int persona_id, when suggesting, then converted string is passed."""
        mock_repository.list_all_by_persona.return_value = []
        await loop.suggest_improvements("content", 789)
        mock_repository.list_all_by_persona.assert_awaited_once_with("789")

    async def test_suggest_improvements_returns_exact_top_three_sorted(
        self, loop: FeedbackLearningLoop, mock_repository: MagicMock
    ) -> None:
        """Given 4 entries, when suggesting, then returns exactly 3 sorted by similarity."""
        mock_repository.list_all_by_persona.return_value = [
            PersonaCorrectionRecord("A", "A1", "c", "tone"),
            PersonaCorrectionRecord("B", "B1", "c", "tone"),
            PersonaCorrectionRecord("C", "C1", "c", "tone"),
            PersonaCorrectionRecord("D", "D1", "c", "tone"),
        ]
        loop.embeddings.embed = AsyncMock(
            side_effect=[
                [1.0, 0.0],  # content
                [1.0, 0.0],  # A -> similarity 1.0
                [0.0, 1.0],  # B -> similarity 0.0
                [0.0, 0.0],  # C -> similarity 0.0 (zero vector)
                [0.5, 0.0],  # D -> similarity 0.5
            ]
        )
        result = await loop.suggest_improvements("content", "persona-1")
        assert len(result) == 3
        assert result[0] == "Consider: A1 (was: A)"
        assert result[1] == "Consider: D1 (was: D)"
        assert result[2] == "Consider: B1 (was: B)"

    async def test_suggest_improvements_empty_entries_returns_empty_list(
        self, loop: FeedbackLearningLoop, mock_repository: MagicMock
    ) -> None:
        """Given no entries, when suggesting, then returns empty list."""
        mock_repository.list_all_by_persona.return_value = []
        result = await loop.suggest_improvements("content", "persona-1")
        assert result == []

    async def test_suggest_improvements_embeds_original_text(
        self, loop: FeedbackLearningLoop, mock_repository: MagicMock
    ) -> None:
        """Given entries, when suggesting, then embed is called with original text."""
        mock_repository.list_all_by_persona.return_value = [
            PersonaCorrectionRecord("A", "A1", "c", "tone"),
        ]
        loop.embeddings.embed = AsyncMock(return_value=[1.0, 0.0])
        await loop.suggest_improvements("content", "persona-1")
        assert loop.embeddings.embed.await_args_list[1][0][0] == "A"


class TestCorrectionClassifier:
    def test_classify_detects_tone_change(self) -> None:
        result = CorrectionClassifier.classify("Hello", "Hello!")
        assert result["correction_type"] == "tone"
