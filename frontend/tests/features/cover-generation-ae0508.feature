@AE-0508 @frontend @publish
Feature: Generate a slide-1 cover from library photos with Grok on the publish step
  As the owner of a Ponto de Vista carousel
  I want to ask Grok for a new cover made from my own photos
  So that I can pick a fresh slide-1 image without a photo shoot

  Background:
    Given the publish page of a finished Ponto de Vista carousel with library photos

  Scenario: The owner generates a cover after confirming
    When the owner ticks a photo, writes a prompt and clicks "Gerar capa"
    Then a confirmation names OpenAI (ChatGPT), the number of photos and the caps
    When the owner confirms
    Then the generation is requested with the photos, the prompt and confirmed true
    And a progress line says the cover is being generated

  Scenario: Cancelling the confirmation sends nothing
    When the owner clicks "Gerar capa" and cancels the confirmation
    Then no generation is requested

  Scenario: A finished generation appears as a cover option
    Given a generation succeeded
    Then the cover options are refreshed and the generated cover is labelled "Capa gerada"

  Scenario: A failed generation can be retried
    Given the last generation failed
    Then the failure reason is shown with "Tentar de novo"
    When the owner clicks "Tentar de novo" and confirms
    Then the same photos and prompt are requested again

  Scenario: The action needs a prompt
    Given the prompt is shorter than 3 characters
    Then "Gerar capa" is disabled

  Scenario: A reached cap disables the action with the reason
    Given the carousel used 4 of 4 generations
    Then "Gerar capa" is disabled and the reason names the per-carousel cap
    Given the month used 40 of 40 generations
    Then "Gerar capa" is disabled and the reason names the monthly cap

  Scenario: The attempt ceiling disables the action with the reason
    Given the carousel used 12 attempts or the month used 120 attempts, failures included
    Then "Gerar capa" is disabled and the reason names the attempt ceiling

  Scenario: The usage line says when the monthly limit resets
    Then the usage line says the monthly limit resets at 21:00 BRT on the last day of the month

  Scenario: At most three photos can be sent
    Given three photos are ticked
    Then the other photos cannot be ticked
