Feature: A website cover switches a completed carousel in final review (AE-0594)
  Pedro's decision (2026-11-02): a cover the owner generates from the website
  ("Gerar capa com Grok") on a completed carousel that still waits for its
  first approval becomes slide 1. The slides are rendered again and the
  carousel stays in final review, so the owner approves the new render
  before anything goes out. Nothing is published, the approval and the
  release are never touched. A published carousel is never switched: the
  picker refuses with cover_switch_requires_review (409) and a generated
  cover stays a picker option. An approved one (scheduled ones included) has
  its review reopened instead, see reopen_review_on_cover_switch_ae0597.feature.
  Telegram approve, publish and schedule act only for the revision of the
  tapped review or reminder.

  Scenario: A website cover switches a completed carousel in final review
    Given a completed carousel waiting in final review for its first approval
    When the owner's website cover generation succeeds
    Then slide_cover is the generated asset with kind ai_image
    And the slides are rendered again
    And the carousel is still in final review, not approved and not public

  Scenario: A website approval read before the switch is refused
    Given the owner's review page read the lock version before the switch
    When the owner approves from that page after the switch
    Then the approve route answers a version conflict and nothing is approved

  Scenario: A failed or overtaken website cover switch is rolled back
    Given the website cover was written to slide 1
    When the render fails in any way, or the carousel left the review before the render
    Then slide 1 goes back to its previous cover, is rendered again, and the reason is rolled_back
    And the Telegram review is sent again
    But when the restore cannot get the lock or its re-render fails the reason is rollback_failed
    And the run is escalated, and the needs-republish marker keeps approval refused

  Scenario: The Telegram review is held while slide 1 changes
    Given an autopilot run waits for the owner's Telegram review of the carousel
    When the owner's website cover generation succeeds
    Then the run is out of awaiting_owner while the slides are rendered again
    And the worker sends the review again at the new lock version

  Scenario: An old Telegram review message cannot approve the new render
    Given slide 1 changed after the review message was sent
    When the owner taps approve, publish or schedule on that older message
    Then nothing is approved or scheduled and the owner is told the review was replaced
    And when no review was sent for the current version yet, the worker sends it

  Scenario: An old Telegram reminder cannot approve the new render
    Given a reminder was sent for an older review revision
    When the owner taps publish on that reminder
    Then nothing is approved

  Scenario: An unknown Telegram message cannot approve anything
    Given a tap comes from a message that is none of the run's reviews or reminders
    When the owner taps publish on it
    Then nothing is approved

  Scenario: No approval lands while a cover switch is between write and render
    Given the website cover was written to slide 1 and its render has not settled
    When the owner approves on the website or on Telegram
    Then both approves are refused and the carousel stays a draft

  Scenario: Approves at earlier gates ignore a pending re-render
    Given a carousel at its content gate carries the needs-republish marker
    When the owner approves the gate on the website or on Telegram
    Then the approve is not refused for the marker

  Scenario: A render never changes slide 1's cover on an approved carousel
    Given an approved or released carousel whose active artifacts recorded another cover
    When the republish service, the sweep, a slide edit or a manual republish renders it
    Then the render is refused with cover_change_requires_review and the slides stay
    And the sweep logs it once and retries only after the carousel changes

  Scenario: A typed publish time answers the review it was asked from
    Given the owner tapped "Outro horário" on a review and slide 1 changed since
    When the owner types a time
    Then nothing is approved or scheduled, and a hold or a new review drops the open time reply

  Scenario: The approve compares and sets at the tapped revision
    Given the lock version moves after the tap was checked
    When the approve runs
    Then its compare-and-set uses the tapped revision and is refused

  Scenario: Concurrent notice ledger writes never erase a recorded review
    Given two writers read the run's ledger and save different records at once
    When both commit
    Then both records are in the ledger

  Scenario: A Telegram GrokBot cover tap on a published carousel is refused clearly
    Given the cover switch refuses because the carousel is published
    When the worker applies the owner's GrokBot cover choice
    Then the review reopens with the reason cover_requires_review

  Scenario: The current Telegram review or reminder still publishes and schedules
    Given the tapped review or reminder was sent for the current lock version
    When the owner publishes now or picks a slot
    Then the approve runs its compare-and-set at that revision and the run moves on

  Scenario: A Telegram publish and a website cover switch race
    Given an autopilot run waits for the owner's review of the carousel
    When the owner taps publish while the website cover switch holds the review
    Then exactly one of them wins and no unseen image is approved

  Scenario: A held run does not block the other autopilot runs
    Given one run is held for a website cover switch
    When the worker ticks
    Then it steps the next active run instead

  Scenario: A Telegram review hold that outlives its task is escalated
    Given a run was held for a website cover and the task never released it
    When the worker sees the hold after its time limit
    Then the run is escalated and no review is sent, since slide 1 may not match the render
    And the needs-republish marker keeps approval refused until the republish sweep renders it

  Scenario: A cover the owner chose while the job ran wins on a completed carousel
    Given the owner picked another slide 1 while the generation ran
    When the owner's website cover generation succeeds
    Then slide 1 keeps the owner's choice and the skip reason is manual_choice
    And a held Telegram review goes back to the owner unchanged

  Scenario: A lock conflict on a completed carousel is skipped and logged
    Given another writer holds the carousel's project lock
    When the owner's website cover generation succeeds
    Then nothing is written and the skip reason is conflict

  Scenario: A failed website generation leaves a completed carousel alone
    Given the Grok bridge fails the owner's website generation
    When the run settles
    Then slide 1, the lock version and the run are unchanged

  Scenario: Replaying a website cover success changes nothing
    Given the owner's website cover already switched slide 1
    When the same success is processed again
    Then the outcome is already_selected and nothing is written or rendered

  Scenario: The picker refuses a published carousel
    Given a released carousel
    When the owner picks another cover
    Then the pick is refused with cover_switch_requires_review and nothing is rendered

  Scenario: An approval that lands while the picker switches is dropped with the write
    Given the picker read the carousel waiting in final review
    When an approval lands before the locked write
    Then the locked write drops that approval with the new slide 1 in one commit

  Scenario: The picker explains that a published carousel cannot change
    Given the picker's switch was refused with cover_switch_requires_review
    Then the publish page says a published carousel's cover cannot change

  Scenario: A website cover on a published carousel stays a picker option
    Given a released carousel
    When the owner's website cover generation succeeds
    Then slide 1 is unchanged and the skip reason is carousel_published

  Scenario: An autopilot cover on a completed carousel is unchanged
    Given a completed carousel in final review
    When an autopilot-started cover generation succeeds
    Then slide 1 is unchanged and the skip reason is carousel_completed
