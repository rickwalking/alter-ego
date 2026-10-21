"""httpx webhook client, transport mocked (contract 2.1).

Gherkin: tests/features/image_bridge.feature
  Scenario: Grok Bot returns an image (the webhook receives prompt, size, token)
  Scenario: Webhook is down
"""

from __future__ import annotations

import json
from uuid import uuid4

import httpx
import pytest
from pydantic import SecretStr

from rag_backend.modules.image_bridge.domain.exceptions import WebhookDeliveryError
from rag_backend.modules.image_bridge.domain.models import WebhookRequest
from rag_backend.modules.image_bridge.infrastructure.webhook_client import (
    HttpxGrokBotWebhook,
    WebhookClientConfig,
)
from tests.unit.modules.image_bridge.support import T0

URL = "https://hooks.example/grokbot/secret-path"


def _request() -> WebhookRequest:
    return WebhookRequest(
        job_id=uuid4(),
        model="gpt-image-2",
        prompt="slide",
        size="1536x1024",
        callback_url="https://h/cb",
        callback_token="tok",
        expires_at=T0,
    )


def _client(handler, auth: str = "Bearer s3cret", header: str = "Authorization"):
    return HttpxGrokBotWebhook(
        WebhookClientConfig(
            url=SecretStr(URL),
            auth_value=SecretStr(auth),
            auth_header=header,
            transport=httpx.MockTransport(handler),
        )
    )


async def test_posts_the_contract_body_with_the_auth_header() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(202)

    webhook_request = _request()
    await _client(handler).deliver(webhook_request)

    sent = seen[0]
    assert str(sent.url) == URL
    assert sent.method == "POST"
    assert sent.headers["Authorization"] == "Bearer s3cret"
    assert sent.headers["Content-Type"] == "application/json"
    assert json.loads(sent.content) == webhook_request.payload()


async def test_custom_header_name_and_no_header_when_value_empty() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200)

    await _client(handler, auth="k", header="X-Cursor-Key").deliver(_request())
    await _client(handler, auth="").deliver(_request())
    assert seen[0].headers["X-Cursor-Key"] == "k"
    assert "Authorization" not in seen[1].headers


# Scenario: Webhook is down
@pytest.mark.parametrize("status", [500, 404, 401, 302])
async def test_non_2xx_raises(status: int) -> None:
    client = _client(lambda request: httpx.Response(status))
    with pytest.raises(WebhookDeliveryError, match=f"HTTP {status}"):
        await client.deliver(_request())


async def test_transport_error_raises_without_leaking_the_url() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout(f"timed out connecting to {URL}")

    with pytest.raises(WebhookDeliveryError) as caught:
        await _client(handler).deliver(_request())
    assert str(caught.value) == "Grok Bot webhook request failed: ConnectTimeout"
    assert caught.value.__cause__ is None
    assert "secret-path" not in repr(caught.value)
