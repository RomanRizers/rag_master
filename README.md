# Paragraph Search Service

FastAPI + Qdrant сервис поиска параграфов по векторному сходству (E5) с React frontend.

## Архитектура

- `frontend` — React SPA (Vite + TypeScript + React Query), отдается через Nginx
- `backend-app` — backend API (FastAPI)
- `qdrant` — векторная база

Frontend и backend разделены по контейнерам.

## Endpoints

### Backend API

- `POST /api/searching` — основной endpoint поиска
- `POST /api/indexing` — основной endpoint индексации

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

## Перевекторизация данных

```bash
cd backend/embeddings
uv run dataset_loader.py
uv run qdrant_uploader.py
```

## Тесты backend

```bash
uv run python -m unittest discover -s tests
```
