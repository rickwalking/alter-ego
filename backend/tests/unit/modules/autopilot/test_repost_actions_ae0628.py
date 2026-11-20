"""Owner buttons on a repost draft and the caption reply.

Gherkin: tests/features/autopilot_repost_drafts_ae0628.feature
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from rag_backend.modules.autopilot.application.deferred_replies import (
    DeferredOwnerMessenger,
)
from rag_backend.modules.autopilot.application.owner_replies import OwnerReplies
from rag_backend.modules.autopilot.application.repost_actions import (
    RepostOwnerActions,
    decidable,
)
from rag_backend.modules.autopilot.domain.insights import InsightMetrics
from rag_backend.modules.autopilot.domain.owner_ports import (
    CallbackAnswer,
    ForceReplyPrompt,
    MessageEdit,
    OwnerText,
)
from rag_backend.modules.autopilot.domain.recommend import ScheduleSignals
from rag_backend.modules.autopilot.domain.repost import Repost
from rag_backend.modules.autopilot.domain.repost_ports import StatusChange
from rag_backend.modules.autopilot.domain.webhook_update import WebhookUpdate
from rag_backend.modules.autopilot.repost_constants import (
    STATUS_APPROVED,
    STATUS_EXPIRED,
    STATUS_PENDING,
    STATUS_REJECTED,
)
from tests.unit.modules.autopilot.repost_fakes import (
    NOW,
    Clock,
    MemoryStore,
    stored,
    window,
)

_OWNER = "424242"


@dataclass
class _Messenger:
    answers: list[CallbackAnswer] = field(default_factory=list)
    edits: list[MessageEdit] = field(default_factory=list)
    asks: list[ForceReplyPrompt] = field(default_factory=list)
    tells: list[OwnerText] = field(default_factory=list)

    async def answer(self, command: CallbackAnswer) -> None:
        self.answers.append(command)

    async def edit(self, command: MessageEdit) -> None:
        self.edits.append(command)

    async def ask(self, command: ForceReplyPrompt) -> None:
        self.asks.append(command)

    async def tell(self, command: OwnerText) -> None:
        self.tells.append(command)


@dataclass
class _Metrics:
    async def metrics(self, media_id: str) -> InsightMetrics:
        del media_id
        return InsightMetrics(views=777)


@dataclass
class _Signals:
    async def load(self) -> ScheduleSignals:
        return ScheduleSignals()


@dataclass
class _Deps:
    reposts: MemoryStore | None
    repost_metrics: _Metrics | None = field(default_factory=_Metrics)
    schedule_signals: _Signals | None = field(default_factory=_Signals)
    clock: Clock = field(default_factory=Clock)
    owner_chat_id: str = _OWNER


class _Host(RepostOwnerActions):
    def __init__(self, deps: _Deps) -> None:
        self._deps = deps
        self.messenger = _Messenger()
        self._replies = DeferredOwnerMessenger(self.messenger)
        self._out = OwnerReplies(self._replies)


def _host(*rows: Repost, store: MemoryStore | None = None) -> tuple[_Host, MemoryStore]:
    store = store if store is not None else MemoryStore()
    for row in rows:
        store.rows[row.id] = row
    return _Host(_Deps(reposts=store)), store


def _ready(**changes: object) -> Repost:
    return stored(preview_ready_at=NOW, telegram_message_id=99, **changes)


def _tap(action: str, repost: Repost) -> WebhookUpdate:
    return WebhookUpdate(
        update_id=1,
        kind="callback",
        actor_id=_OWNER,
        chat_id=_OWNER,
        callback_id="cb",
        data=f"ap:rp:{action}:{repost.id}",
        message_id=99,
    )


def _text(text: str) -> WebhookUpdate:
    return WebhookUpdate(
        update_id=2, kind="message", actor_id=_OWNER, chat_id=_OWNER, text=text
    )


# Scenario: Aprovar schedules the best slot in the window
async def test_approve_in_window() -> None:
    repost = _ready(window=window(1, 27))
    host, store = _host(repost)
    assert await host._repost_callback(_tap("ok", repost))
    await host._replies.deliver()
    saved = store.rows[repost.id]
    assert saved.status == STATUS_APPROVED
    assert saved.cover_choice == "original"
    assert saved.publish_at is not None
    assert repost.window is not None
    assert repost.window.earliest <= saved.publish_at <= repost.window.latest
    assert saved.decided_by == f"owner:{_OWNER}"
    assert host.messenger.edits[0].keyboard is None


# Scenario: Aprovar without a window publishes now
async def test_approve_without_window_publishes_now_with_grok_cover() -> None:
    from uuid import uuid4

    repost = _ready(cover_asset_id=uuid4())
    host, store = _host(repost)
    await host._repost_callback(_tap("ok", repost))
    saved = store.rows[repost.id]
    assert saved.publish_at == NOW
    assert saved.cover_choice == "grok"


async def test_approve_without_signals_source() -> None:
    repost = _ready(window=window())
    store = MemoryStore(rows={repost.id: repost})
    host = _Host(_Deps(reposts=store, schedule_signals=None))
    await host._repost_callback(_tap("ok", repost))
    assert store.rows[repost.id].status == STATUS_APPROVED


# Scenario: Usar capa original approves with the original cover
async def test_original_cover_button() -> None:
    from uuid import uuid4

    repost = _ready(cover_asset_id=uuid4())
    host, store = _host(repost)
    await host._repost_callback(_tap("orig", repost))
    assert store.rows[repost.id].cover_choice == "original"
    assert store.rows[repost.id].status == STATUS_APPROVED


# Scenario: Rejeitar rejects
async def test_reject() -> None:
    repost = _ready()
    host, store = _host(repost)
    await host._repost_callback(_tap("no", repost))
    await host._replies.deliver()
    assert store.rows[repost.id].status == STATUS_REJECTED
    assert "rejeitado" in host.messenger.edits[0].text


# Scenario: Editar legenda replaces the caption from the owner's next text
async def test_caption_edit_flow() -> None:
    repost = _ready()
    host, store = _host(repost)
    await host._repost_callback(_tap("cap", repost))
    await host._replies.deliver()
    assert store.rows[repost.id].caption_edit_at == NOW
    assert host.messenger.asks
    bad = " ".join(f"#t{i}" for i in range(31))
    assert await host._repost_caption_reply(_text(bad))
    await host._replies.deliver()
    assert host.messenger.tells and store.rows[repost.id].caption == repost.caption
    assert await host._repost_caption_reply(_text("  Legenda nova \x07 "))
    await host._replies.deliver()
    saved = store.rows[repost.id]
    assert (saved.caption, saved.status, saved.caption_edit_at) == (
        "Legenda nova",
        STATUS_PENDING,
        None,
    )
    edit = host.messenger.edits[-1]
    assert edit.message_id == 99 and edit.keyboard is not None
    assert "777" in edit.text


async def test_caption_reply_without_pending_edit_is_not_handled() -> None:
    host, _store = _host(_ready())
    assert not await host._repost_caption_reply(_text("hello"))
    old = _ready(caption_edit_at=NOW - timedelta(minutes=16))
    host, _store = _host(old)
    assert not await host._repost_caption_reply(_text("hello"))
    assert not await _Host(_Deps(reposts=None))._repost_caption_reply(_text("x"))


async def test_caption_refresh_without_message_or_metrics() -> None:
    repost = stored(preview_ready_at=NOW, caption_edit_at=NOW)
    store = MemoryStore(rows={repost.id: repost})
    host = _Host(_Deps(reposts=store, repost_metrics=None))
    assert await host._repost_caption_reply(_text("Nova"))
    await host._replies.deliver()
    assert host.messenger.edits == []
    repost2 = _ready(caption_edit_at=NOW)
    store2 = MemoryStore(rows={repost2.id: repost2})
    host2 = _Host(_Deps(reposts=store2, repost_metrics=None))
    await host2._repost_caption_reply(_text("Nova"))
    await host2._replies.deliver()
    assert "—" in host2.messenger.edits[0].text


# Scenario: A tap after expiry or after a decision does nothing
async def test_taps_on_gone_drafts_change_nothing() -> None:
    for repost in (
        _ready(expires_at=NOW - timedelta(minutes=1)),
        _ready(status=STATUS_EXPIRED),
        stored(),
    ):
        host, store = _host(repost)
        assert await host._repost_callback(_tap("ok", repost))
        await host._replies.deliver()
        assert store.rows[repost.id] == repost
        assert host.messenger.answers[0].text.startswith("Este repost")
    host, _ = _host()
    ghost = _ready()
    await host._repost_callback(_tap("ok", ghost))
    await host._replies.deliver()
    assert host.messenger.answers


async def test_lost_race_answers_gone() -> None:
    repost = _ready()

    class _Racing(MemoryStore):
        async def save(self, change: StatusChange) -> bool:
            return False

    for action in ("ok", "no", "cap"):
        host, _store = _host(repost, store=_Racing())
        await host._repost_callback(_tap(action, repost))
        await host._replies.deliver()
        assert host.messenger.answers[-1].text.startswith("Este repost")


async def test_other_callbacks_and_missing_store() -> None:
    host, _ = _host()
    assert not await host._repost_callback(
        WebhookUpdate(update_id=3, kind="callback", data="ap:bst:ok:x", callback_id="c")
    )
    bare = _Host(_Deps(reposts=None))
    repost = _ready()
    assert await bare._repost_callback(_tap("ok", repost))


def test_decidable() -> None:
    assert decidable(_ready(), NOW)
    assert not decidable(stored(), NOW)
    assert not decidable(_ready(status=STATUS_APPROVED), NOW)
    assert not decidable(_ready(), NOW + timedelta(hours=12))
