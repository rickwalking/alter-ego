"""POST /api/autopilot/assets and the topic ``cover`` field.

Gherkin: tests/features/autopilot_grok_cover_ae0418.feature
  Upload: POST /api/autopilot/assets; Topic intake: the optional cover field.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from datetime import timedelta
from io import BytesIO
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from rag_backend.domain.models.carousel_creator_asset import CreatorAssetLibraryQuery
from rag_backend.domain.models.user import UserRole
from rag_backend.infrastructure.database.creator_asset_repository import (
    PostgresCreatorAssetRepository,
)
from rag_backend.infrastructure.database.models.carousel_creator_asset import (
    CarouselCreatorAssetModel,
)
from rag_backend.infrastructure.database.models.user import UserModel
from rag_backend.modules.autopilot.infrastructure.cover_models import (
    AutopilotCoverAssetModel,
)
from rag_backend.modules.autopilot.infrastructure.models import TopicCandidateModel
from tests.integration.autopilot_topic_support import (
    _AS_OF,
    _PATH,
    _URL_A,
    _URL_B,
    _client,
    _Clock,
    _headers,
    _serve,
    _topic,
    configured_key,
)

_ = configured_key
_ASSETS = "/api/autopilot/assets"
_OWNER = "00000000-0000-4000-8000-000000000418"
_X_POST = "https://x.com/poteto/status/2111133080526495985"
_POV = {"mode": "pov", "thesis_draft": "Quem decide o que construir ainda é o dev."}
_POV_NEWS = {"mode": "pov_news", "thesis_draft": "A notícia muda o meu dia de dev."}
_FIVE_MB = 5 * 1024 * 1024


def _image(size: tuple[int, int], fmt: str = "PNG") -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, (20, 40, 60)).save(buffer, format=fmt)
    return buffer.getvalue()


@pytest.fixture
def cover_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, configured_key: None
) -> Iterator[Path]:
    from rag_backend.infrastructure.config.settings import get_settings

    del configured_key
    monkeypatch.setenv("AUTOPILOT_OWNER_USER_ID", _OWNER)
    monkeypatch.setenv("CAROUSEL_CREATOR_ASSETS_DIR", str(tmp_path / "assets"))
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


@pytest.fixture
async def api(
    cover_env: Path,
) -> AsyncIterator[tuple[AsyncClient, AsyncEngine, _Clock]]:
    clock = _Clock(_AS_OF)
    async for client, engine in _client(cover_env / "cover.db", clock):
        await _seed_owner(engine)
        await _serve(engine, (_URL_A, _URL_B, _X_POST), _AS_OF)
        yield client, engine, clock


async def _seed_owner(engine: AsyncEngine) -> None:
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        session.add(
            UserModel(
                id=_OWNER,
                email="owner@example.com",
                full_name="Owner",
                hashed_password="hash",
                role=UserRole.EDITOR.value,
            )
        )
        await session.commit()


async def _upload(
    client: AsyncClient,
    content: bytes | None,
    form: dict[str, str],
) -> dict[str, object]:
    files = (
        {"file": ("cover.png", content, "image/png")} if content is not None else None
    )
    response = await client.post(_ASSETS, headers=_headers(), data=form, files=files)
    return {"status": response.status_code, **response.json()}


# Scenario: An ai_image of 1080x1350 is accepted
@pytest.mark.asyncio
async def test_ai_image_is_stored_as_a_cover_role_asset(
    api: tuple[AsyncClient, AsyncEngine, _Clock],
) -> None:
    """The AI image is never part of the owner's photo library."""
    client, engine, _clock = api
    body = await _upload(client, _image((1080, 1350)), {"kind": "ai_image"})
    assert body["status"] == 201
    assert (body["kind"], body["width"], body["height"]) == ("ai_image", 1080, 1350)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        cover = await session.get(AutopilotCoverAssetModel, UUID(str(body["asset_id"])))
        assert cover is not None
        assert cover.source_url is None
        assert cover.topic_candidate_id is None
        asset = await session.get(CarouselCreatorAssetModel, cover.creator_asset_id)
        assert asset is not None
        assert asset.role == "cover"
        assert asset.owner_id == _OWNER
        library = await PostgresCreatorAssetRepository(session).list_for_owner(
            CreatorAssetLibraryQuery(owner_id=_OWNER)
        )
        assert library == []


# Scenario: An ai_image wider than 4:5 is centre-cropped before the size check
@pytest.mark.asyncio
async def test_wide_jpeg_is_cropped_and_scaled_to_the_slide(
    api: tuple[AsyncClient, AsyncEngine, _Clock],
) -> None:
    client, _engine, _clock = api
    body = await _upload(client, _image((2000, 1350), "JPEG"), {"kind": "ai_image"})
    assert (body["status"], body["width"], body["height"]) == (201, 1080, 1350)


# Scenario: A screenshot keeps its aspect and needs 600 px of width
@pytest.mark.asyncio
async def test_screenshot_keeps_its_size_and_canonical_source(
    api: tuple[AsyncClient, AsyncEngine, _Clock],
) -> None:
    client, engine, _clock = api
    form = {
        "kind": "screenshot",
        "source_url": "https://twitter.com/poteto/status/2111133080526495985/",
    }
    body = await _upload(client, _image((800, 400)), form)
    assert (body["status"], body["width"], body["height"]) == (201, 800, 400)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        cover = await session.get(AutopilotCoverAssetModel, UUID(str(body["asset_id"])))
        assert cover is not None
        assert cover.source_url == _X_POST
    narrow = await _upload(client, _image((599, 900)), form)
    assert (narrow["status"], narrow["detail"]) == (422, "asset_too_small")


# Scenario Outline: Upload rejections carry a stable code
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("content", "form", "status", "code"),
    [
        (
            b"\x89PNG\r\n\x1a\n" + b"0" * _FIVE_MB,
            {"kind": "ai_image"},
            413,
            "asset_too_large",
        ),
        ("wide", {"kind": "ai_image"}, 413, "asset_too_large"),
        ("webp", {"kind": "ai_image"}, 415, "asset_type_unsupported"),
        (b"just some text", {"kind": "ai_image"}, 415, "asset_type_unsupported"),
        (None, {"kind": "ai_image"}, 415, "asset_type_unsupported"),
        ("small", {"kind": "ai_image"}, 422, "asset_too_small"),
        ("ok", {"kind": "photo"}, 422, "asset_kind_invalid"),
        ("ok", {}, 422, "asset_kind_invalid"),
        ("ok", {"kind": "screenshot"}, 422, "asset_source_missing"),
        (
            "ok",
            {"kind": "screenshot", "source_url": "not a url"},
            422,
            "asset_source_missing",
        ),
    ],
)
async def test_upload_rejections(
    api: tuple[AsyncClient, AsyncEngine, _Clock],
    content: bytes | str | None,
    form: dict[str, str],
    status: int,
    code: str,
) -> None:
    client, _engine, _clock = api
    named = {
        "wide": _image((5000, 1000)),
        "webp": _image((1080, 1350), "WEBP"),
        "small": _image((1200, 1200)),
        "ok": _image((1080, 1350)),
    }
    payload = named[content] if isinstance(content, str) else content
    body = await _upload(client, payload, form)
    assert (body["status"], body["detail"]) == (status, code)


# Scenario: The upload route needs the API key
@pytest.mark.asyncio
async def test_upload_needs_the_api_key(
    api: tuple[AsyncClient, AsyncEngine, _Clock],
) -> None:
    client, _engine, _clock = api
    response = await client.post(
        _ASSETS,
        data={"kind": "ai_image"},
        files={"file": ("c.png", _image((1080, 1350)), "image/png")},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_upload_without_an_owner_user_is_unavailable(
    api: tuple[AsyncClient, AsyncEngine, _Clock], monkeypatch: pytest.MonkeyPatch
) -> None:
    from rag_backend.infrastructure.config.settings import get_settings

    client, _engine, _clock = api
    monkeypatch.setenv("AUTOPILOT_OWNER_USER_ID", "")
    get_settings.cache_clear()
    body = await _upload(client, _image((1080, 1350)), {"kind": "ai_image"})
    assert (body["status"], body["detail"]) == (503, "autopilot_owner_unconfigured")


def _with_cover(topic: dict[str, object], asset_id: object) -> dict[str, object]:
    return {**topic, "cover": {"asset_id": str(asset_id)}}


async def _ai_cover(client: AsyncClient) -> str:
    body = await _upload(client, _image((1080, 1350)), {"kind": "ai_image"})
    return str(body["asset_id"])


async def _post(
    client: AsyncClient, topics: list[dict[str, object]]
) -> dict[str, object]:
    response = await client.post(_PATH, headers=_headers(), json={"topics": topics})
    return {"status": response.status_code, **response.json()}


async def _stored_cover(engine: AsyncEngine, asset_id: str) -> tuple[object, object]:
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        topic_cover = await session.scalar(select(TopicCandidateModel.cover_asset_id))
        cover = await session.get(AutopilotCoverAssetModel, UUID(asset_id))
    assert cover is not None
    return topic_cover, cover.topic_candidate_id


# Scenario Outline: A topic with a fresh cover is accepted in every mode
@pytest.mark.asyncio
@pytest.mark.parametrize("mode", [{}, _POV, _POV_NEWS])
async def test_topic_with_cover_is_accepted_in_every_mode(
    api: tuple[AsyncClient, AsyncEngine, _Clock], mode: dict[str, str]
) -> None:
    client, engine, clock = api
    asset_id = await _ai_cover(client)
    clock._moment = _AS_OF + timedelta(hours=1)
    topic = _with_cover({**_topic("Agents ship", _URL_A, 80), **mode}, asset_id)
    body = await _post(client, [topic])
    assert body["status"] == 200
    assert len(body["accepted"]) == 1
    assert body["rejected"] == []
    topic_cover, used_by = await _stored_cover(engine, asset_id)
    assert str(topic_cover) == asset_id
    assert str(used_by) == str(body["accepted"][0])


# Scenario Outline: A bad cover rejects only that topic
@pytest.mark.asyncio
async def test_unknown_and_malformed_covers(
    api: tuple[AsyncClient, AsyncEngine, _Clock],
) -> None:
    client, _engine, _clock = api
    body = await _post(
        client,
        [
            _with_cover(_topic("Agents ship", _URL_A, 80), uuid4()),
            _with_cover(_topic("Models merge", _URL_B, 70), "not-a-uuid"),
            _topic("Robots plan", _URL_B, 60),
        ],
    )
    assert len(body["accepted"]) == 1
    reasons = [(r["index"], r["reason"], r["field"]) for r in body["rejected"]]
    assert reasons == [
        (0, "cover_asset_unknown", "cover.asset_id"),
        (1, "cover_asset_unknown", "cover.asset_id"),
    ]


@pytest.mark.asyncio
async def test_expired_cover_is_rejected(
    api: tuple[AsyncClient, AsyncEngine, _Clock],
) -> None:
    client, engine, clock = api
    asset_id = await _ai_cover(client)
    clock._moment = _AS_OF + timedelta(hours=7)
    await _serve(engine, (_URL_A,), clock._moment)
    body = await _post(
        client, [_with_cover(_topic("Agents ship", _URL_A, 80), asset_id)]
    )
    assert [r["reason"] for r in body["rejected"]] == ["cover_asset_expired"]


@pytest.mark.asyncio
async def test_used_cover_is_rejected_and_one_batch_uses_it_once(
    api: tuple[AsyncClient, AsyncEngine, _Clock],
) -> None:
    client, _engine, _clock = api
    asset_id = await _ai_cover(client)
    # Scenario: The same cover twice in one batch is used once
    body = await _post(
        client,
        [
            _with_cover(_topic("Agents ship", _URL_A, 80), asset_id),
            _with_cover(_topic("Models merge", _URL_B, 70), asset_id),
        ],
    )
    assert len(body["accepted"]) == 1
    assert [(r["index"], r["reason"]) for r in body["rejected"]] == [
        (1, "cover_asset_used")
    ]
    again = await _post(
        client, [_with_cover(_topic("Robots plan", _URL_B, 60), asset_id)]
    )
    assert [r["reason"] for r in again["rejected"]] == ["cover_asset_used"]


@pytest.mark.asyncio
async def test_screenshot_source_must_be_a_topic_source(
    api: tuple[AsyncClient, AsyncEngine, _Clock],
) -> None:
    """A rejected topic leaves the asset free: once fixed and sent again, it is
    accepted.
    """
    client, _engine, _clock = api
    form = {"kind": "screenshot", "source_url": _X_POST}
    asset_id = str((await _upload(client, _image((800, 600)), form))["asset_id"])
    wrong = await _post(
        client, [_with_cover(_topic("Agents ship", _URL_A, 80), asset_id)]
    )
    assert [(r["reason"], r["field"]) for r in wrong["rejected"]] == [
        ("cover_source_invalid", "cover.asset_id")
    ]
    right = await _post(
        client, [_with_cover(_topic("Agents ship", _X_POST, 80), asset_id)]
    )
    assert right["rejected"] == []
    assert len(right["accepted"]) == 1


# Scenario: Unknown keys inside cover reject the batch
@pytest.mark.asyncio
async def test_unknown_key_inside_cover_is_a_batch_422(
    api: tuple[AsyncClient, AsyncEngine, _Clock],
) -> None:
    client, _engine, _clock = api
    topic = {
        **_topic("Agents ship", _URL_A, 80),
        "cover": {"asset_id": str(uuid4()), "url": _URL_A},
    }
    body = await _post(client, [topic])
    assert body["status"] == 422
