Feature: The Meta ads variables reach production
  The boost launch (generation worker) and the owner's pause from Telegram
  (web backend) call the Meta Marketing API with the ads token, account, page
  and Instagram user. The deploy passes them from GitHub secrets with empty
  defaults, so the launch path stays inert until the secrets exist. The boost
  caps are never set from the environment, so the shipped limits apply.

  Scenario: Both prod services receive the Meta ads variables with empty defaults
    Given the deploy workflow and docker-compose.prod.yml
    Then deploy.yml writes META_ADS_ACCESS_TOKEN, META_AD_ACCOUNT_ID, META_PAGE_ID and META_ADS_IG_USER_ID from their secrets
    And the backend and generation-worker services receive each with an empty default

  Scenario: No prod surface overrides the shipped boost caps
    Given the deploy workflow and docker-compose.prod.yml
    Then neither names a boost budget, duration, country, pending or approval cap
