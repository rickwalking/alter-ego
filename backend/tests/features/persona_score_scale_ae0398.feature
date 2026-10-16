Feature: Voice scores are on 0-100 (AE-0398)
  The voice gate's floor is 70 on 0-100. The scoring prompt does not name the
  scale, and the model often answers on 0-10 (prod 2026-10-16: overall 8.2-8.9
  for on-voice copy), so every POV voice gate failed.

  Scenario: A 0-10 answer is scaled to 0-100
    Given the scorer answers overall 8.5 with every score at most 10
    When the answer is parsed
    Then overall is 85 and every score is multiplied by 10

  Scenario: A 0-100 answer is kept as is
    Given the scorer answers overall 82 with tone_match 90
    When the answer is parsed
    Then the scores are unchanged

  Scenario: An all-zero or unreadable answer stays at 0
    Given the scorer answers all zeros, or text that is not JSON
    When the answer is parsed
    Then every score is 0 and the gate fails closed

  Scenario: On-voice copy passes the voice floor
    Given the scorer answers overall 8.2 on the 0-10 scale
    When the gate compares it with the floor of 70
    Then it passes
