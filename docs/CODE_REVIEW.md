# Code Review: RAG Master

Полное ревью кодовой базы по трём направлениям: качество RAG-пайплайна (точность и релевантность), производительность, надёжность продакшн-деплоя.

---

## 🔴 Критические проблемы качества RAG

### 1. Лексический поиск — полный скан коллекции (`O(n)`)
**Файл:** `backend/infrastructure/qdrant/client.py`, функция `_lexical_search()`

**Проблема:** При каждом запросе метод `iter_points()` обходит **все** точки в Qdrant, для каждой считает лексический скор в Python. При 10K+ чанков — деградация латентности в разы.

**Исправление:** Использовать нативный полнотекстовый индекс Qdrant (`payload index` с `FullTextIndexParams`), чтобы фильтрация шла на стороне базы, а не в Python-скрипте.

---

### 2. Эмбеддинги генерируются по одному, не батчами
**Файлы:** `backend/services/api_service.py`, `backend/infrastructure/ml/vectorizer.py`

**Проблема:** `vectorize_text()` принимает один текст. В `index_documents()` вызывается в цикле — по одному чанку за раз. Трансформерные модели дают 5–20× прирост при батч-инференсе.

**Исправление:** Добавить `vectorize_batch(texts: list[str]) -> list[np.ndarray]` в `TextVectorizer`; в `index_documents()` собирать все тексты → один батч-вызов.

```python
# Сейчас
for doc in documents:
    vector = self.vectorizer.vectorize_text(doc["content"])  # N вызовов

# Должно быть
contents = [doc["content"] for doc in documents]
vectors = self.vectorizer.vectorize_batch(contents)  # 1 вызов
```

---

### 3. Upsert в Qdrant — по одной точке за запрос
**Файл:** `backend/infrastructure/qdrant/client.py`, `index_document()`

**Проблема:** Каждый чанк — отдельный HTTP-запрос к Qdrant. Для документа с 200 чанками — 200 round-trip вместо 2–4.

**Исправление:** Добавить `upsert_batch(points, batch_size=100)` и вызывать из `api_service.index_documents()` после батч-векторизации.

---

### 4. Thread-unsafe инференс PyTorch-модели
**Файл:** `backend/infrastructure/ml/vectorizer.py`

**Проблема:** PyTorch-модель не является thread-safe. API-роуты используют `run_in_threadpool()` — несколько потоков могут вызывать `vectorize_text()` одновременно, что приводит к гонке состояний, некорректным эмбеддингам и крэшам.

**Исправление (быстрый):** Добавить `threading.Lock()` в `TextVectorizer.vectorize_text()`.
**Исправление (правильный):** Выделить инференс в отдельную очередь задач или `ProcessPoolExecutor`.

---

### 5. Чанкинг без учёта границ предложений
**Файл:** `backend/ingestion/chunker.py`

**Проблема:** Overlap вычисляется по сырым токенам — чанк может начинаться или заканчиваться посреди предложения. При ретривале теряется контекст на границах.

**Исправление:** После вычисления позиции `start = end - overlap` — сдвинуть вперёд до ближайшей границы предложения (`.`, `!`, `?`, `\n`).

---

### 6. Дубликат-детекция обрезает content до 96 символов
**Файл:** `backend/services/chat_service.py`, функция `_result_fingerprint()`

**Проблема:** Два почти одинаковых чанка, различающихся только в конце строки, не распознаются как дубликаты. В контекст LLM попадает повторяющаяся информация.

**Исправление:**
```python
# Сейчас
str(payload.get("content") or "")[:96]

# Должно быть
hashlib.sha256(payload.get("content", "").encode()).hexdigest()
```

---

### 7. Metadata score может превышать 1.0 до нормализации
**Файл:** `backend/services/chat_service.py`, функция `_metadata_score()`

**Проблема:** Несколько булевых условий суммируются до применения `min(score, 1.0)`. До кэпа score может достигать 1.35+. При взвешенном слиянии с другими компонентами (строго в [0,1]) результирующее ранжирование искажается.

**Исправление:** Использовать `score = max(score, new_value)` для каждого условия (накапливающий максимум), или нормализовать финальный вектор скоров перед слиянием.

---

### 8. PDF-парсинг не извлекает структуру документа
**Файл:** `backend/ingestion/parser.py`

**Проблема:** `pypdf` извлекает плоский текст без секций, заголовков и блоков. В технических документах теряется иерархия — поля `section` и `heading_path` остаются пустыми, что снижает точность metadata-скора при ретривале.

**Улучшение:** Переход на `pymupdf` (fitz) с `page.get_text("blocks")` для получения координат блоков и детекции заголовков по размеру шрифта.

---

## 🟡 Производительность

### 9. Извлечение ключевых слов повторяется для каждого чанка
**Файл:** `backend/services/ingestion_service.py`

**Проблема:** `extract_chunk_keywords()` повторно токенизирует и скорит весь текст чанка для каждого из 200 чанков документа.

**Исправление:** Вычислить ключевые слова на уровне документа один раз, затем для каждого чанка — только фильтрация ключевых слов, встречающихся в его тексте.

---

### 10. `list_indexed_document_ids()` — полный скролл коллекции
**Файл:** `backend/infrastructure/qdrant/client.py`

**Проблема:** Листинг документов и получение index stats требуют прохода по всем точкам коллекции. При 10K документов × 20 чанков = 200K точек — операция медленная и не масштабируется.

**Исправление:** Использовать Qdrant `group_by` API (доступен с v1.7) или вести отдельную таблицу `document_chunks` в PostgreSQL как источник статистики.

---

### 11. Одно соединение с PostgreSQL на каждый store
**Файлы:** `backend/infrastructure/document_store/postgres.py`, `chat_store/postgres.py`, `job_store/postgres.py`

**Проблема:** Каждый store создаёт один `psycopg.connect()` и защищает его `RLock`. Под нагрузкой (50+ параллельных запросов) запросы выстраиваются в очередь и начинают таймаутиться.

**Исправление:** `psycopg_pool.ConnectionPool` с настраиваемым min/max размером пула.

---

### 12. Модель может загружаться несколько раз
**Файл:** `backend/infrastructure/ml/vectorizer.py`

**Проблема:** Если `TextVectorizer()` создаётся при каждом вызове `get_api_service()` (через глобальный fallback), в память загружается ~400MB модели повторно.

**Исправление:** Синглтон-паттерн в `TextVectorizer` или создание единственного экземпляра в `AppServices.__init__()` с передачей через DI.

---

## 🟡 Надёжность и продакшн

### 13. RLock удерживается на всё время LLM-вызова (5–30 сек)
**Файл:** `backend/services/chat_service.py`, метод `send_message()`

**Проблема:** Блокировка захватывается перед вызовом `llm_provider.generate()` и освобождается после его завершения. Параллельные сообщения от других пользователей ждут полного завершения LLM-запроса.

**Исправление:**
```python
# Захватить лок → сохранить user message → отпустить
with self._lock:
    self.chat_store.append_message(session_id, user_message)

# LLM вызов — вне лока
assistant_text = self.llm_provider.generate(llm_messages)

# Захватить лок снова → сохранить ответ
with self._lock:
    self.chat_store.append_message(session_id, assistant_message)
```

---

### 14. Ошибки в SSE-стриме не передаются клиенту
**Файл:** `backend/api/routes.py`, генератор `event_stream()`

**Проблема:** Если LLM обрывает соединение или бросает исключение внутри генератора — клиент получает оборванный стрим без события `error`. UI зависает в состоянии "отвечает" бесконечно.

**Исправление:**
```python
async def event_stream():
    try:
        async for token in token_stream:
            yield _sse_event("delta", {"text": token})
    except Exception as e:
        yield _sse_event("error", {"code": "stream_error", "message": str(e)})
```

---

### 15. Стрим в frontend не обрабатывает ошибки сети
**Файл:** `frontend/src/api/client.ts`, функция `streamChatMessage()`

**Проблема:** Если `reader.read()` бросает исключение (обрыв сети, браузерный abort), оно не поймано → UI навсегда остаётся в состоянии "загрузка", `pendingUserMessage` не очищается.

**Исправление:** Обернуть `while`-loop в `try/catch`, вызывать `onError` callback при любом исключении.

---

### 16. S3: `NoSuchKey` неотличима от других ошибок
**Файл:** `backend/infrastructure/storage/s3.py`, метод `read()`

**Проблема:** Все исключения boto3 ловятся одинаково и возвращают один `StorageError`. Клиент получает 500 вместо 404 при обращении к несуществующему файлу.

**Исправление:**
```python
except ClientError as e:
    if e.response["Error"]["Code"] == "NoSuchKey":
        raise StorageError(message="File not found", status_code=404, ...)
    raise StorageError(message="S3 error", status_code=500, ...)
```

---

### 17. Path traversal через symlink в локальном хранилище
**Файл:** `backend/infrastructure/storage/local.py`, метод `_resolve_path()`

**Проблема:** `Path.resolve()` следует симлинкам. Симлинк внутри `root`, указывающий на путь выше по дереву, обходит проверку границ хранилища.

**Исправление:** Проверять `object_key` на `..` и абсолютные пути до вызова `resolve()`, или использовать `os.path.realpath()` с повторной проверкой после разрешения.

---

### 18. Глобальные геттеры сервисов — потенциальная гонка
**Файл:** `backend/api/routes.py`, функции `get_api_service()` и аналогичные

**Проблема:** `if api_service is None: api_service = ApiService()` — не атомарная операция. При множестве потоков на старте возможно создание двух копий сервиса с двойной загрузкой модели.

**Исправление:** Убрать глобальные переменные-fallback; использовать только `request.app.state.services` (уже корректно устанавливается в lifespan).

---

## 🟡 Качество поиска (алгоритмика)

### 19. Fusion score не даёт реального преимущества за пересечение результатов
**Файл:** `backend/infrastructure/qdrant/client.py`, функция `_fuse_ranked_results()`

**Проблема:** RRF с константой `k=60`: результат на позиции 1 в обоих списках даёт `1/61 + 1/61 ≈ 0.033`. Только в dense — `1/61`. Разница незначительная — пересечение dense+lexical почти не приоритизируется.

**Улучшение:** Уменьшить `k` (например, `k=10`) для большего преимущества у результатов, встречающихся в обоих списках, или перейти на взвешенное слияние по нормализованным скорам.

---

### 20. Query expansion добавляет шум в вектор запроса
**Файл:** `backend/services/query_normalization.py`

**Проблема:** Синонимы и расширения конкатенируются в строку и вместе с оригинальным запросом передаются на эмбеддинг — итоговый вектор "размывается" нерелевантными терминами.

**Улучшение:** Применять расширение только для лексического поиска (BM25-ветка), а для dense поиска передавать только оригинальный (нормализованный) запрос.

---

### 21. Payload-схема чанков не определена формально
**Файл:** `backend/infrastructure/qdrant/client.py`

**Проблема:** Поля payload (`document_id`, `chunk_id`, `token_count`, `page`, `heading_path`, etc.) добавляются через `payload.update(metadata)` без валидации. Фильтры по несуществующим полям падают молча, возвращая неожиданные результаты.

**Исправление:** Определить `class ChunkPayload(BaseModel)` и валидировать перед каждым upsert.

---

## 🟢 Тестовое покрытие — пробелы

| Что не покрыто | Где добавить |
|---|---|
| Обрыв SSE-стрима (backend) | `tests/test_chat_api.py` |
| Обрыв SSE-стрима (frontend) | `frontend/src/api/client.test.ts` |
| S3 `NoSuchKey` → HTTP 404 | `tests/test_storage_adapter.py` |
| Конкурентные операции с chat store | `tests/test_chat_store.py` |
| LLM provider stream failure | `tests/test_llm_provider.py` |
| Батч-векторизация корректность | `tests/test_vectorizer.py` (новый) |

---

## Приоритизация

| Приоритет | Задача | Файлы | Сложность |
|---|---|---|---|
| 🔴 1 | Батч-векторизация + батч-upsert | `vectorizer.py`, `api_service.py`, `qdrant/client.py` | Средняя |
| 🔴 2 | Thread-safe инференс модели | `vectorizer.py` | Низкая |
| 🔴 3 | Заменить full-scan лексический поиск Qdrant payload index | `qdrant/client.py` | Средняя |
| 🔴 4 | SSE stream error handling (backend + frontend) | `routes.py`, `client.ts` | Низкая |
| 🟡 5 | Connection pool для PostgreSQL | `*/postgres.py` | Низкая |
| 🟡 6 | Дубликат-детекция через SHA-256 | `chat_service.py` | Низкая |
| 🟡 7 | Освобождать LLM lock перед вызовом | `chat_service.py` | Низкая |
| 🟡 8 | Границы предложений в чанкере | `chunker.py` | Средняя |
| 🟡 9 | S3 404 distinction | `s3.py` | Низкая |
| 🟡 10 | Query expansion только для BM25 | `query_normalization.py` | Низкая |
| 🟡 11 | Metadata score нормализация | `chat_service.py` | Низкая |
| 🟢 12 | PDF структура через pymupdf | `parser.py` | Высокая |
| 🟢 13 | Формальная ChunkPayload схема | `qdrant/client.py` | Низкая |
