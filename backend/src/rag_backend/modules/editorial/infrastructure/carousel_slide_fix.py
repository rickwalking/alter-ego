"""The autopilot model fix of failing slides, in-process (AE-0401).

``run_slide_fix`` builds the fast-role model (``build_chat_model(settings,
LLM_ROLE_FAST)``), the project's persona (``PovInputsAcl.project_persona``)
for the style guide and the voice re-score, and delegates to the carousel
``SlideFixService``. Imports are lazy like the rest of the automation seam
(the editorial facade loads while the ORM registry is still initialising).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.slide_fix import AUTOFIX_MODEL_ATTEMPTS
from rag_backend.modules.editorial.infrastructure.carousel_automation import (
    EditorialWorkflowEngine,
)
from rag_backend.modules.editorial.infrastructure.pov_inputs import PovInputsAcl

if TYPE_CHECKING:
    from rag_backend.agents.persona_agent import PersonaAgent
    from rag_backend.application.services.carousel.slide_fix_types import (
        SlideFixOutcome,
        SlideFixResult,
        SlideFixTools,
    )

SlideFixModelFactory = Callable[[], BaseChatModel]


@dataclass(frozen=True, kw_only=True)
class SlideFixRequest:
    """One carousel gate; ``model_factory`` overrides the fast model (tests)."""

    session: AsyncSession
    project_id: str
    expected_version: int
    phase: str
    engine: EditorialWorkflowEngine | None = None
    attempts: int = AUTOFIX_MODEL_ATTEMPTS
    model_factory: SlideFixModelFactory | None = None


@dataclass(frozen=True, kw_only=True)
class SlideFixAttemptReport:
    """One model attempt on one slide."""

    slide_index: int
    attempt: int
    rules_before: tuple[str, ...]
    rules_after: tuple[str, ...]
    outcome: str


@dataclass(frozen=True, kw_only=True)
class SlideFixSlideReport:
    """Where one slide ended, with its current PT text for the owner."""

    slide_index: int
    fixed: bool
    rules: tuple[str, ...]
    text: str
    attempts: int


@dataclass(frozen=True, kw_only=True)
class SlideFixReport:
    """``status`` is ``AUTOFIX_STATUS_*``."""

    status: str
    slides: tuple[SlideFixSlideReport, ...] = ()
    attempts: tuple[SlideFixAttemptReport, ...] = ()
    unfixable_rules: tuple[str, ...] = ()


class _ModelRewriter:
    """``SlideRewriter`` on a LangChain chat model with the Langfuse config."""

    def __init__(self, llm: BaseChatModel, config: RunnableConfig) -> None:
        self._llm = llm
        self._config = config

    async def rewrite(self, prompt: str) -> str:
        response = await self._llm.ainvoke([HumanMessage(content=prompt)], self._config)
        return str(response.content)


class _PersonaScorer:
    """``VoiceScorer`` on ``PersonaAgent.evaluate_match`` (0-100 overall)."""

    def __init__(self, agent: PersonaAgent) -> None:
        self._agent = agent

    async def score(self, text: str) -> float:
        from rag_backend.application.services.carousel.slide_fix_targets import (
            overall_score,
        )

        return overall_score(await self._agent.evaluate_match(text))


def _model(request: SlideFixRequest) -> BaseChatModel:
    if request.model_factory is not None:
        return request.model_factory()
    from rag_backend.infrastructure.config.llm_routing_constants import LLM_ROLE_FAST
    from rag_backend.infrastructure.config.settings import get_settings
    from rag_backend.infrastructure.external.chat_model_factory import build_chat_model

    return build_chat_model(get_settings(), LLM_ROLE_FAST)


async def _tools(request: SlideFixRequest, llm: BaseChatModel) -> SlideFixTools:
    from rag_backend.agents.persona_agent import PersonaAgent
    from rag_backend.application.services.carousel.slide_fix_types import (
        SlideFixTools,
    )
    from rag_backend.infrastructure.monitoring_langfuse import (
        get_langfuse_runnable_config,
    )

    rewriter = _ModelRewriter(llm, get_langfuse_runnable_config())
    persona = await PovInputsAcl(request.session).project_persona(request.project_id)
    if persona is None:
        return SlideFixTools(rewriter=rewriter)
    agent = PersonaAgent(persona=persona, llm=llm)
    return SlideFixTools(
        rewriter=rewriter, scorer=_PersonaScorer(agent), style_guide=agent.style_guide()
    )


def _slide(result: SlideFixResult) -> SlideFixSlideReport:
    from rag_backend.application.services.carousel.slide_fix_loop import (
        current_text,
    )

    return SlideFixSlideReport(
        slide_index=result.slide_index,
        fixed=result.fixed,
        rules=tuple(dict.fromkeys(issue.code for issue in result.issues)),
        text=current_text(result),
        attempts=len(result.attempts),
    )


def _report(outcome: SlideFixOutcome) -> SlideFixReport:
    return SlideFixReport(
        status=outcome.status,
        slides=tuple(_slide(result) for result in outcome.results),
        attempts=tuple(
            SlideFixAttemptReport(
                slide_index=attempt.slide_index,
                attempt=attempt.attempt,
                rules_before=attempt.rules_before,
                rules_after=attempt.rules_after,
                outcome=attempt.outcome,
            )
            for result in outcome.results
            for attempt in result.attempts
        ),
        unfixable_rules=outcome.unfixable_rules,
    )


async def run_slide_fix(request: SlideFixRequest) -> SlideFixReport:
    """Model-fix the gate's failing slides and persist the fixed ones."""
    from rag_backend.application.services.carousel.slide_fix_service import (
        SlideFixDeps,
        SlideFixService,
    )
    from rag_backend.application.services.carousel.slide_fix_types import (
        SlideFixCommand,
        SlideFixSettings,
    )
    from rag_backend.infrastructure.config.settings import get_settings
    from rag_backend.infrastructure.database.carousel_repository import (
        PostgresCarouselRepository,
    )

    service = SlideFixService(
        SlideFixDeps(
            db=request.session,
            repo=PostgresCarouselRepository(session=request.session),
            workflow=request.engine,
            tools=await _tools(request, _model(request)),
            settings=SlideFixSettings(
                attempts=request.attempts,
                concurrency=get_settings().content_draft_concurrency,
            ),
        )
    )
    outcome = await service.fix(
        SlideFixCommand(
            project_id=request.project_id,
            expected_version=request.expected_version,
            phase=request.phase,
        )
    )
    return _report(outcome)


__all__ = [
    "SlideFixAttemptReport",
    "SlideFixModelFactory",
    "SlideFixReport",
    "SlideFixRequest",
    "SlideFixSlideReport",
    "run_slide_fix",
]
