"""Удаляет коллекцию в Qdrant"""
from qdrant_client import QdrantClient


client = QdrantClient(host="qdrant", port=6333)
collection_name = "example" # Укажите название коллекции

try:
    client.delete_collection(collection_name=collection_name)
    print(f"Коллекция '{collection_name}' успешно удалена.")
except Exception as e:
    print(f"Ошибка при удалении коллекции: {e}")
