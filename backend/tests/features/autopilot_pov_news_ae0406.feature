Feature: Content mode "pov_news" and scout-verified quotes (AE-0406, ADR-0023)
  As the account owner
  I want the scout to propose news told through my point of view, with real quotes
  So that a news post states the facts, why they matter to a developer and my read,
  and never shows a quote that someone did not write

  Background:
    Given the scout sent the post "https://x.com/kanishksj01/status/1234567890"
      by "kanishksj01" through x-signals with the text
      "In just a day I have run hundreds of cloud agents in parallel across all the lessons in my physics learning app."
    And both topic sources are in the 6-hour allowlist

  # --- Intake: happy paths -------------------------------------------------

  Scenario: A pov_news topic with one verified quote is accepted and queued
    Given a pov_news topic with a thesis_draft and quote "q1"
      whose excerpt is "In just a day I have run hundreds of cloud agents in parallel"
    When the scout posts it to /api/autopilot/topics
    Then the topic is accepted and a run is queued
    And the stored candidate keeps the quote

  Scenario: Excerpt matching ignores curly quotes, CRLF and whitespace runs only
    Given the stored post text contains a line break and straight quotes
    And the excerpt uses curly quotes and one space where the post has "\r\n  "
    When the topic is checked
    Then the excerpt matches the post

  Scenario: Emoji and case are compared exactly
    Given the stored post text contains "agents 🚀 in parallel"
    When the excerpt is "agents 🚀 in parallel"
    Then it matches
    But the excerpt "Agents 🚀 in parallel" does not match

  Scenario: A pov_news topic without quotes is accepted
    Given a pov_news topic with a thesis_draft and no quotes
    When the scout posts it
    Then the topic is accepted

  # --- Intake: regressions (existing clients keep working) -----------------

  Scenario Outline: Topics without pov_news behave as today
    Given a topic with mode <mode>
    When the scout posts it
    Then the outcome is the same as before AE-0406
    And every rejection carries "index" and, when one field caused it, "field"

    Examples:
      | mode          |
      | (absent)      |
      | news_analysis |
      | pov           |

  # --- Intake: per-topic quote rejections ----------------------------------

  Scenario Outline: A quote problem rejects only that topic
    Given a batch with a valid topic and a pov_news topic whose quote <problem>
    When the scout posts it
    Then the valid topic is accepted
    And the pov_news topic is rejected with reason "<reason>" and field "<field>"
    And the response is not a 422

    Examples:
      | problem                                   | reason                | field              |
      | has id "q0"                               | quote_invalid         | quotes[0].id       |
      | has a 61-character name                   | quote_invalid         | quotes[0].name     |
      | has lang_original "es"                    | quote_invalid         | quotes[0].lang_original |
      | cites a URL not listed in sources         | quote_source_invalid  | quotes[0].url      |
      | cites a twitter.com URL (not canonical)   | quote_source_invalid  | quotes[0].url      |
      | cites a post never sent through x-signals | quote_source_invalid  | quotes[0].url      |
      | names a handle other than the URL's       | quote_handle_mismatch | quotes[0].handle   |
      | has an excerpt that is not in the post    | quote_not_in_post     | quotes[0].excerpt  |
      | has an excerpt past the 600-character cut | quote_not_in_post     | quotes[0].excerpt  |
      | has a 16-word text_pt                     | quote_too_long        | quotes[0].text_pt  |
      | has a 19-word text_en                     | quote_too_long        | quotes[0].text_en  |

  Scenario: Four quotes are one topic's quote_invalid
    Given a pov_news topic with 4 quotes
    When the scout posts it
    Then it is rejected with reason "quote_invalid" and field "quotes"

  Scenario: Duplicate quote ids are invalid
    Given a pov_news topic with two quotes both "q1"
    When the scout posts it
    Then it is rejected with reason "quote_invalid" and field "quotes[1].id"

  Scenario: Quotes on a pov topic are refused
    Given a pov topic that carries quotes
    When the scout posts it
    Then it is rejected with reason "quote_invalid" and field "quotes"

  Scenario: An unknown key inside a quote is still a 422
    Given a pov_news topic whose quote has the key "avatar_asset_id"
    When the scout posts it
    Then the API answers 422

  Scenario: pov_news needs a thesis draft and ignores pov_format
    Given a pov_news topic without thesis_draft
    When the scout posts it
    Then it is rejected with reason "thesis_missing" and field "thesis_draft"
    And a pov_news topic with pov_format "comparacao" stores no pov_format

  # --- Caps ------------------------------------------------------------------

  Scenario: pov_news counts toward the daily cap only
    Given this week's Radar IA run was already created
    When a pov_news topic is posted
    Then it is queued
    And it is not counted as a Radar IA run of the week

  # --- Run and pipeline ------------------------------------------------------

  Scenario: A pov_news run waits for the thesis like POV
    Given a queued pov_news run without a confirmed thesis
    When the runner ticks
    Then the run moves to "awaiting_thesis"
    And the Telegram prompt reads "Ponto de Vista: Notícia proposto"

  Scenario: The carousel is a POV deck with the news voice
    Given a confirmed pov_news run with the owner's hook photo
    When the carousel is created
    Then it uses pov_hook_v1, the slide-1 photo and the persona voice gate
    And its outline, hook, content and caption prompts come from carousel_pov_news/v1
    And the project stores the quotes and the topic's sources

  Scenario: A quote is placed verbatim by id, at most twice
    Given the content model returns quote_id "q1" on a point slide, "q2" on the twist and "q3" on a third point
    When the drafts are finalized
    Then the point slide carries the q1 card and the twist the q2 card, with text_pt
    And the third slide carries no card
    And a second use of an already placed quote carries no card
    And a single re-drafted slide carries no card
    And the EN translation of each card is text_en

  Scenario: A model-written quote never reaches a slide
    Given a pov_news draft that carries its own insight quote
    When the drafts are finalized
    Then that insight is removed

  Scenario: The autopilot content gate blocks an altered quote card
    Given a pov_news content gate whose PT card text differs from text_pt
    When the gate is read
    Then it reports a "quote_not_verbatim" quality violation
    And the run is not auto-approved

  Scenario: The quote card shows the initial, the name and the handle, never a URL
    Given a point slide with the q1 card
    When it is rendered
    Then it shows "K", "Kanishk Jain" and "@kanishksj01 · X"
    And the slide HTML contains no "https://"

  Scenario: The caption footer is written by code
    Given a pov_news project with sources "https://x.com/kanishksj01/status/1",
      "https://www.anthropic.com/news/x", "https://x.com/kanishksj01/status/2"
    When the caption is generated
    Then it ends with "Fontes: @kanishksj01, anthropic.com"

  Scenario: Radar IA and POV captions get no footer
    Given a pov project
    When the caption is generated
    Then it has no "Fontes:" line
