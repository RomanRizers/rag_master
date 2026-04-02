# RAG Implementation Plan (Execution-Ready)

## 1. Цель и критерии успеха

### Цель v1
Собрать полноценный single-tenant Chat RAG:
- загрузка PDF/DOCX;
- парсинг и нормализация текста;
- чанкинг и индексация в Qdrant;
- чат с потоковой генерацией ответа (SSE) и цитатами источников;
- интеграция LLM через OpenAI-compatible протокол с переменными `OPENROUTER_*`.

### Критерии готовности v1
- Пользователь может загрузить документ, запустить индексацию и получить статус задачи.
- Индексируемый контент доступен в retrieval без ручных операций.
- Чат-ответы отдаются stream-ом с цитатами (документ/страница/чанк/фрагмент).
- Ошибки ingestion и chat возвращаются в стандартизованном формате.
- Интеграционные тесты (Go) и backend unit-тесты (Python) покрывают критический путь.

### SLO/метрики v1 (целевые)
- `p95 /api/chat/.../messages` < 8s до первого токена.
- `p95 retrieval` < 700ms.
- `ingestion job fail rate` < 2% (без учета битых файлов).
- `5xx rate` < 1%.

## 2. Архитектура (фиксированные решения)

### Компоненты
- `frontend` (React): upload, jobs, chat UI, citations.
- `backend-api` (FastAPI): API, orchestration, SSE-streaming.
- `worker` (Python): async ingestion pipeline.
- `postgres` (системные данные): документы, джобы, чаты.
- `qdrant` (векторный индекс): чанки и embeddings.
- `s3-compatible` (MinIO/S3): оригиналы файлов и артефакты парсинга.

### Сквозные потоки
1. **Ingestion**
   - upload -> record `documents` -> create `ingestion_job` -> worker parse/chunk/embed/upsert -> update job status.
2. **Chat**
   - user message -> query embedding -> retrieve topK -> rerank topN -> prompt assembly -> LLM stream -> citations.

### Single source of truth
- Метаданные и статусы: PostgreSQL.
- Бинарные файлы: S3-compatible storage.
- Retrieval контекст: Qdrant.

## 3. API контракты

## 3.1 Upload и indexing
- `POST /api/documents/upload` (multipart/form-data)
  - поля: `file`, `source_name` (optional), `tags[]` (optional).
  - `201`:
    - `document_id`
    - `file_name`
    - `mime_type`
    - `size_bytes`
    - `status` = `uploaded`
- `POST /api/documents/{document_id}/index`
  - `202`:
    - `job_id`
    - `status` = `queued`
- `GET /api/jobs/{job_id}`
  - `200`:
    - `job_id`
    - `status`: `queued|running|done|failed`
    - `progress`: `0..100`
    - `error_code` (nullable)
    - `error_message` (nullable)
    - `started_at`, `finished_at`

## 3.2 Chat
- `POST /api/chat/sessions`
  - `201`: `session_id`, `created_at`
- `POST /api/chat/sessions/{session_id}/messages`
  - request:
    - `message` (string)
    - `top_k` (optional)
    - `filters` (optional, doc tags/names)
  - response:
    - `text/event-stream` (SSE)
    - events:
      - `delta` (token chunk)
      - `citations` (final array)
      - `done`
      - `error`
- `GET /api/chat/sessions/{session_id}/messages`
  - `200`: список сообщений (user/assistant), включая citations у assistant.

## 3.3 Health/readiness
- `GET /health/live` -> процесс поднят.
- `GET /health/ready` -> backend может работать (Postgres/Qdrant/S3/LLM config checks).

## 3.4 Error shape (единый формат)
```json
{
  "error": {
    "code": "string_machine_code",
    "message": "human_message",
    "details": {}
  }
}
```

Ключевые коды:
- `invalid_file_type`
- `file_too_large`
- `parsing_failed`
- `chunking_failed`
- `embedding_failed`
- `storage_error`
- `retrieval_failed`
- `llm_unavailable`
- `internal_error`

## 4. Модель данных

## 4.1 PostgreSQL таблицы

### `documents`
- `id` (uuid, pk)
- `original_file_name` (text)
- `stored_object_key` (text, unique)
- `mime_type` (text)
- `size_bytes` (bigint)
- `status` (`uploaded|indexing|indexed|failed`)
- `meta` (jsonb)
- `created_at`, `updated_at`

### `ingestion_jobs`
- `id` (uuid, pk)
- `document_id` (uuid, fk -> documents.id)
- `status` (`queued|running|done|failed`)
- `progress` (int)
- `attempt` (int)
- `error_code` (text nullable)
- `error_message` (text nullable)
- `created_at`, `started_at`, `finished_at`

### `chunks_meta`
- `id` (uuid, pk)
- `document_id` (uuid, fk)
- `qdrant_point_id` (text, unique)
- `chunk_index` (int)
- `token_count` (int)
- `page` (int nullable)
- `section` (text nullable)
- `content_preview` (text)
- `created_at`

### `chat_sessions`
- `id` (uuid, pk)
- `title` (text nullable)
- `created_at`, `updated_at`

### `chat_messages`
- `id` (uuid, pk)
- `session_id` (uuid, fk)
- `role` (`user|assistant|system`)
- `content` (text)
- `citations` (jsonb nullable)
- `created_at`

## 4.2 Qdrant payload для чанка
- `document_id`
- `document_name`
- `chunk_id`
- `chunk_index`
- `page` (nullable)
- `section` (nullable)
- `text`
- `source_uri`

## 5. Ingestion pipeline (worker)

## 5.1 Очередь и воркер
- Индексация только async.
- Каждый job идемпотентен:
  - повторная индексация документа удаляет/деактивирует старые чанки документа в Qdrant.
- Retry policy:
  - max 3 попытки для временных ошибок (`storage_error`, сетевые, таймауты).
  - без retry для `invalid_file_type` и битых файлов.

## 5.2 Парсинг
- PDF parser:
  - page-aware extraction (сохранить mapping chunk -> page).
- DOCX parser:
  - извлекать заголовки, абзацы, таблицы как линейный текст с маркерами секций.
- Нормализация:
  - trim, collapse whitespace, удаление пустых блоков.

## 5.3 Чанкинг
- Token-aware:
  - `chunk_size_tokens = 600`
  - `chunk_overlap_tokens = 120`
- Гарантии:
  - чанк не пустой;
  - сохраняется `chunk_index`;
  - при page-aware тексте не теряется номер страницы.

## 5.4 Embeddings
- Используем существующий embedding сервис (E5) для v1.
- Ошибка любого чанка:
  - job -> `failed`
  - фиксируем `error_code=embedding_failed`.

## 6. Retrieval + генерация

## 6.1 Retrieval pipeline
1. embed query
2. dense search в Qdrant `top_k=40` (дефолт)
3. rerank cross-encoder до `top_n=8`
4. context builder (ограничение по токенам prompt)

## 6.2 Prompting policy
- system prompt с правилами:
  - отвечать только по контексту;
  - если контекста недостаточно, явно сообщать об этом;
  - цитировать источники.
- user message + recent history + retrieved context.

## 6.3 LLM abstraction
- Интерфейс `LLMProvider`:
  - `stream_chat(messages, settings) -> iterator[delta/events]`
- Выбор провайдера через `LLM_PROVIDER`:
  - `openrouter` (default)
  - `local`
- Реализация `OpenRouterProvider` (протокол OpenAI-compatible):
  - env:
    - `OPENROUTER_BASE_URL`
    - `OPENROUTER_API_KEY`
    - `OPENROUTER_MODEL`
- Реализация `LocalLLMProvider`:
  - поддержка локального OpenAI-compatible endpoint (например, Ollama/vLLM gateway);
  - env:
    - `LOCAL_LLM_BASE_URL`
    - `LOCAL_LLM_MODEL`
    - `LOCAL_LLM_API_KEY` (optional, если gateway требует ключ).
- Провайдер резолвится фабрикой по `LLM_PROVIDER`, без изменения бизнес-логики чата.

## 7. Frontend требования

- Раздел `Documents`:
  - upload,
  - список документов,
  - запуск индексации,
  - просмотр статуса job (progress/error).
- Раздел `Chat`:
  - список сессий,
  - streaming answer,
  - citations под ответом.
- Ошибки:
  - явные баннеры для `llm_unavailable`, `retrieval_failed`, `parsing_failed`.

## 8. Конфиг и env

Обязательные переменные:
- `QDRANT_URL`
- `COLLECTION_NAME`
- `DATABASE_URL`
- `S3_ENDPOINT`
- `S3_BUCKET`
- `S3_ACCESS_KEY`
- `S3_SECRET_KEY`
- `S3_REGION` (optional)
- `OPENROUTER_BASE_URL`
- `OPENROUTER_API_KEY`
- `OPENROUTER_MODEL`
- `LLM_PROVIDER` (`openrouter|local`)
- `LOCAL_LLM_BASE_URL` (required when `LLM_PROVIDER=local`)
- `LOCAL_LLM_MODEL` (required when `LLM_PROVIDER=local`)
- `LOCAL_LLM_API_KEY` (optional)
- `CHUNK_SIZE_TOKENS`
- `CHUNK_OVERLAP_TOKENS`

## 9. Тестовая стратегия

## 9.1 Python (unit)
- parser tests (pdf/docx);
- chunking boundary tests;
- provider tests (OpenRouter + Local provider + selector factory);
- error mapper tests.

## 9.2 Go (integration)
- upload/index/job lifecycle;
- chat streaming contract;
- citations schema validation;
- readiness endpoints.

## 9.3 Frontend
- API client tests (stream/failure/retry);
- components tests (jobs/chat/citations).

## 9.4 E2E сценарий
- upload PDF -> job done -> ask question -> response with non-empty citations.

## 10. Rollout план (этапы)

- `E1`: DB + S3 + базовые модели документов/джоб.
- `E2`: Upload API + storage adapter.
- `E3`: Worker + parsing + chunking.
- `E4`: Embedding + Qdrant upsert + job completion.
- `E5`: Chat sessions/messages API + retrieval pipeline + rerank.
- `E6`: LLM provider + streaming SSE + citations.
- `E7`: Frontend documents/chat UX.
- `E8`: Tests hardening + observability + readiness checks.

Каждый этап закрывается только после:
- code + tests + docs;
- green test run;
- commit hash записан в changelog этого файла.

## 10.1 Progress tracker (обновляется после каждого commit)

### Статусы этапов
- `E1`: DB + S3 + базовые модели документов/джоб — `in_progress`
- `E2`: Upload API + storage adapter — `done`
- `E3`: Worker + parsing + chunking — `done`
- `E4`: Embedding + Qdrant upsert + job completion — `in_progress`
- `E5`: Chat sessions/messages API + retrieval pipeline + rerank — `in_progress`
- `E6`: LLM provider + streaming SSE + citations — `done`
- `E7`: Frontend documents/chat UX — `todo`
- `E8`: Tests hardening + observability + readiness checks — `todo`

### Выполненные изменения (changelog)
| Status | Date | Task | Commit |
|---|---|---|---|
| done | 2026-04-02 | Master plan + hybrid provider strategy (`openrouter` + `local`) | `20d9468` |
| done | 2026-04-02 | README link на master-plan | `ca600f1` |
| done | 2026-04-02 | LLM config (`LLM_PROVIDER`, `OPENROUTER_*`, `LOCAL_LLM_*`) + `LLMError` | `11d060f` |
| done | 2026-04-02 | Абстракция провайдера LLM и фабрика `openrouter|local` | `9b5babd` |
| done | 2026-04-02 | Unit-тесты провайдера LLM | `4c61689` |
| done | 2026-04-02 | Базовый `ChatService` + chat-схемы API | `30a0684` |
| done | 2026-04-02 | Первые chat endpoints (`create/send/history`) | `a3a5d5a` |
| done | 2026-04-02 | README: chat endpoints + LLM env | `3eff399` |
| done | 2026-04-02 | Progress tracker и commit changelog в master-плане | `1f1e5ea` |
| done | 2026-04-02 | LLM config + `LLMError` для реализации (`openrouter|local`) | `11d060f` |
| done | 2026-04-02 | Реализация провайдера LLM и фабрики выбора | `9b5babd` |
| done | 2026-04-02 | Retrieval-контекст и citations в chat-ответах | `280a810` |
| done | 2026-04-02 | SSE streaming endpoint для chat (`/messages/stream`) + API-тест | `2101314` |
| done | 2026-04-02 | Реальный LLM streaming (`stream_chat`) и интеграция в chat endpoint | `446329e` |
| done | 2026-04-02 | Схемы API документов/джоб и ingestion ошибки | `c2355cf` |
| done | 2026-04-02 | Parser/chunker primitives (txt/docx/pdf optional) | `5ab6f24` |
| done | 2026-04-02 | In-memory сервисы документов и ingestion jobs | `d220c8c` |
| done | 2026-04-02 | Upload/list/index/job endpoints + multipart dependency | `063cdf6` |
| done | 2026-04-02 | API тесты ingestion endpoints | `818e98e` |
| done | 2026-04-02 | README + tracker update по ingestion этапам | `2f5ec68` |
| done | 2026-04-02 | Unit-тесты parser/chunker | `8e777f6` |
| done | 2026-04-02 | Go integration-тесты ingestion API | `e52fdbf` |
| done | 2026-04-02 | Local storage adapter и перевод ingestion на хранение файлов | `e95e95b` |
| done | 2026-04-02 | Unit-тесты локального storage adapter | `e262bc6` |
| done | 2026-04-02 | Подключение `pypdf` для PDF parsing | `e139c2a` |
| done | 2026-04-02 | Health endpoints `/health/live` и `/health/ready` | `c31ef27` |
| done | 2026-04-02 | Unit-тесты health endpoints | `e4f2601` |
| done | 2026-04-02 | S3 storage adapter (`boto3`) + factory switch `local|s3` | `f4a5f95` |
| done | 2026-04-02 | Тесты storage adapter для `s3` и storage factory | `0ca4885` |
| done | 2026-04-02 | MinIO сервис в compose и S3 env wiring | `2455d8f` |
| done | 2026-04-02 | metadata чанков в indexing pipeline и Qdrant payload | `64549c8` |
| done | 2026-04-02 | Тесты metadata validation/forwarding в indexing | `f88fc37` |
| done | 2026-04-02 | Retry policy и attempt tracking для ingestion jobs | `43eadc1` |
| done | 2026-04-02 | Unit-тесты retry-поведения ingestion jobs | `4f20889` |
| done | 2026-04-02 | Hybrid rerank + context budget в chat pipeline + unit-тесты | `e75edcf` |
| done | 2026-04-02 | README/example.env: env настройки rerank и context budget | `00b1c82` |
| done | 2026-04-02 | `GET /api/jobs` + filters (`status`, `document_id`) + API tests | `35a8025` |
| done | 2026-04-02 | README/docs: update endpoints + progress tracker | `bdbd58f` |
| done | 2026-04-02 | `GET /api/chat/sessions` endpoint + chat API test | `0e3cfb9` |
| done | 2026-04-03 | Pluggable chat store abstraction + SQLite backend | `4f7cc48` |
| done | 2026-04-03 | Unit-тесты SQLite chat store | `c2c0972` |
| done | 2026-04-03 | Pluggable ingestion job store abstraction + SQLite backend | `9ad86e0` |
| done | 2026-04-03 | Unit-тесты SQLite ingestion job store | `10d4405` |
| done | 2026-04-03 | Pluggable document store abstraction + SQLite backend | `a1526a6` |
| done | 2026-04-03 | Unit-тесты SQLite document store | `67d92d1` |
| done | 2026-04-03 | Lifecycle wiring: `app.state.services` + startup/shutdown close | `05cb5fe` |
| done | 2026-04-03 | Unit-тест lifecycle и инициализации `app.state.services` | `2ae33af` |
| done | 2026-04-03 | Миграция persistent store слоя: SQLite -> PostgreSQL (`chat/jobs/documents`) | `312e103` |
| done | 2026-04-03 | Unit-тесты store-слоя переведены на PostgreSQL backend | `219b541` |
| done | 2026-04-03 | Alembic + первая Postgres migration (`uuid/timestamptz/jsonb`) и удаление runtime schema creation | `fe35ab9` |
| done | 2026-04-03 | Docker startup: auto `alembic upgrade head` + README runbook по миграциям | `e28b260` |

### Правило ведения трекера
- После каждого нового коммита:
  - обновить статус этапа (`todo/in_progress/done`);
  - добавить строку в таблицу changelog;
  - при переходе этапа в `done` указать ключевые тесты, которыми он подтверждён.

## 11. Commit policy (обязательная)

### Базовое правило
**1 маленькое логическое изменение = 1 commit**.

### Формат сообщений
- `feat(rag): ...`
- `fix(rag): ...`
- `refactor(rag): ...`
- `test(rag): ...`
- `docs(rag): ...`

### Минимальные commit-единицы
- отдельный commit на:
  - API schema change;
  - service logic change;
  - data model/migration;
  - test addition/update;
  - docs update.

### Запреты
- не смешивать в одном commit:
  - бизнес-логику + массовый рефактор стиля;
  - API контракт + не связанные UI-правки;
  - тесты нескольких независимых подсистем.

## 12. Definition of Done (v1)

v1 считается завершенной, когда:
- upload/index/chat работает end-to-end;
- streaming/citations стабильны;
- backend и frontend тесты проходят;
- операции документированы в README и этом плане;
- есть runbook базовой эксплуатации (restart, retry jobs, health checks).
