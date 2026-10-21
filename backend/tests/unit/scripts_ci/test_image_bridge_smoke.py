"""Smoke CLI for the image bridge (rollout step 3).

Gherkin: tests/features/image_bridge.feature
  Scenario: Grok Bot returns an image (one job end to end, reported)
  Scenario: Grok Bot refuses (the OpenAI fallback, only when asked)
"""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType

import pytest
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT = REPO_ROOT / "scripts" / "image_bridge_smoke.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("image_bridge_smoke", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("script spec missing")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


SMOKE = _load()


@dataclass
class _Service:
    size: tuple[int, int] = (1536, 1024)
    error: Exception | None = None
    calls: list[str] = field(default_factory=list)

    async def generate_image(self, prompt: str, output_path: str) -> str:
        self.calls.append(prompt)
        if self.error is not None:
            raise self.error
        Image.new("RGB", self.size).save(output_path, format="PNG")
        return output_path


def _timer():
    ticks = iter([10.0, 73.5])
    return lambda: next(ticks)


async def test_reports_seconds_dimensions_and_provider(tmp_path: Path) -> None:
    output = tmp_path / "smoke.jpg"
    result = await SMOKE.run_smoke(
        SMOKE.SmokeServices(bridge=_Service()),
        SMOKE.SmokeRequest(prompt="p", output=output, timer=_timer()),
    )
    assert result.line() == (
        f"provider=grokbot seconds=63.5 size=1536x1024 output={output}"
    )


async def test_bridge_failure_without_fallback_raises(tmp_path: Path) -> None:
    bridge = _Service(error=RuntimeError("expired"))
    with pytest.raises(RuntimeError, match="expired"):
        await SMOKE.run_smoke(
            SMOKE.SmokeServices(bridge=bridge),
            SMOKE.SmokeRequest(prompt="p", output=tmp_path / "x.jpg"),
        )


async def test_bridge_failure_with_fallback_reports_openai(tmp_path: Path) -> None:
    openai = _Service(size=(1536, 1024))
    result = await SMOKE.run_smoke(
        SMOKE.SmokeServices(bridge=_Service(error=RuntimeError("x")), fallback=openai),
        SMOKE.SmokeRequest(prompt="p", output=tmp_path / "x.jpg", timer=_timer()),
    )
    assert result.provider == "openai_fallback"
    assert openai.calls == ["p"]


def test_arguments_have_safe_defaults() -> None:
    args = SMOKE.parse_args([])
    assert args.with_fallback is False
    assert args.prompt == SMOKE.DEFAULT_PROMPT
    assert args.output.name == "image_bridge_smoke.jpg"
    custom = SMOKE.parse_args(["--prompt", "q", "--with-fallback"])
    assert (custom.prompt, custom.with_fallback) == ("q", True)


def test_missing_urls_exit_with_a_config_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from rag_backend.infrastructure.config import settings as settings_module

    monkeypatch.setenv("GROKBOT_IMAGE_WEBHOOK_URL", "")
    monkeypatch.setenv("IMAGE_BRIDGE_PUBLIC_BASE_URL", "")
    settings_module.get_settings.cache_clear()
    try:
        assert SMOKE.main([]) == SMOKE.EXIT_CONFIG
    finally:
        settings_module.get_settings.cache_clear()
    assert "GROKBOT_IMAGE_WEBHOOK_URL" in capsys.readouterr().err
