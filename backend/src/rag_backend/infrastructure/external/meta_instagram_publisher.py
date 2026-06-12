"""Meta Instagram Graph API publisher.

Ships a 4-step carousel publish against the Instagram Graph API:

    1. Create one item container per image (`is_carousel_item=true`).
    2. Create a parent container with `media_type=CAROUSEL` referencing
       the item children.
    3. Poll the parent container's `status_code` until FINISHED.
    4. Call `media_publish` with the parent creation_id.

The access token + IG user ID come from settings. Images must already
be reachable at the URLs passed in (Meta fetches them server-side).

Scope: Standard Access for a solo-dev's own Instagram Business account
— no Business Verification required, no Tech Provider status. If the
token is missing we surface a clear error instead of calling the API.
"""

from __future__ import annotations

import asyncio

import httpx

from rag_backend.domain.constants import COOKIE_ACCESS_TOKEN
from rag_backend.domain.constants.instagram_publish import (
    ERR_INSTAGRAM_API_NO_ID,
    ERR_INSTAGRAM_API_REQUEST_FAILED,
    ERR_INSTAGRAM_CONTAINER_FAILED,
    ERR_INSTAGRAM_CONTAINER_TIMEOUT,
    ERR_INSTAGRAM_CREDENTIALS_NOT_CONFIGURED,
    ERR_INSTAGRAM_IMAGE_COUNT_INVALID,
)
from rag_backend.domain.constants.retry import META_MAX_ATTEMPTS
from rag_backend.domain.protocols import PublishResult, SocialPublisher
from rag_backend.domain.retry import retry_async
from rag_backend.infrastructure.logging import get_logger

logger = get_logger()

_GRAPH_BASE = "https://graph.facebook.com/v23.0"
_MAX_POLL_ATTEMPTS = 30
_POLL_INTERVAL_SECONDS = 2.0
_CONTAINER_FINISHED = "FINISHED"
_CONTAINER_ERROR = "ERROR"
_CONTAINER_EXPIRED = "EXPIRED"
_MAX_CAROUSEL_ITEMS = 10
MIN_IMAGE_BATCH = 2


class MetaInstagramPublisher(SocialPublisher):
    """Instagram Graph API (`/v23.0`) implementation."""

    def __init__(
        self,
        access_token: str,
        ig_user_id: str,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._token = access_token
        self._ig_user_id = ig_user_id
        self._client = http_client or httpx.AsyncClient(timeout=30.0)
        self._owns_client = http_client is None

    async def publish_instagram(
        self,
        caption: str,
        image_urls: list[str],
    ) -> PublishResult:
        try:
            self._ensure_configured()
            self._validate_images(image_urls)
            item_ids = await self._create_item_containers(image_urls)
            parent_id = await self._create_parent_container(item_ids, caption)
            await self._wait_for_finished(parent_id)
            post_id = await self._publish(parent_id)
        except RuntimeError as exc:
            return PublishResult(status="failed", error_message=str(exc))
        except httpx.HTTPError:
            logger.exception("instagram_publish_http_error")
            return PublishResult(
                status="failed",
                error_message=ERR_INSTAGRAM_API_REQUEST_FAILED,
            )
        return PublishResult(status="published", post_id=post_id)

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    def _ensure_configured(self) -> None:
        if not self._token or not self._ig_user_id:
            raise RuntimeError(ERR_INSTAGRAM_CREDENTIALS_NOT_CONFIGURED)

    @staticmethod
    def _validate_images(image_urls: list[str]) -> None:
        if len(image_urls) < MIN_IMAGE_BATCH or len(image_urls) > _MAX_CAROUSEL_ITEMS:
            raise RuntimeError(ERR_INSTAGRAM_IMAGE_COUNT_INVALID)

    async def _create_item_containers(self, image_urls: list[str]) -> list[str]:
        """Step 1: one container per slide."""
        results: list[str] = []
        for url in image_urls:
            payload = {
                "image_url": url,
                "is_carousel_item": "true",
                COOKIE_ACCESS_TOKEN: self._token,
            }
            container_id = await self._post_and_extract_id(
                f"{_GRAPH_BASE}/{self._ig_user_id}/media", payload
            )
            results.append(container_id)
        return results

    async def _create_parent_container(self, item_ids: list[str], caption: str) -> str:
        """Step 2: parent CAROUSEL container referencing the children."""
        payload = {
            "media_type": "CAROUSEL",
            "children": ",".join(item_ids),
            "caption": caption,
            COOKIE_ACCESS_TOKEN: self._token,
        }
        return await self._post_and_extract_id(
            f"{_GRAPH_BASE}/{self._ig_user_id}/media", payload
        )

    async def _wait_for_finished(self, container_id: str) -> None:
        """Step 3: poll status_code until FINISHED or ERROR."""
        for _attempt in range(_MAX_POLL_ATTEMPTS):
            async for retry_attempt in retry_async(attempts=META_MAX_ATTEMPTS):
                with retry_attempt:
                    response = await self._client.get(
                        f"{_GRAPH_BASE}/{container_id}",
                        params={
                            "fields": "status_code",
                            COOKIE_ACCESS_TOKEN: self._token,
                        },
                    )
                    response.raise_for_status()
            status = response.json().get("status_code", "")
            if status == _CONTAINER_FINISHED:
                return
            if status in {_CONTAINER_ERROR, _CONTAINER_EXPIRED}:
                raise RuntimeError(ERR_INSTAGRAM_CONTAINER_FAILED)
            await asyncio.sleep(_POLL_INTERVAL_SECONDS)
        raise RuntimeError(ERR_INSTAGRAM_CONTAINER_TIMEOUT)

    async def _publish(self, parent_id: str) -> str:
        """Step 4: move the parent container to the published feed."""
        payload = {
            "creation_id": parent_id,
            COOKIE_ACCESS_TOKEN: self._token,
        }
        return await self._post_and_extract_id(
            f"{_GRAPH_BASE}/{self._ig_user_id}/media_publish", payload
        )

    async def _post_and_extract_id(self, url: str, payload: dict[str, str]) -> str:
        async for attempt in retry_async(attempts=META_MAX_ATTEMPTS):
            with attempt:
                response = await self._client.post(url, data=payload)
                response.raise_for_status()
        data = response.json()
        returned_id = data.get("id")
        if not returned_id:
            logger.error("instagram_api_missing_id", url=url, data=data)
            raise RuntimeError(ERR_INSTAGRAM_API_NO_ID)
        return str(returned_id)
