Feature: Variable slide count and slide roles (AE-0374, ADR-0021)
  A presentation contract may declare a slide-count range and a role per slide.
  Fixed contracts (v1-v3) keep their exact behaviour.

  # --- Loader ---------------------------------------------------------------

  Scenario: Fixed contracts are unchanged
    Given the hero_lower_third_v3 contract
    When it is loaded
    Then it accepts exactly 7 slides and has no roles

  Scenario Outline: POV deck sizes
    Given the pov_hook_v1 contract
    When it is expanded for <slides> slides
    Then it has <points> point slides
    And the roles end with twist, save, cta
    And the slides are numbered 1 to <slides>

    Examples:
      | slides | points |
      | 8      | 2      |
      | 9      | 3      |
      | 10     | 4      |

  Scenario: Radar IA v4 with the optional twist
    Given the hero_lower_third_v4 contract
    When it is expanded for 7 slides
    Then the roles are hook, news, impact, impact, impact, verdict, cta
    And only the hook and impact slides need artwork

  Scenario: Expanding outside the range fails
    Given the pov_hook_v1 contract
    When it is expanded for 11 slides
    Then the loader raises slide_count_out_of_range

  Scenario Outline: Invalid ranged contracts are rejected
    Given a contract with <problem>
    When it is loaded
    Then it fails with presentation_policy_invalid

    Examples:
      | problem                                  |
      | an unknown role                          |
      | a role that does not match its type      |
      | roles on only some slides                |
      | a minimum above the maximum              |
      | a maximum different from the sequence    |
      | optional slides without a range          |
      | too few optional slides for the range    |

  # --- Project policy ---------------------------------------------------------

  Scenario: Projects are stamped by mode
    When a POV carousel is created
    Then it is stamped pov_hook_v1
    When a Radar IA carousel is created
    Then it is stamped hero_lower_third_v4

  Scenario: A project's policy is sized to its slide count
    Given a POV project with 8 slides
    Then its policy has 8 slides
    Given a POV project without a slide count
    Then its policy has the contract default of 9 slides

  # --- Outline normalization ---------------------------------------------------

  Scenario: Legacy outline unchanged
    Given an outline of 9 slides without roles
    When it is normalized
    Then it is trimmed to 7 slides with the canonical slide types

  Scenario: Roles are stamped by position, never taken from the model
    Given a POV policy for 9 slides and an outline whose roles are wrong or missing
    When the roles are stamped
    Then every slide gets the role and type of its position

  Scenario: Role outline keeps roles up to 10 slides
    Given an outline of 10 slides with roles
    When it is normalized
    Then it keeps 10 slides and each role's slide type

  # --- Deck rule --------------------------------------------------------------

  Scenario: Outline too long
    Given a POV deck of 11 slides
    When it is validated
    Then slide_count_invalid is reported as a blocker

  Scenario: Legacy decks never get the deck rule
    Given a v3 deck of 6 slides
    When it is validated
    Then no slide_count_invalid is reported
