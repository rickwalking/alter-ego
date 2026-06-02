@frontend @legacy-removal @neon-shell
Feature: Frontend legacy removal (v1.0 → neon dashboard)
  As a maintainer
  I want the editor UI to use only the neon dashboard shell and real API hooks
  So that users never see mock chat threads or dummy create flows from the first implementation

  # Spec: docs/plans/frontend-legacy-removal.md
  # Guards: npm run check:legacy, npm run check:legacy-inventory
  # Unit: src/scripts/legacy-removal-guard.test.ts

  # ---------------------------------------------------------------------------
  # Route & shell (L2, L4)
  # ---------------------------------------------------------------------------

  Scenario: Legacy create URL redirects to neon dashboard workspace
    Given the Next.js app is running
    When I open "/create/00000000-0000-0000-0000-000000000001"
    Then I am redirected to "/dashboard/create/00000000-0000-0000-0000-000000000001"

  Scenario: Public chat URL stays on neon public chat shell
    Given the Next.js app is running
    When I open "/chat"
    Then the browser URL matches "/chat"
    And the browser URL does not match "/dashboard/chat"

  Scenario: Dashboard chat page does not render mock conversation titles
    Given I am authenticated as an editor
    And I navigate to "/dashboard/chat"
    Then the page does not contain "Source Knowledge"
    And the page does not contain "Carousel Preview" as a sidebar conversation name
    And the page does not contain "Hello Pedro. I'm your Alter-Ego assistant"

  # ---------------------------------------------------------------------------
  # Dashboard create (L3)
  # ---------------------------------------------------------------------------

  Scenario: Dashboard create brief uses controlled form not static default topic
    Given I am authenticated as an editor
    And I navigate to "/dashboard/create"
    Then the topic field does not have a hardcoded default value "DeepSeek V4 Analysis"
    And the "Start Carousel" control is enabled when topic and audience are filled

  Scenario: Starting a carousel navigates to dashboard workspace not legacy create route
    Given I am authenticated as an editor
    And I have filled the carousel brief form on "/dashboard/create"
    When I start the carousel
    Then the browser URL matches "/dashboard/create/"
    And the browser URL does not match "/create/"

  Scenario: Dashboard create workspace shows tabbed progress steps
    Given I am authenticated as an editor
    And I open an existing carousel project at "/dashboard/create/{projectId}"
    Then I see progress steps "Brief", "Research", "Outline", "Content", "Images", "Review", and "Publish"
    And the page does not render the legacy global "Header" layout from v1.0

  # ---------------------------------------------------------------------------
  # Forbidden legacy components (L1, L6) — enforced by CI guard
  # ---------------------------------------------------------------------------

  Scenario: Dashboard chat source must not import ChatInterface
    Given the legacy usage guard runs on the repository
    Then no file under "src/app/dashboard" imports "ChatInterface"
    And no file under "src/app/dashboard" imports from "@/features/create/components"

  Scenario: Legacy route group must not exist after Phase 1
    Given the legacy inventory check runs on the repository
    Then the directory "src/app/(create)" does not exist
    And the file "src/features/dashboard/chat/mock-data.ts" does not exist

  # ---------------------------------------------------------------------------
  # Workflow board (replacement map)
  # ---------------------------------------------------------------------------

  Scenario: Workflow kanban cards link to dashboard create workspace
    Given I am authenticated as an editor
    And I navigate to "/dashboard/workflow"
    When I follow the first kanban card link
    Then the browser URL matches "/dashboard/create/"
