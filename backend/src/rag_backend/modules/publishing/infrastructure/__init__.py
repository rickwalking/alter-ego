"""Infrastructure layer for the publishing bounded context.

Private to the module. AE-0126 is scaffolding only: no persistence adapter,
distribution extraction, or outbox is relocated here yet. The concrete
:class:`~rag_backend.infrastructure.database.blog_post_repository.BlogPostRepository`
and the carousel persistence adapter stay at their legacy locations and are
supplied to ``bootstrap_module`` by the inbound edge as the re-exported
repository ports (object-identity shims; see ``domain.ports``). Adapter
relocation + the additive outbox land in AE-0128..0130.
"""
