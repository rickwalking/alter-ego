"""Music suggestion and the published notice copy.

Gherkin: tests/features/autopilot_story_and_music.feature
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from rag_backend.modules.autopilot.constants import NOTICE_PUBLISHED
from rag_backend.modules.autopilot.domain.messages import StatusCopy, status_text
from rag_backend.modules.autopilot.domain.music import music_style_for
from rag_backend.modules.autopilot.domain.publish import PostExtras, PublishNotice
from rag_backend.modules.autopilot.domain.published_copy import (
    extras_payload,
    post_extras_of,
    published_text,
)
from rag_backend.modules.autopilot.infrastructure.publish_notifier import _record
from rag_backend.modules.autopilot.notify_constants import KIND_PUBLISHED

_LINK = "https://www.instagram.com/p/abc/"
_SYNTHWAVE = "lo-fi eletrônico / synthwave"


def _extras(status: str, error: str | None = None) -> PostExtras:
    return PostExtras(story_status=status, story_error=error, music_style=_SYNTHWAVE)


@pytest.mark.unit
class TestMusicStyle:
    """Scenario Outline: The music style follows the niche and image style."""

    @pytest.mark.parametrize(
        ("niche", "style", "music"),
        [
            ("AI", "neo_anime", _SYNTHWAVE),
            ("Inteligência Artificial", "neo_anime", _SYNTHWAVE),
            ("Cibersegurança", "neo_anime", "dark synth"),
            ("Ciberseguranca", "neo_anime", "dark synth"),
            ("Robótica", "neo_anime", "cinematic electronic"),
            ("Culinária", "neo_anime", "lo-fi beats"),
            ("Culinária", "comic_neon", _SYNTHWAVE),
            ("Culinária", "cinematic", "cinematic electronic"),
            ("", "", "lo-fi beats"),
        ],
    )
    def test_style(self, niche: str, style: str, music: str) -> None:
        assert music_style_for(niche, style) == music

    def test_niche_wins_over_the_image_style(self) -> None:
        assert music_style_for("Cybersecurity for devs", "comic_neon") == "dark synth"

    def test_ai_inside_a_word_does_not_match(self) -> None:
        """ "Culinária" ends in "ia" but is one word, not the word "IA"."""
        assert music_style_for("Culinária", "neo_anime") == "lo-fi beats"


@pytest.mark.unit
class TestPublishedText:
    """Scenario: The published notice carries the permalink, the Story, and the nudge."""

    def test_published_story_and_music(self) -> None:
        text = published_text(_LINK, _extras("published"))
        assert text.splitlines() == [
            f"✅ Publicado: {_LINK}",
            "\U0001f4f2 Story: publicado",
            f"\U0001f3b5 Adicione uma música pelo app (20s): sugestão: {_SYNTHWAVE}",
        ]

    def test_failed_story_shows_the_reason(self) -> None:
        text = published_text(_LINK, _extras("failed", "36003"))
        assert "\U0001f4f2 Story falhou: 36003" in text.splitlines()

    def test_no_extras_is_only_the_post_line(self) -> None:
        assert published_text(_LINK, None) == f"✅ Publicado: {_LINK}"

    def test_no_permalink(self) -> None:
        assert published_text("", None) == "✅ Publicado"

    def test_unknown_story_status_has_no_story_line(self) -> None:
        extras = PostExtras(story_status="other", story_error=None, music_style="")
        assert published_text(_LINK, extras) == f"✅ Publicado: {_LINK}"

    def test_status_text_renders_the_extras(self) -> None:
        copy = StatusCopy(
            reason="",
            link="",
            permalink=_LINK,
            days_remaining=None,
            extras=_extras("published"),
        )
        text = status_text(KIND_PUBLISHED, copy)
        assert "\U0001f4f2 Story: publicado" in text
        assert _LINK in text


@pytest.mark.unit
class TestExtrasPayload:
    """The outbox payload round-trips the extras."""

    def test_round_trip(self) -> None:
        extras = _extras("failed", "story_image_missing")
        assert post_extras_of(extras_payload(extras)) == extras

    def test_no_extras_writes_no_keys(self) -> None:
        assert extras_payload(None) == {}
        assert post_extras_of({}) is None

    def test_non_string_error_is_dropped(self) -> None:
        payload = {"story_status": "published", "music_style": "x", "story_error": 3}
        parsed = post_extras_of(payload)
        assert parsed is not None and parsed.story_error is None

    def test_notifier_writes_the_extras_on_the_outbox_row(self) -> None:
        notice = PublishNotice(
            run_id=uuid4(),
            outcome=NOTICE_PUBLISHED,
            permalink=_LINK,
            error_code=None,
            offer_retry=False,
            extras=_extras("published"),
        )
        payload = _record(notice).payload
        assert payload["story_status"] == "published"
        assert payload["music_style"] == _SYNTHWAVE
        assert payload["story_error"] is None
