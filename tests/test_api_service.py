import unittest
from unittest.mock import Mock

from backend.core.exceptions import VectorizationError, StorageError
from backend.services.api_service import ApiService


class ApiServiceTestCase(unittest.TestCase):
    def test_search_query_lowercases_keywords_and_returns_total(self):
        mock_vectorizer = Mock()
        mock_vectorizer.vectorize_text.return_value = [0.1, 0.2]

        mock_qdrant = Mock()
        mock_qdrant.search.return_value = [{"id": "a"}, {"id": "b"}]

        service = ApiService(qdrant_service=mock_qdrant, vectorizer=mock_vectorizer)
        result = service.search_query("hello", top_k=2, keywords=["One", "Two"])

        self.assertEqual(result["total"], 2)
        mock_qdrant.search.assert_called_once_with([0.1, 0.2], 2, ["one", "two"])

    def test_search_query_wraps_vectorizer_error(self):
        mock_vectorizer = Mock()
        mock_vectorizer.vectorize_text.side_effect = RuntimeError("model failed")
        service = ApiService(qdrant_service=Mock(), vectorizer=mock_vectorizer)

        with self.assertRaises(VectorizationError):
            service.search_query("hello", top_k=1)

    def test_index_documents_wraps_storage_error_with_index(self):
        mock_vectorizer = Mock()
        mock_vectorizer.vectorize_text.return_value = [0.1, 0.2]

        mock_qdrant = Mock()
        mock_qdrant.index_document.side_effect = RuntimeError("qdrant down")

        service = ApiService(qdrant_service=mock_qdrant, vectorizer=mock_vectorizer)

        with self.assertRaises(StorageError) as context:
            service.index_documents("doc", [{"content": "test", "keywords": [], "dataframe": None}])

        self.assertEqual(context.exception.details["index"], 0)


if __name__ == "__main__":
    unittest.main()
