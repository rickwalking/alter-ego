# ADR-006: Use JSONB for Rich Content Documents

## Status

Accepted

## Context

Blog posts, carousel slides, and persona profiles require flexible, nested data structures that evolve over time. Traditional relational columns (VARCHAR, TEXT) are too rigid for rich text content, version history, and AI-generated metadata.

## Decision

Use **PostgreSQL JSONB** for rich content documents with the following rules:
1. JSONB for document content, metadata, and version snapshots
2. Dedicated relational columns for query/filter fields (status, created_at, etc.)
3. GIN indexes on JSONB paths used in queries
4. JSON Schema validation at application layer (Zod/Pydantic)

## Decision Drivers

- Rich text content (TipTap/ProseMirror format) is inherently nested
- Version snapshots need to store full document state
- AI-generated metadata (suggestions, scores, citations) varies by content type
- Schema will evolve during the pivot — need flexibility

## Considered Options

### Option 1: Pure Relational (normalized tables)

- **Good:** ACID guarantees; familiar SQL queries
- **Bad:** Excessive JOINs for nested content; schema migrations for every new field
- **Verdict:** Rejected — too rigid for evolving document structures

### Option 2: Document Store (MongoDB)

- **Good:** Native document support; flexible schema
- **Bad:** Additional database to maintain; loses PostgreSQL's reliability and ecosystem
- **Verdict:** Rejected — don't add another database for one use case

### Option 3: PostgreSQL JSONB

- **Good:**
  - Combines document flexibility with relational power
  - Same database we already use
  - GIN indexes enable efficient JSONB queries
  - ACID transactions across JSONB and relational data
- **Bad:**
  - JSONB queries are slower than relational columns
  - No native JSON Schema validation (must enforce at app layer)
  - Can become messy if overused
- **Verdict:** Accepted — best balance of flexibility and consistency

## Guidelines

### When to Use JSONB

| Use Case | Store As |
|----------|----------|
| Rich text content (TipTap nodes) | JSONB |
| Version snapshots | JSONB |
| AI suggestions/metadata | JSONB |
| Configuration/settings | JSONB |
| User preferences | JSONB |
| References/foreign keys | Relational (UUID columns) |
| Query/filter fields | Relational (indexed columns) |
| Aggregations/sums | Relational (numeric columns) |

### Indexing Strategy

```sql
-- GIN index for JSONB path queries
CREATE INDEX idx_blog_posts_content_gin ON blog_posts USING GIN (content);

-- B-tree index on JSONB extracted values (faster than GIN for equality)
CREATE INDEX idx_blog_posts_status ON blog_posts ((content->>'status'));
```

### Validation

```python
# Backend: Pydantic validation before DB insert
from pydantic import BaseModel

class BlogPostContent(BaseModel):
    type: str = "doc"
    content: list[dict]

post.content = BlogPostContent(**raw_content).model_dump()
```

```typescript
// Frontend: Zod validation before API call
const BlogPostContentSchema = z.object({
  type: z.literal("doc"),
  content: z.array(z.record(z.unknown())),
});
```

## Related Decisions

- ADR-007: Use PostgreSQL for Primary Persistence

## Tags

#database #postgres #jsonb #schema
