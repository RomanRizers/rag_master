import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import create_app
from backend.services.document_service import DocumentService


class _FakeIngestionService:
    def __init__(self):
        self.jobs = {}

    def start_indexing(self, document_id: str):
        job = {
            "job_id": "job-1",
            "document_id": document_id,
            "status": "queued",
            "progress": 0,
            "error_code": None,
            "error_message": None,
            "started_at": None,
            "finished_at": None,
        }
        self.jobs[job["job_id"]] = job
        return {"job_id": job["job_id"], "status": "queued", "document_id": document_id}

    def get_job(self, job_id: str):
        return self.jobs[job_id]


class DocumentIngestionApiTestCase(unittest.TestCase):
    def setUp(self):
        app = create_app()
        self.client = TestClient(app)
        self.document_service = DocumentService()
        self.ingestion_service = _FakeIngestionService()

    @patch("backend.api.routes.get_document_service")
    def test_upload_and_list_documents(self, get_document_service_mock):
        get_document_service_mock.return_value = self.document_service

        upload_response = self.client.post(
            "/api/documents/upload",
            files={"file": ("sample.txt", b"hello world", "text/plain")},
            data={"source_name": "manual", "tags": ["tag-a", "tag-b"]},
        )
        self.assertEqual(upload_response.status_code, 201)
        payload = upload_response.json()
        self.assertEqual(payload["file_name"], "sample.txt")
        self.assertEqual(payload["status"], "uploaded")
        self.assertEqual(payload["size_bytes"], 11)

        list_response = self.client.get("/api/documents")
        self.assertEqual(list_response.status_code, 200)
        documents = list_response.json()["documents"]
        self.assertEqual(len(documents), 1)
        self.assertEqual(documents[0]["source_name"], "manual")
        self.assertEqual(documents[0]["tags"], ["tag-a", "tag-b"])

    @patch("backend.api.routes.get_document_service")
    @patch("backend.api.routes.get_ingestion_service")
    def test_start_index_and_get_job_status(self, get_ingestion_service_mock, get_document_service_mock):
        get_document_service_mock.return_value = self.document_service
        get_ingestion_service_mock.return_value = self.ingestion_service

        upload_response = self.client.post(
            "/api/documents/upload",
            files={"file": ("sample.txt", b"hello world", "text/plain")},
        )
        document_id = upload_response.json()["document_id"]

        start_response = self.client.post(f"/api/documents/{document_id}/index")
        self.assertEqual(start_response.status_code, 202)
        self.assertEqual(start_response.json()["job_id"], "job-1")

        job_response = self.client.get("/api/jobs/job-1")
        self.assertEqual(job_response.status_code, 200)
        self.assertEqual(job_response.json()["status"], "queued")

    def test_upload_empty_file_returns_400(self):
        response = self.client.post(
            "/api/documents/upload",
            files={"file": ("empty.txt", b"", "text/plain")},
        )
        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertEqual(payload["error"]["code"], "empty_file")


if __name__ == "__main__":
    unittest.main()
