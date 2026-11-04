Feature: Owner Retry for failed, blocked, escalated and rejected carousels (AE-0606)
  The carousel owner can retry a carousel whose phase failed, whose gate is
  blocked, whose autopilot run escalated, or that the system rejected, from the
  website or from Telegram. One shared backend action decides what the retry
  runs, stages it through the queued resume path, moves an escalated autopilot
  run back to generating and writes the audit, all in one transaction. A
  refusal changes nothing. An owner approve on a rejected carousel is refused:
  Retry is the only way back.

  Scenario: A failed phase parked before its node is re-driven
    Given a carousel whose outline phase failed with its checkpoint parked before the node
    When the owner retries it at the current lock version
    Then a workflow re-drive is staged at the bumped lock version
    And the carousel is in progress
    And one carousel.retry.requested audit is written with retry kind redrive

  Scenario: A blocked content gate is revised with the system retry feedback line
    Given a carousel waiting at the content gate whose approve is blocked by a low persona score
    When the owner retries it at the current lock version
    Then a revise is staged with the fixed system feedback line naming the reason
    And the audit stores the same feedback line

  Scenario: An escalated autopilot run moves back to generating
    Given an autopilot run escalated at the content gate of its carousel
    When the owner taps "Tentar de novo" on the escalation notice
    Then the run moves from escalated to generating with reason owner_carousel_retry
    And a revise of the content phase is staged
    And the Telegram message is edited to say the phase is being redone

  Scenario: Retry on a rejected carousel re-runs the phase it was rejected at
    Given a carousel the system rejected while it waited at the content gate
    When the owner retries it at the current lock version
    Then a revise of the content phase is staged
    And the carousel status is active again

  Scenario: Retry on a carousel rejected at the final review reopens the review
    Given a carousel the system rejected while it waited at the final review
    When the owner retries it at the current lock version
    Then nothing is staged
    And the final review waits for the owner again with the carousel status completed

  Scenario: The retry capability is read without any change
    Given a carousel whose content phase failed
    When the owner reads the retry capability
    Then it says the carousel can be retried and with which kind
    And nothing is written

  Scenario: A double tap ends in run_in_progress
    Given the owner's first retry was accepted
    When the owner retries again
    Then the retry is refused with run_in_progress

  Scenario: A queue dead letter answers use_reprocess
    Given an autopilot run the generation queue parked as a dead letter
    When the owner retries its carousel
    Then the retry is refused with use_reprocess

  Scenario: A closed autopilot run leaves the run alone and re-runs the carousel only
    Given a carousel rejected after its autopilot run closed as rejected
    When the owner retries it
    Then the carousel phase is staged again
    And the autopilot run stays rejected

  Scenario: A revise at the revision cap is refused
    Given a blocked content gate that already used its five revisions
    When the owner retries it
    Then the retry is refused with revision_cap_exceeded
    And nothing is staged

  Scenario: A carousel without a checkpoint is refused with no_checkpoint
    Given a rejected carousel whose checkpoint was pruned
    When the owner retries it
    Then the retry is refused with no_checkpoint

  Scenario: An approved or published carousel is not retryable
    Given a carousel approved for publishing
    When the owner retries it
    Then the retry is refused with not_retryable

  Scenario: A clean gate with no escalation is not retryable
    Given a carousel waiting at the content gate with nothing blocking the approve
    When the owner retries it
    Then the retry is refused with not_retryable

  Scenario: A running autopilot run answers autopilot_active
    Given a carousel whose autopilot run is generating
    When the owner retries it
    Then the retry is refused with autopilot_active

  Scenario: A tap from someone who does not own the carousel changes nothing
    Given a failed carousel owned by someone else
    When a user who is not the owner retries it
    Then the retry is refused with not_owner
    And nothing is staged, audited or moved

  Scenario: A retry sent with the version read before an auto-reject is refused
    Given the owner read a failed carousel at lock version N
    And the system rejected it, bumping the lock version
    When the owner retries with expected version N
    Then the retry is refused with version_conflict
    And nothing is staged or audited

  Scenario: A lost autopilot run compare-and-set rolls back the stage and the audit
    Given an escalated autopilot run that another request moves first
    When the owner retries its carousel
    Then the retry is refused with concurrent_update
    And no stage and no audit remain

  Scenario: An artifact mutation in progress refuses the retry
    Given an artifact mutator holds the carousel lock
    When the owner retries the carousel
    Then the retry is refused with mutation_in_progress

  Scenario: A website approve on a rejected carousel is refused
    Given a carousel the system rejected
    When the owner approves it on the website at the current lock version
    Then the approve is refused with 409 carousel_rejected
    And the carousel stays rejected at the same lock version

  Scenario: A Telegram approve on a rejected carousel is refused
    Given an autopilot run waiting for the owner whose carousel the system rejected
    When the owner taps Approve on the current review
    Then nothing is approved and the owner is told the carousel was rejected

  Scenario: An unattended approve on a rejected carousel is refused
    Given a carousel the system rejected
    When the autopilot approves it through the run-owned path
    Then the approve is refused before any write
