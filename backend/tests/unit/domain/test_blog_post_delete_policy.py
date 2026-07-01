"""Delete-policy completeness over BlogPostOrigin (AE-0296).

Scenario: Every blog post origin has an explicit delete policy
(see features/blog_post_management_ae0296.feature).
"""

from rag_backend.domain.constants.blog_post import (
    BLOG_POST_HARD_DELETABLE_ORIGINS,
    BLOG_POST_LINK_GUARDED_ORIGINS,
    BlogPostOrigin,
)


class TestBlogPostDeletePolicy:
    def test_every_origin_has_exactly_one_delete_policy(self) -> None:
        """A new BlogPostOrigin member cannot ship without a delete policy."""
        covered = BLOG_POST_HARD_DELETABLE_ORIGINS | BLOG_POST_LINK_GUARDED_ORIGINS
        assert covered == frozenset(BlogPostOrigin)

    def test_policy_sets_are_disjoint(self) -> None:
        assert not (BLOG_POST_HARD_DELETABLE_ORIGINS & BLOG_POST_LINK_GUARDED_ORIGINS)

    def test_standalone_is_hard_deletable_and_carousel_is_guarded(self) -> None:
        assert BlogPostOrigin.STANDALONE in BLOG_POST_HARD_DELETABLE_ORIGINS
        assert BlogPostOrigin.CAROUSEL in BLOG_POST_LINK_GUARDED_ORIGINS
