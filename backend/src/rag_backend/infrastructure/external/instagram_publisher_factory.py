"""Build the Graph publisher from process settings."""

from __future__ import annotations

from rag_backend.infrastructure.config.settings import Settings
from rag_backend.infrastructure.external.instagram_token import (
    StaticInstagramTokenProvider,
)
from rag_backend.infrastructure.external.meta_instagram_publisher import (
    MetaInstagramPublisher,
    MetaInstagramPublisherConfig,
)


def build_meta_instagram_publisher(settings: Settings) -> MetaInstagramPublisher:
    """User id, Graph host, and the static token provider."""
    return MetaInstagramPublisher(
        MetaInstagramPublisherConfig(
            ig_user_id=settings.meta_ig_user_id,
            graph_base=settings.meta_ig_graph_base,
            token_provider=StaticInstagramTokenProvider(settings.meta_ig_access_token),
        )
    )
