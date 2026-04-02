import tempfile
import unittest

from backend.infrastructure.chat_store.sqlite import SqliteChatStore


class SqliteChatStoreTestCase(unittest.TestCase):
    def test_create_append_and_read_messages(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SqliteChatStore(db_path=f"{temp_dir}/chat.db")
            session = store.create_session("s1", "2026-04-03T00:00:00+00:00")
            self.assertEqual(session["session_id"], "s1")

            ok = store.append_message(
                "s1",
                {
                    "id": "m1",
                    "role": "user",
                    "content": "hello",
                    "citations": [],
                    "created_at": "2026-04-03T00:00:01+00:00",
                },
            )
            self.assertTrue(ok)

            messages = store.get_messages("s1")
            self.assertIsNotNone(messages)
            self.assertEqual(len(messages), 1)
            self.assertEqual(messages[0]["id"], "m1")

    def test_list_sessions_contains_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SqliteChatStore(db_path=f"{temp_dir}/chat.db")
            store.create_session("s1", "2026-04-03T00:00:00+00:00")
            store.append_message(
                "s1",
                {
                    "id": "m1",
                    "role": "assistant",
                    "content": "answer",
                    "citations": [{"document_id": "d1"}],
                    "created_at": "2026-04-03T00:00:02+00:00",
                },
            )

            sessions = store.list_sessions()
            self.assertEqual(len(sessions), 1)
            self.assertEqual(sessions[0]["session_id"], "s1")
            self.assertEqual(sessions[0]["message_count"], 1)
            self.assertEqual(sessions[0]["last_message_at"], "2026-04-03T00:00:02+00:00")


if __name__ == "__main__":
    unittest.main()
