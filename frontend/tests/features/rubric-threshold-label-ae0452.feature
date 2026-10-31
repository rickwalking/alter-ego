@AE-0452 @frontend
Feature: Rubric thresholds read as a share of the criterion's scale
  A criterion threshold is stored as a fraction (0.0-1.0) of its scoring scale.
  The rubric board shows it as a percentage of that scale, not as a raw fraction
  next to a 0-100 scale.

  Scenario: A criterion threshold shows as a percentage of its scale
    Given a 0-100 criterion with threshold 0.7 and a 1-10 criterion with threshold 0.8
    When the rubric board shows them
    Then they read "≥ 70% (0–100)" and "≥ 80% (1–10)"
