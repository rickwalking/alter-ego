Feature: POV hook voice diversity (AE-0580)
  Consecutive carousels must not open with the same formulas and openings
  ("Opinião impopular: ..."). The hook prompt sees the owner's recent slide-1
  openings and forbids reusing them or their formulas, and the chosen hook
  rotates across the candidates instead of always taking the first. The
  persona voice gate is untouched.

  Scenario: Recent openings are listed and forbidden
    Given the owner has recent POV openings
    When the v2 hook prompt renders
    Then it lists each recent opening
    And it forbids reusing them, their variations and their formulas

  Scenario: No recent openings, no exclusion block
    When the v2 hook prompt renders without recent openings
    Then it carries no exclusion block

  Scenario: The hook call renders v2 with the recent openings
    Given a POV hook request with recent openings
    When the outline agent generates the hook candidates
    Then the carousel_pov hook prompt renders at v2 with those openings

  Scenario: The chosen hook rotates across the candidates
    Given the same five hook candidates for consecutive carousels
    When the outline attaches the hook with the owner's opening count as the seed
    Then consecutive carousels do not reuse the same candidate
    And the same count always picks the same candidate

  Scenario: A candidate repeating a recent opening is dropped
    Given the model returns a candidate identical to a recent opening
    When the outline attaches the hook
    Then that candidate is dropped from slide 1 and never chosen

  Scenario: The owner's saved hook still wins
    Given a saved hook and a candidate list and any seed
    When the outline attaches the hook
    Then slide 1's title is the saved hook

  Scenario: Recent openings come from the owner's other carousels
    Given the owner's recent carousels and another owner's carousel
    When the recent openings load for a new project
    Then only the owner's slide-1 headings come back, newest first
    And the new project itself contributes nothing

  Scenario: Recent openings degrade to none without a database
    When the recent openings load without a session
    Then the list is empty
