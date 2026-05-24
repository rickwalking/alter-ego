"""Quality Agent for rubric evaluation and scoring."""

from typing import Protocol, cast

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage

from rag_backend.agents.input_sanitizer import sanitize_llm_input
from rag_backend.domain.models.rubric import EvaluationMethod, QualityRubric, RubricCriterion
from rag_backend.infrastructure.monitoring_langfuse import get_langfuse_handler


class EmbeddingServiceProtocol(Protocol):
    async def embed_dense(self, texts: list[str]) -> list[list[float]]: ...


class QualityAgent:
    """Evaluates content against rubrics and provides actionable feedback."""

    def __init__(
        self,
        rubric: QualityRubric,
        llm: BaseChatModel,
        embedding_service: EmbeddingServiceProtocol | None = None,
    ) -> None:
        self.rubric = rubric
        self.llm = llm
        self._embedding_service = embedding_service

    async def evaluate(self, content: str, sources: list[str] | None = None) -> dict[str, object]:
        """Evaluate content against the rubric."""
        content = sanitize_llm_input(content)
        if sources:
            sources = [sanitize_llm_input(s) for s in sources]
        sources_str = "\n".join(sources) if sources else "No sources provided"
        prompt = self._build_evaluation_prompt(content, sources_str)

        messages: list[BaseMessage] = [HumanMessage(content=prompt)]
        response = await self.llm.ainvoke(messages, callbacks=get_langfuse_handler())
        return self._parse_evaluation_response(cast(str, response.content))

    def _build_evaluation_prompt(self, content: str, sources_str: str) -> str:
        """Build the evaluation prompt."""
        criteria_str = "\n".join(f"{c['name']}: {c['description']}" for c in self.rubric.criteria)
        return f"""Evaluate this content against the following quality rubric.

RUBRIC NAME: {self.rubric.name}
DESCRIPTION: {self.rubric.description}
APPLICABLE TO: {", ".join(self.rubric.applicable_content_types)}

CRITERIA:
{criteria_str}

CONTENT TO EVALUATE:
{content}

SOURCES USED:
{sources_str}

Format your response as JSON with criterion_scores, overall_score, passed, feedback.
"""

    def _parse_evaluation_response(self, response: str) -> dict[str, object]:
        """Parse the evaluation response into a structured dictionary."""
        try:
            data = __import__("json").loads(response)
            return {
                "overall_score": float(data.get("overall_score", 0)),
                "criteria_scores": {
                    k: {
                        "score": float(v.get("score", 0)),
                        "weight": float(v.get("weight", 0)),
                        "passed": bool(v.get("passed", False)),
                        "feedback": v.get("feedback", ""),
                    }
                    for k, v in data.get("criterion_scores", {}).items()
                },
                "feedback": data.get("feedback", []),
                "passed": bool(data.get("passed", False)),
            }
        except Exception:
            return {
                "overall_score": 0.0,
                "criteria_scores": {},
                "feedback": [],
                "passed": False,
            }

    async def evaluate_criterion(
        self,
        criterion: RubricCriterion,
        content: str,
        sources: list[str] | None = None,
    ) -> float:
        """Evaluate a single criterion."""
        if criterion["evaluation_method"] == EvaluationMethod.AI_AUTO:
            return await self._ai_evaluate(criterion, content, sources or [])
        return 75.0

    async def _ai_evaluate(
        self,
        criterion: RubricCriterion,
        content: str,
        sources: list[str],
    ) -> float:
        """AI-only evaluation of a criterion."""
        prompt = criterion["prompt_template"].format(content=content, sources=sources)

        messages: list[BaseMessage] = [HumanMessage(content=prompt)]
        response = await self.llm.ainvoke(messages, callbacks=get_langfuse_handler())
        return self._extract_score(cast(str, response.content))

    def _extract_score(self, response: str) -> float:
        """Extract a numeric score from the LLM response."""
        import re

        match = re.search(r"[\d.]+", response)
        if match:
            return float(match.group(0))
        return 50.0

    async def generate_improvement_suggestions(
        self,
        criterion: RubricCriterion,
        content: str,
        score: float,
    ) -> list[str]:
        """Generate actionable improvement suggestions for a criterion."""
        content = sanitize_llm_input(content)
        if score >= criterion["min_threshold"]:
            return []

        prompt = f"""Generate 3-5 specific, actionable suggestions to improve this criterion.

CRITERION: {criterion["name"]}
DESCRIPTION: {criterion["description"]}
CURRENT SCORE: {score}/100
THRESHOLD: {criterion["min_threshold"]}/100

CONTENT: {content}
"""

        messages: list[BaseMessage] = [HumanMessage(content=prompt)]
        response = await self.llm.ainvoke(messages, callbacks=get_langfuse_handler())

        suggestions = __import__("re").split(r"[\n·•\-\*]", cast(str, response.content))
        return [
            s.strip() for s in suggestions if s.strip() and not s.strip().startswith("Here are")
        ]

    async def calculate_originality(self, content: str, sources: list[str]) -> float:
        """Calculate originality score based on embedding similarity to sources."""
        content = sanitize_llm_input(content)
        sources = [sanitize_llm_input(s) for s in sources if s.strip()]
        if not sources or self._embedding_service is None:
            base_score = 50.0
            source_bonus = min(len(sources) * 10, 30)
            content_bonus = min(len(content) / 1000, 20)
            return min(100.0, base_score + source_bonus + content_bonus)

        texts = [content, *sources]
        embeddings = await self._embedding_service.embed_dense(texts)
        content_vector = embeddings[0]
        max_similarity = 0.0
        for source_vector in embeddings[1:]:
            similarity = self._cosine_similarity(content_vector, source_vector)
            max_similarity = max(max_similarity, similarity)

        return round(max(0.0, min(100.0, (1.0 - max_similarity) * 100)), 2)

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        dot_product = sum(x * y for x, y in zip(a, b, strict=True))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(dot_product / (norm_a * norm_b))

    async def evaluate_eeat(
        self,
        content: str,
        sources: list[str],
    ) -> dict[str, float]:
        """Evaluate E-E-A-T dimensions."""
        content = sanitize_llm_input(content)
        sources = [sanitize_llm_input(s) for s in sources]
        prompt = f"""Evaluate E-E-A-T for content.

CONTENT: {content[:500]}
SOURCES: {sources}

Format as JSON with experience, expertise, authoritativeness, trustworthiness, overall_eeat.
"""

        messages: list[BaseMessage] = [HumanMessage(content=prompt)]
        response = await self.llm.ainvoke(messages, callbacks=get_langfuse_handler())

        try:
            data = __import__("json").loads(cast(str, response.content))
            return {
                "experience": float(data.get("experience", 50)),
                "expertise": float(data.get("expertise", 50)),
                "authoritativeness": float(data.get("authoritativeness", 50)),
                "trustworthiness": float(data.get("trustworthiness", 50)),
                "overall_eeat": float(data.get("overall_eeat", 50)),
            }
        except Exception:
            return {
                "experience": 50,
                "expertise": 50,
                "authoritativeness": 50,
                "trustworthiness": 50,
                "overall_eeat": 50,
            }


__all__ = ["QualityAgent"]
