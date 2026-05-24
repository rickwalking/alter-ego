"""Document API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.constants import ERR_FORBIDDEN, ERR_NOT_AUTHENTICATED
from rag_backend.api.dependencies import (
    require_authenticated_user,
    require_editor_or_admin,
)
from rag_backend.api.dependencies.resource_access import assert_document_access
from rag_backend.api.schemas import (
    DocumentCreate,
    DocumentListResponse,
    DocumentProcessingStatus,
    DocumentResponse,
    DocumentUploadResponse,
    ErrorResponse,
)
from rag_backend.domain.models import Document, DocumentScope, DocumentStatus, User
from rag_backend.infrastructure.container import get_container
from rag_backend.infrastructure.database.config import get_session
from rag_backend.infrastructure.retrieval.document_processor import load_file_content

router = APIRouter(prefix="/documents", tags=["documents"])


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
    title: str | None = None,
    tags: str | None = None,
    scope: str = "personal",
    is_public: bool = False,
    user: Annotated[User, Depends(require_editor_or_admin)] = None,
    db: AsyncSession = Depends(get_session),
):
    """Upload a document file and process it immediately.

    Accepts PDF, TXT, MD files. The document is processed through the
    full pipeline (chunking + embedding) before returning.
    """
    container = get_container()
    settings = container.settings()

    # Read file content
    raw_bytes = await file.read()

    # Check file size
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

    # Extract text based on file type
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

    # Build metadata
    metadata: dict[str, object] = {"filename": file.filename, "content_type": file.content_type}
    if tags:
        metadata["tags"] = [t.strip() for t in tags.split(",") if t.strip()]

    # Validate scope
    try:
        doc_scope = DocumentScope(scope)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid scope: {scope}. Must be one of: {', '.join(s.value for s in DocumentScope)}",
        ) from None

    # Create document entity
    document = Document(
        title=title or file.filename or "Untitled",
        content=content,
        metadata=metadata,
        scope=doc_scope,
        is_public=is_public,
        owner_id=user.id if user else None,
    )

    # Save to database
    repo = container.document_repository(session=db)
    created_doc = await repo.create(document)
    await db.commit()

    # Process through pipeline immediately
    pipeline = container.document_pipeline(db_session=db)
    try:
        processed_doc = await pipeline.process_document(created_doc)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process document: {e!s}",
        ) from e

    return processed_doc


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
    db: Annotated[AsyncSession, Depends(get_session)],
):
    """Create a new document and start processing.

    The document will be queued for processing (chunking and embedding generation).
    Check the status field to track progress.
    """
    container = get_container()

    # Validate scope
    try:
        doc_scope = DocumentScope(request.scope)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid scope: {request.scope}. Must be one of: {', '.join(s.value for s in DocumentScope)}",
        ) from None

    # Create document entity
    document = Document(
        title=request.title,
        content=request.content,
        metadata=request.metadata,
        scope=doc_scope,
        is_public=request.is_public,
        owner_id=user.id,
    )

    # Save to database
    repo = container.document_repository(session=db)
    created_doc = await repo.create(document)
    await db.commit()

    # Start async processing (in production, this would be a background task)
    # For now, we'll return immediately with pending status
    # The actual processing would be triggered by a background job

    return created_doc


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
    status: Annotated[DocumentStatus | None, Query(description="Filter by status")] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Number of items to return")] = 20,
    offset: Annotated[int, Query(ge=0, description="Number of items to skip")] = 0,
    db: AsyncSession = Depends(get_session),
):
    """List all documents with optional filtering.

    Documents are ordered by updated_at in descending order.
    """
    container = get_container()
    repo = container.document_repository(session=db)

    if user.is_admin():
        documents = await repo.get_all(status=status, limit=limit, offset=offset)
        total = await repo.count(status=status)
    else:
        documents = await repo.get_all_for_owner(
            owner_id=user.id,
            status=status,
            limit=limit,
            offset=offset,
        )
        total = await repo.count_for_owner(owner_id=user.id, status=status)

    return {
        "items": documents,
        "total": total,
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
    db: Annotated[AsyncSession, Depends(get_session)],
):
    """Get a single document by ID."""
    container = get_container()
    repo = container.document_repository(session=db)

    document = await repo.get_by_id(document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with id {document_id} not found",
        )

    assert_document_access(document, user)
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
    db: Annotated[AsyncSession, Depends(get_session)],
):
    """Get document processing status and estimates."""
    container = get_container()
    repo = container.document_repository(session=db)

    document = await repo.get_by_id(document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with id {document_id} not found",
        )

    assert_document_access(document, user)

    # Get pipeline for estimation
    pipeline = container.document_pipeline(db_session=db)
    estimates = pipeline.estimate_processing_time(document)

    return {
        "id": document.id,
        "status": document.status.value,
        "chunk_count": document.chunk_count,
        "estimated_chunks": estimates["estimated_chunks"],
        "estimated_time_seconds": estimates["total_time_seconds"],
    }


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
    db: Annotated[AsyncSession, Depends(get_session)],
):
    """Delete a document and all its associated data.

    This will remove the document from the database and delete all
    associated vectors from the vector store.
    """
    container = get_container()
    repo = container.document_repository(session=db)
    document = await repo.get_by_id(document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with id {document_id} not found",
        )

    assert_document_access(document, user)
    pipeline = container.document_pipeline(db_session=db)

    success = await pipeline.delete_document(str(document_id))
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with id {document_id} not found",
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
    db: Annotated[AsyncSession, Depends(get_session)],
):
    """Reprocess a document.

    This will delete existing vectors and regenerate chunks and embeddings.
    """
    container = get_container()
    repo = container.document_repository(session=db)
    document = await repo.get_by_id(document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with id {document_id} not found",
        )

    assert_document_access(document, user)
    pipeline = container.document_pipeline(db_session=db)

    try:
        return await pipeline.reprocess_document(str(document_id))
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
