Feature: QA follow-ups from the 2026-10-16 run, frontend (AE-0416)
  The publish viewer shows every real slide, its EN tab never presents the PT
  caption as English, the app honours the browser language, the blog dashboard
  pages through every post and the board shows rejected projects apart.

  # --- Publish page slide viewer (B25) ---

  Scenario: The viewer counts the real slide list
    Given a project with 8 slides in its workflow state
    And design tokens listing only 6 rendered slides
    When the publish panel renders
    Then the viewer shows "1 / 8"
    And it renders 8 slide images

  Scenario: The viewer falls back to the design tokens without a slide list
    Given a project with no workflow slides
    And design tokens listing 6 rendered slides
    When the publish panel renders
    Then the viewer shows "1 / 6"

  Scenario: A slide whose image is not rendered shows a placeholder
    Given a slide image that fails to load
    When the viewer renders it
    Then the slide shows "Slide not rendered yet" instead of a broken image

  Scenario: The EN viewer tab requests the EN slide images
    Given the publish panel on the Instagram tab
    When the user selects the EN viewer tab
    Then every slide URL asks for lang=en
    And the slide alt text uses the English title

  Scenario: The EN tab says the Instagram caption is Portuguese
    Given the publish panel on the Instagram tab
    When the user selects the EN viewer tab
    Then a notice says the Instagram caption is published in Portuguese only
    And the caption field is labelled as the PT caption

  Scenario: The PT tab shows no caption-language notice
    Given the publish panel on the Instagram tab with the PT viewer tab
    Then no caption-language notice is shown

  # --- Locale (Accept-Language ignored) ---

  Scenario: A locale cookie wins over the browser language
    Given the cookie "locale=en" and the header "Accept-Language: pt-BR"
    When the request locale is resolved
    Then the locale is "en"

  Scenario: Without a cookie the best Accept-Language match is used
    Given no locale cookie and the header "Accept-Language: pt-BR,pt;q=0.9,en;q=0.8"
    When the request locale is resolved
    Then the locale is "pt"

  Scenario: Quality values decide between supported languages
    Given no locale cookie and the header "Accept-Language: en;q=0.4, pt;q=0.9"
    When the request locale is resolved
    Then the locale is "pt"

  Scenario: An unsupported browser language falls back to the default
    Given no locale cookie and the header "Accept-Language: fr-FR, de;q=0.8"
    When the request locale is resolved
    Then the locale is the default "en"

  Scenario: An invalid cookie value is ignored
    Given the cookie "locale=xx" and the header "Accept-Language: pt"
    When the request locale is resolved
    Then the locale is "pt"

  Scenario: A language refused with q=0 is never picked
    Given no locale cookie and the header "Accept-Language: pt;q=0, en;q=0.5"
    When the request locale is resolved
    Then the locale is "en"

  # --- Dashboard blog list paging ---

  Scenario: The first page asks the API for one page of posts
    When the blog dashboard opens
    Then the list request carries limit=24 and offset=0

  Scenario: The next page asks for the next offset
    Given 50 posts in total
    When the user goes to the next page
    Then the list request carries offset=24
    And the pager reads "Page 2 of 3"

  Scenario: The pager is hidden when everything fits on one page
    Given 10 posts in total
    Then no pager is shown

  Scenario: Status and search filter every post, not just the loaded page
    Given the user is on page 2
    When the user picks the status "draft" or searches "agents"
    Then the list request carries the filter
    And the list goes back to page 1

  Scenario: The previous button is disabled on the first page
    Given the user is on page 1 of 3
    Then "Previous" is disabled and "Next" is enabled

  # --- Workflow board (rejected cards under "Brief") ---

  Scenario: The board shows a localized Rejected column
    Given the board API returns a "rejected" column with one card at phase "content"
    When the board renders
    Then the column is titled "Rejected"
    And the card badge names the phase it was rejected at ("Content")

  # --- Dead code ---

  Scenario: The unused rich-text editor is gone
    Then the publishing module no longer exports RichTextEditor
    And the TipTap packages are not dependencies
