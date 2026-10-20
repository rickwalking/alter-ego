Feature: Blog editor errors are visible and translated (AE-0438, F-11)
  Every failed editor action shows a specific, translated message (pt + en)
  next to the control that failed: restore errors in the version sidebar,
  review errors in the review bar, slot errors on their slot, and 422/409/5xx
  save errors in the editor banner.

  Background:
    Given the owner is logged in as "Pedro"
    And the post is a v2 document under edit

  Scenario: A failed restore shows its error in the version sidebar
    Given a stored version whose restore fails with 422
    When the owner clicks "Restore this version"
    Then the version sidebar shows the restore error message
    And the editor content is unchanged

  Scenario: Restoring an empty version names the problem
    Given the API answers 422 with detail "blog_version_empty"
    When the owner restores that version
    Then the sidebar shows the empty-version message

  Scenario: Submitting your own post for review names the guard
    Given BLOG_ALLOW_SELF_REVIEW is false
    And the owner submits the post with their own reviewer id
    When the API answers 400 with detail "self_review_not_allowed"
    Then the review bar shows the self-review message
    And the post stays "draft"

  Scenario: A publish blocked by the status guard is explained
    Given a draft post
    When the owner clicks Publish and the API answers 400
    Then the review bar shows the status-guard message

  Scenario: A 409 conflict on a save is explained
    Given the post is at lock version 2
    And another tab saved first
    When the owner saves with If-Match 2
    Then the editor banner shows the conflict message
    And the owner's unsaved text is preserved

  Scenario: A failed AI call is explained on the slot
    Given the rewrite or image provider fails with 502
    When the owner retries the slot action
    Then the slot shows the AI failure message

  Scenario: The messages are localized
    Given the pt locale
    Then the review, version, slot and banner errors use pt copy
    And with the en locale they use en copy
