"""Unit tests for carousel access helpers.

Feature: carousel_pipeline_consolidation.feature — security and preview ACL
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from rag_backend.api.constants import ERR_CAROUSEL_NOT_FOUND
from rag_backend.api.dependencies.carousel_access import (
    ProjectSourceLookup,
    assert_carousel_conversation_chat_access,
    get_carousel_project_for_domain_user,
    get_carousel_project_for_user,
    get_carousel_project_for_workflow_user,
    get_project_source_for_user,
    validate_carousel_conversation_metadata,
)
from rag_backend.domain.constants.access_control import (
    ERR_ACCESS_DENIED_NOT_OWNER,
    ERR_CAROUSEL_TOOL_ACCESS_DENIED,
    ERR_INVALID_REQUEST,
    ERR_SOURCE_NOT_FOUND,
)
from rag_backend.domain.constants.conversation import (
    CONVERSATION_METADATA_PROJECT_ID,
    ERR_ANONYMOUS_CAROUSEL_CONVERSATION,
    ERR_CAROUSEL_CONVERSATION_REQUIRES_AUTH,
    ERR_CONVERSATION_OWNERSHIP_DENIED,
)
from rag_backend.domain.models import Conversation, User
from rag_backend.domain.models.user import UserRole
from rag_backend.infrastructure.database.models import UserModel
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.infrastructure.database.models.source_comment import ContentSourceModel


def _user_model(role: UserRole, user_id: str = "user-1") -> MagicMock:
    user = MagicMock()
    user.id = user_id
    user.role = role.value
    return user


def _domain_user(user_id: UUID | None = None, *, admin: bool = False) -> User:
    uid = user_id or uuid4()
    return User(
        id=uid,
        email=f"{uid}@example.com",
        full_name="Test User",
        role=UserRole.ADMIN if admin else UserRole.EDITOR,
        hashed_password="hash",
    )


class TestAssertCarouselConversationChatAccess:
    def test_allows_non_carousel_conversation_without_auth(self) -> None:
        conversation = Conversation(id=uuid4(), metadata={})
        assert_carousel_conversation_chat_access(conversation, None)

    def test_requires_auth_for_carousel_metadata(self) -> None:
        conversation = Conversation(
            id=uuid4(),
            user_id=uuid4(),
            metadata={CONVERSATION_METADATA_PROJECT_ID: str(uuid4())},
        )
        with pytest.raises(HTTPException) as exc_info:
            assert_carousel_conversation_chat_access(conversation, None)
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == ERR_CAROUSEL_CONVERSATION_REQUIRES_AUTH

    def test_rejects_anonymous_carousel_conversation(self) -> None:
        conversation = Conversation(
            id=uuid4(),
            user_id=None,
            metadata={CONVERSATION_METADATA_PROJECT_ID: str(uuid4())},
        )
        user = _domain_user()
        with pytest.raises(HTTPException) as exc_info:
            assert_carousel_conversation_chat_access(conversation, user)
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == ERR_ANONYMOUS_CAROUSEL_CONVERSATION

    def test_rejects_wrong_owner(self) -> None:
        owner_id = uuid4()
        conversation = Conversation(
            id=uuid4(),
            user_id=owner_id,
            metadata={CONVERSATION_METADATA_PROJECT_ID: str(uuid4())},
        )
        other = _domain_user(uuid4())
        with pytest.raises(HTTPException) as exc_info:
            assert_carousel_conversation_chat_access(conversation, other)
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == ERR_CONVERSATION_OWNERSHIP_DENIED

    def test_allows_owner(self) -> None:
        owner_id = uuid4()
        conversation = Conversation(
            id=uuid4(),
            user_id=owner_id,
            metadata={CONVERSATION_METADATA_PROJECT_ID: str(uuid4())},
        )
        owner = _domain_user(owner_id)
        assert_carousel_conversation_chat_access(conversation, owner)


@pytest.mark.asyncio
class TestValidateCarouselConversationMetadata:
    async def test_skips_when_no_project_metadata(self) -> None:
        db = AsyncMock()
        await validate_carousel_conversation_metadata(db, {}, _domain_user())

    async def test_rejects_anonymous_user(self) -> None:
        db = AsyncMock()
        with pytest.raises(HTTPException) as exc_info:
            await validate_carousel_conversation_metadata(
                db,
                {CONVERSATION_METADATA_PROJECT_ID: str(uuid4())},
                None,
            )
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == ERR_CAROUSEL_CONVERSATION_REQUIRES_AUTH

    async def test_rejects_invalid_project_uuid(self) -> None:
        db = AsyncMock()
        with pytest.raises(HTTPException) as exc_info:
            await validate_carousel_conversation_metadata(
                db,
                {CONVERSATION_METADATA_PROJECT_ID: "not-a-uuid"},
                _domain_user(),
            )
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == ERR_INVALID_REQUEST

    async def test_rejects_missing_user_model(self) -> None:
        db = AsyncMock()
        db.get = AsyncMock(return_value=None)
        user = _domain_user()
        with pytest.raises(HTTPException) as exc_info:
            await validate_carousel_conversation_metadata(
                db,
                {CONVERSATION_METADATA_PROJECT_ID: str(uuid4())},
                user,
            )
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == ERR_CAROUSEL_CONVERSATION_REQUIRES_AUTH
        db.get.assert_awaited_once_with(UserModel, str(user.id))

    async def test_loads_project_for_owner(self) -> None:
        project_id = uuid4()
        owner_id = uuid4()
        owner = _domain_user(owner_id)
        user_model = _user_model(UserRole.EDITOR, str(owner_id))
        db = AsyncMock()
        db.get = AsyncMock(return_value=user_model)

        with patch(
            "rag_backend.api.dependencies.carousel_access.get_carousel_project_for_workflow_user",
            new_callable=AsyncMock,
        ) as workflow_get:
            await validate_carousel_conversation_metadata(
                db,
                {CONVERSATION_METADATA_PROJECT_ID: str(project_id)},
                owner,
            )
            workflow_get.assert_awaited_once_with(db, project_id, user_model)


@pytest.mark.asyncio
class TestGetCarouselProjectForWorkflowUser:
    async def test_raises_forbidden_when_missing(self) -> None:
        project_id = uuid4()
        db = AsyncMock()
        db.get = AsyncMock(return_value=None)
        with pytest.raises(HTTPException) as exc_info:
            await get_carousel_project_for_workflow_user(
                db, project_id, _user_model(UserRole.EDITOR)
            )
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == ERR_CAROUSEL_TOOL_ACCESS_DENIED
        db.get.assert_awaited_once_with(CarouselProjectModel, str(project_id))

    async def test_allows_assigned_reviewer(self) -> None:
        reviewer_id = "reviewer-1"
        project = MagicMock(owner_id="other", assigned_reviewer_id=reviewer_id)
        db = AsyncMock()
        db.get = AsyncMock(return_value=project)
        result = await get_carousel_project_for_workflow_user(
            db, uuid4(), _user_model(UserRole.EDITOR, reviewer_id)
        )
        assert result is project

    async def test_allows_owner(self) -> None:
        owner_id = "owner-1"
        project = MagicMock(owner_id=owner_id, assigned_reviewer_id=None)
        db = AsyncMock()
        db.get = AsyncMock(return_value=project)
        result = await get_carousel_project_for_workflow_user(
            db, uuid4(), _user_model(UserRole.EDITOR, owner_id)
        )
        assert result is project

    async def test_denies_non_owner_non_reviewer(self) -> None:
        project = MagicMock(owner_id="owner-1", assigned_reviewer_id=None)
        db = AsyncMock()
        db.get = AsyncMock(return_value=project)
        with pytest.raises(HTTPException) as exc_info:
            await get_carousel_project_for_workflow_user(
                db, uuid4(), _user_model(UserRole.EDITOR, "intruder")
            )
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == ERR_CAROUSEL_TOOL_ACCESS_DENIED

    async def test_allows_admin(self) -> None:
        project = MagicMock(owner_id="other", assigned_reviewer_id=None)
        db = AsyncMock()
        db.get = AsyncMock(return_value=project)
        result = await get_carousel_project_for_workflow_user(
            db, uuid4(), _user_model(UserRole.ADMIN, "admin-1")
        )
        assert result is project


@pytest.mark.asyncio
class TestGetCarouselProjectForUser:
    async def test_raises_not_found(self) -> None:
        project_id = uuid4()
        db = AsyncMock()
        db.get = AsyncMock(return_value=None)
        with pytest.raises(HTTPException) as exc_info:
            await get_carousel_project_for_user(
                db, project_id, _user_model(UserRole.EDITOR)
            )
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == ERR_CAROUSEL_NOT_FOUND
        db.get.assert_awaited_once_with(CarouselProjectModel, str(project_id))

    async def test_allows_owner(self) -> None:
        owner_id = "owner-1"
        project = MagicMock(owner_id=owner_id)
        db = AsyncMock()
        db.get = AsyncMock(return_value=project)
        result = await get_carousel_project_for_user(
            db, uuid4(), _user_model(UserRole.EDITOR, owner_id)
        )
        assert result is project

    async def test_denies_non_owner(self) -> None:
        project = MagicMock(owner_id="owner-1")
        db = AsyncMock()
        db.get = AsyncMock(return_value=project)
        with pytest.raises(HTTPException) as exc_info:
            await get_carousel_project_for_user(
                db, uuid4(), _user_model(UserRole.EDITOR, "other")
            )
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == ERR_ACCESS_DENIED_NOT_OWNER


@pytest.mark.asyncio
class TestGetProjectSourceForUser:
    async def test_raises_when_source_missing(self) -> None:
        project_id = uuid4()
        source_id = uuid4()
        db = AsyncMock()
        project = MagicMock(owner_id="user-1")
        db.get = AsyncMock(side_effect=[project, None])

        with pytest.raises(HTTPException) as exc_info:
            await get_project_source_for_user(
                db,
                ProjectSourceLookup(
                    project_id=project_id,
                    source_id=source_id,
                    user=_user_model(UserRole.EDITOR, "user-1"),
                ),
            )
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == ERR_SOURCE_NOT_FOUND.format(source_id=source_id)
        assert db.get.await_args_list[1] == ((ContentSourceModel, str(source_id)),)

    async def test_raises_when_source_wrong_project(self) -> None:
        project_id = uuid4()
        source_id = uuid4()
        db = AsyncMock()
        project = MagicMock(owner_id="user-1")
        source = MagicMock(project_id=str(uuid4()))
        db.get = AsyncMock(side_effect=[project, source])

        with pytest.raises(HTTPException) as exc_info:
            await get_project_source_for_user(
                db,
                ProjectSourceLookup(
                    project_id=project_id,
                    source_id=source_id,
                    user=_user_model(UserRole.EDITOR, "user-1"),
                ),
            )
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == ERR_SOURCE_NOT_FOUND.format(source_id=source_id)

    async def test_returns_source_for_owner(self) -> None:
        project_id = uuid4()
        source_id = uuid4()
        db = AsyncMock()
        project = MagicMock(owner_id="user-1")
        source = MagicMock(project_id=str(project_id))
        db.get = AsyncMock(side_effect=[project, source])

        result = await get_project_source_for_user(
            db,
            ProjectSourceLookup(
                project_id=project_id,
                source_id=source_id,
                user=_user_model(UserRole.EDITOR, "user-1"),
            ),
        )
        assert result is source
        assert db.get.await_args_list[0] == ((CarouselProjectModel, str(project_id)),)
        assert db.get.await_args_list[1] == ((ContentSourceModel, str(source_id)),)


@pytest.mark.asyncio
class TestGetCarouselProjectForDomainUser:
    async def test_raises_not_found(self) -> None:
        project_id = uuid4()
        db = AsyncMock()
        db.get = AsyncMock(return_value=None)
        with pytest.raises(HTTPException) as exc_info:
            await get_carousel_project_for_domain_user(db, project_id, _domain_user())
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == ERR_CAROUSEL_NOT_FOUND
        db.get.assert_awaited_once_with(CarouselProjectModel, str(project_id))

    async def test_allows_owner(self) -> None:
        owner_id = uuid4()
        project = MagicMock(owner_id=str(owner_id))
        db = AsyncMock()
        db.get = AsyncMock(return_value=project)
        result = await get_carousel_project_for_domain_user(
            db, uuid4(), _domain_user(owner_id)
        )
        assert result is project

    async def test_denies_non_owner(self) -> None:
        project_id = uuid4()
        project = MagicMock(owner_id="someone-else")
        db = AsyncMock()
        db.get = AsyncMock(return_value=project)
        with pytest.raises(HTTPException) as exc_info:
            await get_carousel_project_for_domain_user(db, project_id, _domain_user())
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == ERR_ACCESS_DENIED_NOT_OWNER

    async def test_allows_admin(self) -> None:
        project = MagicMock(owner_id="someone-else")
        db = AsyncMock()
        db.get = AsyncMock(return_value=project)
        result = await get_carousel_project_for_domain_user(
            db, uuid4(), _domain_user(admin=True)
        )
        assert result is project
