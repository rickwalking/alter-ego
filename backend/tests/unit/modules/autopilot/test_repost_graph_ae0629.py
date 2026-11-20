"""Graph adapters: the Reels reader, the Reels publisher, the Telegram messenger.

Gherkin: tests/features/autopilot_reels_list_ae0626.feature,
tests/features/autopilot_repost_publish_ae0629.feature
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from rag_backend.infrastructure.external.meta_instagram_publisher import (
    MetaInstagramPublisherConfig,
)
from rag_backend.modules.autopilot.application.repost_tick_ports import (
    ContainerRequest,
)
from rag_backend.modules.autopilot.domain.exceptions import InstagramCallError
from rag_backend.modules.autopilot.domain.messages import InlineButton, InlineKeyboard
from rag_backend.modules.autopilot.infrastructure.graph_json import GraphJson
from rag_backend.modules.autopilot.infrastructure.reels_gateway import (
    GraphReelGateway,
    parse_collaborators,
    parse_reel,
    parse_reels_page,
)
from rag_backend.modules.autopilot.infrastructure.repost_graph import (
    GraphReelPublisher,
    container_params,
    parse_status,
)
from rag_backend.modules.autopilot.infrastructure.repost_notifier import (
    PreviewMessage,
    TelegramRepostMessenger,
    fits_telegram,
)

_BASE = "https://graph.example"
_USER = "999"


class _Token:
    def __init__(self, value: str = "tok") -> None:
        self.value = value

    async def get(self) -> str:
        return self.value


def _config(token: str = "tok", user: str = _USER) -> MetaInstagramPublisherConfig:
    return MetaInstagramPublisherConfig(
        ig_user_id=user, graph_base=_BASE, token_provider=_Token(token)
    )


def _item(media_id: str, ts: str, product: str = "REELS") -> dict[str, object]:
    return {
        "id": media_id,
        "media_type": "VIDEO",
        "media_product_type": product,
        "timestamp": ts,
        "permalink": f"https://ig/{media_id}",
        "shortcode": "abc",
        "caption": "cap",
        "media_url": "https://cdn/v.mp4",
        "thumbnail_url": "https://cdn/t.jpg",
    }


def test_parse_reels_page_keeps_reels_only() -> None:
    payload = {
        "data": [
            _item("1", "2026-05-10T15:00:00+0000"),
            _item("2", "2026-05-09T15:00:00Z", product="FEED"),
            _item("x", "2026-05-09T15:00:00Z"),
            {"id": "3", "timestamp": "nope"},
            "junk",
        ]
    }
    items = parse_reels_page(payload)
    assert [i.media_id for i in items] == ["1"]
    assert items[0].posted_at == datetime(2026, 5, 10, 15, tzinfo=UTC)
    assert parse_reels_page({"data": "x"}) == []
    naive = parse_reel(_item("5", "2026-05-10T15:00:00"))
    assert naive is not None and naive.posted_at.tzinfo is not None
    assert parse_reel({"id": "5", "timestamp": 3}) is None


def test_parse_collaborators() -> None:
    payload = {
        "data": [
            {"username": "rick"},
            {"username": ""},
            {"username": "x" * 31},
            {"id": 1},
            "j",
        ]
    }
    assert parse_collaborators(payload) == ("rick",)
    assert parse_collaborators({}) == ()


def _client(handler: object) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))  # type: ignore[arg-type]


# Scenario: Only Reels inside the age window are listed
async def test_list_reels_walks_pages_until_since() -> None:
    pages = {
        None: {
            "data": [_item("1", "2026-11-01T00:00:00Z")],
            "paging": {"cursors": {"after": "p2"}},
        },
        "p2": {
            "data": [
                _item("2", "2026-06-01T00:00:00Z"),
                _item("3", "2024-01-01T00:00:00Z"),
            ],
            "paging": {"cursors": {"after": "p3"}},
        },
    }
    seen: list[str | None] = []

    def handler(request: httpx.Request) -> httpx.Response:
        after = request.url.params.get("after")
        seen.append(after)
        assert request.url.params["access_token"] == "tok"
        return httpx.Response(200, json=pages[after])

    async with _client(handler) as client:
        gateway = GraphReelGateway(GraphJson(_config(), client))
        found = await gateway.list_reels(datetime(2025, 1, 1, tzinfo=UTC))
    assert [r.media_id for r in found] == ["1", "2"]
    assert seen == [None, "p2"]
    assert gateway.ig_user_id == _USER


async def test_list_reels_last_page_and_errors() -> None:
    def ok(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": [_item("1", "2026-11-01T00:00:00Z")]})

    async with _client(ok) as client:
        assert (
            len(
                await GraphReelGateway(GraphJson(_config(), client)).list_reels(
                    datetime(2020, 1, 1, tzinfo=UTC)
                )
            )
            == 1
        )

    def bad(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": {"code": 2}})

    async with _client(bad) as client:
        with pytest.raises(InstagramCallError):
            await GraphReelGateway(GraphJson(_config(), client)).list_reels(
                datetime(2020, 1, 1, tzinfo=UTC)
            )

    def html(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>")

    async with _client(html) as client:
        with pytest.raises(InstagramCallError) as error:
            await GraphReelGateway(GraphJson(_config(), client)).list_reels(
                datetime(2020, 1, 1, tzinfo=UTC)
            )
    assert error.value.transient

    async with _client(ok) as client:
        with pytest.raises(InstagramCallError):
            await GraphReelGateway(GraphJson(_config(token=""), client)).list_reels(
                datetime(2020, 1, 1, tzinfo=UTC)
            )


async def test_list_reels_stops_at_page_cap() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "data": [_item("1", "2026-11-01T00:00:00Z")],
                "paging": {"cursors": {"after": "n"}},
            },
        )

    async with _client(handler) as client:
        found = await GraphReelGateway(GraphJson(_config(), client)).list_reels(
            datetime(2020, 1, 1, tzinfo=UTC)
        )
    assert len(found) == 20


async def test_reel_lookup_owner_and_not_found() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        media = request.url.path.strip("/")
        if media == "404":
            return httpx.Response(400, json={"error": {"code": 100}})
        if media == "500":
            return httpx.Response(500, json={"error": {"code": 1}})
        owner = {"id": "other"} if media == "222" else {"id": _USER}
        body = _item(media, "2026-05-10T15:00:00Z") | {"owner": owner}
        if media == "333":
            body.pop("owner")
        return httpx.Response(200, json=body)

    async with _client(handler) as client:
        gateway = GraphReelGateway(GraphJson(_config(), client))
        assert (await gateway.reel("111")) is not None
        assert await gateway.reel("222") is None
        assert await gateway.reel("333") is not None
        assert await gateway.reel("404") is None
        assert await gateway.reel("abc") is None
        with pytest.raises(InstagramCallError):
            await gateway.reel("500")


async def test_collaborators_lookup() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.startswith("/404"):
            return httpx.Response(400, json={"error": {"code": 100}})
        if request.url.path.startswith("/500"):
            return httpx.Response(503, json={})
        return httpx.Response(200, json={"data": [{"username": "rick"}]})

    async with _client(handler) as client:
        gateway = GraphReelGateway(GraphJson(_config(), client))
        assert await gateway.collaborators("111") == ("rick",)
        assert await gateway.collaborators("404") == ()
        with pytest.raises(InstagramCallError):
            await gateway.collaborators("500")


def test_container_params() -> None:
    full = container_params(
        ContainerRequest(
            video_url="https://v",
            caption="c",
            cover_url="https://c",
            share_to_feed=True,
            collaborators=("a", "b"),
        )
    )
    assert full["media_type"] == "REELS" and full["share_to_feed"] == "true"
    assert json.loads(full["collaborators"]) == ["a", "b"]
    assert full["cover_url"] == "https://c"
    bare = container_params(
        ContainerRequest(
            video_url="https://v",
            caption="c",
            cover_url=None,
            share_to_feed=False,
            collaborators=(),
        )
    )
    assert bare["share_to_feed"] == "false"
    assert "cover_url" not in bare and "collaborators" not in bare


def test_parse_status() -> None:
    assert (
        parse_status({"status_code": "FINISHED", "status": "Finished"}).code
        == "FINISHED"
    )
    blank = parse_status({"status": ""})
    assert (blank.code, blank.detail) == ("", None)


# Scenario: A finished container is published
async def test_publisher_flow() -> None:
    calls: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        path = request.url.path
        if path == f"/{_USER}/media":
            assert request.url.params["video_url"] == "https://v"
            return httpx.Response(200, json={"id": "c-1"})
        if path == "/c-1":
            return httpx.Response(200, json={"status_code": "FINISHED"})
        if path == f"/{_USER}/media_publish":
            assert request.url.params["creation_id"] == "c-1"
            return httpx.Response(200, json={"id": "m-1"})
        return httpx.Response(200, json={"permalink": "https://ig/m-1"})

    async with _client(handler) as client:
        publisher = GraphReelPublisher(GraphJson(_config(), client))
        request = ContainerRequest(
            video_url="https://v",
            caption="c",
            cover_url=None,
            share_to_feed=True,
            collaborators=(),
        )
        assert await publisher.create(request) == "c-1"
        assert (await publisher.status("c-1")).code == "FINISHED"
        assert await publisher.publish("c-1") == "m-1"
        assert await publisher.permalink("m-1") == "https://ig/m-1"
    assert calls[0][0] == "POST"


async def test_publisher_errors() -> None:
    def no_id(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/m-1":
            return httpx.Response(200, json={})
        return httpx.Response(200, json={"other": 1})

    async with _client(no_id) as client:
        publisher = GraphReelPublisher(GraphJson(_config(), client))
        with pytest.raises(InstagramCallError) as error:
            await publisher.publish("c")
        assert not error.value.transient
        assert await publisher.permalink("m-1") is None

    def refuse(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": {"code": 9004}})

    async with _client(refuse) as client:
        with pytest.raises(InstagramCallError) as error:
            await GraphReelPublisher(GraphJson(_config(), client)).status("c")
    assert error.value.error_code == "9004"

    def html(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>")

    async with _client(html) as client:
        with pytest.raises(InstagramCallError):
            await GraphReelPublisher(GraphJson(_config(), client)).status("c")
        with pytest.raises(InstagramCallError):
            await GraphReelPublisher(GraphJson(_config(user=""), client)).status("c")


def _keyboard() -> InlineKeyboard:
    return InlineKeyboard(
        rows=((InlineButton(text="ok", callback_data="ap:rp:ok:x"),),)
    )


# Scenario: A pending draft is rendered and sent to the owner
async def test_messenger_sends_cover_video_then_prompt(
    tmp_path: Path, respx_mock: object
) -> None:
    from PIL import Image

    cover = tmp_path / "cover.jpg"
    Image.new("RGB", (10, 10)).save(cover)
    video = tmp_path / "preview.mp4"
    video.write_bytes(b"mp4")
    router = respx_mock  # type: ignore[assignment]
    photo = router.post(url__regex=r".*/sendPhoto").respond(
        200, json={"ok": True, "result": {"message_id": 1}}
    )
    vid = router.post(url__regex=r".*/sendVideo").respond(
        200, json={"ok": True, "result": {"message_id": 2}}
    )
    msg = router.post(url__regex=r".*/sendMessage").respond(
        200, json={"ok": True, "result": {"message_id": 3}}
    )
    messenger = TelegramRepostMessenger(token="t", chat_id="42")
    sent = await messenger.send_preview(
        PreviewMessage(
            cover_path=cover, video_path=video, text="hi", keyboard=_keyboard()
        )
    )
    assert sent == 3
    assert photo.called and vid.called
    body = json.loads(msg.calls.last.request.content)
    assert (
        body["reply_markup"]["inline_keyboard"][0][0]["callback_data"] == "ap:rp:ok:x"
    )
    assert fits_telegram(video)


async def test_messenger_prompt_failure_and_unconfigured(respx_mock: object) -> None:
    router = respx_mock  # type: ignore[assignment]
    router.post(url__regex=r".*/sendMessage").respond(500)
    messenger = TelegramRepostMessenger(token="t", chat_id="42")
    message = PreviewMessage(
        cover_path=None, video_path=None, text="hi", keyboard=_keyboard()
    )
    assert await messenger.send_preview(message) is None
    off = TelegramRepostMessenger(token=" ", chat_id="42")
    assert not off.configured
    assert await off.send_preview(message) is None
    await off.edit(1, "x")
    await off.tell("x")


async def test_messenger_bad_json_edit_and_tell(respx_mock: object) -> None:
    router = respx_mock  # type: ignore[assignment]
    router.post(url__regex=r".*/sendMessage").respond(200, text="oops")
    edit = router.post(url__regex=r".*/editMessageText").respond(200, json={"ok": True})
    messenger = TelegramRepostMessenger(token="t", chat_id="42")
    message = PreviewMessage(
        cover_path=None, video_path=None, text="hi", keyboard=_keyboard()
    )
    assert await messenger.send_preview(message) is None
    await messenger.edit(5, "expired")
    assert json.loads(edit.calls.last.request.content)["message_id"] == 5
    await messenger.tell("published")
