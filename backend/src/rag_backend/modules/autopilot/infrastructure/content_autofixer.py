"""``ContentAutofixer`` backed by the editorial facade (AE-0367).

The engine factory is optional: without it the inspection reads only the
slide rows (no outline key points, no research vocabulary) and the fix cannot
re-translate EN. The webhook, the notifier and the worker all pass one.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.infrastructure.monitoring_langfuse import propagate_attributes
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
    GateRepairCommand,
    GateRepairOutcome,
    QualityIssues,
)
from rag_backend.modules.autopilot.infrastructure.editorial_driver import EngineFactory
from rag_backend.modules.autopilot.webhook_constants import AUTOFIX_REWORK_PHASE
from rag_backend.modules.editorial.public import (
    AUTOFIX_STATUS_CONFLICT,
    AUTOFIX_STATUS_FIXED,
    OwnerAutofixRequest,
    inspect_owner_issues,
    read_project_owner_id,
    run_gate_repair,
    run_owner_autofix,
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
