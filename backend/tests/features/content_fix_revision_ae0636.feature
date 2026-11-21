Feature: A system retry of a blocked content gate fixes fields, it does not re-draft (AE-0636)

  Prod carousel 4223b53a: the content gate blocked only slide 8's three summary
  bodies (over 90 characters, EN using "**" emphasis). Three owner Retries each
  re-drafted all 9 slides from a note that named no slide, so every retry
  brought new violations elsewhere and the persona score fell from 77 to 30.
  The targeted field repair that should have fixed slide 8 timed out at 180 s,
  before the fast model's own 300 s timeout and its fallback, and gave up.

  Background:
    Given a carousel parked at the content gate
    And the content gate blocks slide 2 PT "features[0].body" for being too long

  # --- A: fix, not rework ---------------------------------------------------

  Scenario: A system retry of a blocked gate rewrites only the blocked fields
    When the owner retries and the system writes the revise note
    Then no slide is re-drafted
    And the field repair is asked for "2:pt:features[0].body"
    And every other slide keeps its stored copy
    And the content gate is no longer blocking
    And the retry note is recorded as "applied"

  Scenario: A fix that changes nothing keeps the deck and records the note unchanged
    Given the field repair model answers nothing
    When the owner retries and the system writes the revise note
    Then no slide is re-drafted
    And the localized slides are unchanged
    And the retry note is recorded as "unchanged"

  Scenario: An owner's own revise note still re-drafts the content
    When the owner sends the revise note "Make slide 2 more concrete"
    Then the content is re-drafted with that note

  Scenario Outline: Only a blocked gate with system notes is a fix
    Given the active content notes come from "<sources>"
    And the content gate blocking is <blocking>
    Then the revision is a fix: <fix>

    Examples:
      | sources           | blocking | fix   |
      | autopilot         | true     | true  |
      | autopilot,human   | true     | false |
      | human             | true     | false |
      | untagged          | true     | false |
      | autopilot         | false    | true  |
      | autopilot persona | false    | false |
      | none              | true     | false |

  Scenario: A first draft is never a fix
    Given the carousel has no stored drafts yet
    And the only active note is system-written
    Then the revision is not a fix

  # --- B: the repair loop outlasts a slow model --------------------------------

  Scenario: A failed repair round does not end the loop
    Given the field repair model fails on round 1 and answers on round 2
    When the content gate runs its repair loop
    Then the model is called 2 times
    And the content gate report is no longer blocking

  Scenario: One repair round waits longer than the fast model and its fallback
    Then the repair round timeout is longer than the fast timeout plus the fallback timeout
