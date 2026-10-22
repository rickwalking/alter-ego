"""The carousel's quality rubric in prompts: drafting guidance and the 0-100 judge.

``render_rubric_criteria`` is the block every content-draft prompt ends with;
``CarouselRubricJudge`` scores the drafted slides against the same criteria in
one structured-JSON call (re-rolled and repaired by ``ainvoke_json``).
A criterion's ``prompt_template`` is shown as guidance with its ``{content}`` /
``{sources}`` placeholders dropped.
"""

from __future__ import annotations

import re

from langchain_core.language_models import BaseChatModel

from rag_backend.agents.llm_json_retry import JsonRetryPolicy, ainvoke_json
from rag_backend.agents.prompts.registry import render_prompt
from rag_backend.domain.carousel_rubric_scoring import build_rubric_evaluation
from rag_backend.domain.constants.carousel_rubric import (
    ERR_RUBRIC_SCORES_INVALID,
    RUBRIC_PROMPT_CRITERIA,
    RUBRIC_PROMPT_DOMAIN,
    RUBRIC_PROMPT_EVALUATE,
    RUBRIC_PROMPT_VERSION,
)
from rag_backend.domain.models.carousel_rubric import (
    CarouselRubric,
    CarouselRubricEvaluation,
    JudgedCriterion,
    RubricJudgeRequest,
)
from rag_backend.domain.rubric_scoring import threshold_percent
from rag_backend.infrastructure.llm.json_utils import extract_json

_PLACEHOLDER = re.compile(r"\{(content|sources)\}")
_JUDGE_AGENT = "carousel_rubric_judge"
_JUDGE_MODEL_ID = "carousel-rubric-judge"
_RUN_DETAIL = "rubric scores"


def rubric_prompt_rows(rubric: CarouselRubric) -> list[dict[str, object]]:
    """The criteria as the prompt templates read them."""
    return [
        {
            "id": criterion["id"],
            "name": criterion["name"],
            "description": criterion.get("description", ""),
            "scale": str(criterion.get("scoring_scale", "")),
            "threshold": round(threshold_percent(criterion)),
            "guidance": _PLACEHOLDER.sub(
                "", str(criterion.get("prompt_template", ""))
            ).strip(),
        }
        for criterion in rubric.criteria
    ]


def render_rubric_criteria(rubric: CarouselRubric) -> str:
    """The rubric block appended to a content-draft prompt."""
    text, _config = render_prompt(
        RUBRIC_PROMPT_DOMAIN,
        RUBRIC_PROMPT_CRITERIA,
        variables={"rubric_name": rubric.name, "criteria": rubric_prompt_rows(rubric)},
        version=RUBRIC_PROMPT_VERSION,
    )
    return text.strip()


def _answer(item: object) -> JudgedCriterion:
    if not isinstance(item, dict):
        raise TypeError(ERR_RUBRIC_SCORES_INVALID)
    score = item.get("score")
    if isinstance(score, bool) or not isinstance(score, int | float):
        raise TypeError(ERR_RUBRIC_SCORES_INVALID)
    return JudgedCriterion(
        criterion_id=str(item.get("id", "")),
        score=float(score),
        feedback=str(item.get("feedback", "")),
    )


def parse_judge_answer(raw: str) -> tuple[list[JudgedCriterion], str]:
    """The judge's criteria and overall feedback; ``ValueError`` / ``TypeError`` when malformed."""
    payload = extract_json(raw)
    if not isinstance(payload, dict) or not isinstance(payload.get("criteria"), list):
        raise TypeError(ERR_RUBRIC_SCORES_INVALID)
    answers = [_answer(item) for item in payload["criteria"]]
    return answers, str(payload.get("feedback", ""))


class CarouselRubricJudge:
    """Scores a carousel's drafted slides against its rubric (0-100)."""

    def __init__(self, llm: BaseChatModel) -> None:
        self._llm = llm

    async def score(self, request: RubricJudgeRequest) -> CarouselRubricEvaluation:
        """One judge call; raises ``ValueError`` when the answer never parses."""
        rubric = request.rubric
        prompt, _config = render_prompt(
            RUBRIC_PROMPT_DOMAIN,
            RUBRIC_PROMPT_EVALUATE,
            variables={
                "rubric_name": rubric.name,
                "criteria": rubric_prompt_rows(rubric),
                "content": request.content,
            },
            version=RUBRIC_PROMPT_VERSION,
        )
        (answers, feedback), _raw = await ainvoke_json(
            self._llm,
            prompt,
            JsonRetryPolicy(
                parse=parse_judge_answer,
                agent=_JUDGE_AGENT,
                model_id=_JUDGE_MODEL_ID,
                run_detail=_RUN_DETAIL,
            ),
        )
        return build_rubric_evaluation(rubric, answers, feedback)


__all__ = [
    "CarouselRubricJudge",
    "parse_judge_answer",
    "render_rubric_criteria",
    "rubric_prompt_rows",
]
