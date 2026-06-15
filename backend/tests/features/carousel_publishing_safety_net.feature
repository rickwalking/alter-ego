Feature: Publishing byte-identical safety net (AE-0125)
  As the team refactoring the publishing surface in Phase 6
  I want committed byte-identical baselines for blog / publish / distribution /
  calendar / board / analytics responses
  So that the facade extraction, additive migration and outbox cannot silently
  change a response (AE-0128 / AE-0129 / AE-0131 diff against these baselines)

  Background:
    Given DEBUG and the carousel public base URL are pinned for determinism
    And external channels (Meta/Instagram, LLM) are deterministically stubbed

  # --- Blog-post CRUD ---------------------------------------------------------
  Scenario: blog post create response unchanged
    When the POST /api/blog-posts endpoint runs
    Then the response is 201 and matches the committed snapshot

  Scenario: blog post get response unchanged
    Given a created blog post
    When the GET /api/blog-posts/{id} endpoint runs
    Then the response is 200 and matches the committed snapshot

  Scenario: blog post list response unchanged
    Given a created blog post
    When the GET /api/blog-posts endpoint runs
    Then the response is 200 and matches the committed snapshot

  Scenario: blog post update requires the If-Match version header
    Given a created blog post
    When the PUT /api/blog-posts/{id} endpoint runs without If-Match
    Then the response is 428

  Scenario: blog post update response unchanged with a valid version
    Given a created blog post
    When the PUT /api/blog-posts/{id} endpoint runs with If-Match 1
    Then the response is 200, the lock version is bumped, and it matches the snapshot

  Scenario: blog post delete returns 204 and removes the post
    Given a created blog post
    When the DELETE /api/blog-posts/{id} endpoint runs
    Then the response is 204 and the post is no longer retrievable

  # --- Public carousel blog ---------------------------------------------------
  Scenario: public carousel blog response unchanged
    Given a public carousel with generated blog content
    When GET /api/carousels/{id}/blog runs
    Then the response is 200 and matches the committed snapshot

  Scenario: carousel blog is hidden for a non-public carousel
    Given a non-public carousel
    When GET /api/carousels/{id}/blog runs
    Then the response is 404

  Scenario: i18n carousel blog response unchanged for English
    Given a public carousel with English translations
    When GET /api/carousels/{id}/blog/en runs
    Then the response is 200 and matches the committed snapshot

  # --- Distribution: caption + Instagram publish ------------------------------
  Scenario: generate-caption returns the persisted caption without an LLM call
    Given a carousel with a persisted caption approved for release
    When POST /api/carousels/{id}/caption runs
    Then the response is 200 and matches the committed snapshot

  Scenario: publish to Instagram returns the stubbed published result
    Given a carousel approved for release and a stubbed Instagram publisher
    When POST /api/carousels/{id}/publish/instagram runs
    Then the response is 200 with the stubbed post id and matches the snapshot
    And the route built public image URLs from the pinned base URL

  Scenario: publish to Instagram is forbidden when not approved for release
    Given a carousel that is not approved for release
    When POST /api/carousels/{id}/publish/instagram runs
    Then the response is 403

  # --- Publish flow: approval -> is_public release (current behavior) ---------
  Scenario: publish marks the carousel public (current release flow)
    Given a carousel approved for release that is not yet public
    When POST /api/carousels/{id}/publish runs
    Then the response is 200, is_public is true, and it matches the committed snapshot

  Scenario: publish is forbidden when not approved for release
    Given a carousel that is not approved for release
    When POST /api/carousels/{id}/publish runs
    Then the response is 403

  # --- Calendar / board / analytics -------------------------------------------
  Scenario: content calendar lists a scheduled blog post
    Given a blog post scheduled within the calendar range
    When GET /api/content-calendar runs
    Then the response is 200, includes the scheduled post, and matches the snapshot

  Scenario: workflow board groups the carousel into its phase column
    Given a carousel in the content phase
    When GET /api/workflow-board runs
    Then the response is 200, the project is in the content column, and matches the snapshot

  Scenario: editorial analytics aggregates blog-post counts
    Given a created blog post
    When GET /api/editorial-analytics runs
    Then the response is 200, the totals reflect the post, and it matches the snapshot

  # --- Falsifiability ---------------------------------------------------------
  Scenario: the snapshot diff is non-empty for a mutated response
    Given the live carousel blog response matches the committed baseline
    When the same response is mutated
    Then the snapshot diff rejects it
