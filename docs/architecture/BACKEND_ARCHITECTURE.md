# Agentic RAG Backend Architecture Plan

## Executive Summary

This document outlines the architecture for a Python-based Agentic RAG (Retrieval-Augmented Generation) backend that powers the RAG Chat frontend. The system uses **LangChain Deep Agents** with **hybrid search** (vector similarity + BM25 keyword search) to provide intelligent, context-aware responses.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT (Frontend)                         │
│                     Next.js + React App                         │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       │ WebSocket / SSE (Streaming)
                       │ HTTP REST API
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                     API GATEWAY (FastAPI)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Chat API  │  │ Document API│  │   Streaming Endpoint    │  │
│  │   (REST)    │  │   (REST)    │  │    (WebSocket/SSE)      │  │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘  │
└─────────┼────────────────┼─────────────────────┼────────────────┘
          │                │                     │
          └────────────────┴─────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                   AGENTIC RAG ORCHESTRATOR                       │
│              (LangChain Deep Agents + LangGraph)                 │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Deep Agent with Tools                        │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐  │   │
│  │  │  Tool:       │  │  Tool:       │  │  Tool:         │  │   │
│  │  │Hybrid Search │  │  Document    │  │  Memory        │  │   │
│  │  │  (Primary)   │  │  Management  │  │  (Context)     │  │   │
│  │  └──────┬───────┘  └──────┬───────┘  └───────┬────────┘  │   │
│  └─────────┼────────────────┼──────────────────┼───────────┘   │
└────────────┼────────────────┼──────────────────┼───────────────┘
             │                │                  │
             ▼                ▼                  ▼
┌────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  LLM Provider  │  │  Vector Store    │  │   Memory Store   │
│   (OpenAI/     │  │   (Pinecone      │  │   (Redis/        │
│   Anthropic)   │  │    Hybrid Index) │  │    PostgreSQL)   │
└────────────────┘  └──────────────────┘  └──────────────────┘
```

## Core Components

### 1. Deep Agent Architecture

**Why Deep Agents?**
- Built on LangGraph for durable execution
- Supports streaming, persistence, and human-in-the-loop
- Automatic compression of long conversations
- Virtual filesystem for document management
- Subagent-spawning for complex tasks

**Agent Components:**

```python
# agent/rag_agent.py
from langchain.agents import create_agent
from langchain.tools import tool
from typing import List, Dict

class RAGAgent:
    def __init__(self, vector_store, memory_store, llm):
        self.tools = [
            self.hybrid_search_tool,
            self.document_management_tool,
            self.conversation_memory_tool
        ]
        self.agent = create_agent(
            model=llm,
            tools=self.tools,
            system_prompt=self._get_system_prompt()
        )

    @tool(response_format="content_and_artifact")
    def hybrid_search_tool(self, query: str, top_k: int = 5) -> tuple:
        """
        Perform hybrid search combining vector similarity and BM25.
        Returns both content and retrieved documents as artifact.
        """
        # Dense vector search (semantic)
        dense_results = self.vector_store.similarity_search(query, k=top_k)

        # Sparse vector search (BM25 keyword)
        sparse_results = self.vector_store.sparse_search(query, k=top_k)

        # Fusion: Reciprocal Rank Fusion (RRF)
        fused_results = self._reciprocal_rank_fusion(dense_results, sparse_results)

        serialized = self._serialize_documents(fused_results)
        return serialized, fused_results

    def _reciprocal_rank_fusion(self, dense_results, sparse_results, k=60):
        """
        Combine dense and sparse results using RRF algorithm.
        Score = Σ 1/(k + rank)
        """
        scores = {}

        for rank, doc in enumerate(dense_results):
            scores[doc.id] = scores.get(doc.id, 0) + 1 / (k + rank)

        for rank, doc in enumerate(sparse_results):
            scores[doc.id] = scores.get(doc.id, 0) + 1 / (k + rank)

        # Sort by combined score
        sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [doc for doc_id, score in sorted_docs]
```

### 2. Hybrid Search Implementation

**Why Hybrid Search?**
- **Dense vectors** capture semantic meaning and synonyms
- **Sparse vectors** (BM25) capture exact keyword matches
- Combined approach provides better recall and precision

**Implementation Strategy:**

```python
# retrievers/hybrid_retriever.py
from typing import List
from langchain_core.documents import Document
from pinecone import Pinecone

class HybridRetriever:
    """
    Hybrid retriever combining dense (semantic) and sparse (BM25) search.
    Uses Pinecone's hybrid index with dotproduct metric.
    """

    def __init__(self, index_name: str, alpha: float = 0.5):
        """
        Args:
            alpha: Weight for dense vs sparse (0=BM25 only, 1=semantic only, 0.5=balanced)
        """
        self.pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        self.index = self.pc.Index(index_name)
        self.alpha = alpha

        # Embedding models
        self.dense_embedding_model = "text-embedding-3-large"  # OpenAI
        self.sparse_embedding_model = "pinecone-sparse-english-v0"  # Pinecone

    async def hybrid_search(
        self,
        query: str,
        top_k: int = 5,
        filter: Dict = None
    ) -> List[Document]:
        """
        Perform hybrid search with fusion.

        Pipeline:
        1. Generate dense vector (semantic embedding)
        2. Generate sparse vector (BM25 term frequencies)
        3. Query Pinecone hybrid index
        4. Return ranked documents
        """
        # Generate embeddings
        dense_vector = await self._get_dense_embedding(query)
        sparse_vector = await self._get_sparse_embedding(query)

        # Apply alpha weighting
        weighted_dense, weighted_sparse = self._apply_weighting(
            dense_vector, sparse_vector, self.alpha
        )

        # Query hybrid index
        results = self.index.query(
            vector=weighted_dense,
            sparse_vector=weighted_sparse,
            top_k=top_k,
            filter=filter,
            include_metadata=True
        )

        return self._convert_to_documents(results)

    async def _get_dense_embedding(self, text: str) -> List[float]:
        """Generate dense vector using OpenAI embeddings."""
        from openai import AsyncOpenAI
        client = AsyncOpenAI()

        response = await client.embeddings.create(
            model=self.dense_embedding_model,
            input=text
        )
        return response.data[0].embedding

    async def _get_sparse_embedding(self, text: str) -> Dict:
        """Generate sparse vector using Pinecone's sparse encoder."""
        # Use Pinecone's inference API for sparse vectors
        sparse_embeddings = self.pc.inference.embed(
            model=self.sparse_embedding_model,
            inputs=[text],
            parameters={"input_type": "query"}
        )

        return {
            'indices': sparse_embeddings[0]['sparse_indices'],
            'values': sparse_embeddings[0]['sparse_values']
        }

    def _apply_weighting(self, dense, sparse, alpha):
        """Apply convex combination: alpha * dense + (1-alpha) * sparse"""
        weighted_dense = [v * alpha for v in dense]
        weighted_sparse = {
            'indices': sparse['indices'],
            'values': [v * (1 - alpha) for v in sparse['values']]
        }
        return weighted_dense, weighted_sparse
```

### 3. Streaming Architecture

**Why Streaming?**
- Better UX: Users see responses as they generate
- Reduced perceived latency
- Supports real-time token-by-token display

**Implementation:**

```python
# api/streaming.py
from fastapi import FastAPI, WebSocket
from fastapi.responses import StreamingResponse
import json
import asyncio

app = FastAPI()

@app.websocket("/ws/chat/{conversation_id}")
async def websocket_chat(websocket: WebSocket, conversation_id: str):
    """
    WebSocket endpoint for real-time chat with streaming.

    Message Types:
    - user_message: User sends a message
    - token: Streaming token from LLM
    - tool_call: Agent invokes a tool
    - tool_result: Tool execution result
    - done: Generation complete
    - error: Error occurred
    """
    await websocket.accept()

    try:
        while True:
            # Receive user message
            data = await websocket.receive_json()
            user_message = data["message"]

            # Get agent for this conversation
            agent = await get_or_create_agent(conversation_id)

            # Stream agent response
            async for event in agent.astream(
                {"messages": [{"role": "user", "content": user_message}]},
                stream_mode="values"
            ):
                message = event["messages"][-1]

                # Send different message types based on content
                if message.type == "ai":
                    # Streaming tokens
                    if hasattr(message, 'content'):
                        await websocket.send_json({
                            "type": "token",
                            "content": message.content
                        })

                elif message.type == "tool":
                    # Tool execution
                    await websocket.send_json({
                        "type": "tool_call",
                        "tool": message.name,
                        "input": message.args
                    })

                    # After tool execution, send results
                    if message.artifact:
                        await websocket.send_json({
                            "type": "tool_result",
                            "tool": message.name,
                            "documents": [
                                {
                                    "id": doc.metadata.get("id"),
                                    "title": doc.metadata.get("title"),
                                    "content_preview": doc.page_content[:200]
                                }
                                for doc in message.artifact
                            ]
                        })

            # Signal completion
            await websocket.send_json({
                "type": "done",
                "conversation_id": conversation_id
            })

    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
        await websocket.close()

# Alternative: Server-Sent Events (SSE)
@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    SSE endpoint for streaming chat responses.
    Better for HTTP-only clients.
    """
    async def event_generator():
        agent = await get_or_create_agent(request.conversation_id)

        async for event in agent.astream(
            {"messages": [{"role": "user", "content": request.message}]},
            stream_mode="values"
        ):
            message = event["messages"][-1]

            # Format as SSE
            yield f"data: {json.dumps({
                'type': message.type,
                'content': message.content if hasattr(message, 'content') else None,
                'tool': message.name if hasattr(message, 'name') else None
            })}\n\n"

        # End stream
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
```

### 4. Document Processing Pipeline

```python
# ingestion/document_processor.py
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    UnstructuredMarkdownLoader
)
from typing import List
import hashlib

class DocumentProcessor:
    """
    Process documents for ingestion into vector store.

    Pipeline:
    1. Load document (PDF, TXT, MD)
    2. Split into chunks
    3. Generate embeddings (dense + sparse)
    4. Upsert to hybrid index
    """

    def __init__(self, vector_store):
        self.vector_store = vector_store
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            add_start_index=True
        )

    async def process_document(
        self,
        file_path: str,
        metadata: Dict
    ) -> List[str]:
        """
        Process a document and ingest into vector store.

        Returns:
            List of document IDs
        """
        # 1. Load document
        loader = self._get_loader(file_path)
        documents = loader.load()

        # 2. Split into chunks
        chunks = self.text_splitter.split_documents(documents)

        # 3. Add metadata
        for i, chunk in enumerate(chunks):
            chunk.metadata.update({
                **metadata,
                "chunk_index": i,
                "chunk_hash": self._hash_content(chunk.page_content),
                "source_file": file_path
            })

        # 4. Generate embeddings and upsert
        doc_ids = await self._upsert_chunks(chunks)

        return doc_ids

    async def _upsert_chunks(self, chunks: List[Document]) -> List[str]:
        """Generate embeddings and upsert to hybrid index."""
        records = []

        for chunk in chunks:
            # Generate dense embedding (OpenAI)
            dense_vector = await self._get_dense_embedding(chunk.page_content)

            # Generate sparse embedding (Pinecone)
            sparse_vector = await self._get_sparse_embedding(chunk.page_content)

            records.append({
                "id": chunk.metadata["chunk_hash"],
                "values": dense_vector,
                "sparse_values": sparse_vector,
                "metadata": {
                    "text": chunk.page_content,
                    **chunk.metadata
                }
            })

        # Batch upsert
        self.vector_store.upsert(vectors=records)

        return [r["id"] for r in records]

    def _get_loader(self, file_path: str):
        """Get appropriate loader based on file extension."""
        ext = file_path.lower().split('.')[-1]

        loaders = {
            'pdf': PyPDFLoader,
            'txt': TextLoader,
            'md': UnstructuredMarkdownLoader,
            'markdown': UnstructuredMarkdownLoader
        }

        loader_class = loaders.get(ext, TextLoader)
        return loader_class(file_path)

    def _hash_content(self, content: str) -> str:
        """Generate unique hash for content deduplication."""
        return hashlib.md5(content.encode()).hexdigest()
```

## API Design

### REST Endpoints

```yaml
# OpenAPI Specification
openapi: 3.0.0
info:
  title: RAG Chat API
  version: 1.0.0

paths:
  /api/chat:
    post:
      summary: Send a message (non-streaming)
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                conversation_id:
                  type: string
      responses:
        200:
          description: AI response
          content:
            application/json:
              schema:
                type: object
                properties:
                  response:
                    type: string
                  sources:
                    type: array
                    items:
                      type: object
                      properties:
                        id:
                          type: string
                        title:
                          type: string
                        content:
                          type: string

  /api/chat/stream:
    post:
      summary: Send a message with streaming (SSE)
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                conversation_id:
                  type: string
      responses:
        200:
          description: Streaming response
          content:
            text/event-stream:
              schema:
                type: string

  /api/documents:
    get:
      summary: List all documents
      responses:
        200:
          description: List of documents

    post:
      summary: Upload a new document
      requestBody:
        content:
          multipart/form-data:
            schema:
              type: object
              properties:
                file:
                  type: string
                  format: binary
                title:
                  type: string
                tags:
                  type: array
                  items:
                    type: string
      responses:
        201:
          description: Document uploaded

  /api/documents/{id}:
    get:
      summary: Get document by ID

    put:
      summary: Update document

    delete:
      summary: Delete document

  /api/search:
    post:
      summary: Hybrid search
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                query:
                  type: string
                top_k:
                  type: integer
                  default: 5
                alpha:
                  type: number
                  default: 0.5
      responses:
        200:
          description: Search results

  /ws/chat/{conversation_id}:
    get:
      summary: WebSocket endpoint for real-time chat
      description: |
        WebSocket connection for streaming chat.

        Message Types:
        - Client -> Server: {"message": "user input"}
        - Server -> Client: {"type": "token", "content": "..."}
        - Server -> Client: {"type": "tool_call", "tool": "..."}
        - Server -> Client: {"type": "done"}
```

## Technology Stack

### Core Framework
- **FastAPI** - Modern, fast web framework for building APIs
- **LangChain** - LLM application framework
- **LangGraph** - Agent orchestration and state management

### Vector Database
- **Pinecone** - Managed vector database with hybrid search support
  - Dense vectors: 1024 dimensions (OpenAI text-embedding-3-large)
  - Sparse vectors: BM25-based keyword search
  - Metric: Dot product

### LLM Providers
- **OpenAI** - GPT-4o / GPT-4o-mini (primary)
- **Anthropic** - Claude 3.5 Sonnet (alternative)

### Supporting Infrastructure
- **Redis** - Conversation memory and caching
- **PostgreSQL** - Document metadata and user data
- **Celery** - Background document processing
- **MinIO/S3** - Document storage

### Python Dependencies

```txt
# Core
fastapi==0.115.0
uvicorn[standard]==0.32.0
websockets==13.0

# LangChain
langchain==0.3.0
langchain-core==0.3.0
langchain-openai==0.2.0
langchain-anthropic==0.2.0
langchain-pinecone==0.2.0
langchain-text-splitters==0.3.0
langchain-community==0.3.0

# Vector DB
pinecone-client==5.0.0

# Document Processing
pypdf==5.0.0
unstructured==0.15.0
python-magic==0.4.27

# Data Models
pydantic==2.9.0
sqlalchemy==2.0.35
asyncpg==0.29.0

# Utilities
python-dotenv==1.0.0
httpx==0.27.0
aioredis==2.0.1

# Monitoring
langsmith==0.1.0
structlog==24.4.0
```

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Kubernetes Cluster                        │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │  API Pods    │  │  Worker Pods │  │  WebSocket Pods      │   │
│  │  (FastAPI)   │  │  (Celery)    │  │  (Asyncio)           │   │
│  │  Replicas: 3 │  │  Replicas: 2 │  │  Replicas: 2         │   │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘   │
│         │                  │                      │              │
│         └──────────────────┼──────────────────────┘              │
│                            │                                     │
│  ┌─────────────────────────┴──────────────────────────┐         │
│  │              Services                               │         │
│  │  ┌────────────┐ ┌────────────┐ ┌──────────────┐   │         │
│  │  │ PostgreSQL │ │   Redis    │ │  Pinecone    │   │         │
│  │  │ (Stateful) │ │  (Cache)   │ │  (External)  │   │         │
│  │  └────────────┘ └────────────┘ └──────────────┘   │         │
│  └────────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

## Implementation Phases

### Phase 1: Core Infrastructure (Week 1)
- [ ] Set up FastAPI project structure
- [ ] Configure Pinecone hybrid index
- [ ] Implement document upload and processing
- [ ] Basic CRUD for documents

### Phase 2: RAG Agent (Week 2)
- [ ] Implement hybrid retriever
- [ ] Build LangChain agent with tools
- [ ] Integrate LLM providers
- [ ] Add conversation memory

### Phase 3: Streaming (Week 3)
- [ ] WebSocket implementation
- [ ] SSE fallback endpoint
- [ ] Frontend integration
- [ ] Error handling and reconnection

### Phase 4: Production (Week 4)
- [ ] Kubernetes deployment
- [ ] Monitoring and logging
- [ ] Performance optimization
- [ ] Security hardening

## Security Considerations

1. **API Security**
   - JWT authentication
   - Rate limiting per user
   - Input validation with Pydantic

2. **Data Privacy**
   - Document encryption at rest
   - Secure LLM API key management
   - PII detection and redaction

3. **Prompt Injection Protection**
   - Input sanitization
   - Context isolation
   - Defensive system prompts

## Next Steps

1. Set up development environment
2. Initialize FastAPI project
3. Configure Pinecone hybrid index
4. Implement document ingestion pipeline
5. Build and test the RAG agent
6. Add streaming capabilities
7. Deploy to staging
8. Performance testing and optimization

---

**Estimated Timeline**: 4 weeks for MVP
**Team Size**: 2-3 developers
