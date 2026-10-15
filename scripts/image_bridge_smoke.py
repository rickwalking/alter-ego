#!/usr/bin/env python3
"""GrokBot image bridge smoke test (AE-0393, rollout step 3).

Runs ONE bridge job end to end against the configured environment: creates
the job in the configured database, POSTs the Grok Bot webhook, waits for
the callback on IMAGE_BRIDGE_PUBLIC_BASE_URL, and writes the normalized
image. Prints the seconds, the dimensions and the provider that produced
the image. Works with IMAGE_BRIDGE_ENABLED=false (the flag only gates the
carousel wiring); the webhook and public URLs must be set.

By default only the bridge runs, so a failure is a failure. With
``--with-fallback`` a bridge failure calls OpenAI (paid) instead, as the
carousel path does.

Run where the backend's settings and database are reachable. On prod the
image has no repo-level ``scripts/``, so pipe the file in:
    docker compose -f docker-compose.prod.yml exec -T backend \
        python - --prompt "..." < scripts/image_bridge_smoke.py
Locally:
    cd backend && uv run python ../scripts/image_bridge_smoke.py --prompt "..."

Exit codes: 0 image written, 1 generation failed, 2 configuration error.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import tempfile
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from rag_backend.domain.protocols import ImageGenerationService

DEFAULT_PROMPT = (
    "Editorial illustration for a tech carousel slide: a glowing circuit-board "
    "city at dusk, cinematic light, no text."
)
PROVIDER_GROKBOT = "grokbot"
PROVIDER_OPENAI_FALLBACK = "openai_fallback"
RESULT_FORMAT = (
    "provider={provider} seconds={seconds:.1f} size={width}x{height} output={output}"
)
FAILURE_FORMAT = "image bridge smoke FAILED after {seconds:.1f}s: {kind}: {message}"
CONFIG_FAILURE_FORMAT = "image bridge smoke cannot run: {message}"
OUTPUT_NAME = "image_bridge_smoke.jpg"

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_CONFIG = 2


@dataclass(frozen=True)
class SmokeServices:
    """The bridge, and OpenAI when ``--with-fallback`` is given."""

    bridge: ImageGenerationService
    fallback: ImageGenerationService | None = None


@dataclass(frozen=True)
class SmokeRequest:
    """One smoke run."""

    prompt: str
    output: Path
    timer: Callable[[], float] = time.monotonic


@dataclass(frozen=True)
class SmokeResult:
    """What the run reports."""

    provider: str
    seconds: float
    width: int
    height: int
    output: Path

    def line(self) -> str:
        """The one-line report."""
        return RESULT_FORMAT.format(
            provider=self.provider,
            seconds=self.seconds,
            width=self.width,
            height=self.height,
            output=self.output,
        )


async def run_smoke(services: SmokeServices, request: SmokeRequest) -> SmokeResult:
    """Generate one image; fall back to OpenAI only when it was configured."""
    started = request.timer()
    provider = PROVIDER_GROKBOT
    try:
        await services.bridge.generate_image(request.prompt, str(request.output))
    except Exception:
        if services.fallback is None:
            raise
        provider = PROVIDER_OPENAI_FALLBACK
        await services.fallback.generate_image(request.prompt, str(request.output))
    seconds = request.timer() - started
    with Image.open(request.output) as image:
        width, height = image.size
    return SmokeResult(provider, seconds, width, height, request.output)


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    """CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(tempfile.gettempdir()) / OUTPUT_NAME,
    )
    parser.add_argument(
        "--with-fallback",
        action="store_true",
        help="call OpenAI (paid) when the bridge fails, like the carousel path",
    )
    return parser.parse_args(list(argv))


async def _main(args: argparse.Namespace) -> int:
    from rag_backend.infrastructure.config.settings import get_settings
    from rag_backend.infrastructure.database.config import close_db, init_db
    from rag_backend.infrastructure.external.openai_image import OpenAIImageService
    from rag_backend.modules.image_bridge import (
        ImageBridgeConfigError,
        build_grokbot_image_service,
    )

    settings = get_settings()
    try:
        bridge = build_grokbot_image_service(settings)
    except ImageBridgeConfigError as exc:
        print(CONFIG_FAILURE_FORMAT.format(message=exc), file=sys.stderr)
        return EXIT_CONFIG
    fallback = (
        OpenAIImageService(api_key=settings.openai_api_key)
        if args.with_fallback
        else None
    )
    await init_db(settings.database_url)
    started = time.monotonic()
    try:
        result = await run_smoke(
            SmokeServices(bridge=bridge, fallback=fallback),
            SmokeRequest(prompt=args.prompt, output=args.output),
        )
    except Exception as exc:
        print(
            FAILURE_FORMAT.format(
                seconds=time.monotonic() - started,
                kind=type(exc).__name__,
                message=exc,
            ),
            file=sys.stderr,
        )
        return EXIT_FAILED
    finally:
        await close_db()
    print(result.line())
    return EXIT_OK


def main(argv: Sequence[str]) -> int:
    """Entry point."""
    return asyncio.run(_main(parse_args(argv)))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
