# Alter-Ego chat system prompt, v4 (AE-0499)

The public chat speaks as Pedro ("You are Pedro Marins"), but v3 described Pedro
in the third person in several places, and the model copied it into replies
("I just know Pedro's stuff", "his alter ego"). v4 makes every reference first
person. `alter_ego_agent.py` loads it through `ALTER_EGO_PROMPT_VERSION`
(`domain/constants/alter_ego_voice.py`); v1 to v3 stay untouched for rollback.

Changes from `v3/system.md`:

- New section `SPEAKING AS ME (FIRST PERSON ONLY)`: always "I / my / me" ("eu /
  meu / minha"), never refer to Pedro in the third person, never call yourself
  "his alter ego", "an assistant for Pedro" or "o alter ego dele", and answer in
  the user's language (Portuguese or English). This is the only place the
  forbidden third-person phrases appear, quoted as forbidden.
- "they're Pedro's" (experiences) became "they're your own".
- "You draw from Pedro's CV, projects, blog posts, and notes" became "your own
  CV, your projects, your blog posts, and your notes", with the reply wording
  "my CV", "my projects", "my blog posts".
- The vague answer about how the chat works became first person: "I just answer
  from what I know and have written." / "Eu só respondo com o que eu sei e já
  escrevi." (was "I just know Pedro's stuff and try to be helpful.").
- "Never make up facts about Pedro's experience" became "about your own
  experience".

Unchanged: identity line, tone, the never-mention-companies and no-resume rules,
no tool or system disclosure, "I don't know" over invention, language matching,
the injection guardrails and the voice examples.

Tests: `tests/unit/agents/test_chat_first_person_ae0499.py` (scenarios in
`tests/features/chat_first_person_ae0499.feature`) check that v4 has no
third-person reference outside the rule section and run the reply checker over
the recorded sample replies in `tests/fixtures/chat_first_person_eval.yaml`.
