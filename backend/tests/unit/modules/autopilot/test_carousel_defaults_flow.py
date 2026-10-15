"""Carousel defaults flow from the topic to the project and the review (AE-0361).

Gherkin: tests/features/autopilot_carousel_defaults.feature
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from urllib.parse import parse_qs

import httpx
import pytest
import respx

from rag_backend.modules.autopilot.constants import EVENT_TYPE_READY_FOR_OWNER
from rag_backend.modules.autopilot.domain.gate import ProjectSpec
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.domain.notify import ReviewFacts, ReviewNotice
from rag_backend.modules.autopilot.infrastructure.telegram_notifier import (
    TelegramClientConfig,
    TelegramNotifier,
)
from tests.unit.modules.autopilot import test_owner_notifications as notify
from tests.unit.modules.autopilot.test_autopilot_runner import (
    _OWNER,
    _PROJECT,
    _Editorial,
    _Notices,
    _run,
    _runner,
    _Runs,
    _topic,
)
from tests.unit.modules.autopilot.test_telegram_notifier import _Sleeper

_ANIME = (
    "Futuristic anime in the style of Akira, Ghost in the Shell and "
    "Neon Genesis Evangelion. Background: ai-themed setting."
)
_PROFILE = "Audience: developers · Niche: AI agents · Style: neo_anime"
_MESSAGE = r"https://api.telegram.org/bot.+/sendMessage$"


@dataclass
class _Capture(_Editorial):
    specs: list[ProjectSpec] = field(default_factory=list)

    async def create_project(self, spec: ProjectSpec) -> str:
        self.specs.append(spec)
        assert spec.owner_user_id == _OWNER
        return _PROJECT


async def _spec_for(**topic_changes: str | None) -> ProjectSpec:
    run = _run(AutopilotRunState.QUEUED)
    topic = replace(_topic(run.topic_candidate_id), **topic_changes)
    editorial = _Capture()
    await _runner(_Runs(run=run, topic=topic), editorial, _Notices()).tick()
    assert len(editorial.specs) == 1
    return editorial.specs[0]


@pytest.mark.asyncio
async def test_runner_spec_defaults_to_flat_editorial_template_guidance() -> None:
    """Scenario: Default flat_editorial style and template guidance (AE-0372)."""
    spec = await _spec_for()
    assert spec.image_style == "flat_editorial"
    assert spec.image_guidance == (
        "Clean visuals that follow the chosen image style. "
        "Background: ai-themed setting."
    )


@pytest.mark.asyncio
async def test_runner_spec_neo_anime_gets_the_anime_template() -> None:
    """Scenario: Neo anime style gets the anime template guidance."""
    spec = await _spec_for(image_style="neo_anime")
    assert spec.image_style == "neo_anime"
    assert spec.image_guidance == _ANIME


@pytest.mark.asyncio
async def test_runner_spec_uses_the_style_neutral_template() -> None:
    """Scenario: Non-anime style gets style-neutral template guidance."""
    spec = await _spec_for(image_style="flat_editorial", niche="benchmarks")
    assert spec.image_style == "flat_editorial"
    assert spec.image_guidance == (
        "Clean visuals that follow the chosen image style. "
        "Background: benchmarks-themed setting."
    )


@pytest.mark.asyncio
async def test_runner_spec_keeps_the_scout_guidance() -> None:
    """Scenario: A bot-chosen style is accepted."""
    guidance = "Product photo. Background: a chip fab clean room."
    spec = await _spec_for(image_style="hyperreal", image_guidance=guidance)
    assert spec.image_style == "hyperreal"
    assert spec.image_guidance == guidance


@pytest.mark.asyncio
async def test_review_notice_carries_the_profile_line() -> None:
    """Scenario: The owner review message shows audience, niche and style."""
    facts = ReviewFacts(
        title="Agents",
        caption="The caption",
        slide_paths=("a.jpg",),
        audience="developers",
        niche="AI agents",
        image_style="neo_anime",
    )
    event = notify._event(
        EVENT_TYPE_READY_FOR_OWNER, {"project_id": notify._PROJECT, "revision": 2}
    )
    notifier = notify._Notifier()
    service, _store = notify._service(
        notify._Events([event]),
        notify._Runs(notify._run()),
        notifier,
        notify._Facts(facts),
    )
    assert await service.tick() == 1
    assert notifier.reviews[0].profile == _PROFILE


@pytest.mark.asyncio
async def test_review_notice_without_profile_facts_has_no_line() -> None:
    event = notify._event(
        EVENT_TYPE_READY_FOR_OWNER, {"project_id": notify._PROJECT, "revision": 2}
    )
    notifier = notify._Notifier()
    service, _store = notify._service(
        notify._Events([event]), notify._Runs(notify._run()), notifier
    )
    assert await service.tick() == 1
    assert notifier.reviews[0].profile == ""


@pytest.mark.asyncio
async def test_keyboard_message_starts_with_the_profile_line() -> None:
    """Scenario: The owner review message shows audience, niche and style."""
    notice = ReviewNotice(
        chat_id="42",
        run_id=_run(AutopilotRunState.AWAITING_OWNER).run_id,
        title="Agents",
        persona_score=88.0,
        sources_count=3,
        caption="The caption",
        slide_paths=(),
        prior_album_ids=(),
        profile=_PROFILE,
    )
    ok = httpx.Response(200, json={"ok": True, "result": {"message_id": 5}})
    notifier = TelegramNotifier(TelegramClientConfig(token="t", sleeper=_Sleeper()))
    with respx.mock(assert_all_called=True) as router:
        message = router.post(url__regex=_MESSAGE).mock(return_value=ok)
        await notifier.send_review(notice)
    form = parse_qs(message.calls[0].request.content.decode())
    assert form["text"][0] == f"{_PROFILE}\n\nThe caption"
    assert json.loads(form["reply_markup"][0])["inline_keyboard"]
