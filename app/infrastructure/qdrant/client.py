from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchAny
import qdrant_client
from app.core.config import Config
from app.core.exceptions import StorageError
import uuid
import structlog

logger = structlog.get_logger("qdrant")


class QdrantService:
    def __init__(self):
        """Инициализирует подключение к Qdrant и задает имя коллекции."""
        self.client = qdrant_client.QdrantClient(url=Config.QDRANT_URL)
        self.collection_name = Config.COLLECTION_NAME
        logger.info("qdrant_client_initialized", qdrant_url=Config.QDRANT_URL, collection_name=self.collection_name)

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
        logger.info("qdrant_search_started", top_k=top_k, keywords_count=len(keywords) if keywords else 0)

        try:
            if hasattr(self.client, "query_points"):
                response = self.client.query_points(
                    collection_name=self.collection_name,
                    query=query_vector,
                    query_filter=query_filter,
                    limit=top_k,
                )
                search_result = response.points
            else:
                search_result = self.client.search(
                    collection_name=self.collection_name,
                    query_vector=query_vector,
                    query_filter=query_filter,
                    limit=top_k,
                )
        except Exception as error:
            raise StorageError(message="Qdrant search failed", details={"reason": str(error)}) from error
        logger.info("qdrant_search_finished", results_count=len(search_result))

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
        logger.info(
            "qdrant_index_started",
            document_id=document_id,
            document_name=document_name,
            keywords_count=len(keywords) if keywords else 0,
            has_dataframe=dataframe is not None,
        )

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

        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
        except Exception as error:
            raise StorageError(message="Qdrant upsert failed", details={"reason": str(error)}) from error
        logger.info("qdrant_index_finished", document_id=document_id)
