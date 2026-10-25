@AE-0551 @backend @carousel @image-bridge
Feature: Generate a slide-1 cover from a text prompt alone
  As the owner of a Ponto de Vista carousel
  I want Grok to make a cover from my description without any photo
  So that I can get a new cover even when no photo of mine fits

  Background:
    Given a finished Ponto de Vista carousel owned by the owner

  Scenario: A confirmed generation without photos runs a text-only job
    When the owner asks for a cover with a prompt, no photo ids, and confirms
    Then the API answers 202 with a pending generation
    And the bridge job has no photos and the text-only cover prompt
    And the generated image is stored as a creator asset with role cover
    And the generation is succeeded with that asset and photo count 0

  Scenario: The photo ids may be absent
    When the owner asks for a cover with a prompt and no photo_ids field, and confirms
    Then the API answers 202 with a pending generation

  Scenario: A text-only job sends exactly the text body
    Given a cover job without photos
    When the bridge delivers it to the Grok Bot
    Then the webhook body has the text-only fields, no operation and no image
    And its metadata content type is carousel_cover with the bridge's model

  Scenario: Photo ids are still checked
    When the owner sends more than three photo ids, or a photo that is not theirs
    Then the API refuses the generation and records nothing

  Scenario: A text-only generation follows the same caps and lock
    Given a pending generation on the carousel, or a reached cap
    When the owner asks for a cover without photos
    Then the API answers 409 with the same code as with photos

  Scenario: The text-only prompt keeps the direction as data
    When the text-only cover prompt is rendered with a direction that tries to close the markers
    Then the direction stays between the markers and the prompt asks for no reference images
