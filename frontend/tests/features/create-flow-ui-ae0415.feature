Feature: Create-flow UI fixes from the 2026-10-16 QA run (AE-0415)
  As the carousel owner working through the editorial gates
  I want each gate to show what I am reviewing, the running state to survive a
  reload, the page to follow the workflow and the form to explain its errors
  So that I can review, approve and create carousels without guessing

  # REPORT: ~/alter-ego-qa/2026-10-16-ui/REPORT.md (B01 B13 B15 B18 B24 B25 B26 B27 B28 B30 B31 B32 B33)
  # Tests:
  #   src/app/dashboard/create/workspace/persona-score.test.ts
  #   src/app/dashboard/create/workspace/create-workflow-panel.test.tsx
  #   src/app/dashboard/create/workspace/create-run-progress-banner.test.tsx
  #   src/app/dashboard/create/workspace/create-workflow-progress.test.tsx
  #   src/app/dashboard/create/workspace/create-draft-blog-preview.test.tsx
  #   src/app/dashboard/create/use-follow-workflow-step.test.ts
  #   src/app/dashboard/create/create-error-message.test.ts
  #   src/app/dashboard/create/helpers.test.ts
  #   src/app/dashboard/create/workspace/labeled-field.test.tsx
  #   src/app/dashboard/create/workspace/create-template-section.test.tsx
  #   src/app/dashboard/create/[id]/publish/publish-readiness.test.ts
  #   src/app/dashboard/workflow/localize-board.test.ts
  #   src/modules/editorial/workspace/hooks/use-editorial-workflow-sse.test.ts
  #   src/modules/editorial/workspace/hooks/use-editorial-workflow-resume.test.ts

  # --- B01: persona voice gate on one 0-100 scale ---------------------------

  Scenario: A 0-10 persona score is read on the 0-100 scale
    Given the content gate has persona scores slide_1 84 and slide_2 8.7
    Then the lowest voice score is 84
    And "Aprovar Fase" is not blocked by the persona gate

  Scenario: An unscored slide is ignored by the persona gate
    Given the content gate has persona scores slide_1 80, slide_4 0 and no score for slide_7
    Then the persona gate is not blocked

  Scenario: The persona hint names the slides below the threshold
    Given the content gate has persona scores slide_2 6.5 and slide_3 91
    Then approval is blocked
    And the hint names "Slide 2 (65/100)" and the threshold 70

  # --- B13: research and outline gates show what is being reviewed ----------

  Scenario: The live research gate shows the findings and their sources
    Given the workflow is awaiting review on the research phase with 3 findings
    When the owner opens the research step
    Then each finding is listed with its source and key points above the approve button

  Scenario: The live outline gate shows the slide titles and key points
    Given the workflow is awaiting review on the outline phase with 7 outline slides
    When the owner opens the outline step
    Then the 7 slide titles and their key points are listed
    And the hook picker shows when slide 1 carries hook candidates

  # --- B15 / B26 / B27 / B28: running state ---------------------------------

  Scenario: A reload during a running phase keeps the running state
    Given GET workflow/state reports phase_status "in_progress"
    And the SSE snapshot replays the checkpoint as "awaiting_human"
    When the page loads
    Then the stale snapshot is confirmed against workflow/state before it is applied
    And the running banner shows and the review actions stay hidden
    And the content is read-only and auto-fix is disabled

  Scenario: Requesting a revision shows the running state at once
    Given the research gate is awaiting review
    When the owner clicks "Solicitar revisão" and the backend answers 202 "in_progress"
    Then the status changes to "Em andamento" and the running banner shows

  Scenario: The banner names the phase that is running
    When the owner approves the research gate
    Then the banner reads that the outline is being generated, not research
    And "Processando…" appears once, without promising "até um minuto"
    And no legacy pipeline step list ("Pesquisando tópico…") is shown

  Scenario: The page follows the workflow to the next gate
    Given the owner is on ?step=research while the outline is generated
    When the outline gate becomes ready
    Then the page moves to ?step=outline

  Scenario: A historical step chosen by the owner is not overridden
    Given the outline gate is ready and the owner opened ?step=research on purpose
    Then the page stays on ?step=research

  Scenario: An approved project shows no stale "in progress" panel
    Given the project is "approved_for_publish" with a leftover phase_progress label
    When the owner opens the review step
    Then no "Processando atualmente" panel is shown

  # --- B30: fresh project ----------------------------------------------------

  Scenario: The brief preview of a fresh project is an empty state
    Given no draft blog exists yet (preview returns 404)
    When the owner clicks "Carregar pré-visualização"
    Then "Ainda não há conteúdo de rascunho." is shown, not an error

  Scenario: A fresh project does not request the workflow state
    Given a project whose current_phase is "brief"
    When the workspace loads
    Then GET workflow/state is not requested

  # --- B18 / B32: create form errors and limits -----------------------------

  Scenario: A long topic with an empty brief no longer breaks the niche limit
    Given a 450-character topic and an empty brief
    When the request is built
    Then niche is the topic cut at a word boundary to at most 200 characters

  Scenario: API validation errors are readable
    Given the API answers 422 with "niche: String should have at most 200 characters" twice
    Then the form shows one line naming the "Brief / Nicho" field and its 200-character limit
    And not "HTTP error! status: 422"

  Scenario: A stale create error clears when the form changes
    Given the create form shows an error
    When the owner edits any field or switches the mode
    Then the error is gone

  Scenario: Fields with a limit show a live counter
    When the owner types 12 characters in the topic
    Then the counter reads "12/500"

  # --- B31: accessibility -----------------------------------------------------

  Scenario: Create form labels are tied to their inputs
    Then the topic, audience, brief and image guidance inputs are labelled by their labels

  Scenario: Template cards expose their selection
    Then the template choices are radio buttons and the selected one is checked

  Scenario: POV photo thumbnails have alt text
    Then each thumbnail image has a non-empty alt text

  # --- B25: publish page of an unfinished carousel ---------------------------

  Scenario: The publish page of an unfinished carousel says it is not ready
    Given the workflow is still on the content phase
    When the owner opens the publish page
    Then a "not ready yet" notice is shown
    And no PDF link, slide viewer, rebuild, regenerate, text edit or auto-fix is offered

  Scenario: A POV project is not offered Radar templates
    Given an approved POV project
    Then the "Layout dos Slides" Radar templates section is not shown

  # --- B24 / B33: language ----------------------------------------------------

  Scenario: The PT dashboard has no stray English on the create flow
    Given the locale is "pt"
    Then the create form, steps bar, project summary, sidebar and board statuses are in Portuguese
    And phase ids show as names ("Pesquisa", not "research")

  Scenario: The dashboard offers a language switcher
    Then the dashboard sidebar shows the EN | PT switcher

  Scenario: The template version is not doubled
    Given a project whose template_version is "v2"
    Then the preview header shows "v2", not "vv2"
