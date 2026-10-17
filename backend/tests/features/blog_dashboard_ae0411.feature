Feature: Blog dashboard create, partial update and live state (AE-0411)
  "New Post" must create a draft without a slug clash, a partial update must
  leave untouched fields (the body) as stored, and the dashboard list must say
  whether a post is really live for anonymous readers.

  Scenario: Creating two posts without a slug succeeds
    Given an editor
    When the editor creates two posts titled "Untitled draft" without a slug
    Then both responses are 201
    And each post has a distinct non-empty slug starting with "untitled-draft-"

  Scenario: A given slug is kept
    Given an editor
    When the editor creates a post with slug "my-post"
    Then the response is 201 with slug "my-post"

  Scenario: A duplicate given slug is a clear 409
    Given a post with slug "taken"
    When the editor creates another post with slug "taken"
    Then the API responds 409 with detail "blog_post_slug_conflict"

  Scenario: A blank slug is generated like a missing one
    Given an editor
    When the editor creates a post titled "Revisão humana!" with slug "  "
    Then the response slug starts with "revisao-humana-"

  Scenario: A title-only update keeps the stored content
    Given a post whose content is {"markdown": "# Long body", "translations": {"en": "# Body"}}
    When the editor updates only the title
    Then the stored content is unchanged

  Scenario: An over-long excerpt is rejected as a validation error
    Given an existing post
    When the editor updates the excerpt with 501 characters
    Then the API responds 422

  Scenario: A standalone published post is live
    Given a standalone published post
    When the editor lists blog posts
    Then the post has is_public true

  Scenario: A carousel post whose carousel is not released is not live
    Given a carousel-origin post stored "published" whose carousel is not public
    When the editor lists blog posts
    Then the post has status "published" and is_public false

  Scenario: A carousel post whose carousel is released is live
    Given a carousel-origin post stored "published" whose carousel is public
    When the editor lists blog posts
    Then the post has is_public true

  Scenario: A draft is never live
    Given a standalone draft post
    When the editor lists blog posts
    Then the post has is_public false
