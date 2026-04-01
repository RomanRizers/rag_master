import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import create_app


class ApiValidationTestCase(unittest.TestCase):
    SEARCH_ENDPOINTS = ("/searching", "/api/searching")
    INDEX_ENDPOINTS = ("/indexing", "/api/indexing")

    def setUp(self):
        app = create_app()
        self.client = TestClient(app)

    def test_root_health_is_available(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")

    def test_search_rejects_non_json_content_type(self):
        for endpoint in self.SEARCH_ENDPOINTS:
            response = self.client.post(
                endpoint,
                data='{"query":"hello"}',
                headers={"content-type": "text/plain"},
            )

            self.assertEqual(response.status_code, 415)
            payload = response.json()
            self.assertEqual(payload["error"]["code"], "invalid_content_type")

    def test_search_rejects_invalid_json(self):
        for endpoint in self.SEARCH_ENDPOINTS:
            response = self.client.post(endpoint, data='{"query":', headers={"content-type": "application/json"})

            self.assertEqual(response.status_code, 400)
            payload = response.json()
            self.assertEqual(payload["error"]["code"], "invalid_json")

    def test_search_requires_query(self):
        for endpoint in self.SEARCH_ENDPOINTS:
            response = self.client.post(endpoint, json={"top_k": 3})

            self.assertEqual(response.status_code, 400)
            payload = response.json()
            self.assertEqual(payload["error"]["message"], "Query is required")

    def test_search_validates_top_k_range(self):
        for endpoint in self.SEARCH_ENDPOINTS:
            response = self.client.post(endpoint, json={"query": "hello", "top_k": 0})

            self.assertEqual(response.status_code, 400)
            payload = response.json()
            self.assertEqual(payload["error"]["code"], "invalid_field")

    def test_search_validates_keywords_type(self):
        for endpoint in self.SEARCH_ENDPOINTS:
            response = self.client.post(endpoint, json={"query": "hello", "keywords": "tag"})

            self.assertEqual(response.status_code, 400)
            payload = response.json()
            self.assertEqual(payload["error"]["code"], "invalid_field")

    @patch("backend.api.routes.get_api_service")
    def test_search_success(self, get_api_service_mock):
        service = get_api_service_mock.return_value
        service.search_query.return_value = {"results": [{"id": "1"}], "total": 1}

        for endpoint in self.SEARCH_ENDPOINTS:
            response = self.client.post(endpoint, json={"query": "hello", "top_k": 3, "keywords": ["A"]})

            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["total"], 1)
        self.assertEqual(service.search_query.call_count, len(self.SEARCH_ENDPOINTS))

    def test_indexing_requires_document_name(self):
        for endpoint in self.INDEX_ENDPOINTS:
            response = self.client.post(endpoint, json={"documents": [{"content": "x"}]})

            self.assertEqual(response.status_code, 400)
            payload = response.json()
            self.assertEqual(payload["error"]["message"], "No document name provided")

    def test_indexing_requires_documents(self):
        for endpoint in self.INDEX_ENDPOINTS:
            response = self.client.post(endpoint, json={"document_name": "doc", "documents": []})

            self.assertEqual(response.status_code, 400)
            payload = response.json()
            self.assertEqual(payload["error"]["message"], "No documents to index")

    def test_indexing_validates_document_content(self):
        for endpoint in self.INDEX_ENDPOINTS:
            response = self.client.post(
                endpoint,
                json={"document_name": "doc", "documents": [{"content": "   "}]},
            )

            self.assertEqual(response.status_code, 400)
            payload = response.json()
            self.assertEqual(payload["error"]["code"], "invalid_field")

    @patch("backend.api.routes.get_api_service")
    def test_indexing_success(self, get_api_service_mock):
        service = get_api_service_mock.return_value
        service.index_documents.return_value = {"status": "success", "message": "1 documents indexed."}

        for endpoint in self.INDEX_ENDPOINTS:
            response = self.client.post(
                endpoint,
                json={
                    "document_name": "doc",
                    "documents": [{"content": "abc", "keywords": [" A "], "dataframe": "df"}],
                },
            )

            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["status"], "success")
        self.assertEqual(service.index_documents.call_count, len(self.INDEX_ENDPOINTS))


if __name__ == "__main__":
    unittest.main()
