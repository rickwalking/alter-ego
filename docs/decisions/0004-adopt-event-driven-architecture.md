# ADR-004: Adopt Event-Driven Architecture for Content Workflows

## Status

Accepted

## Context

The pivot introduces complex workflows with multiple phases, human approvals, and parallel AI processing. The current synchronous API model cannot handle:
1. Long-running AI generation (5+ minutes for images)
2. Human approval delays (hours or days)
3. Parallel agent execution
4. Audit trails of who changed what and when

## Decision

Adopt an **event-driven architecture** using **Redis Streams** as the event backbone, with PostgreSQL as the authoritative state store.

## Decision Drivers

- Workflows can span hours or days (human approval gates)
- Multiple services need to react to the same events (notifications, analytics, audit)
- Must support replay for debugging and recovery
- Must not lose events on restarts

## Considered Options

### Option 1: Synchronous REST API Only

- **Good:** Simple, familiar
- **Bad:** HTTP timeouts prevent long-running work; no audit trail; no parallel processing
- **Verdict:** Rejected — doesn't meet requirements

### Option 2: Apache Kafka

- **Good:** Gold standard for event streaming; infinite replay; excellent ecosystem
- **Bad:** Additional infrastructure complexity; overkill for current throughput (<1000 events/day)
- **Verdict:** Rejected — too heavy for current scale; reconsider if we exceed 10k events/day

### Option 3: Redis Streams + PostgreSQL

- **Good:**
  - Redis Streams provide durable, ordered events with consumer groups
  - We already use Redis for caching and sessions
  - PostgreSQL stores authoritative state (event sourcing pattern)
  - Simple to operate; single Redis instance handles our scale
- **Bad:**
  - Not truly infinite retention (configure max memory policy)
  - Less ecosystem than Kafka (no Kafka Connect, fewer tools)
- **Verdict:** Accepted — best fit for our current scale and existing infrastructure

### Option 4: RabbitMQ

- **Good:** Mature message broker; good routing capabilities
- **Bad:** Not a true event log (messages consumed are gone); no native replay
- **Verdict:** Rejected — doesn't support audit/replay requirements

## Consequences

**Good:**
- Workflows can span arbitrary time (events don't timeout)
- Services are decoupled — notification service doesn't block workflow engine
- Full audit trail via event log
- Can replay events to reconstruct state

**Bad:**
- Added complexity — developers must think in events, not just CRUD
- Event schema evolution requires care (add fields, don't remove)
- Debugging distributed workflows is harder than stepping through synchronous code
- Must handle idempotency (same event processed twice)

## Implementation Notes

```python
# Event publisher
async def publish_event(stream: str, event: dict):
    redis.xadd(stream, {"data": json.dumps(event)})

# Event consumer (worker)
async def consume_events(stream: str, group: str, consumer: str):
    messages = redis.xreadgroup(group, consumer, {stream: ">"})
    for msg in messages:
        event = json.loads(msg["data"])
        await handle_event(event)
        redis.xack(stream, group, msg["id"])
```

## Event Schema Standards

All events must follow this structure:

```json
{
  "event_id": "uuid",
  "event_type": "content.project.phase_changed",
  "aggregate_id": "project-uuid",
  "aggregate_type": "project",
  "timestamp": "2026-05-23T12:00:00Z",
  "version": 1,
  "payload": { ... },
  "metadata": {
    "user_id": "user-uuid",
    "trace_id": "trace-uuid",
    "source": "workflow_engine"
  }
}
```

## Related Decisions

- ADR-002: Use LangGraph for Workflow Engine
- ADR-007: Use PostgreSQL for Primary Persistence

## Tags

#architecture #events #redis #workflow
