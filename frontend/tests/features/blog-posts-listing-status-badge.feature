Feature: Blog posts admin listing renders for all workflow statuses (AE-0295)
  The dashboard "Posts do Blog" listing must render every post card without
  crashing, regardless of the post's workflow status. Workflow status and
  content category are distinct domains and must never share a badge palette.

  Scenario: Listing renders posts of every workflow status without crashing
    Given the API returns blog posts with statuses "draft", "under_review", "approved", "published" and "archived"
    When the admin opens the "Posts do Blog" dashboard page
    Then every post card is rendered
    And no runtime TypeError is thrown

  Scenario: Status badge shows a distinct label and color per status
    Given a draft post and a published post are in the listing
    When the cards render
    Then the draft card shows the localized "Draft" badge
    And the published card shows the localized "Published" badge
    And the two badges use different defined background/text colors

  Scenario: Badge falls back safely for an unknown color key
    Given a BlogPostBadge is rendered with a color that is not in the palette map
    When the component renders
    Then it renders a neutral default badge
    And it does not throw

  Scenario: Unknown backend status renders a neutral badge instead of crashing
    Given the API returns a blog post with an unrecognized status value
    When the listing renders
    Then the card renders with a neutral "Unknown" status badge
    And no runtime TypeError is thrown

  Scenario: Frontend status vocabulary matches the backend enum
    Given the backend BlogPostStatus enum source file
    When the frontend status constant list is compared against it
    Then the two vocabularies are identical
