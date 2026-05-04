Feature: Blog Listing Page Internationalization
  As a visitor
  I want blog cards to display titles and summaries in my selected language
  So that I can browse posts comfortably in English or Portuguese

  Background:
    Given the /blog page is rendered server-side
    And completed carousel projects exist with title, title_en, subtitle, subtitle_en

  # ---------------------------------------------------------------------------
  # Locale-Aware Title Rendering
  # ---------------------------------------------------------------------------

  Scenario: Blog cards show English title when locale is English
    Given the user's locale cookie is "en"
    And a completed project has title "Kimi K2.6" and title_en "Kimi K2.6: 300 Agents"
    When the user visits /blog
    Then the post card heading displays "Kimi K2.6: 300 Agents"

  Scenario: Blog cards show Portuguese title when locale is Portuguese
    Given the user's locale cookie is "pt"
    And a completed project has title "Kimi K2.6" and title_en "Kimi K2.6: 300 Agents"
    When the user visits /blog
    Then the post card heading displays "Kimi K2.6"

  Scenario: Blog cards fall back to Portuguese title when English is missing
    Given the user's locale cookie is "en"
    And a completed project has title "Kimi K2.6" and title_en is null
    When the user visits /blog
    Then the post card heading displays "Kimi K2.6"

  Scenario: Blog cards fall back to topic when title is missing
    Given the user's locale cookie is "pt"
    And a completed project has topic "Kimi K2.6" and title is null
    When the user visits /blog
    Then the post card heading displays "Kimi K2.6"

  # ---------------------------------------------------------------------------
  # Per-Post Subtitle / Summary
  # ---------------------------------------------------------------------------

  Scenario: Blog cards show English subtitle as summary
    Given the user's locale cookie is "en"
    And a completed project has subtitle_en "300 agents, 12 hours, zero human babysitting"
    When the user visits /blog
    Then the post card description displays "300 agents, 12 hours, zero human babysitting"

  Scenario: Blog cards show Portuguese subtitle as summary
    Given the user's locale cookie is "pt"
    And a completed project has subtitle "300 agentes, 12 horas, zero babysitting humano"
    When the user visits /blog
    Then the post card description displays "300 agentes, 12 horas, zero babysitting humano"

  Scenario: Blog cards truncate long subtitles to 120 characters
    Given a completed project has subtitle_en with 300 characters
    When the user visits /blog
    Then the post card description ends with "..."
    And the description length does not exceed 120 characters

  Scenario: Blog cards fall back to topic when subtitle is missing
    Given a completed project has topic "Kimi K2.6" and subtitle is null
    When the user visits /blog
    Then the post card description displays "Kimi K2.6"

  # ---------------------------------------------------------------------------
  # No More Generic Subtitle
  # ---------------------------------------------------------------------------

  Scenario: Blog cards do not show generic static subtitle
    Given the user's locale cookie is "en"
    When the user visits /blog
    Then no post card contains the text "AI-generated carousels and blog posts about tech"

  # ---------------------------------------------------------------------------
  # Edge Cases & Mutations
  # ---------------------------------------------------------------------------

  Scenario Outline: Blog cards render correctly under various data states
    Given the user's locale cookie is <locale>
    And a completed project has title <title>, title_en <title_en>, subtitle <subtitle>, subtitle_en <subtitle_en>
    When the user visits /blog
    Then the post card heading is <expected_heading>
    And the post card description is <expected_description>

    Examples:
      | locale | title   | title_en     | subtitle   | subtitle_en  | expected_heading | expected_description |
      | "en"   | "PT"    | "EN"         | "Sub PT"   | "Sub EN"     | "EN"             | "Sub EN"             |
      | "pt"   | "PT"    | "EN"         | "Sub PT"   | "Sub EN"     | "PT"             | "Sub PT"             |
      | "en"   | null    | "EN"         | null       | "Sub EN"     | "EN"             | "Sub EN"             |
      | "pt"   | "PT"    | null         | "Sub PT"   | null         | "PT"             | "Sub PT"             |
      | "en"   | null    | null         | null       | null         | ""               | ""                   |

  Scenario: Empty blog index shows empty state
    Given no completed carousel projects exist
    When the user visits /blog
    Then the page displays "No blog posts yet" in the selected locale
