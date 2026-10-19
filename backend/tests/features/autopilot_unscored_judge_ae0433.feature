Feature: An unscored persona judge never escalates a passing run (AE-0433)
  Prod 2026-10-19 (run 8e484fe5, carousel 5344b6c6): the persona judge timed
  out twice (unscored) after the slide fix rewrote slides 3 and 7; the fix
  kept the slides' old low voice scores, the gate re-read still failed on
  the voice floor and the run escalated "persona_score_below_threshold"
  with failing_slides []. A judge that gives no score is not a verdict: it
  is retried on the next model of the role's queue, the slide is re-scored
  on the next tick, and only a judge that stays unavailable escalates, with
  its own reason. The persona floor itself is unchanged.

  Background:
    Given an autopilot run at the content gate
    And slide 3's voice score is 55, under the floor 70

  Scenario: A judge timeout on the first model is retried on the next model of the queue
    Given the fast role's queue has two models
    And the persona judge times out on the first model
    And the next model of the queue scores the text 82
    When the voice judge scores a slide
    Then the second call goes to the next model of the queue
    And the slide's score is 82

  Scenario: Judge timeout then success on the fallback approves the gate
    Given the slide fix rewrites slide 3
    And the persona judge times out on the first model and scores 82 on the fallback
    When the runner ticks
    Then slide 3's stored voice score is 82
    And the gate is approved

  Scenario: An unscored judge leaves the run generating and marks the slide for a re-score
    Given the slide fix rewrites slide 3 and the rewrite passes every rule
    And the persona judge gives no score on any model
    When the runner ticks
    Then the run is not escalated and stays generating
    And slide 3 keeps its old voice score marked "rescore_pending" with 1 unscored tick
    And no "autopilot_slide_autofix_escalated" is logged

  Scenario: A pending slide is re-scored on the next tick without a rewrite
    Given slide 3 is marked "rescore_pending" after an unscored tick
    And the persona judge now scores slide 3's current text 80
    When the runner ticks
    Then the slide is not rewritten
    And slide 3's stored voice score is 80 without the pending marker
    And the gate is approved

  Scenario: A judge that stays unavailable escalates with its own reason
    Given AUTOPILOT_PERSONA_UNSCORED_MAX_TICKS is 2
    And slide 3 is marked "rescore_pending" after 1 unscored tick
    And the persona judge gives no score on any model
    When the runner ticks
    Then the run is escalated with reason "persona_judge_unavailable"
    And never with reason "persona_score_below_threshold"

  Scenario: A real low score still escalates on the voice floor
    Given the persona judge scores every rewrite of slide 3 at 50
    When the runner ticks
    Then the run is escalated with reason "persona_score_below_threshold"
    And the escalation lists "slide 3"

  Scenario: A re-score that is still low goes back to the rewrite loop
    Given slide 3 is marked "rescore_pending" after an unscored tick
    And the persona judge scores slide 3's current text 50 and its rewrite 85
    When the slide fix runs
    Then slide 3 is rewritten and fixed with the score 85
