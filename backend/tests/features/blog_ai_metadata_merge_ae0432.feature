Feature: AI suggest/improve never erase concurrent metadata writes (AE-0432)
  ai-suggest and ai-improve call the LLM for seconds. Anything committed to the
  post's ai_generation_metadata meanwhile (an image budget reservation, an
  AE-0425 batch reservation, another recorded AI action) must survive: the
  route re-reads the row under the row lock and merges its own change onto the
  latest metadata instead of writing back the copy it loaded before the call.

  Background:
    Given an editor authenticated as EditorUser
    And a v2 blog post

  Scenario: An image budget reservation committed during ai-suggest is kept
    Given the post has reserved 1 image
    When the editor POSTs /blog-posts/{id}/ai-suggest
    And another request reserves 1 more image while the LLM runs
    Then ai_generation_metadata.blog_image_generations is 2
    And the suggest action is recorded with the actions recorded meanwhile

  Scenario: An image budget reservation committed during ai-improve is kept
    Given the post has reserved 1 image
    When the editor POSTs /blog-posts/{id}/ai-improve
    And another request reserves 1 more image while the LLM runs
    Then ai_generation_metadata.blog_image_generations is 2
    And the improve action is recorded

  Scenario: A suggestion stored meanwhile is not lost
    Given another ai-suggest stores its suggestion while the LLM runs
    When this ai-suggest finishes
    Then both suggestions are stored

  Scenario: Reservations on different posts do not wait on each other
    Given a reservation on post A holds its lock
    When post B reserves an image
    Then post B's reservation is not blocked by post A
