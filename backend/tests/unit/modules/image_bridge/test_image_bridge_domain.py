"""Pure domain rules of the image bridge.

Gherkin: tests/features/image_bridge.feature
"""

from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import pytest

from rag_backend.modules.image_bridge.constants import (
    ERROR_CODE_LENGTH,
    ERROR_CODE_UNKNOWN,
    ERROR_MESSAGE_MAX_CHARS,
    MAX_B64_CHARS,
    MAX_IMAGE_BYTES,
)
from rag_backend.modules.image_bridge.domain.callback_body import (
    CallbackError,
    CallbackImage,
    decode_image_b64,
    parse_callback,
)
from rag_backend.modules.image_bridge.domain.exceptions import (
    InvalidCallbackImageError,
    MalformedCallbackError,
)
from rag_backend.modules.image_bridge.domain.models import (
    ImageSize,
    WebhookRequest,
    job_metadata,
)
from rag_backend.modules.image_bridge.domain.tokens import (
    new_callback_token,
    token_digest,
    token_matches,
)
from tests.unit.modules.image_bridge.support import T0, b64, pending_job


# Scenario: Grok Bot returns an image (the ImagesResponse shape)
def test_images_response_yields_the_first_b64_image() -> None:
    parsed = parse_callback({"data": [{"b64_json": "QUJD", "revised_prompt": "x"}]})
    assert parsed == CallbackImage(b64_json="QUJD")


# Scenario: Grok Bot refuses (the OpenAI error shape)
def test_error_body_yields_code_and_message() -> None:
    parsed = parse_callback({
        "error": {
            "type": "image_generation_error",
            "code": "content_policy",
            "message": " refused ",
        }
    })
    assert parsed == CallbackError(code="content_policy", message="refused")


def test_error_without_code_falls_back_to_type_then_unknown() -> None:
    by_type = parse_callback({"error": {"type": "server_error"}})
    assert by_type == CallbackError(code="server_error", message="")
    unknown = parse_callback({"error": {"code": 7, "message": None}})
    assert unknown == CallbackError(code=ERROR_CODE_UNKNOWN, message="")


def test_error_fields_are_bounded() -> None:
    parsed = parse_callback({"error": {"code": "c" * 500, "message": "m" * 5000}})
    assert isinstance(parsed, CallbackError)
    assert len(parsed.code) == ERROR_CODE_LENGTH
    assert len(parsed.message) == ERROR_MESSAGE_MAX_CHARS


# Scenario: Malformed body
@pytest.mark.parametrize(
    "payload",
    [
        [],
        "text",
        None,
        {},
        {"data": []},
        {"data": "x"},
        {"data": [1]},
        {"data": [{"url": "https://evil.example/x.png"}]},
        {"data": [{"b64_json": "   "}]},
        {"data": [{"b64_json": 5}]},
        {"error": "refused"},
        {"error": None},
    ],
)
def test_malformed_bodies_are_rejected(payload: object) -> None:
    with pytest.raises(MalformedCallbackError):
        parse_callback(payload)


def test_url_responses_are_never_followed() -> None:
    """Only b64_json is read: a url entry is malformed, not fetched."""
    with pytest.raises(MalformedCallbackError):
        parse_callback({"data": [{"url": "http://169.254.169.254/"}]})


def test_decode_accepts_whitespace_wrapped_base64() -> None:
    encoded = b64(b"image-bytes")
    wrapped = encoded[:4] + "\n" + encoded[4:] + "\n"
    assert decode_image_b64(wrapped) == b"image-bytes"


# Scenario: Invalid image
@pytest.mark.parametrize("value", ["not base64!!", "QUJ", "@@@@"])
def test_decode_rejects_invalid_base64(value: str) -> None:
    with pytest.raises(InvalidCallbackImageError):
        decode_image_b64(value)


def test_decode_rejects_oversized_text_before_decoding() -> None:
    with pytest.raises(InvalidCallbackImageError):
        decode_image_b64("A" * (MAX_B64_CHARS + 4))


def test_decode_rejects_bytes_over_the_limit() -> None:
    encoded = b64(b"\0" * (MAX_IMAGE_BYTES + 1))
    assert len(encoded) <= MAX_B64_CHARS + 4
    with pytest.raises(InvalidCallbackImageError):
        decode_image_b64(encoded)


def test_decode_accepts_exactly_the_limit() -> None:
    assert len(decode_image_b64(b64(b"\0" * MAX_IMAGE_BYTES))) == MAX_IMAGE_BYTES


# Scenario: Tokens are never stored or logged in clear
def test_tokens_are_random_url_safe_and_43_chars() -> None:
    first, second = new_callback_token(), new_callback_token()
    assert first != second
    assert len(first) == 43
    assert token_digest(first) != first
    assert len(token_digest(first)) == 64


# Scenario: Wrong token / Missing token / Unknown job looks the same
@pytest.mark.parametrize(
    ("presented", "stored", "expected"),
    [
        ("tok", token_digest("tok"), True),
        ("other", token_digest("tok"), False),
        (None, token_digest("tok"), False),
        ("", token_digest(""), False),
        ("tok", None, False),
        ("", None, False),
    ],
)
def test_token_matches(
    presented: str | None, stored: str | None, expected: bool
) -> None:
    assert token_matches(presented, stored) is expected


def test_image_size_parses_width_and_height() -> None:
    assert ImageSize.parse("1536x1024") == ImageSize(width=1536, height=1024)
    assert ImageSize.parse(" 512X768 ") == ImageSize(width=512, height=768)


@pytest.mark.parametrize("text", ["", "1536", "1536x", "x1024", "axb", "1536*1024"])
def test_image_size_rejects_other_text(text: str) -> None:
    with pytest.raises(ValueError, match="WIDTHxHEIGHT"):
        ImageSize.parse(text)


def test_job_overdue_at_and_after_the_deadline() -> None:
    job = pending_job()
    assert not job.is_overdue(job.expires_at - timedelta(seconds=1))
    assert job.is_overdue(job.expires_at)


# Scenario: Grok Bot returns an image (webhook payload, contract 2.1)
def test_webhook_payload_matches_the_contract() -> None:
    job_id = uuid4()
    request = WebhookRequest(
        job_id=job_id,
        model="gpt-image-2",
        prompt="a slide",
        size="1536x1024",
        callback_url="https://h/api/v1/image-bridge/jobs/x/result",
        callback_token="tok",
        expires_at=T0,
        metadata=job_metadata("p-1"),
    )
    assert request.payload() == {
        "job_id": str(job_id),
        "model": "gpt-image-2",
        "prompt": "a slide",
        "size": "1536x1024",
        "n": 1,
        "response_format": "b64_json",
        "callback_url": "https://h/api/v1/image-bridge/jobs/x/result",
        "callback_token": "tok",
        "expires_at": "2026-10-15T20:00:00Z",
        "metadata": {"content_type": "carousel", "project_id": "p-1"},
    }


def test_metadata_omits_an_unknown_project() -> None:
    assert job_metadata(None) == {"content_type": "carousel"}
    assert job_metadata("") == {"content_type": "carousel"}


def test_decoded_size_is_checked_exactly(monkeypatch: pytest.MonkeyPatch) -> None:
    """The base64 length bound is coarse; the decoded byte count is exact."""
    from rag_backend.modules.image_bridge.domain import callback_body

    monkeypatch.setattr(callback_body, "MAX_IMAGE_BYTES", 10)
    assert decode_image_b64(b64(b"0123456789")) == b"0123456789"
    with pytest.raises(InvalidCallbackImageError):
        decode_image_b64(b64(b"0123456789A"))


async def test_system_clock_is_utc_and_sleeps() -> None:
    from rag_backend.modules.image_bridge.infrastructure.clock import SystemClock

    clock = SystemClock()
    assert clock.now().utcoffset() == timedelta(0)
    await clock.sleep(0)
