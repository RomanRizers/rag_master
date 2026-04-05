from qdrant_client.models import Distance, FieldCondition, Filter, MatchAny, MatchValue, PointStruct, VectorParams
import qdrant_client
from backend.core.config import Config
from backend.core.exceptions import StorageError
import uuid
import structlog

logger = structlog.get_logger("qdrant")


class QdrantService:
    def __init__(self):
        """Инициализирует подключение к Qdrant и задает имя коллекции."""
        self.client = qdrant_client.QdrantClient(url=Config.QDRANT_URL)
        self.collection_name = Config.COLLECTION_NAME
        logger.info("qdrant_client_initialized", qdrant_url=Config.QDRANT_URL, collection_name=self.collection_name)

    def search(self, query_vector, top_k, keywords=None, filters=None):
        """Выполняет поиск в коллекции с использованием вектора запроса и фильтрации."""
        must_conditions = []
        if keywords:
            if isinstance(keywords, str):
                keywords = [keywords.lower()]
            else:
                keywords = [kw.lower() for kw in keywords]
            must_conditions.append(
                FieldCondition(
                    key="keywords",
                    match=MatchAny(any=keywords)
                )
            )
        knowledge_bases = filters.get("knowledge_bases") if isinstance(filters, dict) else None
        if knowledge_bases:
            must_conditions.append(
                FieldCondition(
                    key="knowledge_base",
                    match=MatchAny(any=[str(item).strip() for item in knowledge_bases if str(item).strip()])
                )
            )
        query_filter = Filter(must=must_conditions) if must_conditions else None
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

    def index_document(self, document_name, content_vector, content, keywords, dataframe=None, metadata=None):
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

        payload = {
            "document_name": document_name,
            "content": content,
            "keywords": keywords,
            "dataframe": dataframe
        }
        if isinstance(metadata, dict):
            payload.update(metadata)

        point = PointStruct(
            id=document_id,
            vector=content_vector.tolist(),
            payload=payload
        )

        try:
            self._ensure_collection(vector_size=len(content_vector))
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
        except Exception as error:
            raise StorageError(message="Qdrant upsert failed", details={"reason": str(error)}) from error
        logger.info("qdrant_index_finished", document_id=document_id)

    def delete_document_chunks(self, document_id: str):
        logger.info("qdrant_delete_document_chunks_started", document_id=document_id)
        if not self._collection_exists():
            logger.info("qdrant_delete_document_chunks_skipped_missing_collection", document_id=document_id)
            return
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="document_id",
                            match=MatchValue(value=document_id),
                        )
                    ]
                ),
                wait=True,
            )
        except Exception as error:
            raise StorageError(message="Qdrant delete failed", details={"reason": str(error)}) from error
        logger.info("qdrant_delete_document_chunks_finished", document_id=document_id)

    def count_document_chunks(self, document_id: str) -> int:
        logger.info("qdrant_count_document_chunks_started", document_id=document_id)
        if not self._collection_exists():
            logger.info("qdrant_count_document_chunks_missing_collection", document_id=document_id, chunks_count=0)
            return 0
        try:
            response = self.client.count(
                collection_name=self.collection_name,
                count_filter=Filter(
                    must=[
                        FieldCondition(
                            key="document_id",
                            match=MatchValue(value=document_id),
                        )
                    ]
                ),
                exact=True,
            )
        except Exception as error:
            raise StorageError(message="Qdrant count failed", details={"reason": str(error)}) from error
        count = int(getattr(response, "count", 0))
        logger.info("qdrant_count_document_chunks_finished", document_id=document_id, chunks_count=count)
        return count

    def list_indexed_document_ids(self, batch_size: int = 256) -> list[str]:
        logger.info("qdrant_list_indexed_document_ids_started", batch_size=batch_size)
        if batch_size < 1:
            batch_size = 1
        if not self._collection_exists():
            logger.info("qdrant_list_indexed_document_ids_missing_collection", documents_count=0)
            return []

        ids: set[str] = set()
        offset = None
        try:
            while True:
                points, next_offset = self.client.scroll(
                    collection_name=self.collection_name,
                    limit=batch_size,
                    offset=offset,
                    with_payload=["document_id"],
                    with_vectors=False,
                )
                for point in points:
                    payload = getattr(point, "payload", None) or {}
                    document_id = payload.get("document_id")
                    if isinstance(document_id, str) and document_id:
                        ids.add(document_id)
                if next_offset is None:
                    break
                if next_offset == offset:
                    break
                offset = next_offset
        except Exception as error:
            raise StorageError(message="Qdrant list ids failed", details={"reason": str(error)}) from error

        result = sorted(ids)
        logger.info("qdrant_list_indexed_document_ids_finished", documents_count=len(result))
        return result

    def _ensure_collection(self, vector_size: int):
        if self._collection_exists():
            return
        try:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=int(vector_size), distance=Distance.COSINE),
            )
        except Exception as error:
            raise StorageError(message="Qdrant collection create failed", details={"reason": str(error)}) from error
        logger.info("qdrant_collection_created", collection_name=self.collection_name, vector_size=int(vector_size))

    def _collection_exists(self) -> bool:
        try:
            if hasattr(self.client, "collection_exists"):
                return bool(self.client.collection_exists(self.collection_name))
            self.client.get_collection(self.collection_name)
            return True
        except Exception:
            return False
