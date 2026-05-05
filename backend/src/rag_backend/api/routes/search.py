"""Search API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.constants import ERR_NOT_AUTHENTICATED
from rag_backend.api.dependencies import require_authenticated_user
from rag_backend.api.schemas import (
    ErrorResponse,
    SearchRequest,
    SearchResponse,
    SearchResultResponse,
)
from rag_backend.domain.models import User
from rag_backend.infrastructure.container import get_container
from rag_backend.infrastructure.database.config import get_session

router = APIRouter(prefix="/search", tags=["search"])


@router.post(
    "",
    response_model=SearchResponse,
    responses={
        200: {"description": "Search results"},
        400: {"model": ErrorResponse, "description": "Invalid search query"},
        401: {"model": ErrorResponse, "description": ERR_NOT_AUTHENTICATED},
    },
)
async def search_documents(
    request: SearchRequest,
    user: Annotated[User, Depends(require_authenticated_user)],
    _db: Annotated[AsyncSession, Depends(get_session)],
):
    """Search for relevant documents using hybrid search.

    This endpoint performs a hybrid search combining semantic (dense vector)
    and keyword (BM25) search with Reciprocal Rank Fusion.

    Args:
        request: Search request with query and parameters

    Returns:
        List of search results ranked by relevance
    """
    container = get_container()
    retriever = container.retriever()

    try:
        from rag_backend.domain.models import RetrievalQuery

        results = await retriever.retrieve(
            RetrievalQuery(
                query=request.query,
                top_k=request.top_k,
                alpha=request.alpha,
            )
        )

        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append(
                SearchResultResponse(
                    content=result.content,
                    document_id=result.document_id,
                    document_title=result.metadata.get("title", "Untitled"),
                    score=result.score,
                    rank=result.rank,
                    metadata=result.metadata,
                )
            )

        return {
            "query": request.query,
            "results": formatted_results,
            "total": len(formatted_results),
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {e!s}",
        ) from e


@router.get(
    "",
    response_model=SearchResponse,
    responses={
        200: {"description": "Search results"},
        400: {"model": ErrorResponse, "description": "Invalid search query"},
        401: {"model": ErrorResponse, "description": ERR_NOT_AUTHENTICATED},
    },
)
async def search_documents_get(
    user: Annotated[User, Depends(require_authenticated_user)],
    query: Annotated[str, Query(min_length=1, max_length=1000, description="Search query")],
    top_k: Annotated[int, Query(ge=1, le=20, description="Number of results to return")] = 5,
    alpha: Annotated[
        float,
        Query(ge=0.0, le=1.0, description="Hybrid search balance (0=BM25, 1=semantic)"),
    ] = 0.5,
    db: AsyncSession = Depends(get_session),  # noqa: FAST002
):
    """Search for relevant documents using GET request.

    This is a convenience endpoint for simple searches.
    Use POST for more complex search scenarios.
    """
    request = SearchRequest(query=query, top_k=top_k, alpha=alpha)
    return await search_documents(request, user, db)
