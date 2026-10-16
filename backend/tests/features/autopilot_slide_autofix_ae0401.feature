Feature: Autopilot model fix of failing slides (AE-0401)
  At the content and design gates the autopilot repairs blocking copy
  deterministically, then rewrites each slide that still fails (a blocking
  rule, or a voice score under 70) with the fast model, at most 3 attempts,
  then escalates to the owner. A content-quality failure never spends the
  revise budget, and a gate never loops.

  Background:
    Given an autopilot run waiting at the content gate
    And the slide fix model is a fake (no network)

  Scenario: Fixed deterministically, approved without a model call
    Given slide 5's PT heading starts lowercase
    When the runner ticks
    Then the gate is approved
    And the slide fix model is never called

  Scenario: Fixed on attempt 1
    Given slide 3's PT body has an emoji the repair cannot remove
    And the model answers clean copy
    When the runner ticks
    Then slide 3's copy is the model's copy in the checkpoint
    And the content-gate report is clean
    And the gate is approved at the bumped lock version
    And one "autopilot_slide_autofix" attempt is logged with outcome "fixed"

  Scenario: Fixed on attempt 3
    Given slide 3's PT body has an emoji
    And the model answers with an emoji twice, then clean copy
    When the runner ticks
    Then the gate is approved after 3 attempts

  Scenario: Still failing after 3 attempts escalates with the slides listed
    Given slide 3's PT body has an emoji
    And the model always answers with an emoji
    When the runner ticks
    Then the run is escalated with reason "content_quality"
    And the escalation lists "slide 3", "visible_emoji_forbidden", its current text and "3 fix attempts"
    And no revise is sent
    And the checkpoint copy is unchanged

  Scenario: A model error counts as an attempt
    Given slide 3's PT body has an emoji
    And the model fails once, then answers clean copy
    When the runner ticks
    Then attempt 1 is logged with outcome "model_error"
    And the gate is approved after attempt 2

  Scenario: A fix that breaks another rule is retried with the new violation
    Given slide 3's PT body has an emoji
    And the model first moves the emoji into the heading, then answers clean copy
    When the runner ticks
    Then the second prompt names "visible_emoji_forbidden" on the heading
    And the gate is approved

  Scenario: A low voice score on one slide is rewritten and re-scored
    Given slide 2 scored 50 for voice and the others 80
    And the model rewrites slide 2 and the persona scores it 85
    When the slide fix runs
    Then slide 2's copy and its voice score 85 are in the checkpoint
    And the other voice scores are unchanged
    And the gate is approved

  Scenario: Repair makes no progress, the model fix runs, then the run escalates (no loop)
    Given the deterministic repair cannot fix slide 3 (a no-op)
    And the model always answers with an emoji
    When the runner ticks twice
    Then the first tick escalates after 3 model attempts
    And the second tick does nothing to the run

  Scenario: No revise is ever issued for content quality
    Given any content-quality failure at the content or design gate
    When the runner ticks
    Then the runner approves or escalates, never revises

  Scenario: A lost lock writes nothing and retries next tick
    Given another writer moved the lock version during the fix
    When the runner ticks
    Then nothing is written and the run is not escalated

  Scenario: Other reasons keep the revise path
    Given a forbidden phrase in the copy
    When the runner ticks
    Then the gate is revised with reason "forbidden_phrase"
