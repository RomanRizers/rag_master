# Paragraph Search Service

FastAPI + Qdrant сервис поиска параграфов по векторному сходству (E5) с React frontend.

## Master Plan

Подробная спецификация реализации полноценного Chat RAG:

- [docs/RAG_IMPLEMENTATION_PLAN.md](docs/RAG_IMPLEMENTATION_PLAN.md)

## Архитектура

- `frontend` — React SPA (Vite + TypeScript + React Query), отдается через Nginx
- `backend-app` — backend API (FastAPI)
- `qdrant` — векторная база

Frontend и backend разделены по контейнерам.

## Endpoints

### Backend API

- `POST /api/searching` — основной endpoint поиска
- `POST /api/indexing` — основной endpoint индексации
- `POST /api/documents/upload` — загрузить документ (multipart)
- `GET /api/documents` — список загруженных документов
- `POST /api/documents/{document_id}/index` — запустить job индексации
- `GET /api/jobs/{job_id}` — получить статус job индексации
- `POST /api/chat/sessions` — создать chat-сессию
- `POST /api/chat/sessions/{session_id}/messages` — отправить сообщение в сессию
- `POST /api/chat/sessions/{session_id}/messages/stream` — SSE-streaming ответа
- `GET /api/chat/sessions/{session_id}/messages` — получить историю сообщений

### Legacy compatibility

- `POST /searching` -> алиас к `/api/searching`
- `POST /indexing` -> алиас к `/api/indexing`

### Health

- `GET /` -> `{ "status": "ok", "service": "fastapi-backend" }`

## Локальный запуск backend (без Docker)

```bash
uv sync
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
```

Для локальной модели (OpenAI-compatible gateway):

```bash
LLM_PROVIDER=local
LOCAL_LLM_BASE_URL=http://localhost:11434/v1
LOCAL_LLM_MODEL=...
LOCAL_LLM_API_KEY=
```

## Storage backend

```bash
STORAGE_BACKEND=local
DOCUMENTS_STORAGE_PATH=/tmp/rag_documents
```

Сейчас реализован локальный файловый adapter (подготовка к S3/MinIO adapter на следующем этапе).

## Parser зависимости

- `python-multipart` уже включен и нужен для `multipart/form-data` upload.
- Для PDF-парсинга нужен `pypdf` (на текущем этапе опционально, будет включен в следующем шаге ingestion hardening).

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

## Тесты frontend

```bash
cd frontend
npm test
```
