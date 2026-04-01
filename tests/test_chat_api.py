import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import create_app
from backend.services.chat_service import ChatService


class _FakeLLMProvider:
    def generate(self, messages, temperature=0.2, max_tokens=700):
        return "assistant reply"


class ChatApiTestCase(unittest.TestCase):
    def setUp(self):
        app = create_app()
        self.client = TestClient(app)
        self.chat_service = ChatService(llm_provider=_FakeLLMProvider())

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

        history_response = self.client.get(f"/api/chat/sessions/{session_id}/messages")
        self.assertEqual(history_response.status_code, 200)
        history_payload = history_response.json()
        self.assertEqual(len(history_payload["messages"]), 2)
        self.assertEqual(history_payload["messages"][0]["role"], "user")
        self.assertEqual(history_payload["messages"][1]["role"], "assistant")

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


if __name__ == "__main__":
    unittest.main()
