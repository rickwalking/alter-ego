"""Assertion-bearing tests that pin exact FeedbackLearningLoop behaviour.

Feature: Continuous persona improvement from human corrections
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from rag_backend.agents.feedback_learning import FeedbackLearningLoop
from rag_backend.infrastructure.database.persona_correction_repository import (
    PersonaCorrectionRecord,
)

DEFAULT_EXAMPLES = 3


@pytest.fixture
def embeddings() -> MagicMock:
    """An embedding client mapping known texts to fixed vectors."""
    vectors = {
        "content": [1.0, 0.0],
        "orig-a": [1.0, 0.0],
        "corr-a": [1.0, 0.0],
        "orig-b": [1.0, 0.0],
        "corr-b": [0.0, 1.0],
    }
    client = MagicMock()
    client.embed = AsyncMock(side_effect=lambda text: vectors[text])
    return client


@pytest.fixture
def repository() -> MagicMock:
    """A correction repository with one stored correction."""
    record = MagicMock(spec=PersonaCorrectionRecord)
    record.original_text = "orig-a"
    record.corrected_text = "corr-a"
    record.context = "ctx"
    record.correction_type = "tone"
    repo = MagicMock()
    repo.list_recent_by_persona = AsyncMock(return_value=[])
    repo.list_all_by_persona = AsyncMock(return_value=[record])
    return repo


@pytest.fixture
def loop(embeddings: MagicMock, repository: MagicMock) -> FeedbackLearningLoop:
    """A feedback loop over the mocked repository and embeddings."""
    feedback = FeedbackLearningLoop(session=AsyncMock(), embeddings=embeddings)
    feedback._repository = repository
    return feedback


# Scenario: Relevant examples default to three
async def test_relevant_examples_default_limit(
    loop: FeedbackLearningLoop, repository: MagicMock
) -> None:
    """Without k, the three most recent corrections are requested."""
    await loop.get_relevant_examples("persona-1")

    repository.list_recent_by_persona.assert_awaited_once_with(
        "persona-1", DEFAULT_EXAMPLES
    )


# Scenario: A whitespace-only change is a minor edit
async def test_whitespace_only_change_is_minor_edit(
    loop: FeedbackLearningLoop,
) -> None:
    """Removing spaces only is classified as a minor edit."""
    assert await loop.classify_correction("ab cd", "a b c d") == "minor_edit"


# Scenario: Suggestions embed the content being improved
async def test_suggestions_embed_content_first(
    loop: FeedbackLearningLoop, embeddings: MagicMock
) -> None:
    """The content itself is embedded before the stored corrections."""
    result = await loop.suggest_improvements("content", "persona-1")

    assert embeddings.embed.await_args_list[0].args == ("content",)
    assert result == ["Consider: corr-a (was: orig-a)"]


# Scenario: Voice drift averages every sample
async def test_voice_drift_averages_all_samples(
    loop: FeedbackLearningLoop, embeddings: MagicMock
) -> None:
    """Drift is one minus the mean similarity across all samples."""
    result = await loop.analyze_voice_drift(
        "persona-1", [("orig-a", "corr-a"), ("orig-b", "corr-b")]
    )

    assert result == {"drift_score": 0.5, "trends": ["voice_drifting"]}
    assert [call.args for call in embeddings.embed.await_args_list] == [
        ("orig-a",),
        ("corr-a",),
        ("orig-b",),
        ("corr-b",),
    ]
