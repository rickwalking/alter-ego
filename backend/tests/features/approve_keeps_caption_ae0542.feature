Feature: Approving a carousel for publishing never loses its caption
  On prod, approving a carousel from Telegram ("Publicar agora") emptied its saved
  caption and the autopilot posted to Instagram without one. A blog draft created from
  the carousel had an empty distribution home; loading the carousel overlaid that empty
  caption, and the public release saved it back over the real one.

  Scenario: Publish now keeps the saved caption and posts it
    Given a carousel at final review with a saved caption and a blog draft created from it
    And its autopilot run is waiting for the owner
    When the owner taps "Publicar agora"
    Then the run is publishing, the carousel is approved for publishing and public
    And the carousel and its distribution home still hold the saved caption
    And the Instagram post carries that caption

  Scenario: A blog draft with an empty distribution never wipes the caption
    Given a carousel with a saved caption whose blog row has an empty distribution
    When the carousel is loaded and saved again
    Then the saved caption is kept and copied into the distribution home
    And a caption the owner cleared on purpose stays cleared

  Scenario: A blog draft from a carousel starts with the carousel's saved copy
    When a blog draft is created from a carousel
    Then its distribution holds the carousel's caption and LinkedIn posts
    And a standalone draft or a draft for an unknown carousel starts empty

  Scenario: The autopilot worker never posts an empty caption
    Given a publishing run whose carousel caption is empty or blank
    When the publish worker runs
    Then the run fails with the reason instagram_caption_empty and nothing is sent to Instagram
    And the owner gets a Telegram notice with a retry button

  Scenario: The manual publish refuses an empty caption
    When the owner publishes a carousel with an empty or blank caption
    Then the publish is refused with instagram_caption_empty before any Instagram call

  Scenario: A workflow stuck before the final review interrupt is re-driven
    Given the images gate was approved and the run died before the final review opened its review
    And nothing has run for longer than the grace period
    When the autopilot runner reads the gate
    Then the workflow counts as parked and is re-driven instead of waiting forever
    And an approved carousel held for publishing is still never parked
