@AE-0547 @frontend @publish
Feature: Prompt suggestions in the publish step's cover generation
  As the owner generating a cover from my photos
  I want the same prompt suggestions as in the create wizard
  So that I can start from a good direction instead of a blank field

  Scenario: The cover dialog offers prompt suggestions for the carousel
    Given the publish page of a Ponto de Vista carousel with library photos
    Then the "Gerar capa com Grok" prompt shows suggestions for the carousel's topic and palette

  Scenario: Tapping a suggestion fills the prompt, which stays editable
    When the owner taps a suggestion
    Then the prompt field holds that suggestion
    And the owner can still edit it before generating
