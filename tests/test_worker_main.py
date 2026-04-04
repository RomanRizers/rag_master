import unittest
from unittest.mock import Mock, patch

from backend.worker import main as worker_main


class WorkerMainTestCase(unittest.TestCase):
    @patch("backend.worker.main.time.sleep")
    @patch("backend.worker.main.signal.signal")
    @patch("backend.worker.main.build_services")
    def test_main_uses_ingestion_service_from_app_services(self, build_services_mock, signal_mock, sleep_mock):
        ingestion_service = Mock()
        ingestion_service.claim_next_job.side_effect = [None]
        services = Mock()
        services.ingestion_service = ingestion_service
        build_services_mock.return_value = services

        previous_running = worker_main._running
        worker_main._running = True

        def stop_after_first_sleep(_seconds):
            worker_main._running = False

        sleep_mock.side_effect = stop_after_first_sleep

        try:
            worker_main.main()
        finally:
            worker_main._running = previous_running

        build_services_mock.assert_called_once()
        ingestion_service.claim_next_job.assert_called_once()
        services.close.assert_called_once()
        self.assertEqual(signal_mock.call_count, 2)


if __name__ == "__main__":
    unittest.main()
