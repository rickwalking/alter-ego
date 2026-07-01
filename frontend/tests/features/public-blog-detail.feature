Feature: Public blog detail resolves real posts (AE-0297, ADR-0013)
  The public URL /blog/{id} serves blog_posts records through the lean public
  API, keeps legacy carousel-projection URLs working, and never 404s a
  published post for missing design tokens.

  Scenario: Published standalone post renders publicly with the default theme
    Given a published standalone blog post with id X
    When an anonymous visitor opens /blog/X
    Then the post content is rendered with the default public theme
    And the response is not a 404

  Scenario: Published carousel-origin post renders with its design tokens
    Given a published carousel-origin post whose project has design tokens
    When an anonymous visitor opens /blog/{post id}
    Then the post renders through the carousel design path

  Scenario: Carousel-origin post with unreachable design still renders
    Given a published carousel-origin post whose design fetch fails
    When an anonymous visitor opens /blog/{post id}
    Then the post renders with the default public theme instead of 404ing

  Scenario: Legacy carousel project URL keeps working
    Given a public carousel project id used as /blog/{project id}
    When an anonymous visitor opens it
    Then the carousel projection renders as before

  Scenario: Hidden post is not publicly viewable
    Given a blog post that has been hidden/unpublished
    When an anonymous visitor opens /blog/{that id}
    Then the page returns not-found

  Scenario: Unknown id returns not-found
    Given an id that matches no post or projection
    When an anonymous visitor opens /blog/{id}
    Then the page returns not-found

  Scenario: Listing prefers the public feed and falls open to the carousel feed
    Given the public blog feed is available
    Then listing cards come from published blog posts (carousel-origin enriched)
    Given the public blog feed errors
    Then the listing falls back to the existing public carousel feed

  Scenario: Server-side base URL is overridable for production
    Given API_BASE_URL is set server-side
    Then server fetches resolve against it instead of the Docker-internal default
