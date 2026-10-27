@AE-0563 @frontend @dashboard
Feature: Coherent and fresh cover-photo prompt suggestions
  Scenario: Every suggestion is a physically coherent scene
    Given a carousel with a topic
    When the owner looks at any round of cover prompt suggestions
    Then an indoor-only light is only used in an indoor location
    And an outdoor-only light is only used in an outdoor location
    And a pose that needs a jacket collar, stairs or a railing gets one
    And a close-up or half-body shot never carries a full-body pose
    And a prop that sits on a desk or table is only used where there is one

  Scenario: Outras ideias brings genuinely new scenes
    Given the curated suggestions of one round are shown
    When the owner presses "Outras ideias"
    Then no new suggestion shares more than one value with any suggestion of the previous round
    And most props of the new round were not in the previous round

  Scenario: Each round stays varied and stable
    Given any seed and round
    Then the six suggestions never share an option of any dimension
    And no suggestion contains a hex code
    And the same seed and round always give the same suggestions
