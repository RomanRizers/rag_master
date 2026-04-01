import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import create_app


class ApiValidationTestCase(unittest.TestCase):
    def setUp(self):
        app = create_app()
        self.client = TestClient(app)

    def test_search_rejects_non_json_content_type(self):
        response = self.client.post("/searching", data='{"query":"hello"}', headers={"content-type": "text/plain"})

        self.assertEqual(response.status_code, 415)
        payload = response.json()
        self.assertEqual(payload["error"]["code"], "invalid_content_type")

    def test_search_rejects_invalid_json(self):
        response = self.client.post("/searching", data='{"query":', headers={"content-type": "application/json"})

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertEqual(payload["error"]["code"], "invalid_json")

    def test_search_requires_query(self):
        response = self.client.post("/searching", json={"top_k": 3})

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertEqual(payload["error"]["message"], "Query is required")

    def test_search_validates_top_k_range(self):
        response = self.client.post("/searching", json={"query": "hello", "top_k": 0})

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertEqual(payload["error"]["code"], "invalid_field")

    def test_search_validates_keywords_type(self):
        response = self.client.post("/searching", json={"query": "hello", "keywords": "tag"})

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertEqual(payload["error"]["code"], "invalid_field")

    @patch("app.api.get_api_service")
    def test_search_success(self, get_api_service_mock):
        service = get_api_service_mock.return_value
        service.search_query.return_value = {"results": [{"id": "1"}], "total": 1}

        response = self.client.post("/searching", json={"query": "hello", "top_k": 3, "keywords": ["A"]})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total"], 1)
        service.search_query.assert_called_once_with("hello", 3, ["A"])

    def test_indexing_requires_document_name(self):
        response = self.client.post("/indexing", json={"documents": [{"content": "x"}]})

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertEqual(payload["error"]["message"], "No document name provided")

    def test_indexing_requires_documents(self):
        response = self.client.post("/indexing", json={"document_name": "doc", "documents": []})

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertEqual(payload["error"]["message"], "No documents to index")

    def test_indexing_validates_document_content(self):
        response = self.client.post(
            "/indexing",
            json={"document_name": "doc", "documents": [{"content": "   "}]},
        )

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertEqual(payload["error"]["code"], "invalid_field")

    @patch("app.api.get_api_service")
    def test_indexing_success(self, get_api_service_mock):
        service = get_api_service_mock.return_value
        service.index_documents.return_value = {"status": "success", "message": "1 documents indexed."}

        response = self.client.post(
            "/indexing",
            json={
                "document_name": "doc",
                "documents": [{"content": "abc", "keywords": [" A "], "dataframe": "df"}],
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "success")
        service.index_documents.assert_called_once_with(
            "doc",
            [{"content": "abc", "keywords": ["A"], "dataframe": "df"}],
        )


if __name__ == "__main__":
    unittest.main()
