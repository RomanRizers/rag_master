import unittest
from unittest.mock import Mock

from backend.core.exceptions import StorageError, VectorizationError
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
        mock_qdrant.search.assert_called_once_with([0.1, 0.2], 2, ["one", "two"], filters=None)

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

    def test_index_documents_passes_metadata_to_qdrant(self):
        mock_vectorizer = Mock()
        mock_vectorizer.vectorize_text.return_value = [0.1, 0.2]
        mock_qdrant = Mock()
        service = ApiService(qdrant_service=mock_qdrant, vectorizer=mock_vectorizer)

        service.index_documents(
            "doc",
            [
                {
                    "content": "test",
                    "keywords": ["K1"],
                    "dataframe": None,
                    "metadata": {"document_id": "d1", "chunk_index": 3},
                }
            ],
        )

        call_kwargs = mock_qdrant.index_document.call_args.kwargs
        self.assertEqual(call_kwargs["metadata"]["document_id"], "d1")
        self.assertEqual(call_kwargs["metadata"]["chunk_index"], 3)
        self.assertEqual(call_kwargs["content_vector"], [0.1, 0.2])

    def test_delete_document_chunks_calls_qdrant(self):
        mock_qdrant = Mock()
        service = ApiService(qdrant_service=mock_qdrant, vectorizer=Mock())

        service.delete_document_chunks("d1")

        mock_qdrant.delete_document_chunks.assert_called_once_with("d1")

    def test_delete_document_chunks_wraps_storage_error(self):
        mock_qdrant = Mock()
        mock_qdrant.delete_document_chunks.side_effect = RuntimeError("qdrant down")
        service = ApiService(qdrant_service=mock_qdrant, vectorizer=Mock())

        with self.assertRaises(StorageError) as context:
            service.delete_document_chunks("d1")

        self.assertEqual(context.exception.details["document_id"], "d1")

    def test_count_document_chunks_calls_qdrant(self):
        mock_qdrant = Mock()
        mock_qdrant.count_document_chunks.return_value = 7
        service = ApiService(qdrant_service=mock_qdrant, vectorizer=Mock())

        result = service.count_document_chunks("d1")

        self.assertEqual(result, 7)
        mock_qdrant.count_document_chunks.assert_called_once_with("d1")

    def test_count_document_chunks_wraps_storage_error(self):
        mock_qdrant = Mock()
        mock_qdrant.count_document_chunks.side_effect = RuntimeError("qdrant down")
        service = ApiService(qdrant_service=mock_qdrant, vectorizer=Mock())

        with self.assertRaises(StorageError) as context:
            service.count_document_chunks("d1")

        self.assertEqual(context.exception.details["document_id"], "d1")

    def test_list_indexed_document_ids_calls_qdrant(self):
        mock_qdrant = Mock()
        mock_qdrant.list_indexed_document_ids.return_value = ["d1", "d2"]
        service = ApiService(qdrant_service=mock_qdrant, vectorizer=Mock())

        result = service.list_indexed_document_ids()

        self.assertEqual(result, ["d1", "d2"])
        mock_qdrant.list_indexed_document_ids.assert_called_once_with()

    def test_list_indexed_document_ids_wraps_storage_error(self):
        mock_qdrant = Mock()
        mock_qdrant.list_indexed_document_ids.side_effect = RuntimeError("qdrant down")
        service = ApiService(qdrant_service=mock_qdrant, vectorizer=Mock())

        with self.assertRaises(StorageError):
            service.list_indexed_document_ids()


if __name__ == "__main__":
    unittest.main()
