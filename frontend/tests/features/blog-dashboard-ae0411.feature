Feature: Blog dashboard list and editor (AE-0411)
  The blog dashboard lists every post with its real live state, creates new
  drafts, and the editor loads and saves posts without losing content.

  # --- Editor (B05, B19) ---

  Scenario: The editor loads the full post through the detail endpoint
    Given a post that is not in the first list page
    When the editor opens it
    Then the post is fetched from GET /api/blog-posts/{id}
    And the body field shows its stored text

  Scenario: A carousel post body is read from content.markdown
    Given a carousel post whose content is {"markdown": "# Body", "translations": {...}}
    When the editor opens it
    Then the body field shows "# Body"

  Scenario: A title-only save does not send content
    Given a loaded post
    When the user changes only the title and saves
    Then the PUT payload carries only the title

  Scenario: A body edit keeps every other content key
    Given a carousel post with markdown and translations
    When the user edits the body and saves
    Then the PUT content has the new markdown and the same translations

  Scenario: An empty title cannot be saved
    Given a loaded post
    When the user clears the title
    Then a "title is required" message is shown
    And the save button is disabled and no request is sent

  Scenario: A server rejection is shown and the user stays on the editor
    Given a loaded post
    When the save returns 422 or 409 or fails
    Then a localized error message is shown
    And the page does not navigate away
    And no unhandled promise rejection happens

  Scenario: Restoring a version reads either content shape
    Given a version whose snapshot has "markdown"
    When the user restores it
    Then the body field shows that markdown

  # --- List (B07, B17, B20, B24) ---

  Scenario: Every post is listed, with at most one featured card
    Given three published live posts
    When the dashboard list renders
    Then three cards are shown
    And only the newest live post carries the "Featured" tag

  Scenario: A carousel post waiting for its carousel release is not shown as live
    Given a post with status "published" and is_public false
    When the dashboard list renders
    Then its badge reads "Awaiting carousel release"
    And it is not featured
    And it offers no Hide action

  Scenario: The counter shows the real number of posts
    Given the API returns 2 posts
    When the dashboard list renders
    Then the counter reads "2 posts"

  Scenario: An empty search shows an empty state
    Given posts exist
    When the user searches for text no post matches
    Then "No posts match your filters" is shown

  Scenario: No posts at all shows the empty state
    Given the API returns no posts
    Then "No blog posts yet" is shown

  Scenario: Creating a post that fails shows an error
    Given the create request returns 409
    When the user clicks "New Post"
    Then an error message is shown and the button is enabled again

  Scenario: Dashboard copy is localized
    Given the pt locale
    Then the list title, breadcrumb, search placeholder, "New Post" and the new draft title come from pt messages
