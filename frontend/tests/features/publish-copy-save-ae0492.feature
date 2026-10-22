Feature: The publish page saves the caption and the LinkedIn posts
  As the owner of a carousel
  I want the caption and LinkedIn post edits saved on the server
  So that a reload, a copy or an Instagram publish uses the text I wrote

  Scenario: Saving the edited caption sends it with the loaded lock version
    Given the publish page of a carousel loaded at lock version 3
    When the owner edits the Instagram caption and clicks Save
    Then the caption is sent to PATCH /api/carousels/{id}/copy with If-Match 3
    And the page shows "Salvo"

  Scenario: The next save uses the lock version returned by the last save
    Given the owner saved the caption and the server answered lock version 4
    When the owner saves again before the page refreshed
    Then the second save sends If-Match 4

  Scenario: Saving a LinkedIn post sends only the edited languages
    Given the LinkedIn tab
    When the owner edits the PT post and saves
    Then only linkedin_post_pt is sent

  Scenario: Copy and publish wait for the edit to be saved
    Given the owner edited the caption without saving
    Then "Copiar legenda" and "Publicar no Instagram" are disabled with a hint to save first
    And after saving, publishing sends the saved caption

  Scenario: A refreshed project keeps the edits that were not saved
    Given the owner edited the caption and saved the LinkedIn post
    When the project is refetched with the saved post
    Then the unsaved caption edit is still in the editor

  Scenario: A refused save explains why
    When the save is refused as stale, as already published, or while a run is active
    Then the page shows the matching message and keeps the edited text

  Scenario: Leaving with unsaved edits asks first in the page's own dialog
    Given the owner edited a text without saving
    When they follow a link to another dashboard page
    Then a dialog asks whether to discard the edits
    And "Continuar editando" keeps them on the page
    And "Descartar e sair" follows the link
