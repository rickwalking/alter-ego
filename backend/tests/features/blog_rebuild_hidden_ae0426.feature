Feature: Rebuild hidden bad posts as drafts (AE-0426)
  A one-off operational script rebuilds the carousel-origin posts hidden under
  AE-0422 as fresh v2 drafts through the AE-0425 writer pipeline, for owner
  review. Selection uses the durable hide marker (not status), it never
  publishes, and it is idempotent.

  Background:
    Given the AE-0425 writer pipeline is available

  Scenario: Dry-run lists the marker-selected rows
    Given carousel-origin rows whose ai_generation_metadata.hidden_bad_post is set
    And some rows are already at status "draft" because hiding changed the status
    When the script runs with --dry-run
    Then it lists each marker-selected row with the criterion that selected it
    And no row is modified
    And a plain draft without the marker is not selected

  Scenario: A target row is rebuilt as a draft
    Given a marker-selected row with a carousel that still exists
    When the script runs
    Then a single blog.v2 draft is produced for that project
    And the draft has a cover and one image per section
    And content.quality.voice_score and translations.en.quality are stored
    And the row status remains "draft"
    And hidden_bad_post.rebuilt_at is set

  Scenario: The rebuild never publishes
    Given any number of target rows
    When the script completes
    Then no target row has status "published"

  Scenario: Re-running the script is a no-op
    Given a row with hidden_bad_post.rebuilt_at set
    When the script runs again
    Then that row is skipped
    And a row already at schema "blog.v2" with a stored quality score is skipped
    And no duplicate blog_posts row is created for the project

  Scenario: A missing carousel is reported and skipped
    Given a target row whose carousel project no longer exists
    When the script runs
    Then the row is reported as skipped
    And the run does not error

  Scenario: The run is observable
    Given a run over several target rows
    When the script completes
    Then a summary reports selected, rebuilt, skipped and failed counts
    And each rebuilt post has Langfuse traces

  Scenario: A per-post failure does not abort the run
    Given one target row whose generation fails
    When the script runs over several rows
    Then the failed row is counted as failed
    And the remaining rows are still processed
    And the summary is still printed

  Scenario: Missing carousel or notes are reported by the dry run
    Given a target row whose carousel project no longer exists
    And a target row whose carousel has no long_form_notes
    When the script runs with --dry-run
    Then the first row is reported as missing_carousel
    And the second row is reported as missing_notes
    And no paid generation is attempted

  Scenario: A published row is not silently unpublished
    Given a target row with status "published"
    When the script runs without --include-published
    Then the row is reported as currently_published
    And its status remains "published"
    When the script runs with --include-published
    Then the row is rebuilt as a draft

  Scenario: The operator narrows the run
    Given several target rows
    When the script runs with --only for one post
    Then only that post is considered
    When the script runs with --limit or --max-posts
    Then at most that many posts are attempted
    And the summary reports the omitted count

  Scenario: A failed post makes the command exit non-zero
    Given one target row whose generation fails
    When the script completes
    Then any failed row makes the process exit non-zero
