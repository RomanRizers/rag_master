import unittest
import os
from uuid import uuid4

from backend.infrastructure.document_store.postgres import PostgresDocumentStore
from tests.postgres_test_schema import ensure_test_schema


class PostgresDocumentStoreTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        dsn = os.getenv("RAG_TEST_POSTGRES_DSN")
        if dsn:
            ensure_test_schema(dsn)

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
                "knowledge_base": "policies",
                "created_at": "2026-04-03T00:00:00+00:00",
                "object_key": f"{document_id}/sample.txt",
            }
        )
        loaded = store.get_document(document_id)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["file_name"], "sample.txt")
        self.assertEqual(loaded["knowledge_base"], "policies")
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
                    "knowledge_base": f"kb-{index}",
                    "created_at": f"2026-04-03T00:00:0{index}+00:00",
                    "object_key": f"{document_id}/sample.txt",
                }
            )
        docs = [item for item in store.list_documents() if item["document_id"] in set(ids)]
        self.assertEqual(len(docs), 2)

    def test_create_and_list_knowledge_bases(self):
        dsn = os.getenv("RAG_TEST_POSTGRES_DSN")
        if not dsn:
            self.skipTest("set RAG_TEST_POSTGRES_DSN to run postgres store tests")
        store = PostgresDocumentStore(dsn=dsn)
        base_name = f"kb-{uuid4()}"
        created = store.create_knowledge_base({"name": base_name, "created_at": "2026-04-05T00:00:00+00:00"})
        self.assertEqual(created["name"], base_name)
        listed = {item["name"] for item in store.list_knowledge_bases()}
        self.assertIn(base_name, listed)

    def test_update_document_knowledge_base(self):
        dsn = os.getenv("RAG_TEST_POSTGRES_DSN")
        if not dsn:
            self.skipTest("set RAG_TEST_POSTGRES_DSN to run postgres store tests")
        document_id = str(uuid4())
        store = PostgresDocumentStore(dsn=dsn)
        store.create_knowledge_base({"name": "kb-source", "created_at": "2026-04-05T00:00:00+00:00"})
        store.create_knowledge_base({"name": "kb-target", "created_at": "2026-04-05T00:00:00+00:00"})
        store.create_document(
            {
                "document_id": document_id,
                "file_name": "sample.txt",
                "mime_type": "text/plain",
                "size_bytes": 11,
                "status": "uploaded",
                "source_name": None,
                "tags": [],
                "knowledge_base": "kb-source",
                "created_at": "2026-04-03T00:00:00+00:00",
                "object_key": f"{document_id}/sample.txt",
            }
        )

        updated = store.update_document_knowledge_base(document_id, "kb-target")

        self.assertIsNotNone(updated)
        self.assertEqual(updated["knowledge_base"], "kb-target")

    def test_delete_document(self):
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
                "source_name": None,
                "tags": [],
                "knowledge_base": "policies",
                "created_at": "2026-04-03T00:00:00+00:00",
                "object_key": f"{document_id}/sample.txt",
            }
        )
        deleted = store.delete_document(document_id)
        self.assertIsNotNone(deleted)
        self.assertEqual(deleted["document_id"], document_id)
        self.assertIsNone(store.get_document(document_id))


if __name__ == "__main__":
    unittest.main()
