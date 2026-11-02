Feature: A cover switch reopens the final review of an approved carousel (AE-0597)
  Pedro's decision (2026-11-02): a slide-1 cover switch (website picker,
  website auto-switch, GrokBot cover, hook photo) on an approved or scheduled
  carousel drops the approval in the same transaction as the slide-1 write
  and the needs-republish marker. The carousel goes back to final review,
  awaiting human, re-renders, and only a fresh approve restores the approval.
  Published carousels never change. A reopened scheduled run keeps its time
  and waits; a missed slot expires, as the scheduler already does.

  Scenario: A cover switch reopens the review of an approved carousel
    Given a completed carousel approved for publish and not public
    When slide 1 changes through the picker, the website generation, the GrokBot cover or the hook photo
    Then one commit stores the new slide 1, the needs-republish marker and a draft workflow at final_review awaiting_human
    And the checkpoint waits at the final review again
    And the slides are rendered again

  Scenario: A fresh approve restores the approval
    Given a carousel whose review was reopened and whose render settled
    When the owner approves the final review at the current version
    Then the carousel is approved for publish again

  Scenario: A published carousel never changes
    Given a released carousel
    When any cover switch runs
    Then it is refused with cover_switch_requires_review and nothing is written or rendered

  Scenario: A reopened scheduled run keeps its time and gets a new review
    Given an autopilot run scheduled for a time still ahead
    When slide 1 of its carousel changes
    Then the run leaves scheduled and keeps its scheduled time
    And the worker sends the Telegram review again at the new lock version

  Scenario: Approving the new review keeps the scheduled time
    Given a reopened run waiting for the owner with its kept time still ahead
    When the owner approves the new review
    Then the final review is approved and the run is scheduled again at the kept time

  Scenario: A slot that passes while the review waits does not publish
    Given a reopened run waiting for the owner whose kept time has passed
    When the due sweep runs or the owner approves
    Then the run expires with schedule_withdrawn and nothing is approved or published

  Scenario: A kept time approved again on the website publishes at its time
    Given a reopened run waiting for the owner whose carousel was approved again on the website
    When its kept time comes
    Then the due sweep publishes it

  Scenario: The scheduled publish and a cover switch never both win
    Given an approved carousel whose scheduled run is due
    When the due sweep and a cover switch race on Postgres
    Then either the carousel is released with its reviewed cover and the switch is refused as published
    Or the switch lands, the run expires and nothing is released

  Scenario: A release never publishes a carousel whose approval was dropped
    Given a carousel whose review was reopened after the release read it
    When the release writes is_public
    Then nothing is released and the release answers a version conflict

  Scenario: A rolled back switch keeps the review reopened
    Given an approved carousel whose switch render failed
    When the cover is rolled back
    Then the carousel stays a draft in final review and the review is sent again
