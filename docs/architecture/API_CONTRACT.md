# API Contract - Frontend & Backend Integration

## Overview

This document defines the API contract between the Next.js frontend and Python backend for the Agentic RAG system.

## Base URL

```
Development: http://localhost:8000
Production: https://api.your-domain.com
```

## Authentication

All API requests require an API key in the header:

```http
X-API-Key: your-api-key-here
```

## WebSocket Protocol (Primary)

### Connection

**Endpoint:** `ws://localhost:8000/ws/chat/{conversation_id}`

**Connection Flow:**
1. Frontend establishes WebSocket connection
2. Backend accepts connection
3. Bidirectional communication begins
4. Either party can close connection

### Message Types

#### 1. Client -> Server: User Message

```json
{
  "message": "What is machine learning?",
  "conversation_id": "conv_123",
  "metadata": {
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

#### 2. Server -> Client: Streaming Token

```json
{
  "type": "token",
  "content": "Machine",
  "conversation_id": "conv_123",
  "timestamp": "2024-01-15T10:30:01Z"
}
```

#### 3. Server -> Client: Tool Call

```json
{
  "type": "tool_call",
  "tool": "hybrid_search_tool",
  "input": {
    "query": "machine learning",
    "top_k": 5
  },
  "timestamp": "2024-01-15T10:30:02Z"
}
```

#### 4. Server -> Client: Tool Result (with sources)

```json
{
  "type": "tool_result",
  "tool": "hybrid_search_tool",
  "documents": [
    {
      "id": "chunk_abc123",
      "title": "Introduction to Machine Learning",
      "content_preview": "Machine learning is a subset of artificial intelligence...",
      "score": 0.89,
      "metadata": {
        "source_file": "ml-basics.pdf",
        "chunk_index": 3
      }
    },
    {
      "id": "chunk_def456",
      "title": "Deep Learning Fundamentals",
      "content_preview": "Deep learning uses neural networks with multiple layers...",
      "score": 0.76,
      "metadata": {
        "source_file": "deep-learning.pdf",
        "chunk_index": 1
      }
    }
  ],
  "timestamp": "2024-01-15T10:30:03Z"
}
```

#### 5. Server -> Client: Completion

```json
{
  "type": "done",
  "conversation_id": "conv_123",
  "timestamp": "2024-01-15T10:30:05Z"
}
```

#### 6. Server -> Client: Error

```json
{
  "type": "error",
  "code": "AGENT_ERROR",
  "message": "Failed to retrieve context from knowledge base",
  "details": {
    "error_type": "RetrievalError",
    "retries": 3
  },
  "timestamp": "2024-01-15T10:30:06Z"
}
```

## REST API Endpoints

> **The authoritative, machine-generated REST contract lives in [`openapi.json`](./openapi.json)** — exported from the running FastAPI app via
> `backend/scripts/export_openapi.py` (AE-0141). Per-endpoint request/response schemas, status codes, and
> auth requirements are no longer hand-maintained here (they drifted); consult the generated spec or the live
> `/docs` (Swagger) / `/openapi.json` endpoints. The frontend Zod schemas are checked against this artifact by
> the `check:schema-drift` gate. This document retains only the durable narrative below (WebSocket protocol,
> error model, integration patterns, versioning).

## Error Responses

### Standard Error Format

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {}
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_REQUEST` | 400 | Request validation failed |
| `UNAUTHORIZED` | 401 | Invalid or missing API key |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `RATE_LIMITED` | 429 | Too many requests |
| `AGENT_ERROR` | 500 | Agent execution failed |
| `RETRIEVAL_ERROR` | 500 | Vector search failed |
| `LLM_ERROR` | 502 | LLM provider error |
| `INTERNAL_ERROR` | 500 | Internal server error |

### Example Error Responses

**Validation Error (400):**
```json
{
  "success": false,
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Validation failed",
    "details": {
      "field": "title",
      "error": "Title is required"
    }
  }
}
```

**Rate Limit (429):**
```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMITED",
    "message": "Too many requests",
    "details": {
      "retry_after": 60,
      "limit": 100,
      "remaining": 0
    }
  }
}
```

## Frontend Integration Examples

### React Hook for WebSocket Chat

```typescript
// hooks/useWebSocketChat.ts
import { useEffect, useRef, useState, useCallback } from 'react';

interface ChatMessage {
  type: 'user' | 'assistant';
  content: string;
  sources?: Array<{
    id: string;
    title: string;
    content_preview: string;
  }>;
  isStreaming?: boolean;
}

interface WebSocketEvent {
  type: 'token' | 'tool_call' | 'tool_result' | 'done' | 'error';
  content?: string;
  tool?: string;
  documents?: Array<{
    id: string;
    title: string;
    content_preview: string;
  }>;
  message?: string;
}

export function useWebSocketChat(conversationId: string) {
  const ws = useRef<WebSocket | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);

  useEffect(() => {
    const socket = new WebSocket(
      `ws://localhost:8000/ws/chat/${conversationId}`
    );

    socket.onopen = () => setIsConnected(true);
    socket.onclose = () => setIsConnected(false);

    socket.onmessage = (event) => {
      const data: WebSocketEvent = JSON.parse(event.data);

      switch (data.type) {
        case 'token':
          setMessages(prev => {
            const last = prev[prev.length - 1];
            if (last?.type === 'assistant' && last.isStreaming) {
              return [
                ...prev.slice(0, -1),
                { ...last, content: last.content + (data.content || '') }
              ];
            }
            return [...prev, {
              type: 'assistant',
              content: data.content || '',
              isStreaming: true
            }];
          });
          break;

        case 'tool_result':
          setMessages(prev => {
            const last = prev[prev.length - 1];
            if (last?.type === 'assistant') {
              return [
                ...prev.slice(0, -1),
                { ...last, sources: data.documents }
              ];
            }
            return prev;
          });
          break;

        case 'done':
          setMessages(prev => {
            const last = prev[prev.length - 1];
            if (last?.type === 'assistant') {
              return [
                ...prev.slice(0, -1),
                { ...last, isStreaming: false }
              ];
            }
            return prev;
          });
          setIsStreaming(false);
          break;

        case 'error':
          console.error('WebSocket error:', data.message);
          setIsStreaming(false);
          break;
      }
    };

    ws.current = socket;

    return () => {
      socket.close();
    };
  }, [conversationId]);

  const sendMessage = useCallback((message: string) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      // Add user message to list
      setMessages(prev => [...prev, { type: 'user', content: message }]);
      setIsStreaming(true);

      // Send to server
      ws.current.send(JSON.stringify({ message }));
    }
  }, []);

  return { messages, sendMessage, isConnected, isStreaming };
}
```

### Usage in Component

```tsx
// components/ChatInterface.tsx
import { useWebSocketChat } from '@/hooks/useWebSocketChat';

export function ChatInterface({ conversationId }: { conversationId: string }) {
  const { messages, sendMessage, isConnected, isStreaming } = useWebSocketChat(conversationId);
  const [input, setInput] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !isStreaming) {
      sendMessage(input.trim());
      setInput('');
    }
  };

  return (
    <div>
      <div className="connection-status">
        {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
      </div>

      <div className="messages">
        {messages.map((msg, i) => (
          <div key={i} className={`message ${msg.type}`}>
            <p>{msg.content}</p>
            {msg.isStreaming && <span className="typing">...</span>}
            {msg.sources && (
              <div className="sources">
                {msg.sources.map(source => (
                  <span key={source.id} className="source-tag">
                    {source.title}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      <form onSubmit={handleSubmit}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          disabled={!isConnected || isStreaming}
          placeholder="Type your message..."
        />
        <button type="submit" disabled={!isConnected || isStreaming}>
          Send
        </button>
      </form>
    </div>
  );
}
```

## Data Models

### TypeScript Interfaces (Frontend)

> Authoritative schemas are the generated [`openapi.json`](./openapi.json); the interfaces below are a frontend convenience snapshot.

```typescript
// types/api.ts

export interface Document {
  id: string;
  title: string;
  content?: string;
  tags: string[];
  file_type?: string;
  chunk_count: number;
  created_at: string;
  updated_at: string;
}

export interface SearchResult {
  id: string;
  content: string;
  title: string;
  score: number;
  metadata: {
    document_id: string;
    chunk_index: number;
    source_file: string;
  };
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: Array<{
    id: string;
    title: string;
  }>;
  timestamp: string;
}

export interface Conversation {
  id: string;
  title: string;
  message_count: number;
  last_message_at: string;
  created_at: string;
}

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  message?: string;
}

export interface ApiError {
  success: false;
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
}
```

## Versioning

**Current API Version:** `v1`

**Version Header:** All requests should include API version:
```http
X-API-Version: v1
```

## Changelog

### v1.5.0 (Phase 5 — Migration & Launch)
- `POST /api/admin/migration/phase5` — Run data migration (MIG-001–004)
- Feature flags gate editorial workflow, quality, kanban, calendar endpoints (503 when disabled)
- Workflow failure alerts via background worker (MON-002)
- See [editorial-workflow-user-guide.md](../guides/editorial-workflow-user-guide.md)

### v1.4.0 (Phase 4 — Quality & Polish)
- `GET /api/blog-posts/{id}/seo-analyze` — SEO analysis
- `GET /api/blog-posts/{id}/accessibility-check` — Accessibility validation
- `POST /api/blog-posts/{id}/plagiarism-check` — Plagiarism detection
- `GET /api/blog-posts/{id}/ai-disclosure` — AI disclosure label
- `GET /api/editorial-analytics` — Dashboard analytics

### v1.3.0 (Phase 3 — Workflow & Collaboration)
- `GET /api/workflow` — Kanban board
- `GET /api/content-calendar` — Content calendar
- `GET /api/notifications` — Notification center
- `GET /api/workflow-audit/{type}/{id}` — Audit log
- Blog workflow: submit, approve, reject, publish, schedule

### v1.2.0 (Phase 2 — AI Editorial)
- `POST /api/carousels/{id}/editorial-workflow/start` — Start carousel workflow
- `POST /api/carousels/{id}/editorial-workflow/resume` — Resume after human review
- `GET /api/carousels/{id}/editorial-workflow/stream` — SSE workflow events
- `POST /api/blog-posts/{id}/ai/suggest` — AI writing suggestions
- `POST /api/personas`, `GET /api/personas` — Persona management
- `POST /api/rubrics`, `GET /api/rubrics` — Quality rubrics

### v1.0.0 (Current)
- Initial API release
- WebSocket support for streaming
- Hybrid search implementation
- Document management endpoints
