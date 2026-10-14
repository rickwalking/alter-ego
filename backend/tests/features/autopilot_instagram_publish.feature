Feature: Idempotent Instagram publish
  As the autopilot worker
  I want an approved carousel posted to Instagram exactly once
  So that a retry or a crash cannot create a duplicate post

  Scenario: Approved carousel is posted once
    Given a run in "publishing" for a released carousel with 7 slides
    When the publish job runs twice
    Then media_publish is called once
    And the run is "published" with a permalink

  Scenario: Crash after container creation
    Given a run with a stored carousel container id and no post id
    When the publish job runs
    Then no new containers are created
    And the stored container is published

  Scenario: Permanent Meta error
    Given Meta rejects the container with error 36003
    When the publish job runs
    Then the run is "publish_failed" with the Meta error code
    And the owner is notified with a Retry button

  Scenario: Transient Meta error is retried then failed
    Given Meta returns a transient error
    When the publish job runs three times past the backoff
    Then the run is "publish_failed"
    And the owner is notified

  Scenario: Post id already stored skips the Graph API
    Given a publishing run that already has an ig_post_id
    When the publish job runs
    Then the Graph API is not called
    And the run is "published"

  Scenario: Instagram Login token uses graph.instagram.com
    Given the Graph host is the Instagram Login default
    When the publisher creates a container
    Then the request host is graph.instagram.com

  Scenario: Status route returns persisted state
    Given a published run for a carousel
    When the owner requests the instagram status
    Then the response includes state, ig_post_id, permalink and error

  Scenario: Manual route does not publish twice
    Given a carousel whose run already has an ig_post_id
    When the owner posts publish instagram again
    Then the Graph API is not called
    And the response is published

  Scenario: Crash after media_publish recovers the published post
    Given a publishing run whose stored container already reports PUBLISHED
    And the account's recent media include a carousel album posted within 24 hours
    When the publish job runs
    Then media_publish is not called again
    And the run is "published" with the recovered ig_post_id persisted
    And the owner is notified

  Scenario: Published container whose media cannot be matched fails without reposting
    Given a publishing run whose stored container already reports PUBLISHED
    And no carousel album was posted within the last 24 hours
    When the publish job runs
    Then media_publish is not called again
    And the run is "publish_failed" with reason "instagram_published_media_unknown"

  # --- AE-0348 QA round 1 -------------------------------------------------

  Scenario: Retry after exhaustion calls Graph again
    Given a run in "publish_failed" after 3 transient failures
    When the owner taps Retry
    Then the publish attempts are reset to 0
    And the next publish tick calls Graph again

  Scenario: Start failures do not consume the publish retry budget
    Given a run that needed 2 workflow-start attempts
    When the owner approves and the run enters "publishing"
    Then the publish attempts are 0
    And the first publish tick runs with no backoff

  Scenario: Manual publish while an autopilot run exists
    Given a carousel whose autopilot run is "awaiting_owner"
    When the owner calls the manual Instagram publish route
    Then the route answers 409 "autopilot_run_not_publishing"
    And Graph is not called

  Scenario: Manual publish of a carousel without a run is idempotent
    Given a carousel with no autopilot run
    When the manual publish succeeds twice in a row
    Then Graph is called once
    And the post id is persisted and returned both times
    And the status route reports the stored post id

  Scenario: Manual publish and the worker never publish the same run at once
    Given another caller holds the publish claim on a "publishing" run
    When the manual route publishes that carousel
    Then the route answers 409 "instagram_publish_in_progress"
    And the worker tick skips the claimed run
