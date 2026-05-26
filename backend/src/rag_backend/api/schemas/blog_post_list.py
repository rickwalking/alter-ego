"""Query parameters for blog post listing."""

from pydantic import BaseModel, Field

BLOG_SEARCH_MAX_LENGTH = 255


class BlogPostListParams(BaseModel):
    """Filters and pagination for blog post list endpoint."""

    status: str | None = None
    author_id: str | None = None
    search: str | None = Field(None, max_length=BLOG_SEARCH_MAX_LENGTH)
    limit: int = Field(50, ge=1, le=100)
    offset: int = Field(0, ge=0)


__all__ = ["BlogPostListParams"]
