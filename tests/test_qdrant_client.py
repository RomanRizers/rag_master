import unittest
from unittest.mock import Mock, patch

from backend.infrastructure.qdrant.client import QdrantService


class _Point:
    def __init__(self, point_id, payload, score):
        self.id = point_id
        self.payload = payload
        self.score = score


class _QueryResponse:
    def __init__(self, points):
        self.points = points


class QdrantClientCompatibilityTestCase(unittest.TestCase):
    @patch("backend.infrastructure.qdrant.client.qdrant_client.QdrantClient")
    def test_search_uses_query_points_when_available(self, qdrant_client_mock):
        client = Mock()
        client.query_points.return_value = _QueryResponse([_Point("1", {"a": 1}, 0.9)])
        qdrant_client_mock.return_value = client

        service = QdrantService()
        results = service.search([0.1, 0.2], top_k=1)

        client.query_points.assert_called_once()
        self.assertEqual(results, [{"id": "1", "payload": {"a": 1}, "score": 0.9}])

    @patch("backend.infrastructure.qdrant.client.qdrant_client.QdrantClient")
    def test_search_falls_back_to_legacy_search(self, qdrant_client_mock):
        class LegacyClient:
            def search(self, **kwargs):
                return [_Point("2", {"b": 2}, 0.8)]

        qdrant_client_mock.return_value = LegacyClient()
        service = QdrantService()
        results = service.search([0.1, 0.2], top_k=1)

        self.assertEqual(results, [{"id": "2", "payload": {"b": 2}, "score": 0.8}])


if __name__ == "__main__":
    unittest.main()
