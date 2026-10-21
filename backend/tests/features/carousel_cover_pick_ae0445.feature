Feature: Change slide 1's photo of a Ponto de Vista carousel on the publish step (AE-0445)
  As the account owner
  I want to swap slide 1's photo for another photo of my library (or the GrokBot cover)
  So that a finished POV carousel uses the photo I want before I publish it

  Background:
    Given a completed "pov" carousel owned by the owner at final review
    And slide 1 shows the owner's library photo "A"
    And the owner's library also has the photo "B"

  # --- Options ----------------------------------------------------------------

  Scenario: The options are the owner's library photos, the current one marked
    When the owner asks for the cover options
    Then the options are "A" and "B" from the library
    And "A" is the current slide-1 photo

  Scenario: The GrokBot cover offer of the autopilot run is an option too
    Given the carousel's autopilot run has a GrokBot cover offer "G"
    When the owner asks for the cover options
    Then the options include "G" as a GrokBot offer

  Scenario: A library photo whose file is gone is not offered
    Given the stored file of "B" is gone
    When the owner asks for the cover options
    Then "B" is not an option

  Scenario: A Radar IA carousel has no cover options
    Given the carousel is in content mode "news_analysis"
    When the owner asks for the cover options
    Then the response is 422 with detail "cover_pick_not_pov"

  # --- Switch -----------------------------------------------------------------

  Scenario: Choosing another library photo re-renders slide 1 from it
    When the owner chooses "B" at the current lock version
    Then "B" is staged where the slides render
    And the project's slide-1 photo is "B" and no GrokBot cover is set
    And the lock version moves on
    And the carousel is re-rendered through the republish path (hero images reused)

  Scenario: Choosing a library photo replaces a GrokBot cover chosen on Telegram
    Given slide 1 shows the GrokBot cover "G"
    When the owner chooses "B" at the current lock version
    Then no GrokBot cover is set and the slide-1 photo is "B"

  Scenario: Choosing the GrokBot offer stores it as the slide-1 cover
    Given the carousel's autopilot run has a GrokBot cover offer "G"
    When the owner chooses "G" at the current lock version
    Then the project's slide cover is "G"
    And the carousel is re-rendered

  Scenario: A stale lock version is a conflict and writes nothing
    When the owner chooses "B" at an older lock version
    Then the response is 409 with code "version_conflict"
    And the slide-1 photo is still "A"
    And nothing is re-rendered

  Scenario: An active workflow run is a conflict
    Given a workflow run is in progress for the carousel
    When the owner chooses "B"
    Then the response is 409 with code "resume_already_in_progress"

  Scenario Outline: Refused choices
    Given <situation>
    When the owner chooses <asset>
    Then the response is 422 with detail "<code>"
    And nothing is written

    Examples:
      | situation                                   | asset                    | code                         |
      | the carousel is in content mode "news_analysis" | "B"                  | cover_pick_not_pov           |
      | the carousel is not completed               | "B"                      | cover_pick_not_completed     |
      | another user's photo "X" exists             | "X"                      | cover_pick_asset_not_allowed |
      | nothing                                     | an unknown asset id      | cover_pick_asset_not_allowed |
      | the stored file of "B" is gone              | "B"                      | cover_pick_asset_not_allowed |

  Scenario: Another user cannot change the cover
    When a different editor chooses "B"
    Then the response is 403

  Scenario: A failed re-render is reported, the choice stays stored
    Given the republish fails with "render failed"
    When the owner chooses "B" at the current lock version
    Then the response is 422 and lists "render failed"
    And the slide-1 photo is "B"
