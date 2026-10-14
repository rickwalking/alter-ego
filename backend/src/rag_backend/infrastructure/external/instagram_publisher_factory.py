"""Build the Graph publisher from process settings."""

from __future__ import annotations

from rag_backend.domain.protocols.instagram_token import InstagramTokenProvider
from rag_backend.infrastructure.config.settings import Settings
from rag_backend.infrastructure.external.meta_instagram_publisher import (
    MetaInstagramPublisher,
    MetaInstagramPublisherConfig,
)


def build_meta_instagram_publisher(settings: Settings) -> MetaInstagramPublisher:
    """User id, Graph host, and the encrypted-store token provider."""
    return MetaInstagramPublisher(
        MetaInstagramPublisherConfig(
            ig_user_id=settings.meta_ig_user_id,
            graph_base=settings.meta_ig_graph_base,
            token_provider=token_provider_for(settings),
        )
    )


def token_provider_for(settings: Settings) -> InstagramTokenProvider:
    """The encrypted credential store. Tests may replace this function."""
    from rag_backend.modules.autopilot import build_stored_instagram_token_provider

    key = settings.credentials_encryption_key.get_secret_value()
    return build_stored_instagram_token_provider(key)
