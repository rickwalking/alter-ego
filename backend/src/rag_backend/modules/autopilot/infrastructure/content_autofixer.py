"""``ContentAutofixer`` backed by the editorial facade (AE-0367).

The engine factory is optional: without it the inspection reads only the
slide rows (no outline key points, no research vocabulary) and the fix cannot
re-translate EN. The webhook, the notifier and the worker all pass one.

AE-0401: ``fix_slides`` is the model fix of the slides a gate repair left
failing, traced with ``phase=autofix`` and ``agent_name=slide_fixer``.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.slide_fix import (
    AUTOFIX_ESCALATION_ATTEMPTS,
    AUTOFIX_MODEL_ATTEMPTS,
    PERSONA_UNSCORED_MAX_TICKS,
)
from rag_backend.infrastructure.monitoring_langfuse import propagate_attributes
from rag_backend.modules.autopilot.autofix_constants import (
    AGENT_NAME_SLIDE_FIXER,
    PHASE_AUTOFIX,
)
from rag_backend.modules.autopilot.constants import (
    AGENT_NAME_AUTOPILOT,
    CONTENT_TYPE_CAROUSEL,
    LANGFUSE_FIELD_AGENT_NAME,
    LANGFUSE_FIELD_CONTENT_TYPE,
    LANGFUSE_FIELD_PHASE,
    LANGFUSE_FIELD_PROJECT_ID,
    LANGFUSE_FIELD_USER_ID,
)
from rag_backend.modules.autopilot.domain.autofix import (
    AutofixCommand,
    AutofixOutcome,
    AutofixStatus,
    FailingSlide,
    GateRepairCommand,
    GateRepairOutcome,
    QualityIssues,
    SlideFixAttemptRecord,
    SlideFixCommand,
    SlideFixOutcome,
)
from rag_backend.modules.autopilot.infrastructure.editorial_driver import EngineFactory
from rag_backend.modules.autopilot.webhook_constants import AUTOFIX_REWORK_PHASE
from rag_backend.modules.editorial.public import (
    AUTOFIX_STATUS_CONFLICT,
    AUTOFIX_STATUS_FIXED,
    OwnerAutofixRequest,
    SlideFixModelFactory,
    SlideFixReport,
    SlideFixRequest,
    inspect_owner_issues,
    read_project_owner_id,
    run_gate_repair,
    run_owner_autofix,
    run_slide_fix,
)

_STATUSES: dict[str, AutofixStatus] = {
    AUTOFIX_STATUS_FIXED: AutofixStatus.FIXED,
    AUTOFIX_STATUS_CONFLICT: AutofixStatus.CONFLICT,
}


@dataclass(frozen=True, kw_only=True)
class AutofixerConfig:
    """The bound session and, when available, the editorial engine factory."""

    session: AsyncSession
    engine_factory: EngineFactory | None = None
    # AE-0401: model attempts per failing slide (AUTOPILOT_AUTOFIX_ATTEMPTS)
    # and, for tests, the model the slide fix uses instead of the fast role.
    autofix_attempts: int = AUTOFIX_MODEL_ATTEMPTS
    slide_fix_model: SlideFixModelFactory | None = None
    # AE-0407: reasoning-model attempts after the fast ones
    # (AUTOPILOT_AUTOFIX_ESCALATION_ATTEMPTS) and, for tests, their model
    # (None: ``slide_fix_model`` when set, else the reasoning role).
    autofix_escalation_attempts: int = AUTOFIX_ESCALATION_ATTEMPTS
    slide_fix_escalation_model: SlideFixModelFactory | None = None
    # AE-0433: unscored ticks before "persona_judge_unavailable"
    # (AUTOPILOT_PERSONA_UNSCORED_MAX_TICKS).
    persona_unscored_max_ticks: int = PERSONA_UNSCORED_MAX_TICKS


class InProcessContentAutofixer:
    """Inspect and fix one carousel through the editorial facade."""

    def __init__(self, config: AutofixerConfig) -> None:
        self._config = config

    async def inspect(self, project_id: str) -> QualityIssues:
        """Issue lines and fixability. No LLM, no writes."""
        found = await inspect_owner_issues(self._request(project_id, 0))
        return QualityIssues(lines=found.lines, fixable=found.fixable)

    async def autofix(self, command: AutofixCommand) -> AutofixOutcome:
        """Run the fix under autopilot Langfuse metadata."""
        request = self._request(command.project_id, command.expected_version)
        owner = await read_project_owner_id(command.project_id, self._config.session)
        metadata = _trace(command.project_id, AUTOFIX_REWORK_PHASE, owner)
        with propagate_attributes(metadata=metadata):
            report = await run_owner_autofix(request)
        return AutofixOutcome(
            status=_STATUSES.get(report.status, AutofixStatus.NOTHING_TO_FIX),
            remaining=report.remaining,
            translation_failed=report.translation_failed,
        )

    async def repair_gate(self, command: GateRepairCommand) -> GateRepairOutcome:
        """Repair a content/design gate's checkpoint copy (AE-0392)."""
        request = self._request(command.project_id, command.expected_version)
        owner = await read_project_owner_id(command.project_id, self._config.session)
        metadata = _trace(command.project_id, command.phase, owner)
        with propagate_attributes(metadata=metadata):
            report = await run_gate_repair(request)
        return GateRepairOutcome(
            status=_STATUSES.get(report.status, AutofixStatus.NOTHING_TO_FIX),
            fixed_rules=report.fixed_rules,
            remaining_rules=report.remaining_rules,
        )

    async def fix_slides(self, command: SlideFixCommand) -> SlideFixOutcome:
        """Model-fix the slides still failing at a gate (AE-0401)."""
        factory = self._config.engine_factory
        request = SlideFixRequest(
            session=self._config.session,
            project_id=command.project_id,
            expected_version=command.expected_version,
            phase=command.phase,
            engine=factory() if factory is not None else None,
            attempts=self._config.autofix_attempts,
            escalation_attempts=self._config.autofix_escalation_attempts,
            model_factory=self._config.slide_fix_model,
            escalation_model_factory=self._config.slide_fix_escalation_model,
        )
        owner = await read_project_owner_id(command.project_id, self._config.session)
        metadata = _trace(command.project_id, PHASE_AUTOFIX, owner)
        metadata[LANGFUSE_FIELD_AGENT_NAME] = AGENT_NAME_SLIDE_FIXER
        with propagate_attributes(metadata=metadata):
            report = await run_slide_fix(request)
        return _slide_fix_outcome(report, self._config.persona_unscored_max_ticks)

    def _request(self, project_id: str, version: int) -> OwnerAutofixRequest:
        factory = self._config.engine_factory
        return OwnerAutofixRequest(
            session=self._config.session,
            project_id=project_id,
            engine=factory() if factory is not None else None,
            expected_version=version,
        )


def _trace(project_id: str, phase: str, owner: str) -> dict[str, str]:
    return {
        LANGFUSE_FIELD_CONTENT_TYPE: CONTENT_TYPE_CAROUSEL,
        LANGFUSE_FIELD_AGENT_NAME: AGENT_NAME_AUTOPILOT,
        LANGFUSE_FIELD_PHASE: phase,
        LANGFUSE_FIELD_PROJECT_ID: project_id,
        LANGFUSE_FIELD_USER_ID: owner,
    }


def _slide_fix_outcome(report: SlideFixReport, max_ticks: int) -> SlideFixOutcome:
    unscored = [
        slide for slide in report.slides if slide.fixed and slide.unscored_ticks
    ]
    return SlideFixOutcome(
        status=_STATUSES.get(report.status, AutofixStatus.NOTHING_TO_FIX),
        failing=tuple(
            FailingSlide(
                slide_index=slide.slide_index,
                rules=slide.rules,
                text=slide.text,
                attempts=slide.attempts,
            )
            for slide in report.slides
            if not slide.fixed
        ),
        attempts=tuple(
            SlideFixAttemptRecord(
                slide_index=attempt.slide_index,
                attempt=attempt.attempt,
                rules_before=attempt.rules_before,
                rules_after=attempt.rules_after,
                outcome=attempt.outcome,
                model_role=attempt.model_role,
            )
            for attempt in report.attempts
        ),
        unfixable_rules=report.unfixable_rules,
        unscored_slides=tuple(slide.slide_index for slide in unscored),
        judge_unavailable=any(slide.unscored_ticks >= max_ticks for slide in unscored),
    )
