"""Показывает список коллекций в Qdrant"""
from qdrant_client import QdrantClient


client = QdrantClient(host="qdrant", port=6333)

try:
    response = client.get_collections()
    collections = response.collections if hasattr(response, 'collections') else []

    print("Список коллекций в Qdrant:")
    for collection in collections:
        print(f"- {collection}")
except Exception as e:
    print(f"Ошибка при получении списка коллекций: {e}")