import unittest
import os
from uuid import uuid4

from backend.infrastructure.chat_store.postgres import PostgresChatStore
from tests.postgres_test_schema import ensure_test_schema


class PostgresChatStoreTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        dsn = os.getenv("RAG_TEST_POSTGRES_DSN")
        if dsn:
            ensure_test_schema(dsn)

    def test_create_append_and_read_messages(self):
        dsn = os.getenv("RAG_TEST_POSTGRES_DSN")
        if not dsn:
            self.skipTest("set RAG_TEST_POSTGRES_DSN to run postgres store tests")
        session_id = f"s-{uuid4()}"
        store = PostgresChatStore(dsn=dsn)
        session = store.create_session(session_id, "2026-04-03T00:00:00+00:00")
        self.assertEqual(session["session_id"], session_id)
        ok = store.append_message(
            session_id,
            {
                "id": f"m-{uuid4()}",
                "role": "user",
                "content": "hello",
                "citations": [],
                "created_at": "2026-04-03T00:00:01+00:00",
            },
        )
        self.assertTrue(ok)
        messages = store.get_messages(session_id)
        self.assertIsNotNone(messages)
        self.assertEqual(len(messages), 1)

    def test_list_sessions_contains_metadata(self):
        dsn = os.getenv("RAG_TEST_POSTGRES_DSN")
        if not dsn:
            self.skipTest("set RAG_TEST_POSTGRES_DSN to run postgres store tests")
        session_id = f"s-{uuid4()}"
        store = PostgresChatStore(dsn=dsn)
        store.create_session(session_id, "2026-04-03T00:00:00+00:00")
        store.append_message(
            session_id,
            {
                "id": f"m-{uuid4()}",
                "role": "assistant",
                "content": "answer",
                "citations": [{"document_id": "d1"}],
                "created_at": "2026-04-03T00:00:02+00:00",
            },
        )
        sessions = [item for item in store.list_sessions() if item["session_id"] == session_id]
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["message_count"], 1)


if __name__ == "__main__":
    unittest.main()
