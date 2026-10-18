Feature: Grok cover image for slide 1, chosen by the owner per post (AE-0418, ADR-0024)
  As the account owner
  I want GrokBot to attach an optional cover image to a topic
  So that I can swap slide 1 to it with one Telegram tap, and swap back

  Background:
    Given the autopilot API key is configured
    And the autopilot owner user exists

  # --- Upload: POST /api/autopilot/assets -----------------------------------

  Scenario: An ai_image of 1080x1350 is accepted
    When the scout uploads a 1080x1350 PNG with kind "ai_image"
    Then the response is 201 with an asset_id, kind "ai_image", width 1080 and height 1350
    And the image is stored re-encoded under the creator assets with role "cover"

  Scenario: An ai_image wider than 4:5 is centre-cropped before the size check
    When the scout uploads a 2000x1350 JPEG with kind "ai_image"
    Then the response is 201 with width 1080 and height 1350

  Scenario: An ai_image that is too small after the 4:5 crop is rejected
    When the scout uploads a 1200x1200 PNG with kind "ai_image"
    Then the response is 422 with detail "asset_too_small"

  Scenario: A screenshot keeps its aspect and needs 600 px of width
    When the scout uploads a 800x400 PNG with kind "screenshot" and a source_url
    Then the response is 201 with width 800 and height 400
    When the scout uploads a 599x900 PNG with kind "screenshot" and a source_url
    Then the response is 422 with detail "asset_too_small"

  Scenario Outline: Upload rejections carry a stable code
    When the scout uploads <upload>
    Then the response is <status> with detail "<code>"

    Examples:
      | upload                                          | status | code                   |
      | a file over 5 MB                                | 413    | asset_too_large        |
      | a 5000x1000 PNG                                 | 413    | asset_too_large        |
      | a WebP or GIF, or a PNG declared as text        | 415    | asset_type_unsupported |
      | a request without a file part                   | 415    | asset_type_unsupported |
      | a PNG with kind "photo" or no kind              | 422    | asset_kind_invalid     |
      | a screenshot without source_url                 | 422    | asset_source_missing   |

  Scenario: The upload route needs the API key
    When the scout uploads without X-Api-Key
    Then the response is 401

  # --- Topic intake: the optional cover field ------------------------------

  Scenario Outline: A topic with a fresh cover is accepted in every mode
    Given an unused ai_image cover uploaded 1 hour ago
    When the scout posts a <mode> topic with that cover
    Then the topic is accepted and the candidate keeps the cover asset id
    And the cover is marked as used by that topic

    Examples:
      | mode          |
      | news_analysis |
      | pov           |
      | pov_news      |

  Scenario Outline: A bad cover rejects only that topic
    Given <cover>
    When the scout posts a topic with that cover and another topic without one
    Then the topic with the cover is rejected with "<reason>" and field "cover.asset_id"
    And the other topic is accepted

    Examples:
      | cover                                                     | reason               |
      | an asset id nobody uploaded                               | cover_asset_unknown  |
      | an id that is not a UUID                                  | cover_asset_unknown  |
      | a cover uploaded 7 hours ago                              | cover_asset_expired  |
      | a cover already attached to another topic                 | cover_asset_used     |
      | a screenshot whose source_url is not in the topic sources | cover_source_invalid |

  Scenario: The same cover twice in one batch is used once
    Given an unused cover
    When the scout posts two topics with that cover
    Then the first is accepted and the second is rejected with "cover_asset_used"

  # PR #136 review (item 5): the claim is checked, never ignored.
  Scenario: A cover another batch claimed after the read rejects the topic
    Given a cover the intake read as unused
    And another batch claims it before this topic is stored
    When the scout posts a topic with that cover
    Then the topic is rejected with "cover_asset_used" and field "cover.asset_id"
    And the topic is not stored

  Scenario: A cover the sweep deleted after the read rejects the topic
    Given a cover the intake read as unused
    And the sweep deletes it before this topic is stored
    When the scout posts a topic with that cover
    Then the topic is rejected with "cover_asset_unknown"
    And the topic is not stored

  # PR #136 review (item 4): uploads never starve /signals or /topics.
  Scenario: Cover uploads have their own rate limit
    When the scout sends 30 uploads in a minute
    Then none of them is rate limited and the 31st is answered 429
    And the next 10 posts to /topics are all answered 200

  # PR #136 review (item 1): the production proxy must not answer 413 first.
  Scenario: nginx lets a 5 MB cover through to the backend
    Given the nginx and nginx-ssl configs
    Then both have a location for /api/autopilot/assets with client_max_body_size 6m
    And it forwards the same proxy headers as /api/

  Scenario: Unknown keys inside cover reject the batch
    When the scout posts a topic with cover {"asset_id": "...", "url": "..."}
    Then the response is 422

  # --- Default and the owner's choice --------------------------------------

  Scenario: The cover is off by default
    Given a queued pov run whose topic has a cover
    When the runner creates the carousel
    Then slide 1 uses the owner's photo and the project has no slide cover

  Scenario: The POV thesis message offers the cover
    Given a pov run awaiting its thesis whose topic has a cover
    When the Telegram tick sends the thesis prompt
    Then the cover is sent as a photo before the prompt
    And the prompt keyboard has "🖼️ Usar capa do Grok"

  Scenario: "Usar capa do Grok" at the thesis switches slide 1 to the cover, and back
    Given a pov run awaiting its thesis whose topic has a cover
    When the owner taps "🖼️ Usar capa do Grok"
    Then the run records the cover choice and the keyboard shows "📸 Usar minha foto"
    When the owner confirms the thesis and the runner creates the carousel
    Then the project's slide cover is the Grok cover, staged in the output dir
    When the owner had tapped "📸 Usar minha foto" instead
    Then the project has no slide cover

  Scenario: A second tap of the same choice changes nothing
    Given the run already uses the Grok cover
    When the owner taps "🖼️ Usar capa do Grok" again
    Then the run is unchanged and the answer says it is already so

  Scenario: The Radar IA review offers the cover and swaps slide 1
    Given a news_analysis run awaiting the owner whose topic has a cover
    When the review is sent
    Then the cover photo is sent and the review keyboard has "🖼️ Usar capa do Grok"
    When the owner taps it
    Then the run moves to reworking with the cover rework queued
    When the worker tick applies it
    Then the project's slide cover is set, the file is staged, the deck is re-rendered
    And the run is back in awaiting_owner with a new review whose keyboard has "↩️ Usar capa padrão"

  # PR #136 review (item 3): a failed re-render is never reported as done.
  Scenario: A failed slide-1 re-render is escalated, never reported as done
    Given the owner tapped "🖼️ Usar capa do Grok" on a Radar IA review
    When the worker tick switches slide 1 and the re-render reports errors
    Then the switch is "render_failed", not "switched"
    And the run is escalated with reason "cover_render_failed" and the rework is cleared
    And the owner's escalation notice says the cover switch did not render

  Scenario: A cover tap on a run that is not waiting is refused
    Given a run that is generating
    When the owner taps "🖼️ Usar capa do Grok"
    Then the run is unchanged

  Scenario: A non-owner cover tap is ignored
    When someone else taps "🖼️ Usar capa do Grok"
    Then the run is unchanged

  # --- Render ---------------------------------------------------------------

  Scenario: An ai_image cover renders full-bleed under the title
    Given a project whose slide cover is an ai_image staged in the output dir
    When slide 1 renders (POV hook or Radar IA intro)
    Then the slide-1 image is the staged cover

  Scenario: A screenshot cover renders as a framed card with a credit
    Given a project whose slide cover is a screenshot from "https://x.com/poteto/status/1"
    When slide 1 renders
    Then the slide shows the title above a framed card and the credit "@poteto · X"
    And a screenshot from "https://www.theverge.com/a" is credited "theverge.com"

  Scenario: A missing cover file fails the render loudly
    Given a project whose slide cover file is not staged
    When slide 1 renders
    Then a HookPhotoError with "slide_cover_unreadable" is raised

  # --- Cleanup --------------------------------------------------------------

  Scenario: Unused covers older than 6 hours are deleted
    Given an unused cover uploaded 7 hours ago and a used one uploaded 7 hours ago
    When the workers tick sweeps covers
    Then only the unused cover, its creator asset row and its file are deleted

  # PR #136 review (item 2): one creator asset can back two covers.
  Scenario: Sweeping an unused cover keeps a used cover with the same bytes
    Given covers A and B uploaded 7 hours ago with identical bytes
    And B is attached to a topic
    When the workers tick sweeps covers
    Then A is deleted and B, its creator asset and its file survive

  Scenario: The sweep keeps an image a carousel still renders
    Given an unused cover uploaded 7 hours ago that a project's slide cover points at
    When the workers tick sweeps covers
    Then the cover row is deleted but its creator asset and file survive
