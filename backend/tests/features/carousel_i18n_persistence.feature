Feature: Carousel i18n Data Persistence
  As a content author
  I want English titles, subtitles, and niche-aware badges persisted in the database
  So that the frontend can render localized blog cards and post headers correctly

  Background:
    Given the carousel_projects table exists with title_en and subtitle_en columns
    And a carousel project with niche "AI" and topic "Kimi K2.6 Launch"

  # ---------------------------------------------------------------------------
  # Title and Subtitle Persistence
  # ---------------------------------------------------------------------------

  Scenario: English title and subtitle are persisted after generation
    Given the generation pipeline produces title_en "Your AI Agent Now Has Its Own Identity on the Web"
    And subtitle_en "Cloudflare launches native support for agents as API clients"
    When the content node persists the project
    Then the database row contains title_en equal to the generated English title
    And subtitle_en equal to the generated English subtitle

  Scenario: Portuguese title remains in title column
    Given the generation pipeline produces title_pt "Seu agente de IA agora tem identidade própria na web"
    When the content node persists the project
    Then the database row contains title equal to the Portuguese title
    And title_en is stored separately

  Scenario: Fallback when English title is not generated
    Given the generation pipeline produces only a Portuguese blog
    When the content node persists the project
    Then title_en is null
    And subtitle_en is null

  Scenario Outline: _extract_title_and_subtitle handles various markdown structures
    Given a blog markdown string equal to <markdown>
    When _extract_title_and_subtitle is called
    Then the returned title is <expected_title>
    And the returned subtitle is <expected_subtitle>

    Examples:
      | markdown                                      | expected_title     | expected_subtitle |
      | "# Hello World: The Subtitle\n\nBody"          | "Hello World"      | "The Subtitle"    |
      | "# Hello World\n\nBody"                        | "Hello World"      | null              |
      | "Hello World\n\nBody"                          | null               | null              |
      | "# Title: Subtitle: With Colons\n\nBody"       | "Title"            | "Subtitle: With Colons" |
      | ""                                              | null               | null              |
      | "#  Kimi K2.6  \n\n300 Agentes..."              | "Kimi K2.6"        | "300 Agentes..."  |

  # ---------------------------------------------------------------------------
  # Badge Label (Niche-based)
  # ---------------------------------------------------------------------------

  Scenario: Default design tokens use niche as badge_label
    Given a project with niche "Cybersecurity"
    And design_tokens is empty in the database
    When the design endpoint builds default tokens
    Then layout.badge_label equals "Cybersecurity"

  Scenario: Generation pipeline sets badge_label to niche
    Given a project with niche "Dev Tools"
    When the generation pipeline creates design tokens
    Then the persisted design tokens contain layout.badge_label "Dev Tools"

  Scenario Outline: Badge label falls back gracefully for missing niche
    Given a project with niche <niche>
    When default design tokens are built
    Then layout.badge_label equals <expected_badge>

    Examples:
      | niche          | expected_badge |
      | "AI"           | "AI"           |
      | ""             | "CARROSSEL"    |
      | null           | "CARROSSEL"    |
      | "Open Source"  | "Open Source"  |

  # ---------------------------------------------------------------------------
  # Content Cleanup (Mutations & Edge Cases)
  # ---------------------------------------------------------------------------

  Scenario: Leading H1 is stripped before persistence
    Given the LLM returns blog markdown starting with "# Kimi K2.6: 300 Agentes\n\nA Moonshot AI..."
    When the post-generation cleanup runs
    Then the persisted markdown does not start with "# Kimi K2.6"
    And the first line is "A Moonshot AI..."

  Scenario: Backtick-wrapped duplicate paragraphs are removed
    Given the LLM returns markdown containing:
      """
      `A Moonshot AI acaba de lançar o Kimi K2.6...`
      A Moonshot AI acaba de lançar o Kimi K2.6...
      """
    When the post-generation cleanup runs
    Then only one paragraph remains
    And the backtick-wrapped line is removed

  Scenario: HTML fragment artifacts are stripped
    Given the LLM returns markdown containing 'Arquitetura que Torna Sessões de 12 Horas Possíveis" />'
    When the post-generation cleanup runs
    Then the artifact '" />' is removed
    And no unclosed HTML tags remain in the output

  Scenario: Multiple consecutive blank lines are collapsed
    Given the LLM returns markdown with "\n\n\n\n" between sections
    When the post-generation cleanup runs
    Then no more than two consecutive blank lines exist

  Scenario: Cleanup preserves valid markdown syntax
    Given the LLM returns markdown with code blocks, lists, and blockquotes
    When the post-generation cleanup runs
    Then code fences remain intact
    And list markers remain intact
    And blockquote markers remain intact

  Scenario Outline: Cleanup handles various LLM mutation outputs
    Given the raw LLM blog markdown equals <raw>
    When cleanup_markdown is called
    Then the cleaned markdown equals <cleaned>

    Examples:
      | raw | cleaned |
      | "# Title\n\n`Paragraph`\nParagraph" | "Paragraph" |
      | "# Title: Sub\n\nBody\n\n## Section" | "Body\n\n## Section" |
      | "<img alt=\"x\" />\nText" | "Text" |
      | "# Hello\n\n\n\n\nWorld" | "Hello\n\nWorld" |

  # ---------------------------------------------------------------------------
  # Backfill Script
  # ---------------------------------------------------------------------------

  Scenario: Backfill script populates title_en from English translations
    Given a completed project with blog_translations containing "en"
    And title_en is null in the database
    When the backfill script runs
    Then title_en is populated from the English blog heading
    And subtitle_en is populated from the English blog subtitle

  Scenario: Backfill script skips projects without English translations
    Given a completed project with blog_translations containing only "pt"
    When the backfill script runs
    Then title_en remains null
    And subtitle_en remains null

  Scenario: Backfill script updates badge_label from niche
    Given a completed project with niche "Tech" and design_tokens layout.badge_label "CARROSSEL"
    When the backfill script runs
    Then design_tokens layout.badge_label becomes "Tech"

  # ---------------------------------------------------------------------------
  # Database Schema Integrity
  # ---------------------------------------------------------------------------

  Scenario: Migration adds title_en and subtitle_en columns
    Given the database is at the previous revision
    When the Alembic upgrade runs
    Then the carousel_projects table has a title_en column of type String(500)
    And a subtitle_en column of type Text
    And both columns are nullable

  Scenario: Migration is reversible
    Given the database is at the new revision
    When the Alembic downgrade runs
    Then the title_en column does not exist
    And the subtitle_en column does not exist
