"""Ask Meta to validate one boost request's real launch bodies. Creates nothing.

Usage (backend container on prod; reads the request from the app database):
    python -m rag_backend.scripts.boost_validate_only <request_id>
    python -m rag_backend.scripts.boost_validate_only <request_id> \\
        --campaign-id <id> [--adset-id <id> --creative-id <id>]

It builds the exact campaign, ad set, creative and ad bodies the launch would send,
runs the three preflight reads, and posts the campaign and the creative with
``execution_options=["validate_only"]``. The ad set needs ``--campaign-id`` and the
ad needs ``--adset-id`` and ``--creative-id`` (existing objects); without them their
body is printed, token redacted. A POST without ``validate_only`` is refused before
it is sent. One JSON line per call: ok, Meta's error fields, or the held body.

Exit codes: 0 every sent call passed, 1 a call failed or the request/token is
missing, 2 usage error.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.modules.autopilot.infrastructure.boost_store import SqlBoostStore
from rag_backend.modules.autopilot.infrastructure.boost_validate_only import (
    OUTCOME_FAILED,
    CallOutcome,
    CheckInput,
    ParentIds,
    run_checks,
)
from rag_backend.modules.autopilot.infrastructure.meta_graph import ads_config
from rag_backend.scripts.cli_support import (
    EXIT_USAGE,
    GuardedCli,
    run_guarded_cli,
    run_on_own_engine,
)

EXIT_OK = 0
EXIT_FAILED = 1
_TIMEOUT = 20.0
_ERR_REQUEST_ID = "request_id must be a UUID"
_ERR_NOT_FOUND = "boost request not found"
_ERR_NO_ADS_KEY = "the Meta ads access setting is empty"

__all__ = ["EXIT_FAILED", "EXIT_OK", "EXIT_USAGE", "build_parser", "main", "render"]


def build_parser() -> argparse.ArgumentParser:
    """The request id and the optional existing parent ids."""
    parser = argparse.ArgumentParser(prog="boost_validate_only", description=__doc__)
    parser.add_argument("request_id", help="boost request UUID")
    parser.add_argument("--campaign-id", help="existing campaign for the ad set")
    parser.add_argument("--adset-id", help="existing ad set for the ad")
    parser.add_argument("--creative-id", help="existing creative for the ad")
    return parser


def _validate(args: argparse.Namespace) -> str | None:
    try:
        UUID(args.request_id)
    except ValueError:
        return _ERR_REQUEST_ID
    return None


def render(outcome: CallOutcome) -> str:
    """One JSON line. Bodies come redacted; details never hold the token."""
    line: dict[str, object] = {"call": outcome.call, "outcome": outcome.outcome}
    if outcome.error_code:
        line["error_code"] = outcome.error_code
    if outcome.detail:
        line["meta"] = outcome.detail
    if outcome.payload:
        line["payload"] = outcome.payload
    return json.dumps(line, sort_keys=True, ensure_ascii=False)


def _parents(args: argparse.Namespace) -> ParentIds:
    return ParentIds(
        campaign_id=args.campaign_id,
        adset_id=args.adset_id,
        creative_id=args.creative_id,
    )


async def _check(engine: AsyncEngine, args: argparse.Namespace) -> int:
    async with AsyncSession(engine) as session:
        request = await SqlBoostStore(session).get(UUID(args.request_id))
    if request is None:
        print(f"ERROR: {_ERR_NOT_FOUND}", file=sys.stderr)
        return EXIT_FAILED
    settings = get_settings()
    token = settings.meta_ads_access_token.get_secret_value().strip()
    if token == "":
        print(f"ERROR: {_ERR_NO_ADS_KEY}", file=sys.stderr)
        return EXIT_FAILED
    check = CheckInput(request=request, parents=_parents(args), now=datetime.now(UTC))
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        outcomes = await run_checks(check, ads_config(settings, token), client)
    for outcome in outcomes:
        print(render(outcome))
    failed = any(outcome.outcome == OUTCOME_FAILED for outcome in outcomes)
    return EXIT_FAILED if failed else EXIT_OK


def main(argv: Sequence[str] | None = None) -> int:
    """Parse, then check the request on a dedicated engine."""

    async def run(args: argparse.Namespace) -> int:
        return await run_on_own_engine(lambda engine: _check(engine, args))

    cli = GuardedCli(parser=build_parser(), validate=_validate, run=run)
    return run_guarded_cli(cli, argv)


if __name__ == "__main__":
    raise SystemExit(main())
