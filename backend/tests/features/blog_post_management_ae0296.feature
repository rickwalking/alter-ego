Feature: Blog post management guards (AE-0296)
  Hard delete is optimistic-locked and origin-guarded; unpublish is an
  optimistic-locked visibility flip; deleting a carousel project never leaves
  an orphaned publicly-visible blog row.

  Scenario: Delete requires the If-Match version header
    Given an existing standalone blog post
    When the editor sends DELETE without an If-Match header
    Then the API responds 428 precondition required
    And the post still exists

  Scenario: Delete a standalone post with the current version
    Given an existing standalone blog post at lock version 1
    When the editor sends DELETE with If-Match 1
    Then the API responds 204
    And the post no longer exists

  Scenario: Delete with a stale version is rejected
    Given an existing standalone blog post at lock version 2
    When the editor sends DELETE with If-Match 1
    Then the API responds 409 with detail "version_conflict"
    And the post still exists

  Scenario: Delete of a project-linked carousel-origin post is blocked
    Given a carousel-origin blog post still linked to its carousel project
    When the editor sends DELETE with the current If-Match version
    Then the API responds 409 with detail "carousel_origin_delete_blocked"
    And the post still exists

  Scenario: Delete of a detached carousel-origin post is allowed
    Given a carousel-origin blog post whose project_id is null
    When the editor sends DELETE with the current If-Match version
    Then the API responds 204

  Scenario: Unpublish requires the If-Match version header
    Given a published blog post
    When the editor sends POST /unpublish without an If-Match header
    Then the API responds 428 precondition required
    And the post is still published

  Scenario: Unpublish flips a published post to draft and bumps the version
    Given a published blog post at lock version 1
    When the editor sends POST /unpublish with If-Match 1
    Then the API responds 200 with status "draft"
    And published_at is cleared
    And the response lock_version is 2

  Scenario: Unpublish with a stale version is rejected
    Given a published blog post at lock version 2
    When the editor sends POST /unpublish with If-Match 1
    Then the API responds 409 with detail "version_conflict"
    And the post is still published

  Scenario: Every blog post origin has an explicit delete policy
    Given the BlogPostOrigin enum
    When the delete-policy sets are inspected
    Then every origin appears in exactly one policy set

  Scenario: Deleting a carousel project reverts its published blog row to draft
    Given a carousel project whose dual-written blog row is published
    When the project is deleted through the repository
    Then the blog row status is draft with publish stamps cleared
    And its lock_version is bumped
