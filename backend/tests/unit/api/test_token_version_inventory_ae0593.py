"""Every route that reads the access token checks the token version.

Scenarios: ``tests/features/logout_other_sessions_ae0593.feature``. Walks the
dependency tree of every HTTP and websocket route of the real app: the raw
token payload (``api.middleware.auth``) may only be reached through a
dependency that loads the user and refuses a token from before the user's
last password change. Unlike the forced-change flag, there is no exception:
``/api/auth/me`` and ``/api/auth/change-password`` check it too.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute, APIWebSocketRoute

from rag_backend.api.dependencies import auth as dependencies_auth
from rag_backend.api.dependencies import roles
from rag_backend.api.middleware import auth as middleware_auth
from rag_backend.domain.models import User

_VERSION_CHECKED: frozenset[Callable[..., object]] = frozenset({
    dependencies_auth.require_signed_in_user,
    dependencies_auth.get_optional_user,
    roles.get_current_user,
})
_RAW_TOKEN: frozenset[Callable[..., object]] = frozenset({
    middleware_auth.get_current_user,
    middleware_auth.get_current_user_optional,
})


def _reaches_raw_token_unchecked(dependant: Dependant) -> bool:
    """Whether the tree reaches the raw token without a version check."""
    if dependant.call in _VERSION_CHECKED:
        return False
    if dependant.call in _RAW_TOKEN:
        return True
    return any(_reaches_raw_token_unchecked(sub) for sub in dependant.dependencies)


def _reaches_a_check(dependant: Dependant) -> bool:
    """Whether the tree goes through a version-checking dependency."""
    if dependant.call in _VERSION_CHECKED:
        return True
    return any(_reaches_a_check(sub) for sub in dependant.dependencies)


def _routes(app: FastAPI) -> list[APIRoute | APIWebSocketRoute]:
    return [r for r in app.routes if isinstance(r, APIRoute | APIWebSocketRoute)]


def unchecked_paths(app: FastAPI) -> set[str]:
    """Paths of the HTTP and websocket routes that skip the version check."""
    return {
        route.path
        for route in _routes(app)
        if _reaches_raw_token_unchecked(route.dependant)
    }


# Scenario: Every route that reads the token checks the token version
def test_no_route_reads_the_token_without_the_version_check() -> None:
    from rag_backend.api.app import create_app

    app = create_app()

    assert unchecked_paths(app) == set()
    checked = {r.path for r in _routes(app) if _reaches_a_check(r.dependant)}
    assert {"/api/auth/me", "/api/auth/change-password"} <= checked


# Scenario: Every route that reads the token checks the token version
def test_the_inventory_fires_on_a_route_that_reads_the_raw_token() -> None:
    router = APIRouter()

    @router.get("/seeded/raw")
    async def raw(
        payload: Annotated[dict[str, str], Depends(middleware_auth.get_current_user)],
    ) -> dict[str, str]:
        return payload

    @router.get("/seeded/signed-in")
    async def signed_in(
        user: Annotated[User, Depends(dependencies_auth.require_signed_in_user)],
    ) -> str:
        return user.email

    @router.get(
        "/seeded/route-level",
        dependencies=[Depends(middleware_auth.get_current_user_optional)],
    )
    async def route_level() -> None:
        return None

    @router.websocket("/seeded/ws")
    async def socket(
        payload: Annotated[dict[str, str], Depends(middleware_auth.get_current_user)],
    ) -> None:
        del payload

    app = FastAPI()
    app.include_router(router)

    assert unchecked_paths(app) == {"/seeded/raw", "/seeded/route-level", "/seeded/ws"}
