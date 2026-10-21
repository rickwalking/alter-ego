"""The autopilot model fix of failing slides, in-process.

``run_slide_fix`` builds the fast-role model (``build_chat_model(settings,
LLM_ROLE_FAST)``), the reasoning-role model for the escalation attempts
(not built when they are off), the project's persona
(``PovInputsAcl.project_persona``) for the style guide and the voice re-score,
and delegates to the carousel ``SlideFixService``. Imports are lazy like the
rest of the automation seam (the editorial facade loads while the ORM
registry is still initialising).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.slide_fix import (
    AUTOFIX_ESCALATION_ATTEMPTS,
    AUTOFIX_MODEL_ATTEMPTS,
)
from rag_backend.modules.editorial.infrastructure.carousel_automation import (
    EditorialWorkflowEngine,
)
from rag_backend.modules.editorial.infrastructure.pov_inputs import PovInputsAcl

if TYPE_CHECKING:
    from rag_backend.agents.persona_agent import PersonaAgent
    from rag_backend.application.services.carousel.persona_judge import VoiceJudge
    from rag_backend.application.services.carousel.slide_fix_types import (
        SlideFixOutcome,
        SlideFixResult,
        SlideFixTools,
        SlideRewriter,
    )
    from rag_backend.domain.models.persona import PersonaProfile

SlideFixModelFactory = Callable[[], BaseChatModel]


@dataclass(frozen=True, kw_only=True)
class SlideFixRequest:
    """One carousel gate; the factories override the models (tests).

    ``model_factory`` replaces the fast model and, without an
    ``escalation_model_factory``, the reasoning one too, so a test never
    builds a real model.
    """

    session: AsyncSession
    project_id: str
    expected_version: int
    phase: str
    engine: EditorialWorkflowEngine | None = None
    attempts: int = AUTOFIX_MODEL_ATTEMPTS
    escalation_attempts: int = AUTOFIX_ESCALATION_ATTEMPTS
    model_factory: SlideFixModelFactory | None = None
    escalation_model_factory: SlideFixModelFactory | None = None


@dataclass(frozen=True, kw_only=True)
class SlideFixAttemptReport:
    """One model attempt on one slide."""

    slide_index: int
    attempt: int
    rules_before: tuple[str, ...]
    rules_after: tuple[str, ...]
    outcome: str
    model_role: str = ""


@dataclass(frozen=True, kw_only=True)
class SlideFixSlideReport:
    """Where one slide ended, with its current PT text for the owner.

    ``unscored_ticks`` is above zero when the judge could not score the slide's
    copy.
    """

    slide_index: int
    fixed: bool
    rules: tuple[str, ...]
    text: str
    attempts: int
    unscored_ticks: int = 0


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
    """``VoiceScorer`` on ``PersonaAgent.evaluate_match`` (0-100 overall).

    Retried once; None (unscored) when the judge gave no score.
    The retry runs on ``fallback`` (the next model of the queue).
    """

    def __init__(self, agent: VoiceJudge, fallback: VoiceJudge | None = None) -> None:
        self._agent = agent
        self._fallback = fallback

    async def score(self, text: str) -> float | None:
        from rag_backend.application.services.carousel.persona_judge import judge_voice
        from rag_backend.application.services.carousel.slide_fix_targets import (
            overall_score,
        )

        result = await judge_voice(self._agent, text, self._fallback)
        return None if result is None else overall_score(result)


def _role_model(role: str) -> BaseChatModel:
    from rag_backend.infrastructure.config.settings import get_settings
    from rag_backend.infrastructure.external.chat_model_factory import build_chat_model

    return build_chat_model(get_settings(), role)


def _model(request: SlideFixRequest) -> BaseChatModel:
    if request.model_factory is not None:
        return request.model_factory()
    from rag_backend.infrastructure.config.llm_routing_constants import LLM_ROLE_FAST

    return _role_model(LLM_ROLE_FAST)


def _escalation_model(request: SlideFixRequest) -> BaseChatModel | None:
    """The reasoning model, or None when the escalation is off."""
    if request.escalation_attempts <= 0:
        return None
    factory = request.escalation_model_factory or request.model_factory
    if factory is not None:
        return factory()
    from rag_backend.infrastructure.config.llm_routing_constants import (
        LLM_ROLE_REASONING,
    )

    return _role_model(LLM_ROLE_REASONING)


def _fallback_llm(llm: BaseChatModel) -> BaseChatModel | None:
    """The next model of the role's queue (or its fallback); None at the end."""
    from rag_backend.infrastructure.external.routed_chat_model import HasFallback

    return llm.as_fallback() if isinstance(llm, HasFallback) else None


def _fallback_judge(persona: PersonaProfile, llm: BaseChatModel) -> PersonaAgent | None:
    """The persona judge on the fallback model of ``llm``."""
    from rag_backend.agents.persona_agent import PersonaAgent

    fallback = _fallback_llm(llm)
    return None if fallback is None else PersonaAgent(persona=persona, llm=fallback)


def _escalation_rewriter(request: SlideFixRequest) -> SlideRewriter | None:
    from rag_backend.infrastructure.monitoring_langfuse import (
        get_langfuse_runnable_config,
    )

    llm = _escalation_model(request)
    if llm is None:
        return None
    return _ModelRewriter(llm, get_langfuse_runnable_config())


async def _tools(request: SlideFixRequest, llm: BaseChatModel) -> SlideFixTools:
    from rag_backend.agents.persona_agent import PersonaAgent
    from rag_backend.application.services.carousel.slide_fix_types import (
        SlideFixTools,
    )
    from rag_backend.infrastructure.monitoring_langfuse import (
        get_langfuse_runnable_config,
    )

    rewriter = _ModelRewriter(llm, get_langfuse_runnable_config())
    escalation = _escalation_rewriter(request)
    persona = await PovInputsAcl(request.session).project_persona(request.project_id)
    if persona is None:
        return SlideFixTools(rewriter=rewriter, escalation_rewriter=escalation)
    agent = PersonaAgent(persona=persona, llm=llm)
    return SlideFixTools(
        rewriter=rewriter,
        scorer=_PersonaScorer(agent, _fallback_judge(persona, llm)),
        style_guide=agent.style_guide(),
        escalation_rewriter=escalation,
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
        unscored_ticks=result.unscored_ticks,
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
                model_role=attempt.model_role,
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
                escalation_attempts=request.escalation_attempts,
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
