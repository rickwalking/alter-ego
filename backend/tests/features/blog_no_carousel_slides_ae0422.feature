# AE-0422 (A) — the carousel write path stops creating/overwriting/publishing blog posts.
# The public rendering half is in frontend/tests/features/blog_no_carousel_slides_ae0422.feature
# (ADR-0025: carousel-origin posts are always drafts, created on demand).
# A ships before the v2 model (B), so the fixtures here are deliberately legacy/arbitrary content.

Feature: Carousel saves never touch blog posts

  Background:
    Given a carousel project with generated slides

  Scenario: Saving a carousel without a blog row does not create one
    Given the project has no blog_posts row
    When the carousel is saved twice
    Then there is still no blog_posts row for the project

  Scenario: Saving a carousel does not overwrite an existing row
    Given the project has a blog_posts row with legacy markdown content
    And its status is "draft"
    When the carousel is saved
    Then the blog content is unchanged byte-for-byte
    And the status is still "draft"

  Scenario: Saving a hidden post does not re-publish it
    Given the project's blog_posts row was hidden (status "draft" + hidden_bad_post marker)
    When the carousel is saved
    Then the status is still "draft"
    And the hidden_bad_post marker is still present

  Scenario: Every published carousel-origin post is hidden, regardless of body length
    Given a published carousel-origin post with a long, apparently healthy body
    When the hide action runs
    Then the status becomes "draft"
    And the publish stamps are cleared
    And a blog status event is emitted
    And ai_generation_metadata.hidden_bad_post = {at, reason}
    And running the hide action again is a no-op

  Scenario: A published standalone post is not hidden
    Given a published post whose origin is "standalone"
    When the hide action runs
    Then its status remains "published"
    And it has no hidden_bad_post marker

  Scenario: Deleting a carousel still drafts its blog row
    Given the project has a published blog_posts row
    When the carousel is deleted
    Then the blog_posts row survives with its project link cleared
    And its status is "draft"

  # The public-visibility half: hiding a post must also stop the legacy
  # project-id URL from serving it to anonymous visitors (ADR-0013 uniform 404).
  Scenario: An anonymous visitor cannot read a hidden carousel post at the legacy URL
    Given the project's blog_posts row is "draft"
    When an anonymous client requests the legacy carousel blog URL
    Then the response is 404

  Scenario: An anonymous visitor cannot read a hidden carousel post in a language
    Given the project's blog_posts row is "draft"
    When an anonymous client requests the legacy carousel blog language URL
    Then the response is 404

  Scenario: An anonymous visitor can read a published carousel post at the legacy URL
    Given the project's blog_posts row is "published"
    When an anonymous client requests the legacy carousel blog URL
    Then the response is 200

  Scenario: An authenticated editor still previews a hidden carousel post
    Given the project's blog_posts row is "draft"
    When the owner requests the legacy carousel blog URL
    Then the response is 200
