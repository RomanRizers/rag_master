# Paragraph Search Service

FastAPI + Qdrant сервис поиска параграфов по векторному сходству (E5) с React frontend.

## Master Plan

Подробная спецификация реализации полноценного Chat RAG:

- [docs/RAG_IMPLEMENTATION_PLAN.md](docs/RAG_IMPLEMENTATION_PLAN.md)

## Архитектура

- `frontend` — React SPA (Vite + TypeScript + React Query), отдается через Nginx
- `backend-app` — backend API (FastAPI)
- `worker` — фоновая обработка ingestion jobs (очередь в Postgres)
- `postgres` — персистентное хранилище metadata/чатов/джоб
- `qdrant` — векторная база

Frontend и backend разделены по контейнерам.

## Endpoints

### Backend API

- `POST /api/searching` — основной endpoint поиска
- `POST /api/indexing` — основной endpoint индексации
- `POST /api/documents/upload` — загрузить документ (multipart, поддержка: `txt/docx/pdf`, проверка сигнатуры контента + сверка с extension/MIME)
- `GET /api/documents` — список загруженных документов
- `POST /api/documents/{document_id}/index` — запустить job индексации
- `GET /api/documents/{document_id}/index-stats` — статус документа + количество чанков в индексе + последняя job
- `POST /api/admin/index/orphans/cleanup` — cleanup orphan chunk-групп в индексе (`{"dry_run": true|false}`), требует header `X-Admin-API-Key`
- `GET /api/jobs` — список job индексации (filters: `status`, `document_id`)
- `GET /api/jobs/{job_id}` — получить статус job индексации
- `POST /api/chat/sessions` — создать chat-сессию
- `GET /api/chat/sessions` — список chat-сессий
- `POST /api/chat/sessions/{session_id}/messages` — отправить сообщение в сессию
- `POST /api/chat/sessions/{session_id}/messages/stream` — SSE-streaming ответа
- `GET /api/chat/sessions/{session_id}/messages` — получить историю сообщений

### Legacy compatibility

- `POST /searching` -> алиас к `/api/searching`
- `POST /indexing` -> алиас к `/api/indexing`

### Health

- `GET /` -> `{ "status": "ok", "service": "fastapi-backend" }`
- `GET /health/live` -> live check
- `GET /health/ready` -> readiness check (`qdrant` + `storage`)

## Локальный запуск backend (без Docker)

```bash
uv sync
uv run alembic upgrade head
uv run uvicorn backend.main:app --host 0.0.0.0 --port 5000
```

## Запуск всего решения через Docker Compose

```bash
docker compose up --build -d
```

После запуска:

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:5001`
- Qdrant HTTP: `http://localhost:6334`
- MinIO API: `http://localhost:9000`
- MinIO Console: `http://localhost:9001`
- Postgres: `localhost:5432`

## Hugging Face token (рекомендуется)

Чтобы убрать warning про unauthenticated HF requests и ускорить загрузку модели:

```bash
export HF_TOKEN=hf_xxx
docker compose up -d --build
```

Токен читается из `.env` и прокидывается в `backend-app`.

## LLM provider (OpenRouter/local)

```bash
LLM_PROVIDER=openrouter
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_API_KEY=...
OPENROUTER_MODEL=...
CHUNK_SIZE_TOKENS=600
CHUNK_OVERLAP_TOKENS=120
RERANK_TOP_N=8
RERANK_SEMANTIC_WEIGHT=0.7
CHAT_MAX_CONTEXT_CHARS=6000
CHAT_STORE_BACKEND=memory
JOB_STORE_BACKEND=memory
POSTGRES_DSN=postgresql://rag:rag@postgres:5432/rag
ADMIN_API_KEY=change-me
```

`CHAT_STORE_BACKEND`:
- `memory` — in-memory store (default)
- `postgres` — persistent store in PostgreSQL (`POSTGRES_DSN`)

`JOB_STORE_BACKEND`:
- `memory` — in-memory store (default)
- `postgres` — persistent store in PostgreSQL (`POSTGRES_DSN`)

Для локальной модели (OpenAI-compatible gateway):

```bash
LLM_PROVIDER=local
LOCAL_LLM_BASE_URL=http://localhost:11434/v1
LOCAL_LLM_MODEL=...
LOCAL_LLM_API_KEY=
```

Для административного cleanup endpoint:

- передавайте `X-Admin-API-Key: <ADMIN_API_KEY>`;
- при неверном или отсутствующем ключе backend вернет `401` с кодом `unauthorized`.

## Storage backend

```bash
STORAGE_BACKEND=local
DOCUMENTS_STORAGE_PATH=/tmp/rag_documents
DOCUMENT_STORE_BACKEND=memory
POSTGRES_DSN=postgresql://rag:rag@postgres:5432/rag
```

Для S3/MinIO:

```bash
STORAGE_BACKEND=s3
S3_ENDPOINT=http://minio:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET=rag-documents
S3_REGION=us-east-1
S3_AUTO_CREATE_BUCKET=1
```

Поддерживаются оба варианта: `local` и `s3`.

`DOCUMENT_STORE_BACKEND`:
- `memory` — in-memory metadata store (default)
- `postgres` — persistent metadata store in PostgreSQL (`POSTGRES_DSN`)

```bash
INGESTION_WORKER_POLL_SECONDS=1.0
INGESTION_RETRY_BACKOFF_SECONDS=0.5
```

## Parser зависимости

- `python-multipart` уже включен и нужен для `multipart/form-data` upload.
- `pypdf` уже включен для PDF-парсинга.

## Перевекторизация данных

```bash
cd backend/embeddings
uv run dataset_loader.py
uv run qdrant_uploader.py
```

## Тесты backend (Go)

```bash
go test ./tests -v
```

По умолчанию Go-тесты обращаются к `http://localhost:5001`.
Если backend поднят на другом адресе, укажи:

```bash
RAG_API_BASE_URL=http://localhost:5001 go test ./tests -v
```

Медленный сквозной E2E-кейс (индексация + поиск) выключен по умолчанию:

```bash
RAG_RUN_SLOW_E2E=1 go test ./tests -v -run TestOptionalIndexAndSearchFlow
```

## Тесты backend (Python, optional)

```bash
uv run python -m unittest discover -s tests
```

## Миграции Postgres

```bash
uv run alembic upgrade head
```

Откат на один шаг:

```bash
uv run alembic downgrade -1
```

## Тесты frontend

```bash
cd frontend
npm test
```
