"""Search API routes — thin HTTP adapter over the knowledge facade.

The endpoints parse the HTTP request into a knowledge :class:`SearchQuery`,
delegate to the request-scoped :class:`KnowledgeService` facade (resolved via the
``get_knowledge_service`` DI provider at the edge — the route never resolves the
DI container itself), and map the returned ``SearchResultView`` list back onto
the HTTP response. Hybrid-search semantics (RRF, namespaces, ``alpha``/``top_k``) live
behind the facade and are unchanged; the response stays byte-identical to the
pre-refactor route (AE-0093).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from rag_backend.api.constants import ERR_NOT_AUTHENTICATED
from rag_backend.api.dependencies import require_authenticated_user
from rag_backend.api.dependencies.knowledge import get_knowledge_service
from rag_backend.api.schemas import (
    ErrorResponse,
    SearchRequest,
    SearchResponse,
    SearchResultResponse,
)
from rag_backend.domain.models import User
from rag_backend.modules.knowledge import (
    KnowledgeService,
    SearchQuery,
    SearchResultView,
)

router = APIRouter(prefix="/search", tags=["search"])

_DEFAULT_DOCUMENT_TITLE = "Untitled"
_TITLE_METADATA_KEY = "title"


def _to_result_response(result: SearchResultView) -> SearchResultResponse:
    """Map a knowledge ``SearchResultView`` onto the HTTP response shape.

    Derives ``document_title`` from the result metadata exactly like the
    pre-refactor route (``metadata.get("title", "Untitled")``).
    """
    title = result.metadata.get(_TITLE_METADATA_KEY, _DEFAULT_DOCUMENT_TITLE)
    return SearchResultResponse(
        content=result.content,
        document_id=result.document_id,
        document_title=str(title),
        score=result.score,
        rank=result.rank,
        metadata=dict(result.metadata),
    )


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
    service: Annotated[KnowledgeService, Depends(get_knowledge_service)],
):
    """Search for relevant documents using hybrid search.

    This endpoint performs a hybrid search combining semantic (dense vector)
    and keyword (BM25) search with Reciprocal Rank Fusion.

    Args:
        request: Search request with query and parameters

    Returns:
        List of search results ranked by relevance
    """
    try:
        results = await service.search(
            SearchQuery(
                query=request.query,
                top_k=request.top_k,
                alpha=request.alpha,
            )
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {e!s}",
        ) from e

    formatted_results = [_to_result_response(result) for result in results]
    return {
        "query": request.query,
        "results": formatted_results,
        "total": len(formatted_results),
    }


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
    service: Annotated[KnowledgeService, Depends(get_knowledge_service)],
    query: Annotated[
        str, Query(min_length=1, max_length=1000, description="Search query")
    ],
    top_k: Annotated[
        int, Query(ge=1, le=20, description="Number of results to return")
    ] = 5,
    alpha: Annotated[
        float,
        Query(ge=0.0, le=1.0, description="Hybrid search balance (0=BM25, 1=semantic)"),
    ] = 0.5,
):
    """Search for relevant documents using GET request.

    This is a convenience endpoint for simple searches.
    Use POST for more complex search scenarios.
    """
    request = SearchRequest(query=query, top_k=top_k, alpha=alpha)
    return await search_documents(request, user, service)
