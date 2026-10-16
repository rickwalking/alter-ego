Feature: Per-field validation errors and manual fixes on the review forms (AE-0403)
  As a carousel owner fixing slide copy by hand
  I want each validation error shown on the field that caused it, a summary at
  the bottom of each slide form, and a button to submit my manual fixes
  So that I know exactly what to fix and can re-submit without approving

  # Backend: backend/tests/features/review_form_field_errors_ae0403.feature
  # Tests:
  #   src/modules/publishing/distribution/components/slide-text-edit-section.field-errors.test.tsx
  #   src/app/dashboard/create/workspace/phase-review/content-phase-review.field-errors.test.tsx
  #   src/modules/editorial/workspace/lib/slide-field-errors.test.ts
  #   src/modules/editorial/workspace/field-errors-i18n.test.ts

  Background:
    Given a carousel slide 9 whose EN body breaks "emphasis_markup_invalid"

  Scenario: A refused save flags the offending field
    When the owner saves the slide edits and the backend refuses them
    Then the EN body of slide 9 has a red border and aria-invalid="true"
    And the message "Emphasis must use balanced <strong>…</strong> tags" sits under it via aria-describedby

  Scenario: A per-slide summary sits at the bottom of the slide form
    When the save is refused
    Then slide 9's form ends with "Slide 9 · EN body: Emphasis must use balanced <strong>…</strong> tags"
    And the global notice links to slide 9

  Scenario: A length violation names its limit
    Given the backend says "body exceeds max 220 characters (got 300)" for "body_too_long"
    Then the field message reads "Body too long (max 220 characters)"

  Scenario: An unknown violation code falls back to the backend message
    Given a violation with code "some_new_rule" and message "Backend says no"
    Then the field message reads "Backend says no"

  Scenario: Editing a flagged field clears its error
    Given the EN body of slide 9 is flagged
    When the owner edits that field
    Then the field has no error state and its summary line is gone

  Scenario: Submitting manual fixes succeeds
    Given a refused save
    When the owner edits the flagged field and clicks "Submit manual fixes"
    Then the edits are re-submitted
    And on success every error state is removed and the PDF rebuild is pending

  Scenario: Submitting manual fixes is refused again
    Given a refused save
    When the owner submits manual fixes and the backend refuses them again
    Then the new field errors are shown on their fields

  Scenario: Manual fixes at the content step save without approving
    Given the content step is blocked by a violation on slide 9
    When the owner edits the flagged field and clicks "Submit manual fixes"
    Then the edits are saved through an edits-only revise
    And the content step is not approved

  Scenario: Every field-error message exists in pt and en
    Then each field-error i18n key exists in both locale files
