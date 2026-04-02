import tempfile
import unittest

from backend.infrastructure.job_store.sqlite import SqliteJobStore


class SqliteJobStoreTestCase(unittest.TestCase):
    def test_create_get_update_job(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SqliteJobStore(db_path=f"{temp_dir}/jobs.db")
            created = store.create_job(
                {
                    "job_id": "j1",
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
            self.assertEqual(created["job_id"], "j1")

            updated = store.update_job("j1", status="running", progress=30, attempt=1)
            self.assertEqual(updated["status"], "running")
            self.assertEqual(updated["progress"], 30)
            self.assertEqual(updated["attempt"], 1)

            loaded = store.get_job("j1")
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded["status"], "running")

    def test_list_jobs_returns_inserted_records(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SqliteJobStore(db_path=f"{temp_dir}/jobs.db")
            for index in range(2):
                store.create_job(
                    {
                        "job_id": f"j{index}",
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

            jobs = store.list_jobs()
            self.assertEqual(len(jobs), 2)


if __name__ == "__main__":
    unittest.main()
