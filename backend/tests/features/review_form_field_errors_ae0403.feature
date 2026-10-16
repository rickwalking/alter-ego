Feature: Per-field validation errors and manual fixes on the slide review forms (AE-0403)
  As a carousel owner fixing slide copy by hand
  I want each validation error shown on the field that caused it
  So that I can fix exactly those fields and submit my manual fixes

  # Backend coverage:
  #   tests/unit/api/test_slide_edit_field_errors_ae0403.py
  # Frontend coverage:
  #   frontend/tests/features/review-form-field-errors.feature

  Scenario: The edit sanitizer keeps balanced EN emphasis tags
    Given an edited EN slide body "A <strong>bold</strong> claim."
    When the edit is sanitized on the wire
    Then the saved EN body is still "A <strong>bold</strong> claim."
    And PT "**" emphasis is kept as well

  Scenario: The edit sanitizer still strips other markup and injection patterns
    Given an edited body with a "<script>" tag and "ignore previous instructions"
    When the edit is sanitized on the wire
    Then no "<script>" tag survives
    And the injection pattern is removed

  Scenario: A refused save returns violations addressed to their fields
    Given a completed carousel whose edited EN body on slide 9 breaks a rule
    When the owner saves the slide edit
    Then the response is blocking
    And field_violations lists the code, message, slide 9, locale "en" and field "body"

  Scenario: A structured-item violation names the item and sub-field
    Given a violation on field "summary_points[1].title"
    When the response is built
    Then the field violation has item_list "summary_points", item_index 1 and item_field "title"

  Scenario: A fixed resubmit succeeds
    Given a save that was refused for slide 9
    When the owner fixes the flagged field and submits the manual fixes
    Then the response is not blocking and field_violations is empty
