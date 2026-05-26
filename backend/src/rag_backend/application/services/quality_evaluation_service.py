"""Quality evaluation service with threshold gates (AI-009)."""

from __future__ import annotations

from uuid import UUID

from langchain_core.language_models import BaseChatModel

from rag_backend.agents.quality_agent import QualityAgent
from rag_backend.domain.constants.persona import VOICE_MATCH_MIN_SCORE
from rag_backend.domain.models.rubric import QualityRubric
from rag_backend.infrastructure.container import get_container
from rag_backend.infrastructure.monitoring_langfuse import (
    add_quality_score,
    add_voice_match_score,
    create_workflow_trace,
)


class QualityEvaluationService:
    """Runs QualityAgent evaluation and applies rubric thresholds."""

    def __init__(self, llm: BaseChatModel) -> None:
        self._llm = llm
        container = get_container()
        self._embedding_service = container.embedding_service()

    def _build_agent(self, rubric: QualityRubric) -> QualityAgent:
        return QualityAgent(
            rubric=rubric,
            llm=self._llm,
            embedding_service=self._embedding_service,
        )

    async def evaluate_with_thresholds(
        self,
        rubric: QualityRubric,
        content: str,
        sources: list[str] | None = None,
        *,
        project_id: UUID | None = None,
        user_id: str = "system",
        content_type: str = "carousel",
    ) -> dict[str, object]:
        """Evaluate content and attach Langfuse scores when configured."""
        agent = self._build_agent(rubric)
        result = await agent.evaluate(content, sources)
        originality_score = await agent.calculate_originality(content, sources or [])
        result["originality_score"] = originality_score

        trace = None
        if project_id is not None:
            trace = create_workflow_trace(
                project_id=project_id,
                user_id=user_id,
                content_type=content_type,
                metadata={"phase": "quality_check"},
            )

        overall = float(result.get("overall_score", 0))
        passed = bool(result.get("passed", False))

        if trace is not None:
            add_quality_score(
                trace=trace,
                criterion="overall",
                score=overall,
                threshold=VOICE_MATCH_MIN_SCORE,
                passed=passed,
            )
            add_quality_score(
                trace=trace,
                criterion="originality",
                score=originality_score,
                threshold=VOICE_MATCH_MIN_SCORE,
                passed=originality_score >= VOICE_MATCH_MIN_SCORE,
            )
            criteria_scores = result.get("criteria_scores", {})
            if isinstance(criteria_scores, dict):
                for name, data in criteria_scores.items():
                    if isinstance(data, dict):
                        add_quality_score(
                            trace=trace,
                            criterion=str(name),
                            score=float(data.get("score", 0)),
                            threshold=VOICE_MATCH_MIN_SCORE,
                            passed=bool(data.get("passed", False)),
                        )

        return result

    async def evaluate_voice_and_quality(
        self,
        rubric: QualityRubric,
        content: str,
        voice_score: float,
        sources: list[str] | None = None,
        *,
        project_id: UUID | None = None,
    ) -> dict[str, object]:
        """Combine rubric evaluation with voice match score on trace."""
        evaluation = await self.evaluate_with_thresholds(
            rubric=rubric,
            content=content,
            sources=sources,
            project_id=project_id,
        )
        if project_id is not None:
            trace = create_workflow_trace(
                project_id=project_id,
                user_id="system",
                content_type="carousel",
                metadata={"phase": "voice_check"},
            )
            add_voice_match_score(trace=trace, score=voice_score)
        evaluation["voice_match_score"] = voice_score
        return evaluation


__all__ = ["QualityEvaluationService"]
