# Agentic RAG Backend - Project Summary

## 🎯 Project Vision

Build a powerful Agentic RAG (Retrieval-Augmented Generation) backend using Python, LangChain Deep Agents, and hybrid search to power the RAG Chat frontend. The system combines **semantic search** (vector similarity) with **lexical search** (BM25) for superior document retrieval, then uses an intelligent agent to synthesize answers with streaming support.

---

## 📋 Deliverables

### 1. **BACKEND_ARCHITECTURE.md**
Complete architecture document covering:
- System overview and component diagram
- LangChain Deep Agent architecture with tools
- Hybrid search implementation (dense + sparse vectors)
- Streaming architecture (WebSocket + SSE)
- Document processing pipeline
- Technology stack and deployment options

### 2. **BACKEND_IMPLEMENTATION_PLAN.md**
4-week implementation roadmap with:
- **Week 1**: Project setup, database models, document processing
- **Week 2**: Hybrid retriever, RAG agent with tools
- **Week 3**: WebSocket/SSE streaming, API endpoints
- **Week 4**: Docker deployment, production configuration
- Code examples for all major components

### 3. **API_CONTRACT.md**
Complete API specification with:
- WebSocket protocol for real-time streaming
- REST endpoints for documents, search, and chat
- Message types and event formats
- Error handling and response codes
- Frontend integration examples (React hooks)
- TypeScript interfaces

---

## 🏗️ Architecture Highlights

### Core Components

```
┌─────────────────────────────────────────────────────────────────┐
│                     AGENTIC RAG SYSTEM                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐  │
│  │   Deep Agent     │  │  Hybrid Search   │  │   Streaming   │  │
│  │   with Tools     │  │  (Vector + BM25) │  │   (WS/SSE)    │  │
│  └────────┬─────────┘  └────────┬─────────┘  └───────┬───────┘  │
│           │                     │                    │          │
│           └─────────────────────┴────────────────────┘          │
│                              │                                   │
│  ┌───────────────────────────┴──────────────────────────────┐   │
│  │                    FastAPI Backend                        │   │
│  │  • Document upload & processing                          │   │
│  │  • Hybrid search (Pinecone)                              │   │
│  │  • Agent orchestration (LangChain)                       │   │
│  │  • Real-time streaming                                   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│  ┌───────────────────────────┴──────────────────────────────┐   │
│  │              External Services & Storage                  │   │
│  │  • Pinecone (Hybrid Vector Index)                        │   │
│  │  • PostgreSQL (Metadata & Conversations)                 │   │
│  │  • Redis (Caching & Session)                             │   │
│  │  • OpenAI/Anthropic (LLM)                                │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Key Features

#### 1. **Hybrid Search** 🔍
- **Dense vectors**: Semantic similarity using OpenAI embeddings (1024 dimensions)
- **Sparse vectors**: BM25 keyword search using Pinecone's sparse encoder
- **Fusion**: Reciprocal Rank Fusion (RRF) for combining results
- **Alpha weighting**: Adjustable balance between semantic and lexical search

#### 2. **Agentic RAG** 🤖
- **Deep Agents**: Built on LangGraph for durable execution
- **Tools**: Hybrid search, document management, conversation memory
- **Streaming**: Real-time token-by-token response streaming
- **Multi-step reasoning**: Agent can perform multiple searches if needed

#### 3. **Streaming Architecture** ⚡
- **WebSocket**: Primary real-time communication protocol
- **Server-Sent Events (SSE)**: HTTP fallback for simpler clients
- **Event types**: Tokens, tool calls, tool results, completion, errors

#### 4. **Document Processing** 📄
- **Supported formats**: PDF, TXT, MD
- **Chunking**: Recursive character text splitter with overlap
- **Embeddings**: Dense (OpenAI) + Sparse (Pinecone) for each chunk
- **Metadata**: Document ID, title, tags, chunk index

---

## 🛠️ Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Framework** | FastAPI | Modern, fast web framework |
| **Agents** | LangChain + LangGraph | Agent orchestration |
| **LLM** | OpenAI GPT-4o / Anthropic Claude | Language model |
| **Embeddings** | OpenAI text-embedding-3-large | Dense vectors (1024d) |
| **Vector DB** | Pinecone | Hybrid vector index |
| **Database** | PostgreSQL + asyncpg | Metadata & conversations |
| **Cache** | Redis | Session & caching |
| **Python** | 3.11+ | Runtime |
| **Package Manager** | uv | Fast Python package management |

---

## 📊 API Overview

### WebSocket Protocol (Primary)
```
ws://localhost:8000/ws/chat/{conversation_id}
```

**Message Types:**
- `token`: Streaming response content
- `tool_call`: Agent invoking search tool
- `tool_result`: Retrieved documents with metadata
- `done`: Response complete
- `error`: Error occurred

### REST Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat` | POST | Non-streaming chat |
| `/api/chat/stream` | POST | SSE streaming chat |
| `/api/documents` | GET/POST/DELETE | Document CRUD |
| `/api/search` | POST | Hybrid search |
| `/api/conversations` | GET/DELETE | Conversation management |

---

## 🚀 Implementation Timeline

### Week 1: Infrastructure
- [ ] FastAPI project setup with uv
- [ ] PostgreSQL database models
- [ ] Document upload and processing pipeline
- [ ] File chunking and embedding generation

### Week 2: Core RAG
- [ ] Pinecone hybrid index setup
- [ ] Hybrid retriever (dense + sparse)
- [ ] LangChain agent with tools
- [ ] Conversation memory integration

### Week 3: Streaming & API
- [ ] WebSocket implementation
- [ ] SSE fallback endpoint
- [ ] Document management API
- [ ] Search API

### Week 4: Production
- [ ] Docker containerization
- [ ] Kubernetes deployment config
- [ ] Monitoring (LangSmith)
- [ ] Security hardening

**Total Duration**: 4 weeks  
**Team Size**: 2-3 developers

---

## 💡 Key Design Decisions

### Why Hybrid Search?
- **Semantic search** captures meaning and synonyms
- **BM25** captures exact keyword matches (names, jargon, IDs)
- **Combined**: Better recall and precision than either alone

### Why Deep Agents?
- Built on LangGraph for **durable execution**
- **Automatic conversation compression** for long contexts
- **Tool orchestration** with visibility into each step
- **Streaming support** built-in

### Why WebSocket + SSE?
- **WebSocket**: Best for real-time bidirectional communication
- **SSE**: Simple HTTP fallback, works with proxies/firewalls
- **Both**: Maximum compatibility across deployment scenarios

### Why Pinecone?
- Managed service (no ops overhead)
- Native hybrid search support
- Automatic BM25 sparse vector encoding
- Low latency at scale

---

## 📁 Project Files

```
my-app/
├── Frontend (existing)
│   ├── src/
│   ├── components/
│   └── ...
│
└── docs/
    ├── BACKEND_ARCHITECTURE.md      # Complete architecture
    ├── BACKEND_IMPLEMENTATION_PLAN.md # 4-week roadmap
    └── API_CONTRACT.md              # API specification
```

---

## 🎯 Next Steps

1. **Review Documents**: Read through all three documents
2. **Setup Environment**: Install Python 3.11+, uv, Docker
3. **Create Pinecone Account**: Sign up and get API key
4. **Start Implementation**: Follow Week 1 of implementation plan
5. **Test Integration**: Connect frontend to backend WebSocket

---

## 📚 Additional Resources

- **LangChain Docs**: https://python.langchain.com/docs/
- **Pinecone Hybrid Search**: https://docs.pinecone.io/guides/data/understanding-hybrid-search
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **Context7 LangChain**: https://context7.com/websites/langchain/llms.txt

---

## ✅ Summary

This project delivers a complete blueprint for building a production-ready Agentic RAG backend with:

✅ **Hybrid search** (semantic + lexical)  
✅ **Intelligent agent** with tool use  
✅ **Real-time streaming** (WebSocket/SSE)  
✅ **Complete API specification**  
✅ **4-week implementation plan**  
✅ **Docker deployment ready**

**Ready to start building!** 🚀
