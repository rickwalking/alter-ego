"""Document API routes — thin HTTP adapters over the knowledge facade.

Each endpoint parses the HTTP request into a knowledge command/query, delegates
to the request-scoped :class:`KnowledgeService` facade (resolved via the
``get_knowledge_service`` DI provider at the edge — never ``get_container()``
here), and maps the returned view back onto the HTTP response/status. Document
writes commit through the facade's Unit of Work (the single commit owner); the
routes never call ``db.commit()`` (AE-0091/0092).
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status

from rag_backend.api.constants import ERR_FORBIDDEN, ERR_NOT_AUTHENTICATED
from rag_backend.api.dependencies import (
    require_authenticated_user,
    require_editor_or_admin,
)
from rag_backend.api.dependencies.knowledge import get_knowledge_service
from rag_backend.api.dependencies.resource_access import assert_domain_owner_or_admin
from rag_backend.api.schemas import (
    DocumentCreate,
    DocumentListResponse,
    DocumentProcessingStatus,
    DocumentResponse,
    DocumentUploadResponse,
    ErrorResponse,
)
from rag_backend.domain.models import Document, DocumentScope, DocumentStatus, User
from rag_backend.infrastructure.config.settings import Settings, get_settings
from rag_backend.infrastructure.retrieval.document_processor import load_file_content
from rag_backend.modules.knowledge import (
    CreateDocumentCommand,
    DeleteDocumentCommand,
    DocumentStatusQuery,
    GetDocumentQuery,
    IngestDocumentCommand,
    KnowledgeDocumentView,
    KnowledgeService,
    ListDocumentsQuery,
    ReprocessDocumentCommand,
)
from rag_backend.modules.knowledge.domain.commands import MetadataValue

router = APIRouter(prefix="/documents", tags=["documents"])

_DETAIL_NOT_FOUND = "Document with id {document_id} not found"


def _parse_scope(scope: str) -> DocumentScope:
    """Map a scope string to the enum, raising 400 on an unknown value."""
    try:
        return DocumentScope(scope)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid scope: {scope}. Must be one of: "
            f"{', '.join(s.value for s in DocumentScope)}",
        ) from None


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Document uploaded and processed successfully"},
        400: {"model": ErrorResponse, "description": "Invalid file or input"},
        401: {"model": ErrorResponse, "description": ERR_NOT_AUTHENTICATED},
        403: {"model": ErrorResponse, "description": ERR_FORBIDDEN},
        413: {"model": ErrorResponse, "description": "File too large"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def upload_document(
    file: UploadFile,
    service: Annotated[KnowledgeService, Depends(get_knowledge_service)],
    user: Annotated[User, Depends(require_editor_or_admin)],
    settings: Annotated[Settings, Depends(get_settings)],
    title: str | None = None,
    tags: str | None = None,
    scope: str = "personal",
    is_public: bool = False,
):
    """Upload a document file and process it immediately.

    Accepts PDF, TXT, MD files. The document is processed through the
    full pipeline (chunking + embedding) before returning.
    """
    content = await _read_upload_content(file, settings)
    metadata = _build_upload_metadata(file, tags)
    doc_scope = _parse_scope(scope)

    command = IngestDocumentCommand(
        title=title or file.filename or "Untitled",
        content=content,
        metadata=metadata,
        scope=doc_scope,
        is_public=is_public,
        owner_id=user.id if user else None,
    )
    try:
        return await service.ingest(command)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process document: {e!s}",
        ) from e


async def _read_upload_content(file: UploadFile, settings: Settings) -> str:
    """Validate the upload (size/empty/type) and extract its text content."""
    raw_bytes = await file.read()

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(raw_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {settings.max_upload_size_mb}MB",
        )
    if not raw_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )
    try:
        content = load_file_content(raw_bytes, file.filename or "unknown")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read file content: {e!s}",
        ) from e
    if not content.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No text content could be extracted from the file",
        )
    return content


def _build_upload_metadata(
    file: UploadFile, tags: str | None
) -> dict[str, MetadataValue]:
    """Build the document metadata from the upload's filename/content-type/tags."""
    metadata: dict[str, MetadataValue] = {
        "filename": file.filename or "",
        "content_type": file.content_type or "",
    }
    if tags:
        metadata["tags"] = ",".join(t.strip() for t in tags.split(",") if t.strip())
    return metadata


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Document created successfully"},
        400: {"model": ErrorResponse, "description": "Invalid input"},
        401: {"model": ErrorResponse, "description": ERR_NOT_AUTHENTICATED},
        403: {"model": ErrorResponse, "description": ERR_FORBIDDEN},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def create_document(
    request: DocumentCreate,
    user: Annotated[User, Depends(require_editor_or_admin)],
    service: Annotated[KnowledgeService, Depends(get_knowledge_service)],
):
    """Create a new document and start processing.

    The document will be queued for processing (chunking and embedding generation).
    Check the status field to track progress.
    """
    doc_scope = _parse_scope(request.scope)
    command = CreateDocumentCommand(
        title=request.title,
        content=request.content,
        metadata=_to_metadata(request.metadata),
        scope=doc_scope,
        is_public=request.is_public,
        owner_id=user.id,
    )
    return await service.create(command)


@router.get(
    "",
    response_model=DocumentListResponse,
    responses={
        200: {"description": "List of documents"},
        401: {"model": ErrorResponse, "description": ERR_NOT_AUTHENTICATED},
    },
)
async def list_documents(
    user: Annotated[User, Depends(require_authenticated_user)],
    service: Annotated[KnowledgeService, Depends(get_knowledge_service)],
    status: Annotated[
        DocumentStatus | None, Query(description="Filter by status")
    ] = None,
    limit: Annotated[
        int, Query(ge=1, le=100, description="Number of items to return")
    ] = 20,
    offset: Annotated[int, Query(ge=0, description="Number of items to skip")] = 0,
):
    """List all documents with optional filtering.

    Documents are ordered by updated_at in descending order.
    """
    page = await service.list_with_total(
        ListDocumentsQuery(
            status=status,
            limit=limit,
            offset=offset,
            owner_id=user.id,
            is_admin=user.is_admin(),
        )
    )
    return {
        "items": page.items,
        "total": page.total,
        "limit": limit,
        "offset": offset,
    }


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    responses={
        200: {"description": "Document found"},
        401: {"model": ErrorResponse, "description": ERR_NOT_AUTHENTICATED},
        403: {"model": ErrorResponse, "description": ERR_FORBIDDEN},
        404: {"model": ErrorResponse, "description": "Document not found"},
    },
)
async def get_document(
    document_id: UUID,
    user: Annotated[User, Depends(require_authenticated_user)],
    service: Annotated[KnowledgeService, Depends(get_knowledge_service)],
):
    """Get a single document by ID."""
    document = await service.get(GetDocumentQuery(document_id=document_id))
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_DETAIL_NOT_FOUND.format(document_id=document_id),
        )
    _assert_view_access(document, user)
    return document


@router.get(
    "/{document_id}/status",
    response_model=DocumentProcessingStatus,
    responses={
        200: {"description": "Processing status"},
        401: {"model": ErrorResponse, "description": ERR_NOT_AUTHENTICATED},
        404: {"model": ErrorResponse, "description": "Document not found"},
    },
)
async def get_document_status(
    document_id: UUID,
    user: Annotated[User, Depends(require_authenticated_user)],
    service: Annotated[KnowledgeService, Depends(get_knowledge_service)],
):
    """Get document processing status and estimates."""
    document = await service.get(GetDocumentQuery(document_id=document_id))
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_DETAIL_NOT_FOUND.format(document_id=document_id),
        )
    _assert_view_access(document, user)

    estimate = await service.status(DocumentStatusQuery(document_id=document_id))
    if estimate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_DETAIL_NOT_FOUND.format(document_id=document_id),
        )
    return estimate


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Document deleted successfully"},
        401: {"model": ErrorResponse, "description": ERR_NOT_AUTHENTICATED},
        403: {"model": ErrorResponse, "description": ERR_FORBIDDEN},
        404: {"model": ErrorResponse, "description": "Document not found"},
    },
)
async def delete_document(
    document_id: UUID,
    user: Annotated[User, Depends(require_authenticated_user)],
    service: Annotated[KnowledgeService, Depends(get_knowledge_service)],
):
    """Delete a document and all its associated data.

    This will remove the document from the database and delete all
    associated vectors from the vector store.
    """
    document = await service.get(GetDocumentQuery(document_id=document_id))
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_DETAIL_NOT_FOUND.format(document_id=document_id),
        )
    _assert_view_access(document, user)

    success = await service.delete(DeleteDocumentCommand(document_id=document_id))
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_DETAIL_NOT_FOUND.format(document_id=document_id),
        )


@router.post(
    "/{document_id}/reprocess",
    response_model=DocumentResponse,
    responses={
        200: {"description": "Document reprocessing started"},
        401: {"model": ErrorResponse, "description": ERR_NOT_AUTHENTICATED},
        403: {"model": ErrorResponse, "description": ERR_FORBIDDEN},
        404: {"model": ErrorResponse, "description": "Document not found"},
    },
)
async def reprocess_document(
    document_id: UUID,
    user: Annotated[User, Depends(require_authenticated_user)],
    service: Annotated[KnowledgeService, Depends(get_knowledge_service)],
):
    """Reprocess a document.

    This will delete existing vectors and regenerate chunks and embeddings.
    """
    document = await service.get(GetDocumentQuery(document_id=document_id))
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_DETAIL_NOT_FOUND.format(document_id=document_id),
        )
    _assert_view_access(document, user)
    try:
        return await service.reprocess(
            ReprocessDocumentCommand(document_id=document_id)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


def _assert_view_access(document: KnowledgeDocumentView, user: User) -> None:
    """Enforce the legacy owner-or-admin document access check on a view.

    Keys off the document's ``owner_id`` exactly like the pre-refactor route's
    ``assert_document_access`` (ownership ignores ``is_public``), preserving the
    safety net's 403 semantics.
    """
    assert_domain_owner_or_admin(document.owner_id, user)


def _to_metadata(metadata: dict[str, object]) -> dict[str, MetadataValue]:
    """Coerce request metadata to the boundary-safe scalar value type."""
    result: dict[str, MetadataValue] = {}
    for key, value in metadata.items():
        if isinstance(value, str | int | float | bool):
            result[key] = value
        else:
            result[key] = str(value)
    return result


# Re-exported for backwards compatibility with callers importing the entity here.
__all__ = ["Document", "router"]
