# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RAG Master is a production-ready Retrieval-Augmented Generation system. It allows users to upload documents, index them into a vector database, and then query them via chat or search.

## Commands

### Full Stack (Docker)
```bash
docker compose up --build -d        # Start all services
docker compose down                  # Stop all services
```

Services: Frontend (`:3000`), Backend API (`:5001`), Qdrant (`:6334`), MinIO (`:9000`/`:9001`), Postgres (`:5432`)

### Backend (Python)
```bash
uv sync                                          # Install dependencies
uv run alembic upgrade head                      # Apply DB migrations
uv run uvicorn backend.main:app --host 0.0.0.0 --port 5000  # Run API
```

**Tests:**
```bash
uv run python -m unittest discover -s tests -v   # All Python tests
uv run python -m unittest tests.test_rag_e2e_flow -v  # E2E (no external deps)
go test ./tests -v                               # Go API integration tests
RAG_API_BASE_URL=http://localhost:5001 go test ./tests -v  # Against running instance
```

### Frontend (Node/TypeScript)
```bash
cd frontend
npm install
npm run dev     # Dev server on :5173 (proxies /api to :5001)
npm test        # Vitest
npm run build   # Production build
```

## Architecture

### Services

| Component | Technology | Role |
|-----------|-----------|------|
| Backend API | FastAPI (Python) | REST + SSE endpoints |
| Worker | Python daemon | Background ingestion job processor |
| Vector DB | Qdrant | Stores chunk embeddings (E5 model: `d0rj/e5-base-en-ru`) |
| Relational DB | PostgreSQL + Alembic | Documents, jobs, chat sessions |
| Object Storage | MinIO (S3-compatible) | Raw document files |
| Frontend | React 18 + Vite + TypeScript | SPA |

### Dependency Injection

All backend services are wired in `backend/core/services.py` via the `AppServices` dataclass. This is the single source of truth for dependency management — services are created once at startup and injected into route handlers via FastAPI's `Depends()` mechanism. The lifespan handler in `backend/main.py` manages startup/shutdown.

### Document Ingestion Pipeline

1. File uploaded → validated (type/signature/size) → stored in MinIO → job queued
2. Worker polls for pending jobs (default: 1s interval) → claims job → runs:
   - Parse (PDF/DOCX/TXT) → chunk with overlap → extract keywords → embed (E5) → upsert to Qdrant
3. Frontend polls `GET /api/documents/{id}/index-stats` for progress

### Chat/Search Pipeline

1. User query → dense (vector) + sparse (BM25) retrieval from Qdrant
2. Reranking: scores fused from semantic, lexical, keyword, and metadata weights (configurable)
3. Top-N chunks → LLM context → response streamed via SSE
4. SSE stream has two event types: `delta` (token chunks) and `citations` (final batch)

### Knowledge Bases

Documents are grouped by `knowledge_base` field. Each KB can have independent indexing profiles and retrieval strategies. Use `POST /api/knowledge-bases/{name}/reindex` to requeue all docs in a KB.

### Storage Backends (configurable via env)

- `STORAGE_BACKEND`: `local` or `s3`
- `DOCUMENT_STORE_BACKEND`, `CHAT_STORE_BACKEND`, `JOB_STORE_BACKEND`: `memory` or `postgres`
- `LLM_PROVIDER`: `openrouter` or `local` (OpenAI-compatible, e.g., Ollama)

### API Error Format

All errors return a standardized shape:
```json
{"error": {"code": "invalid_file_type", "message": "...", "details": {}}}
```

Admin endpoints require `X-Admin-API-Key` header.

### Frontend

- **API client**: `frontend/src/api/client.ts` — typed fetch wrapper with `ApiRequestError`, SSE streaming, and FormData upload support
- **State**: TanStack React Query for server state
- **Routing**: React Router v6
- **i18n**: Russian/English toggle stored in `localStorage`
- **Theme**: Light/Dark/System stored in `localStorage`

## Key Configuration Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `CHUNK_SIZE_TOKENS` | 600 | Tokens per chunk |
| `CHUNK_OVERLAP_TOKENS` | 120 | Overlap between chunks |
| `DENSE_RETRIEVE_TOP_N` | 40 | Candidates from vector search |
| `RERANK_TOP_N` | 8 | Final results after reranking |
| `RERANK_SEMANTIC_WEIGHT` | — | Weight for vector similarity score |
| `RERANK_LEXICAL_WEIGHT` | — | Weight for BM25 score |
| `OPENROUTER_API_KEY` | — | Required for OpenRouter LLM |
| `OPENROUTER_MODEL` | — | Model ID for OpenRouter |
| `HEALTHCHECK_LLM_ACTIVE_PROBE` | 0 | Set to `1` to probe LLM in health checks |

## Testing Strategy

- **Python unit tests** (`tests/`): cover services, storage adapters, parsers, rate limiter, stores
- **`test_rag_e2e_flow.py`**: service-level E2E with no external dependencies (fastest full-pipeline test)
- **Go integration tests** (`tests/*.go`): hit real HTTP API; require a running backend
- **Frontend tests** (`frontend/src/**/*.test.tsx`): Vitest component tests for `ChatPage`, `DocumentsPage`, API client
