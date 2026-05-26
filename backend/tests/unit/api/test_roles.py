"""Unit tests for JWT-backed role dependencies."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from rag_backend.api.dependencies.roles import get_current_user, require_editor
from rag_backend.domain.models.user import UserRole


@pytest.mark.asyncio
class TestGetCurrentUser:
    async def test_returns_user_for_valid_payload(self) -> None:
        db = AsyncMock()
        user = MagicMock(is_active=True)
        db.get = AsyncMock(return_value=user)

        result = await get_current_user({"sub": "user-1"}, db)

        assert result is user

    async def test_rejects_missing_subject(self) -> None:
        db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user({}, db)

        assert exc_info.value.status_code == 401

    async def test_rejects_inactive_user(self) -> None:
        db = AsyncMock()
        db.get = AsyncMock(return_value=MagicMock(is_active=False))

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user({"sub": "user-1"}, db)

        assert exc_info.value.status_code == 401


@pytest.mark.asyncio
class TestRequireEditor:
    async def test_allows_editor_role(self) -> None:
        user = MagicMock(role=UserRole.EDITOR.value)

        result = await require_editor(user)

        assert result is user

    async def test_rejects_unauthorized_role(self) -> None:
        user = MagicMock(role="viewer")

        with pytest.raises(HTTPException) as exc_info:
            await require_editor(user)

        assert exc_info.value.status_code == 403
