Feature: An abandoned escalation that closes also settles its carousel (AE-0601)
  An escalated autopilot run nobody fixed within 72 hours becomes rejected
  (escalation_expired). Its carousel, still waiting for a human at the gate it
  escalated on, is moved to the same terminal rejected state the stuck-workflow
  auto-reject uses, with the same phase-changed event, so the run and the
  carousel agree. The run closes first; the carousel follows only when it is
  unchanged since the escalation.

  Scenario: Closing an abandoned escalation rejects its waiting carousel
    Given an escalated run older than 72 hours whose carousel waits for a human at the content gate
    And the carousel lock version is the one the run escalated at
    When the recovery sweep runs
    Then the run is rejected with reason escalation_expired
    And the carousel phase status is rejected and its status failed
    And one project phase-changed event records the previous phase and status

  Scenario: A carousel that is no longer waiting for a human is left alone
    Given an escalated run older than 72 hours
    And its carousel is already rejected, approved for publish, published, archived or not awaiting a human
    When the recovery sweep runs
    Then the run is rejected with reason escalation_expired
    And the carousel row is unchanged and no event is emitted

  Scenario: A carousel changed since the escalation is left alone
    Given an escalated run older than 72 hours
    And its carousel waits for a human at a lock version other than the one the run escalated at
    When the recovery sweep runs
    Then the run is rejected with reason escalation_expired
    And the carousel row is unchanged

  Scenario: A run without a carousel or an escalation version settles nothing
    Given an escalated run older than 72 hours with no carousel or no recorded escalation version
    When the recovery sweep runs
    Then the run is rejected with reason escalation_expired
    And no carousel is settled

  Scenario: A second sweep does nothing
    Given an abandoned escalation whose run and carousel were both rejected
    When the recovery sweep runs again
    Then nothing moves and no second event is emitted

  Scenario: A failed carousel settle still closes the run
    Given an escalated run older than 72 hours whose carousel settle raises an error
    When the recovery sweep runs
    Then the run is rejected with reason escalation_expired
    And the failure is logged and the stuck-workflow auto-reject remains the backstop

  Scenario: A run whose close loses the race settles nothing
    Given an escalated run older than 72 hours that another worker moves first
    When the recovery sweep runs
    Then the run close is not applied and the carousel is not settled
