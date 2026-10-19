Feature: Public blog detail resolves real posts (AE-0297, ADR-0013)
  The public URL /blog/{id} serves blog_posts records through the lean public
  API and never 404s a published post for missing design tokens.
  AE-0423 / ADR-0025: the page renders only the post's own blog.v2 document; the
  carousel is read for theme tokens only, and the legacy /blog/{project id}
  carousel-projection URL is retired (see blog_sections_ae0423.feature).

  Scenario: Published standalone post renders publicly with the default theme
    Given a published standalone blog post with id X
    When an anonymous visitor opens /blog/X
    Then the post content is rendered with the default public theme
    And the response is not a 404

  Scenario: Published carousel-origin post renders with its design tokens
    Given a published carousel-origin post whose project has design tokens
    When an anonymous visitor opens /blog/{post id}
    Then the post renders its own blog.v2 document themed by the carousel design tokens

  Scenario: Carousel-origin post with unreachable design still renders
    Given a published carousel-origin post whose design fetch fails
    When an anonymous visitor opens /blog/{post id}
    Then the post renders with the default public theme instead of 404ing

  # SUPERSEDED by AE-0423 / ADR-0025 ("A carousel-origin post with no v2 row is
  # 404" in blog_sections_ae0423.feature): the carousel projection is no longer a
  # public blog read path.
  Scenario: Legacy carousel project URL is retired
    Given a public carousel project id used as /blog/{project id}
    And no published blog_posts row has that id
    When an anonymous visitor opens it
    Then the page returns not-found

  Scenario: Hidden post is not publicly viewable
    Given a blog post that has been hidden/unpublished
    When an anonymous visitor opens /blog/{that id}
    Then the page returns not-found

  Scenario: Unknown id returns not-found
    Given an id that matches no post or projection
    When an anonymous visitor opens /blog/{id}
    Then the page returns not-found

  # AE-0423 / ADR-0025: the fall-open to the carousel feed is SUPERSEDED — its
  # cards linked /blog/{project id}, which is no longer a readable URL.
  Scenario: Listing comes from the public feed only
    Given the public blog feed is available
    Then listing cards come from published blog posts (carousel-origin enriched)
    And each card image is the post's own cover, or none when the cover is null
    Given the public blog feed errors
    Then the listing renders no cards (no dead project-id links)

  Scenario: Server-side base URL is overridable for production
    Given API_BASE_URL is set server-side
    Then server fetches resolve against it instead of the Docker-internal default
