Feature: Rate limits key on the real client, trusting forwarded addresses from nginx only (AE-0589)
  In production every request reached the backend from nginx's container address,
  so login and change-password (5 per minute) shared one bucket across all users:
  a few bad logins locked everyone out. Pedro's decision (2026-11-01): trust a
  forwarded client address only from the proxy (nginx), never from any other peer,
  so nobody can spoof X-Forwarded-For from outside.

  Scenario: A request through nginx keys the limiter on the forwarded client
    Given the backend trusts forwarded addresses the way the production container does
    When nginx forwards a request from client A
    Then the limiter keys the request on client A

  Scenario: A forwarded address from an untrusted peer is ignored
    Given the backend trusts forwarded addresses the way the production container does
    When a peer other than nginx sends a request with a forged X-Forwarded-For
    Then the limiter keys the request on that peer's own address

  Scenario: A forged left-most X-Forwarded-For entry is ignored
    Given the backend trusts forwarded addresses the way the production container does
    When nginx forwards a request whose X-Forwarded-For starts with a client-supplied fake address
    Then the limiter keys the request on the right-most address, the one nginx added

  Scenario: Two clients through nginx get separate login buckets
    Given the backend trusts forwarded addresses the way the production container does
    When client A fails to sign in until the login limit answers 429
    Then client B can still try to sign in and gets 401, not 429

  Scenario: The container healthcheck keeps working
    Given the backend trusts forwarded addresses the way the production container does
    When the healthcheck calls /health from 127.0.0.1
    Then it answers 200

  Scenario: The production config trusts forwarded addresses from nginx only
    Given the production Dockerfile, compose file and nginx configs
    When the proxy settings are read
    Then uvicorn reads proxy headers and trusts only loopback and nginx's fixed address
    And nginx's fixed address is in the pinned subnet and outside the dynamic range
    And nginx sends its own view of the client as X-Forwarded-For and reads the visitor from Cloudflare only

  Scenario: A wrong proxy config is reported
    Given a seeded config that trusts every peer, drops proxy headers, leaves nginx unpinned or appends X-Forwarded-For
    When the proxy settings are checked
    Then each mistake is reported
