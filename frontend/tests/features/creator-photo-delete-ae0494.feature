@AE-0494 @frontend @create
Feature: Delete a photo from the slide-1 photo library in the wizard
  Scenario: Deleting an unused photo after confirming
    Given the slide-1 photo library shows two photos
    When the owner presses "Excluir foto" on one and confirms
    Then the photo is deleted and the library refreshes

  Scenario: Cancelling the delete keeps the photo
    Given the delete confirmation of a photo is shown
    When the owner presses "Cancelar"
    Then nothing is deleted

  Scenario: A photo in use lists the carousels that use it
    Given a carousel uses the photo
    When the owner confirms the delete
    Then the section names the carousels that use the photo with a link to each
    And the photo stays in the library

  Scenario: Deleting the selected photo selects the newest remaining one
    Given the deleted photo was the selected slide-1 photo
    When the delete succeeds
    Then the newest remaining photo is selected
