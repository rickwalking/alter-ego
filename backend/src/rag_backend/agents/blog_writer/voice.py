"""Persona voice scorer of the blog quality gate (AE-0425, ADR-0003).

Implements the ``VoiceScorer`` port with ``PersonaAgent.evaluate_match`` on the
fast model (persona scoring is a fast-role task, ADR-0014). Writing samples are
sanitized before they reach the scoring prompt. A scorer failure is a writer
failure (the run fails recoverable); an unparsable answer scores 0, which the
gate treats as "rewrite once".
"""

from __future__ import annotations

from langchain_core.language_models import BaseChatModel

from rag_backend.agents.blog_writer.constants import ERR_SCORER_FAILED
from rag_backend.agents.blog_writer.persona_block import sanitized_persona
from rag_backend.agents.constants import KEY_OVERALL
from rag_backend.agents.persona_agent import PersonaAgent
from rag_backend.domain.models.blog_generation import VoiceScore, WriterFailedError
from rag_backend.domain.models.persona import PersonaProfile


def _breakdown(result: dict[str, object]) -> dict[str, float | list[str]]:
    breakdown: dict[str, float | list[str]] = {}
    for key, value in result.items():
        if isinstance(value, int | float):
            breakdown[key] = float(value)
        elif isinstance(value, list):
            breakdown[key] = [str(item) for item in value]
    return breakdown


class PersonaVoiceScorer:
    """``PersonaAgent.evaluate_match`` → :class:`VoiceScore` (0-100)."""

    def __init__(self, persona: PersonaProfile, llm: BaseChatModel) -> None:
        self._agent = PersonaAgent(sanitized_persona(persona), llm)

    async def score(self, text: str) -> VoiceScore:
        """Score ``text`` against the persona."""
        try:
            result = await self._agent.evaluate_match(text)
        except Exception as exc:
            raise WriterFailedError(ERR_SCORER_FAILED.format(reason=str(exc))) from exc
        overall = result.get(KEY_OVERALL, 0.0)
        return VoiceScore(
            overall=float(overall) if isinstance(overall, int | float) else 0.0,
            breakdown=_breakdown(result),
        )


__all__ = ["PersonaVoiceScorer"]
