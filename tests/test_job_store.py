import unittest
import os
from uuid import uuid4

from backend.infrastructure.job_store.postgres import PostgresJobStore
from tests.postgres_test_schema import ensure_test_schema


class PostgresJobStoreTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        dsn = os.getenv("RAG_TEST_POSTGRES_DSN")
        if dsn:
            ensure_test_schema(dsn)

    def test_create_get_update_job(self):
        dsn = os.getenv("RAG_TEST_POSTGRES_DSN")
        if not dsn:
            self.skipTest("set RAG_TEST_POSTGRES_DSN to run postgres store tests")
        job_id = f"j-{uuid4()}"
        store = PostgresJobStore(dsn=dsn)
        created = store.create_job(
            {
                "job_id": job_id,
                "document_id": "d1",
                "status": "queued",
                "progress": 0,
                "attempt": 0,
                "error_code": None,
                "error_message": None,
                "started_at": None,
                "finished_at": None,
            }
        )
        self.assertEqual(created["job_id"], job_id)
        updated = store.update_job(job_id, status="running", progress=30, attempt=1)
        self.assertEqual(updated["status"], "running")
        loaded = store.get_job(job_id)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["status"], "running")

    def test_list_jobs_returns_inserted_records(self):
        dsn = os.getenv("RAG_TEST_POSTGRES_DSN")
        if not dsn:
            self.skipTest("set RAG_TEST_POSTGRES_DSN to run postgres store tests")
        store = PostgresJobStore(dsn=dsn)
        first = f"j-{uuid4()}"
        second = f"j-{uuid4()}"
        for job_id in (first, second):
            store.create_job(
                {
                    "job_id": job_id,
                    "document_id": "d1",
                    "status": "queued",
                    "progress": 0,
                    "attempt": 0,
                    "error_code": None,
                    "error_message": None,
                    "started_at": None,
                    "finished_at": None,
                }
            )
        jobs = [item for item in store.list_jobs() if item["job_id"] in {first, second}]
        self.assertEqual(len(jobs), 2)

    def test_claim_next_queued(self):
        dsn = os.getenv("RAG_TEST_POSTGRES_DSN")
        if not dsn:
            self.skipTest("set RAG_TEST_POSTGRES_DSN to run postgres store tests")
        store = PostgresJobStore(dsn=dsn)
        first = f"j-{uuid4()}"
        second = f"j-{uuid4()}"
        for job_id in (first, second):
            store.create_job(
                {
                    "job_id": job_id,
                    "document_id": f"d-{uuid4()}",
                    "status": "queued",
                    "progress": 0,
                    "attempt": 0,
                    "error_code": None,
                    "error_message": None,
                    "started_at": None,
                    "finished_at": None,
                }
            )
        claimed = store.claim_next_queued("2026-04-03T00:00:00+00:00")
        self.assertIsNotNone(claimed)
        self.assertEqual(claimed["status"], "running")


if __name__ == "__main__":
    unittest.main()
