from backend.core.exceptions import StorageError, VectorizationError
from backend.infrastructure.ml.vectorizer import TextVectorizer
from backend.infrastructure.qdrant.client import QdrantService
import structlog

logger = structlog.get_logger("api_service")

class ApiService:
    def __init__(self, qdrant_service=None, vectorizer=None):
        self.qdrant_service = qdrant_service or QdrantService()
        self.vectorizer = vectorizer or TextVectorizer()

    def search_query(self, query: str, top_k: int, keywords: list = None):
        """Выполняет поиск по запросу и возвращает результаты."""
        if keywords:
            keywords = [kw.lower() for kw in keywords]
        logger.info(
            "search_query_started",
            query_length=len(query),
            top_k=top_k,
            keywords_count=len(keywords) if keywords else 0,
        )

        try:
            query_vector = self.vectorizer.vectorize_text(query)
        except VectorizationError:
            raise
        except Exception as error:
            raise VectorizationError(details={"reason": str(error)}) from error

        try:
            search_results = self.qdrant_service.search(query_vector, top_k, keywords)
        except StorageError:
            raise
        except Exception as error:
            raise StorageError(details={"reason": str(error)}) from error

        logger.info("search_query_finished", results_count=len(search_results))

        return {
            "results": search_results,
            "total": len(search_results)
        }

    def index_documents(self, document_name: str, documents: list):
        """Индексирует документы в Qdrant."""
        logger.info(
            "index_documents_started",
            document_name=document_name,
            documents_count=len(documents),
        )
        for index, document in enumerate(documents):
            content = document.get('content')
            keywords = document.get('keywords', [])
            dataframe = document.get('dataframe', None)
            metadata = document.get('metadata', None)
            keywords = [kw.lower() for kw in keywords]

            try:
                content_vector = self.vectorizer.vectorize_text(content)
            except VectorizationError:
                raise
            except Exception as error:
                raise VectorizationError(
                    message="Vectorization failed while indexing",
                    details={"index": index, "reason": str(error)},
                ) from error

            try:
                self.qdrant_service.index_document(
                    document_name=document_name,
                    content_vector=content_vector,
                    content=content,
                    keywords=keywords,
                    dataframe=dataframe,
                    metadata=metadata,
                )
            except StorageError:
                raise
            except Exception as error:
                raise StorageError(
                    message="Storage failed while indexing",
                    details={"index": index, "reason": str(error)},
                ) from error
        logger.info("index_documents_finished", document_name=document_name, documents_count=len(documents))
        return {"status": "success", "message": f"{len(documents)} documents indexed."}

    def delete_document_chunks(self, document_id: str):
        logger.info("delete_document_chunks_started", document_id=document_id)
        try:
            self.qdrant_service.delete_document_chunks(document_id)
        except StorageError:
            raise
        except Exception as error:
            raise StorageError(
                message="Storage failed while deleting document chunks",
                details={"document_id": document_id, "reason": str(error)},
            ) from error
        logger.info("delete_document_chunks_finished", document_id=document_id)

    def count_document_chunks(self, document_id: str) -> int:
        logger.info("count_document_chunks_started", document_id=document_id)
        try:
            count = self.qdrant_service.count_document_chunks(document_id)
        except StorageError:
            raise
        except Exception as error:
            raise StorageError(
                message="Storage failed while counting document chunks",
                details={"document_id": document_id, "reason": str(error)},
            ) from error
        logger.info("count_document_chunks_finished", document_id=document_id, chunks_count=count)
        return count

    def list_indexed_document_ids(self) -> list[str]:
        logger.info("list_indexed_document_ids_started")
        try:
            ids = self.qdrant_service.list_indexed_document_ids()
        except StorageError:
            raise
        except Exception as error:
            raise StorageError(
                message="Storage failed while listing indexed document ids",
                details={"reason": str(error)},
            ) from error
        logger.info("list_indexed_document_ids_finished", documents_count=len(ids))
        return ids
