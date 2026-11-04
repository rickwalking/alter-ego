Feature: A carousel reject bumps lock_version so a stale owner review is refused (AE-0604)
  The stuck-workflow sweep and the abandoned-escalation settle both reject a
  carousel through the same transition. The owner review routes compare
  lock_version only, so the reject bumps it in the same unit of work: an owner
  action sent with the version read before the reject fails the existing
  version-conflict check instead of driving a rejected carousel.

  Scenario: A stale owner approve after a stuck-sweep reject is refused
    Given a carousel waiting for a human at the research gate at lock version N
    And the owner read the carousel at lock version N
    When the stuck-workflow sweep rejects the carousel
    And the owner approves with expected version N
    Then the resume is refused with 409 version_conflict
    And the carousel stays rejected

  Scenario: A stale owner approve after an escalation-close settle is refused
    Given a carousel waiting for a human at the research gate at lock version N
    And the owner read the carousel at lock version N
    When the abandoned-escalation settle rejects the carousel escalated at version N
    And the owner approves with expected version N
    Then the resume is refused with 409 version_conflict
    And the carousel stays rejected

  Scenario: An approve at the post-reject version is refused as carousel_rejected
    Given a carousel the stuck-workflow sweep rejected
    When the owner approves with the carousel's current lock version
    Then the resume is refused with 409 carousel_rejected (AE-0606: Retry is the only way back)
    And the carousel stays rejected at the same lock version

  Scenario: An owner action at the current version on a waiting carousel still works
    Given a carousel waiting for a human at the research gate at lock version N
    When the owner approves with expected version N
    Then the resume is accepted with 202
    And the carousel lock version is N plus 1

  Scenario: The reject bumps the lock version once
    Given a carousel waiting for a human at lock version N
    When the reject transition runs on it
    Then the carousel is rejected at lock version N plus 1
    And a carousel the sweep leaves alone keeps its lock version

  Scenario: A Telegram review tap after a reject closes the run
    Given an autopilot run waiting for the owner on a Telegram review sent at lock version N
    And the carousel was rejected since, at lock version N plus 1
    When the owner taps approve, publish now or schedule on that review
    Then nothing is approved and nothing moves toward publishing
    And the run is rejected with reason carousel_rejected
    And the run is not left in reworking
