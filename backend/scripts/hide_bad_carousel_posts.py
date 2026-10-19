#!/usr/bin/env python3
"""Hide published carousel-origin blog posts (AE-0422 AC6).

One-shot operator action: every published ``origin='carousel'`` post is a legacy
artifact and is flipped to draft with a ``hidden_bad_post`` marker, while
``origin='standalone'`` posts are never touched (ADR-0025). Idempotent: a second
run reports nothing.

    uv run python scripts/hide_bad_carousel_posts.py --dry-run
    uv run python scripts/hide_bad_carousel_posts.py --apply --reason "AE-0422 AC6"

The default is ``--dry-run``; pass ``--apply`` to write.
"""

from __future__ import annotations

import argparse
import asyncio

from rag_backend.application.services.workflow_event_service import WorkflowEventService
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.database.blog_post_hide import (
    DEFAULT_HIDE_REASON,
    BlogPostHideService,
    HideRun,
)
from rag_backend.infrastructure.database.config import (
    close_db,
    get_session_maker,
    init_db,
)
from rag_backend.infrastructure.events.factory import get_event_publisher
from rag_backend.infrastructure.logging import setup_logging


async def _run(*, apply: bool, reason: str) -> None:
    settings = get_settings()
    await init_db(settings.database_url)
    service = BlogPostHideService(
        WorkflowEventService(get_event_publisher(settings.redis_url or None))
    )
    session_maker = get_session_maker()
    try:
        async with session_maker() as session:
            if not apply:
                report = await service.preview(session)
                print(f"dry-run: {report.count} post(s) would be hidden")
            else:
                report = await service.hide(session, HideRun(reason=reason))
                await session.commit()
                print(f"applied: hid {report.count} post(s)")
            for post_id in report.ids:
                print(f"  - {post_id}")
    finally:
        await close_db()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="write changes (default is dry-run)",
    )
    parser.add_argument("--reason", default=DEFAULT_HIDE_REASON)
    args = parser.parse_args()
    setup_logging(debug=get_settings().debug)
    asyncio.run(_run(apply=args.apply, reason=args.reason))


if __name__ == "__main__":
    main()
