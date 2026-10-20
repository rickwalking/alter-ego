Feature: Closing actions are generated and repaired, and revisions stay in scope (AE-0437)

  Prod QA 2026-10-19, carousel 7acaf967 (hero_lower_third_v4): slide 6
  "closing_actions_missing" survived the initial generation, the auto-repair,
  a retry and revision 1; "Corrigir problemas automaticamente" changed nothing.
  Revision 1, asked to change only slides 2 and 6, rewrote slides 1, 3 and 7
  and slide 3 lost its 3 features (F-06, F-10). Carousel 5344b6c6: after a
  correction the closing items were stored under "features", and the EN
  TL;DR was a Portuguese sentence.

  # --- A: the closing slide keeps its items under "actions" ---------------

  Scenario: The drafting instructions ask for closing actions
    Given the content phase skill and the shared content contracts
    Then the closing slide is described with an "actions" array of 3 items
    And no instruction asks for "features" on the closing slide

  Scenario: A closing checklist drafted as features is stored as actions
    Given a drafted closing slide whose PT and EN items are under "features"
    When the localized slide is built
    Then both locales carry the items under "actions" and no "features"

  Scenario: A closing slide read back from its row keeps its actions
    Given a closing slide row whose actions are stored in the "features" column
    When the localized records are rebuilt from the rows
    Then the closing payloads carry the items under "actions"
    And a content slide row keeps its "features"

  Scenario: Real actions win over features
    Given a closing payload with 3 actions and 3 features
    When the closing key is restored
    Then the payload is unchanged

  # --- B: deterministic repair of missing structure ----------------------

  Scenario: The owner autofix fills missing closing actions from the outline
    Given a closing slide without actions whose outline has 3 key points
    When the owner autofix plans its repairs
    Then the PT closing slide gets 3 actions within the closing budgets (30/90)
    And the EN closing slide gets the same items to translate

  Scenario: The owner autofix moves swapped closing features back to actions
    Given a closing slide whose 3 complete items are under "features"
    When the owner autofix plans its repairs
    Then the items are under "actions" in PT and EN with their texts unchanged

  Scenario: Too few key points leave the closing slide for a revision
    Given a closing slide without actions whose outline has 1 key point
    When the owner autofix plans its repairs
    Then no actions are invented

  Scenario: The content gate repair fills closing actions and summary points
    Given the content gate blocks slide 2 "summary_points_missing" and slide 6 "closing_actions_missing"
    And the outline has 3 key points for slides 2 and 6
    When the content gate runs its repair loop
    Then slides 2 and 6 get their items in PT from the outline
    And the EN items are asked from the model as translations
    And the content gate report is no longer blocking

  # --- C: EN copy never keeps Portuguese ---------------------------------

  Scenario: A Portuguese answer for an EN field is dropped
    Given slide 1 EN "tldr_strip" is a repair target
    And the model answers "Eu olho para o computador, não para a demo"
    When the content gate runs its repair loop
    Then slide 1 EN "tldr_strip" does not take the Portuguese answer

  Scenario: A PT copy nobody translated is taken out of EN again
    Given slide 1 EN has no TL;DR and PT has one
    And the field repair model fails
    When the content gate runs its repair loop
    Then slide 1 EN still has no TL;DR

  # --- D: revisions change only the slides they name ---------------------

  Scenario Outline: The revision note names the slides it may change
    Given the revision note "<note>"
    Then the named slides are <slides>

    Examples:
      | note                                                     | slides  |
      | Apenas no slide 6, crie 3 ações                          | 6       |
      | Corrija os slides 2 e 6. Não altere nenhum outro slide.  | 2, 6    |
      | slides 2-4 and slide 7                                   | 2, 3, 4, 7 |
      | slide 3 (pt body): body_empty. Slide renders only        | 3       |
      | Deixe o tom mais leve                                    | none    |

  Scenario: A scoped revision re-drafts only the named and blocked slides
    Given a 7-slide carousel at the content review with stored drafts
    And the content gate blocks slide 2
    And the owner sends the revision note "Altere apenas o slide 6"
    When the content phase regenerates
    Then only slides 2 and 6 are drafted again
    And slides 1, 3, 4, 5 and 7 keep their stored localized copy and drafts
    And slide 3 keeps its 3 features

  Scenario: A general revision note still rewrites the whole deck
    Given the owner sends the revision note "Deixe o tom mais leve"
    When the content phase regenerates
    Then every slide is drafted again

  Scenario: A first draft is never scoped
    Given a carousel without stored slides
    And a note that names slide 6
    Then the revision scope is the whole deck

  Scenario: Slide numbers outside the deck are ignored
    Given a 7-slide carousel with stored slides
    And the revision note "slide 12"
    Then the revision scope is the whole deck
