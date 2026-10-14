"""Meta Instagram Graph API publisher.

Carousel publish is four steps against the configured Graph host:

1. One item container per image (``is_carousel_item``).
2. A parent ``CAROUSEL`` container.
3. Poll ``status_code`` until ``FINISHED``.
4. ``media_publish`` with that container as ``creation_id``.

``META_IG_GRAPH_BASE`` selects the host. The default is Instagram Login
(``graph.instagram.com``). Page tokens can select ``graph.facebook.com``.
The access token comes from an ``InstagramTokenProvider``. AE-0358's
encrypted store is the production provider.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import httpx

from rag_backend.domain.constants import COOKIE_ACCESS_TOKEN
from rag_backend.domain.constants.instagram_publish import (
    CONTAINER_STATUS_ERROR,
    CONTAINER_STATUS_EXPIRED,
    CONTAINER_STATUS_FINISHED,
    ERR_INSTAGRAM_API_NO_ID,
    ERR_INSTAGRAM_API_REQUEST_FAILED,
    ERR_INSTAGRAM_CONTAINER_FAILED,
    ERR_INSTAGRAM_CONTAINER_TIMEOUT,
    ERR_INSTAGRAM_CREDENTIALS_NOT_CONFIGURED,
    ERR_INSTAGRAM_IMAGE_COUNT_INVALID,
    ERR_INSTAGRAM_QUOTA_UNREADABLE,
    FIELD_CAPTION,
    FIELD_CHILDREN,
    FIELD_CREATION_ID,
    FIELD_FIELDS,
    FIELD_ID,
    FIELD_IMAGE_URL,
    FIELD_IS_CAROUSEL_ITEM,
    FIELD_MEDIA_TYPE,
    FIELD_PERMALINK,
    FIELD_STATUS_CODE,
    GRAPH_PATH_MEDIA,
    GRAPH_PATH_MEDIA_NODE,
    GRAPH_PATH_MEDIA_PUBLISH,
    GRAPH_PATH_PUBLISHING_LIMIT,
    HTTP_GET,
    HTTP_POST,
    KEY_CODE,
    KEY_CONFIG,
    KEY_DATA,
    KEY_ERROR,
    KEY_QUOTA_TOTAL,
    KEY_QUOTA_USAGE,
    MAX_INSTAGRAM_CAROUSEL_ITEMS,
    MEDIA_TYPE_CAROUSEL,
    MIN_INSTAGRAM_CAROUSEL_ITEMS,
    PUBLISH_RESULT_FAILED,
    PUBLISH_RESULT_PUBLISHED,
    TRANSIENT_HTTP_STATUS,
    TRANSIENT_META_ERROR_CODES,
    VALUE_TRUE,
)
from rag_backend.domain.constants.retry import META_MAX_ATTEMPTS, META_POLL_MAX_ATTEMPTS
from rag_backend.domain.protocols.instagram_token import InstagramTokenProvider
from rag_backend.domain.protocols.social import PublishResult
from rag_backend.infrastructure.external.instagram_graph_error import (
    InstagramGraphError,
)
from rag_backend.infrastructure.logging import get_logger

logger = get_logger()

# Tests patch this to skip the real poll sleep.
_POLL_INTERVAL_SECONDS = 2.0

_CLIENT_MESSAGES = frozenset({
    ERR_INSTAGRAM_CONTAINER_FAILED,
    ERR_INSTAGRAM_CONTAINER_TIMEOUT,
    ERR_INSTAGRAM_API_NO_ID,
    ERR_INSTAGRAM_QUOTA_UNREADABLE,
})


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
            parent_id = await self.create_carousel_container(caption, image_urls)
            await self.await_container(parent_id)
            post_id = await self.media_publish(parent_id)
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

    async def await_container(self, container_id: str) -> None:
        """Poll until the container is ``FINISHED``. Timeout is transient."""
        for _attempt in range(META_POLL_MAX_ATTEMPTS):
            status = await self._container_status(container_id)
            if status == CONTAINER_STATUS_FINISHED:
                return
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
        return _quota_remaining(payload)

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

    async def _container_status(self, container_id: str) -> str:
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
                return _json_dict(response)
            error = _error_from(response)
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
            return await self._client.request(
                call.method,
                self._url(call.path),
                data=form or None,
                params=query or None,
            )
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


def _json_dict(response: httpx.Response) -> dict[str, object]:
    body: object = response.json()
    if not isinstance(body, dict):
        return {}
    return {str(key): value for key, value in body.items()}


def _error_from(response: httpx.Response) -> InstagramGraphError:
    code = _meta_code(response)
    transient = (
        response.status_code in TRANSIENT_HTTP_STATUS
        or code in TRANSIENT_META_ERROR_CODES
    )
    return InstagramGraphError(
        status_code=response.status_code,
        error_code=code,
        transient=transient,
    )


def _meta_code(response: httpx.Response) -> str:
    error = _json_dict(response).get(KEY_ERROR)
    if isinstance(error, dict):
        code = error.get(KEY_CODE)
        if code is not None:
            return str(code)
    return str(response.status_code)


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


def _quota_remaining(payload: dict[str, object]) -> int:
    data = payload.get(KEY_DATA)
    if not isinstance(data, list) or not data:
        raise _quota_error()
    first = data[0]
    if not isinstance(first, dict):
        raise _quota_error()
    usage = first.get(KEY_QUOTA_USAGE)
    config = first.get(KEY_CONFIG)
    if isinstance(usage, bool) or not isinstance(usage, int):
        raise _quota_error()
    if not isinstance(config, dict):
        raise _quota_error()
    total = config.get(KEY_QUOTA_TOTAL)
    if isinstance(total, bool) or not isinstance(total, int):
        raise _quota_error()
    return total - usage


def _quota_error() -> InstagramGraphError:
    return InstagramGraphError(
        status_code=200,
        error_code=ERR_INSTAGRAM_QUOTA_UNREADABLE,
        transient=True,
    )
