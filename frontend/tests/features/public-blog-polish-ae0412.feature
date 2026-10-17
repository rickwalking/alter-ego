Feature: Public blog renders correctly for anonymous visitors (AE-0412)
  QA 2026-10-16 bugs B08, B21, B22 and B23: public /blog and /blog/{id} must
  load their images without a session, show clean titles, follow the visitor's
  language, expose per-post metadata, and fit a 390px screen.

  # --- B08: images -----------------------------------------------------------

  Scenario: Listing card maps an owner-only preview hero to the public route
    Given a public carousel whose stored hero is "/api/carousels/P/preview/images/slide_1.jpg?lang=pt"
    When the /blog listing builds its card
    Then the card image is "/api/carousels/P/images/slide_1.jpg?lang=pt"
    And no card requests a "/preview/images/" URL

  Scenario: Post page maps preview hero and slide URLs to public routes
    Given a carousel-origin post whose design hero is an owner-only preview URL
    When an anonymous visitor opens /blog/{id}
    Then the hero image URL uses the public "/images/" route with the same lang

  Scenario: Public URLs without a lang keep working
    Given a stored hero "/api/carousels/P/images/slide_1"
    When it is mapped to a public URL
    Then it is unchanged

  Scenario: A missing image does not render a broken image
    Given a card or hero whose image request fails
    When the image errors
    Then the image element is removed and the card keeps its text

  # --- B21: titles and chips --------------------------------------------------

  Scenario: Emphasis markup in a title is not shown raw
    Given a post titled "Why does everyone use <strong>ChatGPT</strong> and not Claude?"
    When the title is shown on a card, the H1 or the page title
    Then the visitor reads "Why does everyone use ChatGPT and not Claude?"

  Scenario: Emphasis markup in the body is rendered as emphasis
    Given a post body containing "<strong>ChatGPT</strong>"
    When the body is rendered
    Then "ChatGPT" is rendered inside a strong element and no "<strong>" text is visible

  Scenario: A placeholder title falls back to a real title
    Given a carousel whose English title is "slide" and Portuguese title is "Gemini 4 Argon chegou."
    When an English visitor sees the card or the post
    Then the title is "Gemini 4 Argon chegou."

  Scenario: Every title candidate is a placeholder
    Given a post whose title candidates are all placeholders
    When the post page renders
    Then the localized "untitled post" label is shown

  Scenario: A long niche is not used as a category chip
    Given a carousel whose niche is a 90-character sentence
    When its card renders
    Then no category chip is shown

  Scenario: A subtitle equal to the title is not repeated
    Given a card whose subtitle equals its title
    When the card renders
    Then no subtitle is shown

  # --- B22: language and SEO --------------------------------------------------

  Scenario: Dates follow the visitor's language
    Given a post created on 2026-10-14
    When a Portuguese visitor sees the card
    Then the date reads "14/10/2026"
    And an English visitor reads "Oct 14, 2026"

  Scenario: Invalid dates are not printed
    Given a post without a publish date
    When the card renders
    Then no "Invalid Date" text is shown

  Scenario: The swipe hint is translated
    Given a Portuguese visitor on a public post
    Then the hint reads "Deslize →"

  Scenario: Each post page has its own metadata
    Given a public post titled "Opinião impopular"
    When the page metadata is generated
    Then the document title contains "Opinião impopular"
    And the description is the post subtitle or excerpt without markup

  Scenario: Metadata for an unknown post
    Given an id that matches no post
    When the page metadata is generated
    Then the generic site title is kept

  # --- B23: responsive header -------------------------------------------------

  Scenario: Public header fits a 390px screen
    Given a 390px wide viewport on /blog
    Then the header does not overflow horizontally
    And both language buttons are visible
