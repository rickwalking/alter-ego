"""httpx client for the Grok Bot webhook (AE-0393, contract section 2.1).

The auth header name and value are configuration, so they match whatever
the Cursor webhook expects. Neither the URL, the auth value nor the body
(which carries the callback token) is ever logged.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx
from pydantic import SecretStr

from rag_backend.modules.image_bridge.constants import (
    CONTENT_TYPE_JSON,
    DEFAULT_WEBHOOK_AUTH_HEADER,
    ERR_WEBHOOK_STATUS,
    ERR_WEBHOOK_TRANSPORT,
    HEADER_CONTENT_TYPE,
    WEBHOOK_TIMEOUT_SECONDS,
)
from rag_backend.modules.image_bridge.domain.exceptions import WebhookDeliveryError
from rag_backend.modules.image_bridge.domain.models import WebhookRequest


@dataclass(frozen=True)
class WebhookClientConfig:
    """Where and how to POST the job."""

    url: SecretStr
    auth_value: SecretStr
    auth_header: str = DEFAULT_WEBHOOK_AUTH_HEADER
    timeout_seconds: float = WEBHOOK_TIMEOUT_SECONDS
    # Tests inject ``httpx.MockTransport``; prod uses the default transport.
    transport: httpx.AsyncBaseTransport | None = None


class HttpxGrokBotWebhook:
    """``GrokBotWebhook`` over httpx with a hard timeout."""

    def __init__(self, config: WebhookClientConfig) -> None:
        self._config = config

    async def deliver(self, request: WebhookRequest) -> None:
        """POST the job; a non-2xx answer or a transport error raises."""
        try:
            async with httpx.AsyncClient(
                timeout=self._config.timeout_seconds,
                transport=self._config.transport,
            ) as client:
                response = await client.post(
                    self._config.url.get_secret_value(),
                    json=request.payload(),
                    headers=self._headers(),
                )
        except httpx.HTTPError as exc:
            # The type only: httpx messages can echo the URL.
            reason = type(exc).__name__
            raise WebhookDeliveryError(
                ERR_WEBHOOK_TRANSPORT.format(reason=reason)
            ) from None
        if not response.is_success:
            raise WebhookDeliveryError(
                ERR_WEBHOOK_STATUS.format(status=response.status_code)
            )

    def _headers(self) -> dict[str, str]:
        headers = {HEADER_CONTENT_TYPE: CONTENT_TYPE_JSON}
        auth_value = self._config.auth_value.get_secret_value()
        if auth_value and self._config.auth_header:
            headers[self._config.auth_header] = auth_value
        return headers
