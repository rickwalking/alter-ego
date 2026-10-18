Feature: Blog generation entry points (AE-0425)
  The owner can start a blog generation from an existing carousel or from a
  standalone topic. Both create a draft and show progress while the writer and
  image steps run; neither publishes automatically.

  Background:
    Given the owner is logged in as "Pedro"

  Scenario: Create a blog from a carousel
    Given a carousel project with a completed research artifact
    When the owner clicks "Create blog from carousel"
    Then POST /blog-posts/from-carousel is called with the project id
    And the owner is sent to the new draft's editor
    And a generation-in-progress indicator is shown

  Scenario: A carousel that already has a blog row is blocked
    Given the carousel project already has a non-deleted blog row
    And it may be a draft, a hidden bad post, approved or published
    When the owner clicks "Create blog from carousel"
    Then an "already exists" message is shown with the existing post
    And no new post is created

  Scenario: Start a standalone blog from a topic
    Given the owner is on the blog dashboard
    When the owner enters a topic and clicks "Generate blog"
    Then POST /blog-posts/generate is called with the topic
    And the owner is sent to the new draft's editor

  Scenario: Generation progress is polled and shown
    Given a generation is in progress
    When the editor polls GET /api/blog-posts/{id}
    Then the progress indicator reflects generation.status
    And when it reaches "complete" the sections and images are shown

  Scenario: A partial generation surfaces failed image slots
    Given generation.status is "partial" with one section image missing
    When the editor renders the post
    Then the missing slot shows a retry control
    And the rest of the document is editable

  Scenario: A failed generation shows a retry affordance
    Given generation.status is "failed"
    When the editor renders the post
    Then a retry control is shown
    And the draft is not discarded

  Scenario: A restart-interrupted generation is explained and retryable
    Given generation.status is "failed"
    And generation.errors[] contains ERR_GENERATION_INTERRUPTED
    And generation.recoverable is true
    When the editor renders the post
    Then a "generation was interrupted" message is shown with a retry control
    And any partial sections remain visible
    And retrying targets the same post id (no duplicate draft)

  Scenario: Generated posts are drafts, never published
    Given a generation completes
    When the dashboard list renders
    Then the new post is shown with a "draft" status badge
    And the public URL returns not-found until the owner publishes

  Scenario: Generation is never triggered from the public carousel page
    Given a public carousel page
    Then no control creates or publishes a blog post
    And a carousel going public does not change any blog status

  Scenario: Generation copy is localized
    Given the pt locale
    Then the generation buttons and progress copy come from pt messages

  Scenario: The section count follows the carousel slide count
    Given a POV carousel with slide_count 9
    When the owner creates a blog post from it
    Then the generated document has 9 sections
    And the image progress shows 10 slots (9 sections + the cover)

  Scenario: A private carousel warns that the post cannot be public
    Given a carousel with is_public false
    When the owner opens the generated blog post
    Then a warning explains that publishing will 404 until the carousel is public
    And the warning links to the carousel visibility setting
