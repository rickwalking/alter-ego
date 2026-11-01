"""Every route that reads the token checks the forced password change flag.

Scenarios: ``tests/features/change_own_password_ae0511.feature``. Walks the
dependency tree of every HTTP and websocket route of the real app: the raw
token payload (``api.middleware.auth``) may only be reached through a
dependency that applies the ``must_change_password`` check, except on
``/api/auth/me`` and ``/api/auth/change-password``.
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

_FLAG_CHECKED: frozenset[Callable[..., object]] = frozenset({
    dependencies_auth.require_authenticated_user,
    dependencies_auth.get_optional_user,
    roles.get_current_user,
})
_RAW_TOKEN: frozenset[Callable[..., object]] = frozenset({
    middleware_auth.get_current_user,
    middleware_auth.get_current_user_optional,
})
_ALLOWED_UNCHECKED = frozenset({"/api/auth/me", "/api/auth/change-password"})


def _reaches_raw_token_unchecked(dependant: Dependant) -> bool:
    """Whether the tree reaches the raw token without a flag-checking dependency."""
    if dependant.call in _FLAG_CHECKED:
        return False
    if dependant.call in _RAW_TOKEN:
        return True
    return any(_reaches_raw_token_unchecked(sub) for sub in dependant.dependencies)


def unchecked_paths(app: FastAPI) -> set[str]:
    """Paths of the HTTP and websocket routes that skip the flag check."""
    return {
        route.path
        for route in app.routes
        if isinstance(route, APIRoute | APIWebSocketRoute)
        and _reaches_raw_token_unchecked(route.dependant)
    }


# Scenario: A user with a temporary password is refused on protected endpoints
def test_only_me_and_change_password_skip_the_flag_check() -> None:
    from rag_backend.api.app import create_app

    assert unchecked_paths(create_app()) == _ALLOWED_UNCHECKED


# Scenario: A user with a temporary password is refused on protected endpoints
def test_the_inventory_fires_on_a_route_that_reads_the_raw_token() -> None:
    router = APIRouter()

    @router.get("/seeded/raw")
    async def raw(
        payload: Annotated[dict[str, str], Depends(middleware_auth.get_current_user)],
    ) -> dict[str, str]:
        return payload

    @router.get("/seeded/checked")
    async def checked(
        user: Annotated[User, Depends(dependencies_auth.require_authenticated_user)],
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
