Feature: Carousel Blog Integration

  Background:
    Given the carousel API is available

  Scenario: Validate carousel design tokens schema
    Given a valid design tokens payload
    When the carouselDesignResponseSchema validates the payload
    Then all required color fields are present
    And all typography fields are present
    And all image fields are present
    And all layout fields are present

  Scenario: Validate blog i18n response schema
    Given a valid blog i18n payload with language "pt"
    When the carouselBlogI18nResponseSchema validates the payload
    Then the markdown field is present
    And the language field equals "pt"
    And available_languages is an array

  Scenario: Reject invalid design tokens with missing fields
    Given an invalid design tokens payload missing "primary" color
    When the carouselDesignResponseSchema validates the payload
    Then validation fails with an error

  Scenario: Validate blog with design response schema
    Given a valid blog with design payload
    When the carouselBlogWithDesignResponseSchema validates the payload
    Then both blog content and design tokens are present

  Scenario: Validate carousel project list response
    Given a valid carousel project list payload
    When the carouselProjectListResponseSchema validates the payload
    Then items is an array of projects
    And total, limit, and offset are numbers

  Scenario: Design tokens convert to CSS custom properties
    Given a valid CarouselDesignResponse object
    When designTokensToCssVars is called
    Then each color field maps to the corresponding CSS variable
    And each typography field maps to the corresponding CSS variable
    And the result is a flat Record<string, string>

  Scenario: Fallback design tokens match schema
    Given FALLBACK_DESIGN_TOKENS constant
    When it is validated against carouselDesignResponseSchema
    Then validation passes successfully

  Scenario: Blog CSS variables have correct property names
    Given the BLOG_CSS_VARS constant
    Then PRIMARY should be "--blog-primary"
    And ACCENT should be "--blog-accent"
    And BG should be "--blog-bg"
    And TEXT should be "--blog-text"

  Scenario: API endpoints generate correct carousel URLs
    Given the API_ENDPOINTS constant
    Then CAROUSEL_BLOG_LANG("id1", "pt") returns "/api/carousels/id1/blog/pt"
    And CAROUSEL_DESIGN("id1") returns "/api/carousels/id1/design"
    And CAROUSEL_SLIDES("id1") returns "/api/carousels/id1/slides"
    And CAROUSEL_IMAGE("id1", "hero") returns "/api/carousels/id1/images/hero"

  Scenario: Blog languages constant has correct values
    Given the BLOG_LANGUAGES constant
    Then PORTUGUESE equals "pt"
    And ENGLISH equals "en"

  Scenario: Default blog language is Portuguese
    Given the DEFAULT_BLOG_LANGUAGE constant
    Then it equals "pt"

  Scenario: useCarouselProject hook constructs correct query
    Given a carousel project ID "abc-123"
    When useCarouselProject is called
    Then the query key includes the project ID
    And the query is disabled when ID is empty

  Scenario: useCarouselBlog uses default language
    Given a carousel project ID "abc-123"
    When useCarouselBlog is called without a language
    Then the default language "pt" is used in the query

  Scenario: Blog post header renders badge with design tokens
    Given a BlogPostHeader with cybersecurity design tokens
    When the component is rendered
    Then the badge text comes from layout.badge_label
    And the badge color uses colors.primary

  Scenario: Blog post content renders markdown
    Given a BlogPostContent with markdown "# Hello World"
    When the component is rendered
    Then the heading is rendered with design token colors
    And paragraph text uses text_muted color

  Scenario: Blog post hero renders image with design styling
    Given a BlogPostHero with an image URL and design tokens
    When the component is rendered
    Then the image alt text uses the title
    And the container has design token border and shadow styling

  Scenario: Back link navigates to /blog
    Given the BackLink component
    When the component is rendered
    Then it links to /blog