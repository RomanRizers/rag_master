from app.qdrant_client import QdrantService
from app.vectorizer import TextVectorizer

class ApiService:
    def __init__(self):
        self.qdrant_service = QdrantService()
        self.vectorizer = TextVectorizer()

    def search_query(self, query: str, top_k: int, keywords: list = None):
        """Выполняет поиск по запросу и возвращает результаты."""
        if keywords:
            keywords = [kw.lower() for kw in keywords]

        query_vector = self.vectorizer.vectorize_text(query)
        search_results = self.qdrant_service.search(query_vector, top_k, keywords)
        return {
            "results": search_results,
            "total": len(search_results)
        }

    def index_documents(self, document_name: str, documents: list):
        """Индексирует документы в Qdrant."""
        for document in documents:
            content = document.get('content')
            keywords = document.get('keywords', [])
            dataframe = document.get('dataframe', None)
            keywords = [kw.lower() for kw in keywords]

            content_vector = self.vectorizer.vectorize_text(content)
            self.qdrant_service.index_document(
                document_name=document_name,
                content_vector=content_vector,
                content=content,
                keywords=keywords,
                dataframe=dataframe
            )
        return {"status": "success", "message": f"{len(documents)} documents indexed."}
