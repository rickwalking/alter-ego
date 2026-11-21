Feature: A fix revision voice-scores the slides it rewrote (AE-0638)

  Prod carousel 4223b53a: the AE-0636 fix cleared slide 8's 9 violations, but the
  fix path never voice-scored the rewritten slide. Its stored score (66) still
  belonged to the old copy, so the autopilot escalated on a voice floor it had
  never measured for the copy on the slide.

  Scenario: A fix re-scores only the slides it rewrote
    Given a carousel parked at a blocked content gate with stored voice scores
    When a system retry fixes slide 2
    Then the judge scores only slide 2's new copy
    And slide 2's voice score is the new score
    And every other slide keeps its stored score
