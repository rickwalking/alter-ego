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

  # QA r2 R3: recovery never guesses, and never posts twice.
  Scenario: A manual post before the container is not taken as the autopilot post
    Given a publishing run whose container was created 5 minutes ago and reports PUBLISHED
    And the only recent album was posted by hand 7 minutes ago
    When the publish job resumes the run
    Then "media_publish" is not called
    And the run is "publish_failed" with reason "instagram_published_media_unknown"
    And the owner is told the post may already be live and to check Instagram
    And the notice has no Retry button
    And tapping an older Retry button for that run changes nothing

  # QA r2 R4: the double-publish edge windows.
  Scenario: A stale publish claim is not taken over while Graph may still run
    Given the publish claim stale window is longer than the slowest possible Graph publish
    And a publishing run holds a stale claim and a container created 1 hour ago with no post id
    When the worker or the manual route tries to claim the run
    Then the claim is refused and other due runs are still published
    And once the container is older than 24 hours it is checked first
    And a container Graph reports as PUBLISHED is recovered instead of posted again

  Scenario: A manual publish crash after the container reuses that container
    Given a carousel without an autopilot run
    When the manual publish creates a container and then fails before media_publish returns
    Then the container id is already stored in the manual ledger
    And the next manual publish finishes that container without creating another

  Scenario: An approved carousel that is not public yet is not failed
    Given the owner tapped Approve and the run is "publishing"
    And the release has not made the carousel public yet
    When the worker ticks within the 5 minute grace window
    Then the run stays "publishing" and no publish-failed message is sent
    And after the grace window a carousel that is still not public fails as before

  # QA r3 Q2: a worker killed mid-publish no longer holds the run for 24 h.
  Scenario Outline: A run held by a dead worker's container is resolved by its status
    Given a publishing run whose stale claim covers a container with no post id
    When the publish job reads the container status as "<status>"
    Then the job <outcome>

    Examples:
      | status      | outcome                                              |
      | PUBLISHED   | takes the claim over and recovers the posted media   |
      | FINISHED    | takes the claim over and calls media_publish once    |
      | ERROR       | takes the claim over and fails the run               |
      | EXPIRED     | takes the claim over and fails the run               |
      | IN_PROGRESS | keeps waiting                                        |

  Scenario: The owner is told once when a publish is held for 30 minutes
    Given a publishing run held by an IN_PROGRESS container for 31 minutes
    When the publish job ticks twice
    Then the owner receives one "publish held" notice

  # QA r3 Q4: the ledger is read again once the manual claim is held.
  Scenario: A manual publish resumes the container another attempt just stored
    Given a carousel without an autopilot run
    And another attempt stores a container in the ledger after our first read
    When the owner's manual publish takes the claim
    Then it re-reads the ledger and resumes that container instead of opening one
    And a post id stored in between is returned without calling Graph

  # AE-0368: prod sat in "publishing" with content_publishing_limit_unreadable.
  Scenario: The quota read requests the config field
    Given the Graph publishing-limit endpoint returns config only when asked for it
    When the publish job reads the content publishing limit
    Then the request carries fields "quota_usage,config"
    And the remaining quota is quota_total minus quota_usage

  Scenario: A quota body without config falls back to the documented limit
    Given the publishing-limit body has quota_usage 0 and no config
    When the publish job runs
    Then the remaining quota is computed against Meta's documented 100 posts per 24 hours
    And a warning is logged
    And the carousel is published

  Scenario: An unreadable quota fails the run instead of looping forever
    Given the publishing-limit body has no readable quota_usage
    When the publish job runs three times past the backoff
    Then no container is created
    And the run is "publish_failed" with reason "content_publishing_limit_unreadable"
    And the owner is notified with a Retry button
