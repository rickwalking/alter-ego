# language: en
@AE-0513 @frontend @dashboard
Feature: The personas page reads cleanly in Portuguese and English, on desktop and phone
  The persona cards show a sensible avatar, translated fallbacks and their
  actions inside the card; the tone sliders show their value and can be used
  from the keyboard; the empty list offers the primary action; and the page
  fits a 390 px phone with touch targets of at least 44 px.

  Scenario: The avatar shows the first letter of the name
    Given a persona named "[Ágata] rascunho"
    When the personas page lists it
    Then its avatar shows "Á"

  Scenario: The avatar initial is uppercased
    Given a persona named "élan"
    When the personas page lists it
    Then its avatar shows "É"

  Scenario: A name without letters shows an avatar icon
    Given a persona named "123 ⚙"
    When the personas page lists it
    Then its avatar shows a person icon labelled for that persona
    And no digit or symbol is used as the initial

  Scenario: A persona without a description says so in the page language
    Given a persona with no description and no opinion style
    When the personas page lists it in Portuguese
    Then its card reads "Sem descrição"
    When the page is in English
    Then its card reads "No description"

  Scenario: A persona without expertise gets a translated role
    Given a persona with no expertise areas
    When the personas page lists it
    Then its card shows the translated default role

  Scenario: Expertise beyond the visible chips is counted
    Given a persona with more expertise areas than the card shows
    When the personas page lists it
    Then the card shows a "+N" chip for the hidden areas

  Scenario: Edit and Delete sit inside the persona card as touch-sized buttons
    Given a persona
    When the personas page lists it
    Then its Edit and Delete buttons are inside its card
    And each button is at least 44 px tall

  Scenario: Tone sliders show their value and work from the keyboard
    Given the persona form
    When the editor tabs to a tone slider
    Then the slider has focus and announces its value as a percentage
    And the value is shown next to the slider
    When the slider value changes
    Then the shown percentage follows it

  Scenario: An empty persona list shows a welcoming empty state with the primary action
    Given the API has no personas
    When the editor opens the personas page
    Then the empty state title says there are no personas yet
    And a touch-sized "Create your first persona" button opens the form

  Scenario: A search without matches keeps its own title
    Given personas that do not match the search
    When the editor searches for "zzz"
    Then the empty state says nothing was found for "zzz"
    And it offers no create button

  Scenario: The personas page keeps touch-sized controls on a 390 px phone
    Given a 390 px wide screen
    When the editor opens the personas page and the persona form
    Then the search box, every form text box and every form button are at least 44 px tall
    And the page has no horizontal scroll
