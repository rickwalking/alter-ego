@AE-0554 @frontend @publish
Feature: The cover panel offers uploads only to the owner and explains upload failures
  As the owner of a Ponto de Vista carousel on the publish step
  I want the cover panel to show its controls only when I can use them, and to say why an upload failed
  So that nobody uploads into the wrong library and I know what to fix

  Scenario: A viewer who is not the owner sees no upload or generate control
    Given a carousel the viewer does not own
    When the publish page shows the cover panel
    Then the viewer stays on the publish page and only the not-owner note is shown
    And there is no "Enviar foto" and no "Gerar capa"

  Scenario: No control is shown while the generation list loads
    Given the generation list is still loading
    Then the panel shows no "Enviar foto" and no "Gerar capa"

  Scenario: An upload failure says its cause
    When an upload is refused with 429, fails on the network, or fails with a server error
    Then the panel says to wait, to check the connection, or to try again
    When an upload is refused for the file itself
    Then the panel shows the wizard's upload sentence

  Scenario: The generation list polls only while a generation runs
    Given no generation is pending
    Then the list is not refetched on an interval
    Given a generation is pending
    Then the list is refetched on an interval until it settles

  Scenario: An uploaded photo is ticked once it is listed
    When the owner uploads a photo
    Then it is not ticked until the cover options list it
    And once listed it is ticked, while at most three are ticked
