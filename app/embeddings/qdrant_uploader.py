import json
import pandas as pd
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, PointStruct
import math
from tqdm import tqdm

with open('vector_e5-base-en-ru.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

df = pd.DataFrame(data)

vector_dim = len(df["content_vector"][0])
print(f"Размерность первого вектора: {vector_dim}")
if df['content_vector'].apply(lambda x: len(x) != vector_dim).any():
    raise ValueError("Некоторые векторы имеют неправильную размерность!")
else:
    print(f"Все вектора имеют правильную размерность ({vector_dim}).")

points = []
for _, row in df.iterrows():
    point = PointStruct(
        id=row["chunk_id"],
        vector=row["content_vector"],
        payload={ 
            "chunk_id": row["chunk_id"],
            "content": row["content"],
            "keywords": row["keywords"]
        }
    )
    points.append(point)

def split_into_batches(points, batch_size):
    """Разделяет список точек на батчи указанного размера."""
    for i in range(0, len(points), batch_size):
        yield points[i:i + batch_size]

client = QdrantClient(host="localhost", port=6334)
collection_name = "gazprom_dataset_e5"

try:
    client.delete_collection(collection_name)
    print(f"Коллекция '{collection_name}' удалена.")
except Exception as e:
    print(f"Ошибка при удалении коллекции (возможно, она не существует): {e}")

try:
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=vector_dim, distance="Cosine")
    )
    print(f"Коллекция '{collection_name}' успешно создана.")
except Exception as e:
    print(f"Ошибка при создании коллекции: {e}")
    raise e

batch_size = 500
for batch in tqdm(split_into_batches(points, batch_size), desc="Uploading batches", total=math.ceil(len(points) / batch_size)):
    try:
        client.upsert(collection_name=collection_name, points=batch)
    except Exception as e:
        print(f"Ошибка при добавлении батча: {e}")

print(f"Все векторы успешно добавлены в коллекцию '{collection_name}'!")

query_vector = points[0].vector
results = client.search(collection_name=collection_name, query_vector=query_vector, limit=1)

print("Результаты поиска для первого вектора:")
print(results)
