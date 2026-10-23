@AE-0508 @backend @carousel @image-bridge
Feature: Generate a slide-1 cover from library photos with Grok
  As the owner of a Ponto de Vista carousel
  I want Grok to make a new cover from my own photos
  So that slide 1 can show a fresh image of me without a photo shoot

  Background:
    Given a finished Ponto de Vista carousel owned by the owner
    And the owner has library photos

  Scenario: A confirmed generation sends the photo bytes and stores a private cover
    When the owner asks for a cover from one photo with a prompt and confirms
    Then the API answers 202 with a pending generation
    And the Grok Bot webhook receives the photo bytes as reference images and no URL
    And the generated image is stored as a creator asset with role cover
    And the generation is succeeded with that asset

  Scenario: The generated cover is a cover option and can be picked
    Given a succeeded generation for the carousel
    When the owner lists the cover options
    Then the generated cover is offered with source generated and kind ai_image
    And the owner's library photos are still offered
    When the owner picks the generated cover
    Then slide 1 shows it as an ai_image cover

  Scenario: Generation needs an explicit confirmation
    When the owner asks for a cover without confirming
    Then the API answers 422 with cover_generation_not_confirmed
    And nothing is recorded

  Scenario: Only the carousel's owner can generate
    When an admin who does not own the carousel asks for a cover
    Then the API answers 403 with cover_generation_not_owner

  Scenario: An invalid request is refused before anything is recorded
    When the owner sends no photo, four photos, a blank or over-long prompt, an unknown field or no confirmation
    Then the API answers 422
    And nothing is recorded and nothing is sent to the Grok Bot

  Scenario: Another owner's photo cannot be sent
    When the owner asks for a cover from a photo that is not theirs
    Then the API answers 422 with cover_generation_photo_not_allowed

  Scenario: A Radar IA carousel cannot generate a cover
    When the owner asks for a cover on a news analysis carousel
    Then the API answers 422 with cover_pick_not_pov

  Scenario: A bridge failure leaves no asset and can be retried
    Given the Grok Bot fails the job
    When the owner asks for a cover and confirms
    Then the generation is failed with cover_generation_bridge_failed
    And no cover asset is stored
    And the failed generation does not count against the caps

  Scenario: An unusable image leaves no asset
    Given the Grok Bot returns an image that breaks the cover rules
    When the owner asks for a cover and confirms
    Then the generation is failed with cover_generation_invalid_image

  Scenario: One generation at a time per carousel
    Given a pending generation for the carousel
    When the owner asks for another cover
    Then the API answers 409 with cover_generation_in_progress

  Scenario: The per-carousel cap is four
    Given four succeeded generations for the carousel
    When the owner asks for another cover
    Then the API answers 409 with cover_generation_carousel_cap

  Scenario: The monthly cap is forty
    Given forty generations by the owner this month on other carousels
    When the owner asks for a cover
    Then the API answers 409 with cover_generation_monthly_cap

  Scenario: A run lost to a restart is reported as interrupted
    Given a pending generation older than the bridge timeout
    When the owner lists the generations
    Then it is failed with cover_generation_interrupted

  Scenario: The bridge is not configured
    Given the image bridge has no webhook URL
    When the owner asks for a cover and confirms
    Then the API answers 503 with cover_generation_unavailable
    And nothing is recorded

  Scenario: Every call is logged for the budget
    When a generation starts and ends
    Then the log carries the time, carousel, prompt SHA-256, model and cost
    And never the prompt text

  Scenario: Text-only bridge jobs keep the old webhook body
    When the images phase asks the bridge for a slide image
    Then the webhook body has no task and no reference_images keys
