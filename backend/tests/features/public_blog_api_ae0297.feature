Feature: Public blog-post read API (AE-0297, ADR-0013)
  A dedicated public, unauthenticated, published-only, lean-schema read
  surface serves the public site; the private/admin surface keeps full detail
  including drafts.

  Scenario: Public list returns only published posts
    Given posts exist in every workflow status
    When an anonymous client GETs /api/public/blog-posts
    Then only published posts are returned
    And they are ordered by published_at descending

  Scenario: Public list ignores client status filters
    Given a draft post exists
    When an anonymous client GETs /api/public/blog-posts?status=draft
    Then the draft is not returned

  Scenario: Published post is publicly readable
    Given a published blog post
    When an anonymous client GETs /api/public/blog-posts/{id}
    Then the response is 200 with the lean public payload

  Scenario Outline: Uniform 404 for every non-published state
    Given a blog post with status "<status>"
    When an anonymous client GETs /api/public/blog-posts/{id}
    Then the response is 404 (no existence leak, never 403/410)

    Examples:
      | status       |
      | draft        |
      | under_review |
      | approved     |
      | archived     |

  Scenario: Unknown id returns the same uniform 404
    When an anonymous client GETs /api/public/blog-posts/{random uuid}
    Then the response is 404

  Scenario: Lean payload never contains internal fields (recursive)
    Given a published post rich in internal fields
    When the public list and detail payloads are serialized
    Then none of the excluded key names appear anywhere in the JSON
      (status, author_id, reviewer_id, editor_comments, version_history,
       ai_suggestions, ai_generation_metadata, lock_version, distribution,
       sources, citations, view_count)

  Scenario: Responses are not cached
    When an anonymous client GETs the public list or detail
    Then the Cache-Control header is "no-store"

  Scenario: The public route resolves no user identity
    Given the FastAPI dependency tree of the public routes
    When it is inspected recursively
    Then no auth/role dependency is present

  Scenario: Authenticated editors get the identical anonymous payload
    Given a published post and an editor with a valid token
    When the editor GETs the public detail with Authorization
    Then the payload is byte-identical to the anonymous payload
    And their own draft still returns 404 on the public route

  Scenario: Private admin surface still returns drafts
    Given an editor with a draft post
    When they GET /api/blog-posts
    Then the draft is included with full detail

  Scenario: Public reads are rate limited
    Given the committed public rate limit
    Then it is at most 120 requests per minute per IP
