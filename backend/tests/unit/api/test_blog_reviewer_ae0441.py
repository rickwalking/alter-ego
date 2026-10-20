"""Unit tests: the blog reviewer resolution (AE-0441).

Feature: backend/tests/features/blog_post_ai_contract_ae0424.feature
(review section: the author may review their own post).
"""

from rag_backend.api.routes.blog_post_workflow import resolve_blog_reviewer


class TestResolveBlogReviewer:
    # Scenario: Submit review moves a draft to under_review (distinct reviewer)
    def test_keeps_the_requested_reviewer(self) -> None:
        assert resolve_blog_reviewer("rev-1", "author-1", "user-1") == "rev-1"

    # Scenario: The author may name themselves as the reviewer
    def test_accepts_the_author_as_reviewer(self) -> None:
        assert resolve_blog_reviewer("author-1", "author-1", "user-1") == "author-1"

    # Scenario: Submit review without a reviewer assigns the author
    def test_defaults_to_the_author(self) -> None:
        assert resolve_blog_reviewer(None, "author-1", "user-1") == "author-1"

    def test_falls_back_to_the_current_user_without_an_author(self) -> None:
        assert resolve_blog_reviewer(None, None, "user-1") == "user-1"
