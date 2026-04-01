"""Показывает содержимое коллекции в Qdrant"""
from qdrant_client import QdrantClient

client = QdrantClient(host="qdrant", port=6333)
collection_name = "example_collection" # Укажите название коллекции

all_records = []
offset = None

while True:
    scroll_result = client.scroll(
        collection_name=collection_name,
        limit=100,
        offset=offset
    )
    records, offset = scroll_result
    all_records.extend(records)
    
    if offset is None:
        break

print("Список всех записей в коллекции:")
for record in all_records:
    print(f"- ID: {record.id}, Payload: {record.payload}")

print(f"Всего записей: {len(all_records)}")
