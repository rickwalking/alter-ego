"""Meta Instagram Graph API publisher.

Carousel publish is four steps against the configured Graph host:

1. One item container per image (``is_carousel_item``).
2. A parent ``CAROUSEL`` container.
3. Poll ``status_code`` until ``FINISHED``.
4. ``media_publish`` with that container as ``creation_id``.

A container that already reports ``PUBLISHED`` (a crash after step 4) is not
published again: its media id is recovered from the account's recent media.

``META_IG_GRAPH_BASE`` selects the host. The default is Instagram Login
(``graph.instagram.com``). Page tokens can select ``graph.facebook.com``.
The access token comes from an ``InstagramTokenProvider``. AE-0358's
encrypted store is the production provider.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx

from rag_backend.domain.constants import COOKIE_ACCESS_TOKEN
from rag_backend.domain.constants.instagram_publish import (
    CONTAINER_CLOCK_SKEW_SECONDS,
    CONTAINER_STATUS_ERROR,
    CONTAINER_STATUS_EXPIRED,
    CONTAINER_STATUS_FINISHED,
    CONTAINER_STATUS_PUBLISHED,
    ERR_INSTAGRAM_API_NO_ID,
    ERR_INSTAGRAM_API_REQUEST_FAILED,
    ERR_INSTAGRAM_CONTAINER_FAILED,
    ERR_INSTAGRAM_CONTAINER_TIMEOUT,
    ERR_INSTAGRAM_CREDENTIALS_NOT_CONFIGURED,
    ERR_INSTAGRAM_IMAGE_COUNT_INVALID,
    ERR_INSTAGRAM_PUBLISHED_MEDIA_UNKNOWN,
    ERR_INSTAGRAM_QUOTA_UNREADABLE,
    FIELD_CAPTION,
    FIELD_CHILDREN,
    FIELD_CREATION_ID,
    FIELD_FIELDS,
    FIELD_ID,
    FIELD_IMAGE_URL,
    FIELD_IS_CAROUSEL_ITEM,
    FIELD_LIMIT,
    FIELD_MEDIA_TYPE,
    FIELD_PERMALINK,
    FIELD_STATUS_CODE,
    FIELD_TIMESTAMP,
    GRAPH_PATH_MEDIA,
    GRAPH_PATH_MEDIA_NODE,
    GRAPH_PATH_MEDIA_PUBLISH,
    GRAPH_PATH_PUBLISHING_LIMIT,
    GRAPH_REQUEST_DEADLINE_SECONDS,
    HTTP_GET,
    HTTP_POST,
    MAX_INSTAGRAM_CAROUSEL_ITEMS,
    MEDIA_TYPE_CAROUSEL,
    MIN_INSTAGRAM_CAROUSEL_ITEMS,
    PUBLISH_RESULT_FAILED,
    PUBLISH_RESULT_PUBLISHED,
    RECENT_MEDIA_LIMIT,
    VALUE_TRUE,
)
from rag_backend.domain.constants.retry import (
    META_MAX_ATTEMPTS,
    META_POLL_INTERVAL_SECONDS,
    META_POLL_MAX_ATTEMPTS,
)
from rag_backend.domain.protocols.instagram_token import InstagramTokenProvider
from rag_backend.domain.protocols.social import PublishResult
from rag_backend.infrastructure.external.instagram_graph_error import (
    InstagramGraphError,
)
from rag_backend.infrastructure.external.instagram_graph_payloads import (
    error_from,
    json_dict,
    quota_remaining,
    recent_carousel_id,
)
from rag_backend.infrastructure.logging import get_logger

logger = get_logger()

# Tests patch these to skip the real poll sleep and to shorten the deadline.
_POLL_INTERVAL_SECONDS = META_POLL_INTERVAL_SECONDS
_REQUEST_DEADLINE_SECONDS: float = GRAPH_REQUEST_DEADLINE_SECONDS

_CLIENT_MESSAGES = frozenset({
    ERR_INSTAGRAM_CONTAINER_FAILED,
    ERR_INSTAGRAM_CONTAINER_TIMEOUT,
    ERR_INSTAGRAM_API_NO_ID,
    ERR_INSTAGRAM_QUOTA_UNREADABLE,
    ERR_INSTAGRAM_PUBLISHED_MEDIA_UNKNOWN,
})
_TERMINAL_OK = frozenset({CONTAINER_STATUS_FINISHED, CONTAINER_STATUS_PUBLISHED})
_RECENT_MEDIA_FIELDS = ",".join((FIELD_ID, FIELD_MEDIA_TYPE, FIELD_TIMESTAMP))


@dataclass(frozen=True, kw_only=True)
class MetaInstagramPublisherConfig:
    """Host, user id, and token source for one publisher instance."""

    ig_user_id: str
    graph_base: str
    token_provider: InstagramTokenProvider


@dataclass(frozen=True, kw_only=True)
class _GraphCall:
    """One Graph request. The token is attached at send time."""

    method: str
    path: str
    form: dict[str, str] | None = None
    query: dict[str, str] | None = None


class MetaInstagramPublisher:
    """Instagram Graph API publisher with split create / poll / publish steps."""

    def __init__(
        self,
        config: MetaInstagramPublisherConfig,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._config = config
        self._client = http_client or httpx.AsyncClient(timeout=30.0)
        self._owns_client = http_client is None

    async def publish_instagram(
        self,
        caption: str,
        image_urls: list[str],
    ) -> PublishResult:
        """Run all four steps. Failures become a ``PublishResult``, never a raise."""
        try:
            created_at = datetime.now(UTC)
            parent_id = await self.create_carousel_container(caption, image_urls)
            post_id = await self.publish_container(parent_id, created_at)
        except RuntimeError as exc:
            return PublishResult(status=PUBLISH_RESULT_FAILED, error_message=str(exc))
        except InstagramGraphError as exc:
            return PublishResult(
                status=PUBLISH_RESULT_FAILED,
                error_message=_client_message(exc),
            )
        except httpx.HTTPError:
            logger.exception("instagram_publish_http_error")
            return PublishResult(
                status=PUBLISH_RESULT_FAILED,
                error_message=ERR_INSTAGRAM_API_REQUEST_FAILED,
            )
        return PublishResult(status=PUBLISH_RESULT_PUBLISHED, post_id=post_id)

    async def current_token(self) -> str:
        """Return the provider's token without calling Graph."""
        return await self._config.token_provider.get()

    def user_configured(self) -> bool:
        """True when an Instagram user id is set."""
        return bool(self._config.ig_user_id)

    async def create_carousel_container(
        self, caption: str, image_urls: list[str]
    ) -> str:
        """Create item containers and the parent carousel. Does not publish."""
        self._validate_images(image_urls)
        item_ids = [await self._create_item(url) for url in image_urls]
        return await self._create_parent(item_ids, caption)

    async def await_container(self, container_id: str) -> str:
        """Poll until ``FINISHED`` or ``PUBLISHED`` and return it. Timeout is transient."""
        for _attempt in range(META_POLL_MAX_ATTEMPTS):
            status = await self.container_status(container_id)
            if status in _TERMINAL_OK:
                return status
            if status in {CONTAINER_STATUS_ERROR, CONTAINER_STATUS_EXPIRED}:
                raise InstagramGraphError(
                    status_code=400,
                    error_code=ERR_INSTAGRAM_CONTAINER_FAILED,
                    transient=False,
                )
            await asyncio.sleep(_POLL_INTERVAL_SECONDS)
        raise InstagramGraphError(
            status_code=0,
            error_code=ERR_INSTAGRAM_CONTAINER_TIMEOUT,
            transient=True,
        )

    async def publish_container(self, container_id: str, created_at: datetime) -> str:
        """Poll, then publish once. An already published container is recovered."""
        status = await self.await_container(container_id)
        if status == CONTAINER_STATUS_PUBLISHED:
            return await self.recover_published_media(container_id, created_at)
        return await self.media_publish(container_id)

    async def recover_published_media(
        self, container_id: str, created_at: datetime
    ) -> str:
        """Media id for a ``PUBLISHED`` container, read from the recent media list.

        Only an album posted after ``created_at`` can match (QA r2 R3). Raises
        a non-transient error when none or several match: calling
        ``media_publish`` again could post the carousel twice.
        """
        payload = await self._request(
            _GraphCall(
                method=HTTP_GET,
                path=GRAPH_PATH_MEDIA.format(ig_user_id=self._config.ig_user_id),
                query={
                    FIELD_FIELDS: _RECENT_MEDIA_FIELDS,
                    FIELD_LIMIT: str(RECENT_MEDIA_LIMIT),
                },
            )
        )
        since = created_at - timedelta(seconds=CONTAINER_CLOCK_SKEW_SECONDS)
        media_id = recent_carousel_id(payload, since)
        logger.warning(
            "instagram_container_already_published",
            container_id=container_id,
            recovered=media_id is not None,
        )
        if media_id is None:
            raise InstagramGraphError(
                status_code=200,
                error_code=ERR_INSTAGRAM_PUBLISHED_MEDIA_UNKNOWN,
                transient=False,
            )
        return media_id

    async def media_publish(self, container_id: str) -> str:
        """Publish one finished container. Returns the media id."""
        payload = await self._request(
            _GraphCall(
                method=HTTP_POST,
                path=GRAPH_PATH_MEDIA_PUBLISH.format(
                    ig_user_id=self._config.ig_user_id
                ),
                form={FIELD_CREATION_ID: container_id},
            )
        )
        return _require_id(payload)

    async def fetch_permalink(self, media_id: str) -> str:
        """Read ``permalink`` for a published media id."""
        payload = await self._request(
            _GraphCall(
                method=HTTP_GET,
                path=GRAPH_PATH_MEDIA_NODE.format(media_id=media_id),
                query={FIELD_FIELDS: FIELD_PERMALINK},
            )
        )
        link = payload.get(FIELD_PERMALINK)
        if not isinstance(link, str) or not link:
            raise InstagramGraphError(
                status_code=200,
                error_code=ERR_INSTAGRAM_API_NO_ID,
                transient=True,
            )
        return link

    async def content_publishing_remaining(self) -> int:
        """Return quota left (``quota_total - quota_usage``). Unreadable is transient."""
        payload = await self._request(
            _GraphCall(
                method=HTTP_GET,
                path=GRAPH_PATH_PUBLISHING_LIMIT.format(
                    ig_user_id=self._config.ig_user_id
                ),
            )
        )
        return quota_remaining(payload)

    async def close(self) -> None:
        """Close the client this instance created."""
        if self._owns_client:
            await self._client.aclose()

    async def _create_item(self, image_url: str) -> str:
        payload = await self._request(
            _GraphCall(
                method=HTTP_POST,
                path=GRAPH_PATH_MEDIA.format(ig_user_id=self._config.ig_user_id),
                form={
                    FIELD_IMAGE_URL: image_url,
                    FIELD_IS_CAROUSEL_ITEM: VALUE_TRUE,
                },
            )
        )
        return _require_id(payload)

    async def _create_parent(self, item_ids: list[str], caption: str) -> str:
        payload = await self._request(
            _GraphCall(
                method=HTTP_POST,
                path=GRAPH_PATH_MEDIA.format(ig_user_id=self._config.ig_user_id),
                form={
                    FIELD_MEDIA_TYPE: MEDIA_TYPE_CAROUSEL,
                    FIELD_CHILDREN: ",".join(item_ids),
                    FIELD_CAPTION: caption,
                },
            )
        )
        return _require_id(payload)

    async def container_status(self, container_id: str) -> str:
        """The container's ``status_code`` (``FINISHED``, ``PUBLISHED``, ...)."""
        payload = await self._request(
            _GraphCall(
                method=HTTP_GET,
                path=GRAPH_PATH_MEDIA_NODE.format(media_id=container_id),
                query={FIELD_FIELDS: FIELD_STATUS_CODE},
            )
        )
        status = payload.get(FIELD_STATUS_CODE, "")
        if isinstance(status, str):
            return status
        return ""

    async def _request(self, call: _GraphCall) -> dict[str, object]:
        token = await self._require_token()
        last_error: InstagramGraphError | None = None
        for _attempt in range(META_MAX_ATTEMPTS):
            response = await self._send(call, token)
            if response.is_success:
                return json_dict(response)
            error = error_from(response)
            if not error.transient:
                raise error
            last_error = error
        if last_error is None:
            raise InstagramGraphError(
                status_code=0,
                error_code=ERR_INSTAGRAM_API_REQUEST_FAILED,
                transient=True,
            )
        raise last_error

    async def _send(self, call: _GraphCall, token: str) -> httpx.Response:
        form = dict(call.form or {})
        query = dict(call.query or {})
        if call.method == HTTP_POST:
            form[COOKIE_ACCESS_TOKEN] = token
        else:
            query[COOKIE_ACCESS_TOKEN] = token
        try:
            async with asyncio.timeout(_REQUEST_DEADLINE_SECONDS):
                return await self._client.request(
                    call.method,
                    self._url(call.path),
                    data=form or None,
                    params=query or None,
                )
        except TimeoutError as exc:
            # One overall deadline per request bounds the worst-case publish
            # time the publish-claim stale window is derived from (QA r2 R4a).
            logger.warning("instagram_graph_request_deadline", path=call.path)
            raise httpx.TimeoutException(ERR_INSTAGRAM_API_REQUEST_FAILED) from exc
        except httpx.HTTPError:
            logger.exception("instagram_graph_transport_error", path=call.path)
            raise

    async def _require_token(self) -> str:
        token = await self.current_token()
        if not token or not self.user_configured():
            raise RuntimeError(ERR_INSTAGRAM_CREDENTIALS_NOT_CONFIGURED)
        return token

    def _url(self, path: str) -> str:
        return f"{self._config.graph_base.rstrip('/')}{path}"

    @staticmethod
    def _validate_images(image_urls: list[str]) -> None:
        count = len(image_urls)
        if count < MIN_INSTAGRAM_CAROUSEL_ITEMS or count > MAX_INSTAGRAM_CAROUSEL_ITEMS:
            raise RuntimeError(ERR_INSTAGRAM_IMAGE_COUNT_INVALID)


def _client_message(exc: InstagramGraphError) -> str:
    if exc.error_code in _CLIENT_MESSAGES:
        return exc.error_code
    return ERR_INSTAGRAM_API_REQUEST_FAILED


def _require_id(payload: dict[str, object]) -> str:
    raw = payload.get(FIELD_ID)
    if raw is None or raw == "":
        logger.error("instagram_api_missing_id")
        raise InstagramGraphError(
            status_code=200,
            error_code=ERR_INSTAGRAM_API_NO_ID,
            transient=False,
        )
    return str(raw)
