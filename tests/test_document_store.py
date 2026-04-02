import unittest
import os
from uuid import uuid4

from backend.infrastructure.document_store.postgres import PostgresDocumentStore


class PostgresDocumentStoreTestCase(unittest.TestCase):
    def test_create_get_and_set_status(self):
        dsn = os.getenv("RAG_TEST_POSTGRES_DSN")
        if not dsn:
            self.skipTest("set RAG_TEST_POSTGRES_DSN to run postgres store tests")
        document_id = f"d-{uuid4()}"
        store = PostgresDocumentStore(dsn=dsn)
        store.create_document(
            {
                "document_id": document_id,
                "file_name": "sample.txt",
                "mime_type": "text/plain",
                "size_bytes": 11,
                "status": "uploaded",
                "source_name": "manual",
                "tags": ["a", "b"],
                "created_at": "2026-04-03T00:00:00+00:00",
                "object_key": f"{document_id}/sample.txt",
            }
        )
        loaded = store.get_document(document_id)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["file_name"], "sample.txt")
        updated = store.set_status(document_id, "indexed")
        self.assertEqual(updated["status"], "indexed")

    def test_list_documents(self):
        dsn = os.getenv("RAG_TEST_POSTGRES_DSN")
        if not dsn:
            self.skipTest("set RAG_TEST_POSTGRES_DSN to run postgres store tests")
        store = PostgresDocumentStore(dsn=dsn)
        ids = []
        for index in range(2):
            document_id = f"d-{uuid4()}"
            ids.append(document_id)
            store.create_document(
                {
                    "document_id": document_id,
                    "file_name": "sample.txt",
                    "mime_type": "text/plain",
                    "size_bytes": 1,
                    "status": "uploaded",
                    "source_name": None,
                    "tags": [],
                    "created_at": f"2026-04-03T00:00:0{index}+00:00",
                    "object_key": f"{document_id}/sample.txt",
                }
            )
        docs = [item for item in store.list_documents() if item["document_id"] in set(ids)]
        self.assertEqual(len(docs), 2)


if __name__ == "__main__":
    unittest.main()
