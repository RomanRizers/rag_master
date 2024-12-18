# Сервис поиска параграфов

Этот проект реализует систему поиска параграфов с использованием векторных представлений текста, ключевых слов и тегов. Мы применяем модели для векторизации текста и алгоритмы для поиска ближайших соседей Qdrant.

## Стек технологий

- **Backend**: Python, Flask
- **Vector DB**: Qdrant
- **Frontend**: HTML, CSS, JavaScript
- **Model**: E5 (e5-base-en-ru)
- **Deploy**: Docker


## Установка и запуск


### 1. Клонирование репозитория

Сначала склоинируйте репозиторий на свое устройство:

```bash
git clone https://github.com/RomanRizers/gazprom_case
cd gazprom_case
```


### 2. Запуск с помощью Docker Compose

Для развертывания проекта с использованием docker-compose выполните следующую команду:

```bash
docker-compose up --build
```

Дождитесь загрузки контейнеров, в терминале это должно выглядеть примерно так:

![Запуск контейнеров](https://drive.google.com/uc?id=1JS7yxtlyXYSZMTorV818dfNoODXu4AJL)


### 3. Переход к клиентской части

После завершения сборки проект будет доступен по ссылке `http://localhost:5000`



### 4. Если хотите заново векторизовать данные и поместить в Qdrant (при запуске контейнеров,  готовая коллекция подтягивается автоматически):
  - Создайте виртуальное окружение и активируйте его:
    ```bash
    python -m venv venv
    source venv/Scripts/activate
    ```
  - Установите зависимости:
    ```bash
    pip install -r requirements.txt
    ```
  - Запустите `dataset_loader.py` (находится в app/embeddings) - векторизует код (ядра CUDA поддерживаются)
  - Запустите `qdrant_uploader.py` (находится в app/embeddings) - создает новую коллекцию и добавляет датасет с векторизованным полем content
    

## Документация API

### 1. Эндпоинт поиска

- **URL**: `http://127.0.0.1:5000/searching`
- **Метод**: `POST`
- **Описание**: Этот эндпоинт выполняет поиск параграфов, используя векторные представления текста и ключевые слова.
- **Параметры запроса**:
  - `query` (string): Текстовый запрос для поиска.
  - `top_k` (integer, optional): Количество наиболее релевантных параграфов, которые должны быть возвращены. По умолчанию 5.
  - `keywords` (array of strings, optional): Массив ключевых слов для фильтрации поиска. Если не переданы, будет произведен поиск по всему тексту.

#### Пример запроса:

```json
{
  "query": "In the novel 'Crime and Punishment', who is the benefactor behind Dunya's watches, and why was Razumikhin particularly pleased to learn this?",
  "top_k": 5,
  "keywords": ["Zosimov left", "cute watches"]
}
```

#### Пример ответа:
```json
{
    "results": [
        {
            "id": "df9bdae9-7efb-5c7c-bb97-0bff6dbf057b",
            "payload": {
                "chunk_id": "df9bdae9-7efb-5c7c-bb97-0bff6dbf057b",
                "content": "You don't need to go at all, stay! Zosimov left, so you should. Don't go... What's the time? Is it twelve already? What cute watches you have, Dunya! Why are you quiet again? Only I keep talking!.. \n - It's a gift from Marfa Petrovna, - answered Dunya. \n - And they're quite expensive, - added Pulcheria Alexandrovna. \n - Oh! They're big, almost not ladylike. \n - I like such, - said Dunya. \n 'So, it’s not from her fiancé', - Razumikhin thought to himself and was pleased for some unknown reason. \n - I thought it was Luzhin's gift, - Raskolnikov remarked. \n - No, he hasn't given anything to Dunechka yet.",
                "keywords": [
                    "zosimov left",
                    "cute watches",
                    "marfa petrovna",
                    "quite expensive",
                    "not ladylike",
                    "fiancé",
                    "luzhin's gift"
                ]
            },
            "score": 0.8665101
        }
    ],
    "total": 1
}
```


### 2. Эндпоинт индексации

- **URL**: `http://127.0.0.1:5000/indexing`
- **Метод**: `POST`
- **Описание**: Этот эндпоинт выполняет индексацию документов в Qdrant. Каждый документ должен содержать текст, ключевые слова и данные о категории (dataframe).
- **Параметры запроса**:
  - `document_name` (string): Название набора данных или коллекции документов (например, название документа).
  - `documents` (array of objects): Массив объектов, каждый из которых содержит:
    - `content` (string): Текстовый контент документа.
    - `dataframe` (string): Категория или метаданные, связанные с документом.
    - `keywords` (array of strings): Массив ключевых слов, связанных с документом.

#### Пример запроса:

```json
{
  "document_name": "Document 1",
  "documents": [
    {
      "content": "CRM позволяет автоматизировать процесс регистрации пользователей на платформе.",
      "dataframe": "Технологии",
      "keywords": ["CRM", "Регистрация"]
    },
    {
      "content": "Использование API ускоряет интеграцию внешних сервисов в основную систему.",
      "dataframe": "Интеграция",
      "keywords": ["API", "Интеграция"]
    },
    {
      "content": "Нефтяная промышленность активно внедряет цифровизацию для повышения эффективности.",
      "dataframe": "Промышленность",
      "keywords": ["Цифровизация", "Нефть"]
    }
  ]
}
```


#### Пример ответа:

```json
{
  "status": "success",
  "message": "3 documents indexed."
}
```


## Тестирование API

Тестирование API проводилось в Postman.

- Перейдите на вкладку Headers
- Убедитесь, что там есть следующая пара:
```bash
Key: Content-Type
Value: application/json
```
- Если заголовок отсутствует, добавьте его вручную

![indexing](https://drive.google.com/uc?id=1lHl6KSJLUh4TZAyKsNr5_l2IZJc5tMcT)

![searching](https://drive.google.com/uc?id=1CjGrglX9dEmMqDZ7QPAVCC2u34gzZSOE)


## Скриншоты клиентской части

![front_rus](https://drive.google.com/uc?id=17KWwvlmy9JMcxsifSAXzJKqggmqyoAxh)


![front_en](https://drive.google.com/uc?id=1Vi_450zsfS5CpnmizpA5n5b2gF3gGv5-)



## Датасет до и после векторизации

до:
![до](https://drive.google.com/uc?id=1CtM5O2wYpt4uyP6X1rwpDApL9c36tInF)
после:
![после](https://drive.google.com/uc?id=1UWuVDT6mjXiianEucE75DKNxF_YBk4HK)

