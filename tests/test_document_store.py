import tempfile
import unittest

from backend.infrastructure.document_store.sqlite import SqliteDocumentStore


class SqliteDocumentStoreTestCase(unittest.TestCase):
    def test_create_get_and_set_status(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SqliteDocumentStore(db_path=f"{temp_dir}/documents.db")
            store.create_document(
                {
                    "document_id": "d1",
                    "file_name": "sample.txt",
                    "mime_type": "text/plain",
                    "size_bytes": 11,
                    "status": "uploaded",
                    "source_name": "manual",
                    "tags": ["a", "b"],
                    "created_at": "2026-04-03T00:00:00+00:00",
                    "object_key": "d1/sample.txt",
                }
            )

            loaded = store.get_document("d1")
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded["file_name"], "sample.txt")
            self.assertEqual(loaded["tags"], ["a", "b"])

            updated = store.set_status("d1", "indexed")
            self.assertEqual(updated["status"], "indexed")

    def test_list_documents(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SqliteDocumentStore(db_path=f"{temp_dir}/documents.db")
            for index in range(2):
                store.create_document(
                    {
                        "document_id": f"d{index}",
                        "file_name": "sample.txt",
                        "mime_type": "text/plain",
                        "size_bytes": 1,
                        "status": "uploaded",
                        "source_name": None,
                        "tags": [],
                        "created_at": f"2026-04-03T00:00:0{index}+00:00",
                        "object_key": f"d{index}/sample.txt",
                    }
                )

            docs = store.list_documents()
            self.assertEqual(len(docs), 2)


if __name__ == "__main__":
    unittest.main()
