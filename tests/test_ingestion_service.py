import tempfile
import unittest
from unittest.mock import patch

from backend.core.exceptions import StorageError
from backend.infrastructure.storage.local import LocalFileStorageAdapter
from backend.services.document_service import DocumentService
from backend.services.ingestion_service import IngestionService


class _ApiServiceFlaky:
    def __init__(self):
        self.calls = 0

    def index_documents(self, document_name: str, documents: list):
        self.calls += 1
        if self.calls < 2:
            raise StorageError(message="temporary")
        return {"status": "success"}

    def delete_document_chunks(self, document_id: str):
        return {"status": "success"}


class _ApiServiceAlwaysFail:
    def __init__(self):
        self.calls = 0

    def index_documents(self, document_name: str, documents: list):
        self.calls += 1
        raise StorageError(message="down")

    def delete_document_chunks(self, document_id: str):
        return {"status": "success"}


class _ApiServiceCapturePayload:
    def __init__(self):
        self.calls = 0
        self.delete_calls = 0
        self.last_deleted_document_id = None
        self.last_document_name = None
        self.last_documents = None

    def index_documents(self, document_name: str, documents: list):
        self.calls += 1
        self.last_document_name = document_name
        self.last_documents = documents
        return {"status": "success"}

    def delete_document_chunks(self, document_id: str):
        self.delete_calls += 1
        self.last_deleted_document_id = document_id
        return {"status": "success"}

    def count_document_chunks(self, document_id: str):
        return 11


class IngestionServiceTestCase(unittest.TestCase):
    def test_start_indexing_is_idempotent_for_active_job(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = LocalFileStorageAdapter(temp_dir)
            documents = DocumentService(storage=storage)
            record = documents.create_document("doc.txt", "text/plain", b"hello world")

            ingestion = IngestionService(document_service=documents, api_service=_ApiServiceFlaky())
            first = ingestion.start_indexing(record["document_id"])
            second = ingestion.start_indexing(record["document_id"])

            self.assertEqual(first["job_id"], second["job_id"])
            self.assertEqual(second["status"], "queued")

    def test_retry_succeeds_on_second_attempt(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = LocalFileStorageAdapter(temp_dir)
            documents = DocumentService(storage=storage)
            record = documents.create_document("doc.txt", "text/plain", b"hello world")

            api_service = _ApiServiceFlaky()
            ingestion = IngestionService(document_service=documents, api_service=api_service)

            result = ingestion.start_indexing(record["document_id"])
            claimed = ingestion.claim_next_job()
            self.assertIsNotNone(claimed)
            self.assertEqual(claimed["job_id"], result["job_id"])
            ingestion.process_job(result["job_id"])
            job = ingestion.get_job(result["job_id"])

            self.assertEqual(job["status"], "done")
            self.assertEqual(job["attempt"], 2)
            self.assertEqual(api_service.calls, 2)

    @patch("backend.services.ingestion_service.time.sleep")
    def test_retry_applies_backoff(self, sleep_mock):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = LocalFileStorageAdapter(temp_dir)
            documents = DocumentService(storage=storage)
            record = documents.create_document("doc.txt", "text/plain", b"hello world")

            api_service = _ApiServiceFlaky()
            ingestion = IngestionService(document_service=documents, api_service=api_service)

            with patch("backend.services.ingestion_service.Config.INGESTION_RETRY_BACKOFF_SECONDS", 0.1):
                result = ingestion.start_indexing(record["document_id"])
                claimed = ingestion.claim_next_job()
                self.assertIsNotNone(claimed)
                self.assertEqual(claimed["job_id"], result["job_id"])
                ingestion.process_job(result["job_id"])

            sleep_mock.assert_called_once_with(0.1)

    def test_retry_exhaustion_marks_job_failed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = LocalFileStorageAdapter(temp_dir)
            documents = DocumentService(storage=storage)
            record = documents.create_document("doc.txt", "text/plain", b"hello world")

            api_service = _ApiServiceAlwaysFail()
            ingestion = IngestionService(document_service=documents, api_service=api_service)

            result = ingestion.start_indexing(record["document_id"])
            claimed = ingestion.claim_next_job()
            self.assertIsNotNone(claimed)
            self.assertEqual(claimed["job_id"], result["job_id"])
            ingestion.process_job(result["job_id"])
            job = ingestion.get_job(result["job_id"])

            self.assertEqual(job["status"], "failed")
            self.assertEqual(job["attempt"], 3)
            self.assertEqual(api_service.calls, 3)

    def test_index_payload_contains_chunk_token_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = LocalFileStorageAdapter(temp_dir)
            documents = DocumentService(storage=storage)
            record = documents.create_document("doc.txt", "text/plain", b"one two three four")

            api_service = _ApiServiceCapturePayload()
            ingestion = IngestionService(document_service=documents, api_service=api_service)

            result = ingestion.start_indexing(record["document_id"])
            claimed = ingestion.claim_next_job()
            self.assertIsNotNone(claimed)
            self.assertEqual(claimed["job_id"], result["job_id"])
            ingestion.process_job(result["job_id"])

            self.assertEqual(api_service.calls, 1)
            self.assertEqual(api_service.delete_calls, 1)
            self.assertEqual(api_service.last_deleted_document_id, record["document_id"])
            self.assertEqual(api_service.last_document_name, "doc.txt")
            self.assertIsNotNone(api_service.last_documents)
            self.assertEqual(len(api_service.last_documents), 1)
            metadata = api_service.last_documents[0]["metadata"]
            self.assertEqual(metadata["document_id"], record["document_id"])
            self.assertEqual(metadata["chunk_id"], f"{record['document_id']}:0")
            self.assertEqual(metadata["chunk_index"], 0)
            self.assertEqual(metadata["token_count"], 4)
            self.assertEqual(metadata["source_uri"], f"{record['document_id']}/doc.txt")

    def test_get_document_index_stats(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = LocalFileStorageAdapter(temp_dir)
            documents = DocumentService(storage=storage)
            record = documents.create_document("doc.txt", "text/plain", b"one two three four")
            api_service = _ApiServiceCapturePayload()
            ingestion = IngestionService(document_service=documents, api_service=api_service)

            queued = ingestion.start_indexing(record["document_id"])
            stats = ingestion.get_document_index_stats(record["document_id"])

            self.assertEqual(stats["document_id"], record["document_id"])
            self.assertEqual(stats["status"], "uploaded")
            self.assertEqual(stats["chunks_count"], 11)
            self.assertEqual(stats["latest_job"]["job_id"], queued["job_id"])


if __name__ == "__main__":
    unittest.main()
