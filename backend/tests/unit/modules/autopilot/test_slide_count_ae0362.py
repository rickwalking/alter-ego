"""The autopilot expects the pipeline's real slide count.

Prod escalation: the first real run hit ``outline_slide_count_mismatch``
because the autopilot created a 6-slide project while the editorial pipeline
always builds the presentation contract's 7 slides.

Gherkin: tests/features/autopilot_runner.feature

The CTA slide uses the owner avatar, so 6 of the 7 slides get a hero image; _HERO_WIDTH
is the gpt-image default size (infrastructure/external/openai_image.py).
"""

from __future__ import annotations

from dataclasses import replace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from rag_backend.application.services.carousel import presentation_policy
from rag_backend.application.services.carousel.presentation_policy_types import (
    PresentationPolicyError,
)
from rag_backend.domain.constants.carousel import (
    CAROUSEL_DEFAULT_SLIDES_CONFIG,
    CAROUSEL_SLIDES_CONFIG_SEVEN,
)
from rag_backend.domain.constants.carousel_presentation import CANONICAL_SLIDE_COUNT
from rag_backend.domain.constants.persona import VOICE_MATCH_MIN_SCORE
from rag_backend.domain.constants.presentation_policy import (
    CREATE_TIME_NEWS_PRESENTATION_POLICY_VERSION,
    CREATE_TIME_PRESENTATION_POLICY_VERSION,
    ERR_PRESENTATION_POLICY_NOT_FOUND,
)
from rag_backend.modules.autopilot.constants import (
    GATE_IMAGES,
    GATE_OUTLINE,
    PHASE_STATUS_AWAITING,
    REASON_IMAGES,
    REASON_OUTLINE,
    REASON_PASSED,
)
from rag_backend.modules.autopilot.domain.gate import (
    GateAction,
    GateSnapshot,
    ImageFact,
    ProjectSpec,
)
from rag_backend.modules.autopilot.domain.policy import decide
from rag_backend.modules.autopilot.infrastructure import editorial_driver
from rag_backend.modules.autopilot.infrastructure.editorial_driver import (
    EditorialDriverConfig,
    InProcessEditorialDriver,
)
from rag_backend.modules.editorial.domain.models import CarouselProject
from rag_backend.modules.editorial.infrastructure.carousel_automation import (
    CarouselAutomationAcl,
)
from rag_backend.modules.editorial.public import slides_in_config

_PROJECT_ID = str(uuid4())
_STALE_SIX_SLIDE_CONFIG = "1 intro, 3 content, 1 closing, 1 cta"
_STALE_SIX_SLIDES = 6
_PIPELINE_SLIDES = 7
_HERO_IMAGES = _PIPELINE_SLIDES - 1
_HERO_WIDTH = 1536
_HERO_HEIGHT = 1024


class _CapturingAcl:
    """Stands in for the editorial ACL; keeps the created project."""

    def __init__(self, _session: object) -> None:
        self.created: list[CarouselProject] = []

    async def create_project(self, project: CarouselProject) -> str:
        self.created.append(project)
        return _PROJECT_ID


def _spec() -> ProjectSpec:
    return ProjectSpec(
        topic="Gemini 4 Argon chegou",
        audience="devs",
        niche="ai",
        brief="brief",
        sources=("https://example.com",),
        owner_user_id="owner-1",
    )


def _driver() -> InProcessEditorialDriver:
    return InProcessEditorialDriver(
        EditorialDriverConfig(
            session=AsyncMock(),
            engine_factory=MagicMock,
            clock=MagicMock(),
            stale_after_seconds=180,
        )
    )


async def _created_project(monkeypatch: pytest.MonkeyPatch) -> CarouselProject:
    holder: list[_CapturingAcl] = []

    def _factory(session: object) -> _CapturingAcl:
        acl = _CapturingAcl(session)
        holder.append(acl)
        return acl

    monkeypatch.setattr(editorial_driver, "CarouselAutomationAcl", _factory)
    await _driver().create_project(_spec())
    return holder[0].created[0]


async def _slide_total(
    monkeypatch: pytest.MonkeyPatch, project: CarouselProject | None
) -> int:
    acl = CarouselAutomationAcl(AsyncMock())

    async def _load(_project_id: str) -> CarouselProject | None:
        return project

    monkeypatch.setattr(acl, "load_project", _load)
    return await acl.slide_total(_PROJECT_ID)


def _project(slides_config: str, policy: str | None) -> CarouselProject:
    return CarouselProject(
        topic="t",
        audience="a",
        niche="ai",
        slides_config=slides_config,
        presentation_policy_version=policy,
    )


def _jpeg() -> ImageFact:
    """A raw OpenAI hero image as the images phase stores it (not slide-sized)."""
    return ImageFact(present=True, is_jpeg=True, width=_HERO_WIDTH, height=_HERO_HEIGHT)


def _gate(phase: str, slides_total: int, count: int) -> GateSnapshot:
    return GateSnapshot(
        phase=phase,
        phase_status=PHASE_STATUS_AWAITING,
        lock_version=1,
        sources=(),
        outline_count=count,
        slides_total=slides_total,
        persona_score=VOICE_MATCH_MIN_SCORE,
        forbidden_hits=(),
        presentation_blockers=(),
        images=tuple(_jpeg() for _ in range(count)),
        revisions_used=0,
        stale=False,
        hero_images_total=_HERO_IMAGES,
    )


def test_seven_slides_config_parses_to_seven() -> None:
    """Scenario: A project rewritten to "7_slides" still expects 7 slides."""
    assert slides_in_config(CAROUSEL_SLIDES_CONFIG_SEVEN) == _PIPELINE_SLIDES
    assert slides_in_config(CAROUSEL_DEFAULT_SLIDES_CONFIG) == _PIPELINE_SLIDES


@pytest.mark.asyncio
async def test_autopilot_project_uses_the_pipeline_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scenario: The autopilot creates the project with the pipeline's 7 slides.

    New Radar IA carousels are stamped hero_lower_third_v4 (7 slides by default, 8 with
    the optional twist).
    """
    project = await _created_project(monkeypatch)
    assert project.slides_config == CAROUSEL_DEFAULT_SLIDES_CONFIG
    assert project.presentation_policy_version == (
        CREATE_TIME_NEWS_PRESENTATION_POLICY_VERSION
    )
    assert await _slide_total(monkeypatch, project) == _PIPELINE_SLIDES


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("slides_config", "policy"),
    [
        (_STALE_SIX_SLIDE_CONFIG, CREATE_TIME_PRESENTATION_POLICY_VERSION),
        (CAROUSEL_SLIDES_CONFIG_SEVEN, CREATE_TIME_PRESENTATION_POLICY_VERSION),
        (_STALE_SIX_SLIDE_CONFIG, None),
    ],
)
async def test_expected_count_is_the_presentation_contract(
    monkeypatch: pytest.MonkeyPatch, slides_config: str, policy: str | None
) -> None:
    """Scenario: The contract's slide_count wins over a stale slides_config."""
    project = _project(slides_config, policy)
    assert await _slide_total(monkeypatch, project) == CANONICAL_SLIDE_COUNT


@pytest.mark.asyncio
async def test_missing_contract_falls_back_to_the_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scenario: An unreadable contract falls back to the project's config."""

    def _boom(_version: str) -> object:
        raise PresentationPolicyError(ERR_PRESENTATION_POLICY_NOT_FOUND)

    monkeypatch.setattr(presentation_policy, "load_presentation_policy", _boom)
    project = _project(_STALE_SIX_SLIDE_CONFIG, CREATE_TIME_PRESENTATION_POLICY_VERSION)
    assert await _slide_total(monkeypatch, project) == _STALE_SIX_SLIDES


@pytest.mark.asyncio
async def test_unknown_project_expects_no_slides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing project keeps the fail-closed zero (the gate then revises)."""
    assert await _slide_total(monkeypatch, None) == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("phase", "count", "action", "reason"),
    [
        (GATE_OUTLINE, _PIPELINE_SLIDES, GateAction.APPROVE, REASON_PASSED),
        (GATE_IMAGES, _HERO_IMAGES, GateAction.APPROVE, REASON_PASSED),
        (GATE_OUTLINE, 5, GateAction.REVISE, REASON_OUTLINE),
        (GATE_IMAGES, _HERO_IMAGES - 1, GateAction.REVISE, REASON_IMAGES),
    ],
)
async def test_gates_pass_on_a_real_seven_slide_run(
    monkeypatch: pytest.MonkeyPatch,
    phase: str,
    count: int,
    action: GateAction,
    reason: str,
) -> None:
    """Scenarios: The outline gate accepts the pipeline's 7 slides and the images
    gate its 6 hero images; a real count mismatch is still revised.
    """
    total = await _slide_total(monkeypatch, await _created_project(monkeypatch))
    decision = decide(_gate(phase, total, count))
    assert (decision.action, decision.reason) == (action, reason)


def test_a_missing_image_file_still_revises() -> None:
    """Scenarios: A real slide-count mismatch is still revised; the images gate
    checks the hero images the pipeline stores (a missing file revises).
    """
    gate = _gate(GATE_IMAGES, _PIPELINE_SLIDES, _HERO_IMAGES)
    missing = ImageFact(present=False, is_jpeg=False, width=0, height=0)
    broken = replace(gate, images=(*gate.images[:-1], missing))
    decision = decide(broken)
    assert (decision.action, decision.reason) == (GateAction.REVISE, REASON_IMAGES)
