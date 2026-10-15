Feature: Autopilot content gate repairs first and reports the real reason (AE-0392)

  Prod carousel f21b2bdb (2026-10-15): the content gate revised with
  "Reason: forbidden_phrase. Measured: ." because every blocking presentation
  rule (sentence case, empty body, EN equal to PT, item counts, tag balance)
  was folded into the forbidden-phrase list. The whole 60-minute content
  phase then regenerated with no hint of what had failed.

  Now a blocking presentation rule is its own reason, content_quality. The
  runner first runs the owner "Fix issues" repair on the checkpoint copy,
  through the editorial facade, and approves a gate it made clean without
  spending a revision. Only what is left is revised, with feedback that names
  each failing slide, rule and offending text.

  Background:
    Given an autopilot run generating a carousel with presentation policy hero_lower_third_v3

  Scenario: A presentation rule is reported as content_quality with rule@slide
    Given the content gate report blocks on portuguese_heading_sentence_case at slide 5 and empty_body at slide 4
    When the gate snapshot is read
    Then it has no forbidden phrase hits
    And the policy reason is content_quality
    And Measured reads "portuguese_heading_sentence_case@5, empty_body@4"

  Scenario: Measured lists at most 10 rule@slide pairs
    Given the content gate report blocks on 12 different slides
    When the revise feedback is built
    Then Measured lists 10 rule@slide pairs

  Scenario: A real forbidden phrase still revises as forbidden_phrase
    Given slide 2's draft contains the persona's forbidden phrase "synergy"
    When the runner ticks at the content gate
    Then no repair is attempted
    And the content phase is revised with reason forbidden_phrase
    And Measured reads "synergy"

  Scenario: A casing-only violation is repaired and approved without a revise
    Given slide 5's heading starts lowercase
    When the runner ticks at the content gate
    Then the checkpoint copy of slide 5 starts uppercase
    And autopilot_content_autorepaired is logged with heading_not_sentence_case_pt
    And the content gate is approved
    And no revision is counted

  Scenario: An empty body the repair can fill is approved
    Given slide 4 has no body or features but its outline has 3 key points
    When the runner ticks at the content gate
    Then slide 4 gets 3 features built from its key points
    And the content gate is approved

  Scenario: A violation the repair cannot fix gets a targeted revise
    Given slide 3's body has a decorative emoji the repair does not remove
    When the runner ticks at the content gate
    Then the repair changes nothing and the lock version is unchanged
    And the content phase is revised once with reason content_quality
    And the feedback names slide 3, its rule visible_emoji_forbidden and its current text
    And the feedback says to change only the listed slides

  Scenario: Repairing part of the violations revises only what is left
    Given slide 5's heading starts lowercase and slide 3's body has a decorative emoji
    When the runner ticks at the content gate
    Then slide 5 is repaired
    And the revise feedback lists slide 3 and not slide 5

  Scenario: Another writer holds the carousel during the repair
    Given the repair loses the lock-version race
    When the runner ticks at the content gate
    Then nothing is revised or approved this tick
    And the next tick tries again

  Scenario: The design gate gets the same treatment
    Given the design gate's presentation report blocks on heading_not_sentence_case_pt at slide 2
    When the runner ticks at the design gate
    Then the policy reason is content_quality
    And the checkpoint copy is repaired and the design gate is approved

  Scenario: Repair still runs before an escalation at the revision cap
    Given the content gate already used both revisions and blocks on a casing rule
    When the runner ticks at the content gate
    Then the gate is repaired and approved instead of escalated

  Scenario: Without a gate repairer the runner revises as before
    Given the worker has no gate repairer wired
    When the runner ticks at a content gate that blocks on a casing rule
    Then the content phase is revised with reason content_quality

  Scenario: Final review stays with the owner
    Given a carousel at final review with a blocking presentation rule
    When the runner ticks
    Then the run moves to awaiting_owner and the owner's "Fix issues" button offers the repair
