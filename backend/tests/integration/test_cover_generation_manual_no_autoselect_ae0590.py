"""A manual Grok cover generation is never auto-selected for slide 1.

Feature: Use the autopilot's generated cover on slide 1
(tests/features/autopilot_cover_autoselect_ae0590.feature). The real app
over an in-memory SQLite database with a fake image bridge editor; the
carousel is paused at a gate, where an autopilot cover would be selected.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from httpx import AsyncClient

from rag_backend.infrastructure.database.config import get_session_maker
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from tests.integration.cover_generation_support import (
    RED,
    FakeEditor,
    generate,
    generation_rows,
    install_fake_editor,
    project,
    set_project,
)
from tests.integration.hook_photo_support import upload_photo


@pytest.fixture(autouse=True)
def _fresh_limiter() -> Iterator[None]:
    from rag_backend.api.middleware.rate_limiting import limiter

    limiter.reset()
    yield
    limiter.reset()


@pytest.mark.integration
async def test_manual_generation_is_only_a_picker_option(
    client: AsyncClient, asset_dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The publish-step generation succeeds and slide 1 is unchanged."""
    # Scenario: A manual generation is never auto-selected
    editor: FakeEditor = install_fake_editor(monkeypatch)
    photo = await upload_photo(client, RED)
    project_id = await project(client, photo["id"])
    await set_project(project_id, status="drafting", phase_status="awaiting_human")

    await generate(client, project_id, [photo["id"]])

    rows = await generation_rows(project_id)
    assert [row["status"] for row in rows] == ["succeeded"]
    assert len(editor.jobs) == 1
    async with get_session_maker()() as session:
        model = await session.get(CarouselProjectModel, project_id)
        assert model is not None
        assert model.slide_cover is None
        assert model.hook_asset_id == photo["id"]
        assert model.lock_version == 4
