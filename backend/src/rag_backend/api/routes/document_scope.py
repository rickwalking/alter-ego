"""Document scope route — move a knowledge document between personal and public.

A thin HTTP adapter over the knowledge facade: it parses the requested scope,
enforces the owner-or-admin check on the document, and delegates the move (old
namespace chunks dropped, re-indexed under the new scope) to
:meth:`KnowledgeService.change_scope`, which commits through its Unit of Work.
"""

from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from rag_backend.api.constants import ERR_FORBIDDEN, ERR_NOT_AUTHENTICATED
from rag_backend.api.dependencies import require_editor_or_admin
from rag_backend.api.dependencies.knowledge import get_knowledge_service
from rag_backend.api.dependencies.resource_access import assert_domain_owner_or_admin
from rag_backend.api.schemas import DocumentResponse, ErrorResponse
from rag_backend.api.schemas.documents import DocumentScopeChange
from rag_backend.domain.models import DocumentScope, User
from rag_backend.modules.knowledge import (
    ChangeDocumentScopeCommand,
    GetDocumentQuery,
    KnowledgeService,
)

router = APIRouter(prefix="/documents", tags=["documents"])

SELECTABLE_SCOPES: tuple[DocumentScope, ...] = (
    DocumentScope.PERSONAL,
    DocumentScope.PUBLIC,
)
"""The scopes an owner may choose for a document (the others are system scopes)."""

_DETAIL_NOT_FOUND = "Document with id {document_id} not found"
_DETAIL_INVALID_SCOPE = "Invalid scope: {scope}. Must be one of: {choices}"


def _selectable_scope(scope: str) -> DocumentScope:
    """The chosen scope, or 400 when it is not one an owner may pick."""
    for candidate in SELECTABLE_SCOPES:
        if candidate.value == scope:
            return candidate
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=_DETAIL_INVALID_SCOPE.format(
            scope=scope,
            choices=", ".join(choice.value for choice in SELECTABLE_SCOPES),
        ),
    )


def _not_found(document_id: UUID) -> HTTPException:
    """The 404 for a document that does not exist."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=_DETAIL_NOT_FOUND.format(document_id=document_id),
    )


@dataclass(frozen=True)
class DocumentScopeCtx:
    """The signed-in editor and the request-scoped knowledge facade."""

    user: User
    service: KnowledgeService


def get_document_scope_ctx(
    user: Annotated[User, Depends(require_editor_or_admin)],
    service: Annotated[KnowledgeService, Depends(get_knowledge_service)],
) -> DocumentScopeCtx:
    """Resolve the write context (auth enforced by the dependency)."""
    return DocumentScopeCtx(user=user, service=service)


@router.patch(
    "/{document_id}/scope",
    response_model=DocumentResponse,
    responses={
        200: {"description": "Document moved to the scope and re-indexed"},
        400: {"model": ErrorResponse, "description": "Scope not selectable"},
        401: {"model": ErrorResponse, "description": ERR_NOT_AUTHENTICATED},
        403: {"model": ErrorResponse, "description": ERR_FORBIDDEN},
        404: {"model": ErrorResponse, "description": "Document not found"},
    },
)
async def change_document_scope(
    document_id: UUID,
    request: DocumentScopeChange,
    ctx: Annotated[DocumentScopeCtx, Depends(get_document_scope_ctx)],
) -> DocumentResponse:
    """Move a document to ``personal`` or ``public`` and re-index it there.

    The same scope returns the document unchanged; any other scope is 400, a
    missing document 404, and a document of someone else 403 (admins excepted).
    """
    scope = _selectable_scope(request.scope)
    document = await ctx.service.get(GetDocumentQuery(document_id=document_id))
    if document is None:
        raise _not_found(document_id)
    assert_domain_owner_or_admin(document.owner_id, ctx.user)
    moved = await ctx.service.change_scope(
        ChangeDocumentScopeCommand(document_id=document_id, scope=scope)
    )
    if moved is None:
        raise _not_found(document_id)
    return DocumentResponse.model_validate(moved)
