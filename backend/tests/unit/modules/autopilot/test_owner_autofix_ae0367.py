"""AE-0367: the Telegram "Fix issues" button on the autopilot side.

Webhook (owner allowlist, update dedupe, CAS, nothing-to-fix), the review
message (issue lines + 4th button) and the worker step that runs the queued
fix. The editorial side is a fake ``ContentAutofixer`` here; the real one is
exercised in tests/unit/application/test_owner_autofix_flow_ae0367.py.

Gherkin: tests/features/autopilot_owner_autofix.feature
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs
from uuid import UUID

import httpx
import pytest
import respx

from rag_backend.modules.autopilot.application.owner_actions import (
    OwnerActionDeps,
    OwnerActionService,
)
from rag_backend.modules.autopilot.application.runner import (
    AutopilotRunner,
    RunnerDependencies,
)
from rag_backend.modules.autopilot.constants import (
    GATE_CONTENT,
    GATE_FINAL_REVIEW,
    REASON_READY,
)
from rag_backend.modules.autopilot.domain.autofix import (
    AutofixCommand,
    AutofixOutcome,
    AutofixStatus,
    QualityIssues,
)
from rag_backend.modules.autopilot.domain.callback_parse import parse_callback
from rag_backend.modules.autopilot.domain.gate import GateSnapshot
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.domain.notify import ReviewNotice
from rag_backend.modules.autopilot.domain.review_issues import (
    review_keyboard_with_fix,
    with_issues,
)
from rag_backend.modules.autopilot.infrastructure.telegram_notifier import (
    TelegramClientConfig,
    TelegramNotifier,
)
from rag_backend.modules.autopilot.notify_constants import (
    BUTTON_FIX,
    CALLBACK_FIX_PREFIX,
    ISSUES_HEADER,
)
from rag_backend.modules.autopilot.recovery_constants import REASON_REWORK_RETRY
from rag_backend.modules.autopilot.webhook_constants import (
    ANSWER_ALREADY,
    ANSWER_FIXING,
    ANSWER_NOTHING_TO_FIX,
    AUTOFIX_REWORK_PHASE,
    KIND_FIX,
    REASON_OWNER_AUTOFIX,
    TEXT_SUPERSEDED,
)
from tests.unit.modules.autopilot.test_autopilot_runner import _Recovery
from tests.unit.modules.autopilot.test_owner_actions import (
    _OWNER,
    _PROJECT,
    _STRANGER,
    _Editorial,
    _Notices,
    _snapshot,
    _tap,
    _Topics,
    _World,
    _world,
)

_LINES = ("Slide 5: heading starts lowercase", "Slide 4: no body or features")


@dataclass
class _Autofixer:
    issues: QualityIssues = field(
        default_factory=lambda: QualityIssues(lines=_LINES, fixable=True)
    )
    status: AutofixStatus = AutofixStatus.FIXED
    inspected: list[str] = field(default_factory=list)
    fixes: list[AutofixCommand] = field(default_factory=list)

    async def inspect(self, project_id: str) -> QualityIssues:
        await asyncio.sleep(0)
        self.inspected.append(project_id)
        return self.issues

    async def autofix(self, command: AutofixCommand) -> AutofixOutcome:
        self.fixes.append(command)
        return AutofixOutcome(status=self.status)


@dataclass
class _Fix:
    world: _World
    autofixer: _Autofixer
    recovery: _Recovery


def _fix_world(autofixer: _Autofixer | None = None) -> _Fix:
    base = _world()
    fixer = autofixer or _Autofixer()
    recovery = _Recovery(runs=base.runs)
    service = OwnerActionService(
        OwnerActionDeps(
            runs=base.runs,
            updates=base.claims,
            pending=base.pending,
            editorial=base.editorial,
            release=base.release,
            messenger=base.messenger,
            recovery=recovery,
            clock=_Clock(),
            owner_chat_id=_OWNER,
            autofix=fixer,
        )
    )
    return _Fix(
        world=replace(base, service=service), autofixer=fixer, recovery=recovery
    )


class _Clock:
    def now(self) -> datetime:
        return datetime(2026, 10, 14, tzinfo=UTC)


async def _press(fix: _Fix, update_id: int, actor: str = _OWNER) -> None:
    update = _tap(update_id, f"ap:fix:{fix.world.runs.run.run_id}", actor=actor)
    await fix.world.service.handle(update)
    await fix.world.service.deliver()


def test_fix_callback_parses() -> None:
    """The 4th button's callback is allowlisted like the other actions."""
    run_id = UUID("22222222-2222-4222-8222-222222222222")
    parsed = parse_callback(f"{CALLBACK_FIX_PREFIX}{run_id}")
    assert parsed is not None
    assert parsed.kind == KIND_FIX
    assert parsed.run_id == run_id
    assert parse_callback(f"ap:fix:{run_id}:x") is None


# Scenario: The review message lists the issues and offers the fix
def test_review_keyboard_gets_a_fourth_button_when_fixable() -> None:
    run_id = UUID("22222222-2222-4222-8222-222222222222")
    fixable = review_keyboard_with_fix(run_id, fixable=True)
    assert len(fixable.rows) == 1
    labels = [button.text for button in fixable.rows[0]]
    assert len(labels) == 4
    assert labels[-1] == BUTTON_FIX
    assert fixable.rows[0][-1].callback_data == f"{CALLBACK_FIX_PREFIX}{run_id}"
    assert len(fixable.rows[0][-1].callback_data.encode()) <= 64


# Scenario: A clean carousel offers no fix button
def test_clean_review_keeps_three_buttons_and_no_issue_block() -> None:
    run_id = UUID("22222222-2222-4222-8222-222222222222")
    keyboard = review_keyboard_with_fix(run_id, fixable=False)
    assert [len(row) for row in keyboard.rows] == [3]
    assert with_issues("Caption", ()) == "Caption"
    assert with_issues("Caption", _LINES) == (
        f"Caption\n\n{ISSUES_HEADER}\n"
        "• Slide 5: heading starts lowercase\n"
        "• Slide 4: no body or features"
    )


def _form(content: bytes) -> dict[str, str]:
    return {key: values[0] for key, values in parse_qs(content.decode()).items()}


@pytest.mark.asyncio
async def test_review_message_carries_issues_and_the_fix_button(tmp_path: Path) -> None:
    """Scenario: The review message lists the issues and offers the fix."""
    run_id = UUID("22222222-2222-4222-8222-222222222222")
    notice = ReviewNotice(
        chat_id="42",
        run_id=run_id,
        title="Argon",
        persona_score=80.0,
        sources_count=3,
        caption="Legenda do carrossel",
        slide_paths=(),
        prior_album_ids=(1, 2),
        issues=_LINES,
        fixable=True,
    )
    ok = httpx.Response(200, json={"ok": True, "result": {"message_id": 7}})
    with respx.mock(assert_all_called=True) as router:
        message = router.post(url__regex=r".+/sendMessage$").mock(return_value=ok)
        notifier = TelegramNotifier(TelegramClientConfig(token="t", sleeper=_Sleeper()))
        result = await notifier.send_review(notice)
    assert result.album_ids == (1, 2)
    form = _form(message.calls[0].request.content)
    assert "Slide 5: heading starts lowercase" in form["text"]
    markup = json.loads(form["reply_markup"])
    callbacks = [
        button["callback_data"] for row in markup["inline_keyboard"] for button in row
    ]
    assert f"{CALLBACK_FIX_PREFIX}{run_id}" in callbacks
    assert tmp_path.exists()


class _Sleeper:
    async def sleep(self, seconds: float) -> None:
        del seconds


# Scenario: Happy path: the owner taps Fix issues (webhook half)
@pytest.mark.asyncio
async def test_tap_queues_the_fix_and_supersedes_the_keyboard() -> None:
    fix = _fix_world()
    await _press(fix, 1)
    run = fix.world.runs.run
    assert run.state is AutopilotRunState.REWORKING
    assert run.state_reason == REASON_OWNER_AUTOFIX
    assert run.rework_phase == AUTOFIX_REWORK_PHASE
    assert fix.autofixer.fixes == []
    assert fix.world.messenger.answers[-1].text == ANSWER_FIXING
    assert fix.world.messenger.edits[-1].text == TEXT_SUPERSEDED
    assert fix.world.messenger.edits[-1].keyboard is None


# Scenario: Double tap fixes once
@pytest.mark.asyncio
async def test_double_tap_queues_once() -> None:
    fix = _fix_world()
    await asyncio.gather(_press(fix, 1), _press(fix, 2))
    await _press(fix, 2)
    answers = [answer.text for answer in fix.world.messenger.answers]
    assert answers.count(ANSWER_FIXING) == 1
    assert ANSWER_ALREADY in answers
    assert fix.world.runs.run.state is AutopilotRunState.REWORKING


# Scenario: Nothing to fix
@pytest.mark.asyncio
async def test_clean_carousel_answers_nothing_to_fix() -> None:
    fix = _fix_world(_Autofixer(issues=QualityIssues()))
    await _press(fix, 1)
    run = fix.world.runs.run
    assert run.state is AutopilotRunState.AWAITING_OWNER
    assert run.rework_phase is None
    assert [answer.text for answer in fix.world.messenger.answers] == [
        ANSWER_NOTHING_TO_FIX
    ]
    assert fix.world.messenger.edits == []


@pytest.mark.asyncio
async def test_without_an_autofixer_nothing_is_fixable() -> None:
    world = _world()
    await world.service.handle(_tap(1, f"ap:fix:{world.runs.run.run_id}"))
    await world.service.deliver()
    assert world.runs.run.state is AutopilotRunState.AWAITING_OWNER
    assert world.messenger.answers[-1].text == ANSWER_NOTHING_TO_FIX


# Scenario: A non-owner tap is ignored
@pytest.mark.asyncio
async def test_stranger_tap_changes_nothing() -> None:
    fix = _fix_world()
    await _press(fix, 1, actor=_STRANGER)
    assert fix.world.runs.run.state is AutopilotRunState.AWAITING_OWNER
    assert fix.autofixer.inspected == []
    assert fix.world.messenger.answers == []


@pytest.mark.asyncio
async def test_a_run_no_longer_awaiting_is_already_handled() -> None:
    fix = _fix_world()
    fix.world.runs.run = replace(fix.world.runs.run, state=AutopilotRunState.PUBLISHING)
    await _press(fix, 1)
    assert fix.world.messenger.answers[-1].text == ANSWER_ALREADY
    assert fix.autofixer.inspected == []


@dataclass
class _VersionedEditorial(_Editorial):
    phase: str = GATE_FINAL_REVIEW
    version: int = 4

    async def read_gate(self, project_id: str) -> GateSnapshot:
        del project_id
        return replace(_snapshot(), phase=self.phase, lock_version=self.version)


async def _queued(status: AutofixStatus) -> tuple[_Fix, _VersionedEditorial]:
    fix = _fix_world(_Autofixer(status=status))
    await _press(fix, 1)
    return fix, _VersionedEditorial()


async def _tick(
    fix: _Fix, editorial: _VersionedEditorial, *, autofix: bool = True
) -> _Notices:
    notices = _Notices()
    runner = AutopilotRunner(
        RunnerDependencies(
            runs=fix.world.runs,
            topics=_Topics(),
            editorial=editorial,
            notices=notices,
            recovery=fix.recovery,
            owner_user_id="owner",
            autofix=fix.autofixer if autofix else None,
        )
    )
    await runner.tick()
    return notices


# Scenario: Happy path: the owner taps Fix issues (worker half)
@pytest.mark.asyncio
async def test_worker_runs_the_fix_then_sends_a_fresh_review() -> None:
    fix, editorial = await _queued(AutofixStatus.FIXED)
    notices = await _tick(fix, editorial)
    assert fix.autofixer.fixes == [
        AutofixCommand(project_id=_PROJECT, expected_version=editorial.version)
    ]
    run = fix.world.runs.run
    assert run.state is AutopilotRunState.AWAITING_OWNER
    assert run.state_reason == REASON_READY
    assert run.rework_phase is None
    assert [notice.revision for notice in notices.ready] == [editorial.version]
    # Scenario: Double tap fixes once — a second tick finds nothing queued.
    await _tick(fix, editorial)
    assert len(fix.autofixer.fixes) == 1


@pytest.mark.asyncio
async def test_worker_with_nothing_left_still_returns_the_review() -> None:
    fix, editorial = await _queued(AutofixStatus.NOTHING_TO_FIX)
    notices = await _tick(fix, editorial)
    assert fix.world.runs.run.state is AutopilotRunState.AWAITING_OWNER
    assert len(notices.ready) == 1


@pytest.mark.asyncio
async def test_a_conflict_keeps_the_fix_for_the_next_tick() -> None:
    fix, editorial = await _queued(AutofixStatus.CONFLICT)
    notices = await _tick(fix, editorial)
    run = fix.world.runs.run
    assert run.state is AutopilotRunState.REWORKING
    assert run.rework_phase == AUTOFIX_REWORK_PHASE
    assert notices.ready == []
    fix.autofixer.status = AutofixStatus.FIXED
    await _tick(fix, editorial)
    assert fix.world.runs.run.state is AutopilotRunState.AWAITING_OWNER
    assert len(fix.autofixer.fixes) == 2


@pytest.mark.asyncio
async def test_without_an_autofixer_the_review_reopens() -> None:
    fix, editorial = await _queued(AutofixStatus.FIXED)
    await _tick(fix, editorial, autofix=False)
    run = fix.world.runs.run
    assert run.state is AutopilotRunState.AWAITING_OWNER
    assert run.state_reason == REASON_REWORK_RETRY
    assert run.rework_phase is None
    assert fix.autofixer.fixes == []


@pytest.mark.asyncio
async def test_a_fix_queued_off_final_review_is_dropped() -> None:
    fix, editorial = await _queued(AutofixStatus.FIXED)
    editorial.phase = GATE_CONTENT
    await _tick(fix, editorial)
    assert fix.autofixer.fixes == []
    assert fix.world.runs.run.rework_phase is None
