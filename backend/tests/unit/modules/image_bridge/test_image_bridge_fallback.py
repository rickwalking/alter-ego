"""``FallbackImageService`` (AC5).

Gherkin: tests/features/image_bridge.feature
  Scenario: Grok Bot refuses / Grok Bot never answers / Webhook is down
  Scenario: Fallback disabled
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest
from structlog.testing import capture_logs

from rag_backend.modules.image_bridge.application.fallback_image_service import (
    FallbackImageConfig,
    FallbackImageService,
    failure_reason,
)
from rag_backend.modules.image_bridge.domain.exceptions import ImageBridgeJobError


@dataclass
class _Service:
    error: Exception | None = None
    calls: list[tuple[str, str]] = field(default_factory=list)

    async def generate_image(self, prompt: str, output_path: str) -> str:
        self.calls.append((prompt, output_path))
        if self.error is not None:
            raise self.error
        return output_path


def _fallback(primary: _Service, openai: _Service, enabled: bool = True):
    return FallbackImageService(
        FallbackImageConfig(primary=primary, fallback=openai, fallback_enabled=enabled)
    )


async def test_primary_success_does_not_call_openai() -> None:
    primary, openai = _Service(), _Service()
    with capture_logs() as logs:
        result = await _fallback(primary, openai).generate_image("p", "/o.jpg")
    assert result == "/o.jpg"
    assert openai.calls == []
    assert logs[-1]["image_provider"] == "grokbot"


# Scenario: Grok Bot refuses -> the OpenAI fallback generates the image
async def test_primary_failure_runs_openai_and_logs_the_reason() -> None:
    primary = _Service(error=ImageBridgeJobError("job 1 failed: content_policy"))
    openai = _Service()
    with capture_logs() as logs:
        result = await _fallback(primary, openai).generate_image("p", "/o.jpg")
    assert result == "/o.jpg"
    assert openai.calls == [("p", "/o.jpg")]
    fallback = [log for log in logs if log["event"] == "image_bridge_fallback"]
    assert fallback[0]["image_provider"] == "openai_fallback"
    assert fallback[0]["reason"] == (
        "ImageBridgeJobError: job 1 failed: content_policy"
    )
    assert logs[-1]["image_provider"] == "openai_fallback"


async def test_any_exception_type_falls_back() -> None:
    primary, openai = _Service(error=OSError("disk")), _Service()
    await _fallback(primary, openai).generate_image("p", "/o.jpg")
    assert openai.calls


# Scenario: Fallback disabled
async def test_disabled_fallback_raises_the_runtime_error() -> None:
    error = ImageBridgeJobError("job 1 expired after 600s")
    primary, openai = _Service(error=error), _Service()
    with pytest.raises(RuntimeError) as caught:
        await _fallback(primary, openai, enabled=False).generate_image("p", "/o")
    assert caught.value is error
    assert openai.calls == []


async def test_openai_failure_after_fallback_propagates() -> None:
    primary = _Service(error=ImageBridgeJobError("x"))
    openai = _Service(error=RuntimeError("OpenAI image generation failed: 500"))
    with pytest.raises(RuntimeError, match="OpenAI image generation failed"):
        await _fallback(primary, openai).generate_image("p", "/o")


def test_reason_is_bounded() -> None:
    assert len(failure_reason(RuntimeError("x" * 1000))) == 300
