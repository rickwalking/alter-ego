"""Tests for the tenacity-based retry utility."""

import httpx
import pytest

from rag_backend.domain.retry import (
    DEFAULT_RETRY_CONFIG,
    _is_retryable_api_error,
    _is_retryable_http,
    retry_async,
    retry_sync,
)


def _make_response(status_code: int) -> httpx.Response:
    return httpx.Response(status_code=status_code)


class TestIsRetryableHttp:
    _REQUEST = httpx.Request("GET", "/")

    def _http(self, status: int, msg: str = "") -> httpx.HTTPStatusError:
        return httpx.HTTPStatusError(msg, request=self._REQUEST, response=_make_response(status))

    def test_429_too_many_requests(self) -> None:
        assert _is_retryable_http(self._http(429))

    def test_500_internal_error(self) -> None:
        assert _is_retryable_http(self._http(500))

    def test_502_bad_gateway(self) -> None:
        assert _is_retryable_http(self._http(502))

    def test_503_unavailable(self) -> None:
        assert _is_retryable_http(self._http(503))

    def test_504_gateway_timeout(self) -> None:
        assert _is_retryable_http(self._http(504))

    def test_400_bad_request_not_retryable(self) -> None:
        assert not _is_retryable_http(self._http(400))

    def test_401_unauthorized_not_retryable(self) -> None:
        assert not _is_retryable_http(self._http(401))

    def test_404_not_found_not_retryable(self) -> None:
        assert not _is_retryable_http(self._http(404))

    def test_timeout_exception(self) -> None:
        exc = httpx.TimeoutException("connection timed out")
        assert _is_retryable_http(exc)

    def test_connect_error(self) -> None:
        exc = httpx.ConnectError("connection refused")
        assert _is_retryable_http(exc)

    def test_remote_protocol_error(self) -> None:
        exc = httpx.RemoteProtocolError("remote closed connection")
        assert _is_retryable_http(exc)

    def test_unrelated_exception_not_retryable(self) -> None:
        exc = ValueError("invalid input")
        assert not _is_retryable_http(exc)


class TestIsRetryableApiError:
    def test_delegates_to_http_check(self) -> None:
        exc = httpx.TimeoutException("timed out")
        assert _is_retryable_api_error(exc)

    def test_rate_limit_in_message(self) -> None:
        exc = RuntimeError("rate limit exceeded")
        assert _is_retryable_api_error(exc)

    def test_timeout_in_message(self) -> None:
        exc = RuntimeError("request timeout after 30s")
        assert _is_retryable_api_error(exc)

    def test_connection_in_message(self) -> None:
        exc = OSError("connection reset by peer")
        assert _is_retryable_api_error(exc)

    def test_try_again_in_message(self) -> None:
        exc = RuntimeError("please try again later")
        assert _is_retryable_api_error(exc)

    def test_random_error_not_retryable(self) -> None:
        exc = RuntimeError("something else entirely")
        assert not _is_retryable_api_error(exc)


class TestRetryConfig:
    def test_default_config_has_expected_keys(self) -> None:
        assert "stop" in DEFAULT_RETRY_CONFIG
        assert "wait" in DEFAULT_RETRY_CONFIG
        assert "retry" in DEFAULT_RETRY_CONFIG

    def test_default_config_stops_after_3_attempts(self) -> None:
        call_count = 0

        def always_fail() -> None:
            nonlocal call_count
            call_count += 1
            raise ConnectionError("transient")

        with pytest.raises(ConnectionError, match="transient"):
            for attempt in retry_sync():
                with attempt:
                    always_fail()

        assert call_count == 3

    def test_sync_retry_succeeds_on_second_attempt(self) -> None:
        call_count = 0

        def fail_then_succeed() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("transient")
            return "success"

        result = None
        for attempt in retry_sync(attempts=3, min_wait=0.01, max_wait=0.05):
            with attempt:
                result = fail_then_succeed()

        assert result == "success"
        assert call_count == 2


@pytest.mark.asyncio
class TestRetryAsync:
    async def test_stops_after_exhausted_attempts(self) -> None:
        call_count = 0

        async def always_fail() -> None:
            nonlocal call_count
            call_count += 1
            raise TimeoutError("timed out")

        with pytest.raises(TimeoutError, match="timed out"):
            async for attempt in retry_async(attempts=2, min_wait=0.01, max_wait=0.05):
                with attempt:
                    await always_fail()

        assert call_count == 2

    async def test_succeeds_on_first_attempt(self) -> None:
        async def succeed() -> str:
            return "ok"

        result = None
        async for attempt in retry_async(attempts=3, min_wait=0.01, max_wait=0.05):
            with attempt:
                result = await succeed()

        assert result == "ok"

    async def test_non_retryable_exception_passes_through(self) -> None:
        async def fail() -> None:
            raise ValueError("not retryable")

        with pytest.raises(ValueError, match="not retryable"):
            async for attempt in retry_async(attempts=3, min_wait=0.01, max_wait=0.05):
                with attempt:
                    await fail()


class TestRetrySyncCustomParams:
    def test_custom_attempts(self) -> None:
        call_count = 0

        def fail() -> None:
            nonlocal call_count
            call_count += 1
            raise OSError("transient")

        with pytest.raises(OSError, match="transient"):
            for attempt in retry_sync(attempts=5, min_wait=0.01, max_wait=0.05):
                with attempt:
                    fail()

        assert call_count == 5
