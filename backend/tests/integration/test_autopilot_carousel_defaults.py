"""GrokBot carousel defaults through the API and the editorial facade (AE-0361).

Gherkin: tests/features/autopilot_carousel_defaults.feature
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from rag_backend.domain.models.user import UserRole
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.infrastructure.database.models.user import UserModel
from rag_backend.modules.autopilot.carousel_constants import (
    REASON_AUDIENCE_NOT_SIMPLE,
    REASON_BRIEF_NOT_SIMPLE,
    REASON_BRIEF_OFF_THEME,
    REASON_IMAGE_STYLE_UNSUPPORTED,
    REASON_NICHE_NOT_SIMPLE,
)
from rag_backend.modules.autopilot.constants import REASON_URL_IN_TEXT
from rag_backend.modules.autopilot.domain.gate import ProjectSpec
from rag_backend.modules.autopilot.infrastructure.editorial_driver import (
    EditorialDriverConfig,
    InProcessEditorialDriver,
)
from rag_backend.modules.autopilot.infrastructure.models import TopicCandidateModel
from rag_backend.modules.autopilot.infrastructure.review_facts import (
    CarouselReviewFacts,
)
from tests.integration.autopilot_topic_support import (
    _AS_OF,
    _PATH,
    _URL_A,
    _client,
    _Clock,
    _headers,
    _serve,
    _topic,
    _topic_count,
    configured_key,
)

_ = configured_key
_OWNER = "autopilot-owner"
_GUIDANCE = "Product photo. Background: a chip fab clean room."


class _DriverClock:
    def now(self) -> datetime:
        return datetime(2026, 10, 14, tzinfo=UTC)


async def _post(
    tmp_path: Path, name: str, topics: list[dict[str, object]]
) -> tuple[int, dict[str, object], AsyncEngine]:
    async for client, engine in _client(tmp_path / name, _Clock(_AS_OF)):
        await _serve(engine, (_URL_A,), _AS_OF)
        response = await client.post(_PATH, headers=_headers(), json={"topics": topics})
    return response.status_code, response.json(), engine


async def _stored_image(engine: AsyncEngine) -> list[tuple[str, str | None]]:
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        result = await session.execute(
            select(TopicCandidateModel.image_style, TopicCandidateModel.image_guidance)
        )
    return [(str(style), guidance) for style, guidance in result.all()]


def _queued(body: dict[str, object]) -> list[object]:
    queued = body["queued"]
    assert isinstance(queued, list)
    return queued


def _reasons(body: dict[str, object]) -> list[tuple[str, str]]:
    rejected = body["rejected"]
    assert isinstance(rejected, list)
    return [(str(item["title"]), str(item["reason"])) for item in rejected]


# Scenario: Default flat_editorial style and template guidance (AE-0372)
@pytest.mark.asyncio
async def test_default_style_is_flat_editorial(
    configured_key: None, tmp_path: Path
) -> None:
    del configured_key
    status, body, engine = await _post(
        tmp_path, "default.db", [_topic("Agents", _URL_A, 80)]
    )
    assert status == 200
    assert body["rejected"] == []
    assert await _stored_image(engine) == [("flat_editorial", None)]


# Scenario: A bot-chosen style is accepted
@pytest.mark.asyncio
async def test_bot_chosen_style_and_guidance_are_stored(
    configured_key: None, tmp_path: Path
) -> None:
    del configured_key
    topic = {
        **_topic("Chips", _URL_A, 80),
        "image_style": "hyperreal",
        "image_guidance": _GUIDANCE,
    }
    status, body, engine = await _post(tmp_path, "chosen.db", [topic])
    assert status == 200
    assert len(_queued(body)) == 1
    assert await _stored_image(engine) == [("hyperreal", _GUIDANCE)]


# Scenario: An unsupported style rejects only that topic
@pytest.mark.asyncio
async def test_unsupported_style_rejects_only_that_topic(
    configured_key: None, tmp_path: Path
) -> None:
    del configured_key
    bad = {**_topic("Agents", _URL_A, 80), "image_style": "watercolor"}
    good = {**_topic("Robots", _URL_A, 70), "image_style": "cinematic"}
    status, body, engine = await _post(tmp_path, "unsupported.db", [bad, good])
    assert status == 200
    assert _reasons(body) == [("Agents", REASON_IMAGE_STYLE_UNSUPPORTED)]
    assert len(_queued(body)) == 1
    assert await _stored_image(engine) == [("cinematic", None)]


# Scenario: An image_style longer than 40 characters fails the batch
@pytest.mark.asyncio
async def test_overlong_style_is_422_and_stores_nothing(
    configured_key: None, tmp_path: Path
) -> None:
    del configured_key
    topic = {**_topic("Agents", _URL_A, 80), "image_style": "x" * 41}
    status, _body, engine = await _post(tmp_path, "overlong.db", [topic])
    assert status == 422
    assert await _topic_count(engine) == 0


# Scenario: Image guidance over 400 characters fails the batch
@pytest.mark.asyncio
async def test_too_long_guidance_is_422(configured_key: None, tmp_path: Path) -> None:
    del configured_key
    topic = {**_topic("Agents", _URL_A, 80), "image_guidance": "x" * 401}
    status, _body, engine = await _post(tmp_path, "long.db", [topic])
    assert status == 422
    assert await _topic_count(engine) == 0


# Scenario: A URL in the image guidance is rejected
@pytest.mark.asyncio
async def test_url_in_guidance_is_rejected(
    configured_key: None, tmp_path: Path
) -> None:
    del configured_key
    topic = {**_topic("Agents", _URL_A, 80), "image_guidance": "See https://x.co"}
    status, body, engine = await _post(tmp_path, "url.db", [topic])
    assert status == 200
    assert _reasons(body) == [("Agents", REASON_URL_IN_TEXT)]
    assert await _topic_count(engine) == 0


# Scenario Outline: Audience or niche that is not simple is rejected
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        (
            "audience",
            "Brazilian developers who build AI tools",
            REASON_AUDIENCE_NOT_SIMPLE,
        ),
        ("niche", "AI agents for enterprise workflows", REASON_NICHE_NOT_SIMPLE),
    ],
)
async def test_not_simple_field_rejects_only_that_topic(
    configured_key: None,
    tmp_path: Path,
    field: str,
    value: str,
    reason: str,
) -> None:
    del configured_key
    wordy = {**_topic("Agents", _URL_A, 90), field: value}
    valid = _topic("Robots", _URL_A, 70)
    status, body, engine = await _post(tmp_path, f"{field}.db", [wordy, valid])
    assert status == 200
    assert _reasons(body) == [("Agents", reason)]
    assert len(_queued(body)) == 1
    assert await _topic_count(engine) == 1


# Scenario: A brief that misses the theme is rejected
# Scenario: A brief longer than 600 characters is rejected
@pytest.mark.asyncio
async def test_off_theme_and_long_briefs_are_rejected(
    configured_key: None, tmp_path: Path
) -> None:
    del configured_key
    off = _topic("GPU prices crash", _URL_A, 80, brief="Cooking recipes for the week.")
    long = _topic("Agents", _URL_A, 70, brief="agents " + "x" * 594)
    status, body, engine = await _post(tmp_path, "brief.db", [off, long])
    assert status == 200
    assert _reasons(body) == [
        ("GPU prices crash", REASON_BRIEF_OFF_THEME),
        ("Agents", REASON_BRIEF_NOT_SIMPLE),
    ]
    assert await _topic_count(engine) == 0


# Scenario: A brief longer than 800 characters fails the batch
@pytest.mark.asyncio
async def test_brief_over_the_schema_limit_is_422(
    configured_key: None, tmp_path: Path
) -> None:
    del configured_key
    topic = _topic("Agents", _URL_A, 80, brief="agents " + "x" * 794)
    status, _body, engine = await _post(tmp_path, "huge.db", [topic])
    assert status == 422
    assert await _topic_count(engine) == 0


# Scenario: The create-project call receives openai, auto, the style and the guidance
# Scenario: The owner review message shows audience, niche and style
@pytest.mark.asyncio
async def test_create_project_sets_openai_auto_style_and_guidance(
    db_session: AsyncSession,
) -> None:
    db_session.add(
        UserModel(
            id=_OWNER,
            email="autopilot@example.com",
            full_name="Autopilot",
            hashed_password="hash",
            role=UserRole.EDITOR.value,
        )
    )
    await db_session.flush()
    driver = InProcessEditorialDriver(
        EditorialDriverConfig(
            session=db_session,
            engine_factory=MagicMock,
            clock=_DriverClock(),
            stale_after_seconds=180,
        )
    )
    guidance = "Cinematic still. Background: a parliament hall."
    spec = ProjectSpec(
        topic="AI act vote",
        audience="policy makers",
        niche="AI regulation",
        brief="What the AI act vote changes.",
        sources=("https://example.com/story",),
        owner_user_id=_OWNER,
        image_style="cinematic",
        image_guidance=guidance,
    )
    project_id = await driver.create_project(spec)

    row = await db_session.get(CarouselProjectModel, project_id)
    assert row is not None
    assert row.image_model == "openai"
    assert row.theme == "auto"
    assert row.image_style == "cinematic"
    assert row.custom_visual_details == guidance
    facts = await CarouselReviewFacts(db_session).load(project_id)
    assert facts is not None
    assert (facts.audience, facts.niche, facts.image_style) == (
        "policy makers",
        "AI regulation",
        "cinematic",
    )
