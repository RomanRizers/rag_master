import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import create_app
from backend.services.chat_service import ChatService


class _FakeLLMProvider:
    def generate(self, messages, temperature=0.2, max_tokens=700):
        return "assistant reply"

    def stream_chat(self, messages, temperature=0.2, max_tokens=700):
        yield "assistant "
        yield "reply"


def _fake_retriever(query, top_k, keywords, filters=None):
    _ = (query, top_k, keywords, filters)
    return {
        "results": [
            {
                "id": "chunk-1",
                "payload": {
                    "document_name": "TestDoc.pdf",
                    "page": 3,
                    "content": "Это релевантный фрагмент для ответа ассистента.",
                    "tags": ["finance", "contracts"],
                },
            },
            {
                "id": "chunk-2",
                "payload": {
                    "document_name": "OtherDoc.pdf",
                    "page": 1,
                    "content": "Другой фрагмент для проверки фильтра.",
                    "tags": ["hr"],
                },
            },
        ],
        "total": 2,
    }


class ChatApiTestCase(unittest.TestCase):
    def setUp(self):
        app = create_app()
        self.client = TestClient(app)
        self.chat_service = ChatService(llm_provider=_FakeLLMProvider(), retriever=_fake_retriever)

    @patch("backend.api.routes.get_chat_service")
    def test_create_session_send_message_and_read_history(self, get_chat_service_mock):
        get_chat_service_mock.return_value = self.chat_service

        create_response = self.client.post("/api/chat/sessions")
        self.assertEqual(create_response.status_code, 200)
        session_id = create_response.json()["session_id"]

        send_response = self.client.post(
            f"/api/chat/sessions/{session_id}/messages",
            json={"message": "hello"},
        )
        self.assertEqual(send_response.status_code, 200)
        payload = send_response.json()
        self.assertEqual(payload["assistant_message"]["content"], "assistant reply")
        citations = payload["assistant_message"]["citations"]
        self.assertGreaterEqual(len(citations), 1)
        citation_names = {item["document_name"] for item in citations}
        self.assertIn("TestDoc.pdf", citation_names)

        history_response = self.client.get(f"/api/chat/sessions/{session_id}/messages")
        self.assertEqual(history_response.status_code, 200)
        history_payload = history_response.json()
        self.assertEqual(len(history_payload["messages"]), 2)
        self.assertEqual(history_payload["messages"][0]["role"], "user")
        self.assertEqual(history_payload["messages"][1]["role"], "assistant")

    @patch("backend.api.routes.get_chat_service")
    def test_list_sessions_returns_created_session(self, get_chat_service_mock):
        get_chat_service_mock.return_value = self.chat_service

        create_response = self.client.post("/api/chat/sessions")
        self.assertEqual(create_response.status_code, 200)
        session_id = create_response.json()["session_id"]

        list_response = self.client.get("/api/chat/sessions")
        self.assertEqual(list_response.status_code, 200)
        sessions = list_response.json()["sessions"]
        self.assertGreaterEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["session_id"], session_id)

    @patch("backend.api.routes.get_chat_service")
    def test_missing_session_returns_404(self, get_chat_service_mock):
        get_chat_service_mock.return_value = self.chat_service

        response = self.client.post(
            "/api/chat/sessions/missing/messages",
            json={"message": "hello"},
        )
        self.assertEqual(response.status_code, 404)
        payload = response.json()
        self.assertEqual(payload["error"]["code"], "session_not_found")

    @patch("backend.api.routes.get_chat_service")
    def test_stream_endpoint_returns_sse_events(self, get_chat_service_mock):
        get_chat_service_mock.return_value = self.chat_service

        create_response = self.client.post("/api/chat/sessions")
        session_id = create_response.json()["session_id"]

        with self.client.stream(
            "POST",
            f"/api/chat/sessions/{session_id}/messages/stream",
            json={"message": "hello"},
        ) as response:
            self.assertEqual(response.status_code, 200)
            self.assertIn("text/event-stream", response.headers.get("content-type", ""))
            raw = response.read().decode("utf-8")

        self.assertIn("event: delta", raw)
        self.assertIn("event: citations", raw)
        self.assertIn("event: done", raw)

    @patch("backend.api.routes.get_chat_service")
    def test_send_message_supports_filters(self, get_chat_service_mock):
        get_chat_service_mock.return_value = self.chat_service

        create_response = self.client.post("/api/chat/sessions")
        session_id = create_response.json()["session_id"]

        send_response = self.client.post(
            f"/api/chat/sessions/{session_id}/messages",
            json={
                "message": "hello",
                "filters": {"document_names": ["TestDoc.pdf"], "tags": ["finance"]},
            },
        )
        self.assertEqual(send_response.status_code, 200)
        payload = send_response.json()
        citations = payload["assistant_message"]["citations"]
        self.assertEqual(len(citations), 1)
        self.assertEqual(citations[0]["document_name"], "TestDoc.pdf")

    @patch("backend.api.routes.get_chat_service")
    def test_send_message_rejects_invalid_filters(self, get_chat_service_mock):
        get_chat_service_mock.return_value = self.chat_service

        create_response = self.client.post("/api/chat/sessions")
        session_id = create_response.json()["session_id"]

        response = self.client.post(
            f"/api/chat/sessions/{session_id}/messages",
            json={"message": "hello", "filters": {"document_names": "bad"}},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "invalid_field")


if __name__ == "__main__":
    unittest.main()
