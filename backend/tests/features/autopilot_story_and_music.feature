Feature: Instagram Story after a carousel post, plus an "add music" nudge (AE-0369)
  As the account owner
  I want every published carousel announced in a Story and a reminder to add music
  So that the post gets reach without me opening the app twice

  Background:
    Given a released public carousel whose PT slide 1 is a 1080x1350 JPEG

  # --- Story image -----------------------------------------------------------

  Scenario: The Story image is a 1080x1920 JPEG under 8 MB
    When the Story image is rendered from slide 1
    Then "story_pt.jpg" is a 1080x1920 JPEG
    And it is at most 8 MB
    And slide 1 sits in the middle over a blurred, darkened copy of itself
    And the caption band reads "Novo post no perfil ↑"

  Scenario: Rendering is deterministic and cached
    Given the Story image was rendered once
    When it is prepared again and slide 1 has not changed
    Then the same file is reused without rendering again

  Scenario: No slide 1 means no Story image
    Given the carousel has no rendered PT slide 1
    When the Story image is prepared
    Then no Story image exists
    And the Story step records "story_image_missing"

  # --- Public route ----------------------------------------------------------

  Scenario: The public route serves the Story image of a public carousel
    Given the Story image was rendered
    When GET /api/carousels/{id}/story-image/pt.jpg is called without auth
    Then the response is 200 with "image/jpeg"

  Scenario: A private carousel's Story image is not served
    Given the carousel is not public
    When GET /api/carousels/{id}/story-image/pt.jpg is called
    Then the response is 404

  Scenario: A public carousel without a rendered Story image is 404
    Given the carousel is public but no Story image was rendered
    When GET /api/carousels/{id}/story-image/pt.jpg is called
    Then the response is 404

  # --- Graph calls -----------------------------------------------------------

  Scenario: The Story is created, polled, and published through Graph
    When the publisher posts the Story image
    Then it POSTs /{ig_user_id}/media with media_type "STORIES" and the image_url
    And it GETs the container with fields "status_code" until "FINISHED"
    And it POSTs /{ig_user_id}/media_publish with the container as creation_id

  # --- Story step after publish ---------------------------------------------

  Scenario: A published carousel also posts one Story
    Given a run in "publishing" for that carousel
    When the publish job runs
    Then the run is "published"
    And one Story is published and its media id is stored
    And the owner notice says the Story was published

  Scenario: A double tick posts one Story
    Given a run in "publishing" for that carousel
    When the publish job runs twice
    Then media_publish is called once for the Story

  Scenario: A stored Story id short-circuits the Story step
    Given the carousel already has a stored Story media id
    When the Story step runs
    Then the Graph API is not called for the Story

  Scenario: A crash after the Story container is resumed, not recreated
    Given a stored Story container younger than 24 hours and no Story media id
    When the Story step runs
    Then no new Story container is created
    And the stored Story container is published

  Scenario: A transient Story error is retried up to 3 times
    Given Graph fails the Story container with a transient error twice
    When the Story step runs
    Then the Story is published on the third attempt

  Scenario: A Story failure leaves the post published
    Given Graph rejects the Story with a permanent error
    When the publish job runs
    Then the run is "published"
    And the Story error is stored
    And the owner notice says "Story falhou" with the reason

  Scenario: A publisher that cannot post Stories skips the Story step
    Given the configured publisher is not the Graph publisher
    When the publish job runs
    Then the run is "published"
    And the owner notice has no Story line

  # --- Telegram notice --------------------------------------------------------

  Scenario: The published notice carries the permalink, the Story, and the music nudge
    Given a published notice with a permalink, a published Story, and niche "AI"
    When the owner notice is rendered
    Then it reads "✅ Publicado: <permalink>"
    And it reads "📲 Story: publicado"
    And it reads "🎵 Adicione uma música pelo app (20s): sugestão: lo-fi eletrônico / synthwave"

  Scenario Outline: The music style follows the niche and image style
    Given a carousel with niche "<niche>" and image style "<style>"
    When the music suggestion is chosen
    Then it is "<music>"

    Examples:
      | niche                   | style      | music                        |
      | AI                      | neo_anime  | lo-fi eletrônico / synthwave |
      | Inteligência Artificial | neo_anime  | lo-fi eletrônico / synthwave |
      | Cibersegurança          | neo_anime  | dark synth                   |
      | Robótica                | neo_anime  | cinematic electronic         |
      | Culinária               | neo_anime  | lo-fi beats                  |
      | Culinária               | comic_neon | lo-fi eletrônico / synthwave |
      | Culinária               | cinematic  | cinematic electronic         |

  # --- Manual path ------------------------------------------------------------

  Scenario: The manual publish route also posts the Story once
    Given a carousel without an autopilot run
    When the owner publishes it manually twice
    Then one carousel and one Story are published
