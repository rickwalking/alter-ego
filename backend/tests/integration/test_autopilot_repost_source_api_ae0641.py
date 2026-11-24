"""POST /api/autopilot/assets/video through the real app, store and folder.

Gherkin: tests/features/autopilot_repost_source_video_ae0641.feature
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from dataclasses import replace
from pathlib import Path
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from rag_backend.modules.autopilot.domain.repost_source import VideoProbe
from rag_backend.modules.autopilot.infrastructure.repost_source_files import (
    FfprobeVideoProbe,
    write_chunks,
)
from rag_backend.modules.autopilot.infrastructure.repost_source_models import (
    RepostSourceModel,
)
from tests.integration.autopilot_topic_support import (
    _AS_OF,
    _client,
    _Clock,
    _headers,
    configured_key,
)
from tests.unit.modules.autopilot.repost_source_fakes import HD

_ = configured_key
_PATH = "/api/autopilot/assets/video"


@pytest.fixture
def output_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, configured_key: None
) -> Iterator[Path]:
    from rag_backend.infrastructure.config.settings import get_settings

    del configured_key
    monkeypatch.setenv("CAROUSEL_OUTPUT_DIR", str(tmp_path / "output" / "carousels"))
    get_settings.cache_clear()
    yield tmp_path / "output" / "reposts" / "sources"
    get_settings.cache_clear()


@pytest.fixture
async def api(
    output_env: Path, tmp_path: Path
) -> AsyncIterator[tuple[AsyncClient, AsyncEngine]]:
    del output_env
    async for client, engine in _client(tmp_path / "s.db", _Clock(_AS_OF)):
        yield client, engine


def _probe(monkeypatch: pytest.MonkeyPatch, result: VideoProbe | None) -> None:
    async def probe(self: FfprobeVideoProbe, path: Path) -> VideoProbe | None:
        del self
        assert path.is_file()
        return result

    monkeypatch.setattr(FfprobeVideoProbe, "probe", probe)


async def _rows(engine: AsyncEngine) -> list[RepostSourceModel]:
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        return list(await session.scalars(select(RepostSourceModel)))


# Scenario: An H.264 portrait video is stored and gets an asset_id
async def test_upload_is_stored_and_answered(
    api: tuple[AsyncClient, AsyncEngine],
    output_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, engine = api
    _probe(monkeypatch, HD)
    response = await client.post(
        _PATH, files={"file": ("cut.mp4", b"x" * 2048, "video/mp4")}, headers=_headers()
    )
    assert response.status_code == 201
    body = response.json()
    asset_id = UUID(body["asset_id"])
    assert body == {
        "asset_id": str(asset_id),
        "kind": "video",
        "width": 1080,
        "height": 1920,
        "duration_s": 86.0,
        "size_bytes": 2048,
    }
    assert (output_env / f"{asset_id}.mp4").read_bytes() == b"x" * 2048
    assert [row.id for row in await _rows(engine)] == [asset_id]
    assert list(output_env.glob("*.part")) == []


# Scenario Outline: An unusable upload is refused and not kept
@pytest.mark.parametrize(
    ("result", "code"),
    [
        (None, "source_not_video"),
        (replace(HD, codec="hevc"), "source_codec_unsupported"),
        (replace(HD, duration_s=200.0), "source_duration_invalid"),
    ],
)
async def test_bad_upload_is_refused_and_not_kept(
    api: tuple[AsyncClient, AsyncEngine],
    output_env: Path,
    monkeypatch: pytest.MonkeyPatch,
    result: VideoProbe | None,
    code: str,
) -> None:
    client, engine = api
    _probe(monkeypatch, result)
    response = await client.post(
        _PATH, files={"file": ("cut.mp4", b"x", "video/mp4")}, headers=_headers()
    )
    assert (response.status_code, response.json()) == (422, {"detail": code})
    assert list(output_env.glob("*")) == []
    assert await _rows(engine) == []


# Scenario Outline: An unusable upload is refused and not kept
async def test_missing_file_and_oversize(
    api: tuple[AsyncClient, AsyncEngine],
    output_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _engine = api
    _probe(monkeypatch, HD)
    missing = await client.post(_PATH, data={"x": "1"}, headers=_headers())
    assert (missing.status_code, missing.json()) == (
        400,
        {"detail": "source_file_missing"},
    )
    from rag_backend.modules.autopilot.api import repost_source

    async def capped(chunks: AsyncIterator[bytes], target: Path) -> int:
        return await write_chunks(chunks, target, 8)

    monkeypatch.setattr(repost_source, "write_chunks", capped)
    big = await client.post(
        _PATH, files={"file": ("cut.mp4", b"x" * 9, "video/mp4")}, headers=_headers()
    )
    assert (big.status_code, big.json()) == (413, {"detail": "source_too_large"})
    assert list(output_env.glob("*")) == []


async def test_upload_requires_the_api_key(
    api: tuple[AsyncClient, AsyncEngine],
) -> None:
    client, _engine = api
    response = await client.post(_PATH, files={"file": ("cut.mp4", b"x", "video/mp4")})
    assert response.status_code == 401
