"""Slide-1 photo helpers for POV integration tests (PR #106 review).

A POV create now needs ``hook_asset_id`` (an uploaded, readable library
photo), so every POV test uploads one first. ``asset_dirs`` points the creator
asset and output folders at ``tmp_path``.
"""

from __future__ import annotations

from io import BytesIO

from httpx import AsyncClient

HOOK_ROLE = "hook"


def png(color: tuple[int, int, int, int]) -> bytes:
    """A tiny RGBA PNG; a distinct colour gives a distinct stored asset."""
    from PIL import Image

    buffer = BytesIO()
    Image.new("RGBA", (16, 20), color).save(buffer, format="PNG")
    return buffer.getvalue()


async def upload_photo(
    client: AsyncClient,
    color: tuple[int, int, int, int] = (9, 9, 9, 0),
    headers: dict[str, str] | None = None,
) -> dict[str, object]:
    """Upload one hook photo to the caller's library and return its body."""
    response = await client.post(
        "/api/carousels/creator-assets",
        files={"file": ("me.png", png(color), "image/png")},
        data={"role": HOOK_ROLE, "pose_tag": "Apontando"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert isinstance(body, dict)
    return body


async def hook_photo_id(client: AsyncClient) -> str:
    """The id of a freshly uploaded hook photo."""
    return str((await upload_photo(client))["id"])
