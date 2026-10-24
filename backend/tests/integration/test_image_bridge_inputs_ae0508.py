"""``GET /api/v1/image-bridge/jobs/{job_id}/inputs/{n}``: the linked photos.

Feature: Generate a slide-1 cover from library photos with Grok
(tests/features/cover_generation_ae0508.feature). The real app over the
in-memory database; photos are generated. Every refusal is a 404.
"""

from __future__ import annotations

import io
import re
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from PIL import Image

from rag_backend.domain.models import UserRole
from rag_backend.infrastructure.database.config import get_session_maker
from rag_backend.infrastructure.database.models import CarouselCoverGenerationModel
from rag_backend.modules.image_bridge.domain.models import (
    ImageBridgeJob,
    ImageBridgeJobStatus,
    JobSuccess,
)
from rag_backend.modules.image_bridge.domain.tokens import token_digest
from rag_backend.modules.image_bridge.infrastructure.repository import (
    SqlImageBridgeJobRepository,
)
from tests.integration.conftest import auth_headers_for, create_test_user
from tests.integration.cover_generation_support import BLUE, RED, project
from tests.integration.hook_photo_support import upload_photo

_TOKEN = "callback-token-for-the-inputs-route-0123456789"
_HEADER = "X-Image-Bridge-Token"
_REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(autouse=True)
def _fresh_limiter() -> Iterator[None]:
    from rag_backend.api.middleware.rate_limiting import limiter

    limiter.reset()
    yield
    limiter.reset()


async def _bridge_job(job_id: UUID, *, expires_in: timedelta) -> None:
    now = datetime.now(UTC)
    await SqlImageBridgeJobRepository(get_session_maker).create(
        ImageBridgeJob(
            id=job_id,
            status=ImageBridgeJobStatus.PENDING,
            size="1024x1536",
            token_sha256=token_digest(_TOKEN),
            created_at=now,
            expires_at=now + expires_in,
        )
    )


async def _generation(
    project_id: str, photo_ids: list[str], status: str = "pending"
) -> UUID:
    from rag_backend.infrastructure.database.models.carousel import (
        CarouselProjectModel,
    )

    generation_id = uuid4()
    async with get_session_maker()() as session:
        owner = (await session.get(CarouselProjectModel, project_id)).owner_id
        session.add(
            CarouselCoverGenerationModel(
                id=str(generation_id),
                project_id=project_id,
                owner_id=owner,
                status=status,
                prompt_sha256="0" * 64,
                photo_count=len(photo_ids),
                photo_ids=photo_ids,
                model="m",
                cost_usd=0.0,
                created_at=datetime.now(UTC),
            )
        )
        await session.commit()
    return generation_id


async def _live_job(client: AsyncClient) -> tuple[UUID, list[str]]:
    first = await upload_photo(client, RED)
    second = await upload_photo(client, BLUE)
    project_id = await project(client, first["id"])
    photo_ids = [str(first["id"]), str(second["id"])]
    job_id = await _generation(project_id, photo_ids)
    await _bridge_job(job_id, expires_in=timedelta(minutes=10))
    return job_id, photo_ids


def _url(job_id: object, index: object) -> str:
    return f"/api/v1/image-bridge/jobs/{job_id}/inputs/{index}"


@pytest.mark.integration
class TestInputs:
    async def test_the_job_token_fetches_each_photo_as_png(
        self, client: AsyncClient, asset_dirs: Path
    ) -> None:
        """Scenario: A confirmed generation links the photos and stores a private cover."""
        job_id, _photos = await _live_job(client)

        for index in (0, 1):
            response = await client.get(
                _url(job_id, index),
                headers={
                    _HEADER: _TOKEN,
                    "Authorization": "",
                    "Origin": "https://elsewhere.example",
                },
            )

            assert response.status_code == 200, response.text
            assert response.headers["content-type"] == "image/png"
            assert response.headers["cache-control"] == "no-store, private"
            assert "access-control-allow-origin" not in response.headers
            with Image.open(io.BytesIO(response.content)) as photo:
                assert photo.format == "PNG"
                assert max(photo.size) <= 1024
                assert not photo.getexif()

    @pytest.mark.parametrize("token", [None, "", "wrong-token"])
    async def test_a_missing_or_wrong_token_is_404(
        self, client: AsyncClient, asset_dirs: Path, token: str | None
    ) -> None:
        """Scenario: The linked photos are served only to the job's own token."""
        job_id, _photos = await _live_job(client)
        headers = {} if token is None else {_HEADER: token}

        response = await client.get(_url(job_id, 0), headers=headers)

        assert response.status_code == 404

    async def test_an_expired_job_is_404(
        self, client: AsyncClient, asset_dirs: Path
    ) -> None:
        """Scenario: The linked photos are served only to the job's own token."""
        first = await upload_photo(client, RED)
        project_id = await project(client, first["id"])
        job_id = await _generation(project_id, [str(first["id"])])
        await _bridge_job(job_id, expires_in=timedelta(seconds=-1))

        response = await client.get(_url(job_id, 0), headers={_HEADER: _TOKEN})

        assert response.status_code == 404

    async def test_a_settled_job_is_404(
        self, client: AsyncClient, asset_dirs: Path
    ) -> None:
        """Scenario: The linked photos are served only to the job's own token."""
        job_id, _photos = await _live_job(client)
        repo = SqlImageBridgeJobRepository(get_session_maker)
        await repo.succeed(JobSuccess(job_id, b"image", datetime.now(UTC)))

        response = await client.get(_url(job_id, 0), headers={_HEADER: _TOKEN})

        assert response.status_code == 404

    async def test_a_settled_generation_is_404(
        self, client: AsyncClient, asset_dirs: Path
    ) -> None:
        """Scenario: The linked photos are served only to the job's own token."""
        first = await upload_photo(client, RED)
        project_id = await project(client, first["id"])
        job_id = await _generation(project_id, [str(first["id"])], status="failed")
        await _bridge_job(job_id, expires_in=timedelta(minutes=10))

        response = await client.get(_url(job_id, 0), headers={_HEADER: _TOKEN})

        assert response.status_code == 404

    @pytest.mark.parametrize("index", ["2", "-1", "x", "10"])
    async def test_an_index_out_of_range_is_404(
        self, client: AsyncClient, asset_dirs: Path, index: str
    ) -> None:
        """Scenario: The linked photos are served only to the job's own token."""
        job_id, _photos = await _live_job(client)

        response = await client.get(_url(job_id, index), headers={_HEADER: _TOKEN})

        assert response.status_code == 404

    async def test_an_unknown_or_malformed_job_is_404(
        self, client: AsyncClient, asset_dirs: Path
    ) -> None:
        """Scenario: The linked photos are served only to the job's own token."""
        for job_id in (uuid4(), "not-a-uuid"):
            response = await client.get(_url(job_id, 0), headers={_HEADER: _TOKEN})
            assert response.status_code == 404

    async def test_another_owners_photo_is_never_served(
        self, client: AsyncClient, asset_dirs: Path
    ) -> None:
        """Scenario: Another owner's photo cannot be sent."""
        first = await upload_photo(client, RED)
        project_id = await project(client, first["id"])
        other = await create_test_user(f"{uuid4().hex}@x.test", UserRole.EDITOR)
        theirs = await upload_photo(client, BLUE, headers=auth_headers_for(other))
        job_id = await _generation(project_id, [str(theirs["id"])])
        await _bridge_job(job_id, expires_in=timedelta(minutes=10))

        response = await client.get(_url(job_id, 0), headers={_HEADER: _TOKEN})

        assert response.status_code == 404


@pytest.mark.parametrize("conf", ["nginx/nginx.conf", "nginx/nginx.conf.ssl"])
def test_nginx_proxies_the_inputs_route(conf: str) -> None:
    """Scenario: The linked photos are served only to the job's own token."""
    text = (_REPO_ROOT / conf).read_text(encoding="utf-8")
    block = re.search(r"location /api/v1/image-bridge/ \{(.*?)\n\s*\}", text, re.S)

    assert block is not None
    assert "proxy_pass http://backend/api/v1/image-bridge/;" in block.group(1)
    assert "limit_except" not in block.group(1)


@pytest.mark.integration
async def test_other_routes_keep_their_cors_headers(
    client: AsyncClient, asset_dirs: Path
) -> None:
    """Scenario: The linked photos are served only to the job's own token."""
    response = await client.get(
        "/api/carousels/creator-assets", headers={"Origin": "https://elsewhere.example"}
    )

    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
