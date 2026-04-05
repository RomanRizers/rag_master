import unittest
from unittest.mock import Mock, patch

from backend.infrastructure.qdrant.client import QdrantService


class QdrantServiceTestCase(unittest.TestCase):
    @patch("backend.infrastructure.qdrant.client.qdrant_client.QdrantClient")
    def test_delete_document_chunks_is_noop_when_collection_missing(self, qdrant_client_mock):
        client = Mock()
        client.collection_exists.return_value = False
        qdrant_client_mock.return_value = client

        service = QdrantService()
        service.delete_document_chunks("doc-1")

        client.delete.assert_not_called()

    @patch("backend.infrastructure.qdrant.client.qdrant_client.QdrantClient")
    def test_index_document_creates_collection_before_upsert(self, qdrant_client_mock):
        client = Mock()
        client.collection_exists.side_effect = [False, True]
        qdrant_client_mock.return_value = client

        class _Vector(list):
            def tolist(self):
                return list(self)

        vector = _Vector([0.1, 0.2, 0.3])

        service = QdrantService()
        service.index_document("doc", vector, "content", [])

        client.create_collection.assert_called_once()
        client.upsert.assert_called_once()

    @patch("backend.infrastructure.qdrant.client.qdrant_client.QdrantClient")
    def test_update_document_knowledge_base_is_noop_when_collection_missing(self, qdrant_client_mock):
        client = Mock()
        client.collection_exists.return_value = False
        qdrant_client_mock.return_value = client

        service = QdrantService()
        service.update_document_knowledge_base("doc-1", "kb-2")

        client.set_payload.assert_not_called()


if __name__ == "__main__":
    unittest.main()
