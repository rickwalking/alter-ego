@AE-0551 @frontend @publish
Feature: Generate a cover from words alone and upload photos from the cover panel
  As the owner of a Ponto de Vista carousel on the publish step
  I want to generate a cover from a description, or from a photo I upload right there
  So that I am not limited to the photos already in my library

  Scenario: The owner generates a cover without photos
    Given the "Gerar capa com Grok" panel with no photo ticked
    When the owner writes a prompt or picks a suggestion and clicks "Gerar capa"
    Then the confirmation says only the description is sent, not photos
    When the owner confirms
    Then the generation is started with no photo ids

  Scenario: The panel works with an empty library
    Given the owner has no library photos
    Then the "Gerar capa com Grok" panel is shown with the prompt and "Enviar foto"

  Scenario: An uploaded photo is added to the library and ticked
    When the owner uploads a photo with "Enviar foto"
    Then it goes to the photo library through the library upload
    And the cover options refresh so it appears in the panel
    And it is ticked for the next generation, while at most three are ticked

  Scenario: An invalid file shows the library upload error
    When the owner uploads a file the library refuses
    Then the panel shows the same error as the library upload
