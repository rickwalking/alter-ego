Feature: Autopilot auto-cover for new carousels (AE-0581)
  When the autopilot starts a fresh carousel, it enqueues exactly one slide-1
  cover generation through the existing Grok images.edit path, with the
  owner's current library photos as references. The owner's standing consent
  (AUTOPILOT_COVER_CONSENT) gates the step: without it the step skips and logs
  and no photo is read or sent. The existing caps (4 per carousel, 40 per
  month, one pending per carousel) refuse extra jobs.

  Scenario: A fresh autopilot carousel gets one cover job
    Given consent is recorded and the owner has library photos
    When a queued run creates and starts a new carousel
    Then exactly one cover generation is recorded and scheduled
    And the request is confirmed, with up to 3 of the owner's library photos
    And the direction is the carousel topic

  Scenario: The owner picked fewer than three photos
    Given consent is recorded and the owner has 2 library photos
    When the cover job starts
    Then exactly those 2 photos go as references

  Scenario: A cap refusal skips the job
    Given consent is recorded and the monthly cap is exhausted
    When a queued run starts a new carousel
    Then no cover job is scheduled and the run continues normally

  Scenario: Without consent no photo is read or sent
    Given no recorded consent
    When a queued run starts a new carousel
    Then the step skips with reason no_consent
    And the owner's library photos are never read

  Scenario: Without library photos the step skips
    Given consent is recorded and the owner has no library photos
    When a queued run starts a new carousel
    Then the step skips with reason no_photos

  Scenario: An unconfigured bridge skips the job
    Given consent is recorded and library photos but no image bridge
    When a queued run starts a new carousel
    Then the step skips with reason bridge_unavailable

  Scenario: A re-driven run does not enqueue a second cover
    Given the carousel already has a cover generation row
    When the run starts again
    Then no second cover job is scheduled

  Scenario: A retried start still gets its cover
    Given the first start failed after the project was attached
    When the retry starts the carousel
    Then the cover step runs and the helper dedups by the generation row

  Scenario: A failed start never schedules a cover
    Given the editorial engine reports a provider outage
    When a queued run tries to start
    Then no cover job is scheduled and the start failure is counted

  Scenario: A cover failure never fails the run
    Given the cover step raises
    When a queued run starts a new carousel
    Then the run still moves to generating
