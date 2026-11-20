"""POST /api/autopilot/assets with ``purpose``.

Gherkin: tests/features/reel_cover_asset_ae0627.feature
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from rag_backend.modules.autopilot.infrastructure.cover_models import (
    AutopilotCoverAssetModel,
)
from tests.integration.autopilot_topic_support import _Clock, configured_key
from tests.integration.test_autopilot_cover_api_ae0418 import (
    _image,
    _upload,
    api,
    cover_env,
)

_ = (configured_key, api, cover_env)
_Api = tuple[object, AsyncEngine, _Clock]


async def _purposes(engine: AsyncEngine) -> list[str]:
    async with async_sessionmaker(engine)() as session:
        rows = await session.scalars(select(AutopilotCoverAssetModel.purpose))
        return list(rows)


# Scenario: An upload without purpose stays a carousel cover
# Scenario: A 9:16 reel cover is accepted at 1080x1920
async def test_reel_and_carousel_uploads(api: _Api) -> None:
    client, engine, _clock = api
    carousel = await _upload(client, _image((1080, 1350)), {"kind": "ai_image"})
    assert (carousel["status"], carousel["purpose"], carousel["height"]) == (
        201,
        "carousel_cover",
        1350,
    )
    reel_cover = await _upload(
        client, _image((1440, 2560)), {"kind": "ai_image", "purpose": "reel_cover"}
    )
    assert (
        reel_cover["status"],
        reel_cover["purpose"],
        reel_cover["width"],
        reel_cover["height"],
    ) == (201, "reel_cover", 1080, 1920)
    assert sorted(await _purposes(engine)) == ["carousel_cover", "reel_cover"]


# Scenario: A reel cover that is not 9:16 is refused
# Scenario: An unknown purpose is refused
async def test_reel_cover_refusals(api: _Api) -> None:
    client, _engine, _clock = api
    for size, form, detail in (
        (
            (1080, 1350),
            {"kind": "ai_image", "purpose": "reel_cover"},
            "asset_ratio_invalid",
        ),
        ((720, 1280), {"kind": "ai_image", "purpose": "reel_cover"}, "asset_too_small"),
        (
            (1080, 1920),
            {"kind": "ai_image", "purpose": "story_cover"},
            "asset_purpose_invalid",
        ),
        (
            (1080, 1920),
            {
                "kind": "screenshot",
                "purpose": "reel_cover",
                "source_url": "https://x.com/a/status/1",
            },
            "asset_kind_invalid",
        ),
    ):
        result = await _upload(client, _image(size), form)
        assert (result["status"], result["detail"]) == (422, detail)
