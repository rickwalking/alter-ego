Feature: The public blog feed never exposes unreleased posts (AE-0449)
  The landing "Latest Posts" and the /blog list both read the public blog
  feed, so a draft, a hidden bad post or a scheduled post must never be in it.

  Scenario: Public list excludes draft, hidden and scheduled posts
    Given a public carousel with a published blog post
    And public carousels whose blog posts are a draft, a hidden bad post and a future-scheduled post
    When an anonymous client GETs /api/public/blog-posts
    Then only the published post is returned

  Scenario: Hidden and scheduled posts are a uniform 404
    Given a hidden bad post and a future-scheduled post
    When an anonymous client GETs each by id
    Then each response is 404
