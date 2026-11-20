"""HTTP routes: /reels, /reels/{id}/video, /repost, /repost/{id}, /reposts, /r/...

Gherkin: tests/features/autopilot_reels_list_ae0626.feature,
tests/features/autopilot_repost_drafts_ae0628.feature,
tests/features/autopilot_repost_publish_ae0629.feature
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
import respx
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from rag_backend.modules.autopilot.api.reels import ReelsBundle, reels_bundle
from rag_backend.modules.autopilot.api.repost import RepostBundle, repost_bundle
from rag_backend.modules.autopilot.api.repost_files import RepostFiles, repost_files
from rag_backend.modules.autopilot.application.reels_service import (
    ReelsDeps,
    ReelsService,
)
from rag_backend.modules.autopilot.application.repost_drafts import (
    RepostDeps,
    RepostDraftService,
)
from rag_backend.modules.autopilot.infrastructure.cover_store import SqlCoverAssetStore
from rag_backend.modules.autopilot.infrastructure.insights_store import SqlInsightsStore
from rag_backend.modules.autopilot.infrastructure.repost_store import SqlRepostStore
from rag_backend.modules.autopilot.repost_constants import (
    STATUS_EXPIRED,
    STATUS_PENDING,
)
from tests.integration.autopilot_topic_support import _headers, configured_key
from tests.unit.modules.autopilot.repost_fakes import (
    MEDIA,
    VIDEO_URL,
    Clock,
    FakeProbe,
    FakeReels,
    reel,
    stored,
)

_ = configured_key
_BASE = "https://site.example"


@dataclass
class _Api:
    client: AsyncClient
    app: FastAPI
    sessions: async_sessionmaker[AsyncSession]
    reels: FakeReels
    root: Path


@pytest.fixture
async def api(tmp_path: Path, configured_key: None) -> AsyncIterator[_Api]:
    import rag_backend.infrastructure.database.config as db_config
    from rag_backend.api.app import create_app
    from rag_backend.api.middleware.rate_limiting import limiter
    from rag_backend.infrastructure.database.config import Base, close_db

    del configured_key
    limiter.reset()
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'api.db'}", poolclass=NullPool
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    db_config.c_engine = engine
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    reels = FakeReels(
        items={
            MEDIA: reel(),
            "222": reel("222", days_old=10),
            "333": reel("333", product="FEED"),
        }
    )
    app = create_app()
    _override(app, sessions, reels, tmp_path)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            yield _Api(
                client=client,
                app=app,
                sessions=sessions,
                reels=reels,
                root=tmp_path / "reposts",
            )
    finally:
        limiter.reset()
        await close_db()
        db_config.c_engine = None


def _override(
    app: FastAPI,
    sessions: async_sessionmaker[AsyncSession],
    reels: FakeReels,
    tmp: Path,
) -> None:
    async def bundle() -> AsyncIterator[RepostBundle]:
        async with sessions() as session:
            store = SqlRepostStore(session)
            yield RepostBundle(
                service=RepostDraftService(
                    RepostDeps(
                        store=store,
                        covers=SqlCoverAssetStore(session),
                        facts=store,
                        reels=reels,
                        probe=FakeProbe(),
                        clock=Clock(),
                    )
                ),
                base=_BASE,
            )

    async def list_bundle() -> AsyncIterator[ReelsBundle]:
        async with sessions() as session:
            store = SqlRepostStore(session)
            service = ReelsService(
                ReelsDeps(
                    reels=reels,
                    insights_gateway=None,
                    insights=SqlInsightsStore(session),
                    facts=store,
                    reposts=store,
                    probe=FakeProbe(),
                    clock=Clock(),
                )
            )
            yield ReelsBundle(service=service, reels=reels)

    async def files() -> AsyncIterator[RepostFiles]:
        async with sessions() as session:
            yield RepostFiles(store=SqlRepostStore(session), root=tmp / "reposts")

    app.dependency_overrides[repost_bundle] = bundle
    app.dependency_overrides[reels_bundle] = list_bundle
    app.dependency_overrides[repost_files] = files


def _body(**changes: object) -> dict[str, object]:
    body: dict[str, object] = {
        "media_id": MEDIA,
        "caption": "Nova legenda #ia",
        "hook_text": "Sua IA aprova o próprio código ruim.",
        "reason": "Views 3x acima da mediana da conta",
        "score": 1.82,
    }
    body.update(changes)
    return body


def _key_headers(key: str = "scout-2026-11-19") -> dict[str, str]:
    return {**_headers(), "Idempotency-Key": key}


# Scenario: A valid draft is accepted
# Scenario: The same key and body replay the original response
async def test_post_repost_and_replay(api: _Api) -> None:
    first = await api.client.post(
        "/api/autopilot/repost", json=_body(), headers=_key_headers()
    )
    assert first.status_code == 202
    data = first.json()
    assert data["status"] == STATUS_PENDING
    assert data["preview_url"] == f"{_BASE}/r/{data['id']}/preview.mp4"
    again = await api.client.post(
        "/api/autopilot/repost", json=_body(), headers=_key_headers()
    )
    assert again.status_code == 202 and again.json() == data


# Scenario: The same key with a different body conflicts
# Scenario Outline: Field rules answer 400 invalid_field
async def test_post_repost_errors_use_the_envelope(api: _Api) -> None:
    await api.client.post("/api/autopilot/repost", json=_body(), headers=_key_headers())
    conflict = await api.client.post(
        "/api/autopilot/repost", json=_body(caption="outra"), headers=_key_headers()
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "idempotency_conflict"
    missing = await api.client.post(
        "/api/autopilot/repost", json=_body(), headers=_headers()
    )
    assert (
        missing.status_code == 400
        and missing.json()["error"]["field"] == "Idempotency-Key"
    )
    short = await api.client.post(
        "/api/autopilot/repost", json=_body(), headers=_key_headers("k-12345")
    )
    assert (short.status_code, short.json()["error"]["field"]) == (
        400,
        "Idempotency-Key",
    )
    for body, field in (
        (_body(unknown=1), "unknown"),
        (_body(caption=None), "caption"),
        (_body(cover={"asset_id": "nope"}), "cover.asset_id"),
        (_body(hook_text="x" * 91), "hook_text"),
    ):
        bad = await api.client.post(
            "/api/autopilot/repost", json=body, headers=_key_headers(f"k-{uuid4().hex}")
        )
        assert bad.status_code == 400, bad.text
        assert bad.json()["error"]["field"] == field
    raw = await api.client.post(
        "/api/autopilot/repost",
        content=b"{",
        headers={**_key_headers("k-raw-json"), "content-type": "application/json"},
    )
    assert raw.json()["error"]["field"] == "body"
    empty = await api.client.post(
        "/api/autopilot/repost", json=[], headers=_key_headers("k-list-body")
    )
    assert empty.status_code == 400


# Scenario: A foreign id or a non-Reel is not found
# Scenario: A Reel younger than 60 days is too recent
async def test_post_repost_eligibility(api: _Api) -> None:
    for media, status, code in (
        ("999", 404, "reel_not_found"),
        ("333", 404, "reel_not_found"),
        ("222", 422, "too_recent"),
    ):
        response = await api.client.post(
            "/api/autopilot/repost",
            json=_body(media_id=media),
            headers=_key_headers(f"k-{media}-abcdef"),
        )
        assert response.status_code == status
        assert response.json()["error"] == {
            "code": code,
            "message": response.json()["error"]["message"],
            "field": None,
        }


# Scenario: GET /repost/{id} and GET /reposts
async def test_get_and_list(api: _Api) -> None:
    created = (
        await api.client.post(
            "/api/autopilot/repost", json=_body(), headers=_key_headers()
        )
    ).json()
    one = await api.client.get(
        f"/api/autopilot/repost/{created['id']}", headers=_headers()
    )
    assert one.status_code == 200
    assert one.json()["status"] == STATUS_PENDING and one.json()["preview_url"] is None
    missing = await api.client.get(
        f"/api/autopilot/repost/{uuid4()}", headers=_headers()
    )
    assert (
        missing.status_code == 404
        and missing.json()["error"]["code"] == "repost_not_found"
    )
    listed = await api.client.get(
        "/api/autopilot/reposts?status=pending_approval&since=2020-01-01T00:00:00Z&limit=5",
        headers=_headers(),
    )
    assert [i["id"] for i in listed.json()["items"]] == [created["id"]]
    for query, field in (
        ("status=nope", "status"),
        ("since=yesterday", "since"),
        ("since=2026-01-01T00:00:00", "since"),
        ("limit=0", "limit"),
    ):
        bad = await api.client.get(
            f"/api/autopilot/reposts?{query}", headers=_headers()
        )
        assert bad.status_code == 400 and bad.json()["error"]["field"] == field
    assert (
        await api.client.get("/api/autopilot/reposts", headers=_headers())
    ).status_code == 200


# Scenario: Every reels and repost route needs the API key
async def test_routes_require_the_key(api: _Api) -> None:
    for method, path in (
        ("GET", "/api/autopilot/reels"),
        ("GET", f"/api/autopilot/reels/{MEDIA}/video"),
        ("GET", f"/api/autopilot/repost/{uuid4()}"),
        ("POST", "/api/autopilot/repost"),
        ("GET", "/api/autopilot/reposts"),
    ):
        response = await api.client.request(method, path)
        assert response.status_code == 401


# Scenario: Only Reels inside the age window are listed
async def test_get_reels(api: _Api) -> None:
    response = await api.client.get("/api/autopilot/reels", headers=_headers())
    assert response.status_code == 200
    data = response.json()
    assert [i["media_id"] for i in data["items"]] == [MEDIA]
    item = data["items"][0]
    assert item["video_url_expires_at"] is not None and item["duration_s"] == 60.0
    assert item["stale"] is True and item["last_repost"] is None
    assert set(data["baseline"]) == {
        "median_views",
        "median_shares_per_100_views",
        "median_engagement_rate",
    }
    bad = await api.client.get("/api/autopilot/reels?limit=500", headers=_headers())
    assert bad.status_code == 400 and bad.json()["error"] == {
        "code": "invalid_field",
        "message": "out of range",
        "field": "limit",
    }


# Scenario: The video route streams the MP4
# Scenario: The video route refuses other media
async def test_reel_video(api: _Api) -> None:
    with respx.mock(assert_all_called=False) as router:
        router.route(host="test").pass_through()
        router.get(VIDEO_URL).respond(
            200, content=b"MP4DATA", headers={"content-length": "7"}
        )
        ok = await api.client.get(
            f"/api/autopilot/reels/{MEDIA}/video", headers=_headers()
        )
        assert ok.status_code == 200
        assert ok.headers["content-type"] == "video/mp4" and ok.content == b"MP4DATA"
        router.get(VIDEO_URL).respond(403)
        cdn_down = await api.client.get(
            f"/api/autopilot/reels/{MEDIA}/video", headers=_headers()
        )
        assert cdn_down.status_code == 503
        router.get(VIDEO_URL).mock(side_effect=httpx.ConnectError("x"))
        broken = await api.client.get(
            f"/api/autopilot/reels/{MEDIA}/video", headers=_headers()
        )
        assert broken.status_code == 503
    for media in ("333", "999"):
        response = await api.client.get(
            f"/api/autopilot/reels/{media}/video", headers=_headers()
        )
        assert (
            response.status_code == 404
            and response.json()["error"]["code"] == "reel_not_found"
        )


# Scenario: Public files are served only for a live repost
async def test_public_files(api: _Api) -> None:
    live = stored()
    gone = stored(status=STATUS_EXPIRED)
    async with api.sessions() as session:
        store = SqlRepostStore(session)
        await store.insert(live)
        await store.insert(gone)
        await store.commit()
    for row in (live, gone):
        folder = api.root / str(row.id)
        folder.mkdir(parents=True)
        (folder / "preview.mp4").write_bytes(b"mp4")
    ok = await api.client.get(f"/r/{live.id}/preview.mp4")
    assert ok.status_code == 200 and ok.headers["content-type"] == "video/mp4"
    head = await api.client.head(f"/r/{live.id}/preview.mp4")
    assert head.status_code == 200 and head.content == b""
    for path in (
        f"/r/{live.id}/cover.jpg",
        f"/r/{live.id}/source.mp4",
        f"/r/{gone.id}/preview.mp4",
        f"/r/{uuid4()}/preview.mp4",
    ):
        assert (await api.client.get(path)).status_code == 404


# Scenario: Too many calls answer the 429 envelope
async def test_rate_limit_uses_the_envelope(api: _Api) -> None:
    statuses = [
        (await api.client.get("/api/autopilot/reposts", headers=_headers())).status_code
        for _ in range(11)
    ]
    assert statuses[-1] == 429
    over = await api.client.get("/api/autopilot/reposts", headers=_headers())
    assert over.json()["error"]["code"] == "rate_limited"


# Scenario: Reposted Reels are hidden
async def test_reels_hide_and_show_last_repost(api: _Api) -> None:
    created = (
        await api.client.post(
            "/api/autopilot/repost", json=_body(), headers=_key_headers()
        )
    ).json()
    hidden = await api.client.get("/api/autopilot/reels", headers=_headers())
    assert hidden.json()["items"] == []
    shown = await api.client.get(
        "/api/autopilot/reels?exclude_reposted_days=0", headers=_headers()
    )
    last = shown.json()["items"][0]["last_repost"]
    assert last["repost_id"] == created["id"] and last["status"] == STATUS_PENDING
