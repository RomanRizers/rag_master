# RAG Operations Runbook

## 1) Быстрый старт и базовые команды

Поднять сервисы:

```bash
docker compose up --build -d
```

Проверить состояние контейнеров:

```bash
docker compose ps
```

Остановить:

```bash
docker compose down
```

Перезапустить backend/worker:

```bash
docker compose restart backend-app worker
```

## 2) Health checks и triage

Проверка liveness:

```bash
curl -sS http://localhost:5001/health/live
```

Проверка readiness:

```bash
curl -sS http://localhost:5001/health/ready | jq
```

Интерпретация `checks`:
- `qdrant=false`: недоступен Qdrant или коллекция не читается.
- `storage=false`: проблемы с `local` storage или S3/MinIO.
- `llm=false`: некорректный конфиг провайдера LLM или недоступен endpoint при active probe.

Если `status=degraded`:
1. Проверить логи backend/worker/qdrant.
2. Проверить env (`OPENROUTER_*`, `LOCAL_LLM_*`, `STORAGE_BACKEND`, `QDRANT_URL`).
3. Исправить конфиг и перезапустить backend/worker.

## 3) Логи и диагностика

Backend:

```bash
docker compose logs -f backend-app
```

Worker:

```bash
docker compose logs -f worker
```

Qdrant:

```bash
docker compose logs -f qdrant
```

MinIO (если `STORAGE_BACKEND=s3`):

```bash
docker compose logs -f minio
```

## 4) Retry индексации документа

Переиндексация выполняется повторным запуском index job для документа:

```bash
curl -sS -X POST "http://localhost:5001/api/documents/<document_id>/index"
```

Проверка статуса job:

```bash
curl -sS "http://localhost:5001/api/jobs/<job_id>" | jq
```

Список последних job:

```bash
curl -sS "http://localhost:5001/api/jobs" | jq
```

## 5) Orphan cleanup в индексе

Dry-run:

```bash
curl -sS -X POST "http://localhost:5001/api/admin/index/orphans/cleanup" \
  -H "Content-Type: application/json" \
  -H "X-Admin-API-Key: ${ADMIN_API_KEY}" \
  -d '{"dry_run": true}' | jq
```

Удаление orphan-данных:

```bash
curl -sS -X POST "http://localhost:5001/api/admin/index/orphans/cleanup" \
  -H "Content-Type: application/json" \
  -H "X-Admin-API-Key: ${ADMIN_API_KEY}" \
  -d '{"dry_run": false}' | jq
```

## 6) Частые инциденты

### Порт 5000/5001 занят
Найти процесс:

```bash
lsof -nP -iTCP:5000 -sTCP:LISTEN
lsof -nP -iTCP:5001 -sTCP:LISTEN
```

Освободить порт (аккуратно):

```bash
kill <PID>
```

### `/health/ready` -> `llm=false`
Проверить:
- `LLM_PROVIDER=openrouter|local`
- для `openrouter`: `OPENROUTER_BASE_URL`, `OPENROUTER_MODEL`, `OPENROUTER_API_KEY`
- для `local`: `LOCAL_LLM_BASE_URL`, `LOCAL_LLM_MODEL`
- если включён `HEALTHCHECK_LLM_ACTIVE_PROBE=1`, проверить доступность `GET {BASE_URL}/models`

### `storage_error` на `/searching` или `/indexing`
Проверить:
- доступность Qdrant (`QDRANT_URL`)
- наличие коллекции (`COLLECTION_NAME`)
- логи `qdrant` и `backend-app`

## 7) Smoke tests после восстановления

```bash
curl -sS http://localhost:5001/
curl -sS http://localhost:5001/health/live
curl -sS http://localhost:5001/health/ready | jq
go test ./tests -v
```
