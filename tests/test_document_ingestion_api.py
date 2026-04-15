import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import create_app
from backend.services.document_service import DocumentService


class _FakeIngestionService:
    def __init__(self):
        self.jobs = {}
        self.deleted_document_ids = []

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

    def list_jobs(self, status: str | None = None, document_id: str | None = None):
        items = list(self.jobs.values())
        if status:
            items = [item for item in items if item.get("status") == status]
        if document_id:
            items = [item for item in items if item.get("document_id") == document_id]
        return items

    def get_document_index_stats(self, document_id: str):
        jobs = self.list_jobs(document_id=document_id)
        latest_job = jobs[0] if jobs else None
        return {
            "document_id": document_id,
            "status": "uploaded",
            "chunks_count": 3,
            "latest_job": latest_job,
        }

    def cleanup_orphan_chunks(self, dry_run: bool = True):
        return {
            "dry_run": dry_run,
            "indexed_documents_count": 4,
            "existing_documents_count": 3,
            "orphan_document_ids": ["orphan-1"],
            "deleted_documents_count": 0 if dry_run else 1,
        }

    def delete_document(self, document_id: str):
        self.deleted_document_ids.append(document_id)
        self.jobs = {
            job_id: job
            for job_id, job in self.jobs.items()
            if job.get("document_id") != document_id
        }
        return {
            "document_id": document_id,
            "file_name": "sample.txt",
            "mime_type": "text/plain",
            "size_bytes": 11,
            "status": "uploaded",
            "source_name": "manual",
            "tags": ["tag-a", "tag-b"],
            "knowledge_base": "policies",
            "created_at": "2026-04-05T00:00:00+00:00",
        }


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
            data={"source_name": "manual", "tags": ["tag-a", "tag-b"], "knowledge_base": "policies"},
        )
        self.assertEqual(upload_response.status_code, 201)
        payload = upload_response.json()
        self.assertEqual(payload["file_name"], "sample.txt")
        self.assertEqual(payload["status"], "uploaded")
        self.assertEqual(payload["size_bytes"], 11)
        self.assertEqual(payload["knowledge_base"], "policies")

        list_response = self.client.get("/api/documents")
        self.assertEqual(list_response.status_code, 200)
        documents = list_response.json()["documents"]
        self.assertEqual(len(documents), 1)
        self.assertEqual(documents[0]["source_name"], "manual")
        self.assertEqual(documents[0]["tags"], ["tag-a", "tag-b"])
        self.assertEqual(documents[0]["knowledge_base"], "policies")

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

    @patch("backend.api.routes.get_document_service")
    @patch("backend.api.routes.get_ingestion_service")
    def test_list_jobs_supports_filters(self, get_ingestion_service_mock, get_document_service_mock):
        get_document_service_mock.return_value = self.document_service
        get_ingestion_service_mock.return_value = self.ingestion_service

        upload_response = self.client.post(
            "/api/documents/upload",
            files={"file": ("sample.txt", b"hello world", "text/plain")},
        )
        document_id = upload_response.json()["document_id"]
        self.client.post(f"/api/documents/{document_id}/index")

        list_response = self.client.get("/api/jobs")
        self.assertEqual(list_response.status_code, 200)
        jobs = list_response.json()["jobs"]
        self.assertEqual(len(jobs), 1)

        filtered = self.client.get("/api/jobs", params={"status": "queued", "document_id": document_id})
        self.assertEqual(filtered.status_code, 200)
        filtered_jobs = filtered.json()["jobs"]
        self.assertEqual(len(filtered_jobs), 1)

    def test_upload_empty_file_returns_400(self):
        response = self.client.post(
            "/api/documents/upload",
            files={"file": ("empty.txt", b"", "text/plain")},
        )
        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertEqual(payload["error"]["code"], "empty_file")

    def test_upload_unsupported_file_type_returns_400(self):
        response = self.client.post(
            "/api/documents/upload",
            files={"file": ("archive.bin", b"fake-bytes", "application/octet-stream")},
        )
        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertEqual(payload["error"]["code"], "invalid_file_type")

    def test_upload_spoofed_pdf_returns_400(self):
        response = self.client.post(
            "/api/documents/upload",
            files={"file": ("spoofed.pdf", b"this is not a pdf", "application/pdf")},
        )
        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertEqual(payload["error"]["code"], "invalid_file_type")

    @patch("backend.services.document_service.Config.MAX_UPLOAD_SIZE_BYTES", 8)
    def test_upload_too_large_returns_413(self):
        response = self.client.post(
            "/api/documents/upload",
            files={"file": ("large.txt", b"0123456789", "text/plain")},
        )
        self.assertEqual(response.status_code, 413)
        payload = response.json()
        self.assertEqual(payload["error"]["code"], "file_too_large")

    @patch("backend.api.routes.get_document_service")
    @patch("backend.api.routes.get_ingestion_service")
    def test_document_index_stats_endpoint(self, get_ingestion_service_mock, get_document_service_mock):
        get_document_service_mock.return_value = self.document_service
        get_ingestion_service_mock.return_value = self.ingestion_service

        upload_response = self.client.post(
            "/api/documents/upload",
            files={"file": ("sample.txt", b"hello world", "text/plain")},
        )
        document_id = upload_response.json()["document_id"]
        self.client.post(f"/api/documents/{document_id}/index")

        response = self.client.get(f"/api/documents/{document_id}/index-stats")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["document_id"], document_id)
        self.assertEqual(payload["chunks_count"], 3)
        self.assertEqual(payload["latest_job"]["job_id"], "job-1")

    @patch("backend.api.routes.get_document_service")
    @patch("backend.api.routes.get_ingestion_service")
    def test_delete_document_endpoint(self, get_ingestion_service_mock, get_document_service_mock):
        get_document_service_mock.return_value = self.document_service
        get_ingestion_service_mock.return_value = self.ingestion_service

        upload_response = self.client.post(
            "/api/documents/upload",
            files={"file": ("sample.txt", b"hello world", "text/plain")},
        )
        document_id = upload_response.json()["document_id"]

        response = self.client.delete(f"/api/documents/{document_id}")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "deleted")
        self.assertEqual(payload["document"]["document_id"], document_id)
        self.assertEqual(self.ingestion_service.deleted_document_ids, [document_id])

    @patch("backend.api.routes.get_document_service")
    def test_list_knowledge_bases_endpoint(self, get_document_service_mock):
        get_document_service_mock.return_value = self.document_service

        self.client.post(
            "/api/documents/upload",
            files={"file": ("sample.txt", b"hello world", "text/plain")},
            data={"knowledge_base": "policies"},
        )
        self.client.post(
            "/api/documents/upload",
            files={"file": ("guide.txt", b"hello world", "text/plain")},
            data={"knowledge_base": "hr"},
        )

        response = self.client.get("/api/knowledge-bases")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        names = {item["name"] for item in payload["knowledge_bases"]}
        self.assertEqual(names, {"hr", "policies"})

    @patch("backend.api.routes.get_document_service")
    @patch("backend.api.routes.get_ingestion_service")
    @patch("backend.api.dependencies.Config.ADMIN_API_KEY", "test-admin-key")
    def test_cleanup_orphan_chunks_endpoint(self, get_ingestion_service_mock, get_document_service_mock):
        get_document_service_mock.return_value = self.document_service
        get_ingestion_service_mock.return_value = self.ingestion_service

        response = self.client.post(
            "/api/admin/index/orphans/cleanup",
            json={"dry_run": True},
            headers={"X-Admin-API-Key": "test-admin-key"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["dry_run"], True)
        self.assertEqual(payload["orphan_document_ids"], ["orphan-1"])
        self.assertEqual(payload["deleted_documents_count"], 0)

    @patch("backend.api.dependencies.Config.ADMIN_API_KEY", "test-admin-key")
    def test_cleanup_orphan_chunks_endpoint_requires_admin_key(self):
        response = self.client.post("/api/admin/index/orphans/cleanup", json={"dry_run": True})
        self.assertEqual(response.status_code, 401)
        payload = response.json()
        self.assertEqual(payload["error"]["code"], "unauthorized")


if __name__ == "__main__":
    unittest.main()
