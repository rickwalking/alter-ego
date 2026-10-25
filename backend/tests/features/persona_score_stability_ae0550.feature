Feature: The persona voice gate is stable and a hand edit can clear it
  The content approve gate refuses a slide whose voice score is under 70. The
  scores moved by 40+ points on unchanged copy between two runs, the judge read only
  the slide body, and a hand edit never re-scored anything, so the owner was stuck
  unless they paid for an LLM revision.

  Scenario: An unchanged slide keeps its score
    Given every slide was scored and the scores carry the fingerprint of the judged copy
    When the content phase scores the slides again with the same copy
    Then the judge is not called and every score is the same as before

  Scenario: An edit that improves the voice clears the gate
    Given slide 2 scored 62 and slide 1 scored 90
    When the reviewer hand-edits slide 2 and submits the edits only
    Then only slide 2 is judged again, its new score is stored, slide 1 keeps 90
    And the content approval is no longer refused for the voice score

  Scenario: The judge reads the slide's visible copy
    Given a checklist slide with a heading, a short body and three items
    When its voice text is built
    Then it holds the heading, the body, every item and the TL;DR strip, and falls back to the draft text without a presentation payload

  Scenario: A stale or unscored entry is judged again
    Given an entry without a fingerprint, one marked for a re-score, and one with no overall
    Then none of them is reused

  Scenario: A judge that gives no score never opens the gate
    Given slide 2 scored 62 and its copy was edited
    When the judge times out on the edited copy
    Then slide 2 keeps 62, marked for a re-score, and approval is still refused
