"""Unit tests for QualityEvaluationService."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from rag_backend.application.services.quality_evaluation_service import (
    QualityEvaluationService,
)
from rag_backend.domain.models.rubric import QualityRubric


@pytest.fixture
def rubric() -> QualityRubric:
    return QualityRubric(
        id=uuid4(),
        name="Blog Quality",
        description="Test rubric",
        criteria=[],
        is_default=True,
    )


@pytest.mark.asyncio
class TestQualityEvaluationService:
    async def test_evaluate_with_thresholds_adds_originality_score(
        self, rubric: QualityRubric
    ) -> None:
        llm = MagicMock()
        mock_container = MagicMock()
        mock_container.embedding_service.return_value = MagicMock()

        mock_agent = AsyncMock()
        mock_agent.evaluate = AsyncMock(
            return_value={
                "overall_score": 82.0,
                "passed": True,
                "criteria_scores": {},
            }
        )
        mock_agent.calculate_originality = AsyncMock(return_value=88.0)

        with (
            patch(
                "rag_backend.application.services.quality_evaluation_service.get_container",
                return_value=mock_container,
            ),
            patch.object(
                QualityEvaluationService, "_build_agent", return_value=mock_agent
            ),
        ):
            service = QualityEvaluationService(llm=llm)
            result = await service.evaluate_with_thresholds(
                rubric=rubric,
                content="Sample blog content",
            )

        assert result["originality_score"] == 88.0
        assert result["overall_score"] == 82.0
