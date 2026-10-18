"""Worker wiring for owner Telegram notices (split from ``bootstrap``).

One tick delivers due reviews, statuses and reminders, asks for each POV
run's thesis (AE-0377) and, AE-0418, sweeps the GrokBot covers nobody used
within 6 hours. Reviews and thesis prompts carry the run's cover offer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.modules.autopilot.application.publish_job import SystemClock
from rag_backend.modules.autopilot.bootstrap_thesis import thesis_prompts
from rag_backend.modules.autopilot.infrastructure.repository import (
    SqlAlchemyAutopilotRepository,
)

if TYPE_CHECKING:
    from rag_backend.modules.autopilot.application.notifications import (
        NotificationDependencies,
    )
    from rag_backend.modules.autopilot.infrastructure.editorial_driver import (
        EngineFactory,
    )


@dataclass(frozen=True, kw_only=True)
class TelegramTickConfig:
    """Worker-tick wiring for owner Telegram notices."""

    token: str
    chat_id: str
    web_base_url: str
    # AE-0367: lets the review list quality issues and offer "Fix issues".
    engine_factory: EngineFactory | None = None


class TelegramNotifyTickAdapter:
    """Deliver pending notices on the tick's session, after the runner."""

    def __init__(self, config: TelegramTickConfig) -> None:
        self._config = config

    async def tick(self, db: AsyncSession) -> int:
        """Send due reviews, statuses, reminders and thesis prompts; sweep covers."""
        from rag_backend.modules.autopilot.application.notifications import (
            OwnerNotificationService,
        )
        from rag_backend.modules.autopilot.bootstrap_cover import cover_sweep

        deps = _notification_deps(db, self._config)
        sent = await OwnerNotificationService(deps).tick()
        # AE-0377: ask the owner to confirm each POV run's thesis (once).
        sent += await thesis_prompts(db, deps).tick()
        # AE-0418: delete the covers nobody used within 6 hours.
        return sent + await cover_sweep(db).tick()


def _notification_deps(
    db: AsyncSession, config: TelegramTickConfig
) -> NotificationDependencies:
    from rag_backend.modules.autopilot.application.notifications import (
        NotificationDependencies,
    )
    from rag_backend.modules.autopilot.infrastructure.content_autofixer import (
        AutofixerConfig,
        InProcessContentAutofixer,
    )
    from rag_backend.modules.autopilot.infrastructure.cover_offers import (
        cover_review_facts,
    )
    from rag_backend.modules.autopilot.infrastructure.notice_source import (
        SqlAutopilotEventSource,
        SqlNoticeLogStore,
    )
    from rag_backend.modules.autopilot.infrastructure.review_facts import (
        CarouselReviewFacts,
    )
    from rag_backend.modules.autopilot.infrastructure.telegram_notifier import (
        AsyncSleeper,
        TelegramClientConfig,
        TelegramNotifier,
    )

    configured = bool(config.token.strip() and config.chat_id.strip())
    autofixer = InProcessContentAutofixer(
        AutofixerConfig(session=db, engine_factory=config.engine_factory)
    )
    return NotificationDependencies(
        events=SqlAutopilotEventSource(db),
        runs=SqlAlchemyAutopilotRepository(db),
        facts=cover_review_facts(CarouselReviewFacts(db, autofixer), db),
        notices=SqlNoticeLogStore(db),
        notifier=TelegramNotifier(
            TelegramClientConfig(token=config.token, sleeper=AsyncSleeper())
        ),
        clock=SystemClock(),
        chat_id=config.chat_id,
        configured=configured,
        web_base_url=config.web_base_url,
    )


def build_telegram_notify_tick(config: TelegramTickConfig) -> TelegramNotifyTickAdapter:
    """Build the worker collaborator. The HTTP client is created per process tick."""
    return TelegramNotifyTickAdapter(config)


__all__ = [
    "TelegramNotifyTickAdapter",
    "TelegramTickConfig",
    "build_telegram_notify_tick",
]
