import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import create_app


class RateLimitMiddlewareTestCase(unittest.TestCase):
    @patch("backend.main.Config.RATE_LIMIT_ENABLED", True)
    @patch("backend.main.Config.RATE_LIMIT_CHAT_RPM", 1)
    @patch("backend.main.Config.RATE_LIMIT_INDEXING_RPM", 100)
    @patch("backend.main.Config.RATE_LIMIT_UPLOAD_RPM", 100)
    def test_chat_rate_limit_returns_429(self):
        app = create_app()
        client = TestClient(app)

        first = client.post("/api/chat/sessions")
        self.assertEqual(first.status_code, 200)

        second = client.post("/api/chat/sessions")
        self.assertEqual(second.status_code, 429)
        payload = second.json()
        self.assertEqual(payload["error"]["code"], "rate_limited")
        self.assertEqual(payload["error"]["details"]["bucket"], "chat")

    @patch("backend.main.Config.RATE_LIMIT_ENABLED", True)
    @patch("backend.main.Config.RATE_LIMIT_UPLOAD_RPM", 1)
    @patch("backend.main.Config.RATE_LIMIT_INDEXING_RPM", 100)
    @patch("backend.main.Config.RATE_LIMIT_CHAT_RPM", 100)
    def test_upload_rate_limit_returns_429(self):
        app = create_app()
        client = TestClient(app)

        first = client.post(
            "/api/documents/upload",
            files={"file": ("a.txt", b"hello", "text/plain")},
        )
        self.assertEqual(first.status_code, 201)

        second = client.post(
            "/api/documents/upload",
            files={"file": ("b.txt", b"world", "text/plain")},
        )
        self.assertEqual(second.status_code, 429)
        payload = second.json()
        self.assertEqual(payload["error"]["code"], "rate_limited")
        self.assertEqual(payload["error"]["details"]["bucket"], "upload")

    @patch("backend.main.Config.RATE_LIMIT_ENABLED", False)
    @patch("backend.main.Config.RATE_LIMIT_UPLOAD_RPM", 1)
    @patch("backend.main.Config.RATE_LIMIT_INDEXING_RPM", 1)
    @patch("backend.main.Config.RATE_LIMIT_CHAT_RPM", 1)
    def test_rate_limit_disabled(self):
        app = create_app()
        client = TestClient(app)

        first = client.post("/api/chat/sessions")
        second = client.post("/api/chat/sessions")
        self.assertNotEqual(first.status_code, 429)
        self.assertNotEqual(second.status_code, 429)


if __name__ == "__main__":
    unittest.main()
