import tempfile
import unittest

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


class _ApiServiceAlwaysFail:
    def __init__(self):
        self.calls = 0

    def index_documents(self, document_name: str, documents: list):
        self.calls += 1
        raise StorageError(message="down")


class IngestionServiceTestCase(unittest.TestCase):
    def test_retry_succeeds_on_second_attempt(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = LocalFileStorageAdapter(temp_dir)
            documents = DocumentService(storage=storage)
            record = documents.create_document("doc.txt", "text/plain", b"hello world")

            api_service = _ApiServiceFlaky()
            ingestion = IngestionService(document_service=documents, api_service=api_service)

            result = ingestion.start_indexing(record["document_id"])
            ingestion._executor.shutdown(wait=True)
            job = ingestion.get_job(result["job_id"])

            self.assertEqual(job["status"], "done")
            self.assertEqual(job["attempt"], 2)
            self.assertEqual(api_service.calls, 2)

    def test_retry_exhaustion_marks_job_failed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = LocalFileStorageAdapter(temp_dir)
            documents = DocumentService(storage=storage)
            record = documents.create_document("doc.txt", "text/plain", b"hello world")

            api_service = _ApiServiceAlwaysFail()
            ingestion = IngestionService(document_service=documents, api_service=api_service)

            result = ingestion.start_indexing(record["document_id"])
            ingestion._executor.shutdown(wait=True)
            job = ingestion.get_job(result["job_id"])

            self.assertEqual(job["status"], "failed")
            self.assertEqual(job["attempt"], 3)
            self.assertEqual(api_service.calls, 3)


if __name__ == "__main__":
    unittest.main()
