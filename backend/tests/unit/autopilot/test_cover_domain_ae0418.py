"""GrokBot cover rules, credit and the Telegram toggle. Pure.

Gherkin: tests/features/autopilot_grok_cover_ae0418.feature
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from rag_backend.domain.models.slide_cover import (
    SlideCover,
    slide_cover_from_row,
    slide_cover_row,
)
from rag_backend.modules.autopilot.domain.cover import (
    CoverAsset,
    CoverCheck,
    CoverFacts,
    CoverForm,
    clean_source,
    cover_credit,
    cover_reason,
    form_problem,
    is_expired,
    parse_asset_id,
    slide_cover_for,
    source_key,
)
from rag_backend.modules.autopilot.domain.cover_offer import (
    CoverOffer,
    chosen_as,
    cover_button,
    cover_caption,
    cover_notice_key,
    parse_cover_callback,
    with_cover_row,
)
from rag_backend.modules.autopilot.domain.messages import InlineButton, InlineKeyboard
from rag_backend.modules.autopilot.domain.thesis import thesis_keyboard

_NOW = datetime(2026, 10, 17, 12, 0, tzinfo=UTC)
_X = "https://x.com/poteto/status/2111133080526495985"
_RUN = UUID("3f0c9b1e-0000-4000-8000-000000000001")


_BASE = CoverAsset(
    asset_id=uuid4(),
    creator_asset_id=uuid4(),
    kind="ai_image",
    source_url=None,
    width=1080,
    height=1350,
    created_at=_NOW - timedelta(hours=1),
    staged_path="assets/creators/abc.webp",
)


def _asset(**overrides: object) -> CoverAsset:
    return replace(_BASE, asset_id=uuid4(), creator_asset_id=uuid4(), **overrides)


def _reason(
    asset: CoverAsset | None,
    sources: tuple[str, ...] = (_X,),
    claimed: frozenset[UUID] = frozenset(),
) -> str | None:
    assets = {asset.asset_id: asset} if asset is not None else {}
    asset_id = str(asset.asset_id) if asset is not None else str(uuid4())
    facts = CoverFacts(assets=assets, now=_NOW, claimed=claimed)
    return cover_reason(CoverCheck(asset_id=asset_id, sources=sources), facts)


@pytest.mark.parametrize(
    ("kind", "source", "code"),
    [
        ("ai_image", None, None),
        ("ai_image", "garbage", None),
        ("screenshot", _X, None),
        ("screenshot", None, "asset_source_missing"),
        ("screenshot", "   ", "asset_source_missing"),
        ("screenshot", "ftp://x.com/a", "asset_source_missing"),
        ("photo", _X, "asset_kind_invalid"),
        (None, None, "asset_kind_invalid"),
    ],
)
def test_form_problem(kind: str | None, source: str | None, code: str | None) -> None:
    assert form_problem(CoverForm(kind=kind, source_url=source)) == code


def test_clean_source_canonicalizes_x_and_other_urls() -> None:
    assert clean_source("https://twitter.com/poteto/status/2111133080526495985/") == _X
    assert (
        clean_source("https://WWW.TheVerge.com/a/#frag") == "https://www.theverge.com/a"
    )
    assert clean_source(None) is None


def test_source_key_matches_x_status_across_hosts() -> None:
    assert source_key("https://twitter.com/poteto/status/2111133080526495985") == _X
    assert source_key("https://example.com/post/") == "https://example.com/post"


def test_fresh_unused_ai_image_is_allowed() -> None:
    assert _reason(_asset()) is None


def test_unknown_and_malformed_ids_are_unknown() -> None:
    assert _reason(None) == "cover_asset_unknown"
    facts = CoverFacts(assets={}, now=_NOW)
    check = CoverCheck(asset_id="not-a-uuid", sources=(_X,))
    assert cover_reason(check, facts) == "cover_asset_unknown"


def test_expired_after_six_hours() -> None:
    assert _reason(_asset(created_at=_NOW - timedelta(hours=6, seconds=1))) == (
        "cover_asset_expired"
    )
    assert _reason(_asset(created_at=_NOW - timedelta(hours=6))) is None
    assert not is_expired(_asset(created_at=_NOW), _NOW)


def test_no_clock_skips_the_age_check() -> None:
    old = _asset(created_at=_NOW - timedelta(days=3))
    facts = CoverFacts(assets={old.asset_id: old})
    assert (
        cover_reason(CoverCheck(asset_id=str(old.asset_id), sources=()), facts) is None
    )


def test_used_or_claimed_in_the_batch_is_used() -> None:
    assert _reason(_asset(topic_candidate_id=uuid4())) == "cover_asset_used"
    asset = _asset()
    assert _reason(asset, claimed=frozenset({asset.asset_id})) == "cover_asset_used"


def test_screenshot_needs_its_source_in_the_topic_sources() -> None:
    shot = _asset(kind="screenshot", source_url=_X)
    assert _reason(shot, sources=(_X,)) is None
    assert (
        _reason(
            shot, sources=("https://twitter.com/poteto/status/2111133080526495985",)
        )
        is None
    )
    assert _reason(shot, sources=("https://example.com/a",)) == "cover_source_invalid"
    assert _reason(_asset(kind="screenshot"), sources=(_X,)) == "cover_source_invalid"


def test_parse_asset_id() -> None:
    value = uuid4()
    assert parse_asset_id(f"  {value} ") == value
    assert parse_asset_id("nope") is None


@pytest.mark.parametrize(
    ("url", "credit"),
    [
        (_X, "@poteto · X"),
        ("https://twitter.com/Poteto/status/1/", "@Poteto · X"),
        ("https://www.theverge.com/a", "theverge.com"),
        ("https://openai.com/index/x", "openai.com"),
        (None, ""),
        ("", ""),
    ],
)
def test_cover_credit(url: str | None, credit: str) -> None:
    assert cover_credit(url) == credit


def test_slide_cover_for_credits_screenshots_only() -> None:
    shot = slide_cover_for(_asset(kind="screenshot", source_url=_X))
    assert shot.credit == "@poteto · X"
    assert shot.is_screenshot
    image = _asset()
    ai = slide_cover_for(image)
    assert (ai.asset_id, ai.kind, ai.staged_path, ai.credit) == (
        image.creator_asset_id,
        "ai_image",
        "assets/creators/abc.webp",
        "",
    )
    assert not ai.is_screenshot


def test_slide_cover_row_round_trip_and_malformed_rows() -> None:
    cover = SlideCover(
        asset_id=uuid4(), kind="screenshot", staged_path="a/b.webp", credit="c"
    )
    assert slide_cover_from_row(slide_cover_row(cover)) == cover
    assert slide_cover_row(None) is None
    row = cover.to_row()
    assert slide_cover_from_row({**row, "credit": 3}) == SlideCover(
        asset_id=cover.asset_id, kind="screenshot", staged_path="a/b.webp"
    )
    assert slide_cover_from_row(None) is None
    assert slide_cover_from_row({**row, "kind": "gif"}) is None
    assert slide_cover_from_row({**row, "asset_id": "nope"}) is None
    assert slide_cover_from_row({**row, "asset_id": 7}) is None
    assert slide_cover_from_row({**row, "staged_path": None}) is None


_OFFER = CoverOffer(
    kind="ai_image", credit="", chosen=False, pov=True, photo_path="/tmp/c.webp"
)


def _offer(**overrides: object) -> CoverOffer:
    return replace(_OFFER, **overrides)


def test_cover_callbacks_parse() -> None:
    on = parse_cover_callback(f"ap:cv:{_RUN}")
    off = parse_cover_callback(f"ap:cvoff:{_RUN}")
    assert on is not None and on.use_cover and on.run_id == _RUN
    assert off is not None and not off.use_cover
    assert parse_cover_callback(f"ap:cvx:{_RUN}") is None
    assert parse_cover_callback("ap:cv:nope") is None


@pytest.mark.parametrize(
    ("offer", "text", "prefix"),
    [
        (_offer(), "🖼️ Usar capa do Grok", "ap:cv:"),
        (_offer(chosen=True), "📸 Usar minha foto", "ap:cvoff:"),
        (_offer(chosen=True, pov=False), "↩️ Usar capa padrão", "ap:cvoff:"),
    ],
)
def test_cover_button(offer: CoverOffer, text: str, prefix: str) -> None:
    button = cover_button(_RUN, offer)
    assert button.text == text
    assert button.callback_data == f"{prefix}{_RUN}"
    assert len(button.callback_data.encode()) <= 64


def test_with_cover_row_appends_a_last_row_only_with_an_offer() -> None:
    keyboard = InlineKeyboard(rows=((InlineButton(text="a", callback_data="b"),),))
    assert with_cover_row(keyboard, _RUN, None) == keyboard
    rows = with_cover_row(keyboard, _RUN, _offer()).rows
    assert len(rows) == 2
    assert rows[-1][0].text == "🖼️ Usar capa do Grok"


def test_thesis_keyboard_offers_the_cover() -> None:
    assert len(thesis_keyboard(_RUN).rows) == 1
    rows = thesis_keyboard(_RUN, _offer()).rows
    assert len(rows) == 2
    assert rows[1][0].callback_data == f"ap:cv:{_RUN}"


def test_caption_and_notice_key_and_chosen_as() -> None:
    assert "imagem gerada" in cover_caption(_offer())
    assert "@poteto · X" in cover_caption(
        _offer(kind="screenshot", credit="@poteto · X")
    )
    assert cover_notice_key("thesis", _RUN) == f"cover:thesis:{_RUN}"
    flipped = chosen_as(_offer(), chosen=True)
    assert flipped.chosen
    assert flipped.photo_path == "/tmp/c.webp"
