Feature: Copy-hygiene validators for carousel slides (AE-0401)
  Prod carousel 98a2e2f0 (autopilot run b241ded5, 2026-10-16) shipped a
  fenced JSON blob as slide copy, a Markdown heading in a body, a hook whose
  body repeated its heading, a summary point cut mid-phrase and EN casing
  forced after a colon. Each defect is a blocking rule on the POV and Radar
  IA contracts, on PT and EN, on the heading, the body and every item. The
  pipeline's emphasis (**bold** in PT, balanced <strong> in EN) is legit.

  Background:
    Given the "pov_hook_v1" presentation policy

  Scenario: The approved 9-slide prod deck passes every rule
    Given the 9 approved slides of carousel 98a2e2f0
    When the deck is validated
    Then no violation is reported

  Scenario: The deck prod shipped is blocked on slides 3 and 8
    Given slide 3 written as a "```Json" fenced bilingual object
    And slide 8's PT body starting with "## Checklist para salvar"
    When the deck is validated
    Then slide 3 is blocked by "structured_payload_in_copy"
    And slide 8 is blocked by "markup_leak"

  Scenario: The deterministic repair restores the approved deck
    Given the deck prod shipped
    When the deterministic repair runs (generation and gate)
    Then the deck equals the approved deck
    And no model is called

  Scenario Outline: Each rule fires on its seeded violation
    Given a content slide whose <locale> <field> is "<text>"
    When the slide is validated
    Then the slide is blocked by "<code>"

    Examples:
      | code                       | locale | field                   | text                                                        |
      | structured_payload_in_copy | pt     | body                    | {"pt": {"heading": "Oi", "body": "Tudo certo por aqui."}}   |
      | structured_payload_in_copy | en     | body                    | The "body": "copy" key leaked into the slide text here.     |
      | markup_leak                | pt     | body                    | ## Checklist para salvar                                    |
      | markup_leak                | en     | body                    | Use the <em>new</em> agent mode for every review you run.   |
      | markup_leak                | pt     | body                    | - Liste os arquivos que o agente pode tocar no ticket.      |
      | markup_leak                | pt     | body                    | Rode o comando `npm test` antes de abrir o PR no time.      |
      | markup_leak                | en     | body                    | First line\nsecond line of the copy that the model escaped. |
      | emphasis_unbalanced        | pt     | body                    | Eu vejo **escopo aberto demais em quase todo PR do time.    |
      | emphasis_unbalanced        | en     | body                    | I see **** in the copy and nobody notices it at review.     |
      | assistant_chatter          | en     | body                    | Here is the revised slide copy you asked me to write today. |
      | assistant_chatter          | pt     | body                    | Claro! Aqui está o texto do slide revisado para o carrossel.|
      | placeholder_text           | pt     | body                    | Eu uso [inserir ferramenta] em todo ticket do meu time.     |
      | placeholder_text           | en     | heading                 | The {topic} that changes everything                         |
      | placeholder_text           | pt     | body                    | TODO escrever o corpo deste slide antes de publicar hoje.   |
      | encoding_garbled           | pt     | body                    | Eu reviso PRs toda semana e o erro Ã© sempre o mesmo aqui.  |
      | copy_truncated             | pt     | body                    | Eu reviso PRs de agentes toda semana e o erro mais comum é  |
      | copy_truncated             | en     | body                    | I review agent PRs every week and the mistake I see is...  |
      | body_too_short             | pt     | body                    | Escopo aberto custa caro.                                   |
      | wrong_language             | pt     | body                    | The agent is not the problem and the vague request is.      |
      | wrong_language             | en     | body                    | O agente não é o problema, o pedido vago é que é.           |
      | repeated_text              | pt     | body                    | O agente erra muito. O agente erra muito. E ninguém vê.     |
      | repeated_text              | en     | body                    | The the agent rewrites whole modules to fix a small bug.    |

  Scenario: A summary point cut mid-phrase is blocked
    Given slide 8's first summary point titled "Comece com dois ou" with body "Três agentes, não dez."
    When the deck is validated
    Then slide 8 is blocked by "structured_item_split"

  Scenario: A hook whose body repeats its heading is blocked
    Given slide 1's heading and body both "Meu time de agentes não é chatbot. É autonomia aprovada."
    When the deck is validated
    Then slide 1 is blocked by "heading_repeated_in_body"

  Scenario: Legit emphasis is never a leak
    Given a PT body with "**escopo**" and an EN body with "<strong>scope</strong>"
    When the slide is validated
    Then no copy-hygiene violation is reported

  Scenario: Older contracts keep their semantics
    Given the "hero_lower_third_v3" presentation policy
    And a body written as a fenced JSON object
    When the slide is validated
    Then no copy-hygiene violation is reported

  Scenario: The EN casing repair never capitalizes after a colon
    Given the EN copy "I see the mistake: It responds" and "How to decide: Pass or return"
    When the deterministic repair runs
    Then the copy reads "I see the mistake: it responds" and "How to decide: pass or return"
    And "Note: I was wrong" and "The tool: Claude Code wins" keep their capitals

  Scenario: A fenced blob's summary points are kept whole
    Given slide 8 written as a fenced blob whose summary_points include "Comece com dois ou três agentes"
    When the deterministic repair runs
    Then the first summary point title is "Comece com dois ou três agentes"

  Scenario: A key point is never split on a connector word
    Given the key point "Comece com dois ou três agentes, não dez."
    When it is split into a summary point
    Then the title is "Comece com dois ou três agentes" and the body "não dez."
