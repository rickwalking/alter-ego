"""ddgs adapter and collector wiring.

The default resolver is ``none``. Building the service does not open a socket.
"""

from __future__ import annotations

from typing import get_args

import pytest

from rag_backend.infrastructure.config.settings import Settings, get_settings
from rag_backend.modules.autopilot.api.router import signals_reader
from rag_backend.modules.autopilot.application.signals_service import SignalsService
from rag_backend.modules.autopilot.bootstrap import default_signals_service
from rag_backend.modules.autopilot.constants import (
    APP_STATE_SIGNALS,
    NO_RESULTS_MARK,
    X_QUERY_SPACING_MAX_SECONDS,
    X_QUERY_SPACING_MIN_SECONDS,
    X_RESOLVER_MIRROR,
    X_RESOLVER_NONE,
    X_SEARCH_MAX_RESULTS,
    X_SEARCH_TIMELIMIT,
)
from rag_backend.modules.autopilot.domain.ports import WebSearchQuery
from rag_backend.modules.autopilot.infrastructure.collectors.ddgs_search import (
    DdgsWebSearch,
)
from rag_backend.modules.autopilot.infrastructure.collectors.factory import (
    AsyncioPause,
    CollectorBuildConfig,
    UniformJitter,
    select_resolver,
)
from rag_backend.modules.autopilot.infrastructure.collectors.http_get import HttpxGetter
from rag_backend.modules.autopilot.infrastructure.collectors.x_resolver import (
    MirrorResolver,
    NoneResolver,
)

_QUERY = WebSearchQuery(text="site:x.com agents", timelimit="d", max_results=10)


class _DDGS:
    def __init__(
        self, rows: list[dict[str, str]] | None = None, *, fail: str = ""
    ) -> None:
        self.rows = rows or []
        self.fail = fail
        self.kwargs: dict[str, object] = {}

    def __enter__(self) -> _DDGS:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def text(self, query: str, **kwargs: object) -> list[object]:
        del query
        self.kwargs = kwargs
        if self.fail:
            raise RuntimeError(self.fail)
        mixed: list[object] = [*self.rows, {"title": "missing href"}, "not-a-dict"]
        return mixed


def _patch(monkeypatch: pytest.MonkeyPatch, client: _DDGS) -> None:
    monkeypatch.setattr("ddgs.DDGS", lambda: client)


@pytest.mark.asyncio
async def test_ddgs_passes_timelimit_and_maps_hits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _DDGS([{"href": "https://example.com/a", "title": "A", "body": "snippet"}])
    _patch(monkeypatch, client)
    hits = await DdgsWebSearch().search(_QUERY)
    assert len(hits) == 1
    assert hits[0].url == "https://example.com/a"
    assert hits[0].snippet == "snippet"
    assert client.kwargs["timelimit"] == X_SEARCH_TIMELIMIT
    assert client.kwargs["max_results"] == X_SEARCH_MAX_RESULTS


@pytest.mark.asyncio
async def test_ddgs_empty_result_is_not_a_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch(monkeypatch, _DDGS(fail=NO_RESULTS_MARK))
    assert await DdgsWebSearch().search(_QUERY) == []


@pytest.mark.asyncio
async def test_ddgs_other_errors_propagate(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch, _DDGS(fail="timed out"))
    with pytest.raises(RuntimeError, match="timed out"):
        await DdgsWebSearch().search(_QUERY)


def test_resolver_setting_matches_the_module_constants() -> None:
    field = Settings.model_fields["autopilot_x_resolver"]
    assert field.default == X_RESOLVER_NONE
    assert set(get_args(field.annotation)) == {X_RESOLVER_NONE, X_RESOLVER_MIRROR}


def test_select_resolver_defaults_to_none_and_mirror_is_explicit() -> None:
    http = HttpxGetter(5.0)
    none = select_resolver(
        CollectorBuildConfig(
            x_resolver=X_RESOLVER_NONE, x_mirror_host="", github_token=""
        ),
        http,
    )
    mirror = select_resolver(
        CollectorBuildConfig(
            x_resolver=X_RESOLVER_MIRROR,
            x_mirror_host="mirror.example",
            github_token="",
        ),
        http,
    )
    assert isinstance(none, NoneResolver)
    assert isinstance(mirror, MirrorResolver)


def test_jitter_stays_inside_the_spacing_window() -> None:
    jitter = UniformJitter()
    gaps = [jitter.seconds() for _ in range(30)]
    assert min(gaps) >= X_QUERY_SPACING_MIN_SECONDS
    assert max(gaps) <= X_QUERY_SPACING_MAX_SECONDS


@pytest.mark.asyncio
async def test_pause_accepts_a_zero_delay() -> None:
    await AsyncioPause().pause(0)


def test_default_service_builds_without_collecting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTOPILOT_X_RESOLVER", X_RESOLVER_NONE)
    monkeypatch.setenv("AUTOPILOT_X_MIRROR_HOST", "")
    monkeypatch.setenv("GITHUB_TOKEN", "")
    get_settings.cache_clear()
    service = default_signals_service()
    assert service.collect_all is not None
    get_settings.cache_clear()


def test_signals_reader_uses_the_override_or_the_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTOPILOT_X_RESOLVER", X_RESOLVER_NONE)
    monkeypatch.setenv("GITHUB_TOKEN", "")
    get_settings.cache_clear()

    class _State:
        pass

    empty = _State()
    request = type("Request", (), {"app": type("App", (), {"state": empty})()})()
    assert isinstance(signals_reader(request), SignalsService)

    class _Idle:
        async def collect_all(self) -> None:
            return None

    idle = _Idle()
    setattr(empty, APP_STATE_SIGNALS, idle)
    assert signals_reader(request) is idle
    get_settings.cache_clear()
