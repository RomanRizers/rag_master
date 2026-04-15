import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import create_app


class _HealthyService:
    def live(self):
        return {"status": "ok"}

    def ready(self):
        return {"status": "ok", "checks": {"qdrant": True, "storage": True}}, True


class _DegradedService:
    def live(self):
        return {"status": "ok"}

    def ready(self):
        return {"status": "degraded", "checks": {"qdrant": False, "storage": True}}, False


class HealthApiTestCase(unittest.TestCase):
    def setUp(self):
        app = create_app()
        self.client = TestClient(app)

    @patch("backend.api.routes.get_health_service")
    def test_health_live_returns_200(self, get_health_service_mock):
        get_health_service_mock.return_value = _HealthyService()
        response = self.client.get("/health/live")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    @patch("backend.api.routes.get_health_service")
    def test_health_ready_returns_200_when_all_checks_pass(self, get_health_service_mock):
        get_health_service_mock.return_value = _HealthyService()
        response = self.client.get("/health/ready")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertTrue(payload["checks"]["qdrant"])
        self.assertTrue(payload["checks"]["storage"])

    @patch("backend.api.routes.get_health_service")
    def test_health_ready_returns_503_when_degraded(self, get_health_service_mock):
        get_health_service_mock.return_value = _DegradedService()
        response = self.client.get("/health/ready")
        self.assertEqual(response.status_code, 503)
        payload = response.json()
        self.assertEqual(payload["status"], "degraded")
        self.assertFalse(payload["checks"]["qdrant"])
        self.assertTrue(payload["checks"]["storage"])


if __name__ == "__main__":
    unittest.main()
