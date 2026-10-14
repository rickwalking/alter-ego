"""Register the Telegram webhook.

Usage, from ``backend``::

    uv run python -m rag_backend.modules.autopilot.scripts.set_webhook \\
        https://example.com/api/telegram/webhook

The URL is the only argument. The bot token and
``TELEGRAM_WEBHOOK_SECRET`` come from settings. The secret is sent as
``secret_token`` and is not printed.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence

import httpx

from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.modules.autopilot.notify_constants import (
    FIELD_OK,
    TELEGRAM_API_HOST,
    TELEGRAM_HTTP_TIMEOUT_SECONDS,
)
from rag_backend.modules.autopilot.webhook_constants import (
    ALLOWED_UPDATE_CALLBACK,
    ALLOWED_UPDATE_MESSAGE,
    FIELD_ALLOWED_UPDATES,
    FIELD_URL,
    FIELD_WEBHOOK_AUTH,
    SET_WEBHOOK_EXIT_FAILED,
    SET_WEBHOOK_EXIT_OK,
    SET_WEBHOOK_EXIT_USAGE,
    TELEGRAM_METHOD_SET_WEBHOOK,
)

_USAGE = (
    "usage: python -m rag_backend.modules.autopilot.scripts.set_webhook <https-url>"
)


def set_webhook_body(url: str, secret: str) -> dict[str, object]:
    """JSON body for Telegram ``setWebhook``."""
    updates: list[str] = [ALLOWED_UPDATE_MESSAGE, ALLOWED_UPDATE_CALLBACK]
    return {
        FIELD_URL: url,
        FIELD_WEBHOOK_AUTH: secret,
        FIELD_ALLOWED_UPDATES: updates,
    }


def main(argv: Sequence[str] | None = None) -> int:
    """POST setWebhook. Returns 0 on success, 2 when the URL is missing."""
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1 or not args[0].strip():
        print(_USAGE, file=sys.stderr)
        return SET_WEBHOOK_EXIT_USAGE
    settings = get_settings()
    token = settings.telegram_bot_token.get_secret_value().strip()
    secret = settings.telegram_webhook_secret.get_secret_value()
    if not token or not secret:
        print("telegram bot token and webhook secret are required", file=sys.stderr)
        return SET_WEBHOOK_EXIT_FAILED
    return _post(token, set_webhook_body(args[0].strip(), secret))


def _post(token: str, body: dict[str, object]) -> int:
    url = f"{TELEGRAM_API_HOST}/bot{token}/{TELEGRAM_METHOD_SET_WEBHOOK}"
    try:
        response = httpx.post(url, json=body, timeout=TELEGRAM_HTTP_TIMEOUT_SECONDS)
        response.raise_for_status()
        payload: object = response.json()
    except httpx.HTTPError as exc:
        print(f"setWebhook failed: {exc.__class__.__name__}", file=sys.stderr)
        return SET_WEBHOOK_EXIT_FAILED
    if isinstance(payload, dict) and payload.get(FIELD_OK) is True:
        print("setWebhook ok")
        return SET_WEBHOOK_EXIT_OK
    print("setWebhook rejected", file=sys.stderr)
    return SET_WEBHOOK_EXIT_FAILED


if __name__ == "__main__":
    raise SystemExit(main())
