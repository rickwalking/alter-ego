---
name: knowledge-base
description: Search and list documents in the knowledge base. Use when the user asks factual questions, wants to find specific information, or needs to see what documents are available.
version: 1.0.0
---

# Knowledge Base

## Purpose

Retrieve information from uploaded documents to answer user questions
accurately and with citations.

## Tools

### search_documents

Semantic search across all uploaded documents.

**Parameters:**
- `query` — the search query string
- `top_k` — number of results to return (default: 5)

**When to use:**
- User asks a factual question
- User references "the document", "my files", "uploaded content"
- Any question that might benefit from grounded retrieval

**Response format:**
Numbered list of snippets with relevance scores. Cite the document title
and score when answering.

### list_documents

List all documents in the knowledge base.

**Parameters:**
- `status` — optional filter: `pending`, `processing`, `completed`, `failed`

**When to use:**
- User asks "what documents do I have?"
- User wants to see upload status

## Critical Rules

- ALWAYS search before answering factual questions
- If retrieval returns nothing, say so clearly — do not hallucinate
- Cite sources with document titles and relevance scores
- Keep answers concise; offer to elaborate if the user wants more detail
