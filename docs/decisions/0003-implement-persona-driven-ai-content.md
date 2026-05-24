# ADR-003: Implement Persona-Driven AI Content Generation

## Status

Accepted

## Context

Current AI-generated content lacks Pedro's authentic voice. Outputs feel generic, overuse certain phrases ("In today's world", "Let's dive in"), and miss personal anecdotes and strong opinions. The pivot requires content that sounds like Pedro wrote it — not AI.

## Decision

Build a **Persona Engine** that captures, enforces, and learns Pedro's writing voice through:
1. Explicit persona profiles (tone, style, forbidden phrases, examples)
2. Voice match scoring (0-100) on all generated content
3. Feedback loop that learns from human edits

## Decision Drivers

- Content must feel authentically human, not AI-generated
- Voice consistency across all carousels and blog posts
- System must improve over time based on corrections
- Must be measurable — we need a score, not a gut feeling

## Considered Options

### Option 1: Prompt Engineering Only

- **Good:** Simple, no new infrastructure
- **Bad:** Fragile — one token can derail the voice; doesn't learn from feedback
- **Verdict:** Rejected — insufficient for production quality

### Option 2: Fine-tuned Model (LoRA/QLoRA)

- **Good:** Highest fidelity voice matching once trained
- **Bad:** Expensive to train and maintain; requires GPU infrastructure; slow iteration cycle
- **Verdict:** Rejected — too expensive and slow for current needs; reconsider at scale

### Option 3: Persona Engine with RAG + Feedback Loop

- **Good:**
  - Immediate — no training required
  - Iterative — improves with every correction
  - Measurable — voice match scoring provides objective quality metric
  - Auditable — we can see why content scored low
- **Bad:**
  - Higher token usage per generation (persona context + examples + feedback)
  - Requires ongoing curation of writing samples
- **Verdict:** Accepted — best balance of quality, cost, and speed

## Consequences

**Good:**
- Content quality becomes measurable and improvable
- Voice drift is detected and flagged before publication
- Feedback from edits automatically improves future outputs
- Can support multiple personas (e.g., "Pedro Professional", "Pedro Casual", "Pedro Portuguese")

**Bad:**
- ~20-30% increase in LLM token usage per generation
- Requires Pedro to actively provide writing samples and mark corrections
- Persona maintenance is ongoing work
- Voice match scoring itself consumes tokens

## Implementation Notes

```python
class PersonaAgent:
    def __init__(self, persona: PersonaProfile):
        self.style_guide = self._build_style_guide(persona)

    async def enforce(self, content: str) -> str:
        prompt = f"{self.style_guide}\n\nRewrite:\n{content}"
        return await llm.complete(prompt)

    async def evaluate_match(self, content: str) -> dict:
        prompt = f"Score this against persona..."
        return await llm.structured_complete(prompt, schema=VoiceScoreSchema)

    async def record_correction(self, original: str, corrected: str):
        # Store in feedback DB; update persona examples
        pass
```

## Related Decisions

- ADR-002: Use LangGraph for Workflow Engine
- ADR-006: Use Pinecone for Vector Store (semantic search over writing samples)

## Tags

#ai #persona #quality #content
