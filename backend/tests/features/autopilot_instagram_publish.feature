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
