# AE-0611 — A re-drafted slide keeps the old EN copy, and the slide rows keep the pre-retry card
Feature: A re-drafted slide stays in step with its EN copy and its slide row
  The EN translation is made once, before the fail-closed retry. When the retry
  re-drafts a PT slide, EN has to follow the new PT, and the slide row has to show
  the new slide as soon as the retry is done, not only when the phase ends.

  Scenario: A re-drafted slide gets its EN copy from the new PT
    Given a slide that blocks the first review and has an EN translation
    And the single retry answers with new PT copy
    When the content phase builds both locales
    Then the EN slide shows the translation of the new PT
    And the stored EN translation of that slide is the new one

  Scenario: Only the re-drafted slides are translated, in one call
    Given a deck where two slides are re-drafted by the retry
    When the content phase builds both locales
    Then one translation call runs and it holds only those two slides
    And the other slides keep their stored EN translation

  Scenario: The translator sees the PT copy the reviewer will see
    Given the retry answers with a labelled scaffold draft
    When the re-drafted slide is translated
    Then the translator gets the PT heading and body recovered from the scaffold
    And it never gets the raw scaffold

  Scenario: A re-draft that carries its own EN needs no translation
    Given the retry answers with a draft that holds both locales
    When the content phase builds both locales
    Then no translation call runs
    And the EN slide shows the EN copy of the fresh draft

  Scenario: A failed translation never keeps the old EN copy
    Given the translation of the re-drafted slide fails
    When the content phase builds both locales
    Then the old EN copy is not shown
    And the failure is logged with the slide numbers
    And the slide stays blocked for the gate repair or the reviewer

  Scenario: A translation that skips the slide never keeps the old EN copy
    Given the translator answers without the re-drafted slide
    When the content phase builds both locales
    Then the old EN copy is not shown
    And the failure is logged with the slide numbers
    And the slide stays blocked for the gate repair or the reviewer

  Scenario: A provider failure of the translation call never keeps the old EN copy
    Given the translation call of the re-drafted slide fails at the provider
    When the content phase builds both locales
    Then the old EN copy is not shown
    And the failure is logged with the slide numbers

  Scenario: A model queue with no model left never keeps the old EN copy
    Given every model of the translation queue is unavailable
    When the content phase builds both locales
    Then the content phase does not raise
    And the old EN copy is not shown
    And the failure is logged with the slide numbers
    And the slide stays blocked for the gate repair or the reviewer

  Scenario: A bug in the translation call is not taken for a failed call
    Given the translation call of the re-drafted slide raises an unexpected error
    When the content phase builds both locales
    Then the error reaches the caller

  Scenario: Nothing is translated when no slide was re-drafted
    Given a deck that blocks and a retry that answers with no draft
    When the content phase builds both locales
    Then no translation call runs
    And every slide keeps its stored EN translation

  Scenario: Nothing is translated for a deck without stored translations
    Given a deck that has no EN translations yet
    And the retry re-drafts a slide
    When the content phase builds both locales
    Then no translation call runs

  Scenario: The slide row follows the retry before the gate repair runs
    Given slide rows written from the first drafts, with a quote card in PT and EN
    And the retry re-drafts that slide without the card
    When the gate repair starts
    Then the slide row already shows the new PT copy and its new EN copy
    And neither locale of the row has the card

  Scenario: The rows are not rewritten when no slide was re-drafted
    Given a deck that blocks and a retry that answers with no draft
    When the gate repair starts
    Then the slide row still shows what it showed before the review

  Scenario: The row EN content kind follows the new EN copy
    Given a slide row whose EN translation has the card's content kind
    When the reviewed copy without the card is written to the row
    Then the row's EN translation has no stale content kind
    And the copy rebuilt from the rows has no translation_shape_mismatch
