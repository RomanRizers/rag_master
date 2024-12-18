from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchAny
import qdrant_client
from app.config import Config
import uuid


class QdrantService:
    def __init__(self):
        """Инициализирует подключение к Qdrant и задает имя коллекции."""
        self.client = qdrant_client.QdrantClient(url=Config.QDRANT_URL)
        self.collection_name = Config.COLLECTION_NAME

    def search(self, query_vector, top_k, keywords=None):
        """Выполняет поиск в коллекции с использованием вектора запроса и фильтрации."""
        query_filter = None
        if keywords:
            if isinstance(keywords, str):
                keywords = [keywords.lower()]
            else:
                keywords = [kw.lower() for kw in keywords]

            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="keywords",
                        match=MatchAny(any=keywords)
                    )
                ]
            )

        search_result = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=query_filter,
            limit=top_k,
        )

        return [
            {
                "id": hit.id,
                "payload": hit.payload,
                "score": hit.score
            }
            for hit in search_result
        ]

    def index_document(self, document_name, content_vector, content, keywords, dataframe=None):
        """Индексирует документ в коллекции Qdrant."""
        document_id = str(uuid.uuid4())

        if keywords:
            keywords = [kw.lower() for kw in keywords]

        point = PointStruct(
            id=document_id,
            vector=content_vector.tolist(),
            payload={
                "document_name": document_name,
                "content": content,
                "keywords": keywords,
                "dataframe": dataframe
            }
        )

        self.client.upsert(
            collection_name=self.collection_name,
            points=[point]
        )

