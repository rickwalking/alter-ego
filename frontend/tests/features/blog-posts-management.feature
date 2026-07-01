Feature: Manage blog posts from the dashboard (AE-0296)
  An admin can edit, delete, and hide (unpublish) blog posts directly from the
  "Posts do Blog" listing. Delete is confirmation-gated and origin-guarded;
  all mutations are optimistic-locked via If-Match.

  Scenario: Edit an existing post
    Given a blog post exists in the listing
    When the admin clicks Edit on its card
    Then the edit page opens for that post
    And saving changes persists via PUT and returns to the listing

  Scenario: Delete a post with confirmation
    Given a standalone blog post exists in the listing
    When the admin clicks Delete and confirms
    Then DELETE /blog-posts/{id} is called with the If-Match header
    And the post disappears from the listing

  Scenario: Cancelling delete keeps the post
    Given the delete confirmation dialog is open
    When the admin cancels
    Then no DELETE request is sent
    And the post remains in the listing

  Scenario: Hide a published post
    Given a published blog post exists in the listing
    When the admin clicks Hide
    Then POST /blog-posts/{id}/unpublish is called with the If-Match header
    And the card's status badge updates to draft without a full reload

  Scenario: Hide is only offered for published posts
    Given a draft blog post exists in the listing
    When its card renders
    Then no Hide control is shown

  Scenario: Delete is not offered for carousel-origin posts
    Given a carousel-origin blog post exists in the listing
    When its card renders
    Then no Delete control is shown
    And Hide remains available for it when published

  Scenario: A stale mutation surfaces a version-conflict message
    Given another session updated the post (lock version bumped)
    When the admin hides or deletes with the stale version
    Then the API responds 409 version_conflict
    And the listing refreshes and shows a localized conflict message
