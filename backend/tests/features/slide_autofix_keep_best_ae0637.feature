Feature: The autopilot slide fix keeps its best attempt (AE-0637)

  Prod carousel 4223b53a, slide 8 (summary): after an owner Retry the autopilot
  slide fix ran 5 attempts. Attempt 2 cleared every copy rule and left only the
  voice floor; attempt 3 started from that copy, made a body too long again, and
  attempts 4 and 5 timed out. The slide fix then wrote nothing at all, so the
  fixes of attempt 2 were lost and the run escalated with the original errors.
  The judge also scored only the PT body or, when it is empty as on a summary
  slide, the heading, never the summary points the rewrite changed.

  Background:
    Given a slide that breaks a copy rule and scores under the voice floor

  Scenario: A slide no attempt fixed keeps its best attempt
    When the rewrite clears the copy rule but the voice stays under the floor
    Then the slide is not fixed but marked improved
    And its best copy and that copy's score are written

  Scenario: An attempt that makes the slide worse is dropped
    Given attempt 1 clears the copy rule and attempt 2 breaks it again
    When attempt 3 runs
    Then it starts from the copy of attempt 1
    And the slide comes back with the copy of attempt 1

  Scenario: A slide no attempt improved keeps its stored copy
    When every attempt still breaks the copy rule
    Then the slide is neither fixed nor improved
    And its stored copy is kept

  Scenario: The voice judge reads the slide's whole visible copy
    When a rewritten slide is voice-scored
    Then the judge reads its heading, body, items and TL;DR, as the content phase does

  Scenario: One rewrite waits longer than the reasoning model and its fallback
    Then the rewrite timeout is longer than the reasoning timeout plus the fallback timeout
