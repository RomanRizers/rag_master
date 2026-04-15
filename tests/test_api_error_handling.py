import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.core.exceptions import StorageError, VectorizationError
from backend.main import create_app


class ApiErrorHandlingTestCase(unittest.TestCase):
    SEARCH_ENDPOINTS = ("/searching", "/api/searching")

    def setUp(self):
        app = create_app()
        self.client = TestClient(app, raise_server_exceptions=False)

    @patch("backend.api.routes.get_api_service")
    def test_maps_vectorization_error(self, get_api_service_mock):
        service = get_api_service_mock.return_value
        service.search_query.side_effect = VectorizationError(message="Vectorization failed")

        for endpoint in self.SEARCH_ENDPOINTS:
            response = self.client.post(endpoint, json={"query": "hello"})
            self.assertEqual(response.status_code, 503)
            payload = response.json()
            self.assertEqual(payload["error"]["code"], "vectorization_error")

    @patch("backend.api.routes.get_api_service")
    def test_maps_storage_error(self, get_api_service_mock):
        service = get_api_service_mock.return_value
        service.search_query.side_effect = StorageError(message="Storage failed")

        for endpoint in self.SEARCH_ENDPOINTS:
            response = self.client.post(endpoint, json={"query": "hello"})
            self.assertEqual(response.status_code, 503)
            payload = response.json()
            self.assertEqual(payload["error"]["code"], "storage_error")

    @patch("backend.api.routes.get_api_service")
    def test_maps_unexpected_error(self, get_api_service_mock):
        service = get_api_service_mock.return_value
        service.search_query.side_effect = RuntimeError("boom")

        for endpoint in self.SEARCH_ENDPOINTS:
            response = self.client.post(endpoint, json={"query": "hello"})
            self.assertEqual(response.status_code, 500)
            payload = response.json()
            self.assertEqual(payload["error"]["code"], "internal_error")
            self.assertEqual(payload["error"]["details"]["type"], "RuntimeError")


if __name__ == "__main__":
    unittest.main()
