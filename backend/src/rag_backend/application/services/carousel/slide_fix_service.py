"""Model fix of the slides still failing at a content/design gate (AE-0401).

Runs after the deterministic gate repair, only for the autopilot:

1. read the gate's checkpoint copy (``load_gate_source``, as the repair);
2. pick the failing slides: blocking violations, or a voice score under the
   floor at the content gate;
3. fix them in parallel (bounded by ``CONTENT_DRAFT_CONCURRENCY``), at most
   ``AUTOPILOT_AUTOFIX_ATTEMPTS`` model attempts each (``slide_fix_loop``);
4. write the fixed slides once, through the reviewer-edit path
   (``apply_localized_slide_edits``) plus their new voice scores, under the
   project lock and the lock-version CAS. ``slide_drafts``,
   ``localized_slides``, ``translations_en``, ``presentation_validation``,
   ``content_gate_validation`` and ``persona_scores`` therefore stay in step.

No model call runs under the lock. A tick that crashes before the write
writes nothing; one that loses the CAS writes nothing and reports a conflict.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from functools import partial
from typing import cast

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.carousel.bounded_gather import gather_bounded
from rag_backend.application.services.carousel.localized_rows_sync import (
    sync_rows_to_localized,
)
from rag_backend.application.services.carousel.owner_autofix_lock import (
    AutofixConflictError,
    LockedWrite,
    write_locked,
)
from rag_backend.application.services.carousel.owner_autofix_source import (
    AutofixSource,
    AutofixSourceRequest,
    WorkflowStateStore,
    load_gate_source,
)
from rag_backend.application.services.carousel.presentation_review_edits import (
    apply_localized_slide_edits,
)
from rag_backend.application.services.carousel.slide_fix_loop import (
    LoopContext,
    fix_slide,
)
from rag_backend.application.services.carousel.slide_fix_targets import (
    TargetQuery,
    TargetSelection,
    select_targets,
    slide_scores,
)
from rag_backend.application.services.carousel.slide_fix_types import (
    DeckContext,
    SlideFixCommand,
    SlideFixOutcome,
    SlideFixResult,
    SlideFixSettings,
    SlideFixTools,
)
from rag_backend.domain.constants.carousel_autofix import (
    AUTOFIX_STATUS_CONFLICT,
    AUTOFIX_STATUS_FIXED,
    AUTOFIX_STATUS_NOTHING_TO_FIX,
)
from rag_backend.domain.constants.carousel_workflow import PERSONA_SCORE_OVERALL_KEY
from rag_backend.domain.constants.slide_fix import (
    LOG_SLIDE_FIX_APPLIED,
    LOG_SLIDE_FIX_CONFLICT,
    LOG_SLIDE_FIX_NOOP,
    PERSONA_SCORE_SLIDE_KEY,
)
from rag_backend.domain.constants.workflow_state_fields import (
    STATE_FIELD_PERSONA_SCORES,
)
from rag_backend.domain.protocols.repositories import CarouselRepository

logger = structlog.get_logger()


@dataclass(frozen=True)
class SlideFixDeps:
    """One session's collaborators. The editorial facade builds them."""

    db: AsyncSession
    repo: CarouselRepository
    workflow: WorkflowStateStore | None
    tools: SlideFixTools
    settings: SlideFixSettings


def _scores_patch(
    state: Mapping[str, object], fixed: list[SlideFixResult]
) -> dict[str, object] | None:
    raw = state.get(STATE_FIELD_PERSONA_SCORES)
    if not isinstance(raw, Mapping) or not raw:
        return None
    scores: dict[str, object] = dict(raw)
    for result in fixed:
        if result.score is None:
            continue
        key = PERSONA_SCORE_SLIDE_KEY.format(index=result.slide_index)
        previous = scores.get(key)
        detail = dict(previous) if isinstance(previous, Mapping) else {}
        scores[key] = {**detail, PERSONA_SCORE_OVERALL_KEY: result.score}
    return scores


def fix_patch(
    state: Mapping[str, object], fixed: list[SlideFixResult]
) -> dict[str, object]:
    """The checkpoint patch: the reviewer-edit updates plus the new scores."""
    updates = apply_localized_slide_edits(state, [result.record for result in fixed])
    scores = _scores_patch(state, fixed)
    if scores is not None:
        updates[STATE_FIELD_PERSONA_SCORES] = scores
    return updates


class SlideFixService:
    """Fix, persist and report the failing slides of one carousel gate."""

    def __init__(self, deps: SlideFixDeps) -> None:
        self._deps = deps

    async def fix(self, command: SlideFixCommand) -> SlideFixOutcome:
        """Fix what can be fixed; report every slide that is still failing."""
        source = await load_gate_source(
            AutofixSourceRequest(
                repo=self._deps.repo,
                project_id=command.project_id,
                workflow=self._deps.workflow,
            )
        )
        if source is None or source.state is None:
            return SlideFixOutcome(status=AUTOFIX_STATUS_NOTHING_TO_FIX)
        selection = self._select(source, command.phase)
        results = await self._run(source, selection)
        fixed = [result for result in results if result.fixed]
        if not fixed:
            logger.info(LOG_SLIDE_FIX_NOOP, project_id=command.project_id)
            return SlideFixOutcome(
                status=AUTOFIX_STATUS_NOTHING_TO_FIX,
                results=results,
                unfixable_rules=selection.unfixable_rules,
            )
        return await self._persist(command, source, (results, selection))

    def _select(self, source: AutofixSource, phase: str) -> TargetSelection:
        return select_targets(
            TargetQuery(
                records=source.records,
                state=cast(Mapping[str, object], source.state),
                policy_version=source.policy_version,
                phase=phase,
                voice_floor=self._deps.settings.voice_floor,
            )
        )

    async def _run(
        self, source: AutofixSource, selection: TargetSelection
    ) -> tuple[SlideFixResult, ...]:
        state = cast(Mapping[str, object], source.state)
        context = LoopContext(
            deck=DeckContext(
                records=source.records,
                policy_version=source.policy_version,
                autofix=source.context,
                scored=bool(slide_scores(state)),
            ),
            tools=self._deps.tools,
            settings=self._deps.settings,
        )
        factories = [
            partial(fix_slide, target, context) for target in selection.targets
        ]
        return tuple(await gather_bounded(factories, self._deps.settings.concurrency))

    async def _persist(
        self,
        command: SlideFixCommand,
        source: AutofixSource,
        found: tuple[tuple[SlideFixResult, ...], TargetSelection],
    ) -> SlideFixOutcome:
        results, selection = found
        fixed = [result for result in results if result.fixed]
        updates = fix_patch(cast(Mapping[str, object], source.state), fixed)
        target = LockedWrite(
            project_id=command.project_id, expected_version=command.expected_version
        )
        try:
            await write_locked(
                self._deps.db, target, lambda: self._write(command.project_id, updates)
            )
        except AutofixConflictError:
            logger.info(LOG_SLIDE_FIX_CONFLICT, project_id=command.project_id)
            return SlideFixOutcome(status=AUTOFIX_STATUS_CONFLICT)
        logger.info(
            LOG_SLIDE_FIX_APPLIED,
            project_id=command.project_id,
            slides=[result.slide_index for result in fixed],
            still_failing=[
                result.slide_index for result in results if not result.fixed
            ],
        )
        return SlideFixOutcome(
            status=AUTOFIX_STATUS_FIXED,
            results=results,
            unfixable_rules=selection.unfixable_rules,
        )

    async def _write(self, project_id: str, updates: dict[str, object]) -> None:
        await sync_rows_to_localized(self._deps.db, project_id, updates)
        await self._deps.db.commit()
        # ``load_gate_source`` found a checkpoint, so the store is wired.
        workflow = cast(WorkflowStateStore, self._deps.workflow)
        await workflow.update_workflow_state(project_id, updates)


__all__ = ["SlideFixDeps", "SlideFixService", "fix_patch"]
